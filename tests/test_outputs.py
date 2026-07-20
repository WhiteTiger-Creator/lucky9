"""Verifier for the Meridian-2 flux-routing task.

The agent's /app/flux.py is run against the shipped network and against a
held-out alternate network. Outputs are checked against exact fixtures and
against structural invariants (canonical checksums, the packing objective, and
the strongest-pathway definition).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path("/app/flux.py")
DATA = Path("/app/data/network.json")
TEST_DIR = Path(os.environ.get("TEST_DIR", "/tests"))
FIX = TEST_DIR / "fixtures"
EXPECTED = json.loads((FIX / "expected_result.json").read_text())

SOURCE = 0
HOP_BOUND = 5


def _run(tmp: Path, input_path: Path = DATA) -> dict:
    out = tmp / "out"
    subprocess.run(
        [sys.executable, str(APP), "--input", str(input_path), "--output-dir", str(out)],
        check=True, capture_output=True, text=True,
    )
    return json.loads((out / "result.json").read_text())


def _canonical_edges(edge_rows):
    edges: dict = {}
    for s, t, w in edge_rows:
        s, t, w = int(s), int(t), int(w)
        if s == t or w < 1 or w > 9:
            continue
        # MX-2251: repeated links collapse to the MINIMUM weight.
        if t not in edges.get(s, {}) or w < edges[s][t]:
            edges.setdefault(s, {})[t] = w
    return edges


def _simple_paths(edges):
    paths = []

    def dfs(node, weight, nodes, depth):
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


def _naive_sum(edge_rows):
    best = {}
    for w, seq in _simple_paths(_canonical_edges(edge_rows)):
        tgt = seq[-1]
        if tgt == SOURCE:
            continue
        if tgt not in best or w > best[tgt]:
            best[tgt] = w
    return sum(best.values())


@pytest.fixture(scope="module")
def result(tmp_path_factory) -> dict:
    """Run the agent's routing once on the shipped network."""
    assert APP.exists(), "flux.py is missing"
    return _run(tmp_path_factory.mktemp("primary"))


def test_result_has_required_keys(result):
    """result.json carries exactly the contracted key set."""
    assert set(result) == {"node_count", "reachable", "strongest_path",
                           "strongest_path_weight", "max_flux",
                           "flux_paths", "flux_path_count", "flux_node_count",
                           "residual_flux", "total_path_efficiency",
                           "max_path_efficiency", "mean_flux_floor",
                           "saturated_endpoints", "saturated_channel_count",
                           "max_throughput", "throughput_ledger_checksum",
                           "total_damping", "total_contention_overlap", "policy_checksum",
                           "dispatched_endpoints",
                           "dispatched_channel_count", "total_conditioned_flux",
                           "max_conditioned_flux", "class_counts",
                           "dispatch_order", "dispatch_checksum",
                           "edge_checksum", "flux_checksum"}


def test_matches_fixture(result):
    """The full result matches the reference fixture exactly."""
    assert result == EXPECTED


def test_generalizes_to_alternate_input(tmp_path):
    """The routing reproduces the reference output for a held-out network."""
    alt_expected = json.loads((FIX / "alt_expected.json").read_text())
    got = _run(tmp_path, input_path=FIX / "alt_network.json")
    assert got == alt_expected


def test_edge_checksum_consistent(result):
    """edge_checksum is the SHA-256 of the canonical-edge serialization."""
    data = json.loads(DATA.read_text())
    edges = _canonical_edges(data["edges"])
    payload = "\n".join(
        f"{s}|{t}|{edges[s][t]}" for s in sorted(edges) for t in sorted(edges[s])
    )
    assert result["edge_checksum"] == hashlib.sha256(payload.encode()).hexdigest()


def test_flux_checksum_consistent(result):
    """flux_checksum is the SHA-256 of the contracted flux payload."""
    paths = ";".join(">".join(str(n) for n in seq) for seq in result["flux_paths"])
    payload = (
        f"{result['node_count']}|{result['max_flux']}|{result['strongest_path_weight']}|"
        f"{'>'.join(str(n) for n in result['strongest_path'])}|"
        f"{','.join(str(n) for n in result['reachable'])}|"
        f"{result['flux_node_count']}|{result['residual_flux']}|"
        f"{result['total_path_efficiency']}|{result['max_path_efficiency']}|"
        f"{result['mean_flux_floor']}|"
        f"{result['saturated_channel_count']}|{result['max_throughput']}|"
        f"{','.join(str(n) for n in result['saturated_endpoints'])}|"
        f"{result['total_damping']}|{result['total_conditioned_flux']}|"
        f"{result['max_conditioned_flux']}|{result['dispatched_channel_count']}|"
        f"{','.join(str(n) for n in result['dispatch_order'])}|{paths}"
    )
    assert result["flux_checksum"] == hashlib.sha256(payload.encode()).hexdigest()


def test_throughput_ledger_consistent(result):
    """The throughput ledger reproduces the log-governed carry/threshold rule."""
    data = json.loads(DATA.read_text())
    edges = _canonical_edges(data["edges"])
    policy_data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    prev_out, sat, max_tp, rows = 0, [], 0, []
    for seq in result["flux_paths"]:
        hops = len(seq) - 1
        # MX-2261: the carry cap and saturation bar come from the INGRESS HUB's
        # resolved policy, so they differ between channels.
        pol = _resolve_policy(seq[1], policy_data) if len(seq) > 1 else _resolve_policy("_", policy_data)
        cflux = sum(edges[seq[i]][seq[i + 1]] for i in range(hops))
        carry_in = max(prev_out - (hops * 5) // 3, 0)
        throughput = cflux + carry_in // 4
        carry_out = min(carry_in + cflux - (hops // 2), pol["throughput_cap"])
        saturated = throughput >= pol["saturation_threshold"]
        if saturated:
            sat.append(seq[-1])
        max_tp = max(max_tp, throughput)
        rows.append(f"{seq[-1]}|{throughput}|{1 if saturated else 0}|{carry_out}")
        prev_out = carry_out
    assert result["saturated_endpoints"] == sorted(sat)
    assert result["saturated_channel_count"] == len(sat)
    assert result["max_throughput"] == max_tp
    assert result["throughput_ledger_checksum"] == hashlib.sha256("\n".join(rows).encode()).hexdigest()


def test_path_efficiency_consistent(result):
    """The efficiency aggregates are the floored per-hop efficiencies of the routed set."""
    data = json.loads(DATA.read_text())
    edges = _canonical_edges(data["edges"])
    effs = []
    for seq in result["flux_paths"]:
        flux = sum(edges[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))
        effs.append(flux // (len(seq) - 1))
    assert result["total_path_efficiency"] == sum(effs)
    assert result["max_path_efficiency"] == (max(effs) if effs else 0)
    fpc = result["flux_path_count"]
    assert result["mean_flux_floor"] == (result["max_flux"] // fpc if fpc else 0)


def test_routed_set_is_valid_disjoint_optimal(result):
    """flux_paths is a vertex-disjoint channel set summing to max_flux."""
    data = json.loads(DATA.read_text())
    edges = _canonical_edges(data["edges"])
    paths = result["flux_paths"]
    assert paths == sorted(paths), "flux_paths must be sorted ascending"
    assert result["flux_path_count"] == len(paths)
    used, total, sites = set(), 0, set()
    for seq in paths:
        assert seq[0] == SOURCE, "each channel begins at the source"
        body = [n for n in seq if n != SOURCE]
        assert not (set(body) & used), "routed channels are not vertex-disjoint"
        used |= set(body)
        sites |= set(body)
        # channel flux is the sum of its consecutive edge weights
        total += sum(edges[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))
    assert total == result["max_flux"], "routed set flux != max_flux"
    assert result["flux_node_count"] == len(sites)


def test_residual_below_max_flux(result):
    """residual_flux is a valid packing no larger than max_flux."""
    assert 0 <= result["residual_flux"] <= result["max_flux"]


def test_max_flux_is_packing_not_naive_sum(result):
    """max_flux is the node-disjoint packing, strictly below the naive per-target sum here."""
    data = json.loads(DATA.read_text())
    naive = _naive_sum(data["edges"])
    assert result["max_flux"] <= naive
    assert result["max_flux"] != naive, "max_flux equals the naive per-target sum (wrong objective)"


def test_strongest_path_well_formed(result):
    """strongest_path starts at the source and its weight is consistent."""
    assert result["strongest_path"][0] == SOURCE
    assert isinstance(result["strongest_path_weight"], int)
    assert result["strongest_path_weight"] >= 0


def test_reachable_sorted_distinct(result):
    """reachable is sorted, distinct, and excludes the source."""
    r = result["reachable"]
    assert r == sorted(set(r))
    assert SOURCE not in r


def test_source_does_not_reference_verifier_trees():
    """The routing source does not read or import verifier artifacts."""
    src = APP.read_text()
    for token in ("/tests", "/solution", "expected_result.json", "alt_expected.json"):
        assert token not in src


# --- site conditioning / dispatch layer -------------------------------------

CONDITIONING = Path("/app/data/site_conditioning.json")
CLASS_ORDER = ("primary", "secondary", "tertiary")
CLASS_RANK = {n: len(CLASS_ORDER) - i for i, n in enumerate(CLASS_ORDER)}
DISPATCH_FLOOR = 5


def _canonical_damping():
    """MX-2215: discard damping outside 0..12, collapse repeats keeping MAXIMUM."""
    rows = json.loads(CONDITIONING.read_text())["sites"]
    out = {}
    for row in rows:
        site, value = int(row["site"]), int(row["damping"])
        if value < 0 or value > 12:
            continue
        # MX-2253: repeated sites collapse to the MINIMUM damping.
        if site not in out or value < out[site]:
            out[site] = value
    return out


def _contention_overlaps(result, edges):
    """MX-2257 attribution: {owner_endpoint: contention_overlap}, computed here
    independently of the reconciler so the dispatch recomputation stays honest."""
    paths = []

    def dfs(node, weight, nodes, depth):
        for target in sorted(edges.get(node, {})):
            if target in nodes:
                continue
            seq = nodes + (target,)
            paths.append((weight + edges[node][target], seq))
            if depth + 1 < HOP_BOUND:
                dfs(target, weight + edges[node][target], seq, depth + 1)

    dfs(SOURCE, 0, (SOURCE,), 0)
    best = {}
    for weight, seq in paths:
        nodes = frozenset(n for n in seq if n != SOURCE)
        if not nodes:
            continue
        cur = best.get(nodes)
        if cur is None or weight > cur[0] or (weight == cur[0] and seq < cur[1]):
            best[nodes] = (weight, seq)

    routed = [frozenset(n for n in seq if n != SOURCE) for seq in result["flux_paths"]]
    endpoints = [seq[-1] for seq in result["flux_paths"]]
    fluxes = [
        sum(edges[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))
        for seq in result["flux_paths"]
    ]
    out = {}
    for nodes in best:
        if nodes in routed:
            continue
        claimants = [i for i, rs in enumerate(routed) if rs & nodes]
        if not claimants:
            continue
        owner = sorted(claimants, key=lambda i: (-fluxes[i], endpoints[i]))[0]
        out[endpoints[owner]] = out.get(endpoints[owner], 0) + len(routed[owner] & nodes)
    return out


def _dispatch_layer(result):
    """Recompute the damping/dispatch layer independently from the routed set."""
    edges = _canonical_edges(json.loads(DATA.read_text())["edges"])
    damping = _canonical_damping()
    policy_data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    prev_out, channels = 0, []
    for seq in result["flux_paths"]:
        hops = len(seq) - 1
        pol = _resolve_policy(seq[1], policy_data) if len(seq) > 1 else _resolve_policy("_", policy_data)
        cflux = sum(edges[seq[i]][seq[i + 1]] for i in range(hops))
        carry_in = max(prev_out - (hops * 5) // 3, 0)
        throughput = cflux + carry_in // 4
        prev_out = min(carry_in + cflux - (hops // 2), pol["throughput_cap"])
        dsum = sum(damping.get(n, 0) for n in seq if n != SOURCE)
        channels.append({
            "endpoint": seq[-1], "hops": hops, "channel_flux": cflux, "seq": seq,
            "throughput": throughput, "saturated": throughput >= pol["saturation_threshold"],
            "policy": pol,
            "damping_sum": dsum,
        })
    # MX-2257: contention from unrouted candidates, attributed to a single owner.
    contention = _contention_overlaps(result, edges)
    for c in channels:
        co = contention.get(c["endpoint"], 0)
        damped = max(c["channel_flux"] - (-(-c["damping_sum"] // 2)) - co, 0)
        c["contention_overlap"] = co
        c["damped_flux"] = damped
        c["conditioned_flux"] = max(damped - (c["hops"] * 3) // 2, 0)
    dispatched = [c for c in channels if c["conditioned_flux"] >= c["policy"]["dispatch_floor"]]
    for c in dispatched:
        if (
            c["conditioned_flux"] >= c["policy"]["primary_min"]
            and c["damping_sum"] <= c["policy"]["primary_damping_max"]
        ) or (c["saturated"] and c["hops"] <= 1):
            c["dispatch_class"] = "primary"
        elif c["saturated"] or c["damped_flux"] >= 12:
            c["dispatch_class"] = "secondary"
        else:
            c["dispatch_class"] = "tertiary"
    ordered = sorted(dispatched, key=lambda c: (
        -CLASS_RANK[c["dispatch_class"]], -c["conditioned_flux"], -c["damped_flux"],
        -c["channel_flux"], -c["throughput"], c["hops"], c["endpoint"]))
    # MX-2255: capacity cap applied AFTER the ordering chain, two per class.
    kept = {}
    capped = []
    for c in ordered:
        taken = kept.get(c["dispatch_class"], 0)
        if taken < 2:
            capped.append(c)
            kept[c["dispatch_class"]] = taken + 1
    return channels, capped, capped


def test_conditioning_canonicalization_discards_and_collapses():
    """Out-of-range damping is discarded (not clamped) and repeated sites collapse by MAXIMUM."""
    raw = json.loads(CONDITIONING.read_text())["sites"]
    damping = _canonical_damping()
    for row in raw:
        if int(row["damping"]) > 12 or int(row["damping"]) < 0:
            # a clamping implementation would have recorded the bound instead
            assert damping.get(int(row["site"])) != 12
    seen = {}
    for row in raw:
        s_, v = int(row["site"]), int(row["damping"])
        if 0 <= v <= 12:
            seen.setdefault(s_, []).append(v)
    for site, values in seen.items():
        if len(values) > 1:
            # MX-2253 reverses this: repeated sites collapse to the MINIMUM.
            assert damping[site] == min(values)
            assert damping[site] != max(values), (
                "the shipped conditioning file must make the two readings differ"
            )


def test_dispatch_admission_matches_independent_computation(result):
    """The dispatched set is exactly the routed channels whose conditioned flux clears the floor."""
    _, dispatched, _ = _dispatch_layer(result)
    assert result["dispatched_endpoints"] == sorted(c["endpoint"] for c in dispatched)
    assert result["dispatched_channel_count"] == len(dispatched)
    assert result["total_conditioned_flux"] == sum(c["conditioned_flux"] for c in dispatched)
    assert result["max_conditioned_flux"] == max((c["conditioned_flux"] for c in dispatched), default=0)


def test_damping_half_rounds_up_not_down(result):
    """The accumulated damping is halved with a CEILING; a floored halving gives a different set."""
    edges = _canonical_edges(json.loads(DATA.read_text())["edges"])
    damping = _canonical_damping()
    floored = []
    for seq in result["flux_paths"]:
        hops = len(seq) - 1
        cflux = sum(edges[seq[i]][seq[i + 1]] for i in range(hops))
        dsum = sum(damping.get(n, 0) for n in seq if n != SOURCE)
        cond = max(max(cflux - (dsum // 2), 0) - (hops * 3) // 2, 0)
        if cond >= DISPATCH_FLOOR:
            floored.append(seq[-1])
    # The shipped network is tuned so the two roundings genuinely disagree.
    assert sorted(floored) != result["dispatched_endpoints"]


def test_total_damping_covers_all_routed_channels(result):
    """total_damping sums damping over every routed channel, not only the dispatched ones."""
    channels, dispatched, _ = _dispatch_layer(result)
    assert result["total_damping"] == sum(c["damping_sum"] for c in channels)
    assert result["total_damping"] != sum(c["damping_sum"] for c in dispatched)


def test_class_counts_enumerate_all_three(result):
    """class_counts always carries all three class names in order, zero-filled."""
    assert list(result["class_counts"]) == list(CLASS_ORDER)
    _, dispatched, _ = _dispatch_layer(result)
    expected = {n: 0 for n in CLASS_ORDER}
    for c in dispatched:
        expected[c["dispatch_class"]] += 1
    assert result["class_counts"] == expected
    assert sum(result["class_counts"].values()) == result["dispatched_channel_count"]


def test_dispatch_order_follows_the_ordering_chain(result):
    """dispatch_order applies the full tie-break chain and is not merely ascending."""
    _, _, ordered = _dispatch_layer(result)
    assert result["dispatch_order"] == [c["endpoint"] for c in ordered]
    assert result["dispatch_order"] != sorted(result["dispatch_order"])
    assert sorted(result["dispatch_order"]) == result["dispatched_endpoints"]


def test_dispatch_checksum_consistent(result):
    """dispatch_checksum is the SHA-256 of the dispatch-row serialization."""
    _, _, ordered = _dispatch_layer(result)
    payload = "\n".join(
        f"{c['endpoint']}|{c['dispatch_class']}|{c['conditioned_flux']}|"
        f"{c['damped_flux']}|{c['damping_sum']}" for c in ordered)
    assert result["dispatch_checksum"] == hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_conditioning_path_is_fixed_not_relative_to_input(tmp_path):
    """--input selects the network only; the conditioning file is never relocated."""
    alt = FIX / "alt_network.json"
    staged = tmp_path / "network.json"
    staged.write_text(alt.read_text())
    # A decoy conditioning file beside the staged input must be ignored.
    (tmp_path / "site_conditioning.json").write_text(
        json.dumps({"sites": [{"site": n, "damping": 12} for n in range(1, 18)]}))
    got = _run(tmp_path / "run", input_path=staged)
    alt_expected = json.loads((FIX / "alt_expected.json").read_text())
    assert got == alt_expected


def test_mx_2257_owner_counts_only_its_own_intersection(result):
    """MX-2257: the owning routed channel adds |own_sites & candidate_sites|, no more.

    Three readings of the attribution rule are possible and the wrong two overstate
    the total. This recomputes the candidate set independently from the network and
    pins the governing reading, asserting the alternatives genuinely differ so the
    check cannot pass tautologically -- and so the rule cannot go dormant unnoticed.
    """
    net = json.loads(DATA.read_text())
    edges: dict[int, dict[int, int]] = {}
    for src, dst, w in net["edges"]:
        if src == dst or not 1 <= w <= 9:   # canonicalization drops these
            continue
        cur = edges.setdefault(src, {}).get(dst)
        if cur is None or w < cur:          # MX-2251: minimum weight wins
            edges[src][dst] = w

    paths: list[tuple[int, tuple[int, ...]]] = []

    def dfs(node, weight, nodes, depth):
        for target in sorted(edges.get(node, {})):
            if target in nodes:
                continue
            seq = nodes + (target,)
            paths.append((weight + edges[node][target], seq))
            if depth + 1 < HOP_BOUND:
                dfs(target, weight + edges[node][target], seq, depth + 1)

    dfs(SOURCE, 0, (SOURCE,), 0)

    best: dict[frozenset, tuple[int, tuple]] = {}
    for weight, seq in paths:
        nodes = frozenset(n for n in seq if n != SOURCE)
        if not nodes:
            continue
        cur = best.get(nodes)
        if cur is None or weight > cur[0] or (weight == cur[0] and seq < cur[1]):
            best[nodes] = (weight, seq)

    routed = [frozenset(n for n in seq if n != SOURCE) for seq in result["flux_paths"]]
    endpoints = [seq[-1] for seq in result["flux_paths"]]
    fluxes = [
        sum(edges[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))
        for seq in result["flux_paths"]
    ]
    candidates = [nodes for nodes in best if nodes not in routed]

    governing = every_claimant = owner_absorbs_all = 0
    multi_claimant = 0
    for cand in candidates:
        claimants = [i for i, rs in enumerate(routed) if rs & cand]
        if not claimants:
            continue
        if len(claimants) > 1:
            multi_claimant += 1
        owner = sorted(claimants, key=lambda i: (-fluxes[i], endpoints[i]))[0]
        governing += len(routed[owner] & cand)
        shared_any = set()
        for i in claimants:
            shared_any |= routed[i] & cand
            every_claimant += len(routed[i] & cand)
        owner_absorbs_all += len(shared_any)

    assert result["total_contention_overlap"] == governing
    assert multi_claimant > 0, "no candidate has multiple claimants -- MX-2257 is dormant"
    assert governing < owner_absorbs_all, "readings coincide -- test cannot discriminate"
    assert governing < every_claimant, "readings coincide -- test cannot discriminate"


POLICY_PATH = Path("/app/data/transport_policies.json")
POLICY_FIELDS = (
    "dispatch_floor", "primary_min", "primary_damping_max",
    "saturation_threshold", "throughput_cap",
)
BASELINE_POLICY = {
    "dispatch_floor": 5, "primary_min": 6, "primary_damping_max": 7,
    "saturation_threshold": 20, "throughput_cap": 60,
}


def _resolve_policy(hub, data):
    base = dict(BASELINE_POLICY)
    for k in POLICY_FIELDS:
        if k in data.get("default", {}):
            base[k] = int(data["default"][k])
    raw = data.get("hub_overrides", {}).get(str(hub))
    if not isinstance(raw, dict):
        return base
    merged = dict(base)
    for k in POLICY_FIELDS:
        if k in raw:
            merged[k] = int(raw[k])
    return merged


def test_policy_source_path_affects_output(tmp_path: Path):
    """MX-2261: thresholds come from the policy file, not from hardcoded constants."""
    original = POLICY_PATH.read_text(encoding="utf-8")
    try:
        baseline = _run(tmp_path / "base")
        bumped = json.loads(original)
        bumped["default"]["dispatch_floor"] = 99
        POLICY_PATH.write_text(json.dumps(bumped), encoding="utf-8")
        changed = _run(tmp_path / "changed")
        assert changed["dispatched_channel_count"] < baseline["dispatched_channel_count"]
        assert changed["policy_checksum"] != baseline["policy_checksum"]
    finally:
        POLICY_PATH.write_text(original, encoding="utf-8")


def test_sparse_hub_override_inherits_remaining_fields():
    """A hub override names some fields; every unlisted field is inherited."""
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sparse = [h for h, v in data["hub_overrides"].items() if len(v) < len(POLICY_FIELDS)]
    assert sparse, "no sparse override -- the inheritance rule is dormant"
    for hub in sparse:
        resolved = _resolve_policy(hub, data)
        assert set(resolved) == set(POLICY_FIELDS)
        for key in POLICY_FIELDS:
            if key not in data["hub_overrides"][hub]:
                expected = int(data["default"].get(key, BASELINE_POLICY[key]))
                assert resolved[key] == expected, f"{hub}.{key} did not inherit"


def test_policy_default_may_omit_fields_and_falls_back_to_baseline():
    """The file default is itself partial; omitted fields keep the shipped baseline."""
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    omitted = [k for k in POLICY_FIELDS if k not in data.get("default", {})]
    assert omitted, "file default names every field -- the baseline tier is dormant"
    for key in omitted:
        assert _resolve_policy("no-such-hub", data)[key] == BASELINE_POLICY[key]


def test_policy_checksum_consistent(result):
    """policy_checksum serializes the RESOLVED values, default then hubs ascending."""
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    base = _resolve_policy("no-such-hub", data)
    lines = ["default|" + "|".join(str(base[k]) for k in POLICY_FIELDS)]
    for hub in sorted(data.get("hub_overrides", {}), key=lambda h: int(h)):
        resolved = _resolve_policy(hub, data)
        lines.append(f"{hub}|" + "|".join(str(resolved[k]) for k in POLICY_FIELDS))
    expected = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    assert result["policy_checksum"] == expected
