#!/usr/bin/env python3
"""Reference stabilizer for the Meridian SE-draining chip-firing model.

Reads /app/data/drops.json, applies every chip drop, stabilizes under the
directed firing rule in /app/docs/model_spec.md, and writes the stabilized
grid and its derived quantities to the output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

THRESHOLD = 4


def stabilize(rows: int, cols: int, drops: list[list[int]]) -> dict:
    grid = [[0] * cols for _ in range(rows)]
    for r, c, n in drops:
        grid[r][c] += n

    fired = [[0] * cols for _ in range(rows)]
    spill = 0
    queue = deque()
    inq = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] >= THRESHOLD:
                queue.append((r, c))
                inq[r][c] = True

    total_firings = 0
    while queue:
        r, c = queue.popleft()
        inq[r][c] = False
        if grid[r][c] < THRESHOLD:
            continue
        times = grid[r][c] // THRESHOLD  # fire greedily; confluent either way
        grid[r][c] -= times * THRESHOLD
        fired[r][c] += times
        total_firings += times
        # send 2 East, 2 South per firing; off-grid drains to the sink
        east_r, east_c = r, c + 1
        south_r, south_c = r + 1, c
        if east_c < cols:
            grid[east_r][east_c] += 2 * times
            if grid[east_r][east_c] >= THRESHOLD and not inq[east_r][east_c]:
                queue.append((east_r, east_c))
                inq[east_r][east_c] = True
        else:
            spill += 2 * times
        if south_r < rows:
            grid[south_r][south_c] += 2 * times
            if grid[south_r][south_c] >= THRESHOLD and not inq[south_r][south_c]:
                queue.append((south_r, south_c))
                inq[south_r][south_c] = True
        else:
            spill += 2 * times

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
