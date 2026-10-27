"""Nightshift cloud-pin protocol fixtures, not real inference or financial proof."""
from copy import deepcopy
import json
import time
from unittest.mock import patch

import pytest

from backend.investigation.model_contracts import tool_definitions
from backend.providers.meterless_client import (
    ClientError, MeterlessClient, NIGHTSHIFT_NVIDIA_MODEL as MODEL,
    valid_runtime_model, project_nightshift_receipt, validate_nightshift_receipt,
)
from backend.providers.structured import NightshiftStructuredProvider, StructuredProviderError
from backend.tests.test_structured_provider import answer, fixture_server

TOKEN = 'fixture-runtime-secret'


def cloud_answer():
    result = answer()
    result.update({'id': 'chatcmpl-fixture-1', 'model': MODEL,
        'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120},
        'meterless': {'schema': 'meterless.compute_receipt.v1',
            'receipt_id': 'rcpt_fixture-1', 'decision_id': 'req_fixture-1',
            'requested_model': MODEL, 'provider_model': MODEL, 'routed_model': MODEL,
            'winning_route': {'provider': 'nvidia', 'model': MODEL},
            'requires_review': False, 'from_cache': False,
            'untrusted_diagnostic': TOKEN}})
    result['choices'][0]['message']['reasoning_content'] = 'Do not retain private model reasoning.'
    return result


def client():
    return MeterlessClient('http://127.0.0.1:1', TOKEN)


def test_only_verified_concrete_cloud_pin_added():
    assert valid_runtime_model(MODEL) and valid_runtime_model('meterless/auto')
    for invalid in ['nvidia/arbitrary', 'nvidia/nemotron-3.5-bolt-e4b',
                    'meterless/nvidia with spaces', 'http://untrusted/model', '', None]:
        assert not valid_runtime_model(invalid)
        with pytest.raises(StructuredProviderError):
            NightshiftStructuredProvider('http://127.0.0.1:1', TOKEN, invalid, enabled=True)


def test_discovery_does_not_infer_arbitrary_cloud_models():
    rows = [{'id': MODEL, 'owned_by': 'nvidia'}, {'id': 'meterless/auto'},
            {'id': 'nvidia/arbitrary', 'owned_by': 'nvidia'},
            {'id': MODEL, 'owned_by': 'unexpected'}, {'id': 'unrelated'}]
    with patch.object(MeterlessClient, '_request', return_value={'data': rows}):
        assert client().discover() == {'status': 'online', 'models': [MODEL, 'meterless/auto']}


def test_cloud_wire_and_projection_preserve_host_contract_and_private_boundaries():
    original = tool_definitions()
    before = deepcopy(original)
    with patch.object(MeterlessClient, '_request', return_value=cloud_answer()) as request:
        result = client().structured({}, original, MODEL, with_receipt=True)
    assert original == before
    body = request.call_args.args[1]
    assert body['model'] == MODEL and body['chat_template_kwargs'] == {'enable_thinking': False}
    assert body['tool_choice'] == 'required' and body['parallel_tool_calls'] is False
    assert '$defs' not in json.dumps(body['tools']) and '$ref' not in json.dumps(body['tools'])
    assert [t['function']['name'] for t in body['tools']] == [t['function']['name'] for t in original]
    assert json.loads(result['proposal']) == {'tool': 'query_financial_evidence', 'arguments': {'metrics': ['revenue']}}
    assert result['receipt']['provider'] == 'nvidia' and result['receipt']['from_cache'] is False
    assert TOKEN not in json.dumps(result) and 'reasoning_content' not in json.dumps(result)
    # Runtime's compute requires_review:false never overrides financial review.
    assert 'requires_review' not in result['receipt']


@pytest.mark.parametrize('kind', ['response_model', 'requested_model', 'provider_model',
    'routed_model', 'winning_model', 'provider', 'cached', 'missing', 'wrong_schema', 'token_in_id'])
def test_wrong_or_unproven_cloud_receipts_fail_closed(kind):
    payload = cloud_answer()
    if kind == 'response_model': payload['model'] = 'meterless/auto'
    elif kind in ('requested_model', 'provider_model', 'routed_model'): payload['meterless'][kind] = 'wrong'
    elif kind == 'winning_model': payload['meterless']['winning_route']['model'] = 'wrong'
    elif kind == 'provider': payload['meterless']['winning_route']['provider'] = 'local'
    elif kind == 'cached': payload['meterless']['from_cache'] = True
    elif kind == 'missing': del payload['meterless']['provider_model']
    elif kind == 'wrong_schema': payload['meterless']['schema'] = 'unexpected'
    elif kind == 'token_in_id': payload['id'] = 'chatcmpl-' + TOKEN
    with patch.object(MeterlessClient, '_request', return_value=payload):
        with pytest.raises(ClientError) as failure:
            client().structured({}, tool_definitions(), MODEL, with_receipt=True)
    assert TOKEN not in str(failure.value)


@pytest.mark.parametrize('value', [True, -1, 1.5, '20', 1_000_000_001])
def test_usage_cannot_smuggle_text_or_noncanonical_numbers(value):
    payload = cloud_answer()
    payload['usage']['completion_tokens'] = value
    with pytest.raises(ClientError):
        project_nightshift_receipt(payload, TOKEN)


def test_receipt_projection_requires_fixed_shape():
    receipt = project_nightshift_receipt(cloud_answer(), TOKEN)
    receipt['arbitrary_private_diagnostic'] = TOKEN
    with pytest.raises(ClientError):
        validate_nightshift_receipt(receipt)


@pytest.mark.parametrize('value', [None, 'untrusted text', [], 4])
def test_malformed_metadata_is_a_sanitized_protocol_error(value):
    payload = cloud_answer()
    payload['meterless'] = value
    with pytest.raises(ClientError, match='Invalid cloud execution receipt'):
        project_nightshift_receipt(payload, TOKEN)


def test_cloud_worker_retains_provenance_without_promoting_financial_acceptance():
    with fixture_server(cloud_answer()) as (url, requests):
        provider = NightshiftStructuredProvider(url, TOKEN, MODEL, enabled=True)
        proposal = json.loads(provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()+8))
        assert proposal['tool'] == 'query_financial_evidence'
        assert len(provider.provider_receipts) == 1 and provider.execution_kind == 'unverified_provider'
        copy = provider.provider_receipts
        copy[0]['provider'] = 'tampered'
        assert provider.provider_receipts[0]['provider'] == 'nvidia'
        assert len(requests) == 1 and requests[0][2]['model'] == MODEL
        assert TOKEN not in json.dumps(provider.provider_receipts)


def test_rejected_native_response_keeps_only_validated_provenance():
    payload = cloud_answer()
    payload['choices'][0]['message']['content'] = 'Unrestricted answer is not a tool proposal'
    with fixture_server(payload) as (url, requests):
        provider = NightshiftStructuredProvider(url, TOKEN, MODEL, enabled=True)
        with pytest.raises(StructuredProviderError, match='structured_provider_unavailable'):
            provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()+8)
        assert len(provider.provider_receipts) == 1
        assert 'Unrestricted answer' not in json.dumps(provider.provider_receipts)
        assert len(requests) == 1


def test_eight_receipts_bound_additional_worker_requests():
    receipt = project_nightshift_receipt(cloud_answer(), TOKEN)
    envelope = json.dumps({'proposal': json.dumps({'tool': 'query_financial_evidence',
        'arguments': {'metrics': ['revenue']}}), 'receipt': receipt}).encode()
    provider = NightshiftStructuredProvider('http://127.0.0.1:1', TOKEN, MODEL, enabled=True)
    with patch('backend.providers.structured.run_structured_worker', return_value=envelope) as worker:
        for _ in range(8):
            provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()+8)
        with pytest.raises(StructuredProviderError):
            provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()+8)
        assert worker.call_count == 8
