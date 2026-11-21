# Architecture and design decisions

For the complete input/mode/module/output tables, see the
[detailed project reference](PROJECT_REFERENCE.md). The
[documentation index](README.md) provides a suggested review path.

`crypto.py` owns Affine arithmetic and UTF-8 nibble armor. `protocol.py` owns
bounded JSON over IPv4 loopback TCP. `providers.py` supplies either exact saved
replies or an explicitly selected Gemini HTTPS backend. `analysis.py` ranks
keys without importing the mood schedule. `validation.py` performs the separate
known-input comparison after recovery. `capture.py` independently reconstructs
the recorded TCP payloads. `runner.py` coordinates real exchanges;
`reporting.py` exports timestamped results and SHA-256 manifests.

`web.py` serves an optional local dashboard with the same Python engine. The
root `index.html` is an independent static portfolio suitable for GitHub Pages;
its JavaScript playground demonstrates the same arithmetic without an API.

## Transport and trust

The server and client bind only to 127.0.0.1. The local protocol deliberately
uses weak substitution for teaching. The API key remains on the server and is
sent to Google's HTTPS endpoint in a header. It is never sent in lab JSON.
HTTPS uses TLS independently of Affine and is not decrypted by this project.
The local dashboard permits only five synthetic cases, bounded POST payloads,
same-origin browser requests and a fixed export allowlist. It is a development
demo, not an authenticated multiuser service or a production security boundary.

## Efficiency

For N letters and K=312 keys, a full-message reference does O(K*N) work.
The histogram implementation counts O(N), then scores O(K*26), and materializes
only the winning plaintext. Tests compare every score against the reference.
`reports/evidence_verification.json` records a seven-repeat local benchmark;
timings depend on the machine and message. Reading PCAPs needs no third-party
packages or capture privileges. Live capture is optional Linux tcpdump work.

## Error behavior

Missing credentials fail before a Gemini run. HTTP/provider errors never switch
to replay. Completed cases survive a later provider failure and the overall
run is marked failed/partial. Existing nonempty CLI exports are not overwritten.
TCP requests and packet streams have size limits. The PCAP reader rejects gaps,
conflicting retransmissions, unsupported fragmentation and incomplete sessions.

## Scope and limitations

English frequency scoring is a heuristic, especially weak for short text,
unusual vocabulary or non-English messages. Re-encryption alone does not prove
the correct key; known input and client comparisons provide stronger checks.
The PCAP reader supports classic PCAP with Ethernet, Linux cooked v1 or raw
IPv4, TCP, one lab request/reply per connection. It does not support pcapng,
IPv6, sequence-number wraparound, general connection reuse or checksum audits.
The capture limit is 64 MiB and the reconstructed stream limit is 1 MiB.
The protocol preserves the coursework's mood-dependent key schedule for evidence
compatibility. It must never be used to protect real personal information.
