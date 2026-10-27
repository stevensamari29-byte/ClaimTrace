"""Synthetic rejection fixtures; these are not recovered live model proposals."""
import json

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from backend.investigation.dispatcher import DispatchError, RestrictedDispatcher
from backend.investigation.proposal_diagnostics import rejection_diagnostic
from backend.tests.test_model_contracts import gate_data


SECRET = 'private-test-sentinel-never-project-into-diagnostics'


def reject(tool, arguments, *, disclosure=None):
    request, _, doc, _ = gate_data()
    effects = []
    dispatcher = RestrictedDispatcher(request, disclosures=[disclosure or doc],
        retriever=lambda *args: effects.append(args))
    with pytest.raises(DispatchError, match='proposal_rejected'):
        dispatcher.dispatch(json.dumps({'tool': tool, 'arguments': arguments}))
    report = dispatcher.report()
    assert report['status'] == 'blocked'
    assert report['conclusion'] is None
    assert report['human_review_status'] == 'required'
    assert report['tool_calls'] == 1
    assert report['limits']['automatic_retries'] == 0
    assert report['trace'] == []
    assert not effects
    with pytest.raises(DispatchError, match='proposal_rejected'):
        dispatcher.dispatch(json.dumps({'tool': 'query_financial_evidence',
                                        'arguments': {'metrics': ['diluted_eps']}}))
    assert dispatcher.report()['tool_calls'] == 1
    assert not effects
    return dispatcher, report


@pytest.mark.parametrize('arguments,path,kind', [
    ({'metrics': 'diluted_eps'}, ['metrics'], 'list_type'),
    ({'metrics': [SECRET]}, ['metrics', '*'], 'literal_error'),
    ({'metrics': ['diluted_eps'], SECRET: SECRET}, ['unknown_field'], 'extra_forbidden'),
    ({}, ['metrics'], 'missing'),
])
def test_schema_diagnostics_never_copy_values_or_injected_keys(arguments, path, kind):
    dispatcher, report = reject('query_financial_evidence', arguments)
    diagnostic = report['rejection_diagnostic']
    assert diagnostic == {'tool': 'query_financial_evidence', 'phase': 'schema',
        'rule': 'canonical_schema_invalid', 'schema_issues': [{'path': path, 'type': kind}]}
    assert SECRET not in json.dumps(diagnostic)
    diagnostic['schema_issues'][0]['path'].append(SECRET)
    assert SECRET not in json.dumps(dispatcher.report()['rejection_diagnostic'])


def test_unknown_tool_name_is_not_exposed():
    _, report = reject(SECRET, {'command': SECRET})
    assert report['rejection_diagnostic'] == {'tool': 'unknown', 'phase': 'gate',
        'rule': 'tool_not_permitted', 'schema_issues': []}


@pytest.mark.parametrize('patch', [
    {'quote_ref': {'text_sha256': '0' * 64}},
    {'quote_ref': {'start': 1}},
    {'quote_ref': {'quote': SECRET}},
    {'period_start': '2026-01-01'},
])
def test_source_binding_rejections_remain_terminal(patch):
    _, _, _, claim = gate_data()
    if 'quote_ref' in patch:
        claim['quote_ref'].update(patch['quote_ref'])
    else:
        claim.update(patch)
    _, report = reject('propose_extracted_claims', {'claims': [claim]})
    assert report['rejection_diagnostic']['rule'] == 'source_binding_invalid'
    assert SECRET not in json.dumps(report['rejection_diagnostic'])


def test_premature_conclusion_explains_prerequisite_without_accepting_it():
    _, report = reject('submit_investigation_conclusion', {
        'schema_version': 'claimtrace.model-tools.v1',
        'findings': [{'claim_id': 'unknown', 'classification': 'supported', 'evidence_ids': []}],
        'briefing_proposal': SECRET, 'human_review_status': 'required',
        'semantic_mapping_status': 'unverified'})
    assert report['rejection_diagnostic']['rule'] == 'conclusion_prerequisite_unsatisfied'
    assert SECRET not in json.dumps(report['rejection_diagnostic'])


@pytest.mark.parametrize('tool,arguments,rule', [
    ('select_evidence_checks', {'claim_ids': ['unknown'], 'checks': ['units']}, 'unknown_or_duplicate_claim'),
    ('calculate_financial_claim', {'claim_id': 'unknown', 'operation': 'compare_value',
                                 'evidence_ids': [SECRET]}, 'unknown_or_duplicate_claim'),
])
def test_unknown_references_remain_rejected(tool, arguments, rule):
    _, report = reject(tool, arguments)
    assert report['rejection_diagnostic']['rule'] == rule
    assert SECRET not in json.dumps(report['rejection_diagnostic'])


def test_unknown_error_text_and_types_are_never_exposed():
    class HostileValueError(ValueError):
        pass
    for error in (ValueError(SECRET), HostileValueError('Tool is not permitted'), RuntimeError(SECRET)):
        diagnostic = rejection_diagnostic(SECRET, error, validation_phase=True)
        assert diagnostic['rule'] == 'unclassified_rejection'
        assert SECRET not in json.dumps(diagnostic)
    error = ValidationError.from_exception_data('private title', [{
        'type': PydanticCustomError(SECRET, SECRET), 'loc': (SECRET, 4), 'input': SECRET}])
    diagnostic = rejection_diagnostic('query_financial_evidence', error, validation_phase=True)
    assert diagnostic['schema_issues'] == [{'path': ['unknown_field', '*'], 'type': 'other'}]
    assert SECRET not in json.dumps(diagnostic)


def test_diagnostic_count_and_paths_are_bounded():
    error = ValidationError.from_exception_data('private title', [{
        'type': 'missing', 'loc': ('claims',) * 12, 'input': SECRET} for _ in range(20)])
    diagnostic = rejection_diagnostic('propose_extracted_claims', error, validation_phase=True)
    assert len(diagnostic['schema_issues']) == 8
    assert all(len(issue['path']) == 8 for issue in diagnostic['schema_issues'])
    assert SECRET not in json.dumps(diagnostic)


def test_execution_errors_are_not_mislabelled_as_gate_rules():
    diagnostic = rejection_diagnostic('query_financial_evidence',
        ValueError('Tool is not permitted'), validation_phase=False)
    assert diagnostic['phase'] == 'execution'
    assert diagnostic['rule'] == 'unclassified_rejection'


def test_success_reports_stay_unchanged_and_malformed_envelopes_fail_closed():
    request, _, doc, claim = gate_data()
    dispatcher = RestrictedDispatcher(request, disclosures=[doc])
    dispatcher.dispatch(json.dumps({'tool': 'propose_extracted_claims', 'arguments': {'claims': [claim]}}))
    assert 'rejection_diagnostic' not in dispatcher.report()
    request, *_ = gate_data()
    dispatcher = RestrictedDispatcher(request)
    with pytest.raises(DispatchError, match='invalid_proposal'):
        dispatcher.dispatch('{"tool":"a","tool":"b","arguments":{}}')
    assert dispatcher.report()['error_code'] == 'invalid_proposal'
    assert 'rejection_diagnostic' not in dispatcher.report()
