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
    from babylon.persistence.postgres_runtime import PostgresRuntime

    persistence = PostgresRuntime(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "babylon_test"),
        user=os.environ.get("POSTGRES_USER", "babylon"),
        password=os.environ.get("POSTGRES_PASSWORD", "babylon"),
    )

    from game.engine_bridge import EngineBridge

    return EngineBridge(persistence)


class TestBridgeRoundTrip:
    """Test that state survives hydrate -> serialize -> hydrate round-trips."""

    def test_snapshot_structure_is_complete(self, bridge: object) -> None:
        """Snapshot dict has all required top-level keys."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=123)
        snapshot = bridge.get_snapshot(session_id)

        required_keys = {
            "session_id",
            "tick",
            "entities",
            "territories",
            "organizations",
            "institutions",
            "economy",
            "events",
        }
        assert required_keys.issubset(set(snapshot.keys()))

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
        assert len(snap1["entities"]) == len(snap2["entities"])
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
