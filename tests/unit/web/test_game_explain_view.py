"""Unit tests for ``GET /api/games/{id}/explain/`` (spec-113 Lane D).

Django test client + a mocked/real bridge, matching the established
pattern in ``tests/unit/web/test_api.py`` (``game.api._bridge_instance``
patched per-test, ``django_db`` + SQLite in-memory).
"""

from __future__ import annotations

import json
import uuid as uuid_mod
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _login_client_with_session(scenario: str = "wayne_county") -> tuple[Client, Any]:
    from game.models import GameSession

    user = User.objects.create_user(username="explainuser", password="explainpass123")  # type: ignore[no-untyped-call]
    client = Client()
    client.login(username="explainuser", password="explainpass123")
    session = GameSession.objects.create(
        id=uuid_mod.uuid4(),
        player_id=user.id,
        scenario=scenario,
        current_tick=0,
        status="active",
    )
    return client, session


def _explain_url(game_id: Any, **query: str) -> str:
    url = reverse("game:game-explain", kwargs={"game_id": str(game_id)})
    if query:
        url += "?" + "&".join(f"{k}={v}" for k, v in query.items())
    return url


class TestURLRouting:
    def test_explain_url_resolves(self) -> None:
        url = reverse(
            "game:game-explain",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/explain/"


class TestRealBridgeHappyPath:
    """Mocked EngineBridge (``hasattr(bridge, "hydrate_state")`` is True on
    any MagicMock — real state/graph supplied via ``return_value``)."""

    def _wire_bridge(self) -> MagicMock:
        import game.api
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()
        mock_bridge = MagicMock()
        mock_bridge.hydrate_state.return_value = (state, graph)
        game.api._bridge_instance = mock_bridge
        return mock_bridge

    def test_global_scope_metric_returns_full_shape(self) -> None:
        self._wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="exploitation_rate", scope="global"))

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["status"] == "ok"
        data = body["data"]
        assert data["metric"] == "exploitation_rate"
        assert data["scope"] == "global"
        assert set(data.keys()) == {"metric", "scope", "value", "formula", "inputs", "constants"}
        assert set(data["formula"].keys()) == {"name", "expression", "doc"}
        assert data["formula"]["name"] == "exploitation_rate"
        assert isinstance(data["inputs"], list)
        assert data["inputs"][0]["kind"] == "metric"
        assert data["inputs"][0]["ref"] == "value_extraction_ratio"

    def test_org_scope_metric_returns_real_entity_values(self) -> None:
        self._wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="revolution_probability", scope="org:C001")
        )

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data["scope"] == "org:C001"
        names = {i["name"] for i in data["inputs"]}
        assert names == {"cohesion", "repression"}

    def test_terminal_metric_has_no_inputs(self) -> None:
        self._wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="imperial_rent", scope="global"))

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data["inputs"] == []
        assert data["constants"] == []
        assert data["formula"]["name"] is None
        assert isinstance(data["value"], float)

    def test_constants_subset_is_extracted_from_inputs(self) -> None:
        self._wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="consciousness_drift", scope="org:C002")
        )

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        constant_names = {c["name"] for c in data["constants"]}
        assert constant_names == {
            "sensitivity_k",
            "decay_lambda",
            "solidarity_pressure",
            "wage_change",
        }
        assert all(c["kind"] == "constant" for c in data["constants"])


class TestErrorResponses:
    def test_missing_metric_param_is_400(self) -> None:
        import game.api

        game.api._bridge_instance = MagicMock()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, scope="global"))

        assert response.status_code == 400

    def test_missing_scope_param_is_400(self) -> None:
        import game.api

        game.api._bridge_instance = MagicMock()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="exploitation_rate"))

        assert response.status_code == 400

    def test_unknown_metric_is_404_with_valid_metrics_listed(self) -> None:
        import game.api
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        mock_bridge = MagicMock()
        mock_bridge.hydrate_state.return_value = (state, state.to_graph())
        game.api._bridge_instance = mock_bridge
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="not_a_real_metric", scope="global"))

        assert response.status_code == 404
        body = json.loads(response.content)
        assert "exploitation_rate" in body["message"]

    def test_unsupported_scope_kind_string_is_400(self) -> None:
        import game.api

        game.api._bridge_instance = MagicMock()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="exploitation_rate", scope="planet"))

        assert response.status_code == 400

    def test_metric_that_does_not_support_requested_scope_is_400(self) -> None:
        import game.api
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        mock_bridge = MagicMock()
        mock_bridge.hydrate_state.return_value = (state, state.to_graph())
        game.api._bridge_instance = mock_bridge
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="imperial_rent", scope="org:C001"))

        assert response.status_code == 400
        body = json.loads(response.content)
        assert "global" in body["message"]

    def test_unresolvable_org_id_is_404(self) -> None:
        import game.api
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        mock_bridge = MagicMock()
        mock_bridge.hydrate_state.return_value = (state, state.to_graph())
        game.api._bridge_instance = mock_bridge
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="revolution_probability", scope="org:GHOST")
        )

        assert response.status_code == 404

    def test_game_not_found_is_404(self) -> None:
        import game.api

        game.api._bridge_instance = MagicMock()
        User.objects.create_user(username="ghostuser", password="ghostpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="ghostuser", password="ghostpass123")

        response = client.get(
            _explain_url(uuid_mod.uuid4(), metric="exploitation_rate", scope="global")
        )

        assert response.status_code == 404

    def test_unauthenticated_request_is_401_or_403(self) -> None:
        client = Client()
        response = client.get(
            _explain_url(uuid_mod.uuid4(), metric="exploitation_rate", scope="global")
        )
        assert response.status_code in (401, 403)


class TestStubBridgeFallback:
    """No Postgres/engine: ``StubEngineBridge`` has no ``hydrate_state``,
    so the view routes through ``StubEngineBridge.get_explain``."""

    def _wire_stub(self) -> None:
        import game.api
        from game.stub_bridge import StubEngineBridge

        game.api._bridge_instance = StubEngineBridge()

    def test_known_metric_returns_full_shape(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="exploitation_rate", scope="global"))

        assert response.status_code == 200
        data = json.loads(response.content)["data"]
        assert data["metric"] == "exploitation_rate"
        assert set(data.keys()) == {"metric", "scope", "value", "formula", "inputs", "constants"}

    def test_unknown_metric_is_404(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="not_a_real_metric", scope="global"))

        assert response.status_code == 404

    def test_every_real_manifest_metric_is_covered_by_the_stub(self) -> None:
        """Stub catalog parity: same metric names as the real manifest."""
        from game.provenance import METRIC_PROVENANCE
        from game.stub_bridge import _STUB_EXPLAIN_METRICS

        assert set(_STUB_EXPLAIN_METRICS.keys()) == set(METRIC_PROVENANCE.keys())
