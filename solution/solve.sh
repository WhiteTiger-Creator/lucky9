#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "${SCRIPT_DIR}/exec_audit.py" /app/exec_audit.py
python3 /app/exec_audit.py repair --output-dir /app/output
