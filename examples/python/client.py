"""Public local-HTTP consumer. No broker implementation or automatic retry."""
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
MAX_RESPONSE = 16 * 1024 * 1024


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 65536:
        raise ValueError('Parameter file exceeds 64 KiB')
    value = json.loads(path.read_text(encoding='utf-8-sig'),
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    return value


def make_request(args):
    execute = '--execute' in args
    args = [a for a in args if a != '--execute']
    if not 1 <= len(args) <= 3:
        raise ValueError('Usage: demo PRODUCT [COMMAND [VALUE]] [--execute]; PRODUCT = tdx | ths')
    product, command = args[0], args[1] if len(args) > 1 else 'query'
    value = args[2] if len(args) > 2 else ''
    contract = read_json(ROOT / 'config/api-contract.json')
    if product not in contract:
        raise ValueError('PRODUCT must be tdx or ths')
    profile = contract[product]
    if command == 'query':
        category = value or 'funds'
        if category not in profile['queries']:
            raise ValueError('Unsupported query for this product')
        spec = dict(method='GET', path=profile['queries'][category], input='none', live=False)
    else:
        if command not in profile['commands']:
            raise ValueError('Unsupported command for this product')
        spec = dict(profile['commands'][command])
    body = None
    if spec['input'] == 'file':
        if not value:
            raise ValueError('Pass a user-created JSON parameter file')
        body = read_json(value)
    elif spec['input'].startswith('id-'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
            raise ValueError('Pass an existing request/preview/action ID')
        if spec['input'] == 'id-path':
            spec['path'] += value
        else:
            body = {'preview_id': value}
    elif value and command != 'query':
        raise ValueError('This command takes no VALUE')
    return product, profile, spec, body, execute


def connection(profile, health=False):
    url = os.environ.get(profile['url_env'], profile['base_url']).rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
            or not parsed.port or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('URL must be http://127.0.0.1:<port>')
    token = os.environ.get(profile['token_env'], '').strip()
    if not health and not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', token):
        raise ValueError('Set ' + profile['token_env'] + ' locally; never commit your token')
    return url, token


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def call(url, token, method, path, body=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(url + path, method=method, headers=headers,
                      data=None if body is None else json.dumps(body, allow_nan=False).encode('utf-8'))
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=90)
    except HTTPError as error:
        response = error
    with response:
        status, raw = response.status, response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError('Response exceeds 16 MiB; do not resubmit')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Response is not a JSON object; do not resubmit')
    return status, value


def dry_run(spec, body, execute):
    if spec['live'] and not execute:
        print(json.dumps({'dry_run': True, 'method': spec['method'], 'path': spec['path'],
                          'body': body, 'note': 'Nothing sent. --execute submits ONE REAL action.'},
                         ensure_ascii=False, indent=2))
        return True
    return False
