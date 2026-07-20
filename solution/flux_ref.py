#!/usr/bin/env python3
"""Reference implementation of the Meridian-2 flux-routing model.

Given a directed weighted flux network, compute the maximum total flux that can
be routed out of the source along node-disjoint simple directed paths, the
tie-broken set of channels that realizes it, the site-conditioning and dispatch
layers applied to that set, several routing aggregates, and integrity
checksums. See /app/docs/model_spec.md for the authoritative contract. This is
NOT the sum of each reachable node's strongest path — pathways that reuse a node
cannot both be routed, so the routed flux is the best node-disjoint packing.
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

CONDITIONING_PATH = Path("/app/data/site_conditioning.json")
DAMPING_MIN = 0
DAMPING_MAX = 12
CLASS_DISPATCH_CAP = 2
POLICY_PATH = Path("/app/data/transport_policies.json")
POLICY_FIELDS = (
    "dispatch_floor", "primary_min", "primary_damping_max",
    "saturation_threshold", "throughput_cap",
)
DEFAULT_POLICY = {
    "dispatch_floor": 5, "primary_min": 6, "primary_damping_max": 7,
    "saturation_threshold": 20, "throughput_cap": 60,
}
CLASS_ORDER = ["primary", "secondary", "tertiary"]
CLASS_RANK = {name: len(CLASS_ORDER) - idx for idx, name in enumerate(CLASS_ORDER)}


def canonical_edges(edge_rows: list[list[int]]) -> dict[int, dict[int, int]]:
    """Normalize edges: drop self-loops and weights outside 1..9, collapse
    duplicate directed (source,target) rows by MINIMUM weight per MX-2251."""
    edges: dict[int, dict[int, int]] = {}
    for row in edge_rows:
        s, t, w = int(row[0]), int(row[1]), int(row[2])
        if s == t or w < WEIGHT_MIN or w > WEIGHT_MAX:
            continue
        cur = edges.get(s, {}).get(t)
        # MX-2251 reverses this: repeated links collapse to the MINIMUM weight.
        if cur is None or w < cur:
            edges.setdefault(s, {})[t] = w
    return edges


def canonical_damping(rows: list[dict]) -> dict[int, int]:
    """Normalize site conditioning per MX-2215: coerce to int, discard damping
    outside the inclusive range 0..12, and collapse repeated site entries
    keeping the MINIMUM damping per MX-2253. Sites absent from the file damp by 0."""
    out: dict[int, int] = {}
    for row in rows:
        try:
            site = int(str(row.get("site", "")).strip())
            value = int(str(row.get("damping", "")).strip())
        except (TypeError, ValueError):
            continue
        if value < DAMPING_MIN or value > DAMPING_MAX:
            continue
        cur = out.get(site)
        # MX-2253 reverses this: repeated sites collapse to the MINIMUM damping.
        if cur is None or value < cur:
            out[site] = value
    return out


def load_policies(path: Path = POLICY_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_policy(raw: object) -> dict:
    """Start from the shipped baseline and overlay any field the object supplies."""
    resolved = dict(DEFAULT_POLICY)
    if isinstance(raw, dict):
        for key in POLICY_FIELDS:
            if key in raw:
                resolved[key] = int(raw[key])
    return resolved


def policy_for_hub(hub: int, policy_data: dict) -> dict:
    """Resolve one ingress hub's policy: baseline, then default, then that hub's override.

    A sparse override supplies only the fields it names; every unlisted field is
    inherited, so an override is never a complete policy on its own.
    """
    base = _normalize_policy(policy_data.get("default", {}))
    overrides = policy_data.get("hub_overrides", {})
    if not isinstance(overrides, dict):
        return base
    raw = overrides.get(str(hub))
    if not isinstance(raw, dict):
        return base
    merged = dict(base)
    for key in POLICY_FIELDS:
        if key in raw:
            merged[key] = int(raw[key])
    return merged


def policy_checksum(policy_data: dict) -> str:
    """Resolved default, then each overridden hub in ascending numeric hub order."""
    lines = [
        "default|" + "|".join(
            str(_normalize_policy(policy_data.get("default", {}))[k]) for k in POLICY_FIELDS
        )
    ]
    overrides = policy_data.get("hub_overrides", {})
    if isinstance(overrides, dict):
        for hub in sorted(overrides, key=lambda h: int(h)):
            resolved = policy_for_hub(int(hub), policy_data)
            lines.append(f"{hub}|" + "|".join(str(resolved[k]) for k in POLICY_FIELDS))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def load_conditioning(path: Path = CONDITIONING_PATH) -> dict[int, int]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return canonical_damping(payload.get("sites", []))


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


def route_flux(node_count: int, edge_rows: list[list[int]], damping: dict[int, int] | None = None,
               policy_data: dict | None = None) -> dict:
    policy_data = policy_data or {}
    edges = canonical_edges(edge_rows)
    paths = _simple_paths(edges)
    damping = damping or {}

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
    # MX-2261: thresholds are resolved PER CHANNEL from the ingress hub's policy
    # (the channel's first hop), not taken from a single global constant.
    prev_out = 0
    saturated_endpoints: list[int] = []
    max_throughput = 0
    tp_rows: list[str] = []
    channels: list[dict] = []
    for seq in flux_paths:
        hops = len(seq) - 1
        cflux = sum(edges[seq[i]][seq[i + 1]] for i in range(hops))
        carry_in = max(prev_out - (hops * 5) // 3, 0)
        throughput = cflux + carry_in // 4
        hub_policy = policy_for_hub(seq[1], policy_data) if len(seq) > 1 else _normalize_policy(
            policy_data.get("default", {})
        )
        carry_out = min(carry_in + cflux - (hops // 2), hub_policy["throughput_cap"])
        saturated = throughput >= hub_policy["saturation_threshold"]
        if saturated:
            saturated_endpoints.append(seq[-1])
        max_throughput = max(max_throughput, throughput)
        tp_rows.append(f"{seq[-1]}|{throughput}|{1 if saturated else 0}|{carry_out}")
        channels.append(
            {
                "seq": seq,
                "endpoint": seq[-1],
                "hops": hops,
                "channel_flux": cflux,
                "throughput": throughput,
                "saturated": saturated,
                "policy": hub_policy,
            }
        )
        prev_out = carry_out
    saturated_endpoints = sorted(saturated_endpoints)
    saturated_channel_count = len(saturated_endpoints)
    throughput_ledger_checksum = hashlib.sha256("\n".join(tp_rows).encode("utf-8")).hexdigest()

    # Site conditioning and dispatch admission. Each routed channel accumulates
    # the damping of the non-source sites it visits; that accumulated damping is
    # HALVED AND ROUNDED UP (ceil) before being subtracted, per MX-2217 final,
    # whereas the hop attenuation that follows it is floored. ceil(x/2) is
    # written -(-x // 2). Both subtractions clamp at zero. The dispatch floor is
    # tuned close to the conditioned-flux distribution, so a one-unit slip in a
    # damping sum, a ceil read as a floor, or a wrong routed set moves channels
    # across the boundary and changes the dispatched set, the class counts, the
    # dispatch order and the dispatch checksum together.
    # MX-2257: site contention. An unrouted candidate that contends for sites held
    # by more than one routed channel is attributed to exactly ONE of them -- the
    # highest channel_flux, ties by smallest endpoint. That owner adds the number of
    # sites IT ITSELF shares with the candidate; every other claimant adds zero for
    # that candidate, and sites the candidate shares only with a non-owner are
    # counted by nobody.
    total_contention_overlap = 0
    for ch in channels:
        ch["site_set"] = frozenset(n for n in ch["seq"] if n != SOURCE)
    for nodes, _weight, _seq in residual_items:
        claimants = [ch for ch in channels if ch["site_set"] & nodes]
        if not claimants:
            continue
        owner = sorted(claimants, key=lambda c: (-c["channel_flux"], c["endpoint"]))[0]
        owner["contention_overlap"] = owner.get("contention_overlap", 0) + len(
            owner["site_set"] & nodes
        )

    total_damping = 0
    for ch in channels:
        damping_sum = sum(damping.get(n, 0) for n in ch["seq"] if n != SOURCE)
        contention_overlap = ch.get("contention_overlap", 0)
        damped_flux = max(
            ch["channel_flux"] - (-(-damping_sum // 2)) - contention_overlap, 0
        )
        conditioned_flux = max(damped_flux - (ch["hops"] * 3) // 2, 0)
        ch["damping_sum"] = damping_sum
        ch["contention_overlap"] = contention_overlap
        ch["damped_flux"] = damped_flux
        ch["conditioned_flux"] = conditioned_flux
        total_damping += damping_sum
        total_contention_overlap += contention_overlap

    dispatched = [
        ch for ch in channels if ch["conditioned_flux"] >= ch["policy"]["dispatch_floor"]
    ]

    # Dispatch class per MX-2221 final. Clauses are evaluated in order; the
    # first matching clause fixes the class.
    for ch in dispatched:
        if (
            (
                ch["conditioned_flux"] >= ch["policy"]["primary_min"]
                and ch["damping_sum"] <= ch["policy"]["primary_damping_max"]
            )
            or (ch["saturated"] and ch["hops"] <= 1)
        ):
            ch["dispatch_class"] = "primary"
        elif ch["saturated"] or ch["damped_flux"] >= 12:
            ch["dispatch_class"] = "secondary"
        else:
            ch["dispatch_class"] = "tertiary"

    class_counts = {name: 0 for name in CLASS_ORDER}
    for ch in dispatched:
        class_counts[ch["dispatch_class"]] += 1

    # Dispatch ordering per MX-2223 final, applied strictly in sequence.
    ordered_dispatch = sorted(
        dispatched,
        key=lambda ch: (
            -CLASS_RANK[ch["dispatch_class"]],
            -ch["conditioned_flux"],
            -ch["damped_flux"],
            -ch["channel_flux"],
            -ch["throughput"],
            ch["hops"],
            ch["endpoint"],
        ),
    )

    # MX-2255: capacity cap applied AFTER the ordering chain, two per class.
    kept_per_class: dict[str, int] = {}
    capped_dispatch = []
    for ch in ordered_dispatch:
        taken = kept_per_class.get(ch["dispatch_class"], 0)
        if taken < CLASS_DISPATCH_CAP:
            capped_dispatch.append(ch)
            kept_per_class[ch["dispatch_class"]] = taken + 1
    ordered_dispatch = capped_dispatch
    dispatched = capped_dispatch
    class_counts = {name: 0 for name in CLASS_ORDER}
    for ch in dispatched:
        class_counts[ch["dispatch_class"]] += 1
    dispatch_order = [ch["endpoint"] for ch in ordered_dispatch]
    dispatched_endpoints = sorted(ch["endpoint"] for ch in dispatched)
    dispatched_channel_count = len(dispatched)
    total_conditioned_flux = sum(ch["conditioned_flux"] for ch in dispatched)
    max_conditioned_flux = max((ch["conditioned_flux"] for ch in dispatched), default=0)

    dispatch_rows = [
        f"{ch['endpoint']}|{ch['dispatch_class']}|{ch['conditioned_flux']}|"
        f"{ch['damped_flux']}|{ch['damping_sum']}"
        for ch in ordered_dispatch
    ]
    dispatch_checksum = hashlib.sha256("\n".join(dispatch_rows).encode("utf-8")).hexdigest()

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
        f"{total_damping}|{total_conditioned_flux}|{max_conditioned_flux}|"
        f"{dispatched_channel_count}|"
        f"{','.join(str(n) for n in dispatch_order)}|"
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
        "total_damping": total_damping,
        "policy_checksum": policy_checksum(policy_data),
        "total_contention_overlap": total_contention_overlap,
        "dispatched_endpoints": dispatched_endpoints,
        "dispatched_channel_count": dispatched_channel_count,
        "total_conditioned_flux": total_conditioned_flux,
        "max_conditioned_flux": max_conditioned_flux,
        "class_counts": class_counts,
        "dispatch_order": dispatch_order,
        "dispatch_checksum": dispatch_checksum,
        "edge_checksum": edge_checksum,
        "flux_checksum": flux_checksum,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/app/data/network.json")
    parser.add_argument("--output-dir", default="/app/output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    damping = load_conditioning()
    result = route_flux(data["node_count"], data["edges"], damping, load_policies())
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
