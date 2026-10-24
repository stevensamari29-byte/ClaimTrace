"""Contract/gate fixtures, not live inference acceptance."""
from datetime import date
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.investigation.model_contracts import (ALL_CHECKS, ModelConclusion,
    ModelProposalGate, TrustedDisclosure, tool_definitions)


def gate_data(value='2.29', **changes):
    request = {'company': {'name': 'Intuitive Surgical', 'ticker': 'ISRG', 'cik': '1035267'},
               'fiscal_year': 2026, 'period': 'Q2', 'as_of': '2026-10-24', 'evidence_backend': 'zetaris'}
    fact = {'id': 'eps', 'document': '10-Q', 'url': 'https://www.sec.gov/Archives/edgar/data/1035267/f.htm',
            'published_at': '2026-07-21', 'period_start': '2026-04-01', 'period_end': '2026-06-30',
            'unit': 'USD/shares', 'value': 2.29, 'concept': 'EarningsPerShareDiluted',
            'locator': 'us-gaap/EarningsPerShareDiluted', 'source_mode': 'live_zetaris'}
    text = '🧾 Diluted EPS was 2.29.'
    disclosure = TrustedDisclosure('filing', text, fact['url'], date(2026,7,21), date(2026,4,1), date(2026,6,30))
    claim = {'id': 'c1', 'text': text, 'metric': 'diluted_eps', 'expected_value_decimal': value,
             'unit': 'USD/shares', 'accounting_basis': 'GAAP', 'period_start': '2026-04-01',
             'period_end': '2026-06-30', 'input_kind': 'model_extracted_proposal',
             'quote_ref': {'disclosure_id': 'filing', 'text_sha256': disclosure.text_sha256,
                           'normalization': 'unicode-codepoints-exact-v1', 'start': 0, 'end': len(text), 'quote': text}}
    return request, fact | changes, disclosure, claim


def prepared(value='2.29', facts=None):
    request, fact, disclosure, claim = gate_data(value)
    gate = ModelProposalGate(request, [fact] if facts is None else facts, [disclosure])
    gate.validate('propose_extracted_claims', {'claims': [claim]})
    return gate


def calculate(gate, ids=None):
    return gate.validate('calculate_financial_claim', {'claim_id': 'c1', 'operation': 'compare_value', 'evidence_ids': ['eps'] if ids is None else ids})


def test_schema_files_match_actual_models():
    root = Path(__file__).resolve().parents[2]
    assert json.loads((root / 'shared/model-tools.json').read_text()) == tool_definitions()
    assert json.loads((root / 'shared/model-output.schema.json').read_text()) == ModelConclusion.model_json_schema()
    for tool in tool_definitions():
        assert tool['function']['strict'] is True
        schema = tool['function']['parameters']
        assert schema['additionalProperties'] is False
        assert set(schema['required']) == set(schema['properties'])


@pytest.mark.parametrize('extra', [{'sql': 'SELECT * FROM anything'}, {'company': {'cik':'1'}}, {'command': 'whoami'}, {'url':'https://evil.invalid'}])
def test_query_rejects_sql_commands_and_scope_overrides(extra):
    with pytest.raises(ValidationError):
        prepared().validate('query_financial_evidence', {'metrics':['revenue']} | extra)


@pytest.mark.parametrize('field,value', [('input_kind','human_assertion'), ('expected_value_decimal',2.29), ('expected_value_decimal','1e999'), ('expected_value_decimal','0e-1000000'), ('period_end','not-a-date')])
def test_extraction_strict_and_bounded(field, value):
    request, fact, doc, claim = gate_data()
    claim[field] = value
    with pytest.raises((ValueError, ValidationError)):
        ModelProposalGate(request,[fact],[doc]).validate('propose_extracted_claims', {'claims':[claim]})


@pytest.mark.parametrize('patch', [{'end': 999}, {'quote':'fabricated'}, {'text_sha256':'0'*64}, {'disclosure_id':'unknown'}])
def test_exact_quote_provenance(patch):
    request,fact,doc,claim = gate_data()
    claim['quote_ref'].update(patch)
    with pytest.raises(ValueError):
        ModelProposalGate(request,[fact],[doc]).validate('propose_extracted_claims', {'claims':[claim]})


def test_unicode_codepoint_quote_and_real_host_verification():
    result = calculate(prepared())
    assert result['host_finding']['classification'] == 'supported'
    assert result['calculations'][0]['actual_decimal'] == '2.29'


def test_no_evidence_can_conclude_incomplete():
    gate = prepared(facts=[])
    assert calculate(gate,[])['host_finding']['classification'] == 'incomplete'
    gate.validate('select_evidence_checks', {'claim_ids':['c1'], 'checks':list(ALL_CHECKS)})
    gate.record_completed_challenge()
    result = gate.validate('submit_investigation_conclusion', {'schema_version':'claimtrace.model-tools.v1',
        'findings':[{'claim_id':'c1','classification':'incomplete','evidence_ids':[]}],
        'briefing_proposal':'No eligible EPS evidence; human review required.', 'human_review_status':'required', 'semantic_mapping_status':'unverified'})
    assert result['human_review_status'] == 'required'


def test_conflicting_fact_cannot_be_omitted():
    _,fact,_,_ = gate_data()
    gate = prepared(facts=[fact, fact | {'id':'contrary','value':3.0}])
    with pytest.raises(ValueError,match='all comparable'):
        calculate(gate)


@pytest.mark.parametrize('patch', [{'published_at':'2026-11-01'}, {'url':'https://www.sec.gov/Archives/edgar/data/1/f.htm'}])
def test_future_or_crossissuer_fact_rejected(patch):
    request,fact,doc,_ = gate_data()
    with pytest.raises(ValueError):
        ModelProposalGate(request,[fact | patch],[doc])


def test_forged_verdict_and_human_approval_rejected():
    gate = prepared('99')
    calculate(gate)
    gate.validate('select_evidence_checks', {'claim_ids':['c1'], 'checks':list(ALL_CHECKS)})
    gate.record_completed_challenge()
    conclusion = {'schema_version':'claimtrace.model-tools.v1', 'findings':[{'claim_id':'c1','classification':'supported','evidence_ids':['eps']}],
                  'briefing_proposal':'Untrusted model prose', 'human_review_status':'required', 'semantic_mapping_status':'unverified'}
    with pytest.raises(ValueError, match='forge'):
        gate.validate('submit_investigation_conclusion',conclusion)
    with pytest.raises(ValidationError):
        gate.validate('submit_investigation_conclusion',conclusion | {'human_review_status':'approved'})


def test_recheck_only_once_and_supported_cannot_trigger():
    gate = prepared('99')
    calculate(gate)
    args = {'claim_id':'c1','reason':'contradicted_value','evidence_ids':['eps']}
    gate.validate('request_additional_investigation',args)
    with pytest.raises(ValueError,match='One recheck'):
        gate.validate('request_additional_investigation',args)
    gate = prepared()
    calculate(gate)
    with pytest.raises(ValueError):
        gate.validate('request_additional_investigation',args)


def test_tool_and_wallclock_bounds_and_defensive_scope():
    request,_,_,_ = gate_data()
    now=[0.0]
    gate = ModelProposalGate(request, clock=lambda:now[0])
    changed = gate.scope
    changed['company']['cik']='1'
    assert gate.scope['company']['cik']=='1035267'
    for _ in range(8):
        gate.validate('query_financial_evidence',{'metrics':['revenue']})
    with pytest.raises(ValueError,match='budget'):
        gate.validate('query_financial_evidence',{'metrics':['revenue']})
    gate = ModelProposalGate(request,clock=lambda:now[0])
    now[0]=120.0
    with pytest.raises(ValueError,match='budget'):
        gate.validate('query_financial_evidence',{'metrics':['revenue']})
