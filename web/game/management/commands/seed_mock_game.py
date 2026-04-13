"""Management command to seed a mock game session.

Creates a Django auth user ``admin/admin`` (if not present) and a
``GameSession`` with a fully-populated ``snapshot_json`` from
``MockEngineBridge._build_initial_snapshot()``.

Usage::

    DJANGO_SETTINGS_MODULE=babylon_web.settings.stub \\
        python manage.py seed_mock_game
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from game.mock_bridge import MockEngineBridge


class Command(BaseCommand):
    """Seed a mock game session for end-to-end testing."""

    help = "Create a mock game session with initial snapshot data."

    def handle(self, *_args: object, **_options: object) -> None:
        # Ensure admin user exists
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password("admin")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin/admin)"))
        else:
            self.stdout.write("Admin user already exists")

        # Create the mock game
        bridge = MockEngineBridge()
        result = bridge.create_game(
            player_id=user.id,
            scenario="wayne_county_mock",
        )

        session_id = result["id"]
        self.stdout.write(self.style.SUCCESS(f"Mock game created: {session_id}"))
        self.stdout.write(f"  Navigate to: /games/{session_id}")
        self.stdout.write("  Login: admin / admin")
