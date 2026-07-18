#!/usr/bin/env python3
"""Meridian-2 network transport computation.

Skeleton only. The network format, the site-conditioning input, the conditioning
rules, the transport-channel definition and span bound, the sustained-flux
observable (max_flux, the maximum flux over vertex-disjoint transport channels —
NOT the per-site sum of strongest channels and NOT a greedy value), the damping
and dispatch layers applied to the routed set, and the exact result.json keys and
checksum serialization are all specified in /app/docs/model_spec.md. Fill in
`route_flux` to evaluate the transport and record the observables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def route_flux(node_count: int, edges: list[list[int]]) -> dict:
    """Evaluate the Meridian-2 network transport and return the observables.

    See /app/docs/model_spec.md for the conditioning of the links, the
    transport-channel definition and 5-link span bound, the max_flux sustained-
    flux observable (the maximum flux over vertex-disjoint channels, which is NOT
    the per-site sum of strongest channels and NOT a greedy value), the site
    conditioning input and the damping/dispatch layers, the result keys, and the
    checksum serialization.
    """
    raise NotImplementedError(
        "Implement the Meridian-2 network transport defined in /app/docs/model_spec.md"
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
