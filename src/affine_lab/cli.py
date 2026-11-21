"""Small command-line interface; default demo is offline recorded replay."""

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from . import __version__
from .analysis import analyze
from .capture import CaptureError, inspect_pcap
from .crypto import Key, decrypt, encrypt
from .providers import ProviderError, load_env, make_provider
from .protocol import LabServer
from .reporting import export_run, run_id, write_json
from .runner import run_cases
from .validation import verify_recorded_run


def parser():
    p = argparse.ArgumentParser(
        prog="affine-lab",
        description="Offline-first Affine cryptanalysis and a local TCP demo.",
    )
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    demo = commands.add_parser(
        "demo", help="Run five real local TCP exchanges and recover their keys"
    )
    demo.add_argument("--provider", choices=["replay", "gemini"], default="replay")
    demo.add_argument("--case", type=int, choices=range(1, 6))
    demo.add_argument("--tcp-port", type=int, default=0)
    demo.add_argument("--output", type=Path)
    demo.add_argument(
        "--capture",
        action="store_true",
        help="Also capture with tcpdump on Linux as root",
    )
    web = commands.add_parser("serve", help="Open a loopback-only dashboard")
    web.add_argument("--provider", choices=["replay", "gemini"], default="replay")
    web.add_argument("--http-port", type=int, default=8765)
    web.add_argument("--tcp-port", type=int, default=9999)
    web.add_argument("--output", type=Path, default=Path("runs"))
    verify = commands.add_parser(
        "verify", help="Independently recheck one recorded run"
    )
    verify.add_argument("folder", type=Path)
    verify.add_argument("--output", type=Path)
    capture = commands.add_parser(
        "inspect-pcap", help="Read/reassemble lab evidence without capture privileges"
    )
    capture.add_argument("file", type=Path)
    capture.add_argument("--port", type=int, default=9999)
    capture.add_argument("--output", type=Path)
    attack = commands.add_parser(
        "analyze", help="Rank all 312 keys for a ciphertext string"
    )
    attack.add_argument("ciphertext")
    batch = commands.add_parser(
        "analyze-csv", help="Analyze English reply rows and export all candidate scores"
    )
    batch.add_argument("file", type=Path)
    batch.add_argument("--output", type=Path, required=True)
    cipher = commands.add_parser(
        "cipher", help="Encrypt/decrypt text with an explicit key"
    )
    cipher.add_argument("action", choices=["encrypt", "decrypt"])
    cipher.add_argument("text")
    cipher.add_argument("--a", type=int, required=True)
    cipher.add_argument("--b", type=int, required=True)
    commands.add_parser(
        "doctor", help="Check local prerequisites without printing any key"
    )
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            load_env()
            print(
                json.dumps(
                    {
                        "python": sys.version.split()[0],
                        "runtime_dependencies": 0,
                        "replay_ready": True,
                        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
                        "model": os.environ.get(
                            "GEMINI_MODEL", "gemini-3.5-flash-lite"
                        ),
                        "tcpdump_available": bool(shutil.which("tcpdump")),
                        "capture_requires": "Linux root + tcpdump; reading saved PCAPs needs neither",
                    },
                    indent=2,
                )
            )
        elif args.command == "cipher":
            fn = encrypt if args.action == "encrypt" else decrypt
            print(fn(args.text, Key(args.a, args.b)))
        elif args.command == "analyze":
            print(json.dumps(analyze(args.ciphertext), indent=2))
        elif args.command == "analyze-csv":
            from .batch import analyze_csv

            result = analyze_csv(args.file, args.output)
            print(
                f"Analyzed {result['analyzed_rows']} replies; skipped {result['skipped_armored_rows']} armored fields. Export: {args.output}"
            )
        elif args.command == "inspect-pcap":
            result = inspect_pcap(args.file, args.port)
            if args.output:
                write_json(args.output, result)
            print(
                json.dumps(
                    {k: v for k, v in result.items() if k != "sessions"}
                    | {"sessions": len(result["sessions"])},
                    indent=2,
                )
            )
        elif args.command == "verify":
            result = verify_recorded_run(args.folder)
            if args.output:
                write_json(args.output, result)
            print(
                f"{args.folder.name}: {len(result['sessions'])}/5 sessions; capture hash {'MATCH' if result['capture_hash_matches'] else 'MISMATCH'}; {'PASS' if result['all_passed'] else 'FAIL'}"
            )
            return 0 if result["all_passed"] else 1
        elif args.command == "serve":
            from .web import Dashboard

            Dashboard(
                make_provider(args.provider),
                http_port=args.http_port,
                tcp_port=args.tcp_port,
                output=args.output,
            ).serve()
        elif args.command == "demo":
            provider = make_provider(args.provider)
            output = args.output or Path("runs") / run_id()
            if output.exists() and any(output.iterdir()):
                raise ValueError("Choose a new, empty output directory")
            capture = None
            with LabServer(provider, args.tcp_port) as server:
                if args.capture:
                    if (
                        sys.platform != "linux"
                        or os.geteuid() != 0
                        or not shutil.which("tcpdump")
                    ):
                        raise ValueError(
                            "--capture needs Linux root and tcpdump; offline replay itself does not"
                        )
                    output.mkdir(parents=True, exist_ok=True)
                    capture = subprocess.Popen(
                        [
                            "tcpdump",
                            "-i",
                            "lo",
                            "-U",
                            "-n",
                            "-s",
                            "0",
                            "-Z",
                            "root",
                            "-w",
                            str(output / "capture.pcap"),
                            "tcp",
                            "port",
                            str(server.address[1]),
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                    time.sleep(0.5)
                    if capture.poll() is not None:
                        _, log = capture.communicate()
                        (output / "capture.log").write_bytes(log)
                        raise ValueError(
                            "tcpdump did not start; see the local capture.log"
                        )
                try:
                    result = run_cases(
                        server, provider, [args.case] if args.case else range(1, 6)
                    )
                finally:
                    if capture is not None and capture.poll() is None:
                        # Let libpcap's kernel buffer deliver the final packets.
                        time.sleep(1.2)
                        capture.send_signal(signal.SIGINT)
                        _, log = capture.communicate(timeout=10)
                        (output / "capture.log").write_bytes(log)
                result["packet_capture"] = bool(args.capture)
                export_run(result, output, allow_existing=bool(args.capture))
            print(f"Mode: {result['mode']} | {result['generation']}")
            for row in result["sessions"]:
                a = row["analysis"]
                print(
                    f"Case {row['session']}: a={a['a']}, b={a['b']}, inverse={a['a_inverse']} | {'PASS' if row['verified'] else 'FAIL'}"
                )
            print(f"Export: {output}\n{'PASS' if result['all_passed'] else 'FAIL'}")
            return 0 if result["all_passed"] else 1
        return 0
    except (ValueError, OSError, ProviderError, CaptureError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
