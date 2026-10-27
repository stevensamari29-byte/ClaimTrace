"""Explicit compact source selections use synthetic source data, never inference."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from unittest.mock import patch

import pytest

from backend.providers.nvidia_spans import (
    compact_tool_definitions, compact_context, canonical_proposal, available_native_tools, inline_local_schema,
    project_wire_constants,
)
from backend.investigation.model_contracts import tool_definitions, ModelProposalGate, TrustedDisclosure
from backend.models import InvestigationRequest
from backend.providers.nvidia import NvidiaClient
from backend.tests.test_nvidia_provider import TOKEN, MODEL, native, fixture_client


def context():
    text = 'Quarterly results. 🧾 GAAP diluted EPS was 2.29 USD/share.'
    start = text.index('GAAP')
    return {'claims': [], 'evidence': [], 'verified': {}, 'selected_checks': {}, 'tool_results': [],
        'disclosures': [{'id': 'sec-fixture', 'text': text,
        'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'quote_spans': [{'start': start, 'end': len(text), 'quote': text[start:]}],
        'period_start': '2026-04-01', 'period_end': '2026-06-30',
        'published_at': '2026-07-21'}]}


def compact(**changes):
    claim = {'id': 'eps', 'disclosure_id': 'sec-fixture', 'span_index': 0,
        'metric': 'diluted_eps', 'expected_value_decimal': '2.29',
        'unit': 'USD/shares', 'accounting_basis': 'GAAP'} | changes
    return {'tool': 'propose_claim_from_span', 'arguments': claim}


def test_explicit_native_schema_and_source_index_are_not_canonical_mutation():
    tools = tool_definitions(); original = deepcopy(tools)
    mapped = compact_tool_definitions(tools)
    assert tools == original
    assert 'propose_claim_from_span' in [t['function']['name'] for t in mapped]
    assert 'propose_extracted_claims' not in [t['function']['name'] for t in mapped]
    extraction = next(t['function']['parameters'] for t in mapped if t['function']['name'] == 'propose_claim_from_span')
    assert set(extraction['properties']) == {'id', 'disclosure_id', 'span_index', 'metric', 'expected_value_decimal', 'unit', 'accounting_basis'}
    assert 'claims' not in extraction['properties'] and '$defs' not in extraction
    assert [t for t in tools if t['function']['name'] != 'propose_extracted_claims'] == [t for t in mapped if t['function']['name'] != 'propose_claim_from_span']
    source = context(); advertised = compact_context(source)
    assert 'span_index' not in source['disclosures'][0]['quote_spans'][0]
    assert advertised['disclosures'][0]['quote_spans'][0]['span_index'] == 0
    assert advertised['disclosures'][0]['text'] == source['disclosures'][0]['text']
    with pytest.raises(ValueError):
        compact_tool_definitions(mapped)


def test_compact_expansion_binds_exact_unicode_quote_without_changing_model_value():
    source = context()
    result, converted = canonical_proposal(compact(expected_value_decimal='9.99'), source)
    assert converted and result['tool'] == 'propose_extracted_claims'
    claim = result['arguments']['claims'][0]
    disclosure = source['disclosures'][0]; span = disclosure['quote_spans'][0]
    assert claim['expected_value_decimal'] == '9.99'  # No financial-value repair.
    assert claim['text'] == span['quote'] and claim['quote_ref']['start'] == span['start']
    assert claim['quote_ref']['end'] == span['end']
    assert claim['quote_ref']['text_sha256'] == disclosure['text_sha256']
    assert claim['period_start'] == disclosure['period_start']
    assert claim['input_kind'] == 'model_extracted_proposal'
    request = InvestigationRequest.model_validate({'company': {'name': 'Fixture', 'ticker': 'ISRG', 'cik': '1035267'},
        'fiscal_year': 2026, 'period': 'Q2', 'as_of': '2026-10-25'})
    document = TrustedDisclosure(id=disclosure['id'], text=disclosure['text'],
        url='https://www.sec.gov/Archives/edgar/data/1035267/fixture.htm',
        period_start=date(2026, 4, 1), period_end=date(2026, 6, 30), published_at=date(2026, 7, 21))
    gate = ModelProposalGate(request, disclosures=[document])
    assert gate.validate(result['tool'], result['arguments']) is not None


@pytest.mark.parametrize('changes', [{'span_index': True}, {'span_index': -1}, {'span_index': 1},
    {'span_index': '0'}, {'disclosure_id': 'memory-id'}, {'start': 2}, {'text': 'repaired'},
    {'text_sha256': 'a'*64}, {'period_start': '2026-01-01'}, {'expected_value_decimal': float('nan')},
    {'expected_value_decimal': 2.29}, {'unit': 'BTC'}])
def test_compact_schema_rejects_ambiguous_or_scope_expanding_input(changes):
    with pytest.raises(ValueError):
        canonical_proposal(compact(**changes), context())


def test_source_integrity_and_duplicate_claims_fail_closed():
    for mutate in [lambda c: c['disclosures'][0].update(text='different'),
                   lambda c: c['disclosures'][0]['quote_spans'][0].update(quote='invented'),
                   lambda c: c['disclosures'][0]['quote_spans'][0].update(start=True),
                   lambda c: c['disclosures'].append(deepcopy(c['disclosures'][0]))]:
        source = context(); mutate(source)
        with pytest.raises(ValueError):
            canonical_proposal(compact(), source)
    proposal = compact(); proposal['arguments'] = {'claims': [proposal['arguments']]}
    with pytest.raises(ValueError):
        canonical_proposal(proposal, context())
    raw = {'tool': 'propose_extracted_claims', 'arguments': {'claims': []}}
    with pytest.raises(ValueError):
        canonical_proposal(raw, context())


def test_flat_compact_call_rejects_nested_wrapper_missing_and_extra_fields():
    for change in ('missing', 'extra', 'nested', 'two_claims'):
        proposal = compact()
        if change == 'missing':
            proposal['arguments'].pop('metric')
        elif change == 'extra':
            proposal['arguments']['period_start'] = '2026-01-01'
        elif change == 'nested':
            proposal['arguments'] = {'claims': [proposal['arguments']]}
        else:
            proposal['arguments'] = {'claims': [proposal['arguments'], deepcopy(proposal['arguments'])]}
        with pytest.raises(ValueError):
            canonical_proposal(proposal, context())


def test_actual_nvidia_wire_alias_expands_and_records_mapping_without_inference():
    payload = native()
    function = payload['choices'][0]['message']['tool_calls'][0]['function']
    function.update(name='propose_claim_from_span', arguments=json.dumps(compact()['arguments']))
    client, request, calls = fixture_client(payload)
    with patch.object(NvidiaClient, '_request', side_effect=request):
        result = client.structured(context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)
    body = calls[-1][1]
    assert body['chat_template_kwargs'] == {'enable_thinking': False}
    assert 'reasoning_budget' not in body
    assert json.loads(body['messages'][1]['content'])['disclosures'][0]['quote_spans'][0]['span_index'] == 0
    assert json.loads(result['proposal'])['tool'] == 'propose_extracted_claims'
    assert result['receipt']['native_tool'] == 'propose_claim_from_span'
    assert result['receipt']['source_binding'] == 'host_registered_span'
    assert result['receipt']['proposed_tool'] == 'propose_extracted_claims'


def _dispatcher(value='2.29'):
    from backend.tests.test_model_contracts import gate_data
    from backend.investigation.dispatcher import RestrictedDispatcher
    request, fact, disclosure, claim = gate_data(value)
    dispatcher = RestrictedDispatcher(request, disclosures=[disclosure], retriever=lambda *args: [fact])
    return dispatcher, claim


def _call(dispatcher, tool, **arguments):
    return dispatcher.dispatch(json.dumps({'tool': tool, 'arguments': arguments}))


def _available(context):
    return {tool['function']['name'] for tool in available_native_tools(tool_definitions(), context)}


def test_legal_native_actions_follow_host_prerequisites_without_selecting_values():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    assert _available(dispatcher.context()) == {'propose_claim_from_span'}
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    assert _available(dispatcher.context()) == {'select_evidence_checks', 'query_financial_evidence'}
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    assert _available(dispatcher.context()) == {'query_financial_evidence'}
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    assert _available(dispatcher.context()) == {'calculate_financial_claim', 'submit_investigation_conclusion'}
    _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='compare_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'submit_investigation_conclusion'}
    assert dispatcher.report()['conclusion'] is None  # No automatic model output.


def test_query_before_check_selection_and_single_non_supported_recheck_are_legal():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher('9.99')
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    assert _available(dispatcher.context()) == {'select_evidence_checks', 'calculate_financial_claim', 'request_additional_investigation'}
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    assert 'submit_investigation_conclusion' in _available(dispatcher.context())
    _call(dispatcher, 'request_additional_investigation', claim_id='c1', reason='contradicted_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'calculate_financial_claim', 'submit_investigation_conclusion'}


def test_missing_or_changed_host_state_cannot_advertise_a_conclusion():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    original = dispatcher.context()
    for key in ('claims', 'verified', 'selected_checks', 'tool_results', 'evidence'):
        changed = deepcopy(original); del changed[key]
        with pytest.raises(ValueError):
            _available(changed)
    changed = deepcopy(original); changed['tool_results'][-1].pop('host_challenge')
    assert 'submit_investigation_conclusion' not in _available(changed)
    changed = deepcopy(original); changed['tool_results'][-1]['host_challenge'][0]['classification'] = 'contradicted'
    assert 'submit_investigation_conclusion' not in _available(changed)
    changed = deepcopy(original); changed['selected_checks']['c1'] = []
    assert 'submit_investigation_conclusion' not in _available(changed)
    changed = deepcopy(original); changed['verified']['c1']['evidence_ids'] = ['unknown']
    with pytest.raises(ValueError):
        _available(changed)


def test_malformed_host_state_rejects_before_provider_network():
    client, request, calls = fixture_client()
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(Exception, match='nvidia_request_rejected'):
            client.structured({'tool_results': [{'state': 'submit_investigation_conclusion'}]},
                              tool_definitions(), MODEL, max_tokens=1536, timeout=5)
    assert calls == []


def test_single_non_supported_no_progress_calculation_requires_model_choice_to_recheck_or_conclude():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher('9.99')
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='compare_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'request_additional_investigation', 'submit_investigation_conclusion'}
    assert dispatcher.report()['conclusion'] is None
    _call(dispatcher, 'request_additional_investigation', claim_id='c1', reason='contradicted_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'calculate_financial_claim', 'submit_investigation_conclusion'}
    _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='compare_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'submit_investigation_conclusion'}
    assert dispatcher.report()['limits']['tool_calls'] == 8
    assert dispatcher.report()['limits']['timeout_seconds'] == 120


def test_later_check_selection_does_not_reset_single_claim_calculation_epoch():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='compare_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'select_evidence_checks'}
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    assert _available(dispatcher.context()) == {'submit_investigation_conclusion'}


def test_multiple_claim_calculation_availability_is_preserved_without_claim_specific_trace():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    second = deepcopy(claim); second['id'] = 'second-eps'
    _call(dispatcher, 'propose_extracted_claims', claims=[claim, second])
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1', 'second-eps'], checks=list(ALL_CHECKS))
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='compare_value', evidence_ids=['eps'])
    assert _available(dispatcher.context()) == {'calculate_financial_claim', 'submit_investigation_conclusion'}


def _schemas(context):
    return {tool['function']['name']: tool['function']['parameters']
            for tool in available_native_tools(tool_definitions(), context)}


def test_single_claim_wire_operations_and_reference_ids_are_host_owned():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    before_query = _schemas(dispatcher.context())
    assert before_query['select_evidence_checks']['properties']['claim_ids']['items']['enum'] == ['c1']
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    context_before = dispatcher.context(); original = deepcopy(context_before)
    host_tools = tool_definitions(); host_original = deepcopy(host_tools)
    tools = available_native_tools(host_tools, context_before)
    schemas = {tool['function']['name']: tool['function']['parameters'] for tool in tools}
    calculate = schemas['calculate_financial_claim']['properties']
    assert calculate['claim_id']['enum'] == ['c1'] and 'const' not in calculate['claim_id']
    assert 'const' not in calculate['operation'] and calculate['operation']['enum'] == ['compare_value']
    assert calculate['evidence_ids']['items']['enum'] == ['eps']
    assert 'const' not in calculate['evidence_ids'] and calculate['evidence_ids']['minItems'] == 1
    conclusion = schemas['submit_investigation_conclusion']['properties']['findings']['items']['properties']
    assert conclusion['claim_id']['enum'] == ['c1']
    assert conclusion['evidence_ids']['items']['enum'] == ['eps']
    assert 'const' not in conclusion['classification']  # The model still proposes a verdict.
    assert context_before == original and host_tools == host_original
    assert context_before['claims'][0]['expected_value_decimal'] == claim['expected_value_decimal']


def test_single_margin_operation_and_empty_citations_are_not_substituted():
    dispatcher, claim = _dispatcher('99')
    claim.update(metric='net_margin', unit='%')
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'query_financial_evidence', metrics=['revenue', 'net_income'])
    fields = _schemas(dispatcher.context())['calculate_financial_claim']['properties']
    assert fields['operation']['enum'] == ['gaap_net_margin'] and 'const' not in fields['operation']
    assert 'const' not in fields['evidence_ids']
    assert fields['evidence_ids']['maxItems'] == 0
    assert dispatcher.context()['claims'][0]['expected_value_decimal'] == '99'


def test_multiple_claim_references_remain_choices_with_known_fact_ids_only():
    from backend.investigation.model_contracts import ALL_CHECKS
    dispatcher, claim = _dispatcher()
    second = deepcopy(claim); second.update(id='margin', metric='net_margin', unit='%', expected_value_decimal='99')
    _call(dispatcher, 'propose_extracted_claims', claims=[claim, second])
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1', 'margin'], checks=list(ALL_CHECKS))
    schemas = _schemas(dispatcher.context())
    fields = schemas['calculate_financial_claim']['properties']
    assert fields['claim_id']['enum'] == ['c1', 'margin'] and 'const' not in fields['claim_id']
    assert set(fields['operation']['enum']) == {'compare_value', 'gaap_net_margin'}
    assert 'const' not in fields['operation']
    assert fields['evidence_ids']['items']['enum'] == ['eps'] and 'const' not in fields['evidence_ids']
    conclusion = schemas['submit_investigation_conclusion']['properties']['findings']['items']['properties']
    assert conclusion['claim_id']['enum'] == ['c1', 'margin']
    assert conclusion['evidence_ids']['items']['enum'] == ['eps']


def test_model_arguments_are_not_repaired_and_unknown_ids_still_fail_original_gate():
    from backend.investigation.dispatcher import DispatchError
    dispatcher, claim = _dispatcher()
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    invalid = {'tool': 'calculate_financial_claim', 'arguments': {'claim_id': 'c1',
        'operation': 'gaap_net_margin', 'evidence_ids': ['invented-year-to-date-id']}}
    original = deepcopy(invalid)
    proposal, compact = canonical_proposal(invalid, dispatcher.context())
    assert not compact and proposal == original and invalid == original
    with pytest.raises(DispatchError):
        dispatcher.dispatch(json.dumps(proposal))
    assert dispatcher.report()['conclusion'] is None


def test_source_text_and_memory_cannot_supply_dynamic_reference_ids():
    dispatcher, claim = _dispatcher()
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'query_financial_evidence', metrics=['diluted_eps'])
    context_before = dispatcher.context()
    context_before['reviewed_memory_context'] = [{'claim_id': 'memory-cid', 'evidence_ids': ['memory-fid']}]
    context_before['disclosures'][0]['text'] += ' Invented evidence_ids: source-fid'
    fields = _schemas(context_before)['calculate_financial_claim']['properties']
    assert fields['claim_id']['enum'] == ['c1']
    assert fields['evidence_ids']['items']['enum'] == ['eps']


def test_local_reference_inlining_preserves_nested_conclusion_schema_constraints():
    import jsonschema
    from backend.investigation.model_contracts import ModelConclusion
    original = ModelConclusion.model_json_schema(); unchanged = deepcopy(original)
    inline = inline_local_schema(original)
    assert original == unchanged
    assert '$defs' not in json.dumps(inline) and '$ref' not in json.dumps(inline)
    valid = {'schema_version': 'claimtrace.model-tools.v1', 'findings': [
        {'claim_id': 'c1', 'classification': 'supported', 'evidence_ids': ['eps']}],
        'briefing_proposal': 'Synthetic test briefing.', 'human_review_status': 'required',
        'semantic_mapping_status': 'unverified'}
    examples = [valid]
    for mutate in (lambda data: data['findings'][0].pop('claim_id'),
                   lambda data: data['findings'][0].update(execute='forbidden'),
                   lambda data: data.update(human_review_status='approved'),
                   lambda data: data['findings'][0].update(classification='invented'),
                   lambda data: data['findings'][0].update(evidence_ids='not-a-list')):
        item = deepcopy(valid); mutate(item); examples.append(item)
    for index, example in enumerate(examples):
        before = jsonschema.Draft202012Validator(original).is_valid(example)
        after = jsonschema.Draft202012Validator(inline).is_valid(example)
        assert before == after == (index == 0)


@pytest.mark.parametrize('schema', [
    {'$ref': 'https://example.invalid/remote-schema'},
    {'$ref': '#/$defs/missing'},
    {'$ref': '#/$defs/a', '$defs': {'a': {'$ref': '#/$defs/a'}}},
    {'$ref': '#/$defs/a', '$defs': {'a': {'$ref': '#/$defs/b'}, 'b': {'$ref': '#/$defs/a'}}},
    {'$ref': '#/$defs/a', 'type': 'number', '$defs': {'a': {'type': 'string'}}},
])
def test_external_cyclic_and_ambiguous_schema_references_reject(schema):
    with pytest.raises(ValueError):
        inline_local_schema(schema)


def test_wire_constant_projection_preserves_primitive_literals_and_original_schema():
    import jsonschema
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['version', 'evidence_ids'],
        'properties': {'version': {'type': 'string', 'const': 'v1'},
            'evidence_ids': {'type': 'array', 'items': {'type': 'string', 'enum': ['a', 'b']},
                             'minItems': 2, 'maxItems': 2, 'const': ['a', 'b']}}}
    original = deepcopy(schema); projected = project_wire_constants(schema)
    assert schema == original and '"const":' not in json.dumps(projected)
    assert projected['required'] == original['required'] and projected['additionalProperties'] is False
    assert projected['properties']['version'] == {'type': 'string', 'enum': ['v1']}
    array = projected['properties']['evidence_ids']
    assert array == {key: value for key, value in original['properties']['evidence_ids'].items() if key != 'const'}
    jsonschema.validate({'version': 'v1', 'evidence_ids': ['a', 'a']}, projected)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({'version': 'v2', 'evidence_ids': ['a', 'b']}, projected)
    for primitive in ('literal', 0, True, None):
        before = {'const': primitive}; after = project_wire_constants(before)
        for candidate in ('literal', 'other', 0, 1, True, False, None):
            assert jsonschema.Draft202012Validator(before).is_valid(candidate) == jsonschema.Draft202012Validator(after).is_valid(candidate)
    with pytest.raises(ValueError):
        project_wire_constants({'$ref': 'https://example.invalid/schema'})


def _margin_dispatcher():
    from backend.tests.test_model_contracts import gate_data
    from backend.investigation.model_contracts import ALL_CHECKS
    from backend.investigation.dispatcher import RestrictedDispatcher
    request, fact, old_disclosure, claim = gate_data('20')
    text = 'Synthetic GAAP net margin was 20 percent.'
    disclosure = TrustedDisclosure(old_disclosure.id, text, old_disclosure.url,
        old_disclosure.published_at, old_disclosure.period_start, old_disclosure.period_end)
    claim.update(text=text, metric='net_margin', unit='%', quote_ref={
        'disclosure_id': disclosure.id, 'text_sha256': disclosure.text_sha256,
        'normalization': 'unicode-codepoints-exact-v1', 'start': 0, 'end': len(text), 'quote': text})
    facts = [fact | {'id': 'rev', 'unit': 'USD', 'concept': 'Revenues', 'value': 100},
             fact | {'id': 'income', 'unit': 'USD', 'concept': 'NetIncomeLoss', 'value': 20}]
    dispatcher = RestrictedDispatcher(request, disclosures=[disclosure], retriever=lambda *args: deepcopy(facts))
    _call(dispatcher, 'propose_extracted_claims', claims=[claim])
    _call(dispatcher, 'select_evidence_checks', claim_ids=['c1'], checks=list(ALL_CHECKS))
    _call(dispatcher, 'query_financial_evidence', metrics=['revenue', 'net_income'])
    return dispatcher


def test_const_free_wire_can_advertise_duplicates_but_original_gate_still_rejects():
    import jsonschema
    from backend.investigation.dispatcher import DispatchError
    dispatcher = _margin_dispatcher()
    schema = _schemas(dispatcher.context())['calculate_financial_claim']
    duplicate = {'claim_id': 'c1', 'operation': 'gaap_net_margin', 'evidence_ids': ['rev', 'rev']}
    assert '"const":' not in json.dumps(schema)
    jsonschema.validate(duplicate, schema)  # Explicitly weaker wire advertisement only.
    with pytest.raises(DispatchError):
        _call(dispatcher, 'calculate_financial_claim', **duplicate)
    assert dispatcher.report()['conclusion'] is None


@pytest.mark.parametrize('ids', [['rev'], ['rev', 'unknown']])
def test_original_gate_independently_rejects_omitted_and_unknown_financial_evidence(ids):
    from backend.investigation.dispatcher import DispatchError
    dispatcher = _margin_dispatcher()
    with pytest.raises(DispatchError):
        _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='gaap_net_margin', evidence_ids=ids)
    assert dispatcher.report()['conclusion'] is None


def test_reordered_comparable_financial_evidence_remains_correctly_verified_by_host():
    dispatcher = _margin_dispatcher()
    result = _call(dispatcher, 'calculate_financial_claim', claim_id='c1', operation='gaap_net_margin', evidence_ids=['income', 'rev'])
    assert result['result']['host_finding']['classification'] == 'supported'
    assert dispatcher.report()['calculations'][-1]['actual_decimal'] == '20.0'
