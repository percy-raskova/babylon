"""Management command: reset sessions wedged in 'resolving' (C.13 watchdog).

A worker killed mid-resolve (OOM, SIGKILL, deploy restart) leaves
``game_session.status='resolving'`` with no surviving process to restore
it; every subsequent resolve/pause/action request is rejected. This
sweeper resets sessions that have been 'resolving' longer than the
threshold back to 'active'. Run periodically (cron/systemd timer) or
once after a crashed deploy.

Usage::

    python manage.py sweep_stale_sessions [--threshold-seconds 120] [--dry-run]
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    """Reset game sessions stuck in 'resolving' back to 'active'."""

    help = "Reset game sessions wedged in 'resolving' status (C.13 watchdog)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--threshold-seconds",
            type=int,
            default=120,
            help="Age in seconds before a 'resolving' session counts as wedged (default: 120)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report wedged sessions without modifying them",
        )

    def handle(self, *_args: object, **options: Any) -> None:
        from game.log_handler import log_game_event
        from game.models import GameSession

        cutoff = timezone.now() - dt.timedelta(seconds=options["threshold_seconds"])
        stale = list(GameSession.objects.filter(status="resolving", updated_at__lt=cutoff))
        if not stale:
            self.stdout.write("No wedged sessions found")
            return
        # Loop bound: the queryset materialized above is finite.
        for session in stale:
            age = (timezone.now() - session.updated_at).total_seconds()
            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] would recover {session.id} (resolving for {age:.0f}s)"
                )
                continue
            # Conditional filter is race-safe against a concurrently
            # completing resolve (which already set 'active').
            GameSession.objects.filter(id=session.id, status="resolving").update(
                status="active", updated_at=timezone.now()
            )
            log_game_event(
                category="game_recover",
                message=f"Sweeper recovered wedged session after {age:.0f}s",
                session_id=session.id,
                tick=session.current_tick,
            )
            self.stdout.write(self.style.SUCCESS(f"Recovered {session.id}"))
