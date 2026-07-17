#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "${SCRIPT_DIR}/stabilize_ref.py" /app/stabilize.py
python3 /app/stabilize.py --output-dir /app/output
