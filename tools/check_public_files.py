"""Check Git upload candidates without printing possible credential values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_DIRS = {'build', 'runtime', 'release', 'captures', 'logs', '.secrets', '.tools', 'node_modules', 'target', 'obj', 'bin'}
FORBIDDEN_EXTENSIONS = {'.dll', '.exe', '.pfx', '.p12', '.pem', '.key', '.dpapi', '.log', '.jsonl', '.zip', '.7z'}
PATTERN = re.compile(r'"(?:password|trade_password|auth_key|private_key|api_key|token)"\s*:\s*"([^"]+)"', re.I)


def check():
    process = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    files = sorted(set(p for p in process.stdout.decode('utf-8').split('\0') if p))
    failures = []
    for file in files:
        path = Path(file)
        if (FORBIDDEN_DIRS.intersection(path.parts) or path.suffix.lower() in FORBIDDEN_EXTENSIONS
                or file.endswith('.local.json') or 'account-auth' in path.name
                or 'service-token' in path.name or path.name in ('system.uid','.did','.iid')):
            failures.append(file + ': private/generated file must not be uploaded')
            continue
        absolute = ROOT / path
        if path.suffix.lower() in ('.md','.json','.py','.js','.cs','.java','.go','.cpp','.yml','.txt') and absolute.exists():
            text = absolute.read_text(encoding='utf-8-sig')
            for match in PATTERN.finditer(text):
                value = match.group(1)
                if not (value.startswith(('YOUR_', '<', 'PLACEHOLDER', 'test_')) or value in ('token','')):
                    failures.append(file + ': possible credential literal; inspect locally')
                    break
    for failure in failures:
        print(failure, file=sys.stderr)
    if not files:
        raise ValueError('No Git upload candidates found')
    print(f'Checked {len(files)} Git upload candidates; {len(failures)} warnings. No secret values printed.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(check())
