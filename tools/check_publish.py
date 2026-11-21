"""Inspect Git's publishable files without printing secret values.

This is a local hygiene check, not a guarantee of platform-policy compliance.
Run before staging/committing; credentials must stay ignored.
"""
import json
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SUPPLIED_ARTIFACTS = {'archive/coursework/psycare_lab/original_server': '7149f7e524b70567a8d19360205105d7430dec5a9fa9557a4ab8bdf3b7ebf7dd'}
PATTERNS = {
    'Groq API key': rb'gsk_[A-Za-z0-9]{30,}',
    'OpenAI API key': rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}',
    'Google API key': rb'AIza[0-9A-Za-z_-]{30,}',
    'GitHub token': rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'AWS access key': rb'(?:AKIA|ASIA)[A-Z0-9]{16}',
    'Private key block': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
}


def main():
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT,
    ).decode('utf-8').split('\0')
    names = sorted(set(name for name in names if name))
    findings = []
    known_key = ''
    if (ROOT/'.env').is_file():
        for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('GEMINI_API_KEY='):
                known_key = line.split('=', 1)[1].strip().strip('\"\'')
    for name in names:
        path = ROOT/name
        if not path.is_file():
            continue
        if path.name == '.env' or path.suffix.lower() in {'.exe','.dll','.pem','.key'}:
            findings.append({'path':name,'reason':'private configuration/history or executable/key file'})
        raw = path.read_bytes()
        if raw.startswith((b'MZ', b'\x7fELF')) and SUPPLIED_ARTIFACTS.get(name) != hashlib.sha256(raw).hexdigest():
            findings.append({'path':name,'reason':'executable binary payload'})
        for label, pattern in PATTERNS.items():
            if re.search(pattern, raw):
                findings.append({'path':name,'reason':label})
        if known_key and known_key.encode() in raw:
            findings.append({'path':name,'reason':'locally configured Gemini key'})
    ignored = subprocess.run(['git','check-ignore','.env'],
                             cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    result = {'candidate_files':len(names),'findings':findings,
              'private_paths_ignored':'.env' in ignored,
              'attributed_supplied_artifacts':list(SUPPLIED_ARTIFACTS),
              'note':'Reviews candidate files and common secret patterns; does not certify GitHub policy compliance.'}
    print(json.dumps(result,indent=2))
    return 1 if findings or not result['private_paths_ignored'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
