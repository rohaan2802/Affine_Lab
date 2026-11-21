# Verification record

The machine-readable records are [quality checks](../reports/quality_checks.json),
[browser checks](../reports/browser_checks.json), [historical recovery](../reports/evidence_verification.json),
[real TCP replay](../reports/replay_demo/result.json) and
[fresh Gemini run](../reports/fresh_gemini/result.json).

## Executed checks

The 38 unittest cases passed on Windows Python 3.14 and Ubuntu/WSL Python 3.12.
They cover all 312 arithmetic round trips, UTF-8 armor, invalid inputs, optimized
score/reference parity, recovery of five fixture keys, all 15 historical sessions,
raw capture metadata, overlap/reordering, retransmission conflicts, gaps and
truncated data. Local tests exercise segmented JSON, malformed requests, five
actual TCP exchanges, exports, partial provider failure and credential separation.
Mocked HTTPS checks verify key-header use and sanitized/no-fallback failures.
HTTP tests cover corpus labels, real runs/history/downloads, CSP headers, private
paths, cross-origin rejection, invalid case IDs and concurrent-run rejection.
CSV tests also verify five recovered reply keys, skipped armored fields, every
candidate/frequency export row, invalid headers/empty text and overwrite protection.

The new Gemini backend was also executed against the real API for all five
synthetic cases. Every recovered key and known-input/client check passed. The
saved result names its provider/model and actual execution time. This is a
point-in-time access/output check; future account quotas or model changes are
not guaranteed. The five fresh replies are distinct from historical PCAP evidence.

The optional Linux capture command was executed in WSL with the existing
tcpdump. The maintained replay export includes its new 50-frame capture and
capture statistics (zero kernel drops). Its five reconstructed request/reply
pairs match the maintained run's JSON; `verify_evidence.py` rechecks that parity.

The package wheel built successfully from `pyproject.toml`. A clean environment
installed it without runtime dependencies, then executed `doctor` and a five-case
TCP replay. Package resources include the runtime fixture and dashboard assets.
The wheel is a temporary verification artifact outside the repository; source
and build metadata are maintained in Git. Rebuild with:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
```

## Browser and presentation

Installed Microsoft Edge/Chromium was tested at 1440, 820, 390 and 320 pixel
widths in both themes, for both the static page and local dashboard: 16 layout
combinations. Checks confirm no page overflow, 3/2/1 gallery columns, visible
mobile menu/close icons, search/filter/empty states, modal next/previous,
arrow/Escape keys, zoom/reset, swipe events, theme controls, setup tabs,
Back to Top and an actual dashboard TCP run/export. All 312 browser arithmetic
keys and candidate scores match Python. Candidate/frequency displays and JSON
download/copy controls are exercised on the static playground. The static page also works via `file://`.
No JavaScript page errors were observed. Swipe is exercised with synthesized
touch events; physical touchscreen devices and assistive-technology sessions
were not tested. Native modal behavior provides focus containment/restoration.

The portfolio checker verifies 24 canonical figure entries, 48 exact PNG
dimensions, README/site image/caption/order parity, local links, anchors and
three HTTPS Live Links table entries. Replay manifest hashes are rechecked.
The shared project-reference paragraphs are matched against both README and
webpage, and local links in all Markdown documentation are checked as well.
External hosting, remote CI execution and physical-device testing are separate
from these reproducible local checks.

## Reproduce

```bash
python -m unittest discover -s tests -v
python tools/verify_evidence.py
python tools/build_portfolio.py
python tools/check_portfolio.py
python tools/check_browser.py
```

Figure/chart/browser tools require the optional development dependencies. On
Linux install Playwright Chromium first. Default execution, saved PCAP inspection
and the local dashboard need only Python's standard library. Benchmark timings
are local measurements, not universal guarantees. See the [architecture](ARCHITECTURE.md)
and [security reflection](SECURITY_REFLECTION.md) for explicit method limits.
