"""Local dashboard with bounded, same-origin controls and private credentials."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import threading
import re
from urllib.parse import urlsplit
from .crypto import encrypt, mood_key
from .fixtures import load_cases, public_cases
from .protocol import LabServer
from .providers import ProviderError
from .reporting import export_run, run_id
from .runner import run_cases
from .protocol import encode_request
from .validation import validate_session


class Dashboard:
    def __init__(self, provider, *, http_port=8765, tcp_port=9999, output=Path("runs")):
        self.provider, self.output = provider, output
        self.backend = LabServer(provider, tcp_port)
        self.busy = threading.Lock()
        try:
            self.http = ThreadingHTTPServer(("127.0.0.1", http_port), Handler)
        except OSError:
            self.backend.server.server_close()
            raise
        self.http.dashboard = self

    def serve(self):
        with self.backend:
            print(f"Dashboard: http://127.0.0.1:{self.http.server_port}", flush=True)
            print(
                f"Mode: {self.provider.mode}; TCP port: {self.backend.address[1]}; credentials stay server-side.",
                flush=True,
            )
            try:
                self.http.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                self.http.server_close()

    def close(self):
        self.http.shutdown()
        self.http.server_close()


class Handler(BaseHTTPRequestHandler):
    @property
    def app(self):
        return self.server.dashboard

    def respond(self, status, value, content_type="application/json; charset=utf-8"):
        data = value if isinstance(value, bytes) else json.dumps(value).encode()
        try:
            self.send_response(status)
            for name, val in {
                "Content-Type": content_type,
                "Content-Length": str(len(data)),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            }.items():
                self.send_header(name, val)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        route = urlsplit(self.path).path
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/favicon.svg": ("favicon.svg", "image/svg+xml"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if route in assets:
            filename, content_type = assets[route]
            self.respond(
                200,
                files("affine_lab").joinpath("web", filename).read_bytes(),
                content_type,
            )
        elif route == "/api/status":
            self.respond(
                200,
                {
                    "mode": self.app.provider.mode,
                    "model": self.app.provider.model,
                    "tcp_port": self.app.backend.address[1],
                    "cases": public_cases(),
                },
            )
        elif route == "/api/recorded":
            rows = []
            for case in load_cases():
                key = mood_key(case["mood"])
                cipher = encrypt(case["recorded_response"], key)
                rows.append(
                    validate_session(
                        {
                            "request": encode_request(case),
                            "response": {"ciphertext": cipher},
                        },
                        case,
                    )
                )
            self.respond(
                200,
                {
                    "mode": "recorded-corpus",
                    "generation": "saved source corpus; no TCP exchange or API call",
                    "sessions": rows,
                },
            )
        elif route == "/api/runs":
            items = []
            if self.app.output.is_dir():
                for folder in sorted(self.app.output.iterdir(), reverse=True):
                    if (
                        re.fullmatch(r"\d{8}T\d{6}_\d{6}Z", folder.name)
                        and (folder / "result.json").is_file()
                    ):
                        try:
                            result = json.loads(
                                (folder / "result.json").read_text(encoding="utf-8")
                            )
                            if (
                                not {"mode", "all_passed", "sessions", "run_time_utc"}
                                <= result.keys()
                            ):
                                continue
                        except (ValueError, OSError, AttributeError):
                            continue
                        items.append(
                            {
                                "id": folder.name,
                                "mode": result["mode"],
                                "all_passed": result["all_passed"],
                                "cases": len(result["sessions"]),
                                "run_time_utc": result["run_time_utc"],
                            }
                        )
                    if len(items) == 20:
                        break
            self.respond(200, {"runs": items})
        elif route.startswith("/api/export/"):
            parts = route.split("/")
            allowed = {
                "result.json",
                "summary.csv",
                "ciphertexts.csv",
                "key_recovery_proof.txt",
                "decrypted_sessions.txt",
                "manifest.json",
            }
            if (
                len(parts) == 5
                and re.fullmatch(r"\d{8}T\d{6}_\d{6}Z", parts[3])
                and parts[4] in allowed
                and (self.app.output / parts[3] / parts[4]).is_file()
            ):
                self.respond(
                    200,
                    (self.app.output / parts[3] / parts[4]).read_bytes(),
                    "text/plain; charset=utf-8",
                )
            else:
                self.respond(404, {"error": "Not found"})
        else:
            self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/run":
            self.respond(404, {"error": "Not found"})
            return
        origin = self.headers.get("Origin")
        permitted = {
            None,
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }
        if (
            origin not in permitted
            or self.headers.get("X-Affine-Lab") != "1"
            or self.headers.get_content_type() != "application/json"
        ):
            self.respond(403, {"error": "Use the local dashboard controls"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024:
                raise ValueError()
            payload = json.loads(self.rfile.read(size))
            case_id = payload.get("case")
            if case_id != "all" and (type(case_id) is not int or not 1 <= case_id <= 5):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            self.respond(400, {"error": "Select one of the five cases or all"})
            return
        if not self.app.busy.acquire(blocking=False):
            self.respond(409, {"error": "A run is already in progress"})
            return
        try:
            result = run_cases(
                self.app.backend,
                self.app.provider,
                range(1, 6) if case_id == "all" else [case_id],
            )
            folder = export_run(result, self.app.output / run_id())
            self.respond(200, {**result, "export_name": folder.name})
        except (ValueError, OSError, ProviderError):
            self.respond(
                502,
                {
                    "error": "Run failed; check provider access or input privately. No replay fallback was used."
                },
            )
        finally:
            self.app.busy.release()

    def log_message(self, *_):
        # Do not log request bodies, headers or credentials.
        pass
