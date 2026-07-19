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


def _wire_bridge(*, acquired_doctrine_ids: tuple[str, ...] = ()) -> MagicMock:
    """Mocked EngineBridge (``hasattr(bridge, "hydrate_state")`` is True on
    any MagicMock — real state/graph supplied via ``return_value``).

    ``acquired_doctrine_ids`` optionally stamps the player org (ORG001)
    past a veil tier -- default ``()`` matches ``wayne_county``'s real
    fresh-game Tier 0 (veil.py's own docstring: "wayne_county's player org
    starts at Tier 0").
    """
    import game.api
    from game.engine_bridge import _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    if acquired_doctrine_ids:
        org = state.organizations["ORG001"].model_copy(
            update={"acquired_doctrine_ids": acquired_doctrine_ids}
        )
        state = state.model_copy(update={"organizations": {**state.organizations, "ORG001": org}})
    graph = state.to_graph()
    mock_bridge = MagicMock()
    mock_bridge.hydrate_state.return_value = (state, graph)
    game.api._bridge_instance = mock_bridge
    return mock_bridge


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

    def _wire_bridge(self, *, acquired_doctrine_ids: tuple[str, ...] = ()) -> MagicMock:
        return _wire_bridge(acquired_doctrine_ids=acquired_doctrine_ids)

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
        """G4 follow-up: imperial_rent's real ledger value requires Tier 1
        (the veil-gate closure below) -- stamp the player org past it so
        this happy-path test keeps demonstrating the real read; the masked
        Tier-0 default is ``TestVeilGating`` below."""
        self._wire_bridge(acquired_doctrine_ids=("class_consciousness", "trade_unionism"))
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


class TestVeilGating:
    """G4 follow-up (owner-adjudicated, same branch as the org-network/
    causal-voice fixes): ``/explain/`` gates value-axis numbers by the
    session's real Veil-of-Money tier, resolved via
    ``engine_bridge._resolve_veil_tier`` -- the same mechanism every other
    G4-audited endpoint uses. ``wayne_county``'s player org starts at
    Tier 0 (unstamped ``_wire_bridge()``), matching every other veil-gate
    test in this codebase (e.g. ``test_engine_bridge_inspectors.py``'s
    ``TestGetInspectorHex``)."""

    def test_tier_zero_masks_imperial_rent(self) -> None:
        _wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="imperial_rent", scope="global"))

        assert response.status_code == 200
        assert json.loads(response.content)["data"]["value"] is None

    def test_tier_two_unlocks_imperial_rent(self) -> None:
        _wire_bridge(acquired_doctrine_ids=("class_consciousness", "trade_unionism"))
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="imperial_rent", scope="global"))

        assert response.status_code == 200
        assert isinstance(json.loads(response.content)["data"]["value"], float)

    def test_tier_zero_masks_exploitation_rate_and_its_metric_input(self) -> None:
        _wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="exploitation_rate", scope="global"))

        data = json.loads(response.content)["data"]
        assert data["value"] is None
        assert data["inputs"][0]["name"] == "exchange_ratio"
        assert data["inputs"][0]["value"] is None

    def test_tier_zero_masks_value_produced_but_not_core_wages(self) -> None:
        """The money-form/value-axis split: core_wages (a wage FLOW) stays
        real below Tier 1; value_produced (literal registry field) masks."""
        _wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="labor_aristocracy_ratio", scope="org:C002")
        )

        data = json.loads(response.content)["data"]
        assert data["value"] is None
        by_name = {i["name"]: i["value"] for i in data["inputs"]}
        assert by_name["value_produced"] is None
        assert by_name["core_wages"] is not None

    def test_tier_zero_never_masks_revolution_probability(self) -> None:
        """Survival Calculus P(S|R) is political, not value-theoretic --
        real even at Tier 0."""
        _wire_bridge()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="revolution_probability", scope="org:C001")
        )

        data = json.loads(response.content)["data"]
        assert data["value"] is not None
        by_name = {i["name"]: i["value"] for i in data["inputs"]}
        assert by_name["cohesion"] is not None
        assert by_name["repression"] is not None


class TestStubBridgeVeilParity:
    """Dev parity (G4 follow-up): the stub's canned ``/explain/`` catalog
    mirrors the same masked-below-Tier-1 shape a real fresh (Tier 0)
    session would show through the view -- ``StubEngineBridge`` has no
    engine to ever advance past ``acquired_ids: []`` (see
    ``get_doctrine_tree``), so its dev fixtures never unlock."""

    def _wire_stub(self) -> None:
        import game.api
        from game.stub_bridge import StubEngineBridge

        game.api._bridge_instance = StubEngineBridge()

    def test_imperial_rent_is_masked(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        response = client.get(_explain_url(session.id, metric="imperial_rent", scope="global"))

        assert json.loads(response.content)["data"]["value"] is None

    def test_exploitation_rate_and_value_extraction_ratio_are_masked(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        for metric in ("exploitation_rate", "value_extraction_ratio"):
            response = client.get(_explain_url(session.id, metric=metric, scope="global"))
            assert json.loads(response.content)["data"]["value"] is None

    def test_labor_aristocracy_ratio_masks_value_produced_but_not_core_wages(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="labor_aristocracy_ratio", scope="org:C002")
        )

        data = json.loads(response.content)["data"]
        assert data["value"] is None
        by_name = {i["name"]: i["value"] for i in data["inputs"]}
        assert by_name["value_produced"] is None
        assert by_name["core_wages"] is not None

    def test_revolution_probability_stays_real(self) -> None:
        self._wire_stub()
        client, session = _login_client_with_session()

        response = client.get(
            _explain_url(session.id, metric="revolution_probability", scope="org:C001")
        )

        data = json.loads(response.content)["data"]
        assert data["value"] is not None
        by_name = {i["name"]: i["value"] for i in data["inputs"]}
        assert by_name["cohesion"] is not None
        assert by_name["repression"] is not None


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
