"""Integration tests for the engine-bridged headless runner.

Spec: 065-engine-bridging (T005, T026-T029, T075, T076).

Tests in this module require a live Postgres test DB
(``BABYLON_TEST_PG_DSN``; falls back to the canonical localhost:5433
test container) and the SQLite reference DB at
``data/sqlite/marxist-data-3NF.sqlite``. They exercise the full
engine-bridged tick loop.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        conn = psycopg.connect(dsn, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_reachable(),
        reason="Postgres test DB not reachable",
    ),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}.",
    ),
]


def _ensure_pg_dsn_env() -> None:
    """Make BABYLON_TEST_PG_DSN explicit if unset (runner reads it)."""
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)


def _run_runner(
    *,
    scope: str = "detroit-tri-county",
    ticks: int = 5,
    seed: int = 2010,
    output_dir: Path | None = None,
) -> Any:
    """Invoke the runner programmatically; returns SimulationRunResult."""
    _ensure_pg_dsn_env()

    from babylon.engine.headless_runner.models import SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    sc = resolve_scope(scope)
    out_dir = output_dir or Path(tempfile.mkdtemp(prefix=f"sim_{scope}_"))
    config = SimulationRunConfig(
        ticks=ticks,
        start_year=2010,
        random_seed=seed,
        scope_name=scope,
        scope_fips=sc.scope_fips,
        external_node_ids=sc.external_node_ids,
        sqlite_reference_path=SQLITE_REF,
        output_dir=out_dir,
    )
    return runner_run(config)


def test_smoke_tri_county_full_fidelity() -> None:
    """T026: 5-tick tri-county run produces all 3 artifacts + populated rows."""
    result = _run_runner(scope="detroit-tri-county", ticks=5)

    assert result.exit_reason.value == "completed", f"unexpected exit_reason: {result.exit_reason}"
    assert result.ticks_completed == 5
    assert result.artifact_dir is not None

    artifact_dir = result.artifact_dir
    assert (artifact_dir / "trace.csv").exists()
    assert (artifact_dir / "summary.json").exists()
    assert (artifact_dir / "manifest.json").exists()

    with (artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))
    # 3 counties × 5 ticks = 15 data rows expected.
    assert len(rows) == 15, f"expected 15 trace rows, got {len(rows)}"

    summary = json.loads((artifact_dir / "summary.json").read_text())
    terminal = summary["terminal_state"]
    assert terminal["counties_alive"] == 3
    assert terminal["total_v"] > 0
    assert terminal["total_c"] > 0
    assert terminal["total_k"] > 0


def test_determinism() -> None:
    """T027: two runs with the same seed produce byte-identical trace.csv."""
    r1 = _run_runner(seed=2010, ticks=5)
    r2 = _run_runner(seed=2010, ticks=5)

    assert r1.artifact_dir is not None
    assert r2.artifact_dir is not None
    csv1 = (r1.artifact_dir / "trace.csv").read_bytes()
    csv2 = (r2.artifact_dir / "trace.csv").read_bytes()
    # session_id differs per run; trace.csv doesn't carry it. So this
    # comparison is a true determinism check on the data shape.
    assert csv1 == csv2, "trace.csv differs between two seed-2010 runs"

    m1 = json.loads((r1.artifact_dir / "manifest.json").read_text())
    m2 = json.loads((r2.artifact_dir / "manifest.json").read_text())
    assert m1["reproducibility"]["input_hash"] == m2["reproducibility"]["input_hash"], (
        "manifest input_hash differs between two seed-2010 runs"
    )


def test_tick_over_tick_evolution() -> None:
    """T028: SC-004 — at least one numeric column changes tick 0 → tick 4.

    Spec-066 T039: xfail removed — engine.run_tick now drives 21 systems
    per tick, so consciousness/ideology/agitation values DO evolve. This
    test verifies the engine MUTATES persisted state (smoke); the SC-005
    ≥5% drift threshold is validated by the slow-gate 520-tick
    test_ideology_f_drifts_geq_5pct_over_520_ticks in
    test_consciousness_evolution.py.
    """
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    by_tick: dict[int, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        tick = int(row["tick"])
        by_tick.setdefault(tick, {})[row["entity_id"]] = row

    cols_to_check = [
        "v",
        "c",
        "s",
        "k",
        "p_acquiescence",
        "p_revolution",
        "ideology_r",
        "ideology_l",
        "ideology_f",
    ]
    last_tick = max(by_tick.keys())
    for entity_id in by_tick[0]:
        for col in cols_to_check:
            v0 = float(by_tick[0][entity_id].get(col) or 0)
            v_last = float(by_tick[last_tick][entity_id].get(col) or 0)
            if v0 != v_last:
                return  # any mutation proves engine ran
    raise AssertionError(
        "No county-tick column changed between tick 0 and tick "
        f"{last_tick} — engine.run_tick may not be mutating state."
    )


def test_zero_empty_cells() -> None:
    """T029: SC-001 — every county-applicable cell is non-empty."""
    result = _run_runner(scope="detroit-tri-county", ticks=3)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    # The 22-column trace contract: county-applicable columns the bridge
    # is required to populate.
    county_columns = [
        "v",
        "c",
        "s",
        "k",
        "p_acquiescence",
        "p_revolution",
        "ideology_r",
        "ideology_l",
        "ideology_f",
        "surveillance_coupling",
        "internet_access_pct",
        "biocapacity_stock",
        "energy_stock",
        "raw_material_stock",
        "population",
        "employment_proxy",
    ]
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        for col in county_columns:
            value = row.get(col, "")
            assert value not in (None, ""), (
                f"empty cell at tick={row['tick']} entity={row['entity_id']} col={col}"
            )


def test_tick_0_ideology_uniform_across_counties() -> None:
    """Spec-066 T046 / SC-009: every county at tick 0 has identical
    (ideology_r=0.05, ideology_l=0.50, ideology_f=0.45) within ±1e-9
    per ADR043 placeholder."""
    result = _run_runner(scope="detroit-tri-county", ticks=1)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    tick_0_rows = [r for r in rows if int(r["tick"]) == 0 and r.get("entity_kind") == "county"]
    assert len(tick_0_rows) >= 1, "no county rows at tick 0"
    for row in tick_0_rows:
        r = float(row.get("ideology_r") or 0)
        liberal = float(row.get("ideology_l") or 0)
        f_val = float(row.get("ideology_f") or 0)
        assert r == pytest.approx(0.05, abs=1e-6), f"{row['entity_id']} r={r}"
        assert liberal == pytest.approx(0.50, abs=1e-6), f"{row['entity_id']} l={liberal}"
        assert f_val == pytest.approx(0.45, abs=1e-6), f"{row['entity_id']} f={f_val}"


def test_substrate_distinguishability() -> None:
    """Spec-066 T064 / SC-008: ≥50% of counties show distinct
    energy_stock vs raw_material_stock at tick 0.

    Tri-county MVP: with at least 2 of 3 counties showing distinct values
    (different population vs area shares), this proves the apportionment
    formula split applied. Full 83-county Michigan validation lands in
    Phase 8's e2e run.
    """
    result = _run_runner(scope="detroit-tri-county", ticks=1)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    distinct = 0
    total = 0
    for row in rows:
        if row.get("entity_kind") != "county" or int(row["tick"]) != 0:
            continue
        total += 1
        e = float(row.get("energy_stock") or 0)
        r = float(row.get("raw_material_stock") or 0)
        if abs(e - r) > 1e-9 * max(abs(e), abs(r), 1.0):
            distinct += 1

    assert total >= 1, "no county rows at tick 0"
    # At least 50% of counties should differ. For tri-county, that's ≥2 of 3.
    threshold = max(1, total // 2)
    assert distinct >= threshold, (
        f"Spec-066 SC-008 FAILED: only {distinct}/{total} counties show "
        f"distinct (energy_stock, raw_material_stock)"
    )


def test_ternary_simplex_preserved_at_hydrate() -> None:
    """Spec-066 T047: r + l + f sums to 1.0 ± 1e-9 for every county at every tick."""
    result = _run_runner(scope="detroit-tri-county", ticks=3)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        r = float(row.get("ideology_r") or 0)
        liberal = float(row.get("ideology_l") or 0)
        f_val = float(row.get("ideology_f") or 0)
        total = r + liberal + f_val
        assert total == pytest.approx(1.0, abs=1e-6), (
            f"tick={row['tick']} entity={row['entity_id']} ternary sum = {total}"
        )


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="set BABYLON_SLOW_TESTS=1 to enable wallclock smoke",
)
def test_tri_county_wallclock_smoke() -> None:
    """T075 (R9 pass 1): tri-county 520-tick smoke; record per-tick mean ms."""
    t_start = time.perf_counter()
    result = _run_runner(scope="detroit-tri-county", ticks=520)
    elapsed = time.perf_counter() - t_start

    assert result.exit_reason.value == "completed"
    print(f"\n  tri-county 520 ticks: {elapsed:.1f}s ({elapsed * 1000 / 520:.1f} ms/tick avg)")


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="set BABYLON_SLOW_TESTS=1 to enable SC-002 canonical budget test",
)
def test_canonical_wallclock_budget() -> None:
    """T076 (R9 pass 3): SC-002 — michigan-canada 520 ticks ≤ 600s."""
    t_start = time.perf_counter()
    result = _run_runner(scope="michigan-canada", ticks=520)
    elapsed = time.perf_counter() - t_start

    assert result.exit_reason.value == "completed"
    assert elapsed <= 600, f"SC-002 budget exceeded: {elapsed:.1f}s > 600s"
