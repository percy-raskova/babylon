"""Annual Φ-distribution-to-counties integration test (T074 / FR-035 / SC-010).

For one external node and a Detroit-tri-county exposure split, run 52 weekly
distributions through ``distribute_phi_week_to_counties()`` and persist each
week's boundary register rows via ``persist_tick_atomic()``. After 52 ticks,
query ``boundary_flow_register`` filtered by ``flow_type='drain_edge'`` AND
``dest_kind='county'``, sum ``magnitude``, assert sum ≈ phi_year within 1e-6.
"""

from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


@pytest.fixture(scope="module")
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture(scope="module")
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def test_annual_phi_distribution_sums_to_phi_year(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """52 weeks × phi_year/52 × exposure_weights == phi_year (FR-035)."""
    from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.systems.phi_distribution import distribute_phi_week_to_counties
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    phi_year = 100_000_000.0  # $100M
    exposure = {"26163": 0.6, "26125": 0.25, "26099": 0.15}

    register = BoundaryFlowRegister()
    for week in range(52):
        distribute_phi_week_to_counties(
            session_id=sid,
            tick=week,
            external_node_id="canada",
            phi_year_inflow=phi_year,
            county_exposure=exposure,
            register=register,
        )
        # Persist this week's buffered rows.
        rows = register.flush()
        envelope = PerTickTransactionEnvelope(
            session_id=sid,
            tick=week,
            boundary_register_rows=rows,
            determinism_hash="c" * 64,
        )
        runtime.persist_tick_atomic(envelope)

    # Query the annual sum via boundary_flow_register
    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT SUM(magnitude) FROM boundary_flow_register "
            "WHERE session_id = %s AND flow_type = 'drain_edge' "
            "AND dest_kind = 'county'",
            (str(sid),),
        ).fetchone()

    assert row is not None
    annual_sum = float(row[0])
    assert math.isclose(annual_sum, phi_year, abs_tol=1e-3), (
        f"FR-035 violated: 52-week sum {annual_sum} != phi_year {phi_year}"
    )


def test_per_county_share_matches_exposure_weight(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """Wayne (60%) gets 60% of annual phi; Oakland (25%) gets 25%; Macomb (15%) gets 15%."""
    from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.systems.phi_distribution import distribute_phi_week_to_counties
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    phi_year = 52_000_000.0  # $52M = $1M/week
    exposure = {"26163": 0.6, "26125": 0.25, "26099": 0.15}

    register = BoundaryFlowRegister()
    for week in range(52):
        distribute_phi_week_to_counties(
            session_id=sid,
            tick=week,
            external_node_id="china",
            phi_year_inflow=phi_year,
            county_exposure=exposure,
            register=register,
        )
        rows = register.flush()
        runtime.persist_tick_atomic(
            PerTickTransactionEnvelope(
                session_id=sid,
                tick=week,
                boundary_register_rows=rows,
                determinism_hash="d" * 64,
            )
        )

    with pg_pool.connection() as conn:
        rows = conn.execute(
            "SELECT dest_node_id, SUM(magnitude) FROM boundary_flow_register "
            "WHERE session_id = %s AND source_node_id = 'china' "
            "GROUP BY dest_node_id",
            (str(sid),),
        ).fetchall()
    by_county = {r[0]: float(r[1]) for r in rows}
    assert math.isclose(by_county["26163"], phi_year * 0.6, abs_tol=1e-3)
    assert math.isclose(by_county["26125"], phi_year * 0.25, abs_tol=1e-3)
    assert math.isclose(by_county["26099"], phi_year * 0.15, abs_tol=1e-3)
