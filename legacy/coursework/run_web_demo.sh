#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source env.sh
PY="${LAB_PYTHON:-/home/codetech/psycare_lab/.venv/bin/python}"
CAPTURE=''
WEB_PID=''
cleanup() {
  if [ -n "$WEB_PID" ]; then
    kill -TERM "$WEB_PID" 2>/dev/null || true
    wait "$WEB_PID" 2>/dev/null || true
  fi
  if [ -n "$CAPTURE" ]; then
    kill -INT "$CAPTURE" 2>/dev/null || true
    wait "$CAPTURE" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
if [ "$(id -u)" -eq 0 ]; then
  mkdir -p web_runs
  export WEB_DEMO_CAPTURE_PATH="web_runs/web_demo_$(date +%Y%m%d_%H%M%S).pcap"
  tcpdump -i lo -U -n -s 0 -Z root -w "$WEB_DEMO_CAPTURE_PATH" 'tcp port 9999' 2>web_runs/capture.log &
  CAPTURE=$!
  sleep 1
  kill -0 "$CAPTURE" || { echo 'Packet capture failed'; exit 1; }
else
  echo 'Live UI enabled without packet capture. Use the root launcher for a PCAP.'
fi
"$PY" -u web_demo.py &
WEB_PID=$!
wait "$WEB_PID"
