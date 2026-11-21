"""Portable exports with explicit run mode, timestamps and content hashes."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def export_run(result: dict, folder: Path, *, allow_existing: bool = False) -> Path:
    if folder.exists() and any(folder.iterdir()) and not allow_existing:
        raise FileExistsError(
            "Output directory is not empty; choose a new run directory"
        )
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "result.json", result)
    with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["session", "mood", "a", "b", "inverse", "chi_squared", "verified"]
        )
        for row in result["sessions"]:
            a = row["analysis"]
            writer.writerow(
                [
                    row["session"],
                    row["case"]["mood"],
                    a["a"],
                    a["b"],
                    a["a_inverse"],
                    a["chi_squared"],
                    row["verified"],
                ]
            )
    with (folder / "ciphertexts.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["session", "direction", "field", "ciphertext"])
        for row in result["sessions"]:
            for field in ["username_enc", "message_enc"]:
                writer.writerow(
                    [row["session"], "Client->Server", field, row["request"][field]]
                )
            writer.writerow(
                [
                    row["session"],
                    "Server->Client",
                    "ciphertext",
                    row["response"]["ciphertext"],
                ]
            )
    proofs, plaintext = [], []
    for row in result["sessions"]:
        proofs.append(
            f"SESSION {row['session']}\n" + "\n".join(row["analysis"]["proof"])
        )
        plaintext.append(
            f"SESSION {row['session']}\nUsername: {row['decoded_username']}\nConcern: {row['decoded_concern']}\nReply: {row['analysis']['plaintext']}"
        )
    (folder / "key_recovery_proof.txt").write_text(
        "\n\n".join(proofs) + "\n", encoding="utf-8"
    )
    (folder / "decrypted_sessions.txt").write_text(
        "\n\n".join(plaintext) + "\n", encoding="utf-8"
    )
    manifest = [
        {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(folder.iterdir())
        if path.is_file() and path.name != "manifest.json"
    ]
    write_json(
        folder / "manifest.json", {"mode": result.get("mode"), "files": manifest}
    )
    return folder
