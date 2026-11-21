"""Shared helpers for the attacker-side scripts (no key in here!)."""
import string

ALPHA = string.ascii_uppercase
# Relative letter frequencies of English text (%), from Lewand (2000),
# "Cryptological Mathematics", Mathematical Association of America.
ENGLISH_FREQ = {
    "A": 8.167, "B": 1.492, "C": 2.782, "D": 4.253, "E": 12.702, "F": 2.228,
    "G": 2.015, "H": 6.094, "I": 6.966, "J": 0.153, "K": 0.772, "L": 4.025,
    "M": 2.406, "N": 6.749, "O": 7.507, "P": 1.929, "Q": 0.095, "R": 5.987,
    "S": 6.327, "T": 9.056, "U": 2.758, "V": 0.978, "W": 2.360, "X": 0.150,
    "Y": 1.974, "Z": 0.074,
}
COMMON_WORDS = {"THE", "AND", "YOU", "TO", "OF", "A", "IS", "IT", "IN", "YOUR",
                "I", "MY", "FOR", "ARE", "THAT", "THIS", "CAN", "WITH", "BE",
                "NOT", "AM", "FEEL", "HELP", "PLEASE", "OR", "ON", "IF", "ME"}


def letter_counts(text: str) -> dict:
    c = {ch: 0 for ch in ALPHA}
    for ch in text.upper():
        if ch in c:
            c[ch] += 1
    return c


def chi_squared(text: str) -> float:
    c = letter_counts(text)
    n = sum(c.values()) or 1
    return sum((c[ch] - n * ENGLISH_FREQ[ch] / 100) ** 2 / (n * ENGLISH_FREQ[ch] / 100) for ch in ALPHA)


def egcd_steps(a: int, m: int):
    """Extended Euclid, returns (gcd, inverse or None, list of text lines)."""
    lines = []
    r0, r1 = m, a % m
    s0, s1 = 0, 1          # coefficients of a
    while r1:
        q = r0 // r1
        lines.append(f"{r0} = {q} x {r1} + {r0 - q * r1}")
        r0, r1 = r1, r0 - q * r1
        s0, s1 = s1, s0 - q * s1
    inv = s0 % m if r0 == 1 else None
    return r0, inv, lines


def affine_decrypt(text: str, a: int, b: int) -> str:
    _, inv, _ = egcd_steps(a, 26)
    out = []
    for ch in text:
        if ch.isupper() and ch in ALPHA:
            out.append(chr((inv * (ord(ch) - 65 - b)) % 26 + 65))
        elif "a" <= ch <= "z":
            out.append(chr((inv * (ord(ch) - 97 - b)) % 26 + 97))
        else:
            out.append(ch)
    return "".join(out)


def word_hit_rate(text: str) -> float:
    words = ["".join(ch for ch in w if ch.isalpha()).upper() for w in text.split()]
    words = [w for w in words if w]
    return sum(w in COMMON_WORDS for w in words) / max(len(words), 1)
