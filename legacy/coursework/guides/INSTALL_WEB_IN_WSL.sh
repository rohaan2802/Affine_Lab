#!/bin/bash
# Run this yourself inside Ubuntu when the reviewed WSL update can proceed.
set -euo pipefail
SOURCE='/mnt/c/Users/CodeTech/Desktop/A#02'
DEST='/home/codetech/A02_PsycoSupport'
LAB="$DEST/psycare_lab"
[ "$(readlink -f "$DEST")" = '/home/codetech/A02_PsycoSupport' ] || exit 1
test -x "$LAB/.venv/bin/python"
python3 - <<'PY'
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
source=Path('/mnt/c/Users/CodeTech/Desktop/A#02')
root=Path('/home/codetech/A02_PsycoSupport');lab=root/'psycare_lab'
backup=root/'web_setup_backups'/datetime.now().strftime('%Y%m%d_%H%M%S')
names=['web_demo.py','run_web_demo.sh','WEB_DEMO_GUIDE.txt','tests/test_web_demo.py']
names += [str(p.relative_to(source/'psycare_lab')) for p in (source/'psycare_lab/web_ui').rglob('*') if p.is_file()]
for name in names:
    old=lab/name
    if old.exists():
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,target)
    old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/'psycare_lab'/name,old)
(lab/'run_web_demo.sh').chmod(0o755)
shutil.copytree(source/'Pre_Demo',root/'pre_demo',dirs_exist_ok=True)
for path in (source/'Pre_Demo').rglob('*'):
    if path.is_file():assert hashlib.sha256(path.read_bytes()).digest()==hashlib.sha256((root/'pre_demo'/path.relative_to(source/'Pre_Demo')).read_bytes()).digest()
tasks=lab/'.vscode/tasks.json';data=json.loads(tasks.read_text());label='Demo: Live web UI (Gemini)'
data['tasks']=[t for t in data['tasks'] if t['label']!=label]
data['tasks'].append({'label':label,'type':'process','command':'/mnt/c/Windows/System32/wsl.exe',
 'args':['-d','Ubuntu','-u','root','--','bash','${workspaceFolder}/run_web_demo.sh'],
 'options':{'cwd':'${workspaceFolder}'},'problemMatcher':[]})
tasks.write_text(json.dumps(data,indent=2))
print('Web files and complete recorded presentation copied. Local .env was not changed.')
PY
cd "$LAB"
source env.sh
bash -n run_web_demo.sh
"$LAB_PYTHON" -m unittest discover -s tests -p test_web_demo.py -v
printf '\nLocal HTTP tests passed. Next, start the live web launcher and verify a real Gemini case.\n'
printf 'wsl.exe -d Ubuntu -u root -- bash /home/codetech/A02_PsycoSupport/psycare_lab/run_web_demo.sh\n'
printf 'Browser: http://127.0.0.1:8765\n'
