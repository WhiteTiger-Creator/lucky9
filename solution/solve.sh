#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "${SCRIPT_DIR}/flux_ref.py" /app/flux.py
python3 /app/flux.py --output-dir /app/output
