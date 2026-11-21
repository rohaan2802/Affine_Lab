import json
from pathlib import Path
import socket
import tempfile
import unittest
from affine_lab.fixtures import get_case
from affine_lab.protocol import (
    LabServer,
    decode_request,
    encode_request,
    exchange,
    receive_json,
)
from affine_lab.providers import ProviderError, ReplayProvider
from affine_lab.reporting import export_run
from affine_lab.runner import run_cases


class ProtocolTests(unittest.TestCase):
    def test_historical_wire_compatibility(self):
        root = Path(__file__).resolve().parents[1]
        sessions = json.loads(
            (root / "data/recorded/tcp_baseline/sessions.json").read_text()
        )
        for i, session in enumerate(sessions, 1):
            self.assertEqual(encode_request(get_case(i)), session["request"])
        with LabServer(ReplayProvider()) as server:
            for i, session in enumerate(sessions, 1):
                self.assertEqual(
                    exchange(get_case(i), server.address)["response"],
                    session["response"],
                )

    def test_five_real_tcp_replay_exchanges_and_exports(self):
        provider = ReplayProvider()
        with LabServer(provider) as server:
            result = run_cases(server, provider)
        self.assertTrue(result["all_passed"])
        self.assertEqual(result["completed_cases"], 5)
        self.assertEqual(result["mode"], "replay")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "run"
            export_run(result, target)
            self.assertEqual(
                len(json.loads((target / "manifest.json").read_text())["files"]), 5
            )
            with self.assertRaises(FileExistsError):
                export_run(result, target)

    def test_partial_failure_is_not_reported_as_success(self):
        class Failing(ReplayProvider):
            def generate(self, username, mood, concern):
                if mood != 3:
                    raise ProviderError("synthetic provider failure")
                return super().generate(username, mood, concern)

        provider = Failing()
        with LabServer(provider) as server:
            result = run_cases(server, provider)
        self.assertFalse(result["all_passed"])
        self.assertEqual(result["completed_cases"], 1)
        self.assertIn("Case 2 failed", result["error"])
        self.assertTrue(result["sessions"][0]["verified"])

    def test_secrets_cannot_travel_in_lab_request(self):
        request = encode_request(get_case(1))
        request["api_key_enc"] = "not-empty"
        with self.assertRaisesRegex(ValueError, "credentials"):
            decode_request(request)

    def test_segmented_json_request(self):
        case = get_case(1)
        with (
            LabServer(ReplayProvider()) as server,
            socket.create_connection(server.address) as connection,
        ):
            data = json.dumps(encode_request(case)).encode()
            for i in range(0, len(data), 7):
                connection.sendall(data[i : i + 7])
            self.assertIn("ciphertext", receive_json(connection))

    def test_invalid_input_returns_error_without_crashing_server(self):
        with LabServer(ReplayProvider()) as server:
            with socket.create_connection(server.address) as connection:
                connection.sendall(b'{"mood":true}')
                self.assertIn("error", receive_json(connection))
            self.assertIn("response", exchange(get_case(1), server.address))
