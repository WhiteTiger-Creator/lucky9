#!/usr/bin/env python3
"""Reference implementation of the Meridian-2 flux-routing model.

Given a directed weighted flux network, compute the maximum total flux that can
be routed out of the source along node-disjoint simple directed paths, together
with the strongest single pathway and integrity checksums. See
/app/docs/model_spec.md for the authoritative contract. This is NOT the sum of
each reachable node's strongest path — pathways that reuse a node cannot both be
routed, so the routed flux is the best node-disjoint packing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE = 0
HOP_BOUND = 5
WEIGHT_MIN = 1
WEIGHT_MAX = 9


def canonical_edges(edge_rows: list[list[int]]) -> dict[int, dict[int, int]]:
    """Normalize edges: drop self-loops and weights outside 1..9, collapse
    duplicate directed (source,target) rows by maximum weight."""
    edges: dict[int, dict[int, int]] = {}
    for row in edge_rows:
        s, t, w = int(row[0]), int(row[1]), int(row[2])
        if s == t or w < WEIGHT_MIN or w > WEIGHT_MAX:
            continue
        cur = edges.get(s, {}).get(t)
        if cur is None or w > cur:
            edges.setdefault(s, {})[t] = w
    return edges


def _simple_paths(edges: dict[int, dict[int, int]]) -> list[tuple[int, tuple[int, ...]]]:
    """Every simple directed path of 1..HOP_BOUND edges from SOURCE."""
    paths: list[tuple[int, tuple[int, ...]]] = []

    def dfs(node: int, weight: int, nodes: tuple[int, ...], depth: int) -> None:
        for target in sorted(edges.get(node, {})):
            if target in nodes:
                continue
            w = weight + edges[node][target]
            seq = nodes + (target,)
            paths.append((w, seq))
            if depth + 1 < HOP_BOUND:
                dfs(target, w, seq, depth + 1)

    dfs(SOURCE, 0, (SOURCE,), 0)
    return paths


def _max_flux(paths: list[tuple[int, tuple[int, ...]]]) -> int:
    """Maximum total weight of node-disjoint (sharing only SOURCE) simple paths."""
    best_for_set: dict[frozenset[int], int] = {}
    for weight, seq in paths:
        nodes = frozenset(n for n in seq if n != SOURCE)
        if nodes and (nodes not in best_for_set or weight > best_for_set[nodes]):
            best_for_set[nodes] = weight
    items = sorted(best_for_set.items(), key=lambda kv: -kv[1])
    best = 0

    def rec(index: int, used: frozenset[int], total: int) -> None:
        nonlocal best
        if total > best:
            best = total
        if index >= len(items):
            return
        rec(index + 1, used, total)
        nodes, weight = items[index]
        if not (nodes & used):
            rec(index + 1, used | nodes, total + weight)

    rec(0, frozenset(), 0)
    return best


def route_flux(node_count: int, edge_rows: list[list[int]]) -> dict:
    edges = canonical_edges(edge_rows)
    paths = _simple_paths(edges)

    reachable = sorted({seq[-1] for _, seq in paths})

    strongest_weight = 0
    strongest_seq: tuple[int, ...] = (SOURCE,)
    for weight, seq in paths:
        if weight > strongest_weight or (weight == strongest_weight and seq < strongest_seq):
            strongest_weight = weight
            strongest_seq = seq

    max_flux = _max_flux(paths)

    edge_payload = "\n".join(
        f"{s}|{t}|{edges[s][t]}" for s in sorted(edges) for t in sorted(edges[s])
    )
    edge_checksum = hashlib.sha256(edge_payload.encode("utf-8")).hexdigest()

    flux_payload = (
        f"{node_count}|{max_flux}|{strongest_weight}|"
        f"{'>'.join(str(n) for n in strongest_seq)}|"
        f"{','.join(str(n) for n in reachable)}"
    )
    flux_checksum = hashlib.sha256(flux_payload.encode("utf-8")).hexdigest()

    return {
        "node_count": node_count,
        "reachable": reachable,
        "strongest_path": list(strongest_seq),
        "strongest_path_weight": strongest_weight,
        "max_flux": max_flux,
        "edge_checksum": edge_checksum,
        "flux_checksum": flux_checksum,
    }


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
