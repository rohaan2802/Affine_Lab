from pathlib import Path
import unittest
from affine_lab.analysis import analyze, chi_squared, rank_keys
from affine_lab.crypto import Key, decrypt, encrypt, mood_key
from affine_lab.fixtures import load_cases
from affine_lab.validation import verify_recorded_run

ROOT = Path(__file__).resolve().parents[1]


class AnalysisTests(unittest.TestCase):
    def test_optimized_scores_match_full_text_reference(self):
        text = load_cases()[0]["recorded_response"]
        cipher = encrypt(text, Key(7, 6))
        for candidate in rank_keys(cipher):
            reference = chi_squared(decrypt(cipher, Key(candidate.a, candidate.b)))
            self.assertAlmostEqual(candidate.score, reference, places=9)

    def test_all_five_recorded_keys_recovered_without_mood_input(self):
        for case in load_cases():
            key = mood_key(case["mood"])
            result = analyze(encrypt(case["recorded_response"], key))
            self.assertEqual((result["a"], result["b"]), (key.a, key.b))
            self.assertEqual(result["plaintext"], case["recorded_response"])
            self.assertEqual(len(result["frequencies"]), 26)
            self.assertIn("312", " ".join(result["proof"]))

    def test_candidate_count_and_stable_order(self):
        ranked = rank_keys("THIS IS A SHORT EXAMPLE")
        self.assertEqual(len(ranked), 312)
        self.assertEqual(len({(c.a, c.b) for c in ranked}), 312)
        self.assertEqual([c.score for c in ranked], sorted(c.score for c in ranked))

    def test_empty_or_nonletter_input_rejected(self):
        for value in ["", "123 !!!", "اردو"]:
            with self.assertRaises(ValueError):
                analyze(value)

    def test_three_historical_runs_and_all_fifteen_sessions(self):
        for name in ["submission", "tcp_baseline", "web_validation"]:
            with self.subTest(run=name):
                result = verify_recorded_run(ROOT / "data/recorded" / name)
                self.assertTrue(result["all_passed"])
                self.assertTrue(result["capture_hash_matches"])
                self.assertEqual(result["frames"], 50)
                self.assertEqual(len(result["sessions"]), 5)
