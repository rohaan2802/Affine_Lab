# Affine Lab — Project Reference

A complete view of the actual inputs, execution boundaries, maintained source and saved evidence.

## Problem, scope and engineering goals

The project asks a concrete question: can an observer recover a conversation protected by an Affine substitution cipher without receiving its key? The independent analyzer ranks candidate keys from the encrypted English reply; a separate verifier then checks the result against known synthetic inputs.

The engineering goal is to make that claim inspectable from end to end: readable source, real local TCP traffic, original packet bytes, explicit provider modes, worked recovery proofs and portable output files. The portfolio extends the original coursework with an independent Python implementation rather than relying on the supplied executable.

The public demonstration uses invented concerns. It is an educational cryptanalysis exercise, not a clinical application, a secure messaging product or a tool for decrypting HTTPS.

## Inputs and the five demonstration cases

Each case has a stable case ID, a synthetic username, a mood from 1 to 10 and a concern string. The baseline fixture also stores the exact English reply required for deterministic replay. Input case selection and ciphertext recovery are separate operations.

The five examples below are the actual packaged cases, not additional invented results. Reusing the same inputs across historical captures, replay and fresh API generation makes key/input comparisons meaningful while allowing model text to vary.

| Case | Mood | Username | Synthetic concern |
| --- | --- | --- | --- |
| 1 | 3 | Rohaan | My final exams start next week and I cannot sleep because I keep thinking I will fail. |
| 2 | 4 | Rohaan | I moved to a new city for university and I have not made any friends yet, the weekends feel very empty. |
| 3 | 5 | Rohaan | I am working part time and studying full time, and I feel tired all the time and fall behind on assignments. |
| 4 | 6 | Rohaan | I had a big argument with my older brother and now we are not talking, and it is bothering me every day. |
| 5 | 7 | Rohaan | My final year project deadline is close, my group members are not replying, and I feel like I have to do everything alone. |

## Execution modes and what each one proves

Choose the mode according to the claim being demonstrated. Recomputing saved evidence, exchanging new TCP messages and generating a new model reply are different activities; the interface and exported JSON label them separately.

Provider selection happens when starting the local server or CLI demo. Gemini produces English text; it does not recover the cipher key. A failed Gemini request does not silently switch the experiment to recorded replies.

| Workflow | Input / reply source | New local TCP? | External API? | Result |
| --- | --- | --- | --- | --- |
| Static playground | Typed text or recorded ciphertext sample | No | No | Candidate keys, frequencies and downloadable JSON |
| Recorded verification | Preserved PCAP bytes and original requests/replies | No | No | Independent payload/hash/input comparisons |
| Dashboard corpus inspection | Packaged baseline replies | No | No | Recomputed analysis, explicitly labelled saved corpus |
| Offline replay | Known synthetic inputs and exact saved replies | Yes | No | New loopback exchange, recovery and run exports |
| Fresh Gemini | Known synthetic inputs and newly generated English | Yes | Yes, HTTPS | New generation and local cipher checks |
| CSV analysis | Selected English-reply rows from a CSV | No | No | Complete rankings and frequency tables; heuristic candidates |

## Message lifecycle and wire-field contract

The client first converts username and concern to UTF-8 bytes. Each byte becomes two A–P nibble letters, after which Affine substitution encrypts the armored string. The server reverses those two steps, obtains a reply, cleans it to uppercase ASCII letters/spaces and encrypts it for the local return path.

The client can decrypt using its known key. Independently, the analyzer sees the reply ciphertext and ranks all 312 valid keys. Mood and known plaintext are consulted by verification only after that ranking.

The local TCP connection and the optional Gemini HTTPS connection are separate transports. Capturing the lab port exposes deliberately weak Affine traffic; it does not expose the API key or decrypt TLS.

| Direction / field | Representation | Validation / role |
| --- | --- | --- |
| Request: username_enc | Affine-encrypted A–P UTF-8 armor | Decoded username must contain 1–100 characters |
| Request: mood | Integer from 1 to 10 | Selects the recorded lab key schedule |
| Request: message_enc | Affine-encrypted A–P UTF-8 armor | Decoded concern must contain 1–2,000 characters |
| Request: api_key_enc | Empty string | Nonempty credentials in this local protocol are rejected |
| Reply: ciphertext | Affine-encrypted uppercase English | Analyzed independently; normal client decryption is compared afterwards |
| Failure: error | A bounded JSON error response | Provider failures remain explicit; no replay fallback |

## Recovery mathematics and measured efficiency

Represent letters as A=0 through Z=25. Encryption is C=(aP+b) mod 26. Decryption is P=a⁻¹(C−b) mod 26, where a must be coprime to 26. Twelve valid multipliers and 26 shifts give 312 candidates.

For each candidate, expected letter counts equal the total ASCII-letter count multiplied by the English reference percentage. The chi-square score sums (observed−expected)²/expected across the alphabet. Lower scores indicate a closer language fit, not a probability of correctness.

For the recovered example a=7, b=6, the inverse is 15 because 7×15=105=4×26+1. Under that candidate E maps to I and T to J. Subtracting 4a+b=8 from 19a+b=9 yields 15a=1 mod 26, which gives a=7 and b=6. These correspondences explain the winning candidate rather than assuming the two most common letters are always E and T.

The optimized scorer counts the ciphertext once and permutes 26 bins per key: O(N+312×26), followed by winning-text decryption. A full-text reference instead performs O(312×N) work. Complete-score parity is tested; CSV export reuses one ranking rather than scoring the same message twice.

On the saved local benchmark, the histogram scorer measured 11.770 ms median versus 377.498 ms for the full-text reference, over 7 repetitions and 689 letters. These are machine/input-specific measurements, not a universal speed claim.

## Maintained source modules and responsibilities

The package separates arithmetic, transport, model access, recovery and post-recovery checks. This keeps the attack independent of the mood schedule and lets the same analysis engine serve CLI, CSV and local dashboard workflows.

| Module | Responsibility | Review focus |
| --- | --- | --- |
| [crypto.py](../src/affine_lab/crypto.py) | Validated keys, substitution, inverses and UTF-8 armor | All valid-key round trips and invalid inputs |
| [analysis.py](../src/affine_lab/analysis.py) | Histogram scoring, ranking, plaintext and worked proof | No mood-schedule input; reference-score parity |
| [capture.py](../src/affine_lab/capture.py) | Classic PCAP parsing and loopback TCP reconstruction | Bounds, sequence gaps, overlaps and conflicting retransmissions |
| [protocol.py](../src/affine_lab/protocol.py) | Bounded JSON/TCP client and server | Actual local exchange and request validation |
| [providers.py](../src/affine_lab/providers.py) | Exact replay or explicit Gemini HTTPS generation | Server-side credentials and no silent fallback |
| [validation.py](../src/affine_lab/validation.py) | Separate known-input, client and capture comparisons | Recovery first, independent checks afterwards |
| [runner.py](../src/affine_lab/runner.py) | Case orchestration and partial-failure reporting | Completed results survive a later failure |
| [reporting.py](../src/affine_lab/reporting.py) | JSON/CSV/proof/plaintext and integrity manifests | Portable outputs and nonempty-directory protection |
| [batch.py](../src/affine_lab/batch.py) | Reply CSV selection and all-candidate exports | Armored fields skipped; heuristic output labelled |
| [web.py](../src/affine_lab/web.py) | Local dashboard routes and export allowlist | Loopback binding, same-origin controls and private paths |
| [cli.py](../src/affine_lab/cli.py) | Runnable commands and optional Linux capture | Clear command results and output locations |
| [pyproject.toml](../pyproject.toml) | Package metadata, entry point and bundled resources | Zero runtime dependencies; wheel build |
| [VS Code workspace](../Affine_Lab.code-workspace) | Editor entry point and matching interpreter setup | Portable demo/test tasks |

## Saved outputs and how to inspect them

New demo runs save to ignored timestamped runs directories. Reviewed examples under reports are maintained evidence. A run records its provider, generation label, execution time, requested/completed cases and overall pass/fail state.

A SHA-256 manifest detects changes relative to a trusted saved manifest. It is integrity metadata rather than a digital signature. Capture files exist only for runs explicitly executed with packet capture.

| Output | Contents | Use in review |
| --- | --- | --- |
| [Replay result JSON](../reports/replay_demo/result.json) | Requests, replies, recovered text, proofs and individual checks | Trace a single case from wire fields to verification |
| [Replay summary CSV](../reports/replay_demo/summary.csv) | Case, mood, a, b, inverse, score and verified flag | Compare the five recovered keys |
| [Recovery proof](../reports/replay_demo/key_recovery_proof.txt) | Congruence equations and inverse reasoning | Explain the mathematics without reading JSON |
| [Decrypted sessions](../reports/replay_demo/decrypted_sessions.txt) | Recovered username, concern and English reply | Inspect complete readable output |
| [Captured replay](../reports/replay_demo/capture.pcap) | New WSL loopback packet bytes from the maintained implementation | Independently reconstruct requests and replies |
| [Fresh Gemini result](../reports/fresh_gemini/result.json) | Separately recorded real API generation and local checks | Distinguish fresh model text from replay |
| [CSV candidate rankings](../reports/batch_analysis/candidate_ranking.csv) | 1,560 scored candidates for five baseline replies | Inspect alternatives rather than only the winning key |
| [CSV letter frequencies](../reports/batch_analysis/letter_frequencies.csv) | 130 measured/reference rows across five replies | Recreate per-letter comparisons |

## Evidence strength and interpretation

Three historical PCAPs contain 15 sessions and 150 frames in total. Each historical session is checked against its raw reconstructed payloads, capture digest, recovered key, decoded inputs, client reply and re-encryption. The maintained replay also has a separately captured 50-frame run.

The local correctness suite has 38 tests on Windows and Ubuntu/WSL. Browser checks cover desktop, tablet and narrow-mobile layouts in both themes, gallery controls, file-based presentation, copy/download controls and JavaScript/Python arithmetic parity for all 312 keys.

The separate fresh Gemini example passed five synthetic cases at its recorded execution time. Future quota/model access and generated content can vary. An arbitrary CSV import or a short browser sample is still a language-fit candidate unless independently verified.

Short text, unusual vocabulary and non-English prose can produce a wrong best candidate. Re-encryption alone cannot establish correctness, because any invertible candidate can transform its own decryption back into the same ciphertext.

## Setup, troubleshooting and reproducibility

Use Python 3.12 or newer, create an environment for your operating system and install the local package. Windows and WSL environments are separate. The default replay and saved capture reader need no third-party runtime packages; figure/browser tools use optional development dependencies.

The static portfolio can open directly from index.html. The local Python dashboard starts separately at 127.0.0.1:8765 and is stopped with Ctrl+C. Neither the static site nor GitHub Pages hosts the TCP server or stores an API key.

| Symptom | Likely cause | Action |
| --- | --- | --- |
| No module named affine_lab | Wrong interpreter or package not installed | Activate the intended environment and run python -m pip install -e . |
| Dashboard port already in use | Another local server is running | Stop that server or select --http-port / --tcp-port |
| CSV needs a ciphertext column | Header does not match the input contract | Use a UTF-8 CSV with ciphertext; inspect docs/CSV_WORKFLOW.md |
| Output directory is not empty | Existing reviewed output is protected | Choose a new output directory rather than overwriting evidence |
| Gemini key missing / quota error | Credentials, account quota or model availability | Check local configuration privately or explicitly restart in replay mode |
| Live capture unavailable on Windows | Optional tcpdump path requires Linux root | Read saved captures without elevation, or use WSL for new capture |

```bash
python -m affine_lab verify data/recorded/tcp_baseline
python -m affine_lab demo
python -m affine_lab analyze-csv data/recorded/tcp_baseline/ciphertexts.csv --output runs/batch
python -m unittest discover -s tests -v
python tools/check_portfolio.py
python tools/check_publish.py
```
