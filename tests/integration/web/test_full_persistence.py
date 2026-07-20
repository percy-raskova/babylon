"""Spec-109 A1: full snapshot persistence through the web resolve path.

The spec-061 FR-003 wire-up that never happened: ``persist_full_tick`` and
``persist_tick_summary`` had **zero production callers**, so ``tick_summary``
/ ``org_snapshot`` / ``edge_snapshot`` stayed empty forever and
``EngineBridge.get_game_timeseries`` returned empty arrays for every session.

These tests drive the real ``EngineBridge`` against Postgres and assert the
read-model tables fill at create (tick 0) and on every resolve.

Scope note: ``territory_snapshot`` is county-keyed (PK includes
``county_fips``) and today no web scenario sets ``Territory.county_fips``,
so hex-resolution sessions legitimately contribute no rows there — enriching
the serializer/scenarios with county identity is spec-109 A2, not A1.

Requires a running PostgreSQL instance (same contract as
``test_game_lifecycle.py``). Skip with: ``pytest -m "not requires_postgres"``.
"""

from __future__ import annotations

import os
import uuid

import pytest

from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL, ensure_ddl_applied

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("POSTGRES_HOST"),
        reason="PostgreSQL not configured (set POSTGRES_HOST)",
    ),
]


@pytest.fixture
def _django_setup() -> None:
    """Ensure Django is configured before running tests."""
    import django
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babylon_web.settings.development")
        django.setup()


@pytest.fixture
def bridge(_django_setup: None) -> object:
    """Create an EngineBridge connected to PostgreSQL."""
    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    conninfo = (
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon_test')} "
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"user={os.environ.get('POSTGRES_USER', 'babylon')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'babylon')}"
    )
    pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, open=True)
    persistence = PostgresRuntime(pool)

    from game.engine_bridge import EngineBridge

    return EngineBridge(persistence)


_COUNT_SQL = {
    "tick_summary": "SELECT COUNT(*) FROM tick_summary WHERE session_id = %s",
    "org_snapshot": "SELECT COUNT(*) FROM org_snapshot WHERE game_id = %s",
    "edge_snapshot": "SELECT COUNT(*) FROM edge_snapshot WHERE game_id = %s",
    "territory_snapshot": "SELECT COUNT(*) FROM territory_snapshot WHERE game_id = %s",
}


def _table_count(persistence: object, table: str, session_id: uuid.UUID) -> int:
    """Count a snapshot table's rows for one session (test-only DB peek)."""
    with persistence._pool.connection() as conn:  # noqa: SLF001
        row = conn.execute(_COUNT_SQL[table], (session_id,)).fetchone()
    assert row is not None
    return int(row[0])


class TestFullTickPersistence:
    """A1 gate: snapshot tables + tick_summary fill at create and per resolve."""

    def test_create_seeds_tick0_summary_and_snapshots(self, bridge: object) -> None:
        """Game creation writes the tick-0 summary row and org/edge snapshots."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        persistence = bridge._persistence  # noqa: SLF001

        assert _table_count(persistence, "tick_summary", session_id) == 1
        assert _table_count(persistence, "org_snapshot", session_id) > 0
        assert _table_count(persistence, "edge_snapshot", session_id) > 0

    def test_resolves_append_summary_rows_and_light_up_timeseries(self, bridge: object) -> None:
        """Two resolves -> three tick_summary rows -> real timeseries arrays."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        bridge.resolve_tick(session_id)
        bridge.resolve_tick(session_id)

        ts = bridge.get_game_timeseries(session_id)
        assert ts["ticks"] == [0, 1, 2]
        # imperial_rent maps from GlobalEconomy.imperial_rent_pool (always present);
        # consciousness averages SocialClass.class_consciousness over state.entities.
        assert all(v is not None for v in ts["imperial_rent"])
        assert all(v is not None for v in ts["consciousness"])
        assert all(v is not None for v in ts["solidarity"])

        persistence = bridge._persistence  # noqa: SLF001
        assert _table_count(persistence, "org_snapshot", session_id) >= 3
        assert _table_count(persistence, "edge_snapshot", session_id) >= 3

    def test_snapshot_rewrite_same_tick_is_benign(self, bridge: object) -> None:
        """The tick_log gate makes a same-tick re-write a logged no-op.

        ``persist_full_tick`` raises ``TickAlreadyResolved`` on a duplicate
        ``(session_id, tick)`` — the wrapper must swallow it (idempotent
        retry) without raising and without duplicating summary rows.
        """
        from game.engine_bridge import _persist_snapshots_safe

        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        persistence = bridge._persistence  # noqa: SLF001
        before = _table_count(persistence, "tick_summary", session_id)

        state, _graph = bridge.hydrate_state(session_id)
        _persist_snapshots_safe(persistence, session_id, state)  # must not raise

        assert _table_count(persistence, "tick_summary", session_id) == before


class TestWebPathMigrations:
    """Playability Spine Task 19 — the Trends-empty root cause (spec-116).

    The live web DB was created before migrations 0033/0034, and the web path
    never applies ``persistence/migrations/00*.sql`` — ``init_schema``'s
    ``CREATE TABLE IF NOT EXISTS`` no-ops on the pre-existing ``tick_summary``,
    so ``persist_tick_summary``/``query_tick_summary_series`` raised
    ``UndefinedColumn`` on every call and BOTH legs were swallowed by their
    best-effort catches (``logger.exception``) — the permanent "No timeseries
    data yet" Trends tab. Assert on ROWS/COLUMNS, never on the absence of
    exceptions (both failure legs are silent by design).
    """

    def test_apply_runtime_migrations_heals_pre_0033_tick_summary(self, bridge: object) -> None:
        """Simulate the pre-0033 web DB, then prove the web applier heals it."""
        from game.engine_bridge import _apply_runtime_migrations

        persistence = bridge._persistence  # noqa: SLF001
        pool = persistence._pool  # noqa: SLF001
        dropped = (
            "price_log",
            "fictitious_log",
            "market_corrections",
            "crisis_pop_share",
            "bifurcation_score_mean",
            "wage_compression_mean",
            "capital_stock_total",
            "unemployment_rate_mean",
        )
        with pool.connection() as conn:
            conn.autocommit = True
            # Self-sufficient setup (nightly 2026-07-19): guarantee the stamp
            # table exists whatever bootstrapped this DB — the old bare-loop
            # db:bootstrap created every schema table EXCEPT the stamp table
            # (its DDL lives only inside ensure_ddl_applied), so the DELETE
            # below crashed with UndefinedTable on nightly's Postgres.
            ensure_ddl_applied(conn, POSTGRES_SCHEMA_DDL)
            for column in dropped:
                conn.execute(f"ALTER TABLE tick_summary DROP COLUMN IF EXISTS {column}")
            # ensure_ddl_applied is digest-stamped: clear the stamps so the
            # applier cannot fast-path past the freshly-broken table. Guarded
            # DDL makes the later re-apply idempotent for sibling tests.
            conn.execute("DELETE FROM _babylon_schema_stamp")

        _apply_runtime_migrations(pool)

        with pool.connection() as conn:
            rows = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tick_summary'"
            ).fetchall()
        columns = {row[0] for row in rows}
        for column in dropped:
            assert column in columns, f"migration did not restore tick_summary.{column}"

    def test_summary_write_and_series_read_round_trip_on_healed_schema(
        self, bridge: object
    ) -> None:
        """The exact write/read pair that failed silently on the live 5432 DB."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        bridge.resolve_tick(session_id)

        ts = bridge.get_game_timeseries(session_id)

        assert ts["ticks"] == [0, 1], (
            "tick_summary rows must exist and be readable — a swallowed "
            "UndefinedColumn on either leg yields [] here"
        )
