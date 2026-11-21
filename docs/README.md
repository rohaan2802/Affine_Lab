# Documentation guide

Start with the guide matching your review goal. The maintained implementation
is in [`src/affine_lab`](../src/affine_lab); the package build and resources are
declared in [`pyproject.toml`](../pyproject.toml).

| Goal | Guide |
| --- | --- |
| Understand the whole project, inputs, modes, protocol, modules and outputs | [Detailed project reference](PROJECT_REFERENCE.md) |
| Give a short demo with copyable commands | [Demo guide](DEMO_GUIDE.txt) |
| Explain the exercise step by step in simple terms | [Complete walkthrough](PROJECT_WALKTHROUGH.txt) |
| Review boundaries, efficiency and failure behavior | [Architecture](ARCHITECTURE.md) |
| Trace original captures and distinguish saved results from fresh runs | [Data provenance](DATA_PROVENANCE.md) |
| Import ciphertext CSVs and inspect complete candidate/frequency exports | [CSV workflow](CSV_WORKFLOW.md) |
| Assess exactly what passed and what was not tested | [Verification](VERIFICATION.md) |
| Understand cipher weaknesses and real-service alternatives | [Security reflection](SECURITY_REFLECTION.md) |
| Read the authored assignment/pre-demo PDFs | [Coursework reports](reports/README.md) |
| Browse matching desktop captures | [Coursework screenshots](../evidence/coursework/index.html) |
| Review earlier authored scripts and browser source | [Historical source](../legacy/coursework/README_HISTORY.md) |
| Understand which historical material stays local and outside Git | [Local history policy](LOCAL_HISTORY.md) |

## Suggested review order

1. Open the [static portfolio](../index.html) and recover its supplied sample.
2. Compare the [replay summary](../reports/replay_demo/summary.csv) with the
   [full result](../reports/replay_demo/result.json) and readable proof.
3. Follow the reference's module table into the maintained analyzer and verifier.
4. Read the provenance and verification guides before interpreting the results.
5. Run a new local replay or CSV analysis using the demo guide.

## Keeping the presentation consistent

The detailed reference content is maintained in
[`tools/project_reference.py`](../tools/project_reference.py). The build tool
renders that same content into the README, webpage and reference document;
dataset rows and benchmark values come from the actual fixtures/reports.
Edit the shared source rather than separately changing generated paragraphs.

```bash
python tools/build_portfolio.py
python tools/check_portfolio.py
python tools/check_publish.py
```

The 24 figure entries are shared through the canonical image manifest. Figure
generation uses development dependencies, while the runtime application remains
standard-library-only. New API generation is never required to rebuild the
static documentation or inspect the saved evidence.
