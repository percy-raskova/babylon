"""Unit tests for AW4-R1 (audit Wave 4 "Topology & the Gramscian Wire").

Deliverable 1: ``EngineBridge.get_org_network`` — the org-network graph
(``OrgNetworkPayload``, ``src/frontend/src/types/game.ts`` ~614-631).
Deliverable 2: ``EngineBridge.get_hypergraph_communities`` — honest-empty
fix for the previously-guaranteed-500 ``GET .../hypergraph/communities/``
route (``HypergraphPayload``, same file ~648-660 — field is ``hyperedges``,
NOT ``communities``).
Deliverable 3: bridge-altitude centrality (per-node degree/betweenness/
closeness) + percolation_ratio (real solidarity giant-component ratio),
both additive keys on the org-network payload.

Uses the real ``wayne_county`` scenario (not mocks) for organization/
territory data — mirrors ``tests/unit/web/test_engine_bridge_inspectors.py``'s
``_wayne_bridge()`` helper. Institutions are added via ``model_copy`` since
no shipped scenario seeds one.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest


def _wayne_bridge() -> tuple[Any, Any]:
    """Real wayne_county scenario graph — organizations ORG001/ORG002,
    real territories, real SOLIDARITY edges (C001<->C004)."""
    from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    graph = state.to_graph()
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = graph
    return EngineBridge(mock_persistence), graph


def _wayne_bridge_with_institution() -> tuple[Any, Any, str]:
    """wayne_county + one hand-built Institution housing ORG001, PRESENCE-
    linked to the same territory ORG001 already occupies (so the resulting
    org-network has a non-trivial connected topology for centrality)."""
    from babylon.models.entities.institution import (
        Institution,
        InternalBalanceOfForces,
        ReproductionMechanism,
    )
    from babylon.models.enums.organizations import ApparatusType
    from babylon.models.enums.social import SocialFunction
    from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    territory_id = state.organizations["ORG001"].territory_ids[0]
    institution = Institution(
        id="INST001",
        name="Test Institution",
        apparatus_type=ApparatusType.RSA_POLICE,
        social_function=SocialFunction.POLICING,
        internal_balance=InternalBalanceOfForces(
            liberal_technocratic=0.34,
            revanchist_fascist=0.33,
            institutionalist_bonapartist=0.33,
        ),
        reproduction=ReproductionMechanism(),
        housed_org_ids=["ORG001"],
        territory_ids=[territory_id],
    )
    state = state.model_copy(update={"institutions": {"INST001": institution}})
    graph = state.to_graph()
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = graph
    return EngineBridge(mock_persistence), graph, territory_id


# --------------------------------------------------------------------- #
# Deliverable 1: get_org_network (EngineBridge)
# --------------------------------------------------------------------- #


@pytest.mark.unit
class TestGetOrgNetworkEngineBridge:
    def test_includes_organizations_institutions_territories(self) -> None:
        bridge, _graph, territory_id = _wayne_bridge_with_institution()

        result = bridge.get_org_network(uuid.uuid4())

        by_id = {n["id"]: n for n in result["nodes"]}
        assert by_id["ORG001"]["type"] == "organization"
        assert by_id["ORG002"]["type"] == "organization"
        assert by_id["INST001"]["type"] == "institution"
        assert by_id[territory_id]["type"] == "territory"

    def test_excludes_social_class_nodes(self) -> None:
        """AW4-R1 verified divergence: OrgNetworkNode.type has no
        "social_class" member — nodes are strictly organization/
        institution/territory, matching the pre-existing view docstring."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_org_network(uuid.uuid4())

        types = {n["type"] for n in result["nodes"]}
        assert types <= {"organization", "institution", "territory"}
        ids = {n["id"] for n in result["nodes"]}
        assert "C001" not in ids  # a real wayne_county social_class id

    def test_edges_carry_mode_as_lowercase_edge_type(self) -> None:
        bridge, _graph, territory_id = _wayne_bridge_with_institution()

        result = bridge.get_org_network(uuid.uuid4())

        edge_by_pair = {(e["source"], e["target"]): e for e in result["edges"]}
        assert edge_by_pair[("ORG001", territory_id)]["mode"] == "presence"
        assert edge_by_pair[("INST001", "ORG001")]["mode"] == "houses"
        assert edge_by_pair[("INST001", territory_id)]["mode"] == "presence"

    def test_territory_filter_restricts_to_orgs_present_there(self) -> None:
        bridge, _graph, territory_id = _wayne_bridge_with_institution()

        result = bridge.get_org_network(uuid.uuid4(), territory_filter=territory_id)

        ids = {n["id"] for n in result["nodes"]}
        assert "ORG001" in ids  # ORG001 operates in territory_id by construction
        assert territory_id in ids
        # ORG002 policed_territory_ids may or may not overlap; the filter
        # must not silently include a territory the request didn't ask for.
        assert all(n["type"] != "territory" or n["id"] == territory_id for n in result["nodes"])

    def test_nodes_and_edges_sorted_deterministically(self) -> None:
        bridge, _graph, _territory_id = _wayne_bridge_with_institution()

        result = bridge.get_org_network(uuid.uuid4())

        node_ids = [n["id"] for n in result["nodes"]]
        assert node_ids == sorted(node_ids)
        edge_keys = [(e["source"], e["target"], e["mode"]) for e in result["edges"]]
        assert edge_keys == sorted(edge_keys)

    def test_tick_reflects_hydrated_state(self) -> None:
        bridge, _graph = _wayne_bridge()

        result = bridge.get_org_network(uuid.uuid4())

        assert result["tick"] == 0


@pytest.mark.unit
class TestGetOrgNetworkStubBridge:
    def test_stub_returns_well_formed_empty_payload(self) -> None:
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        result = stub.get_org_network(uuid.uuid4())

        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["centrality"] == {}
        assert result["percolation_ratio"] is None

    def test_stub_accepts_territory_filter_kwarg(self) -> None:
        """Must not TypeError — api.py's view always passes this kwarg."""
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        result = stub.get_org_network(uuid.uuid4(), territory_filter="T001")

        assert result["nodes"] == []


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrgNetworkAPIView:
    def test_view_returns_envelope(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        import game.api
        from game.engine_bridge import EngineBridge
        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username="orgnetworkuser", password="orgnetworkpass123"
        )
        client = Client()
        client.login(username="orgnetworkuser", password="orgnetworkpass123")
        session = GameSession.objects.create(
            id=uuid.UUID("cccccccc-dddd-eeee-ffff-000000000001"),
            player_id=user.id,
            scenario="wayne_county",
            current_tick=0,
            status="active",
        )
        bridge, graph = _wayne_bridge()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        game.api._bridge_instance = EngineBridge(mock_persistence)

        url = reverse("game:org-network", kwargs={"game_id": str(session.id)})
        response = client.get(url)

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body["data"]
        assert "edges" in body["data"]


# --------------------------------------------------------------------- #
# Deliverable 2: get_hypergraph_communities (EngineBridge + stub)
# --------------------------------------------------------------------- #


@pytest.mark.unit
class TestGetHypergraphCommunitiesEngineBridge:
    def test_returns_honest_empty_hyperedges(self) -> None:
        """Field name is 'hyperedges' (HypergraphPayload, game.ts ~648-651),
        not 'communities' — the real frontend contract, verified."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_hypergraph_communities(uuid.uuid4())

        assert result == {"tick": 0, "hyperedges": []}

    def test_accepts_territory_filter_kwarg(self) -> None:
        """Must not TypeError — api.py's view always passes this kwarg."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_hypergraph_communities(uuid.uuid4(), territory_filter="T001")

        assert result["hyperedges"] == []


@pytest.mark.unit
class TestGetHypergraphCommunitiesStubBridge:
    def test_stub_returns_well_formed_empty_payload(self) -> None:
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        result = stub.get_hypergraph_communities(uuid.uuid4())

        assert result["hyperedges"] == []

    def test_stub_accepts_territory_filter_kwarg(self) -> None:
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        result = stub.get_hypergraph_communities(uuid.uuid4(), territory_filter="T001")

        assert result["hyperedges"] == []


@pytest.mark.unit
@pytest.mark.django_db
class TestGetHypergraphCommunitiesAPIView:
    """Before AW4-R1: GET .../hypergraph/communities/ called a bridge
    method neither bridge implemented -> guaranteed AttributeError -> 500.
    This must now be a clean 200 with an honest-empty envelope."""

    def test_view_returns_envelope_not_500(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        import game.api
        from game.engine_bridge import EngineBridge
        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username="hypergraphuser", password="hypergraphpass123"
        )
        client = Client()
        client.login(username="hypergraphuser", password="hypergraphpass123")
        session = GameSession.objects.create(
            id=uuid.UUID("cccccccc-dddd-eeee-ffff-000000000002"),
            player_id=user.id,
            scenario="wayne_county",
            current_tick=0,
            status="active",
        )
        bridge, graph = _wayne_bridge()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        game.api._bridge_instance = EngineBridge(mock_persistence)

        url = reverse("game:hypergraph-communities", kwargs={"game_id": str(session.id)})
        response = client.get(url)

        assert response.status_code == 200
        assert response.json()["data"]["hyperedges"] == []


# --------------------------------------------------------------------- #
# Deliverable 3: centrality + percolation_ratio
# --------------------------------------------------------------------- #


@pytest.mark.unit
class TestOrgNetworkCentrality:
    def test_centrality_keyed_by_every_returned_node(self) -> None:
        bridge, _graph, _territory_id = _wayne_bridge_with_institution()

        result = bridge.get_org_network(uuid.uuid4())

        node_ids = {n["id"] for n in result["nodes"]}
        assert set(result["centrality"].keys()) == node_ids
        assert all("degree" in v for v in result["centrality"].values())

    def test_empty_network_yields_empty_centrality(self) -> None:
        from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        # No orgs, no institutions, no territories -> empty org-network.
        state = state.model_copy(update={"organizations": {}, "institutions": {}})
        graph = state.to_graph()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_org_network(uuid.uuid4())

        assert result["nodes"] == []
        assert result["centrality"] == {}


@pytest.mark.unit
class TestOrgNetworkPercolationRatio:
    def test_real_value_for_wayne_county(self) -> None:
        """wayne_county seeds a real C001<->C004 SOLIDARITY edge (verified
        via test_engine_bridge_inspectors.py's TestGetInspectorEdge) — the
        ratio must be a real, non-fabricated float in [0, 1], cross-checked
        against the engine's own topology_monitor formula directly."""
        from babylon.engine.topology_monitor import (
            calculate_component_metrics,
            extract_solidarity_subgraph,
        )
        from game.engine_bridge import _build_initial_state_for_scenario

        bridge, graph = _wayne_bridge()

        result = bridge.get_org_network(uuid.uuid4())

        state = _build_initial_state_for_scenario("wayne_county")
        solidarity_graph = extract_solidarity_subgraph(graph)
        _n, _m, expected = calculate_component_metrics(solidarity_graph, len(state.entities))

        assert result["percolation_ratio"] == round(expected, 4)
        assert result["percolation_ratio"] is not None
        assert 0.0 <= result["percolation_ratio"] <= 1.0

    def test_honest_null_when_zero_social_classes(self) -> None:
        from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        state = state.model_copy(update={"entities": {}, "relationships": []})
        graph = state.to_graph()
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_org_network(uuid.uuid4())

        assert result["percolation_ratio"] is None
