"""Independent adversarial model proposals: fixtures, never inference receipts."""
from datetime import date

import jsonschema
import pytest

from backend.investigation.model_contracts import (
    ALL_CHECKS, ModelProposalGate, TrustedDisclosure, tool_definitions,
)


URL = 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm'
TEXT = '😀 Revenue was 100 USD for the quarter.'


def request():
    return dict(company=dict(name='Fixture issuer', ticker='ISRG', cik='1035267'),
                fiscal_year=2026, period='Q2', as_of='2026-07-21', evidence_backend='zetaris')


def disclosure(**changes):
    return TrustedDisclosure(**(dict(id='disclosure', text=TEXT, url=URL,
        published_at=date(2026, 7, 21), period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30)) | changes))


def fact(**changes):
    return dict(id='revenue', document='Fixture SEC 10-Q', url=URL,
        published_at='2026-07-21', period_start='2026-04-01', period_end='2026-06-30',
        unit='USD', value=100, concept='Revenues', locator='fixture revenue table',
        source_mode='live_zetaris', source_sha256='a'*64) | changes


def extracted(**changes):
    doc = disclosure()
    return dict(id='claim', text='Revenue was 100 USD for the quarter.', metric='revenue',
        expected_value_decimal='100', unit='USD', accounting_basis='GAAP',
        period_start='2026-04-01', period_end='2026-06-30', input_kind='model_extracted_proposal',
        quote_ref=dict(disclosure_id='disclosure', text_sha256=doc.text_sha256,
            normalization='unicode-codepoints-exact-v1', start=2, end=len(TEXT), quote=TEXT[2:])) | changes


def make_gate(rows=None, **kwargs):
    return ModelProposalGate(request(), evidence=[fact()] if rows is None else rows,
                             disclosures=[disclosure()], **kwargs)


def register(gate, **changes):
    gate.validate('propose_extracted_claims', {'claims':[extracted(**changes)]})


def calculate(gate, evidence_ids=None):
    return gate.validate('calculate_financial_claim', dict(claim_id='claim',
        operation='compare_value', evidence_ids=['revenue'] if evidence_ids is None else evidence_ids))


def conclusion(classification='supported', evidence_ids=None):
    return dict(schema_version='claimtrace.model-tools.v1', findings=[dict(claim_id='claim',
        classification=classification, evidence_ids=['revenue'] if evidence_ids is None else evidence_ids)],
        briefing_proposal='Untrusted model prose proposal for required human review.',
        semantic_mapping_status='unverified', human_review_status='required')


def finish_challenge(gate):
    gate.validate('select_evidence_checks', {'claim_ids':['claim'], 'checks':list(ALL_CHECKS)})
    gate.record_completed_challenge()


def test_permitted_schema_definitions_validate_actual_examples():
    definitions = {d['function']['name']: d['function']['parameters'] for d in tool_definitions()}
    examples = {
        'propose_extracted_claims': {'claims':[extracted()]},
        'select_evidence_checks': {'claim_ids':['claim'], 'checks':list(ALL_CHECKS)},
        'query_financial_evidence': {'metrics':['revenue']},
        'calculate_financial_claim': {'claim_id':'claim', 'operation':'compare_value', 'evidence_ids':['revenue']},
        'request_additional_investigation': {'claim_id':'claim', 'reason':'contradicted_value', 'evidence_ids':['revenue']},
        'submit_investigation_conclusion': conclusion(),
    }
    assert set(definitions) == set(examples)
    for name, example in examples.items():
        jsonschema.Draft202012Validator.check_schema(definitions[name])
        jsonschema.validate(example, definitions[name])
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(example | {'execute':'arbitrary command'}, definitions[name])


@pytest.mark.parametrize('changes', [dict(sql='SELECT * FROM private'), dict(command='whoami'),
    dict(cik='320193'), dict(as_of='2099-01-01'), dict(table='private'),
    dict(max_tool_calls=999), dict(human_review_status='approved')])
def test_retrieval_proposal_cannot_override_host_scope_or_execute(changes):
    with pytest.raises(ValueError):
        make_gate().validate('query_financial_evidence', {'metrics':['revenue']} | changes)


def test_unknown_tools_and_scope_mutation_are_rejected_or_isolated():
    gate = make_gate()
    with pytest.raises(ValueError):
        gate.validate('run_sql', {'sql':'SELECT 1'})
    copy = gate.scope
    copy['company']['cik'] = '320193'
    assert gate.scope['company']['cik'] == '1035267'


@pytest.mark.parametrize('change', [dict(quote='Revenue was 999 USD.'), dict(start=3),
    dict(text_sha256='b'*64), dict(disclosure_id='fabricated'),
    dict(normalization='utf16'), dict(end=12000)])
def test_exact_unicode_source_quotes_cannot_be_fabricated(change):
    claim = extracted()
    claim['quote_ref'].update(change)
    with pytest.raises(ValueError):
        make_gate().validate('propose_extracted_claims', {'claims':[claim]})


def test_real_unicode_codepoint_offsets_are_accepted():
    gate = make_gate()
    register(gate)
    assert calculate(gate)['host_finding']['classification'] == 'supported'


@pytest.mark.parametrize('url', ['https://evil.invalid/?source='+URL,
    URL.replace('www.sec.gov','www.sec.gov.evil.invalid'),
    URL.replace('1035267','320193'), 'https://user:password@www.sec.gov/Archives/edgar/data/1035267/x.htm'])
def test_registered_disclosure_source_origin_and_issuer_are_enforced(url):
    with pytest.raises(ValueError):
        ModelProposalGate(request(), disclosures=[disclosure(url=url)])


@pytest.mark.parametrize('changes', [dict(published_at='2026-07-22'),
    dict(url=URL.replace('1035267','320193')),
    dict(url=URL.replace('1035267','320193')+'?claimed=/edgar/data/1035267/'), dict(locator='')])
def test_future_foreign_unlocated_financial_sources_rejected(changes):
    with pytest.raises(ValueError):
        make_gate(rows=[fact(**changes)])


@pytest.mark.parametrize('changes', [dict(unit='USD/shares'), dict(accounting_basis='non-GAAP'),
    dict(accounting_basis='unknown'), dict(metric='unsupported', expected_value_decimal=None)])
def test_ineligible_claims_can_conclude_only_incomplete_or_unresolved(changes):
    gate = make_gate()
    register(gate, **changes)
    finding = calculate(gate, [])['host_finding']
    assert finding['classification'] in {'incomplete','unresolved'}
    finish_challenge(gate)
    gate.validate('submit_investigation_conclusion', conclusion(finding['classification'], []))


def test_wrong_claim_period_cannot_be_attached_to_quote():
    with pytest.raises(ValueError):
        register(make_gate(), period_start='2026-01-01')


def test_contrary_evidence_cannot_be_omitted_to_forge_supported_verdict():
    gate = make_gate(rows=[fact(), fact(id='contrary', value=200)])
    register(gate)
    with pytest.raises(ValueError):
        calculate(gate)
    result = calculate(gate, ['revenue','contrary'])
    assert result['host_finding']['classification'] == 'unresolved'
    finish_challenge(gate)
    with pytest.raises(ValueError):
        gate.validate('submit_investigation_conclusion', conclusion())


def test_no_conclusion_before_host_challenge_and_no_model_human_approval():
    gate = make_gate()
    register(gate)
    calculate(gate)
    with pytest.raises(ValueError):
        gate.validate('submit_investigation_conclusion', conclusion())
    finish_challenge(gate)
    with pytest.raises(ValueError):
        gate.validate('submit_investigation_conclusion', conclusion() | {'human_review_status':'approved'})
    with pytest.raises(ValueError):
        gate.validate('submit_investigation_conclusion', conclusion(evidence_ids=['fabricated']))
    gate.validate('submit_investigation_conclusion', conclusion())


def test_missing_evidence_supports_an_honest_incomplete_stop():
    gate = make_gate(rows=[])
    register(gate)
    assert calculate(gate, [])['host_finding']['classification'] == 'incomplete'
    finish_challenge(gate)
    gate.validate('submit_investigation_conclusion', conclusion('incomplete', []))


def test_exact_quote_does_not_establish_semantic_metric_mapping():
    # Deliberately incorrect extraction: the literal quote is about revenue,
    # but proposed metric/number refers to EPS. Arithmetic is possible against
    # an EPS fixture; that must not establish that extraction was faithful.
    gate = make_gate(rows=[fact(id='eps', concept='EarningsPerShareDiluted',
                                unit='USD/shares', value=2.29)])
    register(gate, metric='diluted_eps', unit='USD/shares', expected_value_decimal='2.29')
    result = calculate(gate, ['eps'])
    assert result['host_finding']['classification'] == 'supported'
    assert result['semantic_mapping_status'] == 'unverified'
    assert result['human_review_status'] == 'required'
    finish_challenge(gate)
    proposed = conclusion(evidence_ids=['eps'])
    with pytest.raises(ValueError):
        gate.validate('submit_investigation_conclusion', proposed | {'semantic_mapping_status':'verified'})
    accepted = gate.validate('submit_investigation_conclusion', proposed)
    assert accepted['semantic_mapping_status'] == 'unverified'


def test_single_recheck_and_shared_attempt_budget_are_enforced():
    gate = make_gate()
    register(gate, expected_value_decimal='101')
    calculate(gate)
    proposal = dict(claim_id='claim', reason='contradicted_value', evidence_ids=['revenue'])
    gate.validate('request_additional_investigation', proposal)
    with pytest.raises(ValueError):
        gate.validate('request_additional_investigation', proposal)
    bounded = make_gate()
    for _ in range(8):
        with pytest.raises(ValueError):
            bounded.validate('arbitrary', {})
    with pytest.raises(ValueError, match='budget'):
        bounded.validate('query_financial_evidence', {'metrics':['revenue']})


def test_deadline_expires_at_shared_wall_bound():
    now = [0.0]
    gate = make_gate(clock=lambda:now[0])
    now[0] = 120
    with pytest.raises(ValueError, match='budget'):
        gate.validate('query_financial_evidence', {'metrics':['revenue']})
