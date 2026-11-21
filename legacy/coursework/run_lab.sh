#!/bin/bash
# Execute inside WSL as root only for loopback packet capture.
set -euo pipefail
cd "$(dirname "$0")"
source env.sh
PY="${LAB_PYTHON:-/home/codetech/psycare_lab/.venv/bin/python}"
mkdir -p output evidence
exec > >(tee output/run_log.txt) 2>&1
printf 'Actual run time: '; date --iso-8601=seconds
printf 'Host: '; hostname
printf 'Linux: '; uname -r
"$PY" --version
printf 'Capture scope: loopback interface lo; tcp port 9999 only\n'
printf 'Backend: Gemini API, instructor exception reported by student; NOT offline\n'
SERVER='';CAPTURE=''
cleanup() {
 [ -z "$SERVER" ] || kill "$SERVER" 2>/dev/null || true
 [ -z "$CAPTURE" ] || kill -INT "$CAPTURE" 2>/dev/null || true
}
trap cleanup EXIT
# No credentials are included in this port-filtered capture.
tcpdump -i lo -U -n -s 0 -Z root -w evidence/capture.pcap 'tcp port 9999' 2>output/tcpdump.log &
CAPTURE=$!
: > output/server.log
"$PY" -u server.py >output/server.log 2>&1 &
SERVER=$!
for i in $(seq 1 40); do
 ss -ltnpH | grep -E '127\.0\.0\.1:9999\b' | grep -q "pid=$SERVER," && break
 kill -0 "$SERVER" 2>/dev/null || { cat output/server.log; exit 1; }
 sleep 1
done
ss -ltnpH | grep -E '127\.0\.0\.1:9999\b' | grep -q "pid=$SERVER," || { cat output/server.log; echo 'Server not ready'; exit 1; }
"$PY" -u client.py | tee output/client_output.txt
sleep 2
kill -INT "$CAPTURE"; wait "$CAPTURE" || true; CAPTURE=''
kill "$SERVER"; wait "$SERVER" 2>/dev/null || true; SERVER=''
cat output/tcpdump.log
bash run_analysis.sh
