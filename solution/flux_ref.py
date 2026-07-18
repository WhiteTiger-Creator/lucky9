#!/usr/bin/env python3
"""Reference implementation of the Meridian-2 flux-routing model.

Given a directed weighted flux network, compute the maximum total flux that can
be routed out of the source along node-disjoint simple directed paths, the
tie-broken set of channels that realizes it, several routing aggregates, and
integrity checksums. See /app/docs/model_spec.md for the authoritative
contract. This is NOT the sum of each reachable node's strongest path — pathways
that reuse a node cannot both be routed, so the routed flux is the best
node-disjoint packing.
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


def _packing_items(
    paths: list[tuple[int, tuple[int, ...]]]
) -> list[tuple[frozenset[int], int, tuple[int, ...]]]:
    """One item per distinct non-source node set: its maximum weight and, among
    the paths achieving that weight, the lexicographically smallest sequence."""
    best: dict[frozenset[int], tuple[int, tuple[int, ...]]] = {}
    for weight, seq in paths:
        nodes = frozenset(n for n in seq if n != SOURCE)
        if not nodes:
            continue
        cur = best.get(nodes)
        if cur is None or weight > cur[0] or (weight == cur[0] and seq < cur[1]):
            best[nodes] = (weight, seq)
    return [(nodes, w, seq) for nodes, (w, seq) in best.items()]


def _best_flux_packing(
    items: list[tuple[frozenset[int], int, tuple[int, ...]]]
) -> tuple[int, list[tuple[int, ...]]]:
    """Maximum total weight of node-disjoint items (sharing only SOURCE).

    Returns (best_total, best_paths) where best_paths is the tie-break-selected
    packing: among all node-disjoint item sets whose summed weight equals the
    maximum, the one whose selected path sequences, sorted ascending, form the
    lexicographically smallest tuple. The empty packing (0) is the baseline.
    """
    ordered = sorted(items, key=lambda it: -it[1])
    best_total = 0
    best_sel: tuple[tuple[int, ...], ...] = ()

    def rec(index: int, used: frozenset[int], total: int, chosen: list[tuple[int, ...]]) -> None:
        nonlocal best_total, best_sel
        if index >= len(ordered):
            key = tuple(sorted(chosen))
            if total > best_total or (total == best_total and key < best_sel):
                best_total = total
                best_sel = key
            return
        rec(index + 1, used, total, chosen)
        nodes, weight, seq = ordered[index]
        if not (nodes & used):
            rec(index + 1, used | nodes, total + weight, chosen + [seq])

    rec(0, frozenset(), 0, [])
    return best_total, [list(s) for s in best_sel]


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

    items = _packing_items(paths)
    max_flux, flux_paths = _best_flux_packing(items)

    routed_nodes = sorted({n for seq in flux_paths for n in seq if n != SOURCE})
    flux_path_count = len(flux_paths)
    flux_node_count = len(routed_nodes)

    # Residual: best packing over the channels NOT selected (identified by node
    # set). The competing alternatives that lost the tie-break pack among
    # themselves, so this is a genuine second packing, not trivially zero.
    selected_node_sets = {frozenset(n for n in seq if n != SOURCE) for seq in flux_paths}
    residual_items = [it for it in items if it[0] not in selected_node_sets]
    residual_flux, _ = _best_flux_packing(residual_items)

    # Selection-dependent floor-division aggregates. Per routed channel, the
    # per-hop efficiency is its flux divided by its hop count, ROUNDED DOWN
    # (integer floor division); the totals below sum and max those floors. These
    # depend on the exact tie-broken routed set, and each floor drops any
    # remainder, so an off-by-one in a channel's flux, its hop count, or the
    # routed set changes the result.
    path_efficiencies = []
    for seq in flux_paths:
        channel_flux = sum(edges[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))
        hops = len(seq) - 1
        path_efficiencies.append(channel_flux // hops)
    total_path_efficiency = sum(path_efficiencies)
    max_path_efficiency = max(path_efficiencies, default=0)
    mean_flux_floor = max_flux // flux_path_count if flux_path_count else 0

    # Sequential throughput ledger over the routed channels in order. Carry
    # propagates between consecutive channels and decays by a hop-based penalty;
    # a channel is admitted to the saturated set when its throughput reaches the
    # threshold. Order-dependent and boundary-sensitive: a slip in any floored
    # term shifts a channel across the threshold and changes the set, the count
    # and the ledger checksum. The decay/credit divisors, the threshold and the
    # carry cap are governed by the calibration log.
    SATURATION_THRESHOLD = 20
    THROUGHPUT_CAP = 60
    prev_out = 0
    saturated_endpoints: list[int] = []
    max_throughput = 0
    tp_rows: list[str] = []
    for seq in flux_paths:
        hops = len(seq) - 1
        cflux = sum(edges[seq[i]][seq[i + 1]] for i in range(hops))
        carry_in = max(prev_out - (hops * 5) // 3, 0)
        throughput = cflux + carry_in // 4
        carry_out = min(carry_in + cflux - (hops // 2), THROUGHPUT_CAP)
        if throughput >= SATURATION_THRESHOLD:
            saturated_endpoints.append(seq[-1])
        max_throughput = max(max_throughput, throughput)
        tp_rows.append(f"{seq[-1]}|{throughput}|{1 if throughput >= SATURATION_THRESHOLD else 0}|{carry_out}")
        prev_out = carry_out
    saturated_endpoints = sorted(saturated_endpoints)
    saturated_channel_count = len(saturated_endpoints)
    throughput_ledger_checksum = hashlib.sha256("\n".join(tp_rows).encode("utf-8")).hexdigest()

    edge_payload = "\n".join(
        f"{s}|{t}|{edges[s][t]}" for s in sorted(edges) for t in sorted(edges[s])
    )
    edge_checksum = hashlib.sha256(edge_payload.encode("utf-8")).hexdigest()

    flux_paths_payload = ";".join(">".join(str(n) for n in seq) for seq in flux_paths)
    flux_payload = (
        f"{node_count}|{max_flux}|{strongest_weight}|"
        f"{'>'.join(str(n) for n in strongest_seq)}|"
        f"{','.join(str(n) for n in reachable)}|"
        f"{flux_node_count}|{residual_flux}|"
        f"{total_path_efficiency}|{max_path_efficiency}|{mean_flux_floor}|"
        f"{saturated_channel_count}|{max_throughput}|"
        f"{','.join(str(n) for n in saturated_endpoints)}|"
        f"{flux_paths_payload}"
    )
    flux_checksum = hashlib.sha256(flux_payload.encode("utf-8")).hexdigest()

    return {
        "node_count": node_count,
        "reachable": reachable,
        "strongest_path": list(strongest_seq),
        "strongest_path_weight": strongest_weight,
        "max_flux": max_flux,
        "flux_paths": flux_paths,
        "flux_path_count": flux_path_count,
        "flux_node_count": flux_node_count,
        "residual_flux": residual_flux,
        "total_path_efficiency": total_path_efficiency,
        "max_path_efficiency": max_path_efficiency,
        "mean_flux_floor": mean_flux_floor,
        "saturated_endpoints": saturated_endpoints,
        "saturated_channel_count": saturated_channel_count,
        "max_throughput": max_throughput,
        "throughput_ledger_checksum": throughput_ledger_checksum,
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
