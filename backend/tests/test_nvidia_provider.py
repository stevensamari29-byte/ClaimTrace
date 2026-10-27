"""NVIDIA protocol fixtures only. No credential, model or service calls."""
import io
import json
import time
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from backend.providers import nvidia
from backend.providers.nvidia import NvidiaClient, NvidiaStructuredProvider, NvidiaError
from backend.investigation.model_contracts import tool_definitions
from backend.investigation.nvidia_run import main

TOKEN = 'private-fixture-nvidia-token'
MODEL = 'nvidia/nemotron-fixture'


def query_context():
    from backend.tests.test_model_contracts import gate_data
    from backend.investigation.dispatcher import RestrictedDispatcher
    request, fact, disclosure, claim = gate_data()
    dispatcher = RestrictedDispatcher(request, disclosures=[disclosure], retriever=lambda *args: [fact])
    dispatcher.dispatch(json.dumps({'tool': 'propose_extracted_claims', 'arguments': {'claims': [claim]}}))
    return dispatcher.context()


def native(**changes):
    result = {'id': 'chatcmpl-fixture', 'model': MODEL, 'usage': {'prompt_tokens': 4, 'completion_tokens': 5, 'total_tokens': 9},
              'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                  'tool_calls': [{'type': 'function', 'id': 'call-fixture', 'function': {
                      'name': 'query_financial_evidence', 'arguments': '{"metrics":["revenue"]}'}}]}}]}
    result.update(changes)
    return result


def fixture_client(payload=None, models=None):
    client = NvidiaClient(TOKEN)
    calls = []
    def request(suffix, body=None, *, timeout):
        calls.append((suffix, body, timeout))
        return {'data': [{'id': value} for value in (models if models is not None else [MODEL])]} if suffix == '/models' else payload or native()
    client._opener = None
    return client, request, calls


def test_native_request_discovery_thinking_off_and_receipt():
    client, request, calls = fixture_client()
    with patch.object(NvidiaClient, '_request', side_effect=request):
        result = client.structured(query_context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)
    assert [call[0] for call in calls] == ['/models', '/chat/completions']
    body = calls[-1][1]
    from backend.providers.nvidia_spans import available_native_tools
    assert body['model'] == MODEL and body['tools'] == available_native_tools(tool_definitions(), query_context())
    assert body['tool_choice'] == 'auto' and body['parallel_tool_calls'] is False
    assert body['stream'] is False and body['max_tokens'] == 1536
    assert body['chat_template_kwargs'] == {'enable_thinking': False}
    assert 'reasoning_budget' not in body
    assert 'explicit span_index' in body['messages'][0]['content']
    assert json.loads(result['proposal']) == {'tool': 'query_financial_evidence', 'arguments': {'metrics': ['revenue']}}
    assert result['receipt']['response_model'] == MODEL
    assert result['receipt']['proposed_tool'] == 'query_financial_evidence'
    assert TOKEN not in json.dumps(result)


@pytest.mark.parametrize('model', ['nvidia/nemotron-other', None, 'meterless/auto'])
def test_model_absent_or_wrong_response_never_becomes_receipt(model):
    client, request, _ = fixture_client(native(model=model))
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(NvidiaError, match='model_mismatch'):
            client.structured(query_context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)


def test_unlisted_model_never_sends_completion():
    client, request, calls = fixture_client(models=['nvidia/nemotron-another'])
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(NvidiaError, match='not_available'):
            client.smoke(MODEL, timeout=5)
    assert [call[0] for call in calls] == ['/models']


def test_default_no_network_and_only_approved_local_fields(tmp_path, monkeypatch, capsys):
    config = tmp_path / 'local.env'
    config.write_text('UNRELATED_SECRET=ignored\nNVIDIA_API_KEY=' + TOKEN + '\nNVIDIA_MODEL_ID=' + MODEL + '\nNVIDIA_INFERENCE_ENABLED=true\n')
    monkeypatch.setattr(nvidia, 'LOCAL_CONFIG', config)
    for key in ('NVIDIA_API_KEY', 'NVIDIA_MODEL_ID', 'NVIDIA_INFERENCE_ENABLED', 'NVIDIA_FORMAT_CORRECTION_ENABLED', 'NVIDIA_BASE_URL'):
        monkeypatch.delenv(key, raising=False)
    with patch('subprocess.Popen') as spawn:
        assert main(['--discover']) == 2
        provider = nvidia.configured_nvidia_provider(enabled=True)
        assert provider.receipts == []
        spawn.assert_not_called()
    assert 'UNRELATED_SECRET' not in nvidia.local_configuration()
    monkeypatch.setenv('NVIDIA_MODEL_ID', 'nvidia/nemotron-process')
    assert nvidia.local_configuration()['NVIDIA_MODEL_ID'] == 'nvidia/nemotron-process'
    assert TOKEN not in capsys.readouterr().out


@pytest.mark.parametrize('base', ['http://integrate.api.nvidia.com/v1', 'https://evil.invalid/v1',
    'https://integrate.api.nvidia.com.evil.invalid/v1', 'https://integrate.api.nvidia.com/v1?x=1'])
def test_base_override_never_accepted(base, monkeypatch, tmp_path):
    monkeypatch.setattr(nvidia, 'LOCAL_CONFIG', tmp_path / 'absent')
    monkeypatch.setenv('NVIDIA_BASE_URL', base)
    with pytest.raises(NvidiaError, match='configuration_invalid'):
        nvidia.local_configuration()


@pytest.mark.parametrize('text', ['NVIDIA_API_KEY="unclosed\n', 'NVIDIA_API_KEY=a\nNVIDIA_API_KEY=b\n'])
def test_ambiguous_config_rejected(text, monkeypatch, tmp_path):
    config = tmp_path / 'local.env'; config.write_text(text)
    monkeypatch.setattr(nvidia, 'LOCAL_CONFIG', config)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    with pytest.raises(NvidiaError, match='configuration_invalid'):
        nvidia.local_configuration()


def test_parent_fixed_worker_envelope_and_defensive_receipts(monkeypatch):
    receipt = {'provider': 'nvidia_hosted', 'endpoint': nvidia.BASE_URL, 'requested_model': MODEL,
               'response_model': MODEL, 'response_id': 'fixture', 'usage': {}, 'elapsed_ms': 1,
               'proposed_tool': 'query_financial_evidence'}
    seen = []
    def run(message, deadline):
        seen.append(json.loads(message))
        return json.dumps({'proposal': '{"tool":"query_financial_evidence","arguments":{"metrics":["revenue"]}}', 'receipt': receipt}).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', run)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True)
    assert json.loads(provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()+1))['tool'] == 'query_financial_evidence'
    assert seen[0]['provider'] == 'nvidia' and seen[0]['operation'] == 'propose'
    assert provider.execution_kind == 'unverified_provider'
    copy = provider.receipts; copy[0]['response_model'] = 'changed'
    assert provider.receipts[0]['response_model'] == MODEL


def test_expired_deadline_and_tampered_tools_never_spawn():
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True)
    with patch('subprocess.Popen') as spawn:
        with pytest.raises(NvidiaError):
            provider.propose(context={}, tools=tool_definitions(), deadline=time.monotonic()-1)
        with pytest.raises(NvidiaError):
            provider.propose(context={}, tools=[], deadline=time.monotonic()+1)
        spawn.assert_not_called()


def test_request_headers_fixed_url_and_sanitized_http_error():
    client = NvidiaClient(TOKEN)
    captured = []
    class Opener:
        def open(self, request, timeout):
            captured.append(request)
            raise HTTPError(request.full_url, 401, TOKEN, {}, io.BytesIO(TOKEN.encode()))
    client._opener = Opener()
    with pytest.raises(NvidiaError, match='nvidia_unauthorized') as error:
        client._request('/models', timeout=2)
    assert str(error.value) == 'nvidia_unauthorized' and TOKEN not in str(error.value)
    request = captured[0]
    assert request.full_url == nvidia.BASE_URL + '/models'
    assert request.get_header('Authorization') == 'Bearer ' + TOKEN
    assert not any(key.lower().startswith('meterless') for key in request.headers)


def test_rejected_plain_multiple_and_duplicate_native_calls():
    examples = [native(choices=[]), native()]
    examples[-1]['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{"metrics":[],"metrics":[]}'
    multiple = native(); multiple['choices'][0]['message']['tool_calls'] *= 2; examples.append(multiple)
    plain = native(); plain['choices'][0]['message']['content'] = 'unsupported prose'; examples.append(plain)
    for payload in examples:
        client, request, _ = fixture_client(payload)
        with patch.object(NvidiaClient, '_request', side_effect=request):
            with pytest.raises(NvidiaError, match='invalid_native'):
                client.structured(query_context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)


def test_safe_native_diagnostic_reports_metadata_without_model_text_or_reasoning():
    payload = native()
    message = payload['choices'][0]['message']
    message.update(content='PRIVATE MODEL PROSE', reasoning_content='PRIVATE HIDDEN REASONING')
    message['tool_calls'][0]['function']['arguments'] = '{"secret":"PRIVATE ARGUMENTS"}'
    client, request, _ = fixture_client(payload)
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(NvidiaError) as failure:
            client.structured(query_context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)
    diagnostic = failure.value.diagnostic
    assert diagnostic == {'phase': 'native_decode', 'finish_reason': 'tool_calls', 'role': 'assistant',
        'nonempty_content': True, 'tool_call_count': 1, 'native_tool': 'query_financial_evidence',
        'validation_fields': [], 'binding_error': 'native_tool_invalid'}
    assert 'PRIVATE' not in json.dumps(diagnostic) and TOKEN not in json.dumps(diagnostic)


def test_safe_span_binding_diagnostic_maps_hostile_field_names_to_extra_field():
    from backend.tests.test_nvidia_spans import context, compact
    payload = native(); function = payload['choices'][0]['message']['tool_calls'][0]['function']
    proposal = compact(); proposal['arguments']['PRIVATE-HOSTILE-EXTRA-FIELD'] = 'PRIVATE ARGUMENT VALUE'
    function.update(name='propose_claim_from_span', arguments=json.dumps(proposal['arguments']))
    client, request, _ = fixture_client(payload)
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(NvidiaError) as failure:
            client.structured(context(), tool_definitions(), MODEL, max_tokens=1536, timeout=5)
    diagnostic = failure.value.diagnostic
    assert diagnostic['phase'] == 'span_binding' and diagnostic['binding_error'] == 'canonical_schema_invalid'
    assert diagnostic['validation_fields'] == ['extra_field']
    assert 'PRIVATE' not in json.dumps(diagnostic)


def test_parent_public_diagnostic_is_strict_and_defensive(monkeypatch):
    diagnostic = {'phase': 'native_decode', 'finish_reason': 'length', 'role': 'assistant',
        'nonempty_content': False, 'tool_call_count': 0, 'native_tool': 'unknown',
        'validation_fields': [], 'binding_error': 'native_tool_invalid'}
    result = {'error_code': 'nvidia_invalid_native_tool_call', 'diagnostic': diagnostic}
    monkeypatch.setattr(nvidia, 'run_structured_worker', lambda *args: json.dumps(result).encode())
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True)
    with pytest.raises(NvidiaError):
        provider.propose(context=query_context(), tools=tool_definitions(), deadline=time.monotonic()+1)
    assert provider.last_diagnostic == diagnostic and provider.receipts == []
    copied = provider.last_diagnostic; copied['role'] = 'changed'
    assert provider.last_diagnostic['role'] == 'assistant'
    result['diagnostic'] = diagnostic | {'raw_reasoning': 'PRIVATE VALUE'}
    with pytest.raises(NvidiaError):
        provider.propose(context=query_context(), tools=tool_definitions(), deadline=time.monotonic()+1)
    assert provider.last_diagnostic is None


@pytest.mark.parametrize('change', [{'role': 'PRIVATE ROLE'}, {'finish_reason': 'PRIVATE FINISH'},
    {'native_tool': 'PRIVATE TOOL'}, {'tool_call_count': 999}, {'tool_call_count': True},
    {'nonempty_content': 'PRIVATE TEXT'}, {'binding_error': 'PRIVATE ERROR'},
    {'validation_fields': ['PRIVATE FIELD']}, {'phase': 'PRIVATE PHASE'}])
def test_untrusted_diagnostic_values_fail_closed(change):
    diagnostic = {'phase': 'native_decode', 'finish_reason': 'tool_calls', 'role': 'assistant',
        'nonempty_content': False, 'tool_call_count': 1, 'native_tool': 'query_financial_evidence',
        'validation_fields': [], 'binding_error': 'native_tool_invalid'} | change
    with pytest.raises(ValueError):
        nvidia.validate_diagnostic(diagnostic)


def _format_failure(**changes):
    diagnostic = {'phase': 'span_binding', 'finish_reason': 'tool_calls', 'role': 'assistant',
        'nonempty_content': False, 'tool_call_count': 1, 'native_tool': 'propose_claim_from_span',
        'validation_fields': ['expected_value_decimal'], 'binding_error': 'canonical_schema_invalid'} | changes
    return {'error_code': 'nvidia_invalid_native_tool_call', 'diagnostic': diagnostic}


def _valid_span_result():
    from backend.tests.test_nvidia_spans import context, compact
    from backend.providers.nvidia_spans import canonical_proposal
    proposal, _ = canonical_proposal(compact(), context())
    return {'proposal': json.dumps(proposal), 'receipt': {'provider': 'nvidia_hosted', 'endpoint': nvidia.BASE_URL,
        'requested_model': MODEL, 'response_model': MODEL, 'response_id': 'fixture-valid-new-model-call',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}, 'elapsed_ms': 1,
        'proposed_tool': 'propose_extracted_claims', 'native_tool': 'propose_claim_from_span',
        'source_binding': 'host_registered_span'}}


def test_one_new_model_proposal_corrects_only_typed_format_with_visible_history(monkeypatch):
    from copy import deepcopy
    from backend.tests.test_nvidia_spans import context
    original = context(); unchanged = deepcopy(original)
    responses = [_format_failure(), _valid_span_result()]
    calls = []
    def worker(message, deadline):
        calls.append((json.loads(message), deadline))
        return json.dumps(responses.pop(0)).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    deadline = time.monotonic() + 2
    result = provider.propose(context=original, tools=tool_definitions(), deadline=deadline)
    assert json.loads(result)['tool'] == 'propose_extracted_claims'
    assert provider.propose_attempts == 2 and len(calls) == 2
    assert calls[0][1] == calls[1][1] == deadline
    assert calls[0][0]['context'] == unchanged and original == unchanged
    feedback = calls[1][0]['context'].pop('provider_validation_feedback')
    assert calls[1][0]['context'] == unchanged
    assert feedback == {'code': 'financial_format_rejected_regenerate_new_flat_proposal',
        'validation_fields': ['expected_value_decimal'], 'source_text_is_untrusted': True}
    assert '2.29' not in json.dumps(feedback) and TOKEN not in json.dumps(feedback)
    assert len(provider.receipts) == 1
    assert provider.validation_history[0]['attempt'] == 1
    assert provider.validation_history[0]['self_correction_requested'] is True
    copied = provider.validation_history; copied[0]['diagnostic']['role'] = 'changed'
    assert provider.validation_history[0]['diagnostic']['role'] == 'assistant'
    assert provider.last_error_code is None and provider.last_diagnostic is None


@pytest.mark.parametrize('changes', [
    {'phase': 'native_decode'}, {'binding_error': 'unknown_registered_source'},
    {'binding_error': 'source_integrity_invalid'}, {'binding_error': 'invalid_span_selection'},
    {'validation_fields': ['extra_field']}, {'validation_fields': ['period_start']},
    {'validation_fields': ['disclosure_id']}, {'validation_fields': ['span_index']},
    {'validation_fields': ['id']}, {'validation_fields': ['quote_ref', 'text_sha256']},
    {'validation_fields': []},
])
def test_unsafe_native_source_scope_and_unknown_fields_never_trigger_correction(changes, monkeypatch):
    from backend.tests.test_nvidia_spans import context
    calls = []
    def worker(message, deadline):
        calls.append(json.loads(message)); return json.dumps(_format_failure(**changes)).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    with pytest.raises(NvidiaError):
        provider.propose(context=context(), tools=tool_definitions(), deadline=time.monotonic()+2)
    assert len(calls) == provider.propose_attempts == 1 and provider.receipts == []
    assert provider.validation_history[0]['self_correction_requested'] is False


def test_only_one_format_correction_is_available_for_the_whole_provider(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    responses = [_format_failure(), _valid_span_result(), _format_failure()]
    calls = []
    def worker(message, deadline):
        calls.append(json.loads(message)); return json.dumps(responses.pop(0)).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    deadline = time.monotonic()+2
    provider.propose(context=context(), tools=tool_definitions(), deadline=deadline)
    with pytest.raises(NvidiaError):
        provider.propose(context=context(), tools=tool_definitions(), deadline=deadline)
    assert provider.propose_attempts == len(calls) == 3 and len(provider.receipts) == 1
    assert [row['self_correction_requested'] for row in provider.validation_history] == [True, False]


def test_global_eight_propose_attempt_cap_includes_failed_format_and_correction(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    calls = []
    def worker(message, deadline):
        calls.append(json.loads(message)); return json.dumps(_format_failure() if len(calls) == 1 else _valid_span_result()).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    deadline = time.monotonic()+2
    for _ in range(7):
        provider.propose(context=context(), tools=tool_definitions(), deadline=deadline)
    with pytest.raises(NvidiaError, match='nvidia_propose_budget_exhausted'):
        provider.propose(context=context(), tools=tool_definitions(), deadline=deadline)
    assert provider.propose_attempts == len(calls) == 8 and len(provider.receipts) == 7


def test_original_absolute_deadline_cannot_be_extended_by_a_later_propose(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    clock = [100.0]; calls = []
    monkeypatch.setattr(nvidia.time, 'monotonic', lambda: clock[0])
    def worker(message, deadline):
        calls.append(deadline); return json.dumps(_valid_span_result()).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True)
    provider.propose(context=context(), tools=tool_definitions(), deadline=100.5)
    clock[0] = 100.6
    with pytest.raises(NvidiaError, match='nvidia_deadline_exhausted'):
        provider.propose(context=context(), tools=tool_definitions(), deadline=200)
    assert calls == [100.5] and provider.propose_attempts == 1


def test_format_failure_after_deadline_has_no_second_model_attempt(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    clock = [100.0]; calls = []
    monkeypatch.setattr(nvidia.time, 'monotonic', lambda: clock[0])
    def worker(message, deadline):
        calls.append(deadline); clock[0] = 101.0; return json.dumps(_format_failure()).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    with pytest.raises(NvidiaError):
        provider.propose(context=context(), tools=tool_definitions(), deadline=100.5)
    assert len(calls) == provider.propose_attempts == 1
    assert provider.validation_history[0]['self_correction_requested'] is False


def test_provider_network_failure_counts_an_attempt_without_retry(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    calls = []
    def worker(message, deadline):
        calls.append(deadline); return json.dumps({'error_code': 'nvidia_unauthorized'}).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    with pytest.raises(NvidiaError, match='nvidia_unauthorized'):
        provider.propose(context=context(), tools=tool_definitions(), deadline=time.monotonic()+2)
    assert provider.propose_attempts == len(calls) == 1 and provider.validation_history == []


def test_financial_format_correction_is_disabled_without_separate_host_opt_in(monkeypatch):
    from backend.tests.test_nvidia_spans import context
    calls = []
    def worker(message, deadline):
        calls.append(json.loads(message)); return json.dumps(_format_failure()).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True)
    injected_context = context() | {'NVIDIA_FORMAT_CORRECTION_ENABLED': True, 'allow_format_correction': True}
    with pytest.raises(NvidiaError):
        provider.propose(context=injected_context, tools=tool_definitions(), deadline=time.monotonic()+2)
    assert provider.format_correction_enabled is False
    assert len(calls) == provider.propose_attempts == 1 and provider.receipts == []
    assert provider.validation_history[0]['self_correction_requested'] is False


def test_factory_separate_named_flag_controls_correction_and_process_precedence(monkeypatch, tmp_path):
    config = tmp_path / 'local.env'
    config.write_text('NVIDIA_API_KEY=' + TOKEN + '\nNVIDIA_MODEL_ID=' + MODEL +
        '\nNVIDIA_INFERENCE_ENABLED=true\nNVIDIA_FORMAT_CORRECTION_ENABLED=true\n')
    monkeypatch.setattr(nvidia, 'LOCAL_CONFIG', config)
    for name in ('NVIDIA_API_KEY', 'NVIDIA_MODEL_ID', 'NVIDIA_INFERENCE_ENABLED', 'NVIDIA_FORMAT_CORRECTION_ENABLED', 'NVIDIA_BASE_URL'):
        monkeypatch.delenv(name, raising=False)
    assert nvidia.configured_nvidia_provider(enabled=True).format_correction_enabled is True
    monkeypatch.setenv('NVIDIA_FORMAT_CORRECTION_ENABLED', 'false')
    assert nvidia.configured_nvidia_provider(enabled=True).format_correction_enabled is False
    monkeypatch.delenv('NVIDIA_FORMAT_CORRECTION_ENABLED')
    config.write_text('NVIDIA_API_KEY=' + TOKEN + '\nNVIDIA_MODEL_ID=' + MODEL + '\nNVIDIA_INFERENCE_ENABLED=true\n')
    assert nvidia.configured_nvidia_provider(enabled=True).format_correction_enabled is False


@pytest.mark.parametrize('setting', ['true', 1, None, {}])
def test_correction_constructor_rejects_non_boolean_enablement(setting):
    with pytest.raises(NvidiaError, match='nvidia_configuration_invalid'):
        NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=setting)


def test_observed_super_pair_is_rejected_by_default_and_only_explicitly_reports_dual_names():
    requested, served = nvidia.OBSERVED_SUPER_REQUESTED, nvidia.OBSERVED_SUPER_SERVED
    with pytest.raises(NvidiaError, match='nvidia_response_model_mismatch'):
        nvidia.model_identity_status(requested, served)
    assert nvidia.model_identity_status(requested, served, allow_observed_super_route=True) == nvidia.OBSERVED_SUPER_IDENTITY_STATUS
    assert nvidia.model_identity_status(MODEL, MODEL) == 'requested_and_server_reported_model_match'


@pytest.mark.parametrize('requested,served', [
    (nvidia.OBSERVED_SUPER_SERVED, nvidia.OBSERVED_SUPER_REQUESTED),
    (nvidia.OBSERVED_SUPER_REQUESTED.upper(), nvidia.OBSERVED_SUPER_SERVED),
    (nvidia.OBSERVED_SUPER_REQUESTED, nvidia.OBSERVED_SUPER_SERVED.upper()),
    (nvidia.OBSERVED_SUPER_REQUESTED, nvidia.OBSERVED_SUPER_SERVED + '-other'),
    (nvidia.OBSERVED_SUPER_REQUESTED + '-other', nvidia.OBSERVED_SUPER_SERVED),
    (MODEL, 'private/' + MODEL), (MODEL, 'nvidia/nemotron-other'),
    (nvidia.OBSERVED_SUPER_REQUESTED, 'nvidia/nemotron-3.5-super-120b-a12b'),
])
def test_observed_super_route_never_strips_prefixes_or_accepts_other_ordered_pairs(requested, served):
    with pytest.raises(NvidiaError, match='nvidia_response_model_mismatch'):
        nvidia.model_identity_status(requested, served, allow_observed_super_route=True)


def test_actual_text_wire_receipt_keeps_observed_requested_and_served_names_without_attestation():
    requested, served = nvidia.OBSERVED_SUPER_REQUESTED, nvidia.OBSERVED_SUPER_SERVED
    payload = native(model=served)
    payload['choices'] = [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'READY'}}]
    _, request, calls = fixture_client(payload, models=[requested])
    client = NvidiaClient(TOKEN, allow_observed_super_route=True)
    with patch.object(NvidiaClient, '_request', side_effect=request):
        result = client.smoke(requested, timeout=5)
    assert calls[-1][1]['model'] == requested
    assert all(isinstance(message['content'], str) for message in calls[-1][1]['messages'])
    assert result['receipt']['requested_model'] == requested
    assert result['receipt']['response_model'] == served
    assert result['receipt']['identity_status'] == 'server_reported_name_differs_requested_route'
    assert 'model_identity_verified' not in result['receipt']
    assert 'underlying_weights' not in result['receipt']
    client = NvidiaClient(TOKEN)
    with patch.object(NvidiaClient, '_request', side_effect=request):
        with pytest.raises(NvidiaError, match='nvidia_response_model_mismatch'):
            client.smoke(requested, timeout=5)


@pytest.mark.parametrize('content', [
    [{'type': 'text', 'text': 'hello'}, {'type': 'image_url', 'image_url': {'url': 'https://example.invalid/image'}}],
    {'type': 'image_url', 'url': 'https://example.invalid/image'},
])
def test_observed_route_remains_text_only_before_any_request(content):
    client = NvidiaClient(TOKEN, allow_observed_super_route=True)
    with patch.object(NvidiaClient, '_request') as request:
        with pytest.raises(NvidiaError, match='nvidia_request_rejected'):
            client._completion(nvidia.OBSERVED_SUPER_REQUESTED, [{'role': 'user', 'content': content}],
                               timeout=5, max_tokens=32)
        request.assert_not_called()


@pytest.mark.parametrize('enabled', [False, True])
def test_parent_observed_pair_requires_explicit_opt_in_and_exact_receipt_status(enabled, monkeypatch):
    requested, served = nvidia.OBSERVED_SUPER_REQUESTED, nvidia.OBSERVED_SUPER_SERVED
    receipt = {'provider': 'nvidia_hosted', 'endpoint': nvidia.BASE_URL,
        'requested_model': requested, 'response_model': served, 'response_id': 'observed-fixture',
        'usage': {}, 'elapsed_ms': 1, 'proposed_tool': 'query_financial_evidence',
        'identity_status': nvidia.OBSERVED_SUPER_IDENTITY_STATUS}
    result = {'proposal': '{"tool":"query_financial_evidence","arguments":{"metrics":["revenue"]}}', 'receipt': receipt}
    sent = []
    def worker(message, deadline):
        sent.append(json.loads(message)); return json.dumps(result).encode()
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, requested, enabled=True, allow_observed_super_route=enabled)
    if enabled:
        provider.propose(context=query_context(), tools=tool_definitions(), deadline=time.monotonic()+2)
        assert provider.receipts == [receipt]
    else:
        with pytest.raises(NvidiaError, match='nvidia_response_model_mismatch'):
            provider.propose(context=query_context(), tools=tool_definitions(), deadline=time.monotonic()+2)
        assert provider.receipts == []
    assert sent[0]['allow_observed_super_route'] is enabled


@pytest.mark.parametrize('status', [None, 'requested_and_server_reported_model_match', 'weights_verified', ''])
def test_parent_observed_pair_rejects_missing_or_forged_identity_annotation(status, monkeypatch):
    receipt = {'provider': 'nvidia_hosted', 'endpoint': nvidia.BASE_URL,
        'requested_model': nvidia.OBSERVED_SUPER_REQUESTED, 'response_model': nvidia.OBSERVED_SUPER_SERVED,
        'response_id': 'fixture', 'usage': {}, 'elapsed_ms': 1, 'proposed_tool': 'query_financial_evidence'}
    if status is not None:
        receipt['identity_status'] = status
    result = {'proposal': '{"tool":"query_financial_evidence","arguments":{"metrics":["revenue"]}}', 'receipt': receipt}
    monkeypatch.setattr(nvidia, 'run_structured_worker', lambda *args: json.dumps(result).encode())
    provider = NvidiaStructuredProvider(TOKEN, nvidia.OBSERVED_SUPER_REQUESTED,
                                        enabled=True, allow_observed_super_route=True)
    with pytest.raises(NvidiaError):
        provider.propose(context=query_context(), tools=tool_definitions(), deadline=time.monotonic()+2)
    assert provider.receipts == []


def test_factory_observed_route_flag_is_named_default_off_and_process_overrides_local(monkeypatch, tmp_path):
    config = tmp_path / 'local.env'
    settings = 'NVIDIA_API_KEY=' + TOKEN + '\nNVIDIA_MODEL_ID=' + nvidia.OBSERVED_SUPER_REQUESTED + '\nNVIDIA_INFERENCE_ENABLED=true\n'
    config.write_text(settings)
    monkeypatch.setattr(nvidia, 'LOCAL_CONFIG', config)
    for name in ('NVIDIA_API_KEY', 'NVIDIA_MODEL_ID', 'NVIDIA_INFERENCE_ENABLED', 'NVIDIA_FORMAT_CORRECTION_ENABLED', 'NVIDIA_ALLOW_OBSERVED_SUPER_ROUTE', 'NVIDIA_BASE_URL'):
        monkeypatch.delenv(name, raising=False)
    assert nvidia.configured_nvidia_provider(enabled=True).observed_super_route_enabled is False
    config.write_text(settings + 'NVIDIA_ALLOW_OBSERVED_SUPER_ROUTE=true\n')
    assert nvidia.configured_nvidia_provider(enabled=True).observed_super_route_enabled is True
    monkeypatch.setenv('NVIDIA_ALLOW_OBSERVED_SUPER_ROUTE', 'false')
    assert nvidia.configured_nvidia_provider(enabled=True).observed_super_route_enabled is False


def test_native_auto_never_promotes_plain_text_into_a_tool_or_financial_effect(monkeypatch):
    from backend.tests.test_nvidia_spans import _dispatcher
    dispatcher, _ = _dispatcher()
    plaintext = native(choices=[{'finish_reason': 'stop', 'message': {
        'role': 'assistant', 'content': 'Synthetic plain answer: revenue is verified.'}}])
    client, request, calls = fixture_client(plaintext)
    def worker(message, deadline):
        values = json.loads(message)
        with patch.object(NvidiaClient, '_request', side_effect=request):
            try:
                client.structured(values['context'], values['tools'], values['model'],
                    max_tokens=values['max_tokens'], timeout=values['timeout'])
            except NvidiaError as error:
                return json.dumps({'error_code': str(error), 'diagnostic': error.diagnostic}).encode()
        raise AssertionError('Plaintext must never become a native proposal')
    monkeypatch.setattr(nvidia, 'run_structured_worker', worker)
    provider = NvidiaStructuredProvider(TOKEN, MODEL, enabled=True, allow_format_correction=True)
    report = dispatcher.run(provider)
    assert calls[-1][1]['tool_choice'] == 'auto'
    assert report['status'] == 'blocked' and report['tool_calls'] == 0
    assert report['evidence'] == [] and report['original_claims'] == []
    assert report['conclusion'] is None and provider.receipts == []
    assert provider.propose_attempts == 1 and provider.last_diagnostic['phase'] == 'native_decode'
    assert provider.last_diagnostic['nonempty_content'] is True
    assert provider.validation_history[0]['self_correction_requested'] is False
