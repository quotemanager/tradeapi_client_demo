"""Offline and mock-server checks. NEVER contacts a broker or running local API."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples/python'))
import client


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.handle_call()

    def do_POST(self):
        self.handle_call()

    def handle_call(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        body = json.loads(raw) if raw else None
        self.server.calls.append((self.command, self.path, body, self.headers.get('Authorization')))
        status = self.server.response_status
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Location', '/must-not-be-followed')
        self.end_headers()
        response = self.server.response_body
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))


def runners():
    result = {'python': [sys.executable, 'examples/python/demo.py']}
    node = os.environ.get('DEMO_NODE') or shutil.which('node')
    if node:
        result['nodejs'] = [node, 'examples/nodejs/demo.js']
    exe = ROOT / 'build/cpp/Release/tradeapi_client_demo.exe'
    if exe.exists():
        result['cpp'] = [str(exe)]
    csharp = ROOT / 'build/csharp/TradeApiClientDemo.dll'
    dotnet = os.environ.get('DEMO_DOTNET') or shutil.which('dotnet')
    if csharp.exists() and dotnet:
        result['csharp'] = [dotnet, str(csharp)]
    java = os.environ.get('DEMO_JAVA') or shutil.which('java')
    jar = ROOT / 'examples/java/target/tradeapi-client-demo-1.0.0.jar'
    if jar.exists() and java:
        result['java'] = [java, '-jar', str(jar)]
    go_exe = ROOT / ('build/go/tradeapi-client-demo.exe' if os.name == 'nt' else 'build/go/tradeapi-client-demo')
    if go_exe.exists():
        result['go'] = [str(go_exe)]
    return result


class ExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.executables = runners()
        print('Mock-tested runners:', ', '.join(cls.executables))
        required = {x for x in os.environ.get('DEMO_REQUIRED_RUNNERS', '').split(',') if x}
        if required - cls.executables.keys():
            cls.server.shutdown(); cls.server.server_close()
            raise AssertionError('Missing required runners: ' + str(required - cls.executables.keys()))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.calls = []
        self.server.response_status = 200
        self.server.response_body = {'ok': True, 'result': {'message': '模拟返回', 'records': []}}
        self.token = 'test_' + 'A' * 40  # Dummy mock token, not a real API secret.
        self.env = dict(os.environ, TRADEAPI_TDX_TOKEN=self.token, TRADEAPI_THS_TOKEN=self.token,
                        TRADEAPI_TDX_URL=f'http://127.0.0.1:{self.server.server_port}',
                        TRADEAPI_THS_URL=f'http://127.0.0.1:{self.server.server_port}')

    def invoke(self, runner, *args):
        return subprocess.run(self.executables[runner] + list(args), cwd=ROOT, env=self.env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)

    def test_query_endpoint_mapping_all_products(self):
        contract = client.read_json(ROOT / 'config/api-contract.json')
        for language in self.executables:
            for product, profile in contract.items():
                for category, path in profile['queries'].items():
                    with self.subTest(language=language, product=product, category=category):
                        self.server.calls.clear()
                        result = self.invoke(language, product, 'query', category)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(self.server.calls, [('GET', path, None, 'Bearer ' + self.token)])
                        # JSON may escape non-ASCII text; validate decoded data, not typography.
                        decoded = json.loads(result.stdout.split('\n', 1)[1])
                        self.assertEqual(decoded['result']['message'], '模拟返回')

    def test_default_is_funds_status_and_health(self):
        for language in self.executables:
            for product, status_path in (('tdx','/v1/status'), ('ths','/session/status')):
                for command, path in (([], '/v1/queries/funds' if product=='tdx' else '/query/funds'),
                                      (['status'],status_path), (['health'],'/health')):
                    with self.subTest(language=language, product=product, command=command):
                        self.server.calls.clear()
                        result = self.invoke(language, product, *command)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(len(self.server.calls), 1)
                        self.assertEqual(self.server.calls[0][1], path)

    def test_missing_token_remote_url_and_invalid_product_send_nothing(self):
        for language in self.executables:
            with self.subTest(language=language):
                self.server.calls.clear()
                self.assertNotEqual(self.invoke(language, 'invalid', 'query', 'funds').returncode, 0)
                self.assertNotEqual(self.invoke(language, 'ths', 'query', 'shareholders').returncode, 0)
                self.env['TRADEAPI_TDX_TOKEN'] = ''
                self.assertNotEqual(self.invoke(language, 'tdx').returncode, 0)
                self.env['TRADEAPI_TDX_TOKEN'] = self.token
                self.env['TRADEAPI_TDX_URL'] = 'http://example.invalid:80'
                self.assertNotEqual(self.invoke(language, 'tdx').returncode, 0)
                self.env['TRADEAPI_TDX_URL'] = f'http://127.0.0.1:{self.server.server_port}'
                self.assertEqual(self.server.calls, [])

    def test_real_action_dry_run_and_one_mock_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            for language in self.executables:
                for command, body, path in (
                    ('order', {'request_id':'mock-request-0001','account_variant':'margin','side':'finance_buy',
                               'security_code':'000001','price':'17.72','quantity':100}, '/v1/orders'),
                    ('cancel', {'request_id':'mock-cancel-0001','account_variant':'margin','order_id':'0005'}, '/v1/cancellations')):
                    with self.subTest(language=language, command=command):
                        file = Path(directory) / 'action.local.json'
                        file.write_text(json.dumps(body), encoding='utf-8-sig')
                        self.server.calls.clear()
                        dry = self.invoke(language, 'tdx', command, str(file))
                        self.assertEqual(dry.returncode, 0, dry.stderr)
                        self.assertIn('dry_run', dry.stdout)
                        self.assertEqual(self.server.calls, [])
                        live = self.invoke(language, 'tdx', command, str(file), '--execute')
                        self.assertEqual(live.returncode, 0, live.stderr)
                        self.assertEqual(self.server.calls, [('POST', path, body, 'Bearer '+self.token)])

    def test_ths_preview_poll_submit_and_result(self):
        with tempfile.TemporaryDirectory() as directory:
            for language in self.executables:
                for kind, body, preview_path, submit_path in (
                    ('order', {'side':'buy','security_code':'000001','price':'17.72','quantity':100,
                               'credit_type':'financing_buy'}, '/orders/preview', '/orders/submit'),
                    ('cancel', {'order_id':'0005'}, '/cancels/preview', '/cancels/submit')):
                    with self.subTest(language=language, kind=kind):
                        file = Path(directory) / 'preview.local.json'; file.write_text(json.dumps(body), encoding='utf-8')
                        self.server.calls.clear()
                        result = self.invoke(language, 'ths', 'preview-'+kind, str(file))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(self.server.calls[0][:3], ('POST',preview_path,body))
                        self.server.calls.clear()
                        poll = self.invoke(language, 'ths', 'poll-'+kind, 'mock-preview-0001')
                        self.assertEqual(poll.returncode, 0, poll.stderr)
                        self.assertEqual(self.server.calls[0][:3], ('POST',preview_path,{'preview_id':'mock-preview-0001'}))
                        self.server.calls.clear()
                        dry = self.invoke(language, 'ths', 'submit-'+kind, 'mock-preview-0001')
                        self.assertEqual(dry.returncode, 0, dry.stderr)
                        self.assertEqual(self.server.calls, [])
                        live = self.invoke(language, 'ths', 'submit-'+kind, 'mock-preview-0001', '--execute')
                        self.assertEqual(live.returncode, 0, live.stderr)
                        self.assertEqual(self.server.calls[0][:3], ('POST',submit_path,{'preview_id':'mock-preview-0001'}))
                        self.assertEqual(len(self.server.calls), 1)
                self.server.calls.clear()
                self.assertEqual(self.invoke(language, 'ths', 'result', 'mock-preview-0001').returncode, 0)
                self.assertEqual(self.server.calls[0][1], '/actions/mock-preview-0001')
                self.server.calls.clear()
                self.assertEqual(self.invoke(language, 'tdx', 'result', 'mock-request-0001').returncode, 0)
                self.assertEqual(self.server.calls[0][1], '/v1/actions/mock-request-0001')

    def test_errors_and_redirects_are_not_retried(self):
        for language in self.executables:
            for status in (401, 409, 500, 302):
                with self.subTest(language=language, status=status):
                    self.server.calls.clear()
                    self.server.response_status = status
                    self.server.response_body = {'ok':False,'error':'mock error'}
                    result = self.invoke(language, 'ths', 'submit-order', 'mock-preview-0001', '--execute')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(len(self.server.calls), 1)
                    self.assertEqual(self.server.calls[0][1], '/orders/submit')
            self.server.response_status = 200

    def test_dll_buffer_copy_keeps_http_error_without_resubmit(self):
        dll = ROOT / 'build/cpp/Release/mock_tradeapi.dll'
        if not dll.exists() or os.name != 'nt':
            self.skipTest('Optional Windows mock DLL not built')
        for language in ('python', 'cpp', 'csharp'):
            if language not in self.executables:
                continue
            for product in ('tdx', 'ths'):
                with self.subTest(language=language, product=product), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    for arch, source in (('x64',dll), ('x86',ROOT/'build/cpp-x86/Release/mock_tradeapi.dll')):
                        if source.exists():
                            destination = home/'build'/arch/('tradeapi_'+product+'.dll')
                            destination.parent.mkdir(parents=True)
                            shutil.copyfile(source, destination)
                    self.env['TRADEAPI_'+product.upper()+'_HOME'] = str(home)
                    command = ([sys.executable,'examples/python/dll_demo.py'] if language=='python'
                               else self.executables[language])
                    args = [product, 'query', 'funds'] + ([] if language=='python' else ['--dll'])
                    result = subprocess.run(command + args, cwd=ROOT, env=self.env, capture_output=True,
                                            text=True, encoding='utf-8', errors='strict', timeout=15)
                    self.assertEqual(result.returncode, 1, result.stderr)  # Original HTTP409, even after cache copy.
                    self.assertTrue(result.stdout, result.stderr)
                    self.assertEqual(result.stdout.splitlines()[0], 'HTTP 409')
                    decoded = json.loads(result.stdout.split('\n',1)[1])
                    self.assertEqual(decoded['request_count'], 1)
                    self.assertEqual(len(decoded['padding']), 70000)

    def test_public_sdk_consumer_with_external_mock_package(self):
        source = '''class Client:
    @classmethod
    def from_directory(cls, home):
        return cls()
    def call(self, method, path, body=None):
        return {"ok": True, "method": method, "path": path, "body": body}
'''
        for product in ('tdx', 'ths'):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as directory:
                sdk = Path(directory)/'sdk/python'/('tradeapi_'+product)
                sdk.mkdir(parents=True)
                (sdk/'__init__.py').write_text(source, encoding='utf-8')
                self.env['TRADEAPI_'+product.upper()+'_HOME'] = directory
                result = subprocess.run([sys.executable,'examples/python/sdk_demo.py',product,'query','funds'],
                                        cwd=ROOT, env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['path'], '/v1/queries/funds' if product=='tdx' else '/query/funds')


class RepositoryTests(unittest.TestCase):
    def test_document_links(self):
        for file in ROOT.rglob('*.md'):
            if any(part in ('build','target','.git') for part in file.relative_to(ROOT).parts):
                continue
            text = file.read_text(encoding='utf-8')
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' in link or link.startswith('#'):
                    continue
                target = link.split('#')[0]
                self.assertTrue((file.parent / target).exists(), f'{file}: {link}')

    def test_templates_and_contract_are_public(self):
        for path in (ROOT/'config').glob('*.example.json'):
            value = client.read_json(path)
            self.assertNotIn('token', value)
            self.assertNotIn('password', value)
            self.assertTrue('YOUR_SECURITY_CODE' == value.get('security_code') or 'YOUR_ORDER_ID' == value.get('order_id'))
        self.assertFalse((ROOT / 'src').exists())
        self.assertTrue((ROOT / 'assets/telegram-qr.png').exists())

    def test_python_invalid_json_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad.local.json'
            for value in ('[]', 'null', '{"price":NaN}'):
                path.write_text(value, encoding='utf-8')
                with self.assertRaises(ValueError):
                    client.make_request(['tdx','order',str(path)])
        for value in ('id/other','../health','id?token=secret'):
            with self.assertRaises(ValueError):
                client.make_request(['ths','submit-order',value])


if __name__ == '__main__':
    unittest.main()
