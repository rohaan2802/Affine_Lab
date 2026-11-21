# Evidence provenance

The original assignment workspace contained overlapping runnable copies,
pre-demo exports, backups and report assets. Three distinct packet captures
were retained: `submission`, `tcp_baseline` and `web_validation`. Each has five
synthetic conversations, 50 recorded frames, requests/replies, original
verification metadata and a SHA-256 digest in `data/recorded/provenance.json`.
The captures' actual timestamps are retained; they were recorded in November
2026. The public figures are newly generated from these raw records and the
maintained implementation. Historical report screenshots are not reused.
`data/presentation/dashboard.png` is the original browser capture used to frame
figure 22. It shows an actual local replay test; keeping this source image makes
the portfolio renderer reproducible without relaunching a browser or model.

`src/affine_lab/resources/demo_cases.json` normalizes the five synthetic inputs
and exact baseline replies for deterministic offline replay. It is an intentional
runtime fixture, while raw captures provide independent verification. The three
runs contain different generated replies and are not interchangeable duplicates.
`reports/evidence_verification.json` recomputes recovery and capture parity.
`reports/replay_demo` is a newly executed local TCP run using saved replies.
Its timestamp is a replay execution time, not the original model-generation time.
The maintained replay was captured separately under WSL using the new Python
implementation. Its `capture.pcap` has 50 frames, and `capture_stats.txt` records
zero kernel drops. Its packet payloads are compared with the maintained result
by `tools/verify_evidence.py`; it is not one of the three historical model runs.

The supplied instructor executable and binary loader are not needed by the new
implementation. The supplied artifact is retained with its original attribution
in archive/coursework and is not covered by the maintained source license. Actual credentials remain excluded; supplied instructions and project discussion
records are retained in archive/coursework as documented in `LOCAL_HISTORY.md`. Authored reports and useful earlier source
are included in the public folders described below.
Only synthetic demonstration concerns are included. No actual client/patient
records are represented. Generated replies demonstrate cryptanalysis, not
clinical correctness or suitability for mental-health decisions.

## Coursework reports and presentation screenshots

Authored PDFs, historical source and relevant saved outputs are published under
`docs/reports`, `legacy/coursework` and `reports/coursework`. The 17 existing
edited screenshots are under `evidence/coursework`; desktop and native WSL
evidence copies were synchronized by hash. Their taskbar display date reads
22 October 2026 while actual capture/log timestamps remain 18–19 November 2026.
The PDF embedded image pixels match the six/eleven published screenshots.
Supplied instructions, project-only discussion records and the supplied binary
are included in archive/coursework with a separate third-party notice. This supplementary evidence is separate from the 24 generated
portfolio figures.
