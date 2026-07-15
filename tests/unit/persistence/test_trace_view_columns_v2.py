"""Spec-065 T019: trace view schema parity.

Asserts that ``view_runtime_trace_emission`` (recreated by spec-065
migration 0023) exposes the column set declared in the spec-064
``trace_csv_schema.yaml`` contract — including the previously-NULL
columns that now flow from the new spec-065 subsystem tables
(consciousness, demographics, employment).
"""

from __future__ import annotations

import os

import pytest

PG_DSN = os.environ.get(
    "BABYLON_TEST_PG_DSN",
    "dbname=babylon_test host=localhost port=5433 user=test password=test",
)

# Columns the view MUST expose. Order matches the spec-064
# trace_csv_schema.yaml; spec-065 sources several from new tables
# but column NAMES are unchanged.
EXPECTED_COLUMNS = [
    "session_id",
    "tick",
    "entity_id",
    "entity_kind",
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
    "profit_rate",
    "exploitation_rate",
    "population",
    "employment_proxy",
]


@pytest.fixture(scope="module")
def pool():
    try:
        from psycopg import OperationalError
        from psycopg_pool import ConnectionPool
    except ImportError:
        pytest.skip("psycopg not available")
    try:
        p = ConnectionPool(conninfo=PG_DSN, min_size=1, max_size=2, open=True)
        with p.connection() as c:
            c.execute("SELECT 1")
    except (OperationalError, OSError):
        pytest.skip("Postgres not reachable")
    yield p
    p.close()


def _apply_spec_065_migrations(pool) -> None:
    """Idempotently apply migrations 0020-0023 against the test DB.

    Self-healing (task #77): delegates to the shared
    ``conftest.apply_migrations_healing`` so a shared ``babylon_test`` DB left
    mid-migration by a killed background pytest run is healed loudly with one
    retry instead of erroring fixture setup — see conftest.py docstring.
    """
    from tests.unit.persistence.conftest import apply_migrations_healing

    apply_migrations_healing(pool, glob_pattern="002[0-3]_*.sql")


def test_view_exposes_22_column_contract(pool) -> None:
    """view_runtime_trace_emission has the 22 contract columns."""
    _apply_spec_065_migrations(pool)
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'view_runtime_trace_emission'
            ORDER BY ordinal_position
            """
        ).fetchall()
    actual = [r[0] for r in rows]
    assert actual == EXPECTED_COLUMNS, (
        f"view_runtime_trace_emission columns drift from contract.\n"
        f"Expected: {EXPECTED_COLUMNS}\n"
        f"Actual:   {actual}"
    )


def test_view_can_be_queried(pool) -> None:
    """View executes without error (smoke test for SQL validity)."""
    _apply_spec_065_migrations(pool)
    with pool.connection() as conn:
        result = conn.execute("SELECT COUNT(*) FROM view_runtime_trace_emission").fetchone()
    assert result is not None
    assert result[0] >= 0
