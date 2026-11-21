"""Affine arithmetic and the lab's reversible UTF-8 nibble armor.

This is an educational substitution cipher, not secure encryption.
The generic cipher preserves case/nonletters; the wire protocol separately
normalizes replies and armors inputs to match the recorded implementation.
"""

from dataclasses import dataclass
from math import gcd

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
VALID_MULTIPLIERS = tuple(a for a in range(26) if gcd(a, 26) == 1)


@dataclass(frozen=True, slots=True)
class Key:
    a: int
    b: int

    def __post_init__(self):
        if type(self.a) is not int or self.a not in VALID_MULTIPLIERS:
            raise ValueError("a must be one of the 12 invertible residues modulo 26")
        if type(self.b) is not int or not 0 <= self.b < 26:
            raise ValueError("b must be an integer from 0 to 25")

    @property
    def inverse(self) -> int:
        return pow(self.a, -1, 26)


def mood_key(mood: int) -> Key:
    if type(mood) is not int or not 1 <= mood <= 10:
        raise ValueError("mood must be an integer from 1 to 10")
    b = 2 * mood
    a = b + 1
    while gcd(a, 26) != 1:
        a += 1
    return Key(a, b)


def _transform(text: str, multiplier: int, shift: int) -> str:
    result = []
    for char in text:
        base = 65 if "A" <= char <= "Z" else 97 if "a" <= char <= "z" else None
        result.append(
            chr((multiplier * (ord(char) - base) + shift) % 26 + base)
            if base is not None
            else char
        )
    return "".join(result)


def encrypt(text: str, key: Key) -> str:
    return _transform(text, key.a, key.b)


def decrypt(text: str, key: Key) -> str:
    return _transform(text, key.inverse, -key.inverse * key.b)


def armor(text: str) -> str:
    return "".join(
        chr(65 + (byte >> 4)) + chr(65 + (byte & 15)) for byte in text.encode("utf-8")
    )


def dearmor(text: str) -> str:
    compact = text.replace(" ", "")
    if len(compact) % 2 or any(not "A" <= char <= "P" for char in compact):
        raise ValueError("invalid A-P nibble armor")
    data = bytes(
        ((ord(compact[i]) - 65) << 4) | (ord(compact[i + 1]) - 65)
        for i in range(0, len(compact), 2)
    )
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("armor does not decode to UTF-8") from exc


def clean_reply(text: str) -> str:
    return "".join(
        c for c in text.upper().replace("\n", " ") if c in ALPHABET or c == " "
    )


def euclid_steps(a: int, modulus: int = 26) -> list[str]:
    r0, r1 = modulus, a % modulus
    steps = []
    while r1:
        quotient, remainder = divmod(r0, r1)
        steps.append(f"{r0} = {quotient} * {r1} + {remainder}")
        r0, r1 = r1, remainder
    return steps
