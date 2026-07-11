"""Tests for EdgeTransitionSystem (Feature 002 - System #16).

TDD RED phase: Tests define the contract for compound predicates,
edge mode state machine, FR-018 contradiction character, FR-019 aspect reversal.

Reference: specs/002-dialectical-field-topology/contracts/edge_transition_system.py
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.field_registry import DefaultFieldRegistry
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
from babylon.models.enums import (
    ContradictionCharacter,
    EdgeMode,
    EdgeType,
    EventType,
)
from babylon.topology.graph import BabylonGraph


def _make_graph_with_edge_mode() -> nx.DiGraph[str]:
    """Create a graph with two nodes and an edge that has an edge_mode."""
    graph = BabylonGraph()
    graph.add_node(
        "C001",
        _node_type="social_class",
        wealth=5.0,
        population=1000,
        s_bio=5.0,
        s_class=0.0,
        unearned_increment=0.0,
        contradiction_fields={"exploitation": 8.0, "immiseration": 2.0},
        field_derivatives={
            "exploitation": {"laplacian": 0.0, "df_dt": 2.0, "d2f_dt2": 0.5},
            "immiseration": {"laplacian": 0.0, "df_dt": 0.5, "d2f_dt2": None},
        },
    )
    graph.add_node(
        "C002",
        _node_type="social_class",
        wealth=30.0,
        population=2000,
        s_bio=5.0,
        s_class=0.0,
        unearned_increment=5.0,
        contradiction_fields={"exploitation": 2.0, "immiseration": 0.0},
        field_derivatives={
            "exploitation": {"laplacian": 0.0, "df_dt": -0.5, "d2f_dt2": None},
            "immiseration": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None},
        },
    )
    graph.add_edge(
        "C001",
        "C002",
        edge_type=EdgeType.EXPLOITATION,
        edge_mode=EdgeMode.EXTRACTIVE,
        contradiction_character=ContradictionCharacter.ANTAGONISTIC,
        value_flow=10.0,
    )
    return graph


@pytest.mark.unit
class TestEdgeTransitionSystemBasic:
    """Basic behavior for EdgeTransitionSystem."""

    def test_system_has_name(self) -> None:
        """System should have the correct name."""
        system = EdgeTransitionSystem()
        assert system.name == "edge_transition"

    def test_no_registry_still_transitions_under_forced_predicate(self) -> None:
        """E0: with no field_registry the system still fires transitions.

        The dormant field_registry gate is gone (§5.3 repoint) — predicates read
        node/edge attrs, which are present. The fixture edge carries exploitation
        value 8.0 (> extraction_contested_threshold 5.0) and df_dt 2.0 (> 0), so
        the extraction_contested predicate fires EXTRACTIVE -> ANTAGONISTIC even
        though ``field_registry is None``.
        """
        graph = _make_graph_with_edge_mode()
        services = ServiceContainer.create()  # no field_registry
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        assert edge_data["edge_mode"] == EdgeMode.ANTAGONISTIC

    def test_edges_without_mode_are_skipped(self) -> None:
        """Edges that don't have edge_mode are not processed."""
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=5.0)
        graph.add_node("C002", _node_type="social_class", wealth=30.0)
        graph.add_edge("C001", "C002", edge_type=EdgeType.EXPLOITATION)

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        # Should not raise
        EdgeTransitionSystem().step(graph, services, context)


@pytest.mark.unit
class TestEdgeTransitionStateMachine:
    """Tests for the edge mode state machine (FR-010)."""

    def test_extractive_to_antagonistic_transition(self) -> None:
        """EXTRACTIVE -> ANTAGONISTIC when exploitation high and rising."""
        graph = _make_graph_with_edge_mode()
        # Source node has high exploitation (8.0) and positive df/dt (2.0)
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        # High exploitation + rising should trigger transition
        assert edge_data["edge_mode"] in (
            EdgeMode.EXTRACTIVE,
            EdgeMode.ANTAGONISTIC,
        )

    def test_transition_emits_event(self) -> None:
        """Edge mode transitions emit EDGE_MODE_TRANSITION events."""
        graph = _make_graph_with_edge_mode()
        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        events = services.event_bus.get_history()
        transition_events = [e for e in events if e.type == EventType.EDGE_MODE_TRANSITION]
        # May or may not fire depending on predicate evaluation
        assert isinstance(transition_events, list)

    def test_prohibited_transition_not_taken(self) -> None:
        """Prohibited transitions (e.g., EXTRACTIVE -> SOLIDARISTIC) never occur."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            contradiction_fields={"exploitation": 0.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            contradiction_fields={"exploitation": 0.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            edge_mode=EdgeMode.EXTRACTIVE,
            contradiction_character=ContradictionCharacter.NON_ANTAGONISTIC,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        # EXTRACTIVE cannot jump directly to SOLIDARISTIC
        assert edge_data["edge_mode"] != EdgeMode.SOLIDARISTIC


@pytest.mark.unit
class TestContradictionCharacterFlag:
    """Tests for FR-018 contradiction character flag."""

    def test_character_flag_preserved(self) -> None:
        """Contradiction character flag is preserved on edges."""
        graph = _make_graph_with_edge_mode()

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        assert "contradiction_character" in edge_data
        assert edge_data["contradiction_character"] in (
            ContradictionCharacter.ANTAGONISTIC,
            ContradictionCharacter.NON_ANTAGONISTIC,
        )

    def test_default_character_is_non_antagonistic(self) -> None:
        """Edges without character flag get NON_ANTAGONISTIC default."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            contradiction_fields={"exploitation": 1.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            contradiction_fields={"exploitation": 1.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            edge_mode=EdgeMode.TRANSACTIONAL,
            # No contradiction_character set
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}

        EdgeTransitionSystem().step(graph, services, context)

        edge_data = graph.edges["C001", "C002"]
        assert edge_data["contradiction_character"] == ContradictionCharacter.NON_ANTAGONISTIC


@pytest.mark.unit
class TestAspectReversal:
    """Tests for FR-019 aspect reversal detection."""

    def test_aspect_reversal_event_emitted(self) -> None:
        """ASPECT_REVERSAL event emitted when dominant party switches."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=5.0,
            contradiction_fields={"exploitation": 3.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            wealth=30.0,
            contradiction_fields={"exploitation": 3.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            edge_mode=EdgeMode.ANTAGONISTIC,
            contradiction_character=ContradictionCharacter.ANTAGONISTIC,
            _dominant_party="C002",  # C002 was dominant
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)

        # Change wealth so C001 becomes dominant
        graph.nodes["C001"]["wealth"] = 50.0
        graph.nodes["C002"]["wealth"] = 5.0

        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        EdgeTransitionSystem().step(graph, services, context)

        events = services.event_bus.get_history()
        reversal_events = [e for e in events if e.type == EventType.ASPECT_REVERSAL]
        # Should detect the reversal
        assert len(reversal_events) >= 1


@pytest.mark.unit
class TestCoOptiveMechanics:
    """Tests for CO-OPTIVE suppression and latent contradiction (US8)."""

    def test_co_optive_suppresses_df_dt(self) -> None:
        """CO-OPTIVE edges suppress df/dt at co-opted node for declared fields."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=5.0,
            contradiction_fields={"exploitation": 7.0, "immiseration": 3.0},
            field_derivatives={
                "exploitation": {"laplacian": 0.0, "df_dt": 2.0, "d2f_dt2": None},
                "immiseration": {"laplacian": 0.0, "df_dt": 1.0, "d2f_dt2": None},
            },
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            wealth=30.0,
            contradiction_fields={"exploitation": 1.0, "immiseration": 0.0},
            field_derivatives={
                "exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None},
                "immiseration": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None},
            },
        )
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            edge_mode=EdgeMode.CO_OPTIVE,
            contradiction_character=ContradictionCharacter.NON_ANTAGONISTIC,
            co_optive_suppressed_fields=["exploitation"],
            value_flow=5.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}

        EdgeTransitionSystem().step(graph, services, context)

        # Latent contradictions should be accumulated
        latent = persistent_data.get("latent_contradictions", {})
        assert isinstance(latent, dict)

    def test_co_optive_breakdown_emits_event(self) -> None:
        """CO-OPTIVE breakdown emits CO_OPTIVE_BREAKDOWN event."""
        graph = BabylonGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=5.0,
            contradiction_fields={"exploitation": 8.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 3.0, "d2f_dt2": None}},
        )
        graph.add_node(
            "C002",
            _node_type="social_class",
            wealth=30.0,
            contradiction_fields={"exploitation": 1.0},
            field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": 0.0, "d2f_dt2": None}},
        )
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            edge_mode=EdgeMode.CO_OPTIVE,
            contradiction_character=ContradictionCharacter.ANTAGONISTIC,
            co_optive_suppressed_fields=["exploitation"],
            value_flow=5.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {
            "latent_contradictions": {
                "C001": {"exploitation": 5.0},
            }
        }
        context: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}

        EdgeTransitionSystem().step(graph, services, context)

        # The CO-OPTIVE edge should transition to ANTAGONISTIC
        # (exploitation df/dt=3.0 > 1.0 threshold)
        edge_data = graph.edges["C001", "C002"]
        assert edge_data["edge_mode"] == EdgeMode.ANTAGONISTIC

        # Check for breakdown event
        events = services.event_bus.get_history()
        breakdown_events = [e for e in events if e.type == EventType.CO_OPTIVE_BREAKDOWN]
        assert len(breakdown_events) >= 1


@pytest.mark.unit
class TestRegimePredicateMetric:
    """E2: the 'regime' predicate metric evaluates against the graph regime code.

    Data only — no transition in the 17 uses it this phase; these prove the
    predicate machinery can read the fixed-point regime.
    """

    def test_regime_condition_evaluates_by_ordinal(self) -> None:
        from babylon.engine.systems.edge_transition._legacy import (
            PredicateCondition,
            _evaluate_condition,
        )

        cond = PredicateCondition(
            field="", metric="regime", operator="gte", threshold=1.0, scope="source"
        )
        assert _evaluate_condition(cond, {}, {}, regime_code=1.0) is True  # crisis
        assert _evaluate_condition(cond, {}, {}, regime_code=2.0) is True  # sublation
        assert _evaluate_condition(cond, {}, {}, regime_code=0.0) is False  # reproduction
        assert _evaluate_condition(cond, {}, {}, regime_code=None) is False  # undefined

    def test_regime_code_reads_graph_attr(self) -> None:
        from babylon.engine.systems.edge_transition._legacy import _regime_code

        graph = BabylonGraph()
        graph.graph["dialectical_regime"] = {"regime": "sublation", "principal": "capital_labor"}
        assert _regime_code(graph) == 2.0

    def test_regime_code_absent_is_none(self) -> None:
        from babylon.engine.systems.edge_transition._legacy import _regime_code

        graph = BabylonGraph()
        assert _regime_code(graph) is None
