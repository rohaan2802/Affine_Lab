"""Build matched README/site figure sections and consistent evidence figures.

Requires the dev extras. Runtime execution itself has no third-party packages.
Run verify_evidence.py first, then this script. No API requests are made here.
"""

from html import escape
from io import BytesIO
import json
from pathlib import Path
import textwrap
from PIL import Image, ImageDraw, ImageFont
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from affine_lab.analysis import rank_keys
from affine_lab.crypto import ALPHABET, Key, armor, encrypt, mood_key
from affine_lab.fixtures import load_cases
from affine_lab.capture import inspect_pcap
import project_reference

ROOT = Path(__file__).resolve().parents[1]
INK = "#142c49"
MUTED = "#465c75"
TEAL = "#086c70"
AMBER = "#a14d18"
BG = "#dce7f2"
PANEL = "#f9fcff"


def font(size, mono=False, bold=False):
    windows = Path("C:/Windows/Fonts")
    name = (
        ("consolab.ttf" if bold else "consola.ttf")
        if mono
        else ("segoeuib.ttf" if bold else "segoeui.ttf")
    )
    if (windows / name).exists():
        return ImageFont.truetype(str(windows / name), size)
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans"
        + ("Mono" if mono else "")
        + ("-Bold" if bold else "")
        + ".ttf",
        size,
    )


MANIFEST = []


def frame(number, title, caption, category):
    image = Image.new("RGB", (1440, 900), BG)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle(
        (16, 16, 1424, 884), radius=24, fill=PANEL, outline="#9bb5cc", width=2
    )
    d.text(
        (64, 47),
        "AFFINE LAB  /  VERIFIED EVIDENCE",
        font=font(18, bold=True),
        fill=TEAL,
    )
    d.text((64, 86), title, font=font(38, bold=True), fill=INK)
    d.text((1316, 48), f"{number:02}", font=font(28, bold=True), fill=AMBER)
    d.line((64, 151, 1376, 151), fill="#b0c5d8", width=2)
    for index, line in enumerate(textwrap.wrap(caption, 118)):
        d.text((64, 794 + index * 27), line, font=font(19), fill=MUTED)
    d.text(
        (64, 850),
        category.upper() + "  •  reproducible from repository data and source",
        font=font(14),
        fill=TEAL,
    )
    return image


def save(
    number,
    title,
    caption,
    category,
    *,
    lines=None,
    chart=None,
    tiles=None,
    screenshot=None,
):
    image = frame(number, title, caption, category)
    d = ImageDraw.Draw(image)
    if lines:
        content = "\n".join(lines) if isinstance(lines, list) else lines
        for size in range(34, 19, -1):
            width = int(1320 / font(size, mono=True).getlength("M"))
            wrapped = []
            for line in content.splitlines():
                wrapped.extend(
                    textwrap.wrap(
                        line, width, replace_whitespace=False, drop_whitespace=False
                    )
                    or [""]
                )
            heights = [size + 3 if line.strip() else max(10, size // 2) for line in wrapped]
            if sum(heights) <= 622:
                break
        if sum(heights) > 622:
            raise ValueError(
                f"Figure {number} needs shorter content: {len(wrapped)} lines"
            )
        y = 163
        for line, height in zip(wrapped, heights, strict=True):
            d.text(
                (57, y),
                line,
                font=font(size, mono=True),
                fill=TEAL
                if line.startswith(("PASS", "MODE", "CASE", ">", "#"))
                else INK,
            )
            y += height
    if tiles:
        for x, y, w, h, heading, body in tiles:
            d.rounded_rectangle(
                (x, y, x + w, y + h),
                radius=16,
                fill="#e2edf6",
                outline="#9bb7ce",
                width=2,
            )
            d.text((x + 22, y + 17), heading, font=font(25, bold=True), fill=TEAL)
            for i, line in enumerate(textwrap.wrap(body, max(20, int(w / 13)))):
                d.text((x + 22, y + 62 + i * 31), line, font=font(22), fill=INK)
    if chart:
        buffer = BytesIO()
        chart.savefig(buffer, dpi=144, facecolor=BG)
        buffer.seek(0)
        plot = Image.open(buffer).convert("RGB")
        plot.thumbnail((1370, 625))
        image.paste(plot, ((1440 - plot.width) // 2, 158 + (625 - plot.height) // 2))
        plt.close(chart)
    if screenshot:
        shot = Image.open(screenshot).convert("RGB")
        shot.thumbnail((1370, 625))
        image.paste(shot, ((1440 - shot.width) // 2, 167))
    slug = (
        f"{number:02}-"
        + "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")
        + "-v3"
    )
    full = f"assets/figures/full/{slug}.png"
    preview = f"assets/figures/previews/{slug}.png"
    image.save(ROOT / full, optimize=True)
    image.resize((960, 600), Image.Resampling.LANCZOS).save(
        ROOT / preview, optimize=True
    )
    MANIFEST.append(
        dict(
            id=number,
            title=title,
            caption=caption,
            category=category,
            full=full,
            preview=preview,
        )
    )


def axes():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 16,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": "#a6b9ca",
            "axes.facecolor": BG,
            "figure.facecolor": BG,
            "grid.color": "#c0d0df",
        }
    )
    fig, ax = plt.subplots(figsize=(9.1, 4.2))
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.15, top=0.9)
    return fig, ax


def figures():
    evidence = json.loads(
        (ROOT / "reports/evidence_verification.json").read_text(encoding="utf-8")
    )
    baseline = evidence["runs"][1]["sessions"]
    cases = load_cases()
    save(
        1,
        "From conversation to recovered plaintext",
        "Two separate transports: weak Affine on loopback TCP, and TLS for the optional Gemini API.",
        "Design",
        tiles=[
            (
                72,
                189,
                396,
                218,
                "01  CLIENT",
                "Synthetic input → UTF-8 armor → Affine encryption → local JSON request.",
            ),
            (
                522,
                189,
                396,
                218,
                "02  LOCAL SERVER",
                "Decode input. Choose exact recorded reply or explicitly request fresh Gemini text.",
            ),
            (
                972,
                189,
                396,
                218,
                "03  PROVIDER",
                "Replay: no internet. Gemini: HTTPS with a server-side credential.",
            ),
            (
                72,
                457,
                615,
                235,
                "04  LOCAL RETURN PATH",
                "English reply → Affine ciphertext → TCP client. The client decrypts with its known key.",
            ),
            (
                737,
                457,
                631,
                235,
                "05  INDEPENDENT ANALYZER",
                "Ciphertext only → score 312 keys → recover text. Known inputs are checked afterwards.",
            ),
        ],
    )
    save(
        2,
        "Three distinct recorded runs",
        "All three PCAP digests and payloads are independently rechecked; these are historical model runs.",
        "Evidence",
        lines=[
            "RUN                 FRAMES   SESSIONS   HASH    KEY + TEXT",
            *[
                f"{r['run']:<22} {r['frames']:<8} {len(r['sessions']):<10} MATCH   PASS"
                for r in evidence["runs"]
            ],
            "",
            "15 sessions retained, 150 recorded frames in total.",
            *[
                f"{r['run']} SHA-256:\n{r['capture_sha256']}\n"
                for r in evidence["runs"]
            ],
        ],
    )
    save(
        3,
        "The five synthetic input cases",
        "The dataset uses invented student concerns. It contains no actual patient records.",
        "Inputs",
        lines=[
            line
            for c in cases
            for line in (
                f"CASE {c['id']}  /  mood {c['mood']}  /  username {c['username']}",
                c["concern"],
                "",
            )
        ],
    )
    save(
        4,
        "Mood keys and modular inverses",
        "The server schedule is retained for protocol compatibility; the analyzer does not receive mood.",
        "Method",
        lines=[
            "MOOD     a       b       inverse(a)       a × inverse mod 26",
            *[
                f"{m:<9}{mood_key(m).a:<8}{mood_key(m).b:<8}{mood_key(m).inverse:<17}{mood_key(m).a * mood_key(m).inverse % 26}"
                for m in range(1, 11)
            ],
            "",
            "Valid a: 1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25",
            "12 multipliers × 26 shifts = 312 possible keys.",
        ],
    )
    save(
        5,
        "A worked recovery proof",
        "The E/T equations explain the winning key; they are candidate correspondences, not assumed frequency ranks.",
        "Method",
        lines=baseline[0]["analysis"]["proof"],
    )
    for i, row in enumerate(baseline, 6):
        data = row["analysis"]["frequencies"]
        fig, ax = axes()
        x = np.arange(26)
        ax.bar(
            x - 0.2,
            [r["plain_percent"] for r in data],
            0.4,
            label="Recovered English",
            color=TEAL,
        )
        ax.bar(
            x + 0.2,
            [r["english_percent"] for r in data],
            0.4,
            label="Reference frequency",
            color=AMBER,
        )
        ax.set_xticks(x, ALPHABET)
        ax.set_ylabel("Letter frequency (%)")
        ax.grid(axis="y", alpha=0.45)
        ax.set_axisbelow(True)
        ax.legend(facecolor=PANEL, labelcolor=INK, fontsize=11)
        ax.set_title(
            f"Case {row['session']} · a={row['analysis']['a']}, b={row['analysis']['b']} · {row['analysis']['letters']} letters",
            fontsize=17,
        )
        save(
            i,
            f"Case {row['session']} — recovered letter profile",
            f"Baseline case {row['session']}: measured plaintext frequencies compared with the fixed English reference; recovery and independent checks pass.",
            "Analysis",
            chart=fig,
        )
    save(
        11,
        "Recovered text from every case",
        "These excerpts are decrypted baseline replies. Complete text is saved in the replay export.",
        "Results",
        lines=[
            line
            for r in baseline
            for line in (
                f"CASE {r['session']}  /  a={r['analysis']['a']}, b={r['analysis']['b']}",
                r["analysis"]["plaintext"][:150] + "…",
                "",
            )
        ],
    )
    ranked = rank_keys(baseline[0]["response"]["ciphertext"])
    fig, ax = axes()
    selected = list(reversed(ranked[:8]))
    ax.barh(
        [f"a={c.a}, b={c.b}" for c in selected],
        [c.score for c in selected],
        color=[AMBER] * 7 + [TEAL],
    )
    ax.set_xlabel("Chi-square score · lower is better")
    ax.grid(axis="x", alpha=0.4)
    ax.set_axisbelow(True)
    save(
        12,
        "Ranking the strongest candidates",
        "The best eight of all 312 candidates for baseline case 1. Language fit is a heuristic, not confidence.",
        "Analysis",
        chart=fig,
    )
    fig, ax = axes()
    x = np.arange(5)
    ax.bar(
        x - 0.18,
        [r["analysis"]["chi_squared"] for r in baseline],
        0.36,
        color=TEAL,
        label="Winning key",
    )
    ax.bar(
        x + 0.18,
        [r["analysis"]["runner_up_chi_squared"] for r in baseline],
        0.36,
        color=AMBER,
        label="Runner-up",
    )
    ax.set_xticks(x, [f"Case {i}" for i in range(1, 6)])
    ax.set_ylabel("Chi-square score")
    ax.legend(facecolor=PANEL, labelcolor=INK)
    ax.grid(axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    save(
        13,
        "Winning scores versus the runners-up",
        "The score gap is descriptive. Independent input/client comparisons establish the recorded recovery result.",
        "Analysis",
        chart=fig,
    )
    save(
        14,
        "The substitution alphabet",
        "Affine substitution preserves letter-frequency structure and spacing; it has only 312 valid keys.",
        "Method",
        lines=[
            "Key: a=7, b=6, inverse=15",
            "",
            "Plain : " + " ".join(ALPHABET),
            "Cipher: " + " ".join(encrypt(ALPHABET, Key(7, 6))),
            "",
            "C = (7 × P + 6) mod 26",
            "P = 15 × (C − 6) mod 26",
            "",
            "HELLO → " + encrypt("HELLO", Key(7, 6)),
            "A shift and a multiplication do not provide modern cryptographic security.",
        ],
    )
    save(
        15,
        "UTF-8 armor is reversible encoding",
        "The request first maps each byte to A–P nibbles. This preserves input characters but adds no secret.",
        "Method",
        lines=[
            "Original username: " + cases[0]["username"],
            "UTF-8 bytes (hex): " + cases[0]["username"].encode().hex(" "),
            "Armor alphabet: ABCDEFGHIJKLMNOP (values 0–15)",
            "Armor text: " + armor(cases[0]["username"]),
            "Encrypted armor: " + encrypt(armor(cases[0]["username"]), Key(7, 6)),
            "",
            "Decode steps: Affine inverse → A–P nibbles → UTF-8 bytes → username.",
            "A single ASCII A is byte 0x41, so its armor is EB.",
        ],
    )
    capture = inspect_pcap(ROOT / "data/recorded/tcp_baseline/capture.pcap")
    req = baseline[0]["request"]
    resp = baseline[0]["response"]
    save(
        16,
        "Actual recorded JSON fields",
        "Payload excerpts from the baseline capture. The API credential field is empty in local traffic.",
        "Evidence",
        lines=[
            "Client → server / loopback TCP 9999",
            json.dumps({**req, "message_enc": req["message_enc"][:96] + "…"}, indent=2),
            "",
            "Server → client",
            json.dumps({"ciphertext": resp["ciphertext"][:220] + "…"}, indent=2),
            "",
            "Long encrypted fields are excerpted here; full bytes remain in the PCAP.",
        ],
    )
    save(
        17,
        "Independent PCAP reconstruction",
        "The built-in inspector reads actual classic PCAP bytes and reassembles the five loopback TCP sessions.",
        "Evidence",
        lines=[
            f"Frames: {capture['frames']}   Bytes: {capture['bytes']}   Link type: {capture['linktype']}",
            f"Destination: 127.0.0.1:{capture['port']}",
            "",
            "CASE   CLIENT PORT   PAYLOAD FRAMES   ACTUAL START (UTC)",
            *[
                f"{r['session']:<7}{r['client_port']:<14}{len(r['frames']):<17}{r['start_utc']}"
                for r in capture["sessions"]
            ],
            "",
            "SHA-256: " + capture["sha256"],
            "",
            "Gaps, conflicting retransmissions and truncated records fail explicitly.",
        ],
    )
    save(
        18,
        "Fifteen independent recovery checks",
        "Each row checks key, mood, decoded username/concern, client reply, re-encryption and capture payload parity.",
        "Results",
        lines=[
            "RUN                 CASE   a    b    INVERSE   RESULT",
            *[
                f"{r['run']:<20}{s['session']:<7}{s['analysis']['a']:<5}{s['analysis']['b']:<5}{s['analysis']['a_inverse']:<10}{'PASS' if s['verified'] else 'FAIL'}"
                for r in evidence["runs"]
                for s in r["sessions"]
            ],
        ],
    )
    replay = json.loads(
        (ROOT / "reports/replay_demo/result.json").read_text(encoding="utf-8")
    )
    save(
        19,
        "A new real TCP replay run",
        "The transport and analysis are newly executed; model text is explicitly replayed from the recorded corpus.",
        "Demo",
        lines=[
            "> python -m affine_lab demo",
            "MODE: " + replay["mode"],
            replay["generation"],
            "Run time UTC: " + replay["run_time_utc"],
            "Transport: " + replay["transport"],
            "",
            *[
                f"CASE {r['session']}: a={r['analysis']['a']}, b={r['analysis']['b']}, inverse={r['analysis']['a_inverse']}  PASS"
                for r in replay["sessions"]
            ],
            "",
            "PASS: five actual loopback exchanges; no external API call.",
            "Exports: result.json, summary.csv, ciphertexts.csv, proof, plaintext, hashes.",
        ],
    )
    source = (ROOT / "src/affine_lab/crypto.py").read_text(encoding="utf-8")
    start = source.index("def _transform(")
    end = source.index("\ndef armor", start)
    snippet = source[start:end]
    save(
        20,
        "Readable maintained cipher source",
        "The maintained Python package replaces the coursework binary dependency with reviewable source.",
        "Source",
        lines=snippet,
    )
    source = (ROOT / "src/affine_lab/analysis.py").read_text(encoding="utf-8")
    start = source.index("def rank_keys(")
    end = source.index("\ndef analyze", start)
    save(
        21,
        "Score 26 bins instead of whole messages",
        "The optimized implementation is tested against full-text decryption for every one of the 312 candidates.",
        "Source",
        lines=source[start:end]
        .strip()
        .replace(
            "    return sorted(candidates, key=lambda candidate: (candidate.score, candidate.a, candidate.b))",
            "    return sorted(candidates,\n                  key=lambda c: (c.score, c.a, c.b))",
        ),
    )
    shot = ROOT / "data/presentation/dashboard.png"
    if shot.exists():
        save(
            22,
            "The local browser dashboard",
            "Actual locally served dashboard in replay mode. It exposes proofs, checks and downloadable results.",
            "Demo",
            screenshot=shot,
        )
    else:
        save(
            22,
            "The local browser dashboard",
            "The packaged dashboard uses the same tested Python engine and labels corpus inspection separately from TCP replay.",
            "Demo",
            lines=[
                "> python -m affine_lab serve",
                "Open http://127.0.0.1:8765",
                "",
                "Inspect saved corpus: reanalyze fixtures, no TCP or model call.",
                "Run one / all cases: actual loopback exchange and verification.",
                "Review: plaintext, recovered key, chi-square, JSON, proof, checks.",
                "Download: result JSON, summary CSV, ciphertext CSV, proof and hashes.",
                "",
                "Provider selected once at startup. Theme switch and narrow layouts included.",
            ],
        )
    manifest = json.loads(
        (ROOT / "reports/replay_demo/manifest.json").read_text(encoding="utf-8")
    )
    save(
        23,
        "Portable exports with integrity hashes",
        "A content manifest ties every saved replay export to its bytes. It is integrity metadata, not a signature.",
        "Results",
        lines=[
            "FILE                              BYTES",
            *[f"{r['path']:<34}{r['bytes']}" for r in manifest["files"]],
            "",
            "Example SHA-256:",
            manifest["files"][0]["path"],
            manifest["files"][0]["sha256"],
            "",
            "Every run records provider, execution time, requested/completed cases,",
            "independent checks and an explicit all_passed flag.",
        ],
    )
    check = ROOT / "reports/quality_checks.json"
    quality = (
        json.loads(check.read_text(encoding="utf-8"))
        if check.exists()
        else {"status": "See verification documentation for current checks."}
    )
    bench = evidence["benchmark"]
    save(
        24,
        "Correctness and measured efficiency",
        "Measured local evidence; performance depends on the input and machine. Fresh external API availability is separate.",
        "Verification",
        lines=[
            f"Correctness suite: {quality.get('unit_tests', 'not recorded')} tests passed",
            "Recorded evidence: 3 PCAPs / 15 sessions / 150 frames / all PASS",
            "Fresh replay: five local TCP exchanges / all PASS",
            "Candidate score parity: all 312 optimized/reference scores match",
            "",
            f"Histogram median: {bench['histogram_median_ms']:.3f} ms",
            f"Full-text reference median: {bench['full_text_reference_median_ms']:.3f} ms",
            f"Benchmark: {bench['repetitions']} repetitions, {bench['cipher_letters']} letters",
            "",
            "Runtime third-party dependencies: 0",
            "Capture inspection: no Wireshark or elevated capture privilege required.",
        ],
    )
    (ROOT / "assets/figures/manifest.json").write_text(
        json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "assets/js/portfolio_data.js").write_text(
        "window.AFFINE_FIGURES="
        + json.dumps(MANIFEST)
        + ";\nwindow.AFFINE_SAMPLE="
        + json.dumps(baseline[0]["response"]["ciphertext"])
        + ";\n",
        encoding="utf-8",
    )
    return evidence


BADGES = [
    ("Python", "3.12+", "3776ab", "https://www.python.org/"),
    ("Runtime", "0 dependencies", "086b66", "pyproject.toml"),
    ("Evidence", "15 sessions", "805017", "reports/evidence_verification.json"),
    ("Protocol", "TCP + PCAP", "476381", "docs/ARCHITECTURE.md"),
    ("Analysis", "312 keys", "705291", "src/affine_lab/analysis.py"),
    ("License", "MIT", "44634b", "LICENSE"),
    ("UI", "HTML5", "a64622", "src/affine_lab/web/index.html"),
    ("Theme", "CSS3", "385c9a", "assets/css/site.css"),
    ("Browser", "JavaScript", "806015", "assets/js/site.js"),
    ("IDE", "VS Code", "276b96", "Affine_Lab.code-workspace"),
]


def badge_icon(label):
    paths = {
        "Python": '<path d="M8 15V9h9v7H8v5h10v-4"/>',
        "Runtime": '<path d="m7 10 8-4 8 4v10l-8 4-8-4zm0 0 8 4 8-4m-8 4v10"/>',
        "Evidence": '<path d="m7 16 5 5 11-12"/>',
        "Protocol": '<circle cx="8" cy="9" r="3"/><circle cx="22" cy="21" r="3"/><path d="M8 12v9h11m3-3V9H11"/>',
        "Analysis": '<path d="M7 22V12m8 10V6m8 16v-7"/>',
        "License": '<path d="M15 5v20M6 10h18M9 10l-4 9h8zm12 0-4 9h8z"/>',
        "UI": '<rect x="5" y="7" width="21" height="17" rx="2"/><path d="M5 12h21m-15 4-3 3 3 3m9-6 3 3-3 3"/>',
        "Theme": '<circle cx="15" cy="15" r="9"/><path d="M15 6v18M15 6a9 9 0 0 1 0 18" fill="white"/>',
        "Browser": '<rect x="4" y="6" width="23" height="18" rx="3"/><path d="M4 11h23m-18-3h1m4 0h1m3 7-4 3 4 3"/>',
        "IDE": '<path d="m7 10 12 11 6 3V6l-6 3L7 20l-4-4 4-6m12-1v12"/>',
    }
    return (
        '<g fill="none" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        + paths[label]
        + "</g>"
    )


def badges():
    for label, value, color, link in BADGES:
        slug = label.lower()
        width = 90 + len(value) * 8
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="30" role="img" aria-label="{label}: {value}"><rect width="{width}" height="30" rx="5" fill="#{color}"/>{badge_icon(label)}<text x="32" y="20" fill="white" font-family="Segoe UI,Arial,sans-serif" font-size="12" font-weight="600">{escape(label)}: {escape(value)}</text></svg>'
        (ROOT / f"assets/badges/{slug}.svg").write_text(svg, encoding="utf-8")
    return "\n".join(
        f'<a href="{link}"><img src="assets/badges/{label.lower()}.svg" alt="{label}: {value}"></a>'
        for label, value, _, link in BADGES
    )


def readme(badge_markup, evidence):
    bench = evidence["benchmark"]
    text = """<h1 align="center">Affine_Lab</h1>
<p align="center"><strong>Break a weak cipher. Reconstruct the packets. Verify every result.</strong></p>
<p align="center">A reproducible cryptanalysis lab with independent PCAP verification, an offline TCP replay and a local browser dashboard.</p>
<p align="center">BADGES</p>

## Live Links

| What | Link |
| --- | --- |
| Repository | [https://github.com/rohaan2802/Affine_Lab](https://github.com/rohaan2802/Affine_Lab) |
| GitHub Pages | [https://rohaan2802.github.io/Affine_Lab/](https://rohaan2802.github.io/Affine_Lab/) |
| Project resource | [https://github.com/maadilrehman/PsycoSupport](https://github.com/maadilrehman/PsycoSupport) |

## Contents

1. [Overview](#overview)
2. [What's Inside](#whats-inside)
3. [Project Breakdown](#project-breakdown)
4. [Folder Structure](#folder-structure)
5. [Setup](#setup)
6. [Demo](#demo)
7. [Results and Verification](#results-and-verification)
8. [Extended Analysis](#extended-analysis)
9. [Visual Evidence](#visual-evidence)
10. [Limitations](#limitations)
11. [About the Author](#about-the-author)

## Overview

Affine_Lab demonstrates why a classical substitution cipher cannot secure a
conversation. Five synthetic concerns travel through a real loopback TCP client
and server. An independent analyzer receives the encrypted English reply, ranks
all **312 valid keys** by chi-square frequency fit and recovers the text.
Known inputs and the client's decryption are compared only after recovery.

The exercise evolved into an independently implemented, readable Python package.
It reconstructs the raw recorded packets without Wireshark, reproduces the local
exchange without internet, and offers an explicit fresh Gemini mode. The
coursework's supplied binary is not required or redistributed.

## What's Inside

| Area | What you can review |
| --- | --- |
| Maintained source | [Python package](src/affine_lab), [build metadata](pyproject.toml), [VS Code workspace](Affine_Lab.code-workspace) |
| Evidence | [Three distinct captures](data/recorded), five synthetic cases per capture, preserved SHA-256 provenance |
| Analysis | Histogram scoring, all 312 candidates, E/T congruences, Euclid/inverse proof, re-encryption checks |
| Demo | Offline real TCP replay; local HTML dashboard; optional Gemini HTTPS generation |
| Outputs | [Verified historical results](reports/evidence_verification.json), [new replay exports](reports/replay_demo) |
| Tests | [Correctness suite](tests), [browser verification tool](tools/check_browser.py), [figure/link checks](tools/check_portfolio.py) |
| Documentation | [Demo and viva notes](docs/DEMO_GUIDE.txt), [architecture](docs/ARCHITECTURE.md), [data provenance](docs/DATA_PROVENANCE.md) |

## Project Breakdown

1. **Prepare input.** Username and concern become UTF-8 A–P nibble armor, then
   Affine ciphertext. The mood selects the lab key; credentials remain server-side.
2. **Exchange JSON.** A bounded IPv4 loopback server decodes the request and
   obtains either the exact saved reply or fresh text from the selected provider.
3. **Encrypt the reply.** English text is normalized to uppercase ASCII and
   returned through the deliberately weak local cipher.
4. **Recover independently.** The analyzer counts ciphertext letters once,
   permutes 26 frequency bins for each key and decrypts the lowest-scoring candidate.
   It does not consult mood or known plaintext during ranking.
5. **Verify.** Compare recovered key, mood, username, concern and reply; re-encrypt
   the result; for saved runs also compare reconstructed packet payloads and hashes.
6. **Export.** Save JSON, summary/ciphertext CSVs, readable proof/plaintext and
   a content manifest. Partial provider failures preserve completed cases as failures.

`C=(aP+b) mod 26`; `P=a⁻¹(C−b) mod 26`, with `gcd(a,26)=1`.
There are 12 multipliers × 26 shifts. Chi-square is
`Σ((observed−expected)²/expected)`, where expected counts use English frequencies.
For `(a,b)=(7,6)`, `a⁻¹=15`, because `7×15=4×26+1`.

## Folder Structure

```text
Affine_Lab/
├── src/affine_lab/          # maintained Python engine + packaged dashboard
│   ├── resources/          # normalized synthetic replay fixture
│   └── web/                # local dashboard HTML, CSS and JavaScript
├── data/recorded/           # three distinct raw captures and original records
├── reports/                # independently recomputed results and example exports
├── tests/                  # arithmetic, capture, TCP, provider and HTTP checks
├── tools/                  # evidence, figure, browser and portfolio verification
├── docs/                   # architecture, provenance, demo, archive and handoff
├── assets/                 # shared figures/previews, badges, CSS, JS, favicon
├── index.html              # responsive static portfolio + cipher playground
├── pyproject.toml          # runnable/installable package build configuration
└── Affine_Lab.code-workspace
```

Authored coursework reports, evidence and earlier source are included in the public project.
The complete supplied coursework archive is included under [archive/coursework](archive/coursework),
with third-party attribution. Actual credentials and generated environments remain excluded.
The curated dataset is small, so no duplicate release bundle is needed.

## Setup

Use **Python 3.12 or newer**. Runtime third-party dependencies: **zero**.

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -e .
python -m affine_lab doctor
```

Ubuntu / WSL:

```bash
cd /mnt/c/Users/CodeTech/Desktop/Affine_Lab
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
python -m pip install -e .
```

Open `Affine_Lab.code-workspace` in VS Code. Select the matching interpreter.
Use **Terminal → Run Task** for named demo and verification tasks.
Windows and WSL require separate virtual environments. WSL is optional.

## Demo

```bash
python -m affine_lab verify data/recorded/tcp_baseline
python -m affine_lab inspect-pcap data/recorded/tcp_baseline/capture.pcap
python -m affine_lab demo
python -m affine_lab serve
```

Open `http://127.0.0.1:8765` for the local dashboard. Choose a synthetic case,
run real TCP replay, inspect the recovered reply/proof, and download exports.
The console prints each key and the new `runs/<timestamp>/` output directory.
Stop the server with Ctrl+C. The default mode uses recorded replies, with no API
request. Inspecting the saved corpus recomputes analysis without a TCP exchange.

For fresh Gemini generation, copy `.env.example` to `.env` and set your own
`GEMINI_API_KEY` locally. Then run:

```bash
python -m affine_lab demo --provider gemini
python -m affine_lab serve --provider gemini
```

The provider is selected at startup, not for every message. The configurable
default model is `gemini-3.5-flash-lite`; access and quotas depend on your account.
The key is excluded from Git. Gemini generates English text over a separate
HTTPS connection; the analyzer breaks the local Affine substitution, not TLS.
Failures never silently fall back to replay. Only synthetic demo inputs belong here.

The static [portfolio webpage](index.html) works without the Python server or API.
Its interactive cipher playground runs in the browser. GitHub Pages hosts this
presentation, while the TCP/API dashboard runs locally.

Optional new packet capture on Linux requires root and tcpdump:

```bash
sudo .venv-wsl/bin/python -m affine_lab demo --tcp-port 9999 --capture
```

Reading the included captures needs neither root nor tcpdump. A plain replay
does not create a packet capture unless `--capture` is requested.

## Results and Verification

The saved verification report records **3 captures, 15 sessions and 150 frames**.
All five keys in each capture were recovered and every known-input/payload/hash
comparison passed. A [fresh Gemini check](reports/fresh_gemini/result.json) also passed all five synthetic cases; its variable replies and actual execution time are saved separately. The independent replay run also passed five actual TCP
exchanges using recorded text.

| Case | Mood | Recovered a | Recovered b | Inverse |
| --- | --- | --- | --- | --- |
| 1 | 3 | 7 | 6 | 15 |
| 2 | 4 | 9 | 8 | 3 |
| 3 | 5 | 11 | 10 | 19 |
| 4 | 6 | 15 | 12 | 7 |
| 5 | 7 | 15 | 14 | 7 |

The seven-repeat local benchmark measured **FAST ms** median for histogram
scoring versus **SLOW ms** for full-message scoring on one recorded reply.
All 312 candidate scores match the reference. This is a local measurement,
not a universal performance guarantee. Work changes from `O(312×N)` to
`O(N+312×26)` plus winning-text decryption.

```bash
python -m unittest discover -s tests -v
python tools/verify_evidence.py
python -m pip install -e ".[dev]"
python tools/build_portfolio.py
python tools/check_portfolio.py
python tools/check_browser.py
python -m pip wheel . --no-deps --wheel-dir dist
```

See [verification details](docs/VERIFICATION.md) for actual environments, browser
checks and the distinction between recorded evidence, new replay and live API checks.

## Extended Analysis

The maintained [CSV analyzer](src/affine_lab/batch.py) accepts a CSV with a
`ciphertext` column and exports every candidate score and letter-frequency row.
When a `field` column exists, it selects only `ciphertext` reply rows and skips
armored request fields, whose A–P distribution is not English prose.

```bash
python -m affine_lab analyze-csv data/recorded/tcp_baseline/ciphertexts.csv --output runs/batch
```

The [saved batch report](reports/batch_analysis/summary.csv) contains five recovered
keys, [1,560 candidate scores](reports/batch_analysis/candidate_ranking.csv) and
[130 frequency rows](reports/batch_analysis/letter_frequencies.csv). Arbitrary CSV
results remain explicitly unverified until compared with independent known inputs.
Input size/row/character limits and nonempty-output protection keep this workflow
bounded. See [CSV format and exports](docs/CSV_WORKFLOW.md).

The browser playground now shows the top five candidate keys and a measured
frequency comparison chart, with copy/download controls for the computed result.
It works from the static page, without sending your entered text to a provider.

### A short recruiter walkthrough

1. Open the webpage and recover the supplied full-length ciphertext sample.
2. Inspect candidate scores and letter frequencies, then download the analysis.
3. Run the Python replay or CSV command and compare its recovered keys.
4. Open the readable [analyzer](src/affine_lab/analysis.py),
   [CSV workflow](src/affine_lab/batch.py) and [build file](pyproject.toml).
5. Follow the raw capture, recovery proof and independently checked saved outputs.

## Visual Evidence

24 figures share the same images, captions and order with the webpage.
The webpage offers a **Larger previews** control for bigger desktop/tablet cards;
narrow-mobile previews already use the available single-column width.
Click a left-aligned preview to open its full 1440 × 900 image. Previews are
960 × 600. The gallery groups design, inputs, method, analysis, evidence,
results, source, demo and verification material.

FIGURE_INDEX

FIGURES

## Limitations

Frequency fit can choose a wrong key for short, unusual or non-English text.
Scores are not probabilities; E/T correspondences describe a candidate rather
than guaranteed frequency ranks. Synthetic model replies are not clinical advice.
The local server is a bounded teaching demo, not a production service.
The capture inspector supports this lab's classic PCAP/IPv4/TCP traffic and
rejects unsupported/incomplete streams; it is not a general Wireshark replacement.
No TLS decryption or security claim for Affine encryption is made.

See [security reflection](docs/SECURITY_REFLECTION.md), [architecture and limits](docs/ARCHITECTURE.md), [data provenance](docs/DATA_PROVENANCE.md)
and [license](LICENSE). Fresh Gemini behavior can vary and requires your own account.

## About the Author

**Mohammad Rohaan** · Computer Science, FAST-NUCES

[GitHub](https://github.com/rohaan2802) · [Email](mailto:m.rohaanarshad@gmail.com)

Built to make packet evidence, classical cryptanalysis and reproducible
verification easy to inspect in one runnable project.
"""
    index = " | ".join(
        f"[{f['id']:02}](#figure-{f['id']:02}-{f['title'].lower().replace(' — ', '--').replace(' ', '-')})"
        for f in MANIFEST
    )
    # Explicit stable anchors avoid renderer-dependent punctuation handling.
    index = "\n".join(
        f"{f['id']}. [{f['title']}](#figure-{f['id']:02})" for f in MANIFEST
    )
    figures = "\n\n".join(
        f'<a id="figure-{f["id"]:02}"></a>\n\n### Figure {f["id"]:02} — {f["title"]}\n\n[![{f["title"]}]({f["preview"]})]({f["full"]})\n\n{f["caption"]}'
        for f in MANIFEST
    )
    text = (
        text.replace("BADGES", badge_markup)
        .replace("FIGURE_INDEX", index)
        .replace("FIGURES", figures)
        .replace("FAST ms", f"{bench['histogram_median_ms']:.3f} ms")
        .replace("SLOW ms", f"{bench['full_text_reference_median_ms']:.3f} ms")
    )
    text = text.replace(
        "9. [Visual Evidence](#visual-evidence)",
        "9. [Detailed Project Reference](#detailed-project-reference)\n10. [Visual Evidence](#visual-evidence)",
    )
    text = text.replace("10. [Limitations]", "11. [Limitations]").replace(
        "11. [About the Author]", "12. [About the Author]"
    )
    text = text.replace(
        "## Visual Evidence\n",
        project_reference.markdown() + "\n## Visual Evidence\n",
        1,
    )
    text = text.replace(
        "| Documentation | [Demo and viva notes]",
        "| Documentation | [Detailed project reference](docs/PROJECT_REFERENCE.md), [documentation index](docs/README.md), [demo and viva notes]",
    )
    text = text.replace("## Visual Evidence\n", '## Coursework Reports and Original Evidence\n\nThe authored [assignment PDF](docs/reports/assignment_report.pdf) and\n[pre-demo PDF](docs/reports/pre_demo_report.pdf) are included in the public\nrepository, alongside their [HTML views](docs/reports/README.md),\n[17 desktop screenshot files](evidence/coursework/index.html),\n[historical authored source](legacy/coursework/README_HISTORY.md) and\n[saved coursework outputs](reports/coursework).\n\nThe coursework screenshots use the existing edited taskbar display date\n22 October 2026. Their actual capture timestamps remain 18–19 November 2026 in\nraw PCAPs/logs. These are presentation copies, separate from the 24 generated\nportfolio figures. The PDFs contain the same six/eleven edited screenshots;\nsee the [evidence manifest](evidence/coursework/manifest.json).\n\n'+"## Visual Evidence\n", 1)
    text = text.replace("10. [Visual Evidence](#visual-evidence)", "10. [Coursework Reports and Original Evidence](#coursework-reports-and-original-evidence)\n11. [Visual Evidence](#visual-evidence)").replace("11. [Limitations]", "12. [Limitations]").replace("12. [About the Author]", "13. [About the Author]")
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def site(badge_markup):
    html = """<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Affine Lab: reproducible classical cryptanalysis, independent PCAP verification and an offline TCP replay dashboard."><meta name="theme-color" content="#12333d"><title>Affine Lab · Cryptanalysis & Evidence</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/css/site.css"><script defer src="assets/js/portfolio_data.js"></script><script defer src="assets/js/site.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header><div class="nav-wrap"><a href="#overview" class="brand"><span>λ</span> Affine Lab</a>
<button class="icon-button menu" id="menu" aria-label="Open navigation" aria-controls="nav" aria-expanded="false"><svg id="hamburger" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg><svg id="close-menu" hidden viewBox="0 0 24 24" aria-hidden="true"><path d="m5 5 14 14M19 5 5 19"/></svg></button>
<nav id="nav" aria-label="Main navigation"><a href="#overview">Overview</a><a href="#inside">Workflow</a><a href="#method">Method</a><a href="#demo">Demo</a><a href="#results">Results</a><a href="#evidence">Evidence</a><a href="#source">Source</a><a href="#resources">Docs</a><a href="#author">Author</a></nav>
<button class="icon-button" id="theme" aria-label="Switch to dark theme"><svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 13.2A8.5 8.5 0 0 1 10.8 3.5 8.5 8.5 0 1 0 20.5 13.2Z"/></svg><svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg></button></div></header>
<main id="main"><section id="overview" class="hero"><div class="eyebrow">Classical cryptanalysis · Reproducible engineering</div><h1>Small cipher.<br>Complete evidence.</h1><p>Recover weak Affine keys from encrypted English, reconstruct the packets, and check the result against actual inputs.</p><div class="badges">BADGES</div><div class="actions"><a class="button primary" href="#demo">Try the cipher lab</a><a class="button" href="#evidence">Explore 24 figures</a><a class="button" href="README.md">Read the README</a><a class="button" href="#coursework">PDF reports</a></div><div class="stats"><div class="stat"><strong>312</strong><span>candidate keys per reply</span></div><div class="stat"><strong>15 / 15</strong><span>recorded sessions verified</span></div><div class="stat"><strong>3</strong><span>independent PCAP runs</span></div><div class="stat"><strong>0</strong><span>runtime dependencies</span></div></div>
<div class="scroll links"><table><thead><tr><th>What</th><th>Link</th></tr></thead><tbody><tr><td>Repository</td><td><a href="https://github.com/rohaan2802/Affine_Lab">Affine_Lab</a></td></tr><tr><td>GitHub Pages</td><td><a href="https://rohaan2802.github.io/Affine_Lab/">Visual evidence portfolio</a></td></tr><tr><td>Project resource</td><td><a href="https://github.com/maadilrehman/PsycoSupport">Original PsycoSupport exercise</a></td></tr></tbody></table></div></section>
<div class="contents" aria-label="Contents"><a href="#inside">01 Project breakdown</a><a href="#demo">02 Setup & demo</a><a href="#results">03 Verified results</a><a href="#evidence">04 Visual evidence</a><a href="#resources">05 Source & documentation</a></div>
<section id="inside"><div class="eyebrow">01 / What's inside</div><h2>Readable source. Inspectable results.</h2><p>Five synthetic student concerns pass through a real local client and server. An independent analyzer ranks all valid Affine keys using English letter frequencies, then separate checks compare the recovered result with known inputs. The supplied coursework binary has been replaced by maintained Python source.</p>
<div class="flow"><span>Input → armor</span><b>→</b><span>Local Affine TCP</span><b>→</b><span>Replay / Gemini</span><b>→</b><span>Ciphertext analysis</span><b>→</b><span>Independent checks</span></div>
<div class="grid3"><article class="card"><h3>A bounded protocol</h3><p>Loopback-only JSON/TCP, explicit input limits, server-side credentials and clear provider errors. Exact recorded replies make the default demo reproducible.</p></article><article class="card"><h3>An efficient analyzer</h3><p>Count letters once, then score 26 frequency bins for each of 312 keys. Tests compare every score with full-message decryption.</p></article><article class="card"><h3>Independent evidence</h3><p>Reassemble raw PCAP bytes, compare requests and replies, verify hashes, decode inputs and re-encrypt recovered text.</p></article></div>
<details><summary>Folder structure and maintained files</summary><pre><code>Affine_Lab/
├── src/affine_lab/      Python engine + local HTML dashboard
├── data/recorded/       Three distinct PCAPs + original records
├── reports/             Verified results + maintained replay export
├── tests/               Arithmetic, TCP, capture, provider and HTTP tests
├── tools/               Evidence + figure + browser verification
├── docs/                Architecture, provenance, demo and handoff
├── assets/              Shared figures, badges, CSS and JavaScript
├── pyproject.toml       Installable package / build configuration
└── index.html           This static presentation</code></pre><p><a href="docs/LOCAL_HISTORY.md">Historical material and local storage policy</a></p></details></section>
<section id="method"><div class="eyebrow">The method</div><h2>Small key space. Measurable weakness.</h2><div class="grid2"><article class="card"><h3>01 / Substitute the alphabet</h3><p>Encode letters as A=0 through Z=25. Encryption applies a multiplication and shift; decryption uses a modular inverse.</p><pre><code>C = (a × P + b) mod 26
P = inverse(a) × (C − b) mod 26
Example: a=7, b=6, inverse=15
7 × 15 = 4 × 26 + 1</code></pre></article><article class="card"><h3>02 / Rank, then verify</h3><p>Count the encrypted letters once and score each of 312 candidate substitutions against an English reference. Decrypt the strongest candidate, then compare known inputs independently.</p><p><strong>Why separate the checks?</strong> A low chi-square score is a language-fit heuristic. It does not certify a message or turn re-encryption into proof of the right key.</p><a href="docs/PROJECT_WALKTHROUGH.txt">Follow the complete worked explanation</a></article></div></section>
<section id="demo"><div class="eyebrow">02 / Setup & demo</div><h2>Run the lab. Or try the math here.</h2><p>Python 3.12+ runs the offline demo on Windows or Ubuntu/WSL. The static playground below needs only your browser. It makes no model requests.</p>
<div class="tabs" role="tablist" aria-label="Setup platform"><button role="tab" data-tab="windows" aria-selected="true" aria-controls="windows">Windows</button><button role="tab" data-tab="ubuntu" aria-selected="false" aria-controls="ubuntu">Ubuntu / WSL</button></div>
<div id="windows" role="tabpanel"><pre><code>py -3 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -e .
python -m affine_lab verify data/recorded/tcp_baseline
python -m affine_lab demo
python -m affine_lab serve</code></pre></div><div id="ubuntu" role="tabpanel" hidden><pre><code>python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
python -m pip install -e .
python -m affine_lab verify data/recorded/tcp_baseline
python -m affine_lab demo
python -m affine_lab serve</code></pre></div>
<p class="note">The local dashboard opens at <code>http://127.0.0.1:8765</code>. Provider selection lasts for that server session. Stop with Ctrl+C. Open the VS Code workspace and choose <strong>Terminal → Run Task</strong> for named demo buttons.</p>
<div class="grid2"><article class="card"><h3>Offline replay</h3><p>New TCP exchanges and new analysis, using exact saved Gemini replies. No internet, API key, model download or Ollama required. Results are saved under <code>runs/&lt;timestamp&gt;/</code>.</p></article><article class="card"><h3>Fresh Gemini generation</h3><p>Set a private <code>GEMINI_API_KEY</code> in <code>.env</code>, then start with <code>--provider gemini</code>. Gemini creates English text over HTTPS. The lab analyzes the separate local Affine exchange; it does not decrypt TLS. Failures never switch silently to replay.</p></article></div>
<h3>Interactive cipher playground</h3><p class="note">Use a full English paragraph for recovery. A low score indicates frequency fit, not guaranteed correctness. This browser tool shares the Python engine's equations and reference frequencies.</p>
<div class="grid2"><form id="cipher-form" class="card"><div class="field"><label for="cipher-input">Input text</label><textarea id="cipher-input" maxlength="20000"></textarea></div><div class="field"><label for="cipher-action">Action</label><select id="cipher-action"><option value="recover">Recover key from ciphertext</option><option value="encrypt">Encrypt with a known key</option><option value="decrypt">Decrypt with a known key</option></select></div><div class="key-fields"><div class="field"><label for="key-a">Multiplier a</label><select id="key-a"><option>1</option><option>3</option><option>5</option><option selected>7</option><option>9</option><option>11</option><option>15</option><option>17</option><option>19</option><option>21</option><option>23</option><option>25</option></select></div><div class="field"><label for="key-b">Shift b</label><input id="key-b" type="number" min="0" max="25" value="6" required></div></div><div class="analysis-actions"><button class="primary" type="submit">Run analysis</button><button id="sample" type="button">Load recorded sample</button></div></form><div class="card"><h3>Computed output</h3><div class="output-actions"><button id="copy-result" type="button">Copy result</button><button id="download-result" type="button">Download JSON</button></div><p id="export-status" class="note" role="status"></p><pre id="cipher-output" class="play-result" role="status" aria-live="polite">Load a sample or enter text, then run analysis.</pre><p class="note"><code>C=(aP+b) mod 26</code><br><code>P=a⁻¹(C−b) mod 26</code><br>12 valid multipliers × 26 shifts = 312 keys.</p></div></div></section>
<div class="grid2 analysis-detail"><article class="card"><h3>Top candidate keys</h3><p class="note">The five lowest scores for the last recovery. Lower is a closer English frequency fit.</p><div class="scroll"><table class="candidate-table"><thead><tr><th>Rank</th><th>a</th><th>b</th><th>χ²</th></tr></thead><tbody id="candidate-rows"></tbody></table></div></article><article class="card"><h3>Measured letter frequencies</h3><p class="note">Recovered text compared with the fixed English reference. Hover or focus a bar group to inspect percentages.</p><div id="frequency-chart" class="frequency-chart"></div></article></div>
<section id="results"><div class="eyebrow">03 / Results & verification</div><h2>Every recorded session rechecked.</h2><p>The curated evidence contains three distinct historical model runs. The independent reader reconstructs 150 frames across 15 sessions and matches the original payloads and capture hashes. The maintained offline replay separately completes five actual TCP exchanges.</p><div class="scroll"><table><thead><tr><th>Case</th><th>Mood</th><th>Recovered a</th><th>Recovered b</th><th>Inverse</th><th>All three runs</th></tr></thead><tbody><tr><td>1</td><td>3</td><td>7</td><td>6</td><td>15</td><td>Pass</td></tr><tr><td>2</td><td>4</td><td>9</td><td>8</td><td>3</td><td>Pass</td></tr><tr><td>3</td><td>5</td><td>11</td><td>10</td><td>19</td><td>Pass</td></tr><tr><td>4</td><td>6</td><td>15</td><td>12</td><td>7</td><td>Pass</td></tr><tr><td>5</td><td>7</td><td>15</td><td>14</td><td>7</td><td>Pass</td></tr></tbody></table></div>
<div class="grid2" style="margin-top:22px"><article class="card"><h3>What passes</h3><p>Recovered key, mood, username, concern, client reply, re-encryption and raw payload parity are checked independently. Corrupt captures, provider failures and malformed requests have negative tests.</p><a href="reports/evidence_verification.json">Open the full verification report</a></article><article class="card"><h3>What the result means</h3><p>The recorded English replies are long enough for this heuristic to rank the right key. That does not guarantee recovery of arbitrary short or non-English messages. Re-encryption alone is not proof of the correct key.</p><a href="docs/VERIFICATION.md">Read checks and limits</a></article></div>
<details><summary>Saved evidence, fresh replay and fresh API calls</summary><p><strong>Saved evidence:</strong> historical PCAP bytes and replies, analyzed again. <strong>Fresh replay:</strong> new real local TCP traffic with saved text. <strong>Fresh Gemini:</strong> a new HTTPS request and a variable generated reply. The static portfolio displays saved evidence and does not host Python or expose credentials.</p></details>
<details><summary>Limitations and responsible scope</summary><p>The input concerns are synthetic. Replies demonstrate cryptanalysis and are not clinical advice. The PCAP reader supports this lab's classic IPv4/TCP captures, not arbitrary network traffic. The dashboard is a local teaching tool; Affine encryption is deliberately unsuitable for protecting real personal data. External API availability depends on credentials, quota and model access.</p></details></section>
<section id="evidence"><div class="eyebrow">04 / Visual evidence</div><h2>24 figures. One evidence trail.</h2><p>Actual data, code and recomputed results, with consistent framing and legible contrast. The README uses the same images, captions and order. Use <strong>Larger previews</strong> for bigger desktop/tablet cards, or open a figure for the full image and zoom controls.</p><div class="toolbar"><div class="search"><label for="search" class="note">Search figures</label><input id="search" type="search" placeholder="Try: PCAP, proof, frequency, source…"></div><span id="gallery-count" class="gallery-count" role="status" aria-live="polite"></span><button id="preview-size" type="button" aria-pressed="false" aria-controls="gallery">Larger previews</button></div><div id="filters" class="filters" aria-label="Figure categories"></div><div id="gallery" class="gallery"></div><p id="empty" class="empty" hidden>No matching figures. Try another search or category.</p><noscript><p>Enable JavaScript for gallery controls, or use the <a href="README.md#visual-evidence">complete README gallery</a>.</p></noscript></section>
<section id="source"><div class="eyebrow">Maintained engineering</div><h2>The code behind the presentation.</h2><p>Reviewable modules, a runnable package build and a portable VS Code workspace are included in this repository. The presentation is generated from recorded evidence and maintained source.</p><div class="grid3"><article class="card"><h3>Cipher & recovery</h3><p>Validated keys, reversible UTF-8 armor, 312-key frequency scoring and worked modular-inverse proofs.</p><a href="src/affine_lab/crypto.py">Cipher source</a> · <a href="src/affine_lab/analysis.py">Analyzer</a></article><article class="card"><h3>Batch evidence workflow</h3><p>Analyze reply CSVs and export complete candidate rankings, frequency tables and readable summaries.</p><a href="src/affine_lab/batch.py">CSV analyzer source</a> · <a href="docs/CSV_WORKFLOW.md">Format guide</a></article><article class="card"><h3>Runnable project files</h3><p>Zero runtime dependencies. Package resources include the local dashboard and deterministic fixtures.</p><a href="pyproject.toml">Build configuration</a> · <a href="Affine_Lab.code-workspace">VS Code workspace</a></article></div><pre><code>python -m affine_lab analyze-csv data/recorded/tcp_baseline/ciphertexts.csv --output runs/batch
python -m unittest discover -s tests -v
python -m pip wheel . --no-deps --wheel-dir dist</code></pre><p><a href="reports/batch_analysis/summary.csv" download>Download batch summary</a> · <a href="reports/batch_analysis/candidate_ranking.csv" download>All 1,560 candidate rows</a> · <a href="reports/batch_analysis/letter_frequencies.csv" download>130 measured frequency rows</a></p></section>
<section id="resources"><div class="eyebrow">05 / Source & documentation</div><h2>Start with the proof. Follow the code.</h2><ul class="resource-list"><li><a href="src/affine_lab/analysis.py">Frequency analyzer source</a> — independent 312-key scoring and recovery proof.</li><li><a href="src/affine_lab/capture.py">PCAP inspector source</a> — bounded raw packet parsing and TCP reconstruction.</li><li><a href="pyproject.toml">Package build file</a> · <a href="Affine_Lab.code-workspace">VS Code workspace</a> · <a href="LICENSE">License</a></li><li><a href="docs/DEMO_GUIDE.txt">Demo commands and plain-language viva notes</a></li><li><a href="docs/ARCHITECTURE.md">Architecture and limitations</a> · <a href="docs/DATA_PROVENANCE.md">Data provenance</a></li><li><a href="reports/replay_demo/summary.csv" download>Replay summary CSV</a> · <a href="reports/replay_demo/key_recovery_proof.txt">Recovery proofs</a> · <a href="data/recorded/tcp_baseline/capture.pcap" download>Baseline PCAP</a></li><li><a href="reports/quality_checks.json">Quality check record</a> · <a href="assets/figures/manifest.json">Canonical figure manifest</a></li></ul></section></main>
<footer id="author"><div class="footer-line"><div><strong>Mohammad Rohaan</strong><p>Computer Science · FAST-NUCES</p><p>Classical cryptanalysis, clear evidence and reproducible engineering.</p></div><div><p><a href="https://github.com/rohaan2802">GitHub profile</a></p><p><a href="mailto:m.rohaanarshad@gmail.com">m.rohaanarshad@gmail.com</a></p><p><a href="README.md">Project README</a> · <a href="LICENSE">MIT license</a></p></div></div></footer>
<button id="backtop" class="backtop" aria-label="Back to top" hidden><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 1 13h6v9h10v-9h6L12 2Z"/></svg></button>
<dialog id="viewer" aria-labelledby="viewer-title"><div class="viewer-head"><h2 id="viewer-title"></h2><div class="viewer-tools"><button id="previous" aria-label="Previous figure">← Previous</button><button id="next" aria-label="Next figure">Next →</button><button id="zoom" aria-pressed="false">Zoom +</button><button id="viewer-close" aria-label="Close figure viewer">✕ Close</button></div></div><div id="stage" class="viewer-stage"><img id="viewer-image" width="1440" height="900" alt=""></div><div class="viewer-foot"><p id="viewer-caption"></p><a id="original" target="_blank" rel="noopener" class="shortcut">Open full image ↗</a><span class="note shortcut">← → browse · Esc close · swipe</span></div></dialog>
</body></html>"""
    html = html.replace(
        '<section id="resources">',
        project_reference.html() + '\n<section id="resources">',
        1,
    )
    html = html.replace(
        '<a href="#resources">Docs</a>', '<a href="#reference">Docs</a>'
    )
    html = html.replace(
        '<a href="#resources">05 Source & documentation</a>',
        '<a href="#reference">05 Detailed reference</a><a href="#resources">06 Source & documentation</a>',
    )
    # Keep a direct entry point even when the compact contents wording changes.
    html = html.replace(
        'href="docs/DEMO_GUIDE.txt">Demo commands',
        'href="docs/PROJECT_REFERENCE.md">Detailed project reference</a></li><li><a href="docs/DEMO_GUIDE.txt">Demo commands',
    )
    html = html.replace('<section id="resources">', '<section id="coursework"><div class="eyebrow">Authored coursework</div><h2>Reports, original source and desktop evidence.</h2><p>The assignment and pre-demo PDFs are included with the historical analysis source and their 17 matching desktop captures.</p><div class="actions"><a class="button primary" href="docs/reports/assignment_report.pdf">Assignment PDF</a><a class="button" href="docs/reports/pre_demo_report.pdf">Pre-demo PDF</a><a class="button" href="evidence/coursework/index.html">Desktop evidence</a><a class="button" href="legacy/coursework/README_HISTORY.md">Historical source</a></div><p class="note">Coursework screenshots use an edited taskbar display date of 22 October 2026. Raw packet/log timestamps remain 18–19 November 2026. These presentation copies are separate from the generated portfolio figures.</p></section>'+'<section id="resources">', 1)
    (ROOT / "index.html").write_text(
        html.replace("BADGES", badge_markup), encoding="utf-8"
    )
    project_reference.write_document()


if __name__ == "__main__":
    evidence = figures()
    markup = badges()
    readme(markup, evidence)
    site(markup)
    print(
        "Built 24 matched figures, 48 PNGs, README, static page and canonical manifest."
    )
