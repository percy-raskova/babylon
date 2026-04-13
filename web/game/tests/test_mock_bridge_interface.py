"""Interface completeness tests for MockEngineBridge.

These tests enforce that ``MockEngineBridge`` implements every method that
``api.py`` dispatches to via ``_get_bridge()``.  The failure mode they
guard against is:

    AttributeError: 'MockEngineBridge' object has no attribute 'get_foo'

seen as a 500 on the corresponding API endpoint.

Test methodology:

1. **Interface parity** — extract every ``bridge.<method>`` call from api.py
   and assert MockEngineBridge has a matching callable.
2. **Return shape contracts** — verify non-trivial return structures
   (GeoJSON, summary dicts) have the expected keys.
3. **Endpoint smoke** — for every UI-critical endpoint, issue a real Django
   test-client GET/POST and assert a non-500 status.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import pytest  # type: ignore[import-not-found]

from game.mock_bridge import MockEngineBridge

# ---------------------------------------------------------------------------
# 1. Interface parity — statically extract methods called on `bridge` in api.py
# ---------------------------------------------------------------------------


def _extract_api_bridge_methods() -> set[str]:
    """Parse api.py and extract every ``bridge.<name>(`` call.

    Returns the set of method names the API layer expects on any bridge.
    """
    api_path = Path(__file__).resolve().parent.parent / "api.py"
    source = api_path.read_text()
    return set(re.findall(r"bridge\.([a-z_]+)\(", source))


# Computed once at module level for readability in parametrize IDs.
_REQUIRED_METHODS = sorted(_extract_api_bridge_methods())


@pytest.mark.django_db(transaction=True)
class TestMockBridgeInterfaceParity:
    """Every method called on ``bridge`` in api.py must exist on MockEngineBridge.

    These tests are pure Python introspection — no database access needed.
    """

    @pytest.mark.parametrize("method_name", _REQUIRED_METHODS)  # type: ignore[untyped-decorator]
    def test_method_exists_and_is_callable(self, method_name: str) -> None:
        """Assert bridge has every method the API dispatches to."""
        # Check at class level, not instance level, to avoid DB hits
        assert hasattr(MockEngineBridge, method_name), (
            f"MockEngineBridge is missing '{method_name}' — "
            f"api.py calls bridge.{method_name}() but no such method exists."
        )
        attr = getattr(MockEngineBridge, method_name)
        assert callable(attr), f"MockEngineBridge.{method_name} exists but is not callable."


# ---------------------------------------------------------------------------
# 2. Return shape contracts — verify non-trivial return structures
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestMapSnapshotShape:
    """``get_map_snapshot`` must return a valid GeoJSON FeatureCollection."""

    def setup_method(self) -> None:
        """Create a fresh game session for each test."""
        self.bridge = MockEngineBridge()
        result = self.bridge.create_game(player_id=1, scenario="test")
        self.session_id = uuid.UUID(str(result["id"]))

    def test_returns_feature_collection_type(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id)
        assert result["type"] == "FeatureCollection"

    def test_has_features_list(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id)
        assert isinstance(result["features"], list)
        assert len(result["features"]) > 0

    def test_features_have_properties(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id)
        for feature in result["features"]:
            assert "properties" in feature
            props = feature["properties"]
            assert "heat" in props
            assert "h3_index" in props

    def test_has_metadata(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id)
        assert "metadata" in result
        meta = result["metadata"]
        assert "tick" in meta
        assert "available_metrics" in meta

    def test_zoom_parameter_passed_through(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id, zoom="hex")
        assert result["metadata"]["zoom"] == "hex"

    def test_layer_parameter_passed_through(self) -> None:
        result = self.bridge.get_map_snapshot(self.session_id, layer="consciousness")
        assert result["metadata"]["layer"] == "consciousness"


@pytest.mark.django_db(transaction=True)
class TestGameSummaryShape:
    """``get_game_summary`` must return a dict with required fields."""

    def setup_method(self) -> None:
        """Create a fresh game session for each test."""
        self.bridge = MockEngineBridge()
        result = self.bridge.create_game(player_id=1, scenario="test")
        self.session_id = uuid.UUID(str(result["id"]))

    def test_has_tick(self) -> None:
        result = self.bridge.get_game_summary(self.session_id)
        assert "tick" in result
        assert isinstance(result["tick"], int)

    def test_has_profit_rate(self) -> None:
        result = self.bridge.get_game_summary(self.session_id)
        assert "profit_rate" in result

    def test_has_exploitation_rate(self) -> None:
        result = self.bridge.get_game_summary(self.session_id)
        assert "exploitation_rate" in result

    def test_has_phi(self) -> None:
        result = self.bridge.get_game_summary(self.session_id)
        assert "phi" in result


# ---------------------------------------------------------------------------
# 3. Endpoint smoke tests — every UI-critical endpoint returns non-500
# ---------------------------------------------------------------------------


def _assert_not_500(resp: Any, label: str) -> None:
    """Assert response is not a server error."""
    body = resp.content.decode("utf-8", errors="replace")[:500]
    assert resp.status_code != 500, f"{label} returned 500: {body}"


@pytest.mark.django_db(transaction=True)
class TestApiEndpointSmoke:
    """Each API endpoint must return a non-500 status with MockEngineBridge.

    This tests the *integration* between the API views and the mock bridge:
    a missing method, wrong return type, or unexpected exception will surface
    as a 500 here.
    """

    @pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
    def _setup(self, settings: Any) -> None:
        """Bootstrap a game session and authenticate a test user."""
        settings.BABYLON_MOCK_MODE = True

        from django.contrib.auth.models import User
        from django.test import Client

        self.client = Client()
        user, _ = User.objects.get_or_create(
            username="smoketest",
            defaults={"password": "unusable"},
        )
        user.set_password("smoketest")
        user.save()
        self.client.login(username="smoketest", password="smoketest")

        bridge = MockEngineBridge()
        result = bridge.create_game(player_id=user.pk, scenario="wayne_county_mock")
        self.session_id = str(result["id"])

    # -- Core game loop endpoints --

    def test_state_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/state/")
        _assert_not_500(resp, "state/")

    def test_map_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/map/")
        _assert_not_500(resp, "map/")

    def test_summary_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/summary/")
        _assert_not_500(resp, "summary/")

    def test_actions_available_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/actions/available/")
        _assert_not_500(resp, "actions/available/")

    def test_resolve_endpoint(self) -> None:
        resp = self.client.post(
            f"/api/games/{self.session_id}/resolve/",
            content_type="application/json",
        )
        _assert_not_500(resp, "resolve/")

    # -- Dashboard endpoints --

    def test_timeseries_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/timeseries/")
        _assert_not_500(resp, "timeseries/")

    def test_economy_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/economy/")
        _assert_not_500(resp, "economy/")

    def test_communities_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/communities/")
        _assert_not_500(resp, "communities/")

    def test_organizations_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/organizations/")
        _assert_not_500(resp, "organizations/")

    def test_edges_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/edges/")
        _assert_not_500(resp, "edges/")

    def test_state_apparatus_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/state-apparatus/")
        _assert_not_500(resp, "state-apparatus/")

    def test_journal_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/journal/")
        _assert_not_500(resp, "journal/")

    def test_alerts_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/alerts/")
        _assert_not_500(resp, "alerts/")

    # -- Inspector endpoints --

    def test_inspector_node_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/inspector/node/ent-proletariat/")
        _assert_not_500(resp, "inspector/node/")

    def test_inspector_org_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/inspector/org/org-peoples-front/")
        _assert_not_500(resp, "inspector/org/")

    def test_inspector_hex_endpoint(self) -> None:
        resp = self.client.get(f"/api/games/{self.session_id}/inspector/hex/8428309daffffff/")
        _assert_not_500(resp, "inspector/hex/")
