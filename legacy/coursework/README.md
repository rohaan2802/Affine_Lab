# PsycoSupport — Information Security Assignment

This lab uses the instructor's original Linux server implementation with a
Gemini adapter. The student reported instructor permission for the cloud model
exception. It is **not an offline deployment**. Client/server encryption and
packet capture remain on `127.0.0.1:9999` inside WSL Ubuntu.

## Setup

Use Python 3.12 in WSL, matching the supplied executable's embedded code.
Install `requirements.txt` into a virtual environment. TShark and tcpdump are
needed for capture/export. On this PC these tools were already available.

Copy `.env.example` to `.env` and set your own `GEMINI_API_KEY`. Do not submit
that file. `GEMINI_MODEL` is optional; otherwise an available Flash model is
selected from the API model list. No credentials travel in the local protocol.

The provided binary is stored as `original_server`. `upstream_loader.py` reads
its embedded module. Its original functions handle armor decoding, mood-based
Affine keys, response cleaning and raw TCP JSON. `server.py` substitutes the
Groq SDK interface with Gemini calls and binds the socket to loopback. The
original startup banner still says Groq-backed because that function is
unchanged; the preceding adapter banner records the actual backend.

The instructor's original system prompt is preserved for compatibility. Its
claim to be a licensed therapist is inappropriate for a real product. This is
a synthetic cryptography exercise, not a clinical service.

## Run on this computer

From PowerShell, with the local key file already configured:

```powershell
wsl -d Ubuntu -u root -- unshare --uts --fork bash '/mnt/c/Users/CodeTech/Desktop/A#02/psycare_lab/lab_inner.sh'
```

Root is used for capture in the controlled WSL lab. The separate hostname
namespace is named `rohaan-psylab`; it does not rename the Windows PC. The
runner uses the pre-existing Python environment at
`/home/codetech/psycare_lab/.venv/bin/python`. Set `LAB_PYTHON` to another Python
3.12 environment when reproducing elsewhere. Capture is exclusively `lo`,
filtered to TCP port 9999; remote Gemini TLS traffic is outside its scope.

For analysis only, run `bash run_analysis.sh`. The attack reads ciphertexts
and English frequencies. `scripts/verify_results.py` separately compares the
recovered answers with the supplied implementation and recorded client result.

## Files

- `server.py`, `client.py`, `upstream_loader.py`: local adaptation and client.
- `original_server`: unmodified instructor binary used as the source module.
- `test_cases.json`: five synthetic concerns and different numeric moods.
- `ciphertexts.csv`: captured fields, generated after a successful real run.
- `scripts/`: TCP extraction, independent cryptanalysis and verification.
- `evidence/`: real PCAP, TShark Follow TCP Stream exports and desktop captures.
- `output/`: recovered keys, frequency table, charts and decrypted sessions.

## Method and limitations

Analyze the five server replies separately: different moods use different keys.
Client inputs first encode each UTF-8 byte as two A–P nibble letters, so their
distribution should not be compared directly to ordinary English. Recover a
key from the corresponding English server reply, then decrypt and de-armor
the request. A mood sent in clear also reveals the deterministic key schedule;
this is a separate shortcut, not the ciphertext-only attack.

No fixed disclaimer is added by this adaptation. Discuss repeated structures
only when they actually appear in the captured output. Raw model responses
may vary between runs.

The submission packager excludes `.env`, virtual environments, caches and
download logs. Capture timestamps retain the actual run date. Screenshot taskbar dates were edited to 22/10/2026; see project_notes/04_SCREENSHOT_EDIT_RECORD.txt.
The PDF generator runs on Windows with Playwright and installed Microsoft Edge;
install `requirements-report.txt` only if rebuilding the report elsewhere.
Code/report preparation was assisted by an AI tool; review and understand the
method and follow your course's disclosure rules before submission.

## References

- Instructor repository: https://github.com/maadilrehman/PsycoSupport
- Gemini REST API: https://ai.google.dev/api/generate-content
- TShark manual: https://www.wireshark.org/docs/man-pages/tshark.html
- English letter frequencies: Robert Lewand, *Cryptological Mathematics*,
  Mathematical Association of America, 2000 (reference frequencies only).

## Live demonstration

Open DEMO_GUIDE.txt for the complete Roman Urdu command guide and viva notes.
In the WSL VS Code workspace, Terminal > Run Task provides saved-analysis,
recovered-key display and live-demo options. run_demo.sh backs up the prior
evidence before requesting fresh model responses. The submitted PDF remains
a record of the original run.

## Optional local web interface

`WEB_DEMO_GUIDE.txt` explains the difference between the offline saved viewer
and the optional live browser interface. `web_demo.py` serves the local UI
on port 8765. Live mode runs under WSL Python 3.12, calls the existing local
TCP server and Gemini adapter, and independently verifies each fresh reply.
`run_web_demo.sh` records port-9999 loopback traffic when launched as WSL root.
Live results are stored separately in `web_runs/` and do not overwrite the
verified saved evidence. Windows can run `python web_demo.py --saved-only`
to preview recorded results with all live actions explicitly disabled.
