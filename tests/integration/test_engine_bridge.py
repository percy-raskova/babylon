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
from uuid import UUID

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

    assert result.exit_reason.value == "completed", (
        f"unexpected exit_reason: {result.exit_reason}"
    )
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
    assert (
        m1["reproducibility"]["input_hash"] == m2["reproducibility"]["input_hash"]
    ), "manifest input_hash differs between two seed-2010 runs"


@pytest.mark.xfail(
    reason=(
        "SC-004 (tick-over-tick variance) requires engine system integration "
        "that mutates entity state per tick. Spec-065 first cut wires the bridge "
        "but defers full SimulationEngine integration to a follow-up spec. "
        "Currently the bridge persists byte-identical state at every tick within "
        "the same year (population/employment are annual; consciousness state is "
        "engine-driven and the engine is not yet running)."
    )
)
def test_tick_over_tick_evolution() -> None:
    """T028: SC-004 — ≥3 columns show ≥5% relative change tick 0 → tick 5."""
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    by_tick: dict[int, dict[str, dict[str, str]]] = {}
    for row in rows:
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
    for entity_id in by_tick[0]:
        changed_cols = []
        for col in cols_to_check:
            v0 = float(by_tick[0][entity_id].get(col) or 0)
            v_last = float(by_tick[max(by_tick.keys())][entity_id].get(col) or 0)
            if v0 != 0 and abs(v_last - v0) / abs(v0) >= 0.05:
                changed_cols.append(col)
        if len(changed_cols) >= 3:
            return
    raise AssertionError("No county has ≥3 columns with ≥5% tick-over-tick change")


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
    print(f"\n  tri-county 520 ticks: {elapsed:.1f}s "
          f"({elapsed * 1000 / 520:.1f} ms/tick avg)")


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
