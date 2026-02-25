"""Tests for FieldDerivativeSystem (Feature 002 - System #15).

TDD RED phase: Tests define the contract for spatial derivatives (gradient,
Laplacian), temporal derivatives (df/dt, d2f/dt2).

Reference: specs/002-dialectical-field-topology/contracts/field_derivative_system.py
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.field_registry import DefaultFieldRegistry
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction_field import ContradictionFieldSystem
from babylon.engine.systems.field_derivative import FieldDerivativeSystem
from babylon.models.enums import EdgeType


def _make_two_node_graph() -> nx.DiGraph[str]:
    """Create a minimal graph with two connected social_class nodes."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node(
        "C001",
        _node_type="social_class",
        wealth=5.0,
        population=1000,
        s_bio=5.0,
        s_class=0.0,
        unearned_increment=0.0,
    )
    graph.add_node(
        "C002",
        _node_type="social_class",
        wealth=30.0,
        population=2000,
        s_bio=5.0,
        s_class=0.0,
        unearned_increment=5.0,
    )
    graph.add_edge(
        "C001",
        "C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=10.0,
    )
    return graph


def _run_field_system(
    graph: nx.DiGraph[str],
    persistent_data: dict[str, object],
) -> ServiceContainer:
    """Run ContradictionFieldSystem to populate fields on nodes."""
    registry = DefaultFieldRegistry.with_defaults()
    services = ServiceContainer.create(field_registry=registry)
    context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
    ContradictionFieldSystem().step(graph, services, context)
    return services


@pytest.mark.unit
class TestFieldDerivativeGradient:
    """Tests for spatial gradient computation on edges."""

    def test_writes_field_gradients_to_edge(self) -> None:
        """System writes field_gradients dict to edges."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        assert "field_gradients" in edge_data
        assert isinstance(edge_data["field_gradients"], dict)

    def test_gradient_is_target_minus_source(self) -> None:
        """Gradient = f(target) - f(source) for each field."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        src_fields = graph.nodes["C001"]["contradiction_fields"]
        tgt_fields = graph.nodes["C002"]["contradiction_fields"]
        gradients = graph.edges["C001", "C002"]["field_gradients"]

        for field_name in src_fields:
            expected = tgt_fields[field_name] - src_fields[field_name]
            assert gradients[field_name] == pytest.approx(expected, abs=1e-9), (
                f"Gradient for {field_name} incorrect"
            )


@pytest.mark.unit
class TestFieldDerivativeLaplacian:
    """Tests for spatial Laplacian computation on nodes."""

    def test_writes_field_derivatives_to_node(self) -> None:
        """System writes field_derivatives dict to nodes."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        derivs = graph.nodes["C001"].get("field_derivatives")
        assert derivs is not None
        assert isinstance(derivs, dict)
        assert "exploitation" in derivs
        assert "laplacian" in derivs["exploitation"]

    def test_laplacian_sum_of_differences(self) -> None:
        """Laplacian(i) = sum_j(f(j) - f(i)) for all neighbors j."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        c001_fields = graph.nodes["C001"]["contradiction_fields"]
        c002_fields = graph.nodes["C002"]["contradiction_fields"]
        c001_derivs = graph.nodes["C001"]["field_derivatives"]

        # C001 has one neighbor C002 (outgoing edge)
        for field_name in c001_fields:
            expected = c002_fields[field_name] - c001_fields[field_name]
            assert c001_derivs[field_name]["laplacian"] == pytest.approx(expected, abs=1e-9)

    def test_isolated_node_laplacian_zero(self) -> None:
        """EC-002: Isolated node (degree 0) gets Laplacian = 0.0."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        derivs = graph.nodes["C001"]["field_derivatives"]
        for field_name in derivs:
            assert derivs[field_name]["laplacian"] == 0.0


@pytest.mark.unit
class TestFieldDerivativeTemporal:
    """Tests for temporal derivative computation."""

    def test_df_dt_none_on_first_tick(self) -> None:
        """EC-001: df/dt is None when < 2 ticks of history."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        derivs = graph.nodes["C001"]["field_derivatives"]
        for field_name in derivs:
            assert derivs[field_name]["df_dt"] is None

    def test_d2f_dt2_none_with_two_ticks(self) -> None:
        """EC-001: d2f/dt2 is None when < 3 ticks of history."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Tick 1
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx1)

        # Tick 2
        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx2)
        FieldDerivativeSystem().step(graph, services, ctx2)

        derivs = graph.nodes["C001"]["field_derivatives"]
        for field_name in derivs:
            # df/dt should be defined (2 ticks)
            assert derivs[field_name]["df_dt"] is not None
            # d2f/dt2 should still be None (need 3 ticks)
            assert derivs[field_name]["d2f_dt2"] is None

    def test_df_dt_computed_after_two_ticks(self) -> None:
        """df/dt = f(t) - f(t-1) after 2 ticks of history."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Tick 1: wealth=5
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx1)

        # Change wealth for tick 2 to cause field change
        graph.nodes["C001"]["wealth"] = 0.0

        # Tick 2: wealth=0 (higher exploitation)
        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx2)
        FieldDerivativeSystem().step(graph, services, ctx2)

        derivs = graph.nodes["C001"]["field_derivatives"]
        # exploitation should have increased, so df_dt > 0
        assert derivs["exploitation"]["df_dt"] is not None
        assert derivs["exploitation"]["df_dt"] != 0.0

    def test_d2f_dt2_computed_after_three_ticks(self) -> None:
        """d2f/dt2 = f(t) - 2*f(t-1) + f(t-2) after 3 ticks."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Three ticks with changing wealth
        for tick, wealth in [(1, 10.0), (2, 5.0), (3, 0.0)]:
            graph.nodes["C001"]["wealth"] = wealth
            ctx: dict[str, object] = {"tick": tick, "persistent_data": persistent_data}
            ContradictionFieldSystem().step(graph, services, ctx)

        # Run derivative system on tick 3
        ctx3: dict[str, object] = {"tick": 3, "persistent_data": persistent_data}
        FieldDerivativeSystem().step(graph, services, ctx3)

        derivs = graph.nodes["C001"]["field_derivatives"]
        # d2f/dt2 should now be defined
        assert derivs["exploitation"]["d2f_dt2"] is not None


@pytest.mark.unit
class TestFieldDerivativeSystemBasic:
    """Basic behavior for FieldDerivativeSystem."""

    def test_system_has_name(self) -> None:
        """System should have the correct name."""
        system = FieldDerivativeSystem()
        assert system.name == "field_derivative"

    def test_no_registry_skips(self) -> None:
        """System is a no-op when field_registry is None."""
        graph = _make_two_node_graph()
        services = ServiceContainer.create()
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        assert "field_derivatives" not in graph.nodes["C001"]

    def test_skips_nodes_without_fields(self) -> None:
        """System skips nodes that don't have contradiction_fields."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("T001", _node_type="territory", heat=0.5)

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        assert "field_derivatives" not in graph.nodes["T001"]
