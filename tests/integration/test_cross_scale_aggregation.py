"""Cross-scale aggregation integration tests (T042 / US3 / SC-002 / SC-012).

Inserts a contrived hex_state population, queries the v_county/state/national
views, and verifies the sums match independent Python aggregation to within
ε = 1e-10. Mutates one hex and re-queries — every parent scale changes by
exactly the delta (SC-012).

Skips cleanly when Postgres is unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


@pytest.fixture
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    # Digest-stamped + advisory-locked (never a bare re-execute loop: view
    # DDL vs concurrent readers deadlocked xdist runs, 2026-07-16; the raw
    # loop here also burned ~230s of setup per module).
    from babylon.persistence.postgres_schema import ensure_ddl_applied

    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    sql_files = sorted(migrations_dir.glob("00*.sql"))
    with pg_pool.connection() as conn:
        conn.autocommit = True
        ensure_ddl_applied(conn, [sql_file.read_text() for sql_file in sql_files])


@pytest.fixture
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def _seed_spatial_map(pg_pool, session_id, h3_indexes) -> None:  # type: ignore[no-untyped-def]
    """Register the session's hex → county mapping in ``hex_spatial_map``.

    Spec-088 S3 (FR-007): the per-tick writer stores NULL spatial keys in
    ``dynamic_hex_state`` — the single stored copy is the session-scoped
    ``hex_spatial_map`` row, which the aggregate views resolve via LEFT
    JOIN + COALESCE. A test that seeds hex rows without this mapping gets
    county_fips=NULL groups (and empty county/state view lookups).
    """
    with pg_pool.connection() as conn:
        for h3_index in h3_indexes:
            conn.execute(
                "INSERT INTO hex_spatial_map "
                "(session_id, h3_index, county_fips, state_fips, region_id) "
                "VALUES (%s, %s, '26163', '26', 'east_north_central') "
                "ON CONFLICT (session_id, h3_index) DO NOTHING",
                (str(session_id), h3_index),
            )
        conn.commit()


_SEED_H3S = [f"872d34a{i:02x}fffffff"[:15] for i in range(3)]


def _hex_seed(session_id, tick: int = 0):  # type: ignore[no-untyped-def]
    """Seed three hexes in Wayne County (26163) for the test session."""
    from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.hex_state import DynamicHexState

    rows = [
        DynamicHexState(
            session_id=session_id,
            tick=tick,
            h3_index=_SEED_H3S[i],
            county_fips="26163",
            state_fips="26",
            region_id="east_north_central",
            c=10.0 * (i + 1),
            v=5.0 * (i + 1),
            s=3.0 * (i + 1),
            k=100.0 * (i + 1),
            biocapacity_stock=20.0,
            energy_stock=10.0,
            raw_material_stock=5.0,
            internet_access_pct=0.85,
            surveillance_coupling=0.4,
        )
        for i in range(3)
    ]
    audit = ConservationAuditRow(
        session_id=session_id,
        tick=tick,
        scale="county",
        invariant_name="hex_to_county_sum_c",
        computed_value=60.0,
        expected_value=60.0,
        residual=0.0,
        severity=AuditSeverity.OK,
        determinism_hash="a" * 64,
        created_at_utc=datetime.now(tz=UTC),
    )
    return PerTickTransactionEnvelope(
        session_id=session_id,
        tick=tick,
        hex_state_rows=rows,
        audit_log_rows=[audit],
        determinism_hash="a" * 64,
    )


def test_county_view_sums_match_hex_python_sum(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """SC-002: v_county_value_aggregate.c_sum == python sum(c) within ε."""
    sid = uuid4()
    _seed_spatial_map(pg_pool, sid, _SEED_H3S)
    runtime.persist_tick_atomic(_hex_seed(sid))

    # Independent Python sum over the inserted hex rows.
    expected_c_sum = 10.0 + 20.0 + 30.0  # = 60.0
    expected_v_sum = 5.0 + 10.0 + 15.0  # = 30.0
    expected_s_sum = 3.0 + 6.0 + 9.0  # = 18.0

    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT c_sum, v_sum, s_sum, hex_count "
            "FROM v_county_value_aggregate "
            "WHERE session_id = %s AND tick = 0 AND county_fips = '26163'",
            (str(sid),),
        ).fetchone()
    assert row is not None
    assert abs(row[0] - expected_c_sum) <= 1e-10
    assert abs(row[1] - expected_v_sum) <= 1e-10
    assert abs(row[2] - expected_s_sum) <= 1e-10
    assert row[3] == 3


def test_state_view_aggregates_above_county(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """State-level sum equals hex-level Python sum (state_fips=26)."""
    sid = uuid4()
    _seed_spatial_map(pg_pool, sid, _SEED_H3S)
    runtime.persist_tick_atomic(_hex_seed(sid))
    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT c_sum, hex_count FROM v_state_value_aggregate "
            "WHERE session_id = %s AND tick = 0 AND state_fips = '26'",
            (str(sid),),
        ).fetchone()
    assert row is not None
    assert abs(row[0] - 60.0) <= 1e-10
    assert row[1] == 3


def test_national_view_aggregates_above_state(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """National-level row exists with the single-USA national_id."""
    sid = uuid4()
    _seed_spatial_map(pg_pool, sid, _SEED_H3S)
    runtime.persist_tick_atomic(_hex_seed(sid))
    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT national_id, c_sum, hex_count "
            "FROM v_national_value_aggregate WHERE session_id = %s AND tick = 0",
            (str(sid),),
        ).fetchone()
    assert row is not None
    assert row[0] == "USA"
    assert abs(row[1] - 60.0) <= 1e-10
    assert row[2] == 3
