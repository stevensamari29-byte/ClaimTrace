"""Independent adversarial protocol tests. Loopback fixtures are not model inference."""
import copy
import json
import subprocess
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from backend.investigation.model_contracts import tool_definitions
from backend.providers.meterless_client import MeterlessClient, ClientError
from backend.providers.structured import NightshiftStructuredProvider, StructuredProviderError

TOKEN = 'qa-fixture-token-not-a-real-credential'

class ProtocolHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.server.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(self.server.status)
        self.end_headers()
        try:
            if self.server.drip:
                self.server.started.set()
                for _ in range(100):
                    self.wfile.write(b' ')
                    self.wfile.flush()
                    time.sleep(.03)
            else:
                self.wfile.write(self.server.payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.server.disconnected.set()

class IndependentProviderAcceptance(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ProtocolHandler)
        self.server.daemon_threads = True
        self.server.requests = []
        self.server.status = 200
        self.server.drip = False
        self.server.started = threading.Event()
        self.server.disconnected = threading.Event()
        self.tools = tool_definitions()
        self.name = self.tools[0]['function']['name']
        self.good = {'choices': [{'finish_reason': 'tool_calls', 'message': {
            'role': 'assistant', 'content': None, 'tool_calls': [{'type': 'function',
            'function': {'name': self.name, 'arguments': '{}'}}]}}]}
        self.server.payload = json.dumps(self.good).encode()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def provider(self):
        return NightshiftStructuredProvider(self.base, TOKEN, 'meterless/qa-fixture', enabled=True)

    def test_disabled_default_and_constructor_make_no_requests(self):
        with self.assertRaises(StructuredProviderError):
            NightshiftStructuredProvider(self.base, TOKEN, 'meterless/qa-fixture')
        provider = self.provider()
        self.assertEqual(self.server.requests, [])
        self.assertEqual(provider.execution_kind, 'unverified_provider')
        self.assertNotIn(TOKEN, repr(provider))

    def test_real_worker_single_call_and_native_request_contract(self):
        result = self.provider().propose(context={'scope': 'fixture'}, tools=self.tools, deadline=time.monotonic()+4)
        self.assertEqual(json.loads(result), {'tool': self.name, 'arguments': {}})
        self.assertEqual(len(self.server.requests), 1)
        body = self.server.requests[0]
        self.assertEqual(body['tools'], self.tools)
        self.assertEqual(body['tool_choice'], 'required')
        self.assertFalse(body['parallel_tool_calls'])
        self.assertFalse(body['stream'])
        self.assertLessEqual(body['max_tokens'], 2048)

    def test_ambiguous_refused_truncated_and_unknown_protocols_are_rejected(self):
        variants = []
        for modification in ('two_choices', 'two_calls', 'plain_text', 'refusal', 'length', 'unknown', 'duplicate', 'nonfinite'):
            payload = copy.deepcopy(self.good)
            message = payload['choices'][0]['message']
            if modification == 'two_choices': payload['choices'] *= 2
            elif modification == 'two_calls': message['tool_calls'] *= 2
            elif modification == 'plain_text': message['content'] = 'untrusted answer'
            elif modification == 'refusal': message['refusal'] = 'refused'
            elif modification == 'length': payload['choices'][0]['finish_reason'] = 'length'
            elif modification == 'unknown': message['tool_calls'][0]['function']['name'] = 'arbitrary_sql'
            elif modification == 'duplicate': message['tool_calls'][0]['function']['arguments'] = '{"x":1,"x":2}'
            elif modification == 'nonfinite': message['tool_calls'][0]['function']['arguments'] = '{"x":NaN}'
            variants.append((modification, payload))
        client = MeterlessClient(self.base, TOKEN)
        for name, payload in variants:
            with self.subTest(protocol=name):
                self.server.payload = json.dumps(payload).encode()
                with self.assertRaises(ClientError):
                    client.structured({}, self.tools, 'meterless/qa-fixture')

    def test_untrusted_tool_definition_never_reaches_network(self):
        tools = copy.deepcopy(self.tools)
        tools[0]['function']['name'] = 'run_command'
        with self.assertRaises(StructuredProviderError):
            self.provider().propose(context={}, tools=tools, deadline=time.monotonic()+4)
        self.assertEqual(self.server.requests, [])

    def test_expired_deadline_prevents_child_and_request(self):
        with patch('backend.providers.structured.subprocess.Popen') as launch:
            with self.assertRaises(StructuredProviderError):
                self.provider().propose(context={}, tools=self.tools, deadline=time.monotonic()-1)
            launch.assert_not_called()
        self.assertEqual(self.server.requests, [])

    def test_slow_body_absolute_deadline_kills_and_reaps_worker(self):
        self.server.drip = True
        children = []
        actual_popen = subprocess.Popen
        def capture(*args, **kwargs):
            child = actual_popen(*args, **kwargs)
            children.append(child)
            self.assertNotIn(TOKEN, repr(args))
            self.assertNotIn(TOKEN, repr(kwargs.get('env')))
            return child
        started = time.monotonic()
        with patch('backend.providers.structured.subprocess.Popen', side_effect=capture):
            with self.assertRaises(StructuredProviderError) as caught:
                self.provider().propose(context={}, tools=self.tools, deadline=started+.8)
        self.assertLess(time.monotonic()-started, 2)
        self.assertTrue(children)
        self.assertIsNotNone(children[0].poll())
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertTrue(self.server.started.is_set())
        self.assertTrue(self.server.disconnected.wait(1))

    def test_error_body_secret_and_endpoint_are_not_exposed(self):
        self.server.status = 500
        self.server.payload = (TOKEN + self.base).encode()
        with self.assertRaises(StructuredProviderError) as caught:
            self.provider().propose(context={}, tools=self.tools, deadline=time.monotonic()+4)
        self.assertEqual(str(caught.exception), 'structured_provider_unavailable')
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertNotIn(self.base, str(caught.exception))
