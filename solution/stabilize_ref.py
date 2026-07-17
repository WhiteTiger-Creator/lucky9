#!/usr/bin/env python3
"""Reference simulation for the Meridian-2 directed lattice-relaxation model.

Implements the mandated single-event schedule (smallest-index overloaded site
relaxed once per event) with the state-dependent southward surge defined in
/app/docs/model_spec.md, then records the steady-state lattice and observables.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from pathlib import Path

THRESHOLD = 4


def stabilize(rows: int, cols: int, drops: list[list[int]]) -> dict:
    grid = [[0] * cols for _ in range(rows)]
    for r, c, n in drops:
        grid[r][c] += n

    fired = [[0] * cols for _ in range(rows)]
    spill = 0
    total_firings = 0

    # min-heap keyed by (row, col) realises "relax the smallest-index overloaded
    # site, once per event"; stale entries are skipped on pop.
    heap = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] >= THRESHOLD]
    heapq.heapify(heap)

    while heap:
        r, c = heapq.heappop(heap)
        if grid[r][c] < THRESHOLD:
            continue
        surge = grid[r][c] // 8
        grid[r][c] -= (4 + surge)
        fired[r][c] += 1
        total_firings += 1

        if c + 1 < cols:
            grid[r][c + 1] += 2
            if grid[r][c + 1] >= THRESHOLD:
                heapq.heappush(heap, (r, c + 1))
        else:
            spill += 2

        south = 2 + surge
        if r + 1 < rows:
            grid[r + 1][c] += south
            if grid[r + 1][c] >= THRESHOLD:
                heapq.heappush(heap, (r + 1, c))
        else:
            spill += south

        if grid[r][c] >= THRESHOLD:
            heapq.heappush(heap, (r, c))

    serialized = "\n".join(" ".join(str(v) for v in row) for row in grid)
    checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return {
        "rows": rows,
        "cols": cols,
        "grid": grid,
        "total_firings": total_firings,
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
