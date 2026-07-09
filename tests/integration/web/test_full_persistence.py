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
