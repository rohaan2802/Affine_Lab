"""Five synthetic sessions using the instructor's JSON/TCP protocol."""
import json
import socket
from pathlib import Path
from server import original


def armor(text):
    return ''.join(chr(65 + (byte >> 4)) + chr(65 + (byte & 15))
                   for byte in text.encode('utf-8'))


def run():
    root = Path(__file__).parent
    cases = json.loads((root / 'test_cases.json').read_text())
    results = []
    for index, case in enumerate(cases, 1):
        mood = case['mood']
        b = 2 * mood
        a = original['next_coprime_above'](b)
        enc = lambda text: original['affine_encrypt'](armor(text), a, b)
        payload = {'username_enc': enc(case['username']), 'mood': mood,
                   'message_enc': enc(case['concern']), 'api_key_enc': ''}
        with socket.create_connection(('127.0.0.1', 9999), timeout=600) as conn:
            conn.sendall(json.dumps(payload).encode())
            parts = []
            while data := conn.recv(65536):
                parts.append(data)
        reply = json.loads(b''.join(parts))
        if 'error' in reply:
            raise RuntimeError(reply['error'])
        plain = original['affine_decrypt'](reply['ciphertext'], a, b)
        results.append({'session': index, 'request': payload,
                        'response': reply, 'plaintext': plain})
        print(f'Case {index}: mood={mood}; {len(plain)} response characters', flush=True)
        print(plain, flush=True)
    (root / 'output' / 'client_results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    run()
