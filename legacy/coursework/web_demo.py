"""Local web UI for saved evidence or actual WSL/Gemini test sessions.

Python 3.12: start the original TCP server through the existing adapter.
Other Python versions: --saved-only can preview verified saved evidence.
The browser never receives the model API key.
"""
import argparse
import csv
from datetime import datetime
import importlib
import json
from math import gcd
import os
from pathlib import Path
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
STATE = {'runtime': None, 'busy': threading.Lock(), 'port': 8765}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def saved_root():
    for candidate in [ROOT.parent/'Pre_Demo', ROOT.parent/'pre_demo', ROOT]:
        if (candidate/'output/verification.json').exists():
            return candidate
    return ROOT


def saved_data():
    base = saved_root()
    check = read_json(base/'output/verification.json')
    if not check.get('all_passed'):
        raise ValueError('No verified saved run is available')
    cases = read_json(ROOT/'test_cases.json')
    keys = read_json(base/'output/recovered_keys.json')
    with (base/'output/decrypted.csv').open(encoding='utf-8') as source:
        decrypted = list(csv.DictReader(source))
    results = []
    for key, case in zip(keys, cases, strict=True):
        number = key['session']
        fields = {r['field']: r['plaintext'] for r in decrypted if int(r['session']) == number}
        results.append({'session': number, 'case': case, 'key': key,
                        'plaintext': fields['ciphertext'], 'verified': True})
    return {'provider': check['backend']['provider'], 'model': check['backend']['model'],
            'results': results, 'verification': check,
            'recorded_log': (base/'output/analysis_log.txt').read_text(), 'saved': True}


def run_case(number):
    # The client knows the original key; the attack below independently
    # recovers it from the captured-style response before the comparison.
    runtime = STATE['runtime']
    if runtime is None:
        raise RuntimeError('Live mode requires WSL Python 3.12; this is saved-only preview')
    cases = read_json(ROOT/'test_cases.json')
    case = cases[number-1]
    original = runtime.original
    b = 2*case['mood']; a = original['next_coprime_above'](b)
    client = importlib.import_module('client')
    encrypt = lambda text: original['affine_encrypt'](client.armor(text), a, b)
    request = {'username_enc': encrypt(case['username']), 'mood': case['mood'],
               'message_enc': encrypt(case['concern']), 'api_key_enc': ''}
    with socket.create_connection(('127.0.0.1', 9999), timeout=600) as connection:
        connection.sendall(json.dumps(request).encode())
        received = []
        while data := connection.recv(65536):
            received.append(data)
    response = json.loads(b''.join(received))
    if 'error' in response:
        raise RuntimeError(response['error'])
    from scripts.common import chi_squared, affine_decrypt
    from scripts.analyze import dearmor
    cipher = response['ciphertext']
    ranked = sorted((chi_squared(affine_decrypt(cipher,x,y)), x,y)
                    for x in range(26) if gcd(x,26)==1 for y in range(26))
    score, recovered_a, recovered_b = ranked[0]
    plain = affine_decrypt(cipher,recovered_a,recovered_b)
    try:
        input_matches = (dearmor(affine_decrypt(request['username_enc'],recovered_a,recovered_b))==case['username']
            and dearmor(affine_decrypt(request['message_enc'],recovered_a,recovered_b))==case['concern'])
    except (AssertionError,ValueError,UnicodeError):
        input_matches = False
    verified = ((recovered_a,recovered_b)==(a,b)
        and plain==original['affine_decrypt'](cipher,a,b)
        and original['affine_encrypt'](plain,recovered_a,recovered_b)==cipher
        and input_matches)
    result = {'session':number,'case':case,'request':request,'response':response,
              'plaintext':plain,'verified':verified,
              'key':{'a':recovered_a,'b':recovered_b,'a_inverse':pow(recovered_a,-1,26),
                     'chi_squared':score,'runner_up_chi_squared':ranked[1][0]},
              'provider':'Gemini','model':runtime.MODEL,'saved':False,
              'run_time':datetime.now().astimezone().isoformat(timespec='seconds')}
    folder = ROOT/'web_runs'; folder.mkdir(exist_ok=True)
    name = datetime.now().strftime('%Y%m%d_%H%M%S_%f')+f'_case_{number}.json'
    (folder/name).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


class Handler(BaseHTTPRequestHandler):
    def send(self,status,body,mime='application/json; charset=utf-8'):
        if not isinstance(body,bytes):
            body = json.dumps(body).encode()
        try:
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):
            print('Browser disconnected; completed results remain in web_runs/.',flush=True)

    def do_GET(self):
        route = urlsplit(self.path).path
        files = {'/':('index.html','text/html; charset=utf-8'),
                 '/app.js':('app.js','application/javascript; charset=utf-8'),
                 '/style.css':('style.css','text/css; charset=utf-8')}
        if route in files:
            name,mime=files[route];self.send(200,(ROOT/'web_ui'/name).read_bytes(),mime)
        elif route=='/api/status':
            backend=read_json(saved_root()/'output/backend.json')
            self.send(200,{'live_available':STATE['runtime'] is not None,
                'model':getattr(STATE['runtime'],'MODEL','') or backend['model'],
                'provider':'Gemini','capture':os.environ.get('WEB_DEMO_CAPTURE_PATH',''),
                'cases':read_json(ROOT/'test_cases.json')})
        elif route=='/api/saved':
            try:self.send(200,saved_data())
            except (ValueError,OSError,KeyError):self.send(503,{'error':'Verified saved results unavailable'})
        elif route.startswith('/charts/'):
            allowed={'decrypted_vs_english.png',*[f'session_{n}_frequency.png' for n in range(1,6)]}
            name=route.removeprefix('/charts/')
            if name in allowed:self.send(200,(saved_root()/'output'/name).read_bytes(),'image/png')
            else:self.send(404,{'error':'Not found'})
        else:self.send(404,{'error':'Not found'})

    def do_POST(self):
        if urlsplit(self.path).path!='/api/run':
            self.send(404,{'error':'Not found'});return
        allowed={f'http://127.0.0.1:{STATE["port"]}',f'http://localhost:{STATE["port"]}'}
        if (self.headers.get('Origin') not in allowed|{None}
            or self.headers.get('X-Demo-Request')!='1'
            or self.headers.get_content_type()!='application/json'):
            self.send(403,{'error':'Use this local demo page'});return
        if STATE['runtime'] is None:
            self.send(503,{'error':'Saved-only preview. Start live mode in WSL Python 3.12.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError()
            payload=json.loads(self.rfile.read(size));case=payload.get('case')
            if type(case) is not int or not 1<=case<=5:raise ValueError()
        except (ValueError,TypeError,json.JSONDecodeError):
            self.send(400,{'error':'Select one of the five synthetic cases'});return
        if not STATE['busy'].acquire(blocking=False):
            self.send(409,{'error':'A test is already running; wait for it to finish'});return
        try:self.send(200,run_case(case))
        except (RuntimeError,ValueError,OSError,KeyError) as exc:
            # Known backend messages omit credentials and request headers.
            self.send(502,{'error':str(exc) if isinstance(exc,RuntimeError) else 'Backend request failed; check the private server log'})
        finally:STATE['busy'].release()

    def log_message(self,fmt,*args):
        print(f'Web request: {self.command} {urlsplit(self.path).path}',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--saved-only',action='store_true');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args();STATE['port']=args.port
    if not args.saved_only:
        if sys.version_info[:2]!=(3,12):raise SystemExit('Use WSL Python 3.12 for live mode, or --saved-only for preview.')
        runtime=importlib.import_module('server')
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',9999))
            except OSError:raise SystemExit('Port 9999 is already in use. Stop the earlier lab run first.')
        STATE['runtime']=runtime
        thread=threading.Thread(target=runtime.original['start'],daemon=True);thread.start()
        import time
        for attempt in range(30):
            if not thread.is_alive():raise SystemExit('Original TCP server failed to start')
            # Verify a listening socket through /proc without creating extra packets.
            rows=Path('/proc/net/tcp').read_text().splitlines()[1:]
            if any(row.split()[1]=='0100007F:270F' and row.split()[3]=='0A' for row in rows):break
            time.sleep(.1)
        else:raise SystemExit('TCP server did not become ready')
    web=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Web demo: http://127.0.0.1:{args.port} (loopback only)',flush=True)
    print('Saved-only preview' if args.saved_only else 'Live Gemini enabled; API key stays on server',flush=True)
    try:web.serve_forever()
    except KeyboardInterrupt:pass
    finally:web.server_close()


if __name__=='__main__':main()
