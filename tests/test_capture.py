from pathlib import Path
import tempfile
import unittest
from affine_lab.capture import CaptureError, inspect_pcap, reassemble

ROOT = Path(__file__).resolve().parents[1]


class CaptureTests(unittest.TestCase):
    def test_reordered_and_duplicate_segments(self):
        self.assertEqual(
            reassemble([(103, b"def"), (100, b"abc"), (102, b"cd"), (100, b"abc")]),
            b"abcdef",
        )

    def test_conflicting_retransmission_rejected(self):
        with self.assertRaisesRegex(CaptureError, "conflicting"):
            reassemble([(100, b"abc"), (101, b"ZZ")])

    def test_missing_bytes_rejected(self):
        with self.assertRaisesRegex(CaptureError, "gap"):
            reassemble([(100, b"ab"), (103, b"d")])

    def test_corrupt_and_truncated_files_rejected(self):
        original = (ROOT / "data/recorded/tcp_baseline/capture.pcap").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "bad.pcap"
            for data in [
                b"",
                original[:23],
                original[:25],
                original[:-1],
                b"BAD!" + original[4:],
            ]:
                file.write_bytes(data)
                with self.subTest(length=len(data)), self.assertRaises(CaptureError):
                    inspect_pcap(file)

    def test_actual_capture_metadata(self):
        result = inspect_pcap(ROOT / "data/recorded/tcp_baseline/capture.pcap")
        self.assertEqual(result["frames"], 50)
        self.assertEqual(result["skipped_frames"], 0)
        self.assertEqual(len(result["sessions"]), 5)
        self.assertEqual(
            result["sha256"],
            "2e2b4726500ab366c3178257c45a998a50cf3f329c80e65b182162f5f43ee9e1",
        )
        self.assertTrue(
            all(s["request"]["api_key_enc"] == "" for s in result["sessions"])
        )

    def test_wrong_port_has_no_matching_sessions(self):
        with self.assertRaisesRegex(CaptureError, "no complete"):
            inspect_pcap(ROOT / "data/recorded/tcp_baseline/capture.pcap", port=5000)
