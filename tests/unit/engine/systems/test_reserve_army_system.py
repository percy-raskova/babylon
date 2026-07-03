"""Tests for ReserveArmySystem (Feature 021, US1, System #17)."""

from __future__ import annotations

import networkx as nx

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.models.enums import EventType


def _make_territory_graph(
    territories: dict[str, dict[str, object]],
) -> nx.DiGraph[str]:
    """Build a test graph with territory nodes."""
    graph = BabylonGraph()
    for node_id, attrs in territories.items():
        attrs.setdefault("_node_type", "Territory")
        graph.add_node(node_id, **attrs)
    return graph


def _make_services() -> ServiceContainer:
    """Build minimal service container for reserve army tests."""
    return ServiceContainer.create()


class TestReserveArmySystem:
    """Tests for ReserveArmySystem step logic."""

    def test_name(self) -> None:
        """System has correct name."""
        system = ReserveArmySystem()
        assert system.name == "reserve_army"

    def test_applies_wage_pressure_to_median_wage(self) -> None:
        """Wage pressure reduces median_wage multiplicatively."""
        graph = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.15, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Median wage should be reduced
        assert graph.nodes["wayne"]["median_wage"] < 1000.0
        assert graph.nodes["wayne"]["median_wage"] > 0.0

    def test_higher_ratio_stronger_pressure(self) -> None:
        """Higher reserve ratio produces more wage reduction."""
        graph_high = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.20, "median_wage": 1000.0},
            }
        )
        graph_low = _make_territory_graph(
            {
                "oakland": {"reserve_ratio": 0.05, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph_high, services, {"tick": 1})
        system.step(graph_low, services, {"tick": 1})

        assert graph_high.nodes["wayne"]["median_wage"] < graph_low.nodes["oakland"]["median_wage"]

    def test_zero_ratio_no_change(self) -> None:
        """Zero reserve ratio leaves wage unchanged."""
        graph = _make_territory_graph(
            {
                "oakland": {"reserve_ratio": 0.0, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["oakland"]["median_wage"] == 1000.0

    def test_no_ratio_no_change(self) -> None:
        """Missing reserve_ratio leaves wage unchanged."""
        graph = _make_territory_graph(
            {
                "macomb": {"median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["macomb"]["median_wage"] == 1000.0

    def test_skips_non_territory_nodes(self) -> None:
        """Non-territory nodes are skipped."""
        graph = BabylonGraph()
        graph.add_node("worker1", _node_type="SocialClass", reserve_ratio=0.15, median_wage=500.0)
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Should not have been modified
        assert graph.nodes["worker1"]["median_wage"] == 500.0

    def test_stores_wage_pressure_on_node(self) -> None:
        """Computed wage_pressure is stored on the territory node."""
        graph = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.15, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert "wage_pressure" in graph.nodes["wayne"]
        assert graph.nodes["wayne"]["wage_pressure"] > 0.0

    def test_publishes_event(self) -> None:
        """RESERVE_ARMY_PRESSURE event is published for territories with pressure."""
        graph = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.15, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        events_received: list[object] = []
        services.event_bus.subscribe(
            EventType.RESERVE_ARMY_PRESSURE,
            lambda e: events_received.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(events_received) == 1

    def test_no_event_for_zero_ratio(self) -> None:
        """No event published when reserve ratio is zero."""
        graph = _make_territory_graph(
            {
                "oakland": {"reserve_ratio": 0.0, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        events_received: list[object] = []
        services.event_bus.subscribe(
            EventType.RESERVE_ARMY_PRESSURE,
            lambda e: events_received.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(events_received) == 0

    def test_multiple_territories(self) -> None:
        """System processes all territory nodes."""
        graph = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.15, "median_wage": 1000.0},
                "oakland": {"reserve_ratio": 0.05, "median_wage": 1200.0},
                "macomb": {"reserve_ratio": 0.10, "median_wage": 900.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # All territories should have wage_pressure set
        for node_id in ["wayne", "oakland", "macomb"]:
            assert "wage_pressure" in graph.nodes[node_id]

    def test_wage_pressure_bounded(self) -> None:
        """Wage pressure is bounded by ceiling (no total wage elimination)."""
        graph = _make_territory_graph(
            {
                "wayne": {"reserve_ratio": 0.99, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Even at extreme ratio, wage should remain positive
        assert graph.nodes["wayne"]["median_wage"] > 0.0
        # Wage pressure should not exceed ceiling (0.5)
        assert graph.nodes["wayne"]["wage_pressure"] <= 0.5
