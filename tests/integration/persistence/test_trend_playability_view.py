"""Migration-applies proof for 0041 (M6 Task 41's trend widening).

Database-backed leg of ``test_trend_playability_migration.py``'s
source-level pins (ADR074: Postgres-connected tests are integration
tier), mirroring ``test_tick_summary_trend_view.py``'s fixture verbatim —
EXCEPT the migration sequence: 0038 applies first and 0041 re-declares
over it, exactly as the sorted ``00*.sql`` runner would, proving the
supersession is clean (DROP+CREATE) and the widened view computes real
``LAG`` deltas for the playability series.
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

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "babylon" / "persistence" / "migrations"
)
_TREND_0038 = _MIGRATIONS_DIR / "0038_tick_summary_trend.sql"
_PLAYABILITY_0041 = _MIGRATIONS_DIR / "0041_trend_playability.sql"


@pytest.fixture()
def fresh_db_pool(pg_dsn: str) -> Generator[Any, None, None]:
    """A pool against a brand-new database: spec-037 bootstrap, then
    migrations 0038 → 0041 in runner order."""
    from psycopg_pool import ConnectionPool

    db_name = f"trend_playability_{uuid.uuid4().hex[:12]}"
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
        ensure_ddl_applied(
            conn,
            [
                _TREND_0038.read_text(encoding="utf8"),
                _PLAYABILITY_0041.read_text(encoding="utf8"),
            ],
        )

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


def _insert_playability_row(
    pool: Any,
    session_id: uuid.UUID,
    tick: int,
    *,
    crisis_pop_share: float | None,
    bifurcation_score_mean: float | None,
    wage_compression_mean: float | None,
    capital_stock_total: float | None,
    unemployment_rate_mean: float | None,
) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO tick_summary
                (session_id, tick, crisis_pop_share, bifurcation_score_mean,
                 wage_compression_mean, capital_stock_total, unemployment_rate_mean)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                tick,
                crisis_pop_share,
                bifurcation_score_mean,
                wage_compression_mean,
                capital_stock_total,
                unemployment_rate_mean,
            ),
        )


class TestSupersession:
    def test_view_exists_with_the_widened_column_set(self, fresh_db_pool: Any) -> None:
        """0041's DROP+CREATE over 0038's view leaves exactly the 20
        declared columns, in declared order (the registry contract)."""
        from babylon.projection.registry import declared_view

        with fresh_db_pool.connection() as conn:
            rows = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'v_national_trend' ORDER BY ordinal_position"
            ).fetchall()
        assert tuple(r[0] for r in rows) == declared_view("v_national_trend").columns


class TestPlayabilityLagDeltas:
    def test_first_tick_has_null_playability_deltas(self, fresh_db_pool: Any) -> None:
        session_id = _insert_session(fresh_db_pool)
        _insert_playability_row(
            fresh_db_pool,
            session_id,
            1,
            crisis_pop_share=0.10,
            bifurcation_score_mean=0.3,
            wage_compression_mean=0.5,
            capital_stock_total=1000.0,
            unemployment_rate_mean=0.07,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT crisis_pop_share_delta, bifurcation_score_mean_delta, "
                "wage_compression_mean_delta, capital_stock_total_delta, "
                "unemployment_rate_mean_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 1",
                (session_id,),
            ).fetchone()

        assert row == (None, None, None, None, None)

    def test_second_tick_computes_the_real_playability_deltas(self, fresh_db_pool: Any) -> None:
        session_id = _insert_session(fresh_db_pool)
        _insert_playability_row(
            fresh_db_pool,
            session_id,
            1,
            crisis_pop_share=0.10,
            bifurcation_score_mean=0.3,
            wage_compression_mean=0.5,
            capital_stock_total=1000.0,
            unemployment_rate_mean=0.07,
        )
        _insert_playability_row(
            fresh_db_pool,
            session_id,
            2,
            crisis_pop_share=0.25,
            bifurcation_score_mean=0.2,
            wage_compression_mean=0.6,
            capital_stock_total=900.0,
            unemployment_rate_mean=0.09,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT crisis_pop_share, crisis_pop_share_delta, "
                "bifurcation_score_mean_delta, wage_compression_mean_delta, "
                "capital_stock_total_delta, unemployment_rate_mean_delta "
                "FROM v_national_trend WHERE session_id = %s AND tick = 2",
                (session_id,),
            ).fetchone()

        assert row[0] == pytest.approx(0.25)
        assert row[1] == pytest.approx(0.15)
        assert row[2] == pytest.approx(-0.1)
        assert row[3] == pytest.approx(0.1)
        assert row[4] == pytest.approx(-100.0)
        assert row[5] == pytest.approx(0.02)

    def test_fetch_national_trend_windows_the_tail_oldest_to_newest(
        self, fresh_db_pool: Any
    ) -> None:
        """The M6 fetch layer against the real view: ``last_n`` windows the
        TAIL of the campaign (DESC LIMIT), rows return ascending, and the
        declared-columns SELECT parses into the widened row model."""
        from types import SimpleNamespace

        from babylon.persistence.postgres_aggregation import fetch_national_trend

        session_id = _insert_session(fresh_db_pool)
        for tick in (1, 2, 3):
            _insert_playability_row(
                fresh_db_pool,
                session_id,
                tick,
                crisis_pop_share=0.1 * tick,
                bifurcation_score_mean=None,
                wage_compression_mean=None,
                capital_stock_total=None,
                unemployment_rate_mean=None,
            )

        rows = fetch_national_trend(
            runtime=SimpleNamespace(_pool=fresh_db_pool),  # type: ignore[arg-type]
            session_id=session_id,
            last_n=2,
        )

        assert [r.tick for r in rows] == [2, 3]
        assert rows[1].crisis_pop_share == pytest.approx(0.3)
        assert rows[1].crisis_pop_share_delta == pytest.approx(0.1)

    def test_null_endpoint_yields_null_delta_never_zero(self, fresh_db_pool: Any) -> None:
        """A series absent one side of the step (pre-first-year-boundary
        sparsity) is honest NULL, never a fabricated zero (III.11)."""
        session_id = _insert_session(fresh_db_pool)
        _insert_playability_row(
            fresh_db_pool,
            session_id,
            1,
            crisis_pop_share=None,
            bifurcation_score_mean=None,
            wage_compression_mean=None,
            capital_stock_total=None,
            unemployment_rate_mean=None,
        )
        _insert_playability_row(
            fresh_db_pool,
            session_id,
            2,
            crisis_pop_share=0.25,
            bifurcation_score_mean=0.2,
            wage_compression_mean=0.6,
            capital_stock_total=900.0,
            unemployment_rate_mean=0.09,
        )

        with fresh_db_pool.connection() as conn:
            row = conn.execute(
                "SELECT crisis_pop_share, crisis_pop_share_delta FROM v_national_trend "
                "WHERE session_id = %s AND tick = 2",
                (session_id,),
            ).fetchone()

        assert row[0] == pytest.approx(0.25)
        assert row[1] is None
