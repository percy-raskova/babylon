"""Phase E2: ContradictionSystem classifies the fixed-point regime each tick.

The system stashes ``dialectical_regime`` on the graph after ``_maybe_rupture``
and publishes ``LEVEL_TRANSITION`` on the sublation branch. Two symmetric
counties in one state (26) let the capital_labor spatial field be flat-per-state
(sublation) or vary-within-state (crisis) on demand.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.unit


def _two_county_graph() -> nx.DiGraph[str]:
    """Two counties in state 26, each a worker(10)->owner(30) EXPLOITATION edge.

    Bare nodes (no ``_node_type``), following the Grundrisse-cycle fixture: with
    no SOLIDARITY subgraph the atomization gap is 0, so capital_labor (gap 0.5)
    is the unambiguous principal — the opposition the regime probes.
    """
    graph: nx.DiGraph[str] = nx.DiGraph()
    for i, county in enumerate(("26001", "26002"), start=1):
        graph.add_node(f"w{i}", wealth=10.0, county_fips=county)
        graph.add_node(f"o{i}", wealth=30.0, county_fips=county)
        graph.add_edge(f"w{i}", f"o{i}", edge_type=EdgeType.EXPLOITATION, tension=0.0)
    return graph


def _regime(graph: nx.DiGraph[str]) -> str:
    return graph.graph["dialectical_regime"]["regime"]  # type: ignore[no-any-return]


def _level_transitions(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.LEVEL_TRANSITION]


class TestRegimeClassification:
    def test_stable_first_tick_is_reproduction(self) -> None:
        graph = _two_county_graph()
        services = ServiceContainer.create()
        ContradictionSystem().step(graph, services, {"tick": 1})
        assert _regime(graph) == "reproduction"
        assert graph.graph["dialectical_regime"]["opposition"] == "capital_labor"

    def test_symmetric_rising_gap_sublates_and_fires_level_transition(self) -> None:
        graph = _two_county_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})  # baseline, both gaps 0.5
        # Raise BOTH owners equally: both county gaps rise to 0.8 -> the field is
        # flat within state 26 -> resolved at state -> sublation.
        graph.nodes["o1"]["wealth"] = 90.0
        graph.nodes["o2"]["wealth"] = 90.0
        system.step(graph, services, {"tick": 2})

        assert _regime(graph) == "sublation"
        transitions = _level_transitions(services)
        assert len(transitions) == 1
        payload = transitions[0].payload  # type: ignore[attr-defined]
        assert payload["opposition"] == "capital_labor"
        assert payload["from_level"] == "county"
        assert payload["to_level"] == "state"

    def test_asymmetric_rising_gap_is_crisis_no_level_transition(self) -> None:
        graph = _two_county_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})  # baseline
        # Raise only ONE owner: county gaps diverge (0.8 vs 0.5) within state 26
        # -> NOT resolved at any higher level -> crisis.
        graph.nodes["o1"]["wealth"] = 90.0
        system.step(graph, services, {"tick": 2})

        assert _regime(graph) == "crisis"
        assert _level_transitions(services) == []
