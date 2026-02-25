"""Integration tests for Dialectical Field Topology (Feature 002).

Tests the full pipeline: ContradictionFieldSystem -> FieldDerivativeSystem
-> EdgeTransitionSystem running together across multiple ticks.

Reference: US7 (Detroit empirical validation pattern)
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.field_registry import DefaultFieldRegistry
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction_field import ContradictionFieldSystem
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
from babylon.engine.systems.field_derivative import FieldDerivativeSystem
from babylon.models.enums import ContradictionCharacter, EdgeMode, EdgeType


def _make_detroit_metro_graph() -> nx.DiGraph[str]:
    """Create a stylized Detroit metro area graph.

    Wayne County (proletariat): high exploitation, declining wealth
    Oakland County (petit bourgeoisie): low exploitation, stable wealth
    """
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Wayne County - proletariat (auto workers)
    graph.add_node(
        "wayne_proletariat",
        _node_type="social_class",
        wealth=8.0,
        population=1500,
        s_bio=6.0,
        s_class=3.0,
        unearned_increment=0.0,
        organization=0.3,
    )

    # Oakland County - petit bourgeoisie (suburban professionals)
    graph.add_node(
        "oakland_petty_b",
        _node_type="social_class",
        wealth=45.0,
        population=800,
        s_bio=4.0,
        s_class=1.0,
        unearned_increment=5.0,
        organization=0.1,
    )

    # Exploitation edge: Oakland extracts from Wayne
    graph.add_edge(
        "wayne_proletariat",
        "oakland_petty_b",
        edge_type=EdgeType.EXPLOITATION,
        edge_mode=EdgeMode.EXTRACTIVE,
        contradiction_character=ContradictionCharacter.ANTAGONISTIC,
        value_flow=10.0,
    )

    return graph


@pytest.mark.integration
class TestFieldTopologyMultiTick:
    """Multi-tick integration tests for the full field topology pipeline."""

    def test_three_tick_pipeline(self) -> None:
        """Run 3 systems across 3 ticks, verify data propagation."""
        graph = _make_detroit_metro_graph()
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        field_sys = ContradictionFieldSystem()
        deriv_sys = FieldDerivativeSystem()
        edge_sys = EdgeTransitionSystem()

        max_ticks = 3
        for tick in range(1, max_ticks + 1):
            ctx: dict[str, object] = {"tick": tick, "persistent_data": persistent_data}
            field_sys.step(graph, services, ctx)
            deriv_sys.step(graph, services, ctx)
            edge_sys.step(graph, services, ctx)

        # After 3 ticks, contradiction_fields should exist
        wayne = graph.nodes["wayne_proletariat"]
        assert "contradiction_fields" in wayne
        assert "field_derivatives" in wayne

        # Wayne should have high exploitation (low wealth relative to needs)
        assert wayne["contradiction_fields"]["exploitation"] > 0.0

        # field_derivatives should have temporal values after 3 ticks
        exploitation_deriv = wayne["field_derivatives"]["exploitation"]
        assert "laplacian" in exploitation_deriv
        assert "df_dt" in exploitation_deriv
        assert "d2f_dt2" in exploitation_deriv

    def test_immiseration_increases_with_wealth_decline(self) -> None:
        """Declining wealth produces positive immiseration field."""
        graph = _make_detroit_metro_graph()
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        field_sys = ContradictionFieldSystem()

        # Tick 1: baseline
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        field_sys.step(graph, services, ctx1)

        # Decline wealth for tick 2
        graph.nodes["wayne_proletariat"]["wealth"] = 3.0

        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        field_sys.step(graph, services, ctx2)

        fields = graph.nodes["wayne_proletariat"]["contradiction_fields"]
        assert fields["immiseration"] > 0.0

    def test_principal_contradiction_identified(self) -> None:
        """Principal contradiction is identified after 2+ ticks."""
        graph = _make_detroit_metro_graph()
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        field_sys = ContradictionFieldSystem()
        deriv_sys = FieldDerivativeSystem()

        # Tick 1
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        field_sys.step(graph, services, ctx1)
        deriv_sys.step(graph, services, ctx1)

        # Change conditions for tick 2
        graph.nodes["wayne_proletariat"]["wealth"] = 1.0

        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        field_sys.step(graph, services, ctx2)
        deriv_sys.step(graph, services, ctx2)

        pc = graph.graph.get("principal_contradiction")
        assert pc is not None
        assert pc["field_name"] is not None

    def test_edge_gradients_across_exploitation_edge(self) -> None:
        """Edge gradients capture exploitation differential between counties."""
        graph = _make_detroit_metro_graph()
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        ctx: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx)
        FieldDerivativeSystem().step(graph, services, ctx)

        edge_data = graph.edges["wayne_proletariat", "oakland_petty_b"]
        assert "field_gradients" in edge_data

        # Exploitation gradient should be negative (Wayne has higher exploitation)
        wayne_exploit = graph.nodes["wayne_proletariat"]["contradiction_fields"]["exploitation"]
        oakland_exploit = graph.nodes["oakland_petty_b"]["contradiction_fields"]["exploitation"]
        expected_gradient = oakland_exploit - wayne_exploit
        assert edge_data["field_gradients"]["exploitation"] == pytest.approx(
            expected_gradient, abs=1e-9
        )
