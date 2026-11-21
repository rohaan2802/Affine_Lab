"""Build a readable HTML/PDF report only from verified run artifacts.

Run on Windows with Python, Playwright and installed Microsoft Edge.
"""
import csv
import html
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT.parent if ROOT.name=='psycare_lab' else ROOT
escape=lambda value:html.escape(str(value))


def table(headers, rows, css=''):
    return '<table class="'+css+'"><thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def para(text):return '<p>'+escape(text)+'</p>'
def pre(text):return '<pre>'+escape(text)+'</pre>'
def image(path, caption):return '<figure><img src="'+path.as_uri()+'"><figcaption>'+escape(caption)+'</figcaption></figure>'
def section(title, body):return '<section><h1>'+escape(title)+'</h1>'+body+'</section>'


def main():
    verify=json.loads((ROOT/'output/verification.json').read_text())
    assert verify['all_passed']
    keys=json.loads((ROOT/'output/recovered_keys.json').read_text())
    cases=json.loads((ROOT/'test_cases.json').read_text())
    capture=json.loads((ROOT/'output/captured_sessions.json').read_text())
    freq=list(csv.DictReader((ROOT/'output/frequency_table.csv').open()))
    backend=verify['backend'];runlog=(ROOT/'output/run_log.txt').read_text()
    proof=(ROOT/'output/key_recovery_proof.txt').read_text()
    pages=[]
    pages.append(section('Information Security — Assignment 2',
        '<h2>PsycoSupport: traffic capture and Affine cryptanalysis</h2>'+para('FAST–NUCES · Fall 2026 · Student: Rohaan')+
        para('This report records five synthetic sessions captured on my local WSL Ubuntu loopback interface. The instructor-provided server cipher and protocol were preserved. The language-model call uses Gemini through a small adapter, following the instructor permission reported for this assignment.')+
        table(['Item','Actual configuration'],[['Environment','Windows desktop + WSL2 Ubuntu; Python 3.12.3'],['Lab hostname','rohaan-psylab (private UTS namespace)'],['Transport','TCP JSON on 127.0.0.1:9999'],['Capture','tcpdump on lo; tcp port 9999'],['Model',backend['model']],['Network status','Cloud-assisted: internet required for Gemini'],['Evidence date','Actual run: '+runlog.splitlines()[0].removeprefix('Actual run time: ')],['Results','5 complete sessions; 15 ciphertext fields; all recovered plaintexts verified']])+
        '<h2>Requirement coverage</h2>'+table(['Task','Evidence'],[['1. Deployment','Original-server adapter, environment log, backend.json'],['2. Interception','capture.pcap, ciphertexts.csv, five Follow TCP Stream exports'],['3. Cryptanalysis','Per-session frequencies, 312-key ranking, modular proofs and decryptions'],['4. Engineering analysis','Security discussion and reflection below']])+
        para('Exception: the original brief requires an offline Ollama pipeline. This submission uses the specifically permitted Gemini alternative and does not claim to meet the offline requirement. The brief labels its heading Assignment #1 while the working folder names this Assignment 2; this report follows the folder name.')))
    pages.append(section('1. Deployment and original behavior',
        para('The supplied repository contains Linux executables rather than the revised Python source. The embedded Python 3.12 server module was read from the provided PyInstaller archive. The loader preserves its original functions; a compatible adapter replaces the Groq SDK call with the Gemini REST API. The server binds to loopback rather than 0.0.0.0 to limit exposure. The original startup banner still mentions Groq, while the adapter banner records Gemini as the actual provider.')+
        pre('Client → armored and Affine-encrypted JSON → 127.0.0.1:9999\nServer → Gemini over HTTPS → cleaned English reply\nServer → Affine-encrypted JSON reply → local client')+
        para('For mood m, the original key rule is b = 2m and a is the next integer above b that is coprime with 26. Input bytes are encoded as pairs of A–P letters before encryption. Server advice is converted to uppercase A–Z and spaces, then encrypted directly. These two payload types therefore have different frequency distributions.')+
        para('No cloud key is sent through the lab socket. The local api_key_enc field is empty because the adapter reads GEMINI_API_KEY only on the server. The local .env is excluded from the submission. The key is sent only to the Gemini API in an HTTPS header.')+
        '<h2>Reproduction</h2>'+pre("wsl -d Ubuntu -u root -- unshare --uts --fork bash\n'/mnt/c/Users/CodeTech/Desktop/A#02/psycare_lab/lab_inner.sh'\n\n# Analysis of an existing capture (inside WSL):\nbash run_analysis.sh")+
        para('The Windows launch command is shown over two lines for readability; enter it as one command. Root privileges are used for tcpdump in this controlled WSL environment. The UTS namespace changes only the lab hostname; Windows is not renamed. Gemini requires internet, so an offline network namespace is not used.')+
        '<h2>Run evidence</h2>'+pre('\n'.join(runlog.splitlines()[:7]))))
    pages.append(section('2. Capture and test inputs',
        para('Only synthetic concerns were sent. The five inputs cover exam pressure, loneliness after moving, balancing work with studies, a family disagreement and a group-project deadline. The username is my first name, not a patient identifier.')+
        table(['Session','Mood','Synthetic concern'],[[i,c['mood'],c['concern']] for i,c in enumerate(cases,1)])+
        pre("tcpdump -i lo -U -n -s 0 -w evidence/capture.pcap 'tcp port 9999'\nWireshark display filter: tcp.port == 9999\nTShark export: -q -z follow,tcp,ascii,<stream_index>")+
        para('Port 9999 is the actual port in the instructor executable; 5000 in the brief is an example. The extraction script reassembles each direction by TCP sequence number, checks retransmission consistency and rejects gaps. It parses the request/response JSON and exports username_enc, message_enc and ciphertext exactly into ciphertexts.csv. Empty API-key fields are not counted as ciphertexts.')+
        table(['Session','TCP stream','Captured data frames','Ciphertext fields'],[[s['session'],s['tcp_stream'],str(min(s['frames']))+'–'+str(max(s['frames'])),3] for s in capture])+
        para('The PCAP and TShark Follow TCP Stream exports are the primary evidence. Desktop screenshots show the saved capture in Wireshark; they do not replace or fabricate captured packets. Actual packet/log timestamps remain unchanged. If screenshot display dates were edited, the accompanying project_notes/04_SCREENSHOT_EDIT_RECORD.txt records those edits and the original capture dates.')+
        para('The first export attempt used an incorrect root-user tool path. After correcting that lookup, analysis was rerun on this unchanged PCAP and all independent checks passed. The capture log preserves the original attempt; output/analysis_log.txt records the final successful analysis.')))
    pages.append(section('3. Frequency analysis and key recovery',
        para('Al-Kindi-style analysis uses unequal English letter frequencies. E and T are useful hypotheses, but short passages do not guarantee that the two most frequent ciphertext letters correspond to them. I tested each of the 12 valid multipliers and 26 shifts, decrypted the reply and ranked its 312 candidates by chi-squared distance to an English reference distribution.')+
        pre('E(x) = (a·x + b) mod 26; A=0, …, Z=25\nD(y) = a⁻¹·(y − b) mod 26\nχ² = Σ (observed − expected)² / expected\nexpected(letter) = letter_count × English_frequency(letter) / 100')+
        para('Each reply is attacked separately. Pooling the raw ciphertext from different moods would combine different substitutions and weaken the analysis. The English frequency table is an approximate language model, not proof by itself. Readable plaintext, valid UTF-8 request decoding, re-encryption and a separate comparison with the original implementation confirm each result.')+
        table(['Session','a','b','a inverse','Best χ²','Runner-up χ²'],[[k['session'],k['a'],k['b'],k['a_inverse'],f"{k['chi_squared']:.2f}",f"{k['runner_up_chi_squared']:.2f}"] for k in keys])+
        para('The attack script does not import the server, use the mood-key rule, or read client plaintext. A separate verification script accesses those after recovery. Cleartext mood is also a stronger design flaw: anyone who knows the deterministic schedule can derive a and b directly; that shortcut is not used for the frequency attack.')+
        image(ROOT/'output/decrypted_vs_english.png','Figure 1. Combined recovered English compared with the reference frequencies.')))
    for key,case in zip(keys,cases,strict=True):
        n=key['session'];segment=proof.split(f'SESSION {n}:',1)[1].split('\nSESSION ',1)[0]
        pages.append(section(f'4.{n} Session {n} — complete decryption',
            para(f"Mood {case['mood']}; synthetic input: {case['concern']}")+
            '<h2>Recovered server reply</h2>'+para(key['plaintext'])+
            '<h2>Mathematical working</h2>'+pre(f'SESSION {n}:'+segment)+
            para('The username and concern were also decrypted and de-armored successfully. Their complete recovered text is in output/decrypted.csv and output/decrypted_sessions.txt; the verification compares it exactly with the synthetic input.')))
    pages.append(section('5. Security engineering and reflection',
        '<h2>Why the wrapper fails</h2>'+para('A deterministic monoalphabetic substitution preserves word lengths, spaces and letter-count patterns. Repeated names or conventional advice wording supply likely plaintext. Where a product appends a fixed disclaimer, the same wording can expose letter correspondences across replies. This original server does not enforce such a disclaimer, so none is added or claimed as evidence here. Even without it, the small 312-key space and normal English statistics were sufficient.')+
        para('The client armor is encoding, not additional cryptographic protection. Mood is sent in clear and deterministically selects the key. The original server also writes decrypted advice to admin_log.txt. Network encryption alone would not protect this plaintext log from local users or malware with file access. A stronger model does not repair a weak encryption wrapper.')+
        table(['Alternative','Practical protection','Limits'],[['UNIX domain socket','Use a pathname socket in a private directory, owner-only permissions and peer-credential checks.','This gives local access control, not encryption against a privileged host attacker.'],['TLS 1.3','Authenticate the server and encrypt TCP traffic. For a local self-signed certificate, pin or explicitly trust the certificate; keep hostname verification.','Disabling verification defeats authentication. Protect private keys and consider mutual TLS for client authentication.']])+
        '<h2>Input and ethical reflection</h2>'+para('All concerns are fictional, and capture was restricted to my own loopback application. No public host, patient data or another user’s traffic was tested. The original model prompt says it is a licensed therapist; that claim is unsuitable for a real service and is preserved only to reproduce the supplied lab behavior. Model-generated replies in this report are test data, not medical advice.')+
        para('The result shows the difference between hiding readable text and providing modern confidentiality and integrity. Frequency recovery can be uncertain on very short samples, so independent validation matters. Gemini also changes the privacy boundary: prompts leave the machine over HTTPS. Instructor permission does not make this an offline or wholly local application.')+
        para('Preparation note: AI assistance was used to prepare code and report structure. The included run artifacts, independent checks and source attribution allow the work to be reviewed and reproduced.')))
    for start in [1,3,5]:
        pages.append(section('6. Frequency charts', ''.join(image(ROOT/f'output/session_{n}_frequency.png',
            f'Figure 2.{n}. Session {n}: captured ciphertext compared with the English reference.')
            for n in range(start,min(start+2,6)))))
    for start in [1,3,5]:
        body=''
        for n in range(start,min(start+2,6)):
            path=ROOT/f'evidence/desktop_session_{n}.png'
            if path.exists():body+=image(path,f'Figure {n+2}. Actual Windows desktop: Wireshark Follow TCP Stream, session {n}.')
        if start==5 and (ROOT/'evidence/desktop_capture_overview.png').exists():
            body+=image(ROOT/'evidence/desktop_capture_overview.png','Figure 8. Capture overview: all 50 packets pass the loopback application display filter.')
        if body:pages.append(section('7. Desktop capture evidence',body))
    for n in range(1,6):
        data=[r for r in freq if int(r['session'])==n]
        pages.append(section(f'Appendix A.{n} — full frequency table',table(['Letter','Cipher count','Cipher %','Recovered %','English %'],[[r['letter'],r['cipher_count'],r['cipher_percent'],r['decrypted_percent'],r['english_percent']] for r in data],'compact')+
            para('Counts use A–Z only. Spaces are excluded. The reference is the letter-frequency table attributed to Lewand (2000). The CSV includes all five tables in machine-readable form.')))
    refs=[('Instructor source','https://github.com/maadilrehman/PsycoSupport'),('Gemini API','https://ai.google.dev/api/generate-content'),('TShark manual','https://www.wireshark.org/docs/man-pages/tshark.html'),('UNIX sockets','https://man7.org/linux/man-pages/man7/unix.7.html'),('TLS 1.3 specification','https://www.rfc-editor.org/info/rfc9846')]
    pages.append(section('Appendix B — verification and references',
        para('All five recovered keys matched the instructor’s original key schedule after the ciphertext-only attack. All five server replies matched client-side decryption. All usernames and concerns matched the synthetic test inputs. Every server ciphertext was reproduced exactly by re-encrypting the recovered reply.')+
        table(['Artifact','SHA-256'],[['capture.pcap',verify['pcap_sha256']],['Original server',verify['original_server_sha256']]],'hashes')+
        ''.join(para(name+': ')+f'<p><a href="{url}">{url}</a></p>' for name,url in refs)+
        para('English reference: Robert Lewand, Cryptological Mathematics, Mathematical Association of America, 2000. Repository revision: '+(ROOT/'upstream_commit.txt').read_text().strip())+
        para('Submission contains report.pdf, ciphertexts.csv, scripts/, evidence/, output/ and the reproducible lab source. Local .env, environments, caches and provisioning logs are excluded.')))
    css='''@page {size:A4;margin:17mm 17mm 18mm} body{font:10.5pt/1.43 Arial,sans-serif;color:#202830}h1{font-size:19pt;color:#25465c;border-bottom:1px solid #acbac5;padding-bottom:7px}h2{font-size:12.5pt;margin:15px 0 7px}p{margin:8px 0}section{break-before:page}section:first-child{break-before:auto}table{width:100%;border-collapse:collapse;font-size:9pt;margin:12px 0}th,td{border:1px solid #c8d0d5;padding:6px;text-align:left;vertical-align:top}th{background:#eaf0f4}tr{break-inside:avoid}pre{font:8pt/1.4 Consolas,monospace;background:#f2f4f6;padding:10px;white-space:pre-wrap;overflow-wrap:anywhere}figure{margin:12px 0;break-inside:avoid}img{display:block;max-width:100%;max-height:215mm;margin:auto}figcaption{font-size:8.5pt;color:#515d67;text-align:center;margin-top:5px}.compact td,.compact th{padding:5px}.hashes{table-layout:fixed}.hashes td{word-break:break-all}a{color:#25465c}'''
    document='<!doctype html><html><head><meta charset="utf-8"><title>PsycoSupport report</title><style>'+css+'</style></head><body>'+''.join(pages)+'</body></html>'
    report=DEST/'report.html';report.write_text(document,encoding='utf-8')
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page();page.goto(report.as_uri());page.wait_for_load_state('networkidle')
        page.pdf(path=str(DEST/'report.pdf'),print_background=True,prefer_css_page_size=True,
            display_header_footer=True,header_template='<span></span>',
            footer_template='<div style="width:100%;text-align:center;font:8px Arial;color:#687580">Information Security · PsycoSupport &nbsp; | &nbsp; <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        browser.close()
    print('Generated report.html and report.pdf from verified real outputs.')


if __name__=='__main__':main()
