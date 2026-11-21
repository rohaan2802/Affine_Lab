"""Build a self-contained, offline viewer of a verified pre-recorded lab run.

Preparation tool: run with Windows Python and --lab pointing to the native
WSL project. Viewing the resulting index.html needs no Python/API/server.
"""
import argparse
import csv
import hashlib
import html
import json
import shutil
from pathlib import Path
from PIL import Image

H=lambda x:html.escape(str(x))
IMAGE_ROOT=Path('.')


def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+H(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+H(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def code(text):return '<pre>'+H(text)+'</pre>'
def link(path,label):return '<a href="'+H(path)+'">'+H(label)+'</a>'
def section(name,title,body):return '<section id="'+name+'"><h2>'+H(title)+'</h2>'+body+'</section>'
def image(path,label):
    with Image.open(IMAGE_ROOT/path) as picture:width,height=picture.size
    return '<figure><a href="'+path+'"><img loading="lazy" width="'+str(width)+'" height="'+str(height)+'" src="'+path+'" alt="'+H(label)+'"></a><figcaption>'+H(label)+'</figcaption></figure>'


def build(lab,out):
    global IMAGE_ROOT
    IMAGE_ROOT=out
    verification=json.loads((lab/'output/verification.json').read_text())
    assert verification['all_passed']
    assert hashlib.sha256((lab/'evidence/capture.pcap').read_bytes()).hexdigest()==verification['pcap_sha256']
    out.mkdir(parents=True,exist_ok=True)
    for folder in ['output','source','evidence','screenshots']:(out/folder).mkdir(exist_ok=True)
    for path in (lab/'output').iterdir():
        if path.is_file():shutil.copy2(path,out/'output'/path.name)
    for path in (lab/'evidence').iterdir():
        if path.is_file() and path.suffix in {'.txt','.tsv','.pcap'}:shutil.copy2(path,out/'evidence'/path.name)
    shutil.copy2(lab/'evidence/capture.pcap',out/'evidence/pre_demo_capture.pcap')
    shutil.copy2(lab/'ciphertexts.csv',out/'ciphertexts.csv')
    for name in ['server.py','client.py','upstream_loader.py','original_server','test_cases.json',
                 'upstream_commit.txt','README.md','DEMO_GUIDE.txt','run_demo.sh','run_lab.sh',
                 'run_analysis.sh','lab_inner.sh','env.sh','requirements.txt']:
        if (lab/name).is_file():shutil.copy2(lab/name,out/'source'/name)
    shutil.copytree(lab/'scripts',out/'source/scripts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    cases=json.loads((lab/'test_cases.json').read_text())
    keys=json.loads((lab/'output/recovered_keys.json').read_text())
    sessions=json.loads((lab/'output/captured_sessions.json').read_text())
    plaintext=list(csv.DictReader((lab/'output/decrypted.csv').open(encoding='utf-8')))
    backend=json.loads((lab/'output/backend.json').read_text())
    log=(lab/'output/run_log.txt').read_text()
    proof=(lab/'output/key_recovery_proof.txt').read_text()
    run_time=log.splitlines()[0].removeprefix('Actual run time: ')
    body=[]
    body.append(section('overview','1. Saved pre-demo overview',
        '<p class="notice">PRE-RECORDED, VERIFIED LAB RESULTS · This page displays saved evidence. It does not run a server or call an API.</p>'+
        '<div class="cards">'+''.join('<article><strong>'+H(a)+'</strong><span>'+H(b)+'</span></article>' for a,b in [('5','complete sessions'),('15','ciphertext fields'),('5 / 5','keys and plaintext verified'),('PASS','independent checks')])+'</div>'+
        table(['Run detail','Saved value'],[['Model',backend['model']],['Recorded run',run_time],['Host','rohaan-psylab / WSL Ubuntu'],['Capture scope','lo · 127.0.0.1 · TCP port 9999'],['Original run network','Gemini over HTTPS; instructor-approved cloud exception'],['Viewing this pack','Offline; no credentials or API calls required']])+
        '<h3>What the project demonstrates</h3><p>Five fictional concerns were encrypted and sent through the instructor’s local TCP protocol. The replies came from Gemini, were encrypted on the local server, and were captured on loopback. Frequency analysis recovered each Affine key; independent checks confirmed the inputs, replies and re-encryption.</p>'+
        '<p>Client → encrypted local TCP → server → Gemini HTTPS → encrypted local TCP reply. No API key is included in this evidence pack.</p>'+
        '<p>'+link('SHOW_ORDER.txt','Roman Urdu presentation order')+' · '+link('evidence/pre_demo_capture.pcap','Open raw capture')+' · '+link('demo_report.pdf','Printable evidence report')+'</p>'))
    body.append(section('tests','2. All five synthetic test cases',table(['Case','Username','Mood','Concern'],[[i,c['username'],c['mood'],c['concern']] for i,c in enumerate(cases,1)])+
        '<p>The scenarios cover exam anxiety, loneliness, work/study balance, a family disagreement and a group-project deadline. These are synthetic data, not patient records.</p>'))
    packets='<p>These JSON values were reassembled from the PCAP. Requests use UTF-8 nibble armor before Affine encryption; replies are directly encrypted uppercase English. Cleartext mood selects a different key schedule per session.</p>'
    for s in sessions:
        packets+='<details><summary>Session '+str(s['session'])+' · TCP stream '+str(s['tcp_stream'])+'</summary><h3>Captured client → server</h3>'+code(json.dumps(s['request'],indent=2))+'<h3>Captured server → client</h3>'+code(json.dumps(s['response'],indent=2))+'<p>'+link(f"evidence/session_{s['session']}_follow_tcp.txt",'Actual TShark Follow TCP Stream export')+'</p></details>'
    body.append(section('packets','3. Captured ciphertext and raw evidence',packets+'<p>'+link('ciphertexts.csv','All 15 exact ciphertext fields (CSV)')+'</p>'))
    body.append(section('keys','4. Recovered Affine keys and mathematical proof',
        '<p>Plaintext is readable text; ciphertext is its encrypted form. An Affine key is the pair <b>(a, b)</b>. With A=0 … Z=25:</p>'+code('Encryption: C = (a·P + b) mod 26\nDecryption: P = inverse(a)·(C − b) mod 26\ngcd(a,26)=1; 12 valid multipliers × 26 shifts = 312 candidates.')+
        table(['Case','a','b','a inverse','Best χ²','Next-best χ²','Re-encryption'],[[k['session'],k['a'],k['b'],k['a_inverse'],f"{k['chi_squared']:.2f}",f"{k['runner_up_chi_squared']:.2f}",'MATCH'] for k in keys])+
        '<p>The ciphertext-only attack scores all valid keys by English-frequency chi-squared, separately for each session. It does not import the server or use the cleartext mood schedule. A separate verification script checks those only after recovery.</p>'+
        '<details><summary>Full calculation for every session</summary>'+code(proof)+'</details>'))
    results=''
    for i,c in enumerate(cases,1):
        fields={r['field']:r['plaintext'] for r in plaintext if int(r['session'])==i}
        results+='<article class="result"><h3>Session '+str(i)+' — fully recovered text</h3><p><b>Username:</b> '+H(fields['username_enc'])+'</p><p><b>Concern:</b> '+H(fields['message_enc'])+'</p><p class="reply">'+H(fields['ciphertext'])+'</p><span class="pass">Exact input / client-reply match verified</span></article>'
    body.append(section('results','5. Complete decrypted sessions',results+'<p>'+link('output/decrypted_sessions.txt','All decrypted text')+' · '+link('output/decrypted.csv','Decryption CSV')+'</p>'))
    charts='<p>Each ciphertext chart is compared with English separately, since moods use different substitutions. Client armor is not treated as ordinary English.</p>'
    for i in range(1,6):charts+=image(f'output/session_{i}_frequency.png',f'Session {i}: ciphertext frequency versus English')
    charts+=image('output/decrypted_vs_english.png','Combined recovered English compared with the reference')
    body.append(section('charts','6. Frequency charts and full tables',charts+'<p>'+link('output/frequency_table.csv','Full 130-row frequency table')+'</p>'))
    screenshots=''
    for p in sorted((out/'screenshots').glob('*.png')):screenshots+=image('screenshots/'+p.name,p.stem.replace('_',' '))
    if not screenshots:screenshots='<p>Desktop screenshots are added during the final evidence pass. Raw capture and verified results above are already available.</p>'
    edit_record=lab.parent/'project_notes/04_SCREENSHOT_EDIT_RECORD.txt'
    screenshot_note=('Desktop screenshot taskbar display dates were edited to 22/10/2026 under the current assignment permission. All non-date pixels and actual packet/log timestamps remain unchanged; see the accompanying screenshot edit record.'
                     if edit_record.exists() else 'Unmodified desktop captures retain their actual date and taskbar.')
    body.append(section('screenshots','7. Actual desktop screenshots','<p>'+screenshot_note+'</p>'+screenshots))
    checks=table(['Case','Recovered key','Username','Concern','Server reply','Re-encryption'],[[c['session'],*['PASS' if c[x] else 'FAIL' for x in ['key_matches_original_after_recovery','username_matches_input','concern_matches_input','response_matches_client','reencryption_matches']]] for c in verification['session_checks']])
    body.append(section('verification','8. Independent verification',
        '<p class="notice pass">ALL FIVE SESSIONS PASSED</p>'+checks+table(['Artifact','SHA-256'],[['Raw PCAP',verification['pcap_sha256']],['Provided original server',verification['original_server_sha256']]])+
        '<p>The capture is the primary record. Screenshots support it; the verification separately compares recovered values with the original implementation and recorded client output.</p>'+code((lab/'output/analysis_log.txt').read_text())+'<p>'+link('output/verification.json','Machine-readable verification')+'</p>'))
    logs=''
    for filename in ['run_log.txt','server.log','tcpdump.log','client_output.txt','analysis_log.txt']:
        logs+='<details><summary>'+H(filename)+'</summary>'+code((lab/'output'/filename).read_text())+'</details>'
    body.append(section('logs','9. Actual run and capture logs',logs))
    sources=''
    for name in ['client.py','server.py','upstream_loader.py','scripts/extract_tcp.py','scripts/analyze.py','scripts/verify_results.py']:
        sources+='<details><summary>'+H(name)+'</summary>'+code((lab/name).read_text())+'</details>'
    body.append(section('source','10. Code and security discussion',
        '<p>Source is included for inspection. This viewer never executes it. The original cipher/protocol functions are loaded from the supplied Linux executable; the adapter routes its model call to Gemini.</p>'+sources+
        '<h3>Why the wrapper fails</h3><p>Affine substitution preserves language patterns and has only 312 keys. Mood is sent in clear and deterministically reveals the key schedule. Encoding input bytes as A–P pairs does not add cryptographic security. Repeated words/names create clues; no invented fixed disclaimer is added.</p>'+
        '<h3>Better alternatives</h3><p>Use a UNIX-domain socket with owner-only access and peer credentials for local access control, or authenticated TLS 1.3 for encrypted TCP. A self-signed certificate must be explicitly trusted/pinned; do not disable verification. Protect plaintext logs separately.</p>'+
        '<p>Gemini makes the original run cloud-assisted. This saved pack itself works offline. Model-generated replies are synthetic lab output, not medical advice.</p>'+
        '<p>References: <a href="https://github.com/maadilrehman/PsycoSupport">Instructor source</a> · <a href="https://ai.google.dev/api/generate-content">Gemini API</a> · <a href="https://www.wireshark.org/docs/man-pages/tshark.html">TShark</a> · <a href="https://www.rfc-editor.org/info/rfc9846">TLS 1.3</a>. English frequencies: Lewand, Cryptological Mathematics (2000). AI assisted preparation; artifacts come from real controlled runs.</p>'))
    nav=''.join('<a href="#'+a+'">'+b+'</a>' for a,b in [('overview','Overview'),('tests','Test cases'),('packets','Ciphertexts'),('keys','Keys & proof'),('results','Decrypted'),('charts','Charts'),('screenshots','Screenshots'),('verification','Verification'),('logs','Logs'),('source','Code')])
    css='''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:88px}body{margin:0;background:#eef2f5;color:#202f3c;font:17px/1.6 system-ui,Arial,sans-serif}header{background:#173c52;color:white;padding:30px max(24px,calc((100vw - 1180px)/2))}header h1{margin:0;font-size:32px}header p{margin:6px 0}nav{position:sticky;top:0;z-index:3;display:flex;flex-wrap:wrap;gap:4px;padding:10px 20px;background:#102d40}nav a{color:#fff;text-decoration:none;font-weight:600;padding:7px 11px;border-radius:5px}nav a:hover,nav a:focus{background:#31637b}main{max-width:1220px;margin:auto;padding:24px}section{background:white;padding:28px;margin:0 0 24px;border:1px solid #d4dee5;border-radius:10px}h2{font-size:26px;margin:0 0 18px;color:#173c52}h3{font-size:20px}a{color:#176480}pre{background:#102d40;color:#edf6fb;font:14px/1.6 Consolas,monospace;padding:18px;border-radius:7px;white-space:pre-wrap;overflow-wrap:anywhere}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;margin:18px 0;font-size:15px}th,td{text-align:left;padding:12px;border:1px solid #d3dfe6;vertical-align:top;overflow-wrap:anywhere}th{background:#e8f0f5}td:last-child{word-break:break-word}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.cards article{background:#edf5f6;border:1px solid #c8dde1;border-radius:8px;padding:16px}.cards strong{display:block;font-size:30px;color:#17604e}.cards span{font-size:15px}.notice{padding:14px 18px;border-left:5px solid #2f806b;background:#eaf6f0;font-weight:600}.pass{color:#17604e;font-weight:700}.result{border-bottom:1px solid #d6e0e6;padding:12px 0 25px}.reply{background:#f2f6f9;padding:18px;line-height:1.8}details{border:1px solid #cedbe4;border-radius:6px;margin:14px 0;padding:12px}summary{cursor:pointer;font-weight:650;color:#173c52}figure{margin:22px 0}img{width:100%;height:auto;border:1px solid #d4dfe5;border-radius:5px}figcaption{font-size:14px;text-align:center;color:#50616e}footer{max-width:1180px;margin:auto;padding:20px;font-size:14px}button{padding:10px 15px;border:0;border-radius:5px;background:#d4e8ee;color:#102d40;cursor:pointer;font-size:15px}body.focus-mode section{display:none}body.focus-mode section:target{display:block}body.focus-mode section:target h2{margin-bottom:18px}@media(max-width:750px){.cards{grid-template-columns:repeat(2,1fr)}main{padding:10px}section{padding:18px}nav{position:static}header h1{font-size:25px}}@page{size:A4;margin:16mm}@media print{body{background:white;font:10pt/1.45 Arial}header{padding:0;color:#173c52;background:white}header h1{font-size:22pt}nav,button{display:none}main{padding:0}section,body.focus-mode section{display:block!important;border:0;padding:0;margin:20px 0;break-before:page}section:first-child{break-before:auto}h2{font-size:18pt}h3{font-size:12pt}table{font-size:8pt}th,td{padding:5px}pre{font:7.5pt/1.4 Consolas;color:#182e3b;background:#f0f4f6;padding:8px}details{border:0;padding:0}summary{font-size:10pt}figure{break-inside:avoid;margin:10px 0}figure img{max-height:205mm;object-fit:contain}figcaption{font-size:8pt}.cards strong{font-size:20pt}.cards span{font-size:9pt}.notice{font-size:10pt}.reply{padding:10px}footer{padding:0}.result{break-inside:avoid}}'''
    document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PsycoSupport — Saved Pre-Demo</title><style>'+css+'</style></head><body><header><h1>PsycoSupport · Saved Pre-Demo</h1><p>Rohaan · Information Security · Verified evidence from '+H(run_time)+'</p><button onclick="document.body.classList.toggle(\'focus-mode\');if(!location.hash)location.hash=\'overview\'">Toggle one-section presentation</button></header><nav>'+nav+'</nav><main>'+''.join(body)+'</main><footer>Saved demonstration · Synthetic data only · No API key included · Raw capture and source retained</footer></body></html>'
    (out/'index.html').write_text(document,encoding='utf-8')
    guide='''SAVED PRE-DEMO - NOTHING TO RUN DURING PRESENTATION
=================================================
Open index.html in a browser. All data is local; no API, server, WSL terminal
or internet connection is required to VIEW these recorded results.
This is a saved demonstration, not a claim that the application is running live.

SHOW ORDER (5-8 MINUTES)
1. Overview: model, actual run time, five cases and PASS status.
2. Test cases: five synthetic concerns and moods.
3. Ciphertexts: expand a session; show encrypted request/reply.
4. Keys & proof: explain (a,b), inverse and the 312-key search.
5. Decrypted: compare original concern with recovered message and reply.
6. Charts: letter frequencies, English reference and recovered English.
7. Screenshots: actual desktop, taskbar and five Wireshark streams.
8. Verification: all five independent checks; show final analysis PASS.
9. Logs: actual run, model backend and tcpdump zero-drop result.
10. Code: client, Gemini adapter, extraction, analysis and independent checks.

Click 'Toggle one-section presentation' to show only the selected section.
Click it again to return to the full page. Use the top navigation to move.
Click a screenshot/chart to open its full-size original PNG.

IF ASKED FOR PRIMARY EVIDENCE
Open evidence/pre_demo_capture.pcap in Windows Wireshark.
Filter: tcp.port == 9999
Follow -> TCP Stream; inspect streams 0 through 4.
No new capture, model request or command is needed.
The exact stream exports are also in evidence/session_N_follow_tcp.txt.

QUICK EXPLANATION
Plaintext = readable text. Ciphertext = encrypted text.
Affine key = (a,b); encryption C=(a*P+b) mod26, A=0...Z=25.
Decrypt with inverse(a): P=inverse(a)*(C-b) mod26.
12 valid a values * 26 b values = 312 keys. English-frequency scores rank
the candidates, then independent checks confirm the result.
Moods use different keys; do not pool different ciphertext substitutions.
Cleartext mood also reveals the original deterministic key schedule.

HONEST LIMITS
The original model run used Gemini, so it was cloud-assisted, not offline.
Only viewing this saved pack is offline. Replies are synthetic lab output,
not medical advice. Screenshot dates are actual dates, not AI edits.
The .env and its API key are not in this pack. Do not open your private .env
during presentation. The previously submitted report is a separate record.
'''
    (out/'SHOW_ORDER.txt').write_text(guide,encoding='utf-8')
    if edit_record.exists():
        guide_path=out/'SHOW_ORDER.txt'
        text=guide_path.read_text(encoding='utf-8').replace('Screenshot dates are actual dates, not AI edits.',
            'Screenshot taskbar display dates were edited to 22/10/2026; actual capture chronology is documented separately.')
        guide_path.write_text(text,encoding='utf-8')
    if (lab.parent/'project_notes').is_dir():
        shutil.copytree(lab.parent/'project_notes',out/'project_notes',dirs_exist_ok=True)
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name not in {'MANIFEST.json','PACK_CHECK.json'}:
            files.append({'path':path.relative_to(out).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (out/'MANIFEST.json').write_text(json.dumps({'model':backend['model'],'run_time':run_time,'pcap_sha256':verification['pcap_sha256'],'files':files},indent=2))
    print(f'Built saved viewer at {out}; model={backend["model"]}; sessions={len(sessions)}')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lab',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();build(args.lab,args.out)
