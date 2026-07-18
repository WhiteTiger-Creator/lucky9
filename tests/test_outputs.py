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
        if t not in edges.get(s, {}) or w > edges[s][t]:
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
                           "residual_flux", "edge_checksum", "flux_checksum"}


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
        f"{result['flux_node_count']}|{result['residual_flux']}|{paths}"
    )
    assert result["flux_checksum"] == hashlib.sha256(payload.encode()).hexdigest()


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
