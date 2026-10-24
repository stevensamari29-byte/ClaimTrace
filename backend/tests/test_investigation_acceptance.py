"""Independent adversarial acceptance. Injected rows are fixtures, never live receipts."""
from copy import deepcopy
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from backend.investigation.controller import run_investigation
from backend.investigation.models import InvestigationInput
from backend.investigation.memory import HMemMemory, MemoryError


def payload(**claim_changes):
    claim = dict(id='assertion', text='Revenue was USD 100 in the quarter.', metric='revenue',
                 expected_value_decimal='100', unit='USD', accounting_basis='GAAP',
                 period_start='2026-04-01', period_end='2026-06-30')
    claim.update(claim_changes)
    return dict(request=dict(company=dict(name='Fixture issuer', ticker='ISRG', cik='0001035267'),
                             fiscal_year=2026, period='Q2', as_of='2026-07-21', evidence_backend='zetaris'),
                claim_inputs=[claim])


def fact(**changes):
    row = dict(id='fixture-revenue', document='SEC fixture 10-Q',
               url='https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm',
               published_at='2026-07-21', period_start='2026-04-01', period_end='2026-06-30',
               unit='USD', value=100, concept='Revenues', locator='fixture-context',
               source_mode='live_zetaris', source_sha256='a'*64)
    row.update(changes)
    return row


def investigate(data=None, rows=None, **kwargs):
    rows = [fact()] if rows is None else rows
    return run_investigation(data or payload(), retriever=lambda request, timeout: deepcopy(rows), **kwargs)


def assert_integrity(report):
    assert report['execution_mode'] == 'incomplete_no_live_model'
    assert report['model_inference_performed'] is False
    assert report['human_review_status'] == 'required'
    assert report['tool_calls'] <= report['limits']['max_tool_calls']
    assert len(report['trace']) <= 10
    ids = [e['id'] for e in report['evidence']]
    assert len(ids) == len(set(ids))
    citations = {c['evidence_id'] for c in report['citations']}
    for finding in report['findings']:
        assert set(finding['evidence_ids']) <= citations
        if finding['classification'] in ('supported', 'contradicted'):
            assert finding['evidence_ids']


def test_incorrect_calculation_gets_challenged_with_second_real_tool_invocation():
    report = investigate(payload(expected_value_decimal='101'))
    assert_integrity(report)
    assert report['findings'][0]['classification'] == 'contradicted'
    assert sum(t['state'] == 'recheck' for t in report['trace']) == 1
    assert Decimal(report['calculations'][0]['difference_decimal']) == -1


@pytest.mark.parametrize('changes', [dict(unit='USD/shares'), dict(accounting_basis='non-GAAP'),
    dict(period_start='2026-01-01'), dict(metric='unsupported', expected_value_decimal=None)])
def test_ineligible_assertions_are_never_supported(changes):
    report = investigate(payload(**changes))
    assert_integrity(report)
    assert report['findings'][0]['classification'] in ('incomplete', 'unresolved')


@pytest.mark.parametrize('rows', [[], [fact(published_at='2026-07-22')],
    [fact(locator='')], [fact(url='https://www.sec.gov/Archives/edgar/data/320193/filing.htm')],
    [fact(period_start='2026-01-01')]])
def test_missing_future_foreign_or_ytd_evidence_cannot_support(rows):
    report = investigate(rows=rows)
    assert_integrity(report)
    assert report['findings'][0]['classification'] in ('incomplete', 'unresolved')


def test_conflicting_same_id_rows_preserve_both_versions_and_resolvable_citations():
    report = investigate(rows=[fact(), fact(value=101)])
    assert_integrity(report)
    assert report['findings'][0]['classification'] == 'unresolved'
    assert len(report['evidence']) == 2


def test_net_margin_uses_net_income_and_no_zero_denominator():
    margin = payload(metric='net_margin', expected_value_decimal='20', unit='%')
    report = investigate(margin, [fact(value=200), fact(id='income', concept='NetIncomeLoss', value=40)])
    assert_integrity(report)
    assert report['findings'][0]['classification'] == 'supported'
    assert Decimal(report['calculations'][0]['value_decimal']) == 20
    report = investigate(margin, [fact(value=0), fact(id='income', concept='NetIncomeLoss', value=40)])
    assert report['findings'][0]['classification'] == 'unresolved'


def test_one_shared_tool_budget_cannot_be_bypassed_by_multiple_claims():
    data = payload()
    data['claim_inputs'] += [{**data['claim_inputs'][0], 'id':'second'}]
    report = investigate(data, max_tool_calls=1)
    assert_integrity(report)
    assert report['tool_calls'] == 1
    assert all(f['classification'] == 'unresolved' for f in report['findings'])


@pytest.mark.parametrize('field', ['expected_value_decimal', 'tolerance_decimal'])
@pytest.mark.parametrize('number', ['1e999999', '1e-999999', '9'*500])
def test_unbounded_decimal_input_is_rejected_before_arithmetic(field, number):
    with pytest.raises((ValidationError, ValueError)):
        InvestigationInput.model_validate(payload(**{field:number}))


def test_real_hmem_reject_approve_restart_correct_and_source_revalidation(tmp_path):
    request = InvestigationInput.model_validate(payload()).request
    rows = [fact()]
    memory = HMemMemory(tmp_path, scope_id='qa-local', actor='qa-human')
    denied = memory.propose(request, 'Unapproved interpretation', rows, 'deny')
    assert memory.review(denied, approved_digest=denied['digest'], approve=False)['status'] == 'rejected'
    assert memory.recall(request, rows) == []
    proposal = memory.propose(request, 'Quarterly, not six month, revenue.', rows, 'first')
    with pytest.raises(MemoryError):
        memory.review(proposal, approved_digest='wrong', approve=True)
    initial = memory.review(proposal, approved_digest=proposal['digest'], approve=True)
    assert memory.review(proposal, approved_digest=proposal['digest'], approve=True) == initial
    restarted = HMemMemory(tmp_path, scope_id='qa-local', actor='qa-human')
    assert restarted.recall(request, rows)[0]['memory_id'] == initial['memory_id']
    correction = restarted.propose(request, 'Reviewed correction: GAAP quarterly revenue.', rows, 'second', initial['memory_id'])
    second = restarted.review(correction, approved_digest=correction['digest'], approve=True)
    recall = HMemMemory(tmp_path, scope_id='qa-local', actor='qa-human').recall(request, rows)
    assert len(recall) == 1 and recall[0]['memory_id'] == second['memory_id']
    assert recall[0]['supersedes'] == initial['memory_id']
    assert restarted.recall(request, [fact(value=101)]) == []
    assert restarted.recall(request, [fact(source_sha256='b'*64)]) == []
    assert HMemMemory(tmp_path, scope_id='other-local', actor='qa-human').recall(request, rows) == []
    assert restarted.feedback(request, second['memory_id'], 'helpful')['status'] == 'feedback_recorded'
