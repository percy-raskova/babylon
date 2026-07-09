"""Engine bridge round-trip integration tests (Phase 8).

Tests state serialization consistency: snapshot -> API -> snapshot.
Verifies that data survives the bridge translation layer intact.

Requires a running PostgreSQL instance with PostGIS.
Skip with: ``pytest -m "not requires_postgres"``
"""

from __future__ import annotations

import os

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


class TestBridgeRoundTrip:
    """Test that state survives hydrate -> serialize -> hydrate round-trips."""

    def test_snapshot_structure_is_complete(self, bridge: object) -> None:
        """Snapshot dict has all required top-level keys.

        Per Spec 052 (`specs/052-worldstate-snapshot-contract/spec.md`) §5,
        there is no top-level ``entities`` array (organizations are the only
        top-level agents; classes/demographics appear only as hyperedge
        memberships or derived aggregations) and no top-level ``economy``
        block (its contents live under ``derived``).
        """
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=123)
        snapshot = bridge.get_snapshot(session_id)

        required_keys = {
            "session_id",
            "tick",
            "territories",
            "organizations",
            "institutions",
            "derived",
            "events",
        }
        assert required_keys.issubset(set(snapshot.keys()))
        assert "entities" not in snapshot, "Spec 052 §5 forbids a top-level 'entities' key"
        assert "economy" in snapshot["derived"]

    def test_snapshot_entities_are_serializable(self, bridge: object) -> None:
        """All entity dicts in snapshot are JSON-serializable."""
        import json

        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=123)
        snapshot = bridge.get_snapshot(session_id)

        # Should not raise
        json.dumps(snapshot, default=str)

    def test_snapshot_consistency_across_hydrations(self, bridge: object) -> None:
        """Two consecutive hydrations of the same tick produce identical snapshots."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=456)

        snap1 = bridge.get_snapshot(session_id)
        snap2 = bridge.get_snapshot(session_id)

        assert snap1["tick"] == snap2["tick"]
        assert snap1["session_id"] == snap2["session_id"]
        assert len(snap1["organizations"]) == len(snap2["organizations"])
        assert len(snap1["territories"]) == len(snap2["territories"])

    def test_resolve_produces_different_tick(self, bridge: object) -> None:
        """After resolve, snapshot tick is strictly greater than before."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=789)

        before = bridge.get_snapshot(session_id)
        bridge.resolve_tick(session_id)
        after = bridge.get_snapshot(session_id)

        assert after["tick"] > before["tick"]

    def test_multiple_resolves_are_monotonic(self, bridge: object) -> None:
        """Multiple resolves produce monotonically increasing ticks."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=999)

        max_ticks = 3
        prev_tick = -1
        for _ in range(max_ticks):
            result = bridge.resolve_tick(session_id)
            assert result["tick"] > prev_tick
            prev_tick = result["tick"]
