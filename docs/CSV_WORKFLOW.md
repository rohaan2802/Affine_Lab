# CSV analysis workflow

Use the maintained CLI to analyze a set of encrypted English replies without
starting a model, TCP server or browser. The implementation is
[`batch.py`](../src/affine_lab/batch.py), installed as part of the normal package.

```bash
python -m affine_lab analyze-csv data/recorded/tcp_baseline/ciphertexts.csv --output runs/batch
```

The minimal input is a UTF-8 CSV with a `ciphertext` header. Standard CSV quoting
allows commas and newlines in a field. An optional `session` column is preserved
for traceability. If a `field` column exists, only rows whose field is exactly
`ciphertext` are analyzed. This skips the lab's armored username/message fields,
which are reversible A–P byte representations rather than English prose.

| Output | Contents |
| --- | --- |
| `analysis.json` | Input-row IDs, recovered candidate text, proofs, frequencies and all candidate scores |
| `summary.csv` | Per-row key, inverse, letter count and chi-square score |
| `candidate_ranking.csv` | 312 ranked keys per reply, with no scores omitted |
| `letter_frequencies.csv` | 26 rows per reply: ciphertext count/percentage, recovered percentage and English reference |

The saved [example output](../reports/batch_analysis/summary.csv) analyzes five
baseline replies, skips ten armored request fields, and exports 1,560 candidate
rows plus 130 frequency rows. It does not create model responses or new network
captures. Raw source evidence remains under `data/recorded/tcp_baseline`.

An analysis candidate is **not independently verified** merely because it fits
English. Arbitrary imported messages may be short, non-English or outside the
Affine model. The output explicitly distinguishes this heuristic from the
separate known-input verification performed by the lab's recorded-run command.

The workflow limits input files to 4 MiB, input records to 1,000 and each selected
ciphertext to 20,000 characters. Invalid inputs are rejected before exports are
written. Existing nonempty output directories are preserved; choose a new run
directory when repeating the command.

The static browser playground offers a related single-message workflow: recover
or transform text, inspect five candidates and a measured frequency chart, then
copy the text or download JSON. Browser analysis stays local to the page.
