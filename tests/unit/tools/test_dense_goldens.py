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

_PENDING_CEREMONY_SKIP_REASON = "PENDING CEREMONY: golden minted by the Task 11 ceremony"


def _skip_if_pending_ceremony(scenario_name: str) -> None:
    """Skip loudly for a scenario whose baseline hasn't been minted yet.

    Keyed off the explicit ``rt.PENDING_CEREMONY`` allowlist, never off
    golden-file absence: a scenario NOT in the allowlist whose golden is
    missing (e.g. one of the five already-minted scenarios, accidentally
    deleted) must still FAIL loudly, not silently skip — that's exactly the
    failure mode a file-absence-keyed skip would mask. Task 11's ceremony
    mints ``single_county``'s golden and removes it from
    ``PENDING_CEREMONY`` in the same commit, which turns this skip back into
    a real assertion automatically.
    """
    if scenario_name in rt.PENDING_CEREMONY:
        pytest.skip(_PENDING_CEREMONY_SKIP_REASON)


@pytest.mark.parametrize("scenario_name", sorted(rt.SCENARIOS))
def test_dense_golden_exists_for_every_scenario(scenario_name: str) -> None:
    """Every scenario in SCENARIOS has a committed dense CSV golden."""
    _skip_if_pending_ceremony(scenario_name)
    golden_path = DENSE_DIR / f"{scenario_name}.csv"
    assert golden_path.exists(), (
        f"missing dense golden for {scenario_name!r} at {golden_path} — "
        "run `mise run qa:regression-generate-dense`"
    )


@pytest.mark.parametrize("scenario_name", sorted(rt.SCENARIOS))
def test_dense_golden_has_documented_column_shape(scenario_name: str) -> None:
    """The header starts with 'tick' and every row has the same width as the header."""
    _skip_if_pending_ceremony(scenario_name)
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
    _skip_if_pending_ceremony(scenario_name)
    expected_max_ticks = rt.load_baseline(BASELINE_DIR / f"{scenario_name}.json").max_ticks
    _baseline, dense = rt.run_scenario_dense(scenario_name, max_ticks=expected_max_ticks)

    passed, report = rt.compare_dense_trace(dense, BASELINE_DIR)

    assert passed, f"{scenario_name}: dense golden drifted — {report}"


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

    passed, report = rt.compare_dense_trace(dense, tmp_path)

    assert not passed, "mutation was not detected — dense compare is a rubber stamp"
    assert report is not None
    assert report.tick == mutated_tick
    assert report.column == mutated_column

    # And the real committed golden (never touched — only the tmp_path copy
    # was mutated) still compares clean.
    passed_real, _ = rt.compare_dense_trace(dense, BASELINE_DIR)
    assert passed_real, "the committed golden must remain unaffected by this mutation test"


def test_appended_trailing_column_produces_a_loud_header_report(tmp_path: Path) -> None:
    """A golden missing a trailing column (schema widening) fails loudly, not silently.

    CRITICAL-1 regression: ``compare_dense_trace`` used to parse the fresh
    CSV's header into a throwaway local and call ``attribute_divergence``
    with only the golden's (shorter) header. Walking the fresh rows through
    that shorter header meant every *shared* column still compared equal
    (by construction here — the golden is the real trace with its last
    column dropped, values otherwise identical), so ``attribute_divergence``
    returned ``None`` even though the byte blobs already differ — a dense
    FAIL that printed nothing and wrote no JSON entry
    (``compare_all_baselines``'s ``if not dense_ok and dense_report is not
    None`` guard silently no-ops on ``None``). This is exactly the shape
    Task 9's dense-header widening (E3) would trigger. The fix compares
    ``expected_header``/``actual_header`` before any cell walk and
    short-circuits to a ``column="<header>"`` report.
    """
    scenario_name = "two_node"
    expected_max_ticks = rt.load_baseline(BASELINE_DIR / f"{scenario_name}.json").max_ticks
    _baseline, dense = rt.run_scenario_dense(scenario_name, max_ticks=expected_max_ticks)

    golden_trace = rt.DenseTrace(
        scenario=scenario_name,
        header=dense.header[:-1],
        rows=[row[:-1] for row in dense.rows],
    )
    scratch_dense_dir = tmp_path / "dense"
    scratch_dense_dir.mkdir()
    (scratch_dense_dir / f"{scenario_name}.csv").write_bytes(
        rt.dense_trace_to_csv_bytes(golden_trace)
    )

    passed, report = rt.compare_dense_trace(dense, tmp_path)

    assert not passed, "a widened dense header must fail the gate"
    assert report is not None, (
        "silent FAIL reproduced: a schema-widened header with byte-identical "
        "shared cells must still produce a loud attribution, never None"
    )
    assert report.column == "<header>"
    assert report.channel == "<column set changed>"
    assert report.tick == 0
    assert report.magnitude is None
    assert report.last_agreeing_tick is None
    assert report.candidate_systems == ()
    assert dense.header[-1] not in report.expected
    assert dense.header[-1] in report.actual


def test_inserted_mid_header_column_attributes_to_header_not_a_shifted_cell(
    tmp_path: Path,
) -> None:
    """A column inserted mid-header is attributed to ``<header>``, not a shifted cell.

    CRITICAL-1 regression: without a header check ahead of the cell walk, an
    inserted column shifts every later index, and the old
    golden-header-only walk would misattribute the resulting mismatch to
    whichever unrelated, otherwise-unchanged column happened to land at the
    first shifted index — at tick/row 0, actively misleading whoever reads
    the attribution.
    """
    scenario_name = "two_node"
    expected_max_ticks = rt.load_baseline(BASELINE_DIR / f"{scenario_name}.json").max_ticks
    _baseline, dense = rt.run_scenario_dense(scenario_name, max_ticks=expected_max_ticks)

    insert_at = 2  # mid-header: between the first two economy_* columns
    golden_trace = rt.DenseTrace(
        scenario=scenario_name,
        header=dense.header[:insert_at] + ["inserted_col"] + dense.header[insert_at:],
        rows=[row[:insert_at] + ["0.0"] + row[insert_at:] for row in dense.rows],
    )
    scratch_dense_dir = tmp_path / "dense"
    scratch_dense_dir.mkdir()
    (scratch_dense_dir / f"{scenario_name}.csv").write_bytes(
        rt.dense_trace_to_csv_bytes(golden_trace)
    )

    passed, report = rt.compare_dense_trace(dense, tmp_path)

    assert not passed
    assert report is not None
    assert report.column == "<header>", (
        f"must attribute the header-shape change itself, not a shifted cell "
        f"(got column={report.column!r})"
    )
    assert report.channel == "<column set changed>"
    assert "inserted_col" in report.expected
    assert "inserted_col" not in report.actual
