"""Unit tests for ``GET /api/games/{id}/narration/`` (program-20 Track B, task B5).

Django test client + real ``NarrationRecord`` rows (B4), matching the
established pattern in ``tests/unit/web/test_game_explain_view.py``
(``django_db`` + SQLite in-memory, ``User``/``GameSession`` fixtures via a
login helper). No bridge involved — this view reads straight off
``session.narration_records`` and the ``BABYLON_LLM_NARRATOR`` flag.

Contract (``src/frontend/src/types/narration.ts`` /
``src/frontend/src/lib/narration/client.ts``): the wire payload is
``{"status": "offline"|"pending"|"ready", "beats": [...]}`` inside the
standard envelope, with camelCase ``subjectRef`` on each beat.
"""

from __future__ import annotations

import json
import uuid as uuid_mod
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _login_client_with_session(scenario: str = "wayne_county") -> tuple[Client, Any]:
    from game.models import GameSession

    user = User.objects.create_user(username="narrationuser", password="narrationpass123")  # type: ignore[no-untyped-call]
    client = Client()
    client.login(username="narrationuser", password="narrationpass123")
    session = GameSession.objects.create(
        id=uuid_mod.uuid4(),
        player_id=user.id,
        scenario=scenario,
        current_tick=0,
        status="active",
    )
    return client, session


def _narration_url(game_id: Any, **query: str) -> str:
    url = reverse("game:game-narration", kwargs={"game_id": str(game_id)})
    if query:
        url += "?" + "&".join(f"{k}={v}" for k, v in query.items())
    return url


class TestURLRouting:
    def test_narration_url_resolves(self) -> None:
        url = reverse(
            "game:game-narration",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/narration/"


class TestFlagOff:
    """``BABYLON_LLM_NARRATOR`` off (the default) is an honest, labeled
    'offline' — never a fake-empty 'ready' (III.11)."""

    def test_flag_off_returns_offline_with_no_beats(self) -> None:
        client, session = _login_client_with_session()

        response = client.get(_narration_url(session.id))

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["data"] == {"status": "offline", "beats": []}

    def test_flag_off_ignores_existing_records(self) -> None:
        """Even with rows already persisted, flag-off never surfaces them —
        offline means "the narrator isn't on", not "no beats exist yet"."""
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="wire-1",
            scope="tick",
            subject_ref=None,
            headline="H",
            body="B",
            register="wire",
            model_id="m",
            prompt_version="v",
        )

        response = client.get(_narration_url(session.id))

        data = json.loads(response.content)["data"]
        assert data == {"status": "offline", "beats": []}


@pytest.fixture
def _flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from django.conf import settings as django_settings

    monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)


class TestFlagOnEmpty:
    def test_no_records_is_pending(self, _flag_on: None) -> None:
        client, session = _login_client_with_session()

        response = client.get(_narration_url(session.id))

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data == {"status": "pending", "beats": []}


class TestFlagOnSeeded:
    def test_seeded_records_are_ready_with_exact_beat_shape(self, _flag_on: None) -> None:
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=3,
            beat_id="wire-3",
            scope="event",
            subject_ref="evt-42",
            headline="RENT EXTRACTED",
            body="Federal agents breached the WCLF hall.",
            register="wire",
            model_id="@cf/openai/gpt-oss-20b",
            prompt_version="sha256:abc123",
        )

        response = client.get(_narration_url(session.id))

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data["status"] == "ready"
        assert data["beats"] == [
            {
                "id": "wire-3",
                "tick": 3,
                "scope": "event",
                "subjectRef": "evt-42",
                "headline": "RENT EXTRACTED",
                "body": "Federal agents breached the WCLF hall.",
                "register": "wire",
            }
        ]

    def test_degraded_records_are_included_not_hidden(self, _flag_on: None) -> None:
        """III.11 loud failure: a degraded beat is a real beat in the list —
        it is never filtered out just because generation failed."""
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=5,
            beat_id="wire-5",
            scope="tick",
            subject_ref=None,
            headline="NARRATOR DEGRADED",
            body="simulated timeout",
            register="wire",
            model_id="m",
            prompt_version="v",
            degraded=True,
            error="simulated timeout",
        )

        response = client.get(_narration_url(session.id))

        data = json.loads(response.content)["data"]
        assert data["status"] == "ready"
        assert len(data["beats"]) == 1
        beat = data["beats"][0]
        assert beat["headline"] == "NARRATOR DEGRADED"
        assert beat["body"] == "simulated timeout"
        # No extra 'degraded' key leaks onto the wire beat shape — the
        # contract (types/narration.ts NarrationBeat) has exactly these 7 keys.
        assert set(beat.keys()) == {
            "id",
            "tick",
            "scope",
            "subjectRef",
            "headline",
            "body",
            "register",
        }

    def test_since_tick_filters_to_tick_gte(self, _flag_on: None) -> None:
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="wire-1",
            scope="tick",
            headline="early",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )
        NarrationRecord.objects.create(
            session=session,
            tick=5,
            beat_id="wire-5",
            scope="tick",
            headline="late",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )

        response = client.get(_narration_url(session.id, since_tick="3"))

        data = json.loads(response.content)["data"]
        assert [b["headline"] for b in data["beats"]] == ["late"]

    def test_missing_since_tick_defaults_to_zero_returns_all(self, _flag_on: None) -> None:
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=0,
            beat_id="wire-0",
            scope="tick",
            headline="zero",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )

        response = client.get(_narration_url(session.id))

        data = json.loads(response.content)["data"]
        assert [b["headline"] for b in data["beats"]] == ["zero"]

    def test_non_integer_since_tick_is_a_loud_400(self, _flag_on: None) -> None:
        client, session = _login_client_with_session()

        response = client.get(_narration_url(session.id, since_tick="not-a-number"))

        assert response.status_code == 400

    def test_beats_ordered_by_tick_then_beat_id(self, _flag_on: None) -> None:
        from game.models import NarrationRecord

        client, session = _login_client_with_session()
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="wire-1",
            scope="tick",
            headline="w1",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="analysis-1",
            scope="tick",
            headline="a1",
            body="b",
            register="analysis",
            model_id="m",
            prompt_version="v",
        )

        response = client.get(_narration_url(session.id))

        data = json.loads(response.content)["data"]
        assert [b["id"] for b in data["beats"]] == ["analysis-1", "wire-1"]


class TestErrorResponses:
    def test_unknown_game_is_404(self) -> None:
        User.objects.create_user(username="ghostnarrationuser", password="ghostpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="ghostnarrationuser", password="ghostpass123")

        response = client.get(_narration_url(uuid_mod.uuid4()))

        assert response.status_code == 404

    def test_unauthenticated_request_is_401_or_403(self) -> None:
        client = Client()
        response = client.get(_narration_url(uuid_mod.uuid4()))
        assert response.status_code in (401, 403)
