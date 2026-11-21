"""Local HTTP checks; no Gemini calls and no instructor-binary execution."""
import importlib.util
import json
from pathlib import Path
import threading
import unittest
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('web_demo',ROOT/'web_demo.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)


class WebDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.STATE['runtime']=None
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        app.STATE['port']=cls.server.server_port
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def get(self,path):
        return urllib.request.urlopen(self.base+path,timeout=10)

    def test_page_and_assets(self):
        for path in ['/','/app.js','/style.css']:
            with self.get(path) as response:
                self.assertEqual(response.status,200)
                self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])

    def test_saved_data_is_verified_and_complete(self):
        with self.get('/api/saved') as response:data=json.load(response)
        self.assertTrue(data['saved']);self.assertEqual(len(data['results']),5)
        self.assertTrue(all(r['verified'] for r in data['results']))
        self.assertTrue(data['verification']['all_passed'])

    def test_preview_has_no_live_backend(self):
        with self.get('/api/status') as response:data=json.load(response)
        self.assertFalse(data['live_available']);self.assertEqual(len(data['cases']),5)
        self.assertNotIn('api_key',data)

    def test_private_files_are_not_served(self):
        for path in ['/.env','/source/.env','/charts/../.env','/server.py']:
            with self.assertRaises(urllib.error.HTTPError) as error:self.get(path)
            self.assertEqual(error.exception.code,404)
            error.exception.close()

    def test_cross_origin_live_request_is_rejected(self):
        request=urllib.request.Request(self.base+'/api/run',data=b'{"case":1}',headers={
            'Content-Type':'application/json','X-Demo-Request':'1','Origin':'https://unrelated.example'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
        self.assertEqual(error.exception.code,403)
        error.exception.close()

    def test_saved_preview_never_fakes_a_live_result(self):
        request=urllib.request.Request(self.base+'/api/run',data=b'{"case":1}',headers={
            'Content-Type':'application/json','X-Demo-Request':'1','Origin':self.base})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
        self.assertEqual(error.exception.code,503)
        error.exception.close()

    def test_recorded_chart(self):
        with self.get('/charts/session_1_frequency.png') as response:
            self.assertEqual(response.headers['Content-Type'],'image/png')
            self.assertTrue(response.read().startswith(b'\x89PNG'))


if __name__=='__main__':unittest.main()
