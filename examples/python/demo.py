"""Run from the repository root: python examples/python/demo.py tdx query funds."""
import json
import sys
from client import call, connection, dry_run, make_request


def main(args=None):
    _, profile, spec, body, execute = make_request(sys.argv[1:] if args is None else args)
    if dry_run(spec, body, execute):
        return 0
    url, token = connection(profile, spec['path'] == '/health')
    status, response = call(url, token, spec['method'], spec['path'], body)
    print('HTTP', status)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if status == 200 and response.get('ok') is not False else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        print('No automatic retry. Reconcile any submitted action in the official client.', file=sys.stderr)
        raise SystemExit(1)
