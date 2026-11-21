"""Explicit recorded replay or optional live Gemini; never silent fallback."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
from .fixtures import load_cases


class ProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class ReplayProvider:
    mode: str = "replay"
    model: str = "recorded-gemini-3.5-flash-lite"

    def generate(self, username: str, mood: int, concern: str) -> str:
        for case in load_cases():
            if (case["username"], case["mood"], case["concern"]) == (
                username,
                mood,
                concern,
            ):
                return case["recorded_response"]
        raise ProviderError("Replay accepts only the five packaged synthetic cases")


def load_env(path: Path = Path(".env")) -> None:
    """Only read the two provider settings; never execute a shell file."""
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                if name.strip() in {"GEMINI_API_KEY", "GEMINI_MODEL"}:
                    os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


class GeminiProvider:
    mode = "gemini"

    def __init__(self, *, api_key: str | None = None, model: str | None = None):
        load_env()
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        if not self._api_key:
            raise ProviderError("GEMINI_API_KEY is not configured locally")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", self.model):
            raise ProviderError("Invalid model name")

    def generate(self, username: str, mood: int, concern: str) -> str:
        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "You are a supportive assistant in a fictional cryptography lab, not a clinician. "
                        "Respond in plain English in one paragraph of 6-8 sentences. "
                        "Include the synthetic user's name naturally. Do not diagnose, recommend medication, "
                        "request personal data, or claim professional qualifications."
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"Synthetic user: {username}. Mood: {mood}/10. Fictional concern: {concern}"
                        }
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1400},
        }
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json", "x-goog-api-key": self._api_key},
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    result = json.load(response)
                text = "".join(
                    p.get("text", "")
                    for c in result.get("candidates", [])
                    for p in c.get("content", {}).get("parts", [])
                    if not p.get("thought")
                )
                if not text.strip():
                    raise ProviderError(
                        "Gemini returned no text; no replay fallback was used"
                    )
                return text
            except urllib.error.HTTPError as exc:
                status = exc.code
                exc.close()
                if status in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise ProviderError(
                    f"Gemini HTTP {status}; check account access/quota privately"
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise ProviderError(
                    "Gemini transport timed out or failed; no fallback was used"
                ) from None
        raise ProviderError("Gemini request failed")


def make_provider(mode: str):
    if mode == "replay":
        return ReplayProvider()
    if mode == "gemini":
        return GeminiProvider()
    raise ValueError("provider must be replay or gemini")
