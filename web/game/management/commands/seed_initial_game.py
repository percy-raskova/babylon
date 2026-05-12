"""Management command: seed an initial real-engine game session.

Spec 061 US7 (T110, FR-032): replaces the deleted ``seed_mock_game``
command. Creates a Django auth user (admin/admin by default) and a
real ``EngineBridge``-backed game session — no fixture data, no
``snapshot_json`` blob.

Usage::

    python manage.py seed_initial_game [--scenario wayne_county] [--player admin]

If the engine bridge isn't initialized (e.g., Postgres is unreachable
or the app is running under stub settings), the command exits with a
clear error rather than falling back to a mock.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Seed a real-engine game session for development and testing."""

    help = "Create a real-engine game session (spec 061 replacement for seed_mock_game)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--scenario",
            type=str,
            default="wayne_county",
            help="Scenario name (default: wayne_county, the constitutional test case)",
        )
        parser.add_argument(
            "--player",
            type=str,
            default="admin",
            help="Django auth username for the player (created if absent)",
        )
        parser.add_argument(
            "--rng-seed",
            type=int,
            default=0,
            help="Deterministic RNG seed for action resolution (FR-024)",
        )

    def handle(self, *_args: object, **options: Any) -> None:
        scenario: str = options["scenario"]
        player_username: str = options["player"]
        rng_seed: int = options["rng_seed"]

        user, created = User.objects.get_or_create(
            username=player_username,
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(player_username)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created auth user {player_username}/{player_username} (is_staff=True)"
                )
            )
        else:
            self.stdout.write(f"Auth user {player_username!r} already exists")

        # Real bridge — refuse to fall back on the deleted MockEngineBridge.
        from game import api as game_api

        bridge = game_api._bridge_instance  # noqa: SLF001 — module singleton
        if bridge is None:
            raise CommandError(
                "EngineBridge not initialized. Set up PostgreSQL and run via the "
                "production settings module, or call init_bridge(persistence) "
                "before invoking this command."
            )

        if type(bridge).__name__ != "EngineBridge":
            raise CommandError(
                f"Expected EngineBridge, got {type(bridge).__name__}. "
                "Spec 061 US7 removed the mock bridge fallback; use the real "
                "Postgres-backed bridge."
            )

        session_id = bridge.create_game(
            scenario=scenario,
            rng_seed=rng_seed,
            player_id=user.id,
        )
        self.stdout.write(self.style.SUCCESS(f"Game session created: {session_id}"))
        self.stdout.write(f"  Scenario: {scenario}")
        self.stdout.write(f"  RNG seed: {rng_seed}")
        self.stdout.write(f"  Player:   {player_username}")
        self.stdout.write(f"  Navigate to: /games/{session_id}")
