"""Verifier for the Meridian-2 directed lattice-relaxation simulation.

The agent's /app/stabilize.py is run against the shipped initial load and against
a held-out alternate load. Observables are checked against exact fixtures and
against physical invariants (steady state, load conservation, independent
checksum).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path("/app/stabilize.py")
DATA = Path("/app/data/drops.json")
TEST_DIR = Path(os.environ.get("TEST_DIR", "/tests"))
FIX = TEST_DIR / "fixtures"
EXPECTED = json.loads((FIX / "expected_result.json").read_text())


def _run(tmp: Path, input_path: Path = DATA) -> dict:
    out = tmp / "out"
    subprocess.run(
        [sys.executable, str(APP), "--input", str(input_path), "--output-dir", str(out)],
        check=True, capture_output=True, text=True,
    )
    return json.loads((out / "result.json").read_text())


@pytest.fixture(scope="module")
def result(tmp_path_factory) -> dict:
    """Run the agent's simulation once on the shipped initial load."""
    assert APP.exists(), "stabilize.py is missing"
    return _run(tmp_path_factory.mktemp("primary"))


def test_result_has_required_keys(result):
    """result.json carries exactly the contracted key set."""
    assert set(result) == {"rows", "cols", "grid", "total_firings",
                           "row_firings", "spill", "grid_checksum"}


def test_grid_matches_fixture(result):
    """The steady-state lattice matches the reference fixture exactly."""
    assert result["grid"] == EXPECTED["grid"]


def test_scalar_fields_match_fixture(result):
    """total_firings, row_firings and spill match the reference fixture."""
    assert result["total_firings"] == EXPECTED["total_firings"]
    assert result["row_firings"] == EXPECTED["row_firings"]
    assert result["spill"] == EXPECTED["spill"]


def test_checksum_matches_fixture(result):
    """grid_checksum matches the reference fixture."""
    assert result["grid_checksum"] == EXPECTED["grid_checksum"]


def test_grid_is_stabilized(result):
    """Every steady-state site holds a value in 0..3."""
    assert all(0 <= v <= 3 for row in result["grid"] for v in row)


def test_checksum_is_consistent_with_grid(result):
    """grid_checksum is the SHA-256 of the spec's grid serialization."""
    serialized = "\n".join(" ".join(str(v) for v in row) for row in result["grid"])
    assert result["grid_checksum"] == hashlib.sha256(serialized.encode()).hexdigest()


def test_chip_conservation(result):
    """Initial load equals the load left on the lattice plus the spill."""
    data = json.loads(DATA.read_text())
    initial = sum(n for _, _, n in data["drops"])
    on_grid = sum(v for row in result["grid"] for v in row)
    assert initial == on_grid + result["spill"]


def test_row_firings_sum_to_total(result):
    """row_firings sums to total_firings."""
    assert sum(result["row_firings"]) == result["total_firings"]


def test_is_idempotent(result, tmp_path):
    """A second run on the same input reproduces the result byte-for-byte."""
    assert _run(tmp_path) == result


def test_generalizes_to_alternate_input(tmp_path):
    """The simulation produces the reference output for a held-out load."""
    alt_expected = json.loads((FIX / "alt_expected.json").read_text())
    got = _run(tmp_path, input_path=FIX / "alt_drops.json")
    assert got == alt_expected


def test_source_does_not_reference_verifier_trees():
    """The stabilizer does not read or import verifier artifacts."""
    src = APP.read_text()
    for token in ("/tests", "/solution", "expected_result.json", "alt_expected.json"):
        assert token not in src
