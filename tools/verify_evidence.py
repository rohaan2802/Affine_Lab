"""Recompute the public evidence report. Run after installing the local package."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from affine_lab.analysis import chi_squared, rank_keys
from affine_lab.crypto import Key, decrypt
from affine_lab.protocol import LabServer
from affine_lab.providers import ReplayProvider
from affine_lab.runner import run_cases
from affine_lab.reporting import export_run, write_json
from affine_lab.validation import verify_recorded_run
from affine_lab.capture import inspect_pcap

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-demo",
        action="store_true",
        help="Replace the maintained replay report",
    )
    args = parser.parse_args()
    reports = [
        verify_recorded_run(ROOT / "data/recorded" / name)
        for name in ("submission", "tcp_baseline", "web_validation")
    ]
    text = reports[1]["sessions"][0]["response"]["ciphertext"]
    fast, reference = [], []
    for _ in range(7):
        start = time.perf_counter()
        ranked = rank_keys(text)
        fast.append(time.perf_counter() - start)
        start = time.perf_counter()
        naive = sorted(
            (chi_squared(decrypt(text, Key(c.a, c.b))), c.a, c.b) for c in ranked
        )
        reference.append(time.perf_counter() - start)
    assert all(
        abs(c.score - ref[0]) < 1e-8 and (c.a, c.b) == ref[1:]
        for c, ref in zip(ranked, naive)
    )
    write_json(
        ROOT / "reports/evidence_verification.json",
        {
            "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "all_passed": all(r["all_passed"] for r in reports),
            "runs": reports,
            "benchmark": {
                "repetitions": 7,
                "cipher_letters": sum(ch.isalpha() for ch in text),
                "histogram_median_ms": statistics.median(fast) * 1000,
                "full_text_reference_median_ms": statistics.median(reference) * 1000,
                "score_parity": True,
                "scope": "one recorded message on this machine; not a universal speed guarantee",
            },
        },
    )
    target = ROOT / "reports/replay_demo"
    if args.refresh_demo and (target / "capture.pcap").exists():
        raise ValueError(
            "Preserve the captured replay folder first; use the CLI for new timestamped runs"
        )
    if args.refresh_demo or not target.exists():
        provider = ReplayProvider()
        with LabServer(provider) as server:
            result = run_cases(server, provider)
        export_run(result, target, allow_existing=args.refresh_demo)
    if (target / "capture.pcap").exists():
        saved = json.loads((target / "result.json").read_text(encoding="utf-8"))
        captured = inspect_pcap(target / "capture.pcap", saved["tcp_port"])
        assert len(captured["sessions"]) == len(saved["sessions"]) == 5
        assert all(
            a["request"] == b["request"] and a["response"] == b["response"]
            for a, b in zip(captured["sessions"], saved["sessions"])
        )
    print("PASS: 3 captures, 15 sessions, 312-key score parity, maintained TCP replay")


if __name__ == "__main__":
    main()
