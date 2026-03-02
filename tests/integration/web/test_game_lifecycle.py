"""Full game lifecycle integration test (Phase 8).

Tests the complete flow: create game -> submit action -> resolve tick -> verify results.
Requires a running PostgreSQL instance with PostGIS.

Skip with: ``pytest -m "not requires_postgres"``
"""

from __future__ import annotations

import os
import uuid

import pytest

# Skip entire module if Postgres is not available
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


class TestGameLifecycle:
    """End-to-end game lifecycle: create -> submit -> resolve -> verify."""

    def test_create_game_returns_uuid(self, bridge: object) -> None:
        """Creating a game returns a valid UUID."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=42)
        assert isinstance(session_id, uuid.UUID)

    def test_snapshot_after_create(self, bridge: object) -> None:
        """Snapshot after creation shows tick 0 with initial state."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=42)
        snapshot = bridge.get_snapshot(session_id)

        assert snapshot["session_id"] == str(session_id)
        assert isinstance(snapshot["tick"], int)
        assert "entities" in snapshot
        assert "territories" in snapshot

    def test_resolve_tick_advances_state(self, bridge: object) -> None:
        """Resolving a tick advances the tick counter."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=42)

        initial_snapshot = bridge.get_snapshot(session_id)
        initial_tick = initial_snapshot["tick"]

        result = bridge.resolve_tick(session_id)
        assert result["tick"] == initial_tick + 1

    def test_available_actions_returns_dict(self, bridge: object) -> None:
        """Available actions returns a dict with session info and actions."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)
        session_id = bridge.create_game(scenario="default", rng_seed=42)
        available = bridge.get_available_actions(session_id)

        assert "session_id" in available
        assert "tick" in available
        assert "actions" in available
        assert isinstance(available["actions"], dict)

    def test_full_lifecycle_create_submit_resolve(self, bridge: object) -> None:
        """Full lifecycle: create game, submit action, resolve, check results."""
        from game.engine_bridge import EngineBridge

        assert isinstance(bridge, EngineBridge)

        # 1. Create game
        session_id = bridge.create_game(scenario="default", rng_seed=42, player_id=1)
        assert isinstance(session_id, uuid.UUID)

        # 2. Get initial state
        snapshot = bridge.get_snapshot(session_id)
        assert snapshot["tick"] == 0

        # 3. Submit a player action (if orgs available)
        available = bridge.get_available_actions(session_id)
        org_actions = available.get("actions", {})

        if org_actions:
            first_org = next(iter(org_actions))
            first_action = org_actions[first_org][0]
            turn_id = bridge.submit_action(
                session_id=session_id,
                tick=0,
                org_id=first_org,
                verb="AGITATE",
                action_type=first_action.get("action_type"),
                target_id=first_action.get("target_id"),
            )
            assert isinstance(turn_id, int)

        # 4. Resolve tick
        resolved = bridge.resolve_tick(session_id)
        assert resolved["tick"] == 1
        assert resolved["session_id"] == str(session_id)

        # 5. Verify state advanced
        new_snapshot = bridge.get_snapshot(session_id)
        assert new_snapshot["tick"] >= 1
