"""Spec 061 T106 / FR-032 + FR-033: seed_initial_game uses the real engine.

The replacement for the deleted ``seed_mock_game`` command must:

1. Refuse to run when ``game.api._bridge_instance`` is None (the bridge
   wasn't initialized — typically because Postgres was unreachable at
   boot, see FR-006).
2. Refuse to run when the bridge is a class other than ``EngineBridge``
   (e.g., a leftover stub).
3. Create or reuse the Django auth user named via ``--player``.
4. Defer to ``EngineBridge.create_game()`` for the actual session
   creation — no ``snapshot_json`` blob written by the command.

Migration 0008 dropped ``game_session.snapshot_json`` entirely, so the
original spec assertion ("snapshot_json empty/absent") is now structurally
guaranteed by the schema. These tests focus on the *bridge-selection
contract* of the command, which is the remaining behavior worth pinning.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.integration


class TestSeedInitialGameBridgeContract:
    """T106 / FR-032: the seed command never falls back to a mock."""

    def test_raises_when_bridge_is_none(self, db, monkeypatch) -> None:  # noqa: ARG002
        """When the engine bridge wasn't initialized, the command must fail loud."""
        from game import api as game_api

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)

        with pytest.raises(CommandError, match="EngineBridge not initialized"):
            call_command(
                "seed_initial_game",
                "--scenario",
                "wayne_county",
                "--player",
                "spec061-t106-noop",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_raises_when_bridge_is_wrong_class(self, db, monkeypatch) -> None:  # noqa: ARG002
        """Any bridge that isn't EngineBridge (e.g., a stub) is rejected."""
        from game import api as game_api

        class _ImposterBridge:
            """A bridge that is NOT EngineBridge."""

        monkeypatch.setattr(game_api, "_bridge_instance", _ImposterBridge(), raising=False)

        with pytest.raises(CommandError, match="Expected EngineBridge"):
            call_command(
                "seed_initial_game",
                "--scenario",
                "wayne_county",
                "--player",
                "spec061-t106-noop",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_creates_django_user_when_absent(self, db, monkeypatch) -> None:  # noqa: ARG002
        """The --player auth user is created on demand (before the bridge call)."""
        from game import api as game_api

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)

        User = get_user_model()
        username = "spec061-t106-newuser"
        User.objects.filter(username=username).delete()  # ensure absent

        # The command will raise CommandError because bridge is None,
        # but only AFTER it has created the auth user.
        with pytest.raises(CommandError):
            call_command(
                "seed_initial_game",
                "--player",
                username,
                stdout=StringIO(),
                stderr=StringIO(),
            )

        user = User.objects.get(username=username)
        assert user.is_staff is True, "seeded player should be staff"
        assert user.is_superuser is True, "seeded player should be superuser"

    def test_reuses_existing_django_user(self, db, monkeypatch) -> None:  # noqa: ARG002
        """If the --player username already exists, it is reused (not duplicated)."""
        from game import api as game_api

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)

        User = get_user_model()
        username = "spec061-t106-existing"
        User.objects.filter(username=username).delete()
        User.objects.create_user(username=username, password="test")

        before_count = User.objects.filter(username=username).count()
        assert before_count == 1

        with pytest.raises(CommandError):
            call_command(
                "seed_initial_game",
                "--player",
                username,
                stdout=StringIO(),
                stderr=StringIO(),
            )

        after_count = User.objects.filter(username=username).count()
        assert after_count == 1, "seed command must not duplicate existing users"
