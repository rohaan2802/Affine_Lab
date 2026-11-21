#!/bin/bash
# Optional: a private hostname namespace, without isolating internet access.
set -euo pipefail
hostname rohaan-psylab
exec bash "$(dirname "$0")/run_lab.sh"
