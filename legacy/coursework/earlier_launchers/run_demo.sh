#!/bin/bash
# Run inside the private UTS namespace; capture needs WSL root.
set -euo pipefail
cd "$(dirname "$0")"
source env.sh
PY="${LAB_PYTHON:-/home/codetech/A02_PsycoSupport/psycare_lab/.venv/bin/python}"
if [ "$(id -u)" -ne 0 ]; then
  echo 'Use the exact wsl.exe / PowerShell command in DEMO_GUIDE.txt.'
  exit 1
fi
if [ -n "$(ss -ltnH 'sport = :9999')" ]; then
  echo 'Port 9999 is already in use. Stop the earlier lab server first.'
  exit 1
fi
"$PY" scripts/prepare_demo.py
exec bash lab_inner.sh
