import unittest
from affine_lab.crypto import (
    Key,
    armor,
    dearmor,
    decrypt,
    encrypt,
    mood_key,
    VALID_MULTIPLIERS,
    clean_reply,
)


class CryptoTests(unittest.TestCase):
    def test_known_vector(self):
        self.assertEqual(encrypt("HELLO", Key(7, 6)), "DIFFA")
        self.assertEqual(decrypt("DIFFA", Key(7, 6)), "HELLO")
        self.assertEqual(encrypt("E", Key(7, 6)), "I")

    def test_all_312_key_round_trips(self):
        text = "Hello, World! café 2026 — اردو"
        for a in VALID_MULTIPLIERS:
            for b in range(26):
                with self.subTest(a=a, b=b):
                    key = Key(a, b)
                    self.assertEqual(decrypt(encrypt(text, key), key), text)
                    self.assertEqual(a * key.inverse % 26, 1)

    def test_utf8_armor_round_trip(self):
        for text in ["", "Rohaan", "café", "اردو 👋", "line\nnext"]:
            self.assertEqual(dearmor(armor(text)), text)
        self.assertEqual(armor("A"), "EB")

    def test_invalid_armor(self):
        for text in ["A", "AQ", "12", "ZZ", "PP"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                dearmor(text)

    def test_invalid_keys(self):
        for a, b in [(0, 1), (2, 1), (13, 4), (True, 0), (7, 26), (7, -1), (7, False)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                Key(a, b)

    def test_mood_key_schedule(self):
        expected = [
            (3, 2),
            (5, 4),
            (7, 6),
            (9, 8),
            (11, 10),
            (15, 12),
            (15, 14),
            (17, 16),
            (19, 18),
            (21, 20),
        ]
        self.assertEqual(
            [(mood_key(m).a, mood_key(m).b) for m in range(1, 11)], expected
        )
        for mood in [0, 11, True, "5"]:
            with self.assertRaises(ValueError):
                mood_key(mood)

    def test_protocol_reply_cleaning(self):
        self.assertEqual(
            clean_reply("Hi, Rohaan!\nTry 2 breaks."), "HI ROHAAN TRY  BREAKS"
        )
