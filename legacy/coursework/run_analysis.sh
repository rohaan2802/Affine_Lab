#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source env.sh
mkdir -p output
exec > >(tee output/analysis_log.txt) 2>&1
printf 'Analysis time: '; date --iso-8601=seconds
PY="${LAB_PYTHON:-/home/codetech/psycare_lab/.venv/bin/python}"
"$PY" scripts/extract_tcp.py
"$PY" scripts/analyze.py
"$PY" scripts/verify_results.py
