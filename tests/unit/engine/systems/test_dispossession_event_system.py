"""Tests for DispossessionEventSystem (Feature 021, US2, System #10)."""

from __future__ import annotations

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.kernel.event_bus import Event
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EventType, SectorType, SocialRole
from babylon.models.world_state import WorldState


def _make_territory_graph(
    territories: dict[str, dict[str, float]],
) -> BabylonGraph:
    """Build a to_graph-shaped test graph with territory nodes.

    Nodes carry the exact ``_node_type="territory"`` marker production
    writes (``WorldState.to_graph``) — hand-seeded ``"Territory"``
    markers previously masked the Feature-021 case bug. The system's
    ``fips_code`` / ``year`` reads fall back to their ``.get()``
    defaults; no test asserts them, so they are not seeded.
    """
    state = WorldState(
        tick=0,
        territories={
            node_id: Territory(
                id=node_id,
                name=f"County {node_id}",
                sector_type=SectorType.RESIDENTIAL,
                **attrs,
            )
            for node_id, attrs in territories.items()
        },
    )
    return state.to_graph()


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
                "T001": {
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

        assert "dispossession_intensity" in graph.nodes["T001"]
        assert graph.nodes["T001"]["dispossession_intensity"] > 0.0

    def test_zero_rates_no_event(self) -> None:
        """Zero dispossession rates produce no events."""
        graph = _make_territory_graph(
            {
                "T002": {
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
                "T001": {
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

        assert graph.nodes["T001"]["wealth"] < 1_000_000.0

    def test_value_transfer_clamped_to_wealth(self) -> None:
        """Value transfer cannot exceed territory wealth."""
        graph = _make_territory_graph(
            {
                "T001": {
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

        assert graph.nodes["T001"]["wealth"] >= 0.0

    def test_publishes_dispossession_event(self) -> None:
        """DISPOSSESSION_EVENT is published for active territories."""
        graph = _make_territory_graph(
            {
                "T001": {
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
                "T001": {
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
        state = WorldState(
            tick=0,
            entities={
                "C001": SocialClass(
                    id="C001",
                    name="Worker",
                    role=SocialRole.PERIPHERY_PROLETARIAT,
                    wealth=500.0,
                ),
            },
        )
        graph = state.to_graph()
        # Decoy Feature-021 input on a social_class node (update_node merges
        # attrs; these tests never call from_graph on this graph).
        graph.update_node("C001", foreclosure_rate=0.10)
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["C001"]["wealth"] == 500.0

    def test_multiple_territories(self) -> None:
        """System processes all territory nodes with dispossession."""
        graph = _make_territory_graph(
            {
                "T001": {
                    "foreclosure_rate": 0.08,
                    "eviction_rate": 0.05,
                    "wealth": 1_000_000.0,
                },
                "T002": {
                    "foreclosure_rate": 0.02,
                    "eviction_rate": 0.01,
                    "wealth": 2_000_000.0,
                },
            }
        )
        services = _make_services()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert "dispossession_intensity" in graph.nodes["T001"]
        assert "dispossession_intensity" in graph.nodes["T002"]
        # T001 should have higher intensity
        assert (
            graph.nodes["T001"]["dispossession_intensity"]
            > graph.nodes["T002"]["dispossession_intensity"]
        )

    def test_no_wealth_no_transfer(self) -> None:
        """Zero wealth means no value transfer event, but dispossession event still fires."""
        graph = _make_territory_graph(
            {
                "T001": {
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
