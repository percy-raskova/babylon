"""Tests for ReserveArmySystem (Feature 021, US1, System #5)."""

from __future__ import annotations

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.reserve_army import ReserveArmySystem
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
    markers previously masked the Feature-021 case bug.
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
                "T001": {"reserve_ratio": 0.15, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Median wage should be reduced
        assert graph.nodes["T001"]["median_wage"] < 1000.0
        assert graph.nodes["T001"]["median_wage"] > 0.0

    def test_higher_ratio_stronger_pressure(self) -> None:
        """Higher reserve ratio produces more wage reduction."""
        graph_high = _make_territory_graph(
            {
                "T001": {"reserve_ratio": 0.20, "median_wage": 1000.0},
            }
        )
        graph_low = _make_territory_graph(
            {
                "T002": {"reserve_ratio": 0.05, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph_high, services, {"tick": 1})
        system.step(graph_low, services, {"tick": 1})

        assert graph_high.nodes["T001"]["median_wage"] < graph_low.nodes["T002"]["median_wage"]

    def test_zero_ratio_no_change(self) -> None:
        """Zero reserve ratio leaves wage unchanged."""
        graph = _make_territory_graph(
            {
                "T002": {"reserve_ratio": 0.0, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["T002"]["median_wage"] == 1000.0

    def test_no_ratio_no_change(self) -> None:
        """Default (zero) reserve_ratio leaves wage unchanged."""
        graph = _make_territory_graph(
            {
                "T003": {"median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert graph.nodes["T003"]["median_wage"] == 1000.0

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
        # Decoy Feature-021 inputs on a social_class node (update_node merges
        # attrs; these tests never call from_graph on this graph).
        graph.update_node("C001", reserve_ratio=0.15, median_wage=500.0)
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Should not have been modified
        assert graph.nodes["C001"]["median_wage"] == 500.0

    def test_stores_wage_pressure_on_node(self) -> None:
        """Computed wage_pressure is stored on the territory node."""
        graph = _make_territory_graph(
            {
                "T001": {"reserve_ratio": 0.15, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        assert "wage_pressure" in graph.nodes["T001"]
        assert graph.nodes["T001"]["wage_pressure"] > 0.0

    def test_publishes_event(self) -> None:
        """RESERVE_ARMY_PRESSURE event is published for territories with pressure."""
        graph = _make_territory_graph(
            {
                "T001": {"reserve_ratio": 0.15, "median_wage": 1000.0},
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
                "T002": {"reserve_ratio": 0.0, "median_wage": 1000.0},
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
                "T001": {"reserve_ratio": 0.15, "median_wage": 1000.0},
                "T002": {"reserve_ratio": 0.05, "median_wage": 1200.0},
                "T003": {"reserve_ratio": 0.10, "median_wage": 900.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # All territories should have wage_pressure set
        for node_id in ["T001", "T002", "T003"]:
            assert "wage_pressure" in graph.nodes[node_id]

    def test_wage_pressure_bounded(self) -> None:
        """Wage pressure is bounded by ceiling (no total wage elimination)."""
        graph = _make_territory_graph(
            {
                "T001": {"reserve_ratio": 0.99, "median_wage": 1000.0},
            }
        )
        services = _make_services()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        # Even at extreme ratio, wage should remain positive
        assert graph.nodes["T001"]["median_wage"] > 0.0
        # Wage pressure should not exceed ceiling (0.5)
        assert graph.nodes["T001"]["wage_pressure"] <= 0.5
