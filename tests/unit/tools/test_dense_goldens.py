"""Tests for the dense per-tick golden traces (Program 13 item 2).

Constitution III.12 (Behavioral Contracts, Amendment Q) corollary (c) names
dense full-trace goldens as the fix for the audited sparsity gap: the
sampled checkpoints in ``tests/baselines/<scenario>.json`` pin ~9 variables
at every 10th tick (~54 numbers for a 52-tick scenario) — a
plausible-but-wrong engine could pass. ``tests/baselines/dense/<scenario>.csv``
pins every tick instead.

This module verifies two things:

1. The five dense goldens actually exist, one per ``SCENARIOS`` entry, with
   the documented column shape (a ``tick`` first column plus per-entity and
   per-relationship columns — see ``docs/reference/determinism-contract.rst``
   "Dense Golden Traces").
2. The comparison path is not a rubber stamp: a synthetic one-cell mutation
   on a *copy* of a golden (never the committed golden itself) is caught,
   loudly, naming the divergent tick and column.
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import pytest

# Mirror the import path used by tools/*.py and its existing unit tests
# (see tests/unit/tools/test_shared_signature.py).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

BASELINE_DIR = Path(__file__).resolve().parents[3] / "tests" / "baselines"
DENSE_DIR = BASELINE_DIR / "dense"


@pytest.mark.parametrize("scenario_name", sorted(rt.SCENARIOS))
def test_dense_golden_exists_for_every_scenario(scenario_name: str) -> None:
    """Every scenario in SCENARIOS has a committed dense CSV golden."""
    golden_path = DENSE_DIR / f"{scenario_name}.csv"
    assert golden_path.exists(), (
        f"missing dense golden for {scenario_name!r} at {golden_path} — "
        "run `mise run qa:regression-generate-dense`"
    )


@pytest.mark.parametrize("scenario_name", sorted(rt.SCENARIOS))
def test_dense_golden_has_documented_column_shape(scenario_name: str) -> None:
    """The header starts with 'tick' and every row has the same width as the header."""
    golden_path = DENSE_DIR / f"{scenario_name}.csv"
    with golden_path.open(newline="") as f:
        rows = list(csv.reader(f))

    assert rows, f"{golden_path} is empty"
    header = rows[0]
    assert header[0] == "tick"
    assert "economy_imperial_rent_pool" in header
    # At least one per-entity wealth column and one per-edge tension column,
    # per the column contract documented in determinism-contract.rst.
    assert any(col.endswith("_wealth") for col in header)
    assert any(col.startswith("edge_") and col.endswith("_tension") for col in header)

    for row in rows[1:]:
        assert len(row) == len(header), (
            f"{golden_path}: row width {len(row)} != header width {len(header)}"
        )

    # tick column is 0..N with no gaps (every tick covered, not sampled).
    ticks = [int(row[0]) for row in rows[1:]]
    assert ticks == list(range(len(ticks))), f"{golden_path}: dense trace is not gap-free"


@pytest.mark.parametrize("scenario_name", sorted(rt.SCENARIOS))
def test_dense_trace_regeneration_matches_committed_golden(scenario_name: str) -> None:
    """Re-running the scenario reproduces the committed golden byte-for-byte."""
    expected_max_ticks = rt.load_baseline(BASELINE_DIR / f"{scenario_name}.json").max_ticks
    _baseline, dense = rt.run_scenario_dense(scenario_name, max_ticks=expected_max_ticks)

    passed, diagnostic = rt.compare_dense_trace(dense, BASELINE_DIR)

    assert passed, f"{scenario_name}: dense golden drifted — {diagnostic}"


def test_compare_dense_trace_catches_a_synthetic_one_value_mutation(tmp_path: Path) -> None:
    """A single mutated cell in a *copy* of a golden is caught, loudly.

    RED-phase gate for Program 13 item 2: dense comparison must not be a
    rubber stamp. Copies the real committed golden into a scratch
    ``tmp_path`` baseline dir, corrupts exactly one cell, and asserts
    ``compare_dense_trace`` reports the mutation with the exact
    tick+column it touched — never a silent pass (Constitution III.11).
    """
    scenario_name = "two_node"
    scratch_dense_dir = tmp_path / "dense"
    scratch_dense_dir.mkdir()
    committed_golden = DENSE_DIR / f"{scenario_name}.csv"
    scratch_golden = scratch_dense_dir / f"{scenario_name}.csv"
    shutil.copy(committed_golden, scratch_golden)

    with scratch_golden.open(newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    mutated_tick = 5
    mutated_column = "C001_wealth"
    col_idx = header.index(mutated_column)
    original_value = rows[mutated_tick + 1][col_idx]  # +1 for the header row
    rows[mutated_tick + 1][col_idx] = "999999.0"
    assert rows[mutated_tick + 1][col_idx] != original_value

    with scratch_golden.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)

    expected_max_ticks = rt.load_baseline(BASELINE_DIR / f"{scenario_name}.json").max_ticks
    _baseline, dense = rt.run_scenario_dense(scenario_name, max_ticks=expected_max_ticks)

    passed, diagnostic = rt.compare_dense_trace(dense, tmp_path)

    assert not passed, "mutation was not detected — dense compare is a rubber stamp"
    assert diagnostic is not None
    assert f"tick {mutated_tick}" in diagnostic
    assert mutated_column in diagnostic

    # And the real committed golden (never touched — only the tmp_path copy
    # was mutated) still compares clean.
    passed_real, _ = rt.compare_dense_trace(dense, BASELINE_DIR)
    assert passed_real, "the committed golden must remain unaffected by this mutation test"
