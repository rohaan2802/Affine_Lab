import csv
import json
from pathlib import Path
import tempfile
import unittest
from affine_lab.batch import analyze_csv

ROOT = Path(__file__).resolve().parents[1]


class BatchTests(unittest.TestCase):
    def test_recorded_replies_and_complete_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "result"
            result = analyze_csv(
                ROOT / "data/recorded/tcp_baseline/ciphertexts.csv", target
            )
            self.assertEqual(result["analyzed_rows"], 5)
            self.assertEqual(result["skipped_armored_rows"], 10)
            self.assertEqual(
                [(r["analysis"]["a"], r["analysis"]["b"]) for r in result["sessions"]],
                [(7, 6), (9, 8), (11, 10), (15, 12), (15, 14)],
            )
            with (target / "candidate_ranking.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 1560)
            with (target / "letter_frequencies.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 130)
            self.assertIn(
                "Unverified",
                json.loads((target / "analysis.json").read_text())["verification"],
            )

    def test_nonempty_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "keep.txt").write_text("keep")
            with self.assertRaises(ValueError):
                analyze_csv(ROOT / "data/recorded/tcp_baseline/ciphertexts.csv", target)
            self.assertEqual((target / "keep.txt").read_text(), "keep")

    def test_missing_column_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "bad.csv"
            source.write_text("message\nhello\n")
            with self.assertRaises(ValueError):
                analyze_csv(source, Path(temp) / "out")
            self.assertFalse((Path(temp) / "out").exists())

    def test_nonletter_input_rejected_with_row_number(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "bad.csv"
            source.write_text("ciphertext\n12345\n")
            with self.assertRaisesRegex(ValueError, "Row 1"):
                analyze_csv(source, Path(temp) / "out")
