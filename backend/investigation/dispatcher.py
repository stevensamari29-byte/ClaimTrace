"""Restricted host execution seam. No working live model adapter is supplied.

Only trusted application code constructs providers/retrievers/disclosures. Source
text and provider output remain untrusted data, never commands or configuration.
"""
import json
import time
from typing import Protocol

from backend.models import InvestigationRequest
from .model_contracts import (ALL_CHECKS, AdditionalInvestigation, CalculateClaim,
    ExtractClaims, ModelConclusion, ModelProposalGate, QueryEvidence, SelectChecks,
    tool_definitions)
from .retrieval import retrieve
from .tools import CONCEPTS


class DispatchError(RuntimeError):
    """Sanitized failure code; private provider/reader exceptions never escape."""


class StructuredProvider(Protocol):
    """Future integration contract, not implemented by MeterlessClient.chat.

    Trusted adapters must enforce the absolute monotonic deadline themselves,
    including streaming/response reads, with no background calls after expiry.
    Return exactly one JSON {tool, arguments} envelope, <=64 KiB UTF-8. This is
    an application protocol; actual Nightshift tool-call support is unverified.
    """
    structured_deadline_protocol: str  # 'claimtrace.structured-deadline.v1'
    execution_kind: str  # 'protocol_fixture' or 'unverified_provider'

    def propose(self, *, context: dict, tools: list, deadline: float) -> str: ...


def decode_proposal(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > 65536:
        raise DispatchError('invalid_proposal')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
        if not isinstance(value, dict) or set(value) != {'tool', 'arguments'} or not isinstance(value['tool'], str) or not isinstance(value['arguments'], dict):
            raise ValueError
        return value
    except (ValueError, TypeError, RecursionError):
        raise DispatchError('invalid_proposal') from None


class RestrictedDispatcher:
    """One immutable investigation and shared execution budget.

    Public dispatch accepts JSON, never Python objects from model text. No SQL,
    arbitrary URLs, commands, memory writes or approvals are exposed. An invalid
    proposal or failed effect is terminal; previously supported findings cannot
    become a final report after a failed recheck/provider/time boundary.
    """
    def __init__(self, request, *, disclosures=(), evidence=(), retriever=None,
                 clock=time.monotonic, timeout_seconds=120, max_tool_calls=8, memory=None):
        if (type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 120 or
                type(max_tool_calls) is not int or not 1 <= max_tool_calls <= 8):
            raise ValueError('Invalid execution bounds')
        self._clock = clock
        self._started = clock()
        self._deadline = self._started + timeout_seconds
        self._max_calls = max_tool_calls
        self._calls = 0
        self._transitions = 0
        self._rechecks = 0
        self._queried = False
        self._failed = None
        self._conclusion = None
        self._trace = []
        self._calculations = []
        self._challenges = []
        if memory is not None:
            from .memory import HMemMemory
            if type(memory) is not HMemMemory:
                raise ValueError('Trusted H-MEM adapter required')
        self._memory = memory
        self._memory_context = []
        self._memory_status = 'not_requested'
        self._retriever = retriever or retrieve
        self._request = request if isinstance(request, InvestigationRequest) else InvestigationRequest.model_validate(request)
        self._request = self._request.model_copy(deep=True)
        disclosures = tuple(disclosures)
        if len(disclosures) > 3 or sum(len(d.text) for d in disclosures) > 12000:
            raise ValueError('Disclosure text exceeds shared bounds')
        self._gate = ModelProposalGate(self._request, disclosures=disclosures, clock=clock)
        self._gate.register_host_evidence(evidence)
        self._disclosures = [{'id': d.id, 'text': d.text, 'url': d.url,
                             'published_at': d.published_at.isoformat(),
                             'text_sha256': d.text_sha256,
                             'period_start': d.period_start.isoformat(), 'period_end': d.period_end.isoformat()}
                            for d in disclosures]

    def _check(self):
        if self._failed:
            raise DispatchError(self._failed)
        if self._clock() >= self._deadline:
            self._fail('deadline_exhausted')
        if self._conclusion is not None:
            raise DispatchError('investigation_closed')

    def _fail(self, code):
        self._failed = code
        self._conclusion = None
        raise DispatchError(code)

    def _event(self, state, **details):
        if self._transitions >= 10:
            self._fail('transition_budget_exhausted')
        self._transitions += 1
        self._trace.append({'step': self._transitions, 'state': state, **details})

    def context(self):
        """Defensive bounded source/tool context; no private config or callables."""
        return json.loads(json.dumps({'scope': self._gate.scope,
            'disclosures': self._disclosures, **self._gate.host_snapshot(),
            'tool_results': self._trace, 'human_review_status': 'required',
            'reviewed_memory_context': self._memory_context, 'memory_status': self._memory_status,
            'source_text_is_untrusted': True, 'semantic_mapping_status': 'unverified'}))

    def _collect(self, metrics=None, recheck=False):
        request = InvestigationRequest.model_validate(self._gate.scope)
        if recheck and request.evidence_backend == 'zetaris':
            request.evidence_backend = 'sec'
        expected = request.model_dump(mode='json')
        try:
            rows = self._retriever(request, min(45, self._deadline - self._clock()))
            self._check()
            # Readers may canonicalize display names, but not the CIK or scope.
            actual = request.model_dump(mode='json')
            if (actual['fiscal_year'], actual['period'], actual['as_of'], actual['evidence_backend'], int(actual['company']['cik'])) != (expected['fiscal_year'], expected['period'], expected['as_of'], expected['evidence_backend'], int(expected['company']['cik'])):
                raise ValueError('Reader changed scope')
            rows = list(rows)
            # Validate the entire returned batch, including nonselected concepts,
            # before filtering. Reader output can never introduce a future fact.
            if metrics is not None:
                allowed = set().union(*(CONCEPTS[m] for m in metrics))
                # Scoped reader returns at most 25 facts. Validate all first in
                # a throwaway gate; this does not reset the actual run's budget.
                validator = ModelProposalGate(self._gate.scope, clock=self._clock)
                validator.register_host_evidence(rows)
                rows = [row for row in validator.host_snapshot()['evidence'] if row['concept'] in allowed]
            self._gate.register_host_evidence(rows)
            refreshed = self._gate.refresh_host_verifications()
            self._calculations = refreshed['calculations']
            if self._memory is not None:
                self._recall_memory(request)
        except DispatchError:
            raise
        except Exception:
            self._fail('evidence_unavailable_or_invalid')

    def _recall_memory(self, request):
        """Recall only after host ingestion; never grant memory tool effects."""
        self._check()
        original_timeout = self._memory.timeout
        try:
            self._memory.timeout = min(original_timeout, 3, self._deadline - self._clock())
            rows = self._memory.recall(request, self._gate.host_snapshot()['evidence'])
            self._check()
            if not isinstance(rows, list) or len(rows) > 8:
                raise ValueError
            encoded = json.dumps(rows, allow_nan=False)
            if len(encoded.encode('utf-8')) > 16384:
                raise ValueError
            self._memory_context = json.loads(encoded)
            self._memory_status = 'reviewed_context_only_not_financial_fact'
        except DispatchError:
            raise
        except Exception:
            self._memory_context = []
            self._memory_status = 'unavailable'
            self._check()
        finally:
            self._memory.timeout = original_timeout

    def _challenge(self):
        snapshot = self._gate.host_snapshot()
        if not snapshot['claims'] or any(set(snapshot['selected_checks'].get(c['id'], ())) != set(ALL_CHECKS) for c in snapshot['claims']):
            return
        refreshed = self._gate.refresh_host_verifications()
        self._calculations = refreshed['calculations']
        # The verifier actually checks exact dates/units/GAAP/conflicts, while
        # ingestion checks issuer/provenance/cutoff. Preserve every qualification.
        self._challenges = [{'claim_id': f['claim_id'], 'checks_run': list(ALL_CHECKS),
            'classification': f['classification'], 'evidence_ids': f['evidence_ids'],
            'missing_context': ['Semantic extraction requires human review.',
                                'Original source decimal precision is unavailable.'],
            'explanation': f['explanation']} for f in refreshed['findings']]
        self._gate.record_completed_challenge()
        # Host checks are part of this accepted tool transition, not an extra
        # model round. Keep their observable result beside the actual effect.
        self._trace[-1]['host_challenge'] = self._challenges

    def dispatch(self, proposal_json):
        self._check()
        if self._calls >= self._max_calls:
            self._fail('tool_budget_exhausted')
        self._calls += 1  # Invalid attempts also consume budget.
        try:
            envelope = decode_proposal(proposal_json)
            name, arguments = envelope['tool'], envelope['arguments']
            result = self._gate.validate(name, arguments)
            proposal_type = {'query_financial_evidence': QueryEvidence,
                             'request_additional_investigation': AdditionalInvestigation,
                             'calculate_financial_claim': CalculateClaim,
                             'select_evidence_checks': SelectChecks,
                             'propose_extracted_claims': ExtractClaims,
                             'submit_investigation_conclusion': ModelConclusion}[name]
            if proposal_type is QueryEvidence:
                if self._queried:
                    self._fail('initial_query_already_used')
                self._queried = True
                self._collect(arguments['metrics'])
            elif proposal_type is AdditionalInvestigation:
                self._rechecks += 1
                self._collect(recheck=True)
            self._check()
            self._event(name)
            if proposal_type in (CalculateClaim, AdditionalInvestigation, SelectChecks, QueryEvidence):
                self._challenge()
            self._check()
            if proposal_type is ModelConclusion:
                # Never render unvalidated model prose as the financial briefing.
                self._conclusion = {'findings': list(self._gate.host_snapshot()['verified'].values()),
                                    'briefing': 'Host-verified financial checks; semantic interpretation requires human review.'}
            return json.loads(json.dumps({'ok': True, 'tool': name, 'result': result,
                    'host_state': self._gate.host_snapshot(), 'human_review_status': 'required'}))
        except DispatchError as error:
            self._failed = str(error)
            self._conclusion = None
            raise
        except Exception:
            self._fail('proposal_rejected')

    def run(self, provider=None):
        """Execute trusted structured protocol, or fail explicitly before network.

        Existing MeterlessClient has no structured/deadline protocol and is
        deliberately rejected. A declaration is a trusted adapter contract,
        never evidence of genuine live inference or underlying Nemotron usage.
        """
        try:
            self._check()
            if (getattr(provider, 'structured_deadline_protocol', None) != 'claimtrace.structured-deadline.v1' or
                    getattr(provider, 'execution_kind', None) not in ('protocol_fixture', 'unverified_provider') or
                    not callable(getattr(provider, 'propose', None))):
                self._fail('structured_provider_unavailable')
            for _ in range(self._max_calls - self._calls):
                self._check()
                try:
                    raw = provider.propose(context=self.context(), tools=tool_definitions(), deadline=self._deadline)
                except Exception:
                    self._fail('provider_unavailable')
                self._check()
                self.dispatch(raw)
                if self._conclusion is not None:
                    return self.report(provider_kind=provider.execution_kind)
            self._fail('tool_budget_exhausted')
        except DispatchError:
            return self.report(provider_kind=getattr(provider, 'execution_kind', 'unavailable'))

    def report(self, *, provider_kind='none'):
        if provider_kind not in ('none', 'unavailable', 'protocol_fixture', 'unverified_provider'):
            provider_kind = 'unavailable'
        if self._clock() >= self._deadline and self._failed is None:
            self._failed, self._conclusion = 'deadline_exhausted', None
        snapshot = self._gate.host_snapshot()
        return json.loads(json.dumps({'schema_version': 'claimtrace.dispatcher.v1',
            'execution_mode': 'incomplete_no_verified_live_model',
            'live_inference_verified': False, 'provider_kind': provider_kind,
            'model_inference_performed': False if provider_kind in ('none', 'unavailable', 'protocol_fixture') else None,
            'status': 'blocked' if self._failed else ('review_required' if self._conclusion else 'in_progress'),
            'error_code': self._failed, 'scope': self._gate.scope,
            'conclusion': self._conclusion, 'diagnostic_findings': list(snapshot['verified'].values()),
            'evidence': snapshot['evidence'], 'calculations': self._calculations,
            'challenge_findings': self._challenges,
            'citations': [{'evidence_id': e['id'], 'url': e['url'], 'published_at': e['published_at'],
                           'locator': e['locator'], 'source_sha256': e['source_sha256'], 'source_mode': e['source_mode']}
                          for e in snapshot['evidence']],
            'trace': list(self._trace), 'tool_calls': self._calls, 'rechecks': self._rechecks,
            'limits': {'tool_calls': self._max_calls, 'transitions': 10, 'rechecks': 1,
                       'timeout_seconds': self._deadline - self._started, 'automatic_retries': 0},
            'human_review_status': 'required', 'semantic_mapping_status': 'unverified',
            'limitations': ['No verified live Nightshift/Nemotron inference.',
                           'Exact source quotes do not prove semantic extraction accuracy.',
                           'Existing readers carry fiscal identity; evidence dates alone do not independently establish fiscal calendars.',
                           'Decimal calculations retain the legacy source float precision limitation.',
                           'Optional H-MEM recall is reviewed context only; models cannot write corrections or grant approval.']}))
