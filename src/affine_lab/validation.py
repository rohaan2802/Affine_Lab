"""Post-recovery validation, deliberately separate from frequency scoring."""

import hashlib
import json
from pathlib import Path
from .analysis import analyze
from .crypto import Key, dearmor, decrypt, encrypt, mood_key
from .fixtures import get_case


def validate_session(
    session: dict, case: dict, *, client_plaintext: str | None = None
) -> dict:
    request, response = session["request"], session["response"]
    result = analyze(response["ciphertext"])
    candidate = Key(result["a"], result["b"])
    original_key = mood_key(case["mood"])
    try:
        username = dearmor(decrypt(request["username_enc"], candidate))
        concern = dearmor(decrypt(request["message_enc"], candidate))
    except ValueError:
        username, concern = "", ""
    expected_plain = (
        client_plaintext
        if client_plaintext is not None
        else decrypt(response["ciphertext"], original_key)
    )
    checks = {
        "key_matches": candidate == original_key,
        "mood_matches": request["mood"] == case["mood"],
        "username_matches": username == case["username"],
        "concern_matches": concern == case["concern"],
        "reply_matches": result["plaintext"] == expected_plain,
        "reencryption_matches": encrypt(result["plaintext"], candidate)
        == response["ciphertext"],
    }
    return {
        "session": case["id"],
        "case": {k: case[k] for k in ("id", "username", "mood", "concern")},
        "analysis": result,
        "decoded_username": username,
        "decoded_concern": concern,
        "request": request,
        "response": response,
        "checks": checks,
        "verified": all(checks.values()),
    }


def verify_recorded_run(folder: Path, *, parse_capture: bool = True) -> dict:
    from .capture import inspect_pcap

    sessions = json.loads((folder / "sessions.json").read_text(encoding="utf-8-sig"))
    if len(sessions) != 5:
        raise ValueError("recorded run must contain exactly five sessions")
    capture = inspect_pcap(folder / "capture.pcap") if parse_capture else None
    if capture is not None and len(capture["sessions"]) != 5:
        raise ValueError("capture must contain five complete sessions")
    results = []
    for index, session in enumerate(sessions, 1):
        result = validate_session(session, get_case(index))
        if capture is not None:
            actual = capture["sessions"][index - 1]
            result["checks"]["capture_request_matches"] = (
                actual["request"] == session["request"]
            )
            result["checks"]["capture_response_matches"] = (
                actual["response"] == session["response"]
            )
            result["verified"] = all(result["checks"].values())
        results.append(result)
    digest = hashlib.sha256((folder / "capture.pcap").read_bytes()).hexdigest()
    recorded = json.loads(
        (folder / "verification.json").read_text(encoding="utf-8-sig")
    )
    hash_matches = digest == recorded["pcap_sha256"]
    return {
        "run": folder.name,
        "mode": "recorded-evidence",
        "sessions": results,
        "capture_sha256": digest,
        "capture_hash_matches": hash_matches,
        "frames": capture["frames"] if capture else None,
        "all_passed": hash_matches and all(r["verified"] for r in results),
    }
