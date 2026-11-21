"""Run a real local TCP exchange, then recover and independently verify it."""

from datetime import datetime, timezone
from .fixtures import get_case
from .protocol import exchange
from .validation import validate_session
from .providers import ProviderError


def run_cases(server, provider, case_ids=range(1, 6)) -> dict:
    rows, failure = [], None
    requested = list(case_ids)
    for case_id in requested:
        try:
            case = get_case(case_id)
            transaction = exchange(case, server.address)
            row = validate_session(
                transaction, case, client_plaintext=transaction["client_plaintext"]
            )
            rows.append(row)
        except (ProviderError, OSError, ValueError):
            failure = f"Case {case_id} failed; completed results were preserved. No provider fallback was used."
            break
    return {
        "mode": provider.mode,
        "model": provider.model,
        "generation": "recorded response replay; no API call"
        if provider.mode == "replay"
        else "fresh Gemini response over HTTPS",
        "transport": "real IPv4 loopback TCP",
        "tcp_port": server.address[1],
        "run_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requested_cases": requested,
        "completed_cases": len(rows),
        "error": failure,
        "sessions": rows,
        "all_passed": failure is None
        and len(rows) == len(requested)
        and all(row["verified"] for row in rows),
    }
