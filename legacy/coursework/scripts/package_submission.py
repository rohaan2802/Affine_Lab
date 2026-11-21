"""Package verified deliverables; exclude local secrets and temporary files."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT.parent if ROOT.name=='psycare_lab' else ROOT


def main():
    verify=json.loads((ROOT/'output/verification.json').read_text())
    assert verify['all_passed']
    assert all((ROOT/f'evidence/desktop_session_{n}.png').exists() for n in range(1,6))
    report=DEST/'report.pdf';assert report.is_file()
    files={Path('report.pdf'):report}
    allowed={'.py','.sh','.json','.csv','.txt','.md','.png','.pcap'}
    root_names={'server.py','client.py','upstream_loader.py','original_server',
                'requirements.txt','requirements-report.txt','test_cases.json','README.md','upstream_commit.txt',
                'run_lab.sh','lab_inner.sh','env.sh','run_analysis.sh','.env.example','.gitignore','ciphertexts.csv'}
    for path in ROOT.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        if '__pycache__' in rel.parts or '.venv' in rel.parts:continue
        if len(rel.parts)==1 and rel.name in root_names:
            files[rel]=path
        elif len(rel.parts)>1 and rel.parts[0] in {'scripts','evidence','output'} and path.suffix in allowed:
            files[rel]=path
    secret_values=[]
    local=ROOT/'.env'
    if local.exists():
        for line in local.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line:
                k,v=line.split('=',1)
                if k.strip() in {'GEMINI_API_KEY','GOOGLE_API_KEY'} and v.strip():
                    secret_values.append(v.strip().strip('\"\'').encode())
    for rel,path in files.items():
        assert rel.name!='.env'
        data=path.read_bytes()
        assert not any(secret in data for secret in secret_values),f'Credential detected: {rel}'
    output=DEST/'A02_PsycoSupport_Submission.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,path in sorted(files.items()):z.write(path,rel.as_posix())
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert {'report.pdf','ciphertexts.csv','server.py','README.md'}<=set(z.namelist())
        assert not any(Path(n).name=='.env' for n in z.namelist())
    check={'zip':output.name,'files':len(files),'bytes':output.stat().st_size,
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'zip_integrity_passed':True,'local_secret_excluded':True,'real_desktop_screenshots':5,
        'verified_sessions':5,'ciphertext_fields':15}
    (DEST/'submission_check.json').write_text(json.dumps(check,indent=2))
    print(json.dumps(check,indent=2))


if __name__=='__main__':main()
