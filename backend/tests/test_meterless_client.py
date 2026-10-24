"""Local HTTP fixture tests only. This is NOT a Nightshift verification."""
import json
import threading
import unittest
from http.client import BadStatusLine, IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from backend.providers.meterless_client import MeterlessClient, ClientError, normalize_base, auto_detect


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.seen.append((self.path, dict(self.headers), None))
        self.respond()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.seen.append((self.path, dict(self.headers), body))
        self.respond()

    def respond(self):
        code, payload = self.server.reply
        self.send_response(code)
        if code == 302:
            self.send_header('Location', self.server.redirect)
        self.end_headers()
        self.wfile.write(payload)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.reply = (200, b'{"data":[{"id":"meterless/novel.future"},{"id":"other/model"}]}')
        self.server.seen = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = MeterlessClient('http://127.0.0.1:' + str(self.server.server_port), 'fixture-private-token')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_models_headers_unknown_ids_and_no_construction_call(self):
        self.assertEqual(self.server.seen, [])
        self.assertEqual(self.client.discover(), {'status':'online', 'models':['meterless/novel.future']})
        path, headers, _ = self.server.seen[0]
        headers = {k.lower():v for k,v in headers.items()}
        self.assertEqual(path, '/v1/models')
        self.assertEqual(headers['authorization'], 'Bearer fixture-private-token')
        self.assertEqual(headers['meterless-app'], 'claimtrace')
        self.assertNotIn('meterless-scope', headers)
        self.assertNotIn('fixture-private-token', repr(self.client))

    def test_auth_and_invalid_response_states(self):
        for code, payload, status in [(401,b'secret-body','unauthorized'), (403,b'','unauthorized'), (500,b'','offline'), (200,b'not-json','offline'), (200,b'[]','offline'), (200,b'{"data":{}}','offline'), (200,b'{"data":[{"id":1}]}','offline'), (200,b'{"data":[]}','offline')]:
            with self.subTest(code=code,payload=payload):
                self.server.reply = (code,payload)
                self.assertEqual(self.client.discover()['status'], status)

    def test_chat_plain_text_headers_and_response(self):
        self.server.reply = (200,b'{"choices":[{"message":{"content":"fixture reply"}}]}')
        with patch.object(self.client._opener, 'open', wraps=self.client._opener.open) as opened:
            self.assertEqual(self.client.chat('plain fixture', 'meterless/novel.future'), 'fixture reply')
            self.assertEqual(opened.call_args.kwargs['timeout'], 180)
        path, headers, body = self.server.seen[0]
        self.assertEqual(path, '/v1/chat/completions')
        self.assertEqual({k.lower():v for k,v in headers.items()}['meterless-scope'], 'user')
        self.assertEqual(body['messages'][0]['content'], 'plain fixture')
        self.assertEqual(body['max_tokens'], 128)
        self.assertFalse(body['stream'])

    def test_wrong_chat_shape_and_sanitized_error(self):
        for payload in (b'{}',b'null',b'{"choices":[]}',b'{"choices":[{"message":{"content":[]}}]}'):
            self.server.reply = (200,payload)
            with self.assertRaises(ClientError):
                self.client.chat('fixture','meterless/text')
        self.server.reply = (500,b'fixture-private-token secret-response')
        with self.assertRaises(ClientError) as caught:
            self.client.chat('fixture','meterless/text')
        self.assertEqual(str(caught.exception), 'Runtime HTTP failure')

    def test_redirect_refused_without_second_request(self):
        self.server.redirect = self.client.base_url + '/models?secret=value'
        self.server.reply = (302,b'')
        self.assertEqual(self.client.discover()['status'], 'offline')
        self.assertEqual(len(self.server.seen),1)

    def test_injected_transport_timeout_is_offline_and_sanitized(self):
        with patch.object(self.client._opener, 'open', side_effect=TimeoutError('private token text')):
            self.assertEqual(self.client.discover()['status'], 'offline')
            with self.assertRaisesRegex(ClientError,'^Runtime unavailable or invalid JSON$'):
                self.client.chat('fixture','meterless/text')

    def test_protocol_errors_and_nested_json_are_sanitized(self):
        for error in (BadStatusLine('private-server-text'), IncompleteRead(b'private-server-text')):
            with self.subTest(error=type(error).__name__):
                with patch.object(self.client._opener, 'open', side_effect=error):
                    self.assertEqual(self.client.discover()['status'], 'offline')
                    with self.assertRaisesRegex(ClientError,'^Runtime unavailable or invalid JSON$'):
                        self.client.chat('fixture','meterless/text')
        self.server.reply = (200,b'[' * 3000 + b'0' + b']' * 3000)
        self.assertEqual(self.client.discover()['status'], 'offline')
        with self.assertRaises(ClientError):
            self.client.chat('fixture','meterless/text')
        with patch('backend.providers.meterless_client.json.loads',side_effect=RecursionError('private-parser-text')):
            self.assertEqual(self.client.discover()['status'],'offline')

    def test_real_malformed_http_status_is_sanitized(self):
        # A real local socket response tests urllib's protocol parser boundary.
        import socketserver
        class Malformed(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.recv(8192)
                self.request.sendall(b'private-server-text\r\n\r\n')
        with socketserver.TCPServer(('127.0.0.1',0),Malformed) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                client=MeterlessClient('http://127.0.0.1:'+str(server.server_address[1]),'fixture')
                self.assertEqual(client.discover()['status'],'offline')
                with self.assertRaisesRegex(ClientError,'^Runtime unavailable or invalid JSON$'):
                    client.chat('fixture','meterless/text')
            finally:
                server.shutdown()
                thread.join()


class Configuration(unittest.TestCase):
    def test_normalization_all_pasted_suffixes(self):
        for suffix in ('','/','/v1','/v1/','/models','/chat/completions','/v1/models','/v1/chat/completions','/healthz'):
            for host, expected in [('localhost:8088','http://localhost:8088/v1'),('[::1]:8090','http://[::1]:8090/v1'),('host.example','https://host.example/v1'),('https://host.example:443','https://host.example:443/v1')]:
                with self.subTest(host=host,suffix=suffix):
                    self.assertEqual(normalize_base(host+suffix),expected)

    def test_unsafe_or_malformed_urls_rejected_without_echo(self):
        for value in ('http://remote.example','https://user:private@host.example','https://host.example?token=private','https://host.example/#private','http://localhost:99999','http://localhost:0','http://localhost/path','http://localhost/v1/v1','file:///tmp','http://localhost\nprivate','',None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as caught:
                    normalize_base(value)
                self.assertNotIn('private',str(caught.exception))

    def test_invalid_token_app_timeout_no_requests(self):
        for token in ('','rt-local','bad\ntoken'):
            with self.assertRaises(ValueError):
                MeterlessClient('localhost',token)
        for app in ('Upper','space app',''):
            with self.assertRaises(ValueError):
                MeterlessClient('localhost','fixture',app)
        for timeout in (0,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                MeterlessClient('localhost','fixture',discovery_timeout=timeout)

    def test_auto_detect_opt_in_and_loopback_only(self):
        with patch.object(MeterlessClient,'discover', return_value={'status':'offline','models':[]}) as discover:
            with self.assertRaises(ValueError):
                auto_detect('fixture')
            discover.assert_not_called()
        urls=[]
        def offline(client):
            urls.append(client.base_url)
            return {'status':'offline','models':[]}
        with patch.object(MeterlessClient,'discover',offline):
            self.assertIsNone(auto_detect('fixture',enabled=True)[0])
        self.assertEqual(len(urls),12)
        self.assertTrue(all(any(host in url for host in ('127.0.0.1','localhost','[::1]')) for url in urls))

    def test_auto_detect_keeps_first_unauthorized_hit(self):
        with patch.object(MeterlessClient,'discover', return_value={'status':'unauthorized','models':[]}) as discover:
            client,state=auto_detect('fixture',enabled=True)
            self.assertEqual(client.base_url,'http://127.0.0.1:8088/v1')
            self.assertEqual(state['status'],'unauthorized')
            self.assertEqual(discover.call_count,1)


if __name__ == '__main__':
    unittest.main()
