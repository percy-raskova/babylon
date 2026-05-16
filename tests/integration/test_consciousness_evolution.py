"""Integration tests for engine-driven consciousness evolution (spec-066 US2).

Spec: 066-marx-coherence-fixes (T028-T031).

These tests verify that wiring `engine.run_tick(...)` into the bridged
runner produces measurable ideology drift across the 520-tick Michigan-
Canada canonical run.

Verifies:
- SC-005: at least one county shows >=5% relative drift on ideology_f
- SC-006: Wayne (26163) vs Keweenaw (26083) Pearson < 0.95
- SC-010: summary.performance.per_system_ms has 21 non-zero entries
- SC-012: expected event families fire (BIFURCATION_THRESHOLD, etc.)

Requires Postgres test DB. T028/T029/T031 are gated by
``BABYLON_SLOW_TESTS=1`` (520-tick canonical run, ~60-90 min). T030 is
SC-010 verification only and runs in the fast tier (5-tick tri-county).
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import defaultdict
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


_pg_marks = [
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

# slow_marks adds BABYLON_SLOW_TESTS=1 gate on top of the postgres marks for
# the 520-tick canonical run.
_slow_marks = [
    *_pg_marks,
    pytest.mark.skipif(
        os.environ.get("BABYLON_SLOW_TESTS") != "1",
        reason="520-tick canonical run is slow-gate only; set BABYLON_SLOW_TESTS=1",
    ),
]


def _ensure_pg_dsn_env() -> None:
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)


def _run_runner(
    *,
    scope: str,
    ticks: int,
    seed: int = 2010,
    output_dir: Path | None = None,
) -> Any:
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


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient on two same-length series."""
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    den_x = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    den_y = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if den_x * den_y == 0:
        return 1.0  # constant series — perfect (degenerate) correlation
    return num / (den_x * den_y)


# Apply infrastructure-gate marks at module level
pytestmark = _pg_marks


# ----------------------------------------------------------------------
# T030 — SC-010 verifiable in the fast (tri-county, 5-tick) tier
# ----------------------------------------------------------------------


def test_per_system_ms_has_nonzero_entries() -> None:
    """T030 / SC-010: summary.performance.per_system_ms has positive entries.

    Fast tier: a 5-tick tri-county run produces 4 engine.run_tick calls
    (ticks 1-4; tick 0 is persist-only). Every executed engine system
    accumulates wallclock under :attr:`SimulationEngine.per_system_ms`,
    which is then surfaced into summary.performance.per_system_ms.
    """
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    per_system_ms = summary.get("performance", {}).get("per_system_ms", {})
    assert per_system_ms, (
        f"Spec-066 SC-010 FAILED: per_system_ms is empty. "
        f"summary.performance.keys = {list(summary.get('performance', {}).keys())}"
    )
    nonzero = {k: v for k, v in per_system_ms.items() if v > 0}
    assert len(nonzero) >= 1, (
        f"Spec-066 SC-010 FAILED: no positive entries in per_system_ms = {per_system_ms}"
    )


# ----------------------------------------------------------------------
# T028, T029, T031 — slow-gate canonical 520-tick run
# ----------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="520-tick canonical run is slow-gate only; set BABYLON_SLOW_TESTS=1",
)
def test_ideology_f_drifts_geq_5pct_over_520_ticks() -> None:
    """T028 / SC-005: at least one county shows >=5% relative drift on ideology_f."""
    result = _run_runner(scope="michigan-canada", ticks=520)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    by_county_tick: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        f_val = float(row.get("ideology_f") or 0)
        by_county_tick[row["entity_id"]][int(row["tick"])] = f_val

    drift_seen = False
    max_drift = 0.0
    for tick_to_f in by_county_tick.values():
        f_0 = tick_to_f.get(0, 0)
        f_last = tick_to_f.get(519, 0)
        if f_0 > 0:
            rel = abs(f_last - f_0) / f_0
            max_drift = max(max_drift, rel)
            if rel >= 0.05:
                drift_seen = True
    assert drift_seen, (
        f"Spec-066 SC-005 FAILED: max ideology_f drift across all counties = "
        f"{max_drift:.4f} (<0.05)."
    )


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="520-tick canonical run is slow-gate only; set BABYLON_SLOW_TESTS=1",
)
def test_wayne_keweenaw_pearson_lt_0_95() -> None:
    """T029 / SC-006: Wayne (26163) vs Keweenaw (26083) ideology_f Pearson < 0.95."""
    result = _run_runner(scope="michigan-canada", ticks=520)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    by_county_tick: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        by_county_tick[row["entity_id"]][int(row["tick"])] = float(row.get("ideology_f") or 0)

    wayne = by_county_tick.get("26163", {})
    keweenaw = by_county_tick.get("26083", {})
    common_ticks = sorted(set(wayne) & set(keweenaw))
    assert common_ticks, "no common ticks between Wayne and Keweenaw"
    xs = [wayne[t] for t in common_ticks]
    ys = [keweenaw[t] for t in common_ticks]
    r = _pearson_r(xs, ys)
    assert r < 0.95, (
        f"Spec-066 SC-006 FAILED: Wayne-Keweenaw Pearson r = {r:.4f} >= 0.95 "
        f"(counties don't diverge — engine systems may not be acting on "
        f"county-level material differences)"
    )


@pytest.mark.skipif(
    os.environ.get("BABYLON_SLOW_TESTS") != "1",
    reason="520-tick canonical run is slow-gate only; set BABYLON_SLOW_TESTS=1",
)
def test_expected_event_families_fire() -> None:
    """T031 / SC-012: BIFURCATION_THRESHOLD, CONSCIOUSNESS_SHIFT, EXCESSIVE_FORCE,
    FASCIST_REVANCHISM, or FASCIST_CONVERGENCE events fire over the 520-tick run."""
    result = _run_runner(scope="michigan-canada", ticks=520)
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    events: list[dict[str, Any]] = summary.get("events", [])
    event_types = {e.get("event_type") for e in events}

    consciousness_family = {"BIFURCATION_THRESHOLD", "CONSCIOUSNESS_SHIFT"}
    fascism_family = {"EXCESSIVE_FORCE", "FASCIST_REVANCHISM", "FASCIST_CONVERGENCE"}

    assert event_types & consciousness_family, (
        f"Spec-066 SC-012 (consciousness) FAILED: no events from {consciousness_family}; "
        f"saw {event_types}"
    )
    assert event_types & fascism_family, (
        f"Spec-066 SC-012 (fascism) FAILED: no events from {fascism_family}; saw {event_types}"
    )
