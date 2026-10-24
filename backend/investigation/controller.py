"""Bounded deterministic groundwork for an incomplete investigation agent.

Decisions are explicit rules. No model, invented quote, or inferred human approval.
"""
import hashlib
import time
import uuid

from backend.models import Evidence
from .models import InvestigationInput
from .retrieval import retrieve
from .tools import verify


def run_investigation(data: InvestigationInput | dict, *, memory=None, retriever=None,
                      timeout_seconds=120, max_tool_calls=8, clock=time.monotonic):
    data = data if isinstance(data, InvestigationInput) else InvestigationInput.model_validate(data)
    if not 0 < timeout_seconds <= 120 or not 1 <= max_tool_calls <= 8:
        raise ValueError('Bounds must be positive and no greater than 120 seconds / 8 tool calls')
    request = data.request.model_copy(deep=True)
    started = clock()
    deadline = started + timeout_seconds
    trace, evidence, rejected, calculations, memories = [], [], [], [], []
    limitations = ['Incomplete agent implementation: no live model extraction, reasoning or generation.',
                   'Typed human assertions and deterministic rules choose tools and conclusions.',
                   'Financial inputs cross the existing float boundary; Decimal operations do not recover original source precision.',
                   'Fiscal-year/quarter identity is validated by the existing source readers; the legacy Evidence object carries dates, not a second independent fiscal-calendar mapping.',
                   'Only GAAP revenue, diluted EPS, net income and net margin are supported; no reconciliation or causal reasoning.',
                   'GAAP classification is restricted to the allowlisted us-gaap concepts returned by existing scoped SEC/Zetaris readers; no non-GAAP reconciliation is inferred.',
                   'A Zetaris challenge may request the existing SEC reader for additional concepts; no independent issuer release or arbitrary document is fetched.']
    calls = 0
    failure = False

    def remaining():
        return max(0, deadline - clock())

    def event(state, **kwargs):
        if len(trace) < 10:
            trace.append({'step': len(trace) + 1, 'state': state,
                          'elapsed_ms': round(max(0, clock() - started) * 1000), **kwargs})

    def permit():
        nonlocal calls, failure
        if calls >= max_tool_calls or remaining() <= 0:
            failure = True
            return False
        calls += 1
        return True

    def collect(backend=None):
        nonlocal failure
        if not permit():
            return {'ok': False, 'error_code': 'budget_exhausted'}
        try:
            tool_request = request.model_copy(deep=True)
            tool_request.evidence_backend = backend or request.evidence_backend
            rows = (retriever or retrieve)(tool_request, min(45, remaining()))
            request.company = tool_request.company
            if remaining() <= 0:
                raise TimeoutError
            for raw in rows:
                e = raw if isinstance(raw, Evidence) else Evidence.model_validate(raw)
                reason = None
                days = (e.period_end - e.period_start).days + 1
                valid_duration = 330 <= days <= 380 if request.period == 'FY' else 70 <= days <= 105
                if e.published_at > request.as_of or e.period_end > request.as_of:
                    reason = 'after_as_of'
                elif not valid_duration:
                    reason = 'duration_mismatch'
                elif f'/edgar/data/{int(request.company.cik)}/' not in e.url:
                    reason = 'issuer_not_verified_in_document_url'
                elif not e.document.strip() or not e.locator.strip():
                    reason = 'missing_source_locator'
                if reason:
                    rejected.append({'evidence_id': e.id, 'reason': reason})
                    continue
                if any(old == e for old in evidence):
                    continue
                if any(old.id == e.id for old in evidence):
                    # Preserve contrary versions rather than overwrite an earlier fact.
                    suffix = hashlib.sha256(e.model_dump_json().encode()).hexdigest()[:12]
                    e = e.model_copy(update={'id': e.id + '-version-' + suffix})
                if any(old == e for old in evidence):
                    continue
                evidence.append(e)
            return {'ok': True, 'eligible_count': len(evidence), 'rejected_count': len(rejected)}
        except Exception:
            failure = True
            return {'ok': False, 'error_code': 'evidence_unavailable_or_deadline'}

    def verify_batch():
        nonlocal calculations
        if not permit():
            return [{'claim_id': c.id, 'classification': 'unresolved', 'evidence_ids': [],
                     'explanation': 'Global time/tool budget exhausted.', 'supporting_findings': [],
                     'challenging_findings': []} for c in data.claim_inputs]
        findings, batch = [], []
        for claim in data.claim_inputs:
            finding, computed = verify(claim, evidence)
            findings.append(finding)
            batch.extend(computed)
        calculations = batch
        return findings

    event('validate', decision='Typed human assertions accepted; model extraction unavailable.')
    event('retrieve', tool='retrieve_financial_evidence', backend=request.evidence_backend, **collect())
    # A memory adapter must enforce its own <=3 second worker deadline. Recall
    # sees only current eligible facts and can never replace financial values.
    if memory is not None and evidence and remaining() >= 3 and permit():
        try:
            memories = memory.recall(request, evidence)
            if remaining() <= 0:
                raise TimeoutError
            event('recall', tool='hmem_recall', ok=True, count=len(memories))
        except Exception:
            memories = []
            limitations.append('Reviewed memory was unavailable; no correction was applied.')
            event('recall', tool='hmem_recall', ok=False, error_code='memory_unavailable')
    findings = verify_batch()
    initial = [dict(f) for f in findings]
    event('verify', tool='financial_verification_batch', classifications=[f['classification'] for f in findings])
    challenges = []
    for f in findings:
        claim = next(c for c in data.claim_inputs if c.id == f['claim_id'])
        cited = [e for e in evidence if e.id in f['evidence_ids']]
        issues = ['Legacy float boundary limits precision; source rounding is not independently established.']
        if f['classification'] != 'supported':
            issues.append(f['explanation'])
        if f['evidence_ids'] and any(e.source_sha256 is None for e in evidence if e.id in f['evidence_ids']):
            issues.append('Source content hash is unavailable for at least one citation.')
        challenges.append({'claim_id': f['claim_id'], 'checks': issues,
                           'quality_checks': {'accounting_basis_is_gaap': claim.accounting_basis == 'GAAP',
                                              'exact_period_matches': bool(cited) and all(e.period_start == claim.period_start and e.period_end == claim.period_end for e in cited),
                                              'publication_cutoff_met': bool(cited) and all(e.published_at <= request.as_of for e in cited),
                                              'citations_resolve': bool(cited) and len(cited) == len(f['evidence_ids']),
                                              'comparable_value_check': f['classification'],
                                              'source_precision_established': False},
                           'additional_evidence_needed': f['classification'] != 'supported'})
    recheck = any(c['additional_evidence_needed'] for c in challenges)
    event('challenge', decision='Request one fresh read for missing or contrary evidence.' if recheck else 'Comparable values agree; retain precision qualifications.', findings=challenges)
    if recheck:
        recheck_backend = 'sec' if request.evidence_backend == 'zetaris' else request.evidence_backend
        event('recheck', tool='retrieve_financial_evidence', backend=recheck_backend, reason='Explicit challenger found missing, conflicting, unsupported or contrary evidence; request additional SEC concepts when starting from Zetaris.', **collect(recheck_backend))
        findings = verify_batch()
        event('reverify', tool='financial_verification_batch', classifications=[f['classification'] for f in findings])
    if failure:
        limitations.append('A retrieval failed or the shared time/tool budget was exhausted; any earlier evidence is retained for human review.')
        for f in findings:
            # A failed challenge cannot establish that the initial explanation survived.
            f['classification'] = 'unresolved'
            f['explanation'] += ' The bounded investigation could not complete its checks.'
    for f in findings:
        f['supporting_findings'] = ['Comparable evidence and declared tolerance agree.'] if f['classification'] == 'supported' else []
        f['challenging_findings'] = next(c['checks'] for c in challenges if c['claim_id'] == f['claim_id'])
    event('conclude', decision='Return source-backed deterministic findings for required human review; model capability remains incomplete.')
    return {'schema_version': 'claimtrace.investigation.v1', 'run_id': str(uuid.uuid4()),
            'execution_mode': 'incomplete_no_live_model', 'model_inference_performed': False,
            'request': request.model_dump(mode='json'),
            'original_claims': [c.model_dump(mode='json') for c in data.claim_inputs],
            'status': 'partial' if evidence else 'blocked',
            'evidence': [e.model_dump(mode='json') for e in evidence],
            'rejected_evidence': rejected, 'initial_findings': initial, 'findings': findings,
            'calculations': calculations, 'challenge_findings': challenges,
            'citations': [{'evidence_id': e.id, 'url': e.url, 'document': e.document,
                           'published_at': e.published_at.isoformat(), 'locator': e.locator,
                           'source_mode': e.source_mode, 'source_sha256': e.source_sha256} for e in evidence],
            'reviewed_memory': memories, 'trace': trace, 'tool_calls': calls,
            'limits': {'max_claims': 3, 'max_tool_calls': max_tool_calls, 'max_transitions': 10,
                       'timeout_seconds': timeout_seconds, 'max_rechecks': 1, 'automatic_retries': 0},
            'limitations': limitations, 'human_review_status': 'required'}
