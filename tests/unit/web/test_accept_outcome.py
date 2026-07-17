"""Spec-116 Task 5: accept-outcome — the mercy affordance (FR-116-5).

``EngineBridge.accept_outcome`` reads the latest snapshot's persisted
``endgame_progress`` graph attribute (the same channel
:meth:`EngineBridge.get_journal_objectives` reads, see
``tests/unit/web/test_spec095_bridge.py``) and, when the currently recognized
pattern has locked, ends the campaign immediately: it stamps a durable
``ENDGAME`` ``tick_event`` row through the exact same path
:meth:`EngineBridge.resolve_tick` uses for its own horizon-reached
``EndgameEvent`` (FOLLOW-PATTERN: ``tests/unit/web/test_endgame_wiring.py``'s
MagicMock-persistence idiom; ``tests/unit/web/test_spec095_bridge.py``'s
``_pool``/cursor mocking idiom for the durable-readback half).

``TestAcceptOutcomeView`` exercises the Django view + URL wiring
(FOLLOW-PATTERN: ``TestRecoverEndpoint`` in ``tests/unit/web/test_api.py``).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse

from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("cccccccc-dddd-eeee-ffff-000000000000")


def _mock_graph(graph_attrs: dict[str, Any]) -> MagicMock:
    graph = MagicMock()
    graph.graph = graph_attrs
    return graph


def _make_mock_persistence(graph_attrs: dict[str, Any]) -> MagicMock:
    mock = MagicMock()
    mock.hydrate_graph.return_value = _mock_graph(graph_attrs)
    return mock


class TestAcceptOutcomeRequiresLock:
    """No locked pattern -> ValueError('outcome not locked')."""

    def test_raises_when_no_endgame_progress_block_at_all(self) -> None:
        mock_persistence = _make_mock_persistence({"tick": 5})
        bridge = EngineBridge(mock_persistence)

        with pytest.raises(ValueError, match="outcome not locked"):
            bridge.accept_outcome(_SESSION)

    def test_raises_when_pattern_recognized_but_not_yet_locked(self) -> None:
        mock_persistence = _make_mock_persistence(
            {
                "tick": 5,
                "endgame_progress": {
                    "axes": {"fascist_consolidation": 1.0},
                    "pattern": "fascist_consolidation",
                    "since_tick": 5,
                    "horizon_tick": 5200,
                    "locked": False,
                },
            }
        )
        bridge = EngineBridge(mock_persistence)

        with pytest.raises(ValueError, match="outcome not locked"):
            bridge.accept_outcome(_SESSION)

    def test_does_not_persist_anything_when_not_locked(self) -> None:
        mock_persistence = _make_mock_persistence({"tick": 5})
        bridge = EngineBridge(mock_persistence)

        with pytest.raises(ValueError):
            bridge.accept_outcome(_SESSION)

        mock_persistence.persist_tick_events.assert_not_called()


class TestAcceptOutcomeStampsDurableEndgame:
    """Locked fascist pattern at tick T -> accept_outcome persists the ENDGAME
    tick_event row with outcome fascist_consolidation and payload
    {"accepted_at_tick": T}; get_endgame_state now returns that outcome."""

    def _locked_persistence(self) -> MagicMock:
        return _make_mock_persistence(
            {
                "tick": 12,
                "endgame_progress": {
                    "axes": {
                        "revolutionary_victory": 0.1,
                        "ecological_collapse": 0.0,
                        "fascist_consolidation": 1.0,
                        "red_ogv": 0.0,
                        "fragmented_collapse": 0.0,
                    },
                    "pattern": "fascist_consolidation",
                    "since_tick": 10,
                    "horizon_tick": 5200,
                    "locked": True,
                },
            }
        )

    def test_returns_the_locked_pattern_and_tick(self) -> None:
        mock_persistence = self._locked_persistence()
        bridge = EngineBridge(mock_persistence)

        result = bridge.accept_outcome(_SESSION)

        assert result == {
            "outcome": "fascist_consolidation",
            "tick": 12,
            "accepted": True,
        }

    def test_persists_through_the_resolve_tick_tick_event_path(self) -> None:
        mock_persistence = self._locked_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.accept_outcome(_SESSION)

        mock_persistence.persist_tick_events.assert_called_once()
        call_args = mock_persistence.persist_tick_events.call_args
        assert call_args.args[0] == _SESSION
        assert call_args.args[1] == 12
        rows = call_args.args[2]
        assert len(rows) == 1
        row = rows[0]
        assert row["event_type"] == "endgame_reached"
        assert row["detail"]["outcome"] == "fascist_consolidation"
        assert row["detail"]["accepted_at_tick"] == 12

    def test_get_endgame_state_reads_back_the_accepted_outcome(self) -> None:
        """The durable-readback half: once accept_outcome's tick_event row
        exists, get_endgame_state (via _fetch_endgame_event_row's SELECT)
        must report the accepted outcome — FOLLOW-PATTERN:
        test_spec095_bridge.py::test_returns_outcome_when_endgame_fires'
        _pool/cursor mocking idiom."""
        mock_persistence = self._locked_persistence()
        bridge = EngineBridge(mock_persistence)
        bridge.accept_outcome(_SESSION)

        # Simulate the durable row accept_outcome just wrote being read back
        # by a fresh get_endgame_state call (real Postgres would round-trip
        # this row for real; here the mock pool's cursor is wired to return
        # exactly what accept_outcome persisted).
        mock_persistence._pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (
            12,
            {"kind": "endgame_reached", "outcome": "fascist_consolidation", "accepted_at_tick": 12},
            "Babylon falls",
        )
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = cursor
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        mock_persistence._pool.connection.return_value = conn

        result = bridge.get_endgame_state(_SESSION)

        assert result["outcome"] == "fascist_consolidation"
        assert result["tick"] == 12


@pytest.mark.django_db
class TestAcceptOutcomeView:
    """View + URL wiring (FOLLOW-PATTERN: TestRecoverEndpoint in test_api.py)."""

    def test_accept_outcome_url(self) -> None:
        url = reverse(
            "game:game-accept-outcome",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/accept-outcome/"

    def _make_client_and_session(self) -> tuple[Client, Any]:
        import uuid as uuid_mod

        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(username="acceptuser", password="acceptpass")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="acceptuser", password="acceptpass")
        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=12,
            status="active",
        )
        return client, session

    def test_accepts_a_locked_outcome(self) -> None:
        import game.api

        client, session = self._make_client_and_session()

        mock_bridge = MagicMock()
        mock_bridge.accept_outcome.return_value = {
            "outcome": "fascist_consolidation",
            "tick": 12,
            "accepted": True,
        }
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/accept-outcome/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 200
        import json

        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["data"] == {
            "outcome": "fascist_consolidation",
            "tick": 12,
            "accepted": True,
        }

    def test_rejects_when_bridge_reports_not_locked(self) -> None:
        import game.api

        client, session = self._make_client_and_session()

        mock_bridge = MagicMock()
        mock_bridge.accept_outcome.side_effect = ValueError("outcome not locked")
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/accept-outcome/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 400
        import json

        body = json.loads(response.content)
        assert body["status"] == "error"
        assert body["message"] == "outcome not locked"

    def test_unauthenticated_returns_403(self) -> None:
        from django.test import RequestFactory

        from game.api import game_accept_outcome

        factory = RequestFactory()
        request = factory.post("/api/games/some-uuid/accept-outcome/")
        response = game_accept_outcome(request, game_id="some-uuid")
        assert response.status_code == 403

    def test_game_not_found_returns_404(self) -> None:
        import uuid as uuid_mod

        from django.contrib.auth.models import User

        User.objects.create_user(username="nogameuser", password="nogamepass")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="nogameuser", password="nogamepass")

        response = client.post(f"/api/games/{uuid_mod.uuid4()}/accept-outcome/")

        assert response.status_code == 404
