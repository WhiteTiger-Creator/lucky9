#!/usr/bin/env python3
"""Meridian chip-firing stabilizer.

This draft implements the classic four-neighbour sandpile: it fires cells at a
threshold of 4 and pushes one chip to each orthogonal neighbour. It predates
the SE-draining rule and does not match the current model contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

THRESHOLD = 4


def stabilize(rows: int, cols: int, drops: list[list[int]]) -> dict:
    grid = [[0] * cols for _ in range(rows)]
    for r, c, n in drops:
        grid[r][c] += n

    fired = [[0] * cols for _ in range(rows)]
    spill = 0
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            for c in range(cols):
                while grid[r][c] >= THRESHOLD:
                    grid[r][c] -= THRESHOLD
                    fired[r][c] += 1
                    changed = True
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            grid[nr][nc] += 1
                        else:
                            spill += 1

    serialized = "\n".join(" ".join(str(v) for v in row) for row in grid)
    checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return {
        "rows": rows,
        "cols": cols,
        "grid": grid,
        "total_firings": sum(sum(row) for row in fired),
        "row_firings": [sum(row) for row in fired],
        "spill": spill,
        "grid_checksum": checksum,
    }


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
