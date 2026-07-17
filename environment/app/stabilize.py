#!/usr/bin/env python3
"""Meridian-2 directed lattice-relaxation simulation.

Skeleton only. The form of the model and the output contract are in
/app/docs/model_spec.md; the calibrated constants (overload threshold, surge
divisor, base removal, eastward and southward fluxes) and the relaxation
schedule are recorded in /app/docs/calibration_notebook.md and must be
reconciled from it. Fill in `stabilize` to evolve the lattice to its steady
state and record the observables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def stabilize(rows: int, cols: int, drops: list[list[int]]) -> dict:
    """Evolve the Meridian-2 lattice to its steady state.

    See /app/docs/model_spec.md for the relaxation-rule form and the exact
    observable keys and checksum serialization. Reconcile the calibrated
    constants and the relaxation schedule from /app/docs/calibration_notebook.md.
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
