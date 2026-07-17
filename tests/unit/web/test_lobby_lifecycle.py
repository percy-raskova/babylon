"""Lobby lifecycle surface (spec-116 FR-116-3).

Covers the three backend seams the lobby rebuild rides on:

- ``web/game/codenames.py`` — deterministic UUID-derived operation codenames;
- ``codename`` surfaced by ``GET /api/games/`` (list) and ``GET /api/games/{id}/``;
- ``DELETE /api/games/{id}/`` (hard delete, FK cascade) and
  ``POST /api/games/{id}/archive/`` (reversible ``status='abandoned'``).

Pattern provenance: Client/django_db view tests follow
``tests/unit/web/test_api.py::TestCreateGameScenarioValidation``; URL-resolution
tests follow ``TestURLRouting``. Imports stay inside test bodies so a missing
module fails the TEST (red phase), not collection.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client
from django.urls import reverse


def _login_client(username: str) -> tuple[Client, int]:
    """Create a fresh user and return a logged-in test client plus the user id."""
    from django.contrib.auth.models import User

    user = User.objects.create_user(username=username, password="lobbypass123")  # type: ignore[no-untyped-call]
    client = Client()
    client.login(username=username, password="lobbypass123")
    return client, int(user.id)


@pytest.mark.unit
class TestOperationCodename:
    """The codename generator is a pure, deterministic function of the UUID."""

    def test_same_uuid_always_yields_the_same_codename(self) -> None:
        from game.codenames import operation_codename

        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert operation_codename(sid) == operation_codename(sid)

    def test_codename_is_two_uppercase_words_from_the_curated_lists(self) -> None:
        from game.codenames import _LEFT, _RIGHT, operation_codename

        parts = operation_codename(uuid.uuid4()).split(" ")
        assert len(parts) == 2
        assert parts[0] in _LEFT
        assert parts[1] in _RIGHT

    def test_codename_derives_from_uuid_not_rng_seed(self) -> None:
        """Sessions differing only in leading UUID bytes get distinct names.

        Guards the recon gotcha: ``rng_seed`` is 0 for every existing session
        (serializer default, lobby never sends one), so a seed-derived codename
        would collide across ALL games. UUID bytes 0-1 select the left word and
        bytes 2-3 the right word, so these two UUIDs provably differ.
        """
        from game.codenames import operation_codename

        a = operation_codename(uuid.UUID("00000000-0000-0000-0000-000000000000"))
        b = operation_codename(uuid.UUID("00010001-0000-0000-0000-000000000000"))
        assert a != b


@pytest.mark.unit
class TestGameSessionListSerializerCodename:
    """``codename`` must be a DECLARED field — DRF silently drops undeclared keys."""

    def test_codename_round_trips_through_the_list_serializer(self) -> None:
        from game.serializers import GameSessionListSerializer

        row = {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "scenario": "wayne_county",
            "current_tick": 3,
            "status": "active",
            "created_at": "2026-07-17T12:00:00Z",
            "codename": "CRIMSON HARVEST",
        }
        serializer = GameSessionListSerializer(row)
        assert serializer.data["codename"] == "CRIMSON HARVEST"


@pytest.mark.unit
@pytest.mark.django_db
class TestLobbyCodenameSurfacing:
    """Both list and detail views emit the derived codename."""

    def test_game_list_rows_carry_the_derived_codename(self) -> None:
        from game.codenames import operation_codename
        from game.models import GameSession

        client, user_id = _login_client("lister")
        session = GameSession.objects.create(player_id=user_id, scenario="wayne_county")

        response = client.get("/api/games/")

        assert response.status_code == 200
        rows = json.loads(response.content)["data"]
        assert rows[0]["codename"] == operation_codename(session.id)

    def test_game_detail_carries_the_derived_codename(self) -> None:
        from game.codenames import operation_codename
        from game.models import GameSession

        client, user_id = _login_client("detailer")
        session = GameSession.objects.create(player_id=user_id, scenario="wayne_county")

        response = client.get(f"/api/games/{session.id}/")

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data["codename"] == operation_codename(session.id)


@pytest.mark.unit
@pytest.mark.django_db
class TestGameDeleteAndArchive:
    """DELETE = permanent (cascade); archive = reversible status flip."""

    @pytest.fixture(autouse=True)
    def _cascade_target_tables(self) -> None:
        """Create the DELETE cascade's target tables, scoped to this class only.

        These ``managed=False`` snapshot tables (real schema:
        ``src/babylon/persistence/postgres_schema.py``; Django FK mirror:
        ``web/game/models.py``, all ``on_delete=CASCADE``) are correctly
        cascaded in Postgres. But the *shared* SQLite unit-test fixture
        (``tests/unit/web/conftest.py::_create_unmanaged_tables``) only
        creates 4 of the ~11 tables FK'd to ``game_session`` — it predates
        the Program-037 snapshot tables and was never exercised by a real
        cascade-delete test until now. Rather than widen that shared
        fixture's blast radius across the whole unit suite, the missing
        tables are created here, scoped to this class. Django's delete
        collector only needs the ``game_id`` column to issue
        ``DELETE FROM <table> WHERE game_id = ...`` against a table with
        zero related rows — no other columns are read.
        """
        from django.db import connection

        with connection.cursor() as cursor:
            for table in (
                "territory_snapshot",
                "org_snapshot",
                "class_snapshot",
                "edge_snapshot",
                "community_snapshot",
                "economic_summary",
                "tick_event",
            ):
                cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} "
                    "(game_id CHAR(32) NOT NULL REFERENCES game_session(id))"
                )

    def test_archive_url_resolves(self) -> None:
        url = reverse(
            "game:game-archive",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/archive/"

    def test_delete_removes_the_session_row(self) -> None:
        from game.models import GameSession

        client, user_id = _login_client("deleter")
        session = GameSession.objects.create(player_id=user_id, scenario="wayne_county")

        response = client.delete(f"/api/games/{session.id}/")

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["data"] == {"deleted": True}
        assert GameSession.objects.filter(id=session.id).count() == 0

    def test_delete_another_users_session_is_a_404(self) -> None:
        from game.models import GameSession

        _, owner_id = _login_client("owner")
        session = GameSession.objects.create(player_id=owner_id, scenario="wayne_county")
        intruder, _ = _login_client("intruder")

        response = intruder.delete(f"/api/games/{session.id}/")

        assert response.status_code == 404
        assert GameSession.objects.filter(id=session.id).count() == 1

    def test_archive_sets_status_abandoned(self) -> None:
        from game.models import GameSession

        client, user_id = _login_client("archiver")
        session = GameSession.objects.create(player_id=user_id, scenario="wayne_county")

        response = client.post(f"/api/games/{session.id}/archive/")

        assert response.status_code == 200
        assert json.loads(response.content)["data"] == {"status": "abandoned"}
        session.refresh_from_db()
        assert session.status == "abandoned"

    def test_archiving_an_archived_game_is_a_loud_400(self) -> None:
        from game.models import GameSession

        client, user_id = _login_client("rearchiver")
        session = GameSession.objects.create(
            player_id=user_id, scenario="wayne_county", status="abandoned"
        )

        response = client.post(f"/api/games/{session.id}/archive/")

        assert response.status_code == 400
        assert json.loads(response.content)["status"] == "error"
