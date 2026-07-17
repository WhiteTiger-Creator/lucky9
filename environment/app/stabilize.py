#!/usr/bin/env python3
"""Meridian-2 SE-draining chip-firing simulation.

Skeleton only. The Meridian-2 toppling rule, the mandated firing schedule, the
output keys, and the grid_checksum serialization are all specified in
/app/docs/model_spec.md. Fill in `stabilize` to evolve the field to its
stabilized configuration and emit result.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def stabilize(rows: int, cols: int, drops: list[list[int]]) -> dict:
    """Evolve the Meridian-2 field to its stabilized configuration.

    See /app/docs/model_spec.md for the toppling rule, the mandated firing
    schedule (fire the smallest-index unstable site once per step), the surge
    term, and the exact result.json keys and checksum serialization.
    """
    raise NotImplementedError(
        "Implement the Meridian-2 model defined in /app/docs/model_spec.md"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/app/data/drops.json")
    parser.add_argument("--output-dir", default="/app/output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    result = stabilize(data["rows"], data["cols"], data["drops"])
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
