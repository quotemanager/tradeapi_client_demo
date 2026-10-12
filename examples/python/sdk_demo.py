"""Use only the PUBLIC SDK supplied in an external runtime package."""
import importlib
import json
import os
from pathlib import Path
import sys
from client import dry_run, make_request


def main():
    product, _, spec, body, execute = make_request(sys.argv[1:])
    if dry_run(spec, body, execute):
        return 0
    home = os.environ.get('TRADEAPI_' + product.upper() + '_HOME')
    if not home:
        raise ValueError('Set TRADEAPI_' + product.upper() + '_HOME to your runtime package')
    sdk_path = Path(home) / 'sdk/python'
    if not sdk_path.is_dir():
        raise ValueError('Runtime package has no sdk/python directory')
    sys.path.insert(0, str(sdk_path))
    module = importlib.import_module('tradeapi_' + product)
    api = module.Client.from_directory(home)
    # The public call method covers query, orders, cancellations and saved results.
    # spec['path'] is a verified endpoint, not an account password or broker protocol.
    response = api.call(spec['method'], spec['path'], body)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response.get('ok') is not False else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as error:
        response = getattr(error, 'response', None)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, indent=2))
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        print('No automatic retry.', file=sys.stderr)
        raise SystemExit(1)
