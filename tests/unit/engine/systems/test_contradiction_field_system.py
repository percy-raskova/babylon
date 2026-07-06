"""Tests for ContradictionFieldSystem (Feature 002 - System #14).

TDD RED phase: Tests define the contract for contradiction field computation.

Reference: specs/002-dialectical-field-topology/contracts/contradiction_field_system.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import networkx as nx
import pytest

from babylon.engine.field_registry import DefaultFieldRegistry
from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction_field import _FIELD_EDGE_TYPES, ContradictionFieldSystem
from babylon.models.enums import EdgeType
from babylon.models.graph import GraphEdge


@pytest.mark.unit
class TestContradictionFieldSystemBasic:
    """Basic behavior for ContradictionFieldSystem."""

    def test_system_has_name(self) -> None:
        """System should have the correct name."""
        system = ContradictionFieldSystem()
        assert system.name == "contradiction_field"

    def test_writes_contradiction_fields_to_node(self) -> None:
        """System writes contradiction_fields dict to social_class nodes."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=20.0,
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"].get("contradiction_fields")
        assert fields is not None
        assert isinstance(fields, dict)
        assert "exploitation" in fields
        assert "immiseration" in fields
        assert "imperial_rent" in fields
        assert "displacement" in fields

    def test_field_values_in_bounds(self) -> None:
        """All field values are in [0.0, 10.0] after normalization (EC-007)."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=0.0,  # Extreme case: destitute
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=100.0,  # Extreme case: high rent
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        for field_name, value in fields.items():
            assert 0.0 <= value <= 10.0, f"Field {field_name} = {value} out of bounds"

    def test_skips_non_social_class_nodes(self) -> None:
        """System only processes social_class nodes, not territory nodes."""
        graph = BabylonGraph()
        graph.add_node("T001", _node_type="territory", heat=0.5)
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        assert "contradiction_fields" not in graph.nodes["T001"]
        assert "contradiction_fields" in graph.nodes["C001"]


@pytest.mark.unit
class TestContradictionFieldHistory:
    """Tests for contradiction_history in persistent_data."""

    def test_stores_history_in_persistent_data(self) -> None:
        """System stores field values in persistent_data contradiction_history."""
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

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        history = persistent_data.get("contradiction_history")
        assert history is not None
        assert "C001" in history  # type: ignore[operator]
        # Each field should have a list with one entry
        c001_history = history["C001"]  # type: ignore[index]
        assert "exploitation" in c001_history

    def test_history_rolling_window_max_3(self) -> None:
        """History window never exceeds 3 entries per node per field."""
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

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        system = ContradictionFieldSystem()

        # Run 5 ticks to test window
        max_ticks = 5
        for tick in range(max_ticks):
            context: dict[str, object] = {
                "tick": tick,
                "persistent_data": persistent_data,
            }
            system.step(graph, services, context)

        history = persistent_data["contradiction_history"]
        c001_history = history["C001"]  # type: ignore[index]
        for _field_name, values in c001_history.items():  # type: ignore[union-attr]
            assert len(values) <= 3, f"History window exceeded 3 for {_field_name}"

    def test_injects_previous_wealth_for_immiseration(self) -> None:
        """System injects _previous_wealth so immiseration can compute decline."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=20.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        system = ContradictionFieldSystem()

        # Tick 1: wealth=20
        context1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        system.step(graph, services, context1)

        # Change wealth for tick 2
        graph.nodes["C001"]["wealth"] = 10.0
        context2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        system.step(graph, services, context2)

        # Immiseration should be positive (wealth dropped from 20 to 10)
        fields = graph.nodes["C001"]["contradiction_fields"]
        assert fields["immiseration"] > 0.0

    def test_exploitation_destitute_worker(self) -> None:
        """Destitute worker (wealth=0) has high exploitation field."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=0.0,
            population=500,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        # Destitute worker should have high exploitation
        assert fields["exploitation"] > 5.0

    def test_wealthy_node_low_exploitation(self) -> None:
        """Wealthy node (wealth > subsistence) has low exploitation."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=50.0,  # Well above subsistence
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        # Wealthy node should have low or zero exploitation
        assert fields["exploitation"] == 0.0


@pytest.mark.unit
class TestContradictionFieldNoRegistry:
    """E0: with no field_registry, fields are sourced from the opposition layer."""

    @staticmethod
    def _opposition_graph() -> nx.DiGraph[str]:
        """C001 with two incident tension edges (0.2, 0.8) + an atomization gap.

        The two edges let a mean-vs-max mutation be caught: mean(0.2, 0.8) = 0.5
        is distinct from max(0.2, 0.8) = 0.8.
        """
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=10.0, population=1000)
        graph.add_node("C002", _node_type="social_class", wealth=30.0, population=1000)
        graph.add_edge("C001", "C002", edge_type=EdgeType.EXPLOITATION, tension=0.2)
        graph.add_edge("C002", "C001", edge_type=EdgeType.WAGES, tension=0.8)
        graph.graph["opposition_states"] = {"atomization": {"gap": 0.3}}
        return graph

    def test_exploitation_field_is_mean_incident_tension_not_max(self) -> None:
        """exploitation = MEAN of incident edge tensions (kills the max mutant)."""
        graph = self._opposition_graph()
        services = ServiceContainer.create()  # no field_registry
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        ContradictionFieldSystem().step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        assert fields["exploitation"] == pytest.approx(0.5)  # mean(0.2, 0.8), not 0.8

    def test_atomization_field_is_global_opposition_gap(self) -> None:
        """atomization = the global atomization opposition gap from @18's snapshot."""
        graph = self._opposition_graph()
        services = ServiceContainer.create()
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        ContradictionFieldSystem().step(graph, services, context)

        assert graph.nodes["C001"]["contradiction_fields"]["atomization"] == pytest.approx(0.3)

    def test_history_window_populated_without_registry(self) -> None:
        """The 3-tick rolling history is written on the opposition-source path too."""
        graph = self._opposition_graph()
        services = ServiceContainer.create()
        persistent: dict[str, object] = {}

        for tick in (1, 2):
            ctx: dict[str, object] = {"tick": tick, "persistent_data": persistent}
            ContradictionFieldSystem().step(graph, services, ctx)

        history = persistent["contradiction_history"]["C001"]
        assert history["exploitation"] == [pytest.approx(0.5), pytest.approx(0.5)]

    def test_no_edges_no_snapshot_writes_zero_fields(self) -> None:
        """Absent edges/snapshot: fields still written (not skipped), all zero."""
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=10.0, population=1000)
        services = ServiceContainer.create()
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        ContradictionFieldSystem().step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        assert fields == {"exploitation": 0.0, "atomization": 0.0}


@pytest.mark.unit
class TestContradictionFieldTensionIndex:
    """O(N+M) tension-index optimization for the opposition-source path.

    The original ``_step_from_oppositions`` called ``_incident_tension_mean``
    PER social_class node, each call scanning all M field edges of 3 types —
    O(N x M) at national scale (>30 min/tick). The refactor builds the
    per-node tension index in a SINGLE pass over edges (O(N+M)).
    """

    @staticmethod
    def _populate_field_graph(graph: BabylonGraph) -> None:
        """Add 5 social_class nodes + 4 field edges spanning all 3 field types.

        Edge tension means per node (verifies mean-not-max AND cross-type
        aggregation AND per-node isolation):
            C000: edges 1,2,4 incident -> mean(0.2, 0.8, 0.4) = 0.4667
            C001: edges 1,2 incident   -> mean(0.2, 0.8)       = 0.5
            C002: edges 3,4 incident   -> mean(0.6, 0.4)       = 0.5
            C003: edge 3 incident      -> mean(0.6)            = 0.6
            C004: no incident edges    -> 0.0
        """
        for i in range(5):
            graph.add_node(
                f"C{i:03d}",
                _node_type="social_class",
                wealth=10.0,
                population=1000,
            )
        graph.add_edge("C000", "C001", edge_type=EdgeType.EXPLOITATION, tension=0.2)
        graph.add_edge("C001", "C000", edge_type=EdgeType.WAGES, tension=0.8)
        graph.add_edge("C002", "C003", edge_type=EdgeType.TENANCY, tension=0.6)
        graph.add_edge("C000", "C002", edge_type=EdgeType.EXPLOITATION, tension=0.4)

    def test_per_node_exploitation_is_mean_of_incident_tensions(self) -> None:
        """Each node's exploitation field = mean of its incident tensions."""
        graph = BabylonGraph()
        self._populate_field_graph(graph)
        services = ServiceContainer.create()
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        ContradictionFieldSystem().step(graph, services, context)

        expected = {
            "C000": pytest.approx(0.4666667, abs=1e-6),
            "C001": pytest.approx(0.5),
            "C002": pytest.approx(0.5),
            "C003": pytest.approx(0.6),
            "C004": pytest.approx(0.0),
        }
        for node_id, want in expected.items():
            got = graph.nodes[node_id]["contradiction_fields"]["exploitation"]
            assert got == want, f"{node_id}: expected {want}, got {got}"

    def test_step_scans_edges_once_not_per_node(self) -> None:
        """O(N+M) contract: query_edges called once per field edge type.

        The O(N x M) per-node scan calls query_edges 3 * N times (3 field
        edge types, once per node). The single-pass index calls it exactly
        len(_FIELD_EDGE_TYPES) times regardless of node count. This is the
        algorithmic-complexity regression gate.
        """
        graph = _QueryEdgesCountingGraph()
        self._populate_field_graph(graph)
        services = ServiceContainer.create()
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        ContradictionFieldSystem().step(graph, services, context)

        # 5 nodes x 3 edge types = 15 calls under the old O(N x M) scan;
        # the index build scans each edge type exactly once (3 calls).
        assert graph.query_edges_calls <= len(_FIELD_EDGE_TYPES), (
            f"Expected <= {len(_FIELD_EDGE_TYPES)} query_edges calls (single "
            f"pass), got {graph.query_edges_calls} (per-node scan regression)"
        )


class _QueryEdgesCountingGraph(BabylonGraph):
    """BabylonGraph subclass counting query_edges calls (complexity test only).

    A subclass (not a wrapper) so it remains a structural
    :class:`GraphProtocol` and ``SystemBase._wrap_graph`` passes it through
    unchanged. Only ``query_edges`` is intercepted; all other GraphProtocol
    methods are inherited verbatim from :class:`BabylonGraph`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.query_edges_calls: int = 0

    def query_edges(
        self,
        edge_type: str | None = None,
        predicate: Callable[[GraphEdge], bool] | None = None,
        min_weight: float | None = None,
        max_weight: float | None = None,
    ) -> Iterator[GraphEdge]:
        self.query_edges_calls += 1
        return super().query_edges(
            edge_type=edge_type,
            predicate=predicate,
            min_weight=min_weight,
            max_weight=max_weight,
        )
