"""Local HTTP bridge to the accepted deterministic controller and real H-MEM."""
import json
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, ValidationError

from .models import StrictModel
from .investigation import InvestigationInput, run_investigation
from .investigation.memory import HMemMemory
from .run_store import RunStore, RunNotFound, ReviewConflict

router = APIRouter(prefix='/api/investigation-runs', tags=['local investigation runs'])


def get_store():
    return RunStore()


def get_runner():
    return run_investigation


def get_memory():
    return HMemMemory(scope_id='local-cli', actor='local-human')


class ReviewInput(StrictModel):
    report_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_review_version: int = Field(strict=True, ge=0, le=2_147_483_647)
    decision: Literal['approved', 'rejected']
    comment: str = Field(default='', max_length=2000)


def local_request(request: Request):
    """Development-only boundary; not a substitute for multiuser authorization."""
    try:
        host = urlsplit('http://' + request.headers.get('host', ''))
        allowed = {'localhost', '127.0.0.1', '[::1]', '::1', 'testserver'}
        if host.hostname not in allowed or host.username or host.password or host.path:
            raise ValueError
        if host.port not in (None, 8000, 5173):
            raise ValueError
        origin = request.headers.get('origin')
        if origin is not None:
            parsed = urlsplit(origin)
            if (parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1', 'testserver'}
                    or parsed.port not in (None, 8000, 5173) or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment):
                raise ValueError
        if request.client and request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
            raise ValueError
    except ValueError:
        raise HTTPException(403, 'Investigation runs are restricted to the trusted local development interface.') from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


async def typed_body(request, model):
    local_request(request)
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise HTTPException(415, 'Send an application/json request.')
    body = bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body) > 65_536:
            raise HTTPException(413, 'Investigation request exceeds the local request limit.')
    try:
        value = json.loads(body, object_pairs_hook=_unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return model.model_validate(value)
    except (ValueError, TypeError, ValidationError, RecursionError):
        raise HTTPException(422, 'Check the typed investigation or review fields; unknown fields are not accepted.') from None


def failure(error):
    if isinstance(error, RunNotFound):
        return HTTPException(404, {'code': 'run_not_found', 'message': 'Investigation run was not found.'})
    if isinstance(error, ReviewConflict):
        return HTTPException(409, {'code': 'review_conflict', 'message': 'The report digest or review version changed. Reload this run before reviewing again.'})
    return HTTPException(503, {'code': 'run_or_storage_unavailable', 'message': 'The investigation or local storage is unavailable. No result or review success was substituted.'})


@router.post('')
async def create_run(request: Request, store=Depends(get_store), runner=Depends(get_runner), memory=Depends(get_memory)):
    data = await typed_body(request, InvestigationInput)
    try:
        # The synchronous controller owns evidence/tool/deadline enforcement.
        # Run it off the event loop so read/review routes remain responsive.
        from starlette.concurrency import run_in_threadpool
        report = await run_in_threadpool(runner, data, memory=memory)
        scope = report.get('request', {})
        original = data.request.model_dump(mode='json')
        if (any(scope.get(key) != original[key] for key in ('fiscal_year', 'period', 'as_of', 'evidence_backend'))
                or str(scope.get('company', {}).get('cik', '')).zfill(10) != original['company']['cik'].zfill(10)
                or report.get('original_claims') != [claim.model_dump(mode='json') for claim in data.claim_inputs]):
            raise ValueError('Controller scope mismatch')
        return store.save(report)
    except Exception as error:
        raise failure(error) from None


@router.get('/{run_id}')
def read_run(run_id: UUID, request: Request, store=Depends(get_store)):
    local_request(request)
    try:
        return store.get(str(run_id))
    except Exception as error:
        raise failure(error) from None


@router.post('/{run_id}/review')
async def review_run(run_id: UUID, request: Request, store=Depends(get_store)):
    data = await typed_body(request, ReviewInput)
    try:
        return store.review(str(run_id), data.report_digest, data.expected_review_version, data.decision, data.comment)
    except Exception as error:
        raise failure(error) from None
