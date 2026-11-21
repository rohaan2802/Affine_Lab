"""Ciphertext-only frequency scoring. No mood schedule or server imports.

Count letters once, then permute 26 bins for each candidate. This avoids
decrypting the entire message 312 times. Only shortlisted text is materialized.
"""

from collections import Counter
from dataclasses import asdict, dataclass
from .crypto import ALPHABET, VALID_MULTIPLIERS, Key, decrypt, euclid_steps

# Lewand, Cryptological Mathematics (2000), percentages.
ENGLISH = (
    8.167,
    1.492,
    2.782,
    4.253,
    12.702,
    2.228,
    2.015,
    6.094,
    6.966,
    0.153,
    0.772,
    4.025,
    2.406,
    6.749,
    7.507,
    1.929,
    0.095,
    5.987,
    6.327,
    9.056,
    2.758,
    0.978,
    2.360,
    0.150,
    1.974,
    0.074,
)


@dataclass(frozen=True, slots=True)
class Candidate:
    score: float
    a: int
    b: int

    def to_dict(self):
        return asdict(self)


def counts(text: str) -> list[int]:
    counter = Counter(c for c in text.upper() if c in ALPHABET)
    return [counter[c] for c in ALPHABET]


def chi_squared(text: str) -> float:
    observed = counts(text)
    total = sum(observed)
    if not total:
        raise ValueError("frequency analysis needs ASCII letters")
    return sum(
        (value - total * freq / 100) ** 2 / (total * freq / 100)
        for value, freq in zip(observed, ENGLISH, strict=True)
    )


def rank_keys(ciphertext: str) -> list[Candidate]:
    cipher_counts = counts(ciphertext)
    total = sum(cipher_counts)
    if not total:
        raise ValueError("ciphertext has no ASCII letters to analyze")
    expected = [total * freq / 100 for freq in ENGLISH]
    candidates = []
    for a in VALID_MULTIPLIERS:
        for b in range(26):
            score = sum(
                (cipher_counts[(a * p + b) % 26] - expected[p]) ** 2 / expected[p]
                for p in range(26)
            )
            candidates.append(Candidate(score, a, b))
    return sorted(
        candidates, key=lambda candidate: (candidate.score, candidate.a, candidate.b)
    )


def analyze(ciphertext: str, *, include_candidates: bool = False) -> dict:
    """Recover a candidate; optionally retain the complete ranking for exports."""
    ranked = rank_keys(ciphertext)
    winner = ranked[0]
    key = Key(winner.a, winner.b)
    plain = decrypt(ciphertext, key)
    observed = counts(ciphertext)
    plain_counts = counts(plain)
    total = sum(observed)
    c_e, c_t = (4 * key.a + key.b) % 26, (19 * key.a + key.b) % 26
    proof = [
        "A=0 ... Z=25; C=(a*P+b) mod 26.",
        "312 valid keys scored against English; E/T are candidate correspondences, not guaranteed frequency ranks.",
        f"Winning correspondence E->{ALPHABET[c_e]}, T->{ALPHABET[c_t]}.",
        f"4a+b={c_e}; 19a+b={c_t} (mod 26).",
        f"15a={(c_t - c_e) % 26} (mod 26); inverse(15)=7 because 15*7=4*26+1.",
        f"a=7*{(c_t - c_e) % 26} mod 26={key.a}; b={c_e}-4*{key.a} mod 26={key.b}.",
        *euclid_steps(key.a),
        f"inverse(a)={key.inverse}; {key.a}*{key.inverse}={(key.a * key.inverse) // 26}*26+1.",
        f"P={key.inverse}*(C-{key.b}) mod 26.",
    ]
    result = {
        "a": key.a,
        "b": key.b,
        "a_inverse": key.inverse,
        "chi_squared": winner.score,
        "runner_up_chi_squared": ranked[1].score,
        "letters": total,
        "plaintext": plain,
        "top_candidates": [c.to_dict() for c in ranked[:5]],
        "proof": proof,
        "frequencies": [
            {
                "letter": c,
                "cipher_count": observed[i],
                "cipher_percent": 100 * observed[i] / total,
                "plain_percent": 100 * plain_counts[i] / total,
                "english_percent": ENGLISH[i],
            }
            for i, c in enumerate(ALPHABET)
        ],
        "note": "Language-fit ranking is not a probability; verify short or unusual text independently.",
    }
    if include_candidates:
        result["candidates"] = [candidate.to_dict() for candidate in ranked]
    return result
