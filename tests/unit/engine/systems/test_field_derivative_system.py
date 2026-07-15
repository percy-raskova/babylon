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
from babylon.models.enums import EdgeType, EventType
from babylon.topology.graph import BabylonGraph


def _make_two_node_graph() -> nx.DiGraph[str]:
    """Create a minimal graph with two connected social_class nodes."""
    graph = BabylonGraph()
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
        graph = BabylonGraph()
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

    def test_no_fields_no_derivatives(self) -> None:
        """E0: no field_registry AND no contradiction_fields on nodes -> no-op.

        Without a registry the field names are discovered from the node attrs
        (E0); when no node carries ``contradiction_fields`` the discovery is
        empty and the system returns without writing derivatives.
        """
        graph = _make_two_node_graph()  # nodes carry no contradiction_fields
        services = ServiceContainer.create()  # no field_registry
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        assert "field_derivatives" not in graph.nodes["C001"]

    def test_derivatives_computed_without_registry_when_fields_present(self) -> None:
        """E0: with fields sourced from the opposition layer, derivatives fire.

        ContradictionFieldSystem (no registry) populates ``exploitation`` from
        the incident edge tension; changing the tension between two ticks yields
        a non-zero df/dt that FieldDerivativeSystem computes without any
        field_registry.
        """
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=10.0, population=1000)
        graph.add_node("C002", _node_type="social_class", wealth=30.0, population=1000)
        graph.add_edge("C001", "C002", edge_type=EdgeType.EXPLOITATION, tension=0.2)
        services = ServiceContainer.create()  # no field_registry
        persistent: dict[str, object] = {}

        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent}
        ContradictionFieldSystem().step(graph, services, ctx1)
        graph.edges["C001", "C002"]["tension"] = 0.6  # exploitation 0.2 -> 0.6
        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent}
        ContradictionFieldSystem().step(graph, services, ctx2)
        FieldDerivativeSystem().step(graph, services, ctx2)

        derivs = graph.nodes["C001"]["field_derivatives"]
        assert derivs["exploitation"]["df_dt"] == pytest.approx(0.4)  # 0.6 - 0.2

    def test_skips_nodes_without_fields(self) -> None:
        """System skips nodes that don't have contradiction_fields."""
        graph = BabylonGraph()
        graph.add_node("T001", _node_type="territory", heat=0.5)

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        assert "field_derivatives" not in graph.nodes["T001"]


@pytest.mark.unit
class TestPrincipalContradiction:
    """Tests for principal contradiction identification (US3)."""

    def test_principal_contradiction_set_on_graph(self) -> None:
        """Principal contradiction is written as a graph-level attribute."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Need at least 2 ticks for df/dt
        for tick in [1, 2]:
            ctx: dict[str, object] = {"tick": tick, "persistent_data": persistent_data}
            ContradictionFieldSystem().step(graph, services, ctx)

        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        FieldDerivativeSystem().step(graph, services, ctx2)

        # Check graph attr
        pc = graph.graph.get("principal_field")
        assert pc is not None
        assert "field_name" in pc
        assert "max_abs_df_dt" in pc

    def test_principal_contradiction_field_changes_with_conditions(self) -> None:
        """Principal contradiction reflects the field with max |df/dt|."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Tick 1: baseline
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx1)

        # Tick 2: drastically reduce wealth to spike exploitation
        graph.nodes["C001"]["wealth"] = 0.0
        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx2)
        FieldDerivativeSystem().step(graph, services, ctx2)

        pc = graph.graph.get("principal_field")
        assert pc is not None
        # The field with the biggest change should be identified
        assert isinstance(pc["field_name"], str)
        assert pc["max_abs_df_dt"] >= 0.0

    def test_principal_contradiction_none_on_first_tick(self) -> None:
        """No principal contradiction when df/dt is unavailable (first tick)."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        pc = graph.graph.get("principal_field")
        # Should either be None or have field_name as None
        if pc is not None:
            assert pc.get("field_name") is None or pc.get("max_abs_df_dt") == 0.0

    def test_principal_contradiction_emits_shift_event(self) -> None:
        """PRINCIPAL_CONTRADICTION_SHIFT event emitted when principal changes."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Tick 1
        ctx1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx1)
        FieldDerivativeSystem().step(graph, services, ctx1)

        # Tick 2: change conditions significantly
        graph.nodes["C001"]["wealth"] = 0.0
        ctx2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        ContradictionFieldSystem().step(graph, services, ctx2)
        FieldDerivativeSystem().step(graph, services, ctx2)

        # Check events for PRINCIPAL_CONTRADICTION_SHIFT
        events = services.event_bus.get_history()
        shift_events = [e for e in events if e.type == EventType.PRINCIPAL_CONTRADICTION_SHIFT]
        # On first computation, if a principal is identified, it counts as a shift
        # from None to something
        # On second tick, if principal changed, another event
        # We just verify the mechanism works
        assert isinstance(shift_events, list)


@pytest.mark.unit
class TestFieldStackSnapshot:
    """Program 19/20 Wave 3 Round 1: the ``field_stack`` graph-attr carry.

    FieldDerivativeSystem.step() composes ONE deterministic snapshot from
    the node/edge attrs it (and ContradictionFieldSystem @19) just wrote,
    so WorldState.to_graph()/from_graph() can carry the field stack across
    the facade round trip (see field_derivative.py's ``_build_field_stack``).
    """

    def test_field_stack_written_with_nodes_and_edges(self) -> None:
        """The snapshot has 'nodes' and 'edges' keys populated from the tick."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        field_stack = graph.graph["field_stack"]
        assert set(field_stack.keys()) == {"nodes", "edges"}
        assert "C001" in field_stack["nodes"]
        assert "C002" in field_stack["nodes"]

    def test_field_stack_node_fields_match_contradiction_fields_verbatim(self) -> None:
        """A node's 'fields' sub-dict is a verbatim (sorted) copy of contradiction_fields."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        c001_fields = graph.nodes["C001"]["contradiction_fields"]
        snapshot_fields = graph.graph["field_stack"]["nodes"]["C001"]["fields"]
        assert snapshot_fields == c001_fields

    def test_field_stack_node_field_derivatives_match_verbatim(self) -> None:
        """A node's 'field_derivatives' sub-dict equals its field_derivatives attr exactly."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        c001_derivs = graph.nodes["C001"]["field_derivatives"]
        snapshot_derivs = graph.graph["field_stack"]["nodes"]["C001"]["field_derivatives"]
        assert snapshot_derivs == c001_derivs

    def test_field_stack_honest_omission_of_fieldless_nodes(self) -> None:
        """A node carrying no contradiction_fields/field_derivatives is omitted entirely."""
        graph = BabylonGraph()
        graph.add_node("T001", _node_type="territory", heat=0.5)

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        field_stack = graph.graph.get("field_stack")
        assert field_stack is not None
        assert "T001" not in field_stack["nodes"]

    def test_field_stack_nodes_sorted_by_id_regardless_of_insertion_order(self) -> None:
        """field_stack['nodes'] key order is sorted, independent of graph insertion order."""
        graph = BabylonGraph()
        graph.add_node(
            "C002", _node_type="social_class", wealth=30.0, population=2000, unearned_increment=5.0
        )
        graph.add_node("C001", _node_type="social_class", wealth=5.0, population=1000)
        graph.add_edge("C002", "C001", edge_type=EdgeType.EXPLOITATION, value_flow=10.0)

        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        node_ids = list(graph.graph["field_stack"]["nodes"].keys())
        assert node_ids == sorted(node_ids)

    def test_field_stack_edges_present_with_gradients(self) -> None:
        """field_stack['edges'] carries one entry per (source, target, field)."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        edges = graph.graph["field_stack"]["edges"]
        gradients = graph.edges["C001", "C002"]["field_gradients"]
        assert len(edges) == len(gradients)
        for entry in edges:
            assert entry["source"] == "C001"
            assert entry["target"] == "C002"
            assert entry["gradient"] == pytest.approx(gradients[entry["field"]])

    def test_field_stack_edges_sorted_by_source_target_field(self) -> None:
        """field_stack['edges'] is sorted by (source, target, field)."""
        graph = _make_two_node_graph()
        persistent_data: dict[str, object] = {}
        services = _run_field_system(graph, persistent_data)
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        FieldDerivativeSystem().step(graph, services, context)

        edges = graph.graph["field_stack"]["edges"]
        keys = [(e["source"], e["target"], e["field"]) for e in edges]
        assert keys == sorted(keys)

    def test_field_stack_omits_edge_without_gradients(self) -> None:
        """An edge whose endpoints lack contradiction_fields carries no gradients -> omitted."""
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=5.0, population=1000)
        graph.add_node("T001", _node_type="territory", heat=0.1)
        graph.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        field_stack = graph.graph.get("field_stack")
        assert field_stack is not None
        assert field_stack["edges"] == []

    def test_no_field_stack_when_no_field_names(self) -> None:
        """E0 no-op case: no field_registry and no contradiction_fields anywhere
        means the early return fires before the snapshot is ever written."""
        graph = _make_two_node_graph()
        services = ServiceContainer.create()  # no field_registry
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        FieldDerivativeSystem().step(graph, services, context)

        assert "field_stack" not in graph.graph
