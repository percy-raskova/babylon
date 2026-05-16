"""Integration tests for engine-driven consciousness evolution (spec-066 US2).

Spec: 066-marx-coherence-fixes (T028-T031).

These tests verify that wiring `engine.run_tick(...)` into the bridged
runner produces measurable ideology drift across the 520-tick Michigan-
Canada canonical run. Slow-gate only (BABYLON_SLOW_TESTS=1 required).

Verifies:
- SC-005: at least one county shows >=5% relative drift on ideology_f
- SC-006: Wayne (26163) vs Keweenaw (26083) Pearson < 0.95
- SC-010: summary.performance.per_system_ms has 21 non-zero entries
- SC-012: expected event families fire (BIFURCATION_THRESHOLD, etc.)

Requires Postgres test DB AND ``BABYLON_SLOW_TESTS=1``.
"""

from __future__ import annotations

import os
from pathlib import Path

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
    pytest.mark.skipif(
        os.environ.get("BABYLON_SLOW_TESTS") != "1",
        reason="520-tick canonical run is slow-gate only; set BABYLON_SLOW_TESTS=1",
    ),
]


def test_ideology_f_drifts_geq_5pct_over_520_ticks() -> None:
    """T028 / SC-005: at least one county shows >=5% relative drift on ideology_f
    between tick 0 and tick 519."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T032-T038 wire engine + edges)")


def test_wayne_keweenaw_pearson_lt_0_95() -> None:
    """T029 / SC-006: Pearson correlation of ideology_f time-series between
    Wayne (26163) and Keweenaw (26083) is < 0.95 (counties diverge)."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T032-T038 wire engine + edges)")


def test_per_system_ms_has_21_nonzero_entries() -> None:
    """T030 / SC-010: summary.performance.per_system_ms has exactly 21 keys,
    each with a strictly positive value (every engine system actually ran)."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T034-T036 invoke engine)")


def test_expected_event_families_fire() -> None:
    """T031 / SC-012: summary.events contains at least one BIFURCATION_THRESHOLD
    OR CONSCIOUSNESS_SHIFT event AND at least one EXCESSIVE_FORCE OR
    FASCIST_REVANCHISM OR FASCIST_CONVERGENCE event."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T032-T038 wire engine + edges)")
