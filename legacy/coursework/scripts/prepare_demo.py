"""Keep the existing evidence before a fresh demonstration; never copy .env."""
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


def main():
    if not (os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')):
        raise SystemExit('API key missing. Set it in the local .env before the demo.')
    target = ROOT.parent / 'demo_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    target.mkdir(parents=True)
    for name in ['evidence', 'output']:
        if (ROOT/name).exists():
            shutil.copytree(ROOT/name, target/name)
    for name in ['ciphertexts.csv', 'admin_log.txt']:
        if (ROOT/name).is_file():
            shutil.copy2(ROOT/name, target/name)
    print(f'Previous evidence backed up to: {target}', flush=True)
    print('The local .env was not copied.', flush=True)


if __name__ == '__main__':
    main()
