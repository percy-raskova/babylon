"""Migration-applies proof for 0038 (T5 Unit U2's ``v_national_trend``).

Database-backed leg of ``test_tick_summary_trend_migration.py``'s
source-level pins — ADR074's test-estate law (Postgres-connected tests
belong in the integration tier). Follows the ``ensure_ddl_applied`` idiom
(``test_migration_idempotency.py``'s ``fresh_db_pool`` fixture pattern): a
fresh, disposable database bootstrapped with the spec-037 schema, then
migration 0038 applied directly (this test targets ONE migration, not the
whole runner sequence) — proving the view creates and its ``LAG`` windows
compute real per-session, per-tick deltas.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql

from babylon.persistence.postgres_schema import ensure_ddl_applied

pytestmark = pytest.mark.integration

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "babylon"
    / "persistence"
    / "migrations"
    / "0038_tick_summary_trend.sql"
)


@pytest.fixture()
def fresh_db_pool(pg_dsn: str) -> Generator[Any, None, None]:
    """A pool against a brand-new database, spec-037-bootstrapped then
    migration-0038-applied — mirrors ``test_migration_idempotency.py``'s
    own ``fresh_db_pool`` fixture (a disposable per-test database, never
    the shared ``babylon_test``)."""
    from psycopg_pool import ConnectionPool

    db_name = f"trend_view_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(pg_dsn, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not available (set BABYLON_TEST_PG_DSN)")
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    fresh_dsn = re.sub(r"dbname=\S+", f"dbname={db_name}", pg_dsn)
    pool = ConnectionPool(conninfo=fresh_dsn, min_size=1, max_size=2, open=True)

    from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

    with pool.connection() as conn:
        conn.autocommit = True
        for ddl in POSTGRES_SCHEMA_DDL:
            conn.execute(ddl)
        ensure_ddl_applied(conn, [_MIGRATION.read_text(encoding="utf8")])

    try:
        yield pool
    finally:
        pool.close()
        with psycopg.connect(pg_dsn, autocommit=True) as admin2:
            admin2.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_name)))


def _insert_session(pool: Any) -> uuid.UUID:
    session_id = uuid.uuid4()
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO game_session (id, scenario) VALUES (%s, %s)",
            (session_id, "test_scenario"),
        )
    return session_id


def _insert_tick_summary_row(
    pool: Any,
    session_id: uuid.UUID,
    tick: int,
    *,
    imperial_rent: float | None,
    price_log: float | None,
    fictitious_log: float | None,
    market_corrections: int | None,
) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO tick_summary
                (session_id, tick, imperial_rent, price_log, fictitious_log, market_corrections)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (session_id, tick, imperial_rent, price_log, fictitious_log, market_corrections),
        )


class TestViewCreates:
    def test_view_exists_after_migration(self, fresh_db_pool: Any) -> None:
        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM pg_views WHERE viewname = 'v_national_trend'"
            ).fetchone()
        assert row is not None


class TestLagDeltas:
    def test_first_tick_has_null_deltas(self, fresh_db_pool: Any) -> None:
        """No prior row to LAG against — honest NULL, never a fabricated zero."""
        session_id = _insert_session(fresh_db_pool)
        _insert_tick_summary_row(
            fresh_db_pool,
            session_id,
            1,
            imperial_rent=10.0,
            price_log=0.1,
            fictitious_log=0.2,
            market_corrections=0,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT imperial_rent_delta, price_log_delta, fictitious_log_delta, "
                "market_corrections_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 1",
                (session_id,),
            ).fetchone()

        assert row == (None, None, None, None)

    def test_second_tick_computes_the_real_delta(self, fresh_db_pool: Any) -> None:
        session_id = _insert_session(fresh_db_pool)
        _insert_tick_summary_row(
            fresh_db_pool,
            session_id,
            1,
            imperial_rent=10.0,
            price_log=0.1,
            fictitious_log=0.2,
            market_corrections=0,
        )
        _insert_tick_summary_row(
            fresh_db_pool,
            session_id,
            2,
            imperial_rent=12.5,
            price_log=0.15,
            fictitious_log=0.05,
            market_corrections=1,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT imperial_rent, imperial_rent_delta, price_log_delta, "
                "fictitious_log_delta, market_corrections_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 2",
                (session_id,),
            ).fetchone()

        assert row[0] == pytest.approx(12.5)
        assert row[1] == pytest.approx(2.5)
        assert row[2] == pytest.approx(0.05)
        assert row[3] == pytest.approx(-0.15)
        assert row[4] == 1  # one correction snapped between tick 1 and tick 2

    def test_sessions_never_lag_across_each_other(self, fresh_db_pool: Any) -> None:
        """``PARTITION BY session_id``: two campaigns' tick-1 rows never see
        each other's history."""
        session_a = _insert_session(fresh_db_pool)
        session_b = _insert_session(fresh_db_pool)
        _insert_tick_summary_row(
            fresh_db_pool,
            session_a,
            1,
            imperial_rent=100.0,
            price_log=None,
            fictitious_log=None,
            market_corrections=None,
        )
        _insert_tick_summary_row(
            fresh_db_pool,
            session_b,
            1,
            imperial_rent=1.0,
            price_log=None,
            fictitious_log=None,
            market_corrections=None,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT imperial_rent_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 1",
                (session_b,),
            ).fetchone()

        assert row == (None,)

    def test_null_endpoint_yields_null_delta_never_a_fabricated_zero(
        self, fresh_db_pool: Any
    ) -> None:
        session_id = _insert_session(fresh_db_pool)
        _insert_tick_summary_row(
            fresh_db_pool,
            session_id,
            1,
            imperial_rent=None,
            price_log=None,
            fictitious_log=None,
            market_corrections=None,
        )
        _insert_tick_summary_row(
            fresh_db_pool,
            session_id,
            2,
            imperial_rent=5.0,
            price_log=None,
            fictitious_log=None,
            market_corrections=None,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT imperial_rent_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 2",
                (session_id,),
            ).fetchone()

        assert row == (None,)
