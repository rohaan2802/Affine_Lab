import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from affine_lab.providers import ReplayProvider
from affine_lab.web import Dashboard


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Dashboard(
            ReplayProvider(), http_port=0, tcp_port=0, output=Path(self.temp.name)
        )
        self.app.backend.__enter__()
        self.thread = threading.Thread(target=self.app.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.app.http.server_port}"

    def tearDown(self):
        self.app.close()
        self.thread.join()
        self.app.backend.__exit__()
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.load(response)

    def post(self, case, origin=None):
        headers = {"Content-Type": "application/json", "X-Affine-Lab": "1"}
        if origin:
            headers["Origin"] = origin
        return urlopen(
            Request(
                self.base + "/api/run", json.dumps({"case": case}).encode(), headers
            )
        )

    def test_status_and_saved_corpus_are_labelled(self):
        self.assertEqual(self.get("/api/status")["mode"], "replay")
        data = self.get("/api/recorded")
        self.assertEqual(data["mode"], "recorded-corpus")
        self.assertEqual(sum(r["verified"] for r in data["sessions"]), 5)

    def test_real_run_history_and_export(self):
        with self.post("all") as response:
            result = json.load(response)
        self.assertTrue(result["all_passed"])
        run = self.get("/api/runs")["runs"][0]
        self.assertEqual(run["cases"], 5)
        export = self.get(f"/api/export/{run['id']}/result.json")
        self.assertEqual(export["mode"], "replay")

    def test_private_paths_and_cross_origin_rejected(self):
        for path in ["/.env", "/api/export/../../.env", "/src/affine_lab/providers.py"]:
            with self.assertRaises(HTTPError) as error:
                self.get(path)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
        with self.assertRaises(HTTPError) as error:
            self.post(1, "https://example.com")
        self.assertEqual(error.exception.code, 403)
        error.exception.close()

    def test_bad_case_and_concurrent_run_rejected(self):
        with self.assertRaises(HTTPError) as error:
            self.post(True)
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        self.app.busy.acquire()
        try:
            with self.assertRaises(HTTPError) as error:
                self.post(1)
            self.assertEqual(error.exception.code, 409)
            error.exception.close()
        finally:
            self.app.busy.release()

    def test_assets_have_content_security_policy(self):
        for path in ["/", "/app.js", "/style.css", "/favicon.svg"]:
            with urlopen(self.base + path) as response:
                self.assertIn(
                    "default-src 'self'", response.headers["Content-Security-Policy"]
                )
                self.assertTrue(response.read())
