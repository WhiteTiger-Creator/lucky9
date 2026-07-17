#!/usr/bin/env python3
"""Meridian-2 flux-routing computation.

Skeleton only. The network format, canonicalization rules, the pathway
definition and hop bound, the routed-flux (node-disjoint packing) objective, and
the exact result.json keys and checksum serialization are all specified in
/app/docs/model_spec.md. Fill in `route_flux` to compute the routing and record
the observables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def route_flux(node_count: int, edges: list[list[int]]) -> dict:
    """Route the Meridian-2 flux network and return the result observables.

    See /app/docs/model_spec.md for canonicalization, the pathway definition and
    5-edge hop bound, the max_flux node-disjoint packing objective (which is NOT
    the per-target sum of strongest pathways), the result keys, and the checksum
    serialization.
    """
    raise NotImplementedError(
        "Implement the Meridian-2 flux routing defined in /app/docs/model_spec.md"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/app/data/network.json")
    parser.add_argument("--output-dir", default="/app/output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    result = route_flux(data["node_count"], data["edges"])
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
