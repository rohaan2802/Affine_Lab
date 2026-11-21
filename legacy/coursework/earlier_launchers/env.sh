export TASK_LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LAB_PYTHON="$TASK_LAB/.venv/bin/python"
export PATH="$TASK_LAB/.tools/bin:$PATH"
export TSHARK="$TASK_LAB/.tools/bin/tshark"
export PYTHONUNBUFFERED=1
