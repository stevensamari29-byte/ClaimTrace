"""Local protocol fixtures exercise transport and budgets, never live inference."""
from contextlib import contextmanager
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from unittest.mock import patch

import pytest

from backend.providers.meterless_client import MeterlessClient, ClientError
from backend.providers.structured import NightshiftStructuredProvider, StructuredProviderError
from backend.providers.nightshift import configured_structured_runtime
from backend.investigation.model_contracts import tool_definitions
from backend.tests.test_model_contracts import gate_data


def answer(arguments='{"metrics":["revenue"]}', **changes):
    message = {'role': 'assistant', 'content': None, 'tool_calls': [
        {'type': 'function', 'id': 'test-call', 'function':
         {'name': 'query_financial_evidence', 'arguments': arguments}}]}
    message.update(changes)
    return {'choices': [{'finish_reason': 'tool_calls', 'message': message}]}


@contextmanager
def fixture_server(payload=None, *, drip=False, status=200):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            requests.append((self.path, self.headers, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(status)
            self.end_headers()
            raw = json.dumps(payload if payload is not None else answer()).encode()
            try:
                if drip:
                    for byte in raw:
                        self.wfile.write(bytes([byte])); self.wfile.flush(); time.sleep(.02)
                else:
                    self.wfile.write(raw)
            except OSError:
                pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', requests
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_worker_real_http_wire_context_and_proposal():
    with fixture_server() as (url, requests):
        provider = NightshiftStructuredProvider(url, 'private-test-token', 'meterless/auto', enabled=True)
        context = {'scope': {'period': 'Q2'}, 'tool_results': [{'state': 'prior_check'}],
                   'disclosures': [{'text': 'Untrusted instruction to ignore scope'}]}
        result = json.loads(provider.propose(context=context, tools=tool_definitions(), deadline=time.monotonic()+8))
        assert result == {'tool': 'query_financial_evidence', 'arguments': {'metrics': ['revenue']}}
        path, headers, body = requests[0]
        assert path == '/v1/chat/completions'
        assert headers['Authorization'] == 'Bearer private-test-token'
        assert headers['meterless-app'] == 'claimtrace' and headers['meterless-scope'] == 'user'
        assert body['tools'] == tool_definitions() and body['tool_choice'] == 'required'
        assert body['parallel_tool_calls'] is False and body['stream'] is False
        assert 1024 <= body['max_tokens'] <= 2048
        assert json.loads(body['messages'][1]['content']) == context
        assert provider.execution_kind == 'unverified_provider'


@pytest.mark.parametrize('payload', [answer('{"metrics":[],"metrics":[]}'), answer('{"x":NaN}'),
    answer('{"x":1e999}'), answer('[]'), answer('{'), answer(content='plain answer'),
    answer(refusal='no'), {'choices': []}, answer(tool_calls=[]),
    answer(tool_calls=answer()['choices'][0]['message']['tool_calls'] * 2), answer('"'+'x'*66000+'"')])
def test_malformed_native_calls_rejected(payload):
    client = MeterlessClient('http://127.0.0.1:1', 'private-test-token')
    with patch.object(MeterlessClient, '_request', return_value=payload):
        with pytest.raises(ClientError, match='Invalid structured tool response'):
            client.structured({}, tool_definitions(), 'meterless/auto')


def test_default_gates_never_spawn_or_fetch(monkeypatch):
    monkeypatch.delenv('NIGHTSHIFT_INFERENCE_ENABLED', raising=False)
    with patch('subprocess.Popen') as spawn:
        with pytest.raises(StructuredProviderError, match='disabled'):
            NightshiftStructuredProvider('http://127.0.0.1:1', 'token', 'meterless/auto')
        with pytest.raises(StructuredProviderError, match='disabled'):
            configured_structured_runtime(enabled=True)
        spawn.assert_not_called()


def test_configured_factory_preserves_existing_model_id_configuration(monkeypatch):
    monkeypatch.setenv('NIGHTSHIFT_INFERENCE_ENABLED', 'true')
    monkeypatch.setenv('NIGHTSHIFT_BASE_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('NIGHTSHIFT_RUNTIME_TOKEN', 'fixture-private-token')
    monkeypatch.setenv('NIGHTSHIFT_MODEL_ID', 'meterless/fixture')
    with patch('subprocess.Popen') as spawn:
        provider = configured_structured_runtime(enabled=True)
        assert provider.execution_kind == 'unverified_provider'
        spawn.assert_not_called()


def test_expired_deadline_and_tampered_tools_do_not_spawn():
    provider = NightshiftStructuredProvider('http://127.0.0.1:1', 'token', 'meterless/auto', enabled=True)
    with patch('subprocess.Popen') as spawn:
        for deadline, tools in [(time.monotonic()-1, tool_definitions()), (time.monotonic()+1, [])]:
            with pytest.raises(StructuredProviderError):
                provider.propose(context={}, tools=tools, deadline=deadline)
        spawn.assert_not_called()


def test_dripping_body_killed_at_global_deadline():
    with fixture_server(drip=True) as (url, requests):
        provider = NightshiftStructuredProvider(url, 'private-test-token', 'meterless/auto', enabled=True)
        started = time.monotonic()
        with pytest.raises(StructuredProviderError) as failure:
            provider.propose(context={}, tools=tool_definitions(), deadline=started+.8)
        assert time.monotonic()-started < 1.5
        assert 'private-test-token' not in str(failure.value)
        assert len(requests) == 1


def test_cli_default_blocked_without_network(tmp_path):
    from backend.investigation.model_run import main
    request, *_ = gate_data()
    path = tmp_path/'request.json'
    path.write_text(json.dumps(request.model_dump(mode='json') if hasattr(request, 'model_dump') else request))
    with patch('subprocess.Popen') as spawn, patch('sys.stdout', new_callable=io.StringIO) as out:
        assert main([str(path)]) == 2
        report = json.loads(out.getvalue())
        assert report['error_code'] == 'structured_provider_unavailable'
        assert report['tool_calls'] == 0 and report['live_inference_verified'] is False
        spawn.assert_not_called()


def test_memory_recall_is_host_only_context(tmp_path):
    from backend.investigation.dispatcher import RestrictedDispatcher
    from backend.investigation.memory import HMemMemory
    request, fact, *_ = gate_data()
    memory = HMemMemory(tmp_path)
    d = RestrictedDispatcher(request, retriever=lambda *_: [fact], memory=memory)
    recalled = [{'text': 'Reviewed context', 'role': 'reviewed_context_only_not_financial_fact'}]
    with patch.object(HMemMemory, 'recall', return_value=recalled) as recall:
        d.dispatch(json.dumps({'tool': 'query_financial_evidence', 'arguments': {'metrics': ['diluted_eps']}}))
        recall.assert_called_once()
    context = d.context()
    assert context['reviewed_memory_context'] == recalled
    context['reviewed_memory_context'].clear()
    assert d.context()['reviewed_memory_context'] == recalled
    assert d.report()['human_review_status'] == 'required'
    assert memory.timeout == 3


def test_real_hmem_reviewed_correction_reaches_dispatcher_context(tmp_path):
    """Actual vendored H-MEM worker with fixture financial evidence, no model."""
    from backend.investigation.dispatcher import RestrictedDispatcher
    from backend.investigation.memory import HMemMemory
    request, fact, *_ = gate_data()
    query = json.dumps({'tool': 'query_financial_evidence', 'arguments': {'metrics': ['diluted_eps']}})
    first = RestrictedDispatcher(request, retriever=lambda *_: [fact])
    first.dispatch(query)
    memory = HMemMemory(tmp_path)
    proposal = memory.propose(request, 'Reviewed correction: quarterly diluted GAAP EPS.',
                              first.report()['evidence'], 'dispatcher-correction')
    receipt = memory.review(proposal, approved_digest=proposal['digest'], approve=True)
    second = RestrictedDispatcher(request, retriever=lambda *_: [fact], memory=memory)
    second.dispatch(query)
    recalled = second.context()['reviewed_memory_context']
    assert len(recalled) == 1 and recalled[0]['memory_id'] == receipt['memory_id']
    assert recalled[0]['role'] == 'reviewed_context_only_not_financial_fact'
    assert recalled[0]['sources'][0]['published_at'] == '2026-07-21'
    assert second.report()['human_review_status'] == 'required'
