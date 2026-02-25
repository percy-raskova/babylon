"""Tests for DispossessionEventSystem (Feature 021, US2, System #18)."""

from __future__ import annotations

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import EventType


def _make_territory_graph(
    territories: dict[str, dict[str, object]],
) -> nx.DiGraph[str]:
    """Build a test graph with territory nodes."""
    graph: nx.DiGraph[str] = nx.DiGraph()
    for node_id, attrs in territories.items():
        attrs.setdefault("_node_type", "Territory")
        attrs.setdefault("fips_code", "26163")
        attrs.setdefault("year", 2010)
        graph.add_node(node_id, **attrs)
    return graph


def _make_services() -> ServiceContainer:
    """Build minimal service container for dispossession tests."""
    return ServiceContainer.create()


class TestDispossessionEventSystem:
    """Tests for DispossessionEventSystem step logic."""

    def test_name(self) -> None:
        """System has correct name."""
        system = DispossessionEventSystem()
        assert system.name == "dispossession_events"

    def test_computes_intensity(self) -> None:
        """Dispossession intensity is computed and stored on node."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "displacement_rate": 0.03,
                    "wealth": 1_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert "dispossession_intensity" in graph.nodes["wayne"]
        assert graph.nodes["wayne"]["dispossession_intensity"] > 0.0

    def test_zero_rates_no_event(self) -> None:
        """Zero dispossession rates produce no events."""
        graph = _make_territory_graph(
            {
                "oakland": {
                    "foreclosure_rate": 0.0,
                    "eviction_rate": 0.0,
                    "displacement_rate": 0.0,
                    "wealth": 1_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        events: list[Event] = []
        services.event_bus.subscribe(
            EventType.DISPOSSESSION_EVENT,
            lambda e: events.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(events) == 0

    def test_value_transfer_reduces_wealth(self) -> None:
        """Dispossession reduces territory wealth."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "displacement_rate": 0.03,
                    "wealth": 1_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["wayne"]["wealth"] < 1_000_000.0

    def test_value_transfer_clamped_to_wealth(self) -> None:
        """Value transfer cannot exceed territory wealth."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.99,
                    "eviction_rate": 0.99,
                    "displacement_rate": 0.99,
                    "wealth": 100.0,  # Very low wealth
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["wayne"]["wealth"] >= 0.0

    def test_publishes_dispossession_event(self) -> None:
        """DISPOSSESSION_EVENT is published for active territories."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "wealth": 1_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        events: list[Event] = []
        services.event_bus.subscribe(
            EventType.DISPOSSESSION_EVENT,
            lambda e: events.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(events) == 1

    def test_publishes_value_transfer_event(self) -> None:
        """VALUE_TRANSFER event is published when wealth > 0."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "wealth": 1_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        events: list[Event] = []
        services.event_bus.subscribe(
            EventType.VALUE_TRANSFER,
            lambda e: events.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(events) == 1
        assert events[0].payload["total_transferred"] > 0.0
        assert events[0].payload["net_received"] > 0.0
        assert events[0].payload["deadweight_loss"] > 0.0

    def test_skips_non_territory_nodes(self) -> None:
        """Non-territory nodes are skipped."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "worker1",
            _node_type="SocialClass",
            foreclosure_rate=0.10,
            wealth=500.0,
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["worker1"]["wealth"] == 500.0

    def test_multiple_territories(self) -> None:
        """System processes all territory nodes with dispossession."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "wealth": 1_000_000.0,
                },
                "oakland": {
                    "foreclosure_rate": 0.02,
                    "eviction_rate": 0.01,
                    "wealth": 2_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert "dispossession_intensity" in graph.nodes["wayne"]
        assert "dispossession_intensity" in graph.nodes["oakland"]
        # Wayne should have higher intensity
        assert (
            graph.nodes["wayne"]["dispossession_intensity"]
            > graph.nodes["oakland"]["dispossession_intensity"]
        )

    def test_no_wealth_no_transfer(self) -> None:
        """Zero wealth means no value transfer event, but dispossession event still fires."""
        graph = _make_territory_graph(
            {
                "wayne": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "wealth": 0.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        transfer_events: list[Event] = []
        disp_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.VALUE_TRANSFER,
            lambda e: transfer_events.append(e),
        )
        services.event_bus.subscribe(
            EventType.DISPOSSESSION_EVENT,
            lambda e: disp_events.append(e),
        )

        system.step(graph, services, {"tick": 1})

        assert len(transfer_events) == 0
        assert len(disp_events) == 1
