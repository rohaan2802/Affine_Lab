"""Original server functions, with only Groq calls routed to Gemini.

Cipher, armor, mood keys, prompts, cleaning, TCP handling and logging are
loaded unchanged from the supplied executable. Bind is loopback-only.
"""
import json
import os
import sys
import types
import time
import urllib.request
import urllib.error
from pathlib import Path
from upstream_loader import load_server_code

ROOT = Path(__file__).parent
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines() if (ROOT / '.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        name, value = line.split('=', 1)
        os.environ.setdefault(name.strip(), value.strip().strip('\"\''))
MODEL = os.environ.get('GEMINI_MODEL', '')


def gemini_request(path, payload=None):
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        raise RuntimeError('Set GEMINI_API_KEY locally; do not submit the key')
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/' + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            # Credentials and remote response bodies stay out of evidence.
            raise RuntimeError(f'Gemini HTTP {exc.code}; check model access/quota locally') from None


def choose_model():
    global MODEL
    if not MODEL:
        available = [m['name'].removeprefix('models/') for m in gemini_request('models').get('models', [])
                     if 'generateContent' in m.get('supportedGenerationMethods', [])]
        preferred = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite',
                     'gemini-2.5-flash-lite', 'gemini-2.5-flash']
        MODEL = next((m for m in preferred if m in available), '')
        if not MODEL:
            MODEL = next((m for m in available if 'flash' in m and 'preview' not in m), '')
        if not MODEL:
            raise RuntimeError('Set GEMINI_MODEL to an available text model')
    return MODEL


class GeminiGroqAdapter:
    def __init__(self, api_key=None):
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, model, temperature, top_p, max_tokens, messages):
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        contents = [{'role': 'model' if m['role'] == 'assistant' else 'user',
                     'parts': [{'text': m['content']}]} for m in messages if m['role'] != 'system']
        payload = {'systemInstruction': {'parts': [{'text': system}]}, 'contents': contents,
                   'generationConfig': {'temperature': temperature, 'topP': top_p,
                                        'maxOutputTokens': max(1024, max_tokens)}}
        body = gemini_request(f'models/{choose_model()}:generateContent', payload)
        text = ''.join(p.get('text', '') for c in body.get('candidates', [])
                       for p in c.get('content', {}).get('parts', []) if not p.get('thought'))
        if not text.strip():
            raise RuntimeError('Gemini returned no response text; no synthetic fallback used')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(
            message=types.SimpleNamespace(content=text))])


shim = types.ModuleType('groq')
shim.Groq = GeminiGroqAdapter
sys.modules['groq'] = shim
original = {'__name__': 'instructor_server'}
exec(load_server_code(), original)
original['HOST'] = '127.0.0.1'

if __name__ == '__main__':
    print(f'Backend: Gemini / {choose_model()}; capture: loopback TCP 9999', flush=True)
    (ROOT / 'output' / 'backend.json').write_text(json.dumps({'provider': 'Gemini', 'model': MODEL,
        'offline': False, 'instructor_permission': 'Reported by student'}))
    original['start']()
