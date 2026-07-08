"""Tests for the sweep_stale_sessions watchdog command (C.13).

A worker killed mid-resolve leaves ``game_session.status='resolving'``
forever; the sweeper resets sessions older than the threshold.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from game.models import GameEventLog, GameSession


def _make_session(status: str, age_seconds: int) -> GameSession:
    session = GameSession.objects.create(
        id=uuid.uuid4(), scenario="two_node", current_tick=1, status=status
    )
    # QuerySet.update() bypasses auto_now — backdate the transition clock.
    GameSession.objects.filter(id=session.id).update(
        updated_at=timezone.now() - dt.timedelta(seconds=age_seconds)
    )
    session.refresh_from_db()
    return session


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_recovers_stale_resolving_session() -> None:
    stale = _make_session("resolving", 600)
    fresh = _make_session("resolving", 10)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert stale.status == "active"
    assert fresh.status == "resolving"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_ignores_non_resolving_sessions() -> None:
    active = _make_session("active", 600)
    paused = _make_session("paused", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    active.refresh_from_db()
    paused.refresh_from_db()
    assert active.status == "active"
    assert paused.status == "paused"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_dry_run_changes_nothing() -> None:
    stale = _make_session("resolving", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120", "--dry-run")

    stale.refresh_from_db()
    assert stale.status == "resolving"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_logs_recovery_event() -> None:
    stale = _make_session("resolving", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    assert GameEventLog.objects.filter(session_id=stale.id, category="game_recover").exists()
