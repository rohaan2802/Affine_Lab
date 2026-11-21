"""Bounded CSV cryptanalysis with complete candidate/frequency exports."""

import csv
from pathlib import Path
from .analysis import analyze
from .reporting import write_json


def analyze_csv(source: Path, output: Path) -> dict:
    """Analyze English reply fields; never treat armored requests as English."""
    if source.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("CSV input exceeds 4 MiB")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new, empty batch output directory")
    rows, skipped = [], 0
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "ciphertext" not in reader.fieldnames:
            raise ValueError("CSV needs a ciphertext column")
        for index, item in enumerate(reader, 1):
            if index > 1000:
                raise ValueError("CSV exceeds 1000 input rows")
            if "field" in item and item["field"] != "ciphertext":
                skipped += 1
                continue
            text = item.get("ciphertext") or ""
            if len(text) > 20000:
                raise ValueError(f"Row {index} exceeds 20000 characters")
            try:
                result = analyze(text, include_candidates=True)
            except ValueError as exc:
                raise ValueError(f"Row {index}: {exc}") from None
            candidates = result.pop("candidates")
            rows.append(
                {
                    "input_row": index,
                    "session": item.get("session") or str(index),
                    "analysis": result,
                    "candidates": candidates,
                }
            )
    if not rows:
        raise ValueError("CSV contains no English reply ciphertext rows")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "mode": "csv-analysis",
        "source_name": source.name,
        "analyzed_rows": len(rows),
        "skipped_armored_rows": skipped,
        "verification": "Unverified language-fit candidates; no known-input comparison",
        "sessions": rows,
    }
    write_json(output / "analysis.json", report)
    definitions = [
        (
            "summary.csv",
            ["input_row", "session", "a", "b", "inverse", "letters", "chi_squared"],
            [
                [
                    r["input_row"],
                    r["session"],
                    r["analysis"]["a"],
                    r["analysis"]["b"],
                    r["analysis"]["a_inverse"],
                    r["analysis"]["letters"],
                    r["analysis"]["chi_squared"],
                ]
                for r in rows
            ],
        ),
        (
            "candidate_ranking.csv",
            ["input_row", "rank", "a", "b", "chi_squared"],
            [
                [r["input_row"], i, c["a"], c["b"], c["score"]]
                for r in rows
                for i, c in enumerate(r["candidates"], 1)
            ],
        ),
        (
            "letter_frequencies.csv",
            [
                "input_row",
                "letter",
                "cipher_count",
                "cipher_percent",
                "plain_percent",
                "english_percent",
            ],
            [
                [
                    r["input_row"],
                    *[
                        f[k]
                        for k in (
                            "letter",
                            "cipher_count",
                            "cipher_percent",
                            "plain_percent",
                            "english_percent",
                        )
                    ],
                ]
                for r in rows
                for f in r["analysis"]["frequencies"]
            ],
        ),
    ]
    for filename, header, data in definitions:
        with (output / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(data)
    return report
