"""Integration tests for Capital Volume I feedback loops (Feature 021, US4).

Tests that the three Volume I mechanisms produce verified feedback loops:
- Reserve army → median_wage → variable capital suppression
- Dispossession → value transfer → wealth redistribution
- Exploitation mode → visibility → consciousness dynamics
"""

from __future__ import annotations

from babylon.economics.working_day.classifier import DefaultWorkingDayClassifier
from babylon.economics.working_day.types import WorkingDayState
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.kernel.event_bus import Event
from babylon.models.entities.territory import Territory
from babylon.models.enums import EventType, ExploitationMode, SectorType
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph


def _make_detroit_graph() -> BabylonGraph:
    """Build a to_graph-shaped graph modeling Wayne/Oakland/Macomb counties.

    Nodes carry the exact ``_node_type="territory"`` marker production
    writes (``WorldState.to_graph``) — hand-seeded ``"Territory"``
    markers previously masked the Feature-021 case bug. Territory ids
    must match ``^(T[0-9]{3,}|[0-9a-f]{15})$``, so the counties are
    T001=Wayne, T002=Oakland, T003=Macomb.
    """
    state = WorldState(
        tick=0,
        territories={
            # Wayne County — high unemployment, high dispossession
            "T001": Territory(
                id="T001",
                name="Wayne County",
                sector_type=SectorType.RESIDENTIAL,
                reserve_ratio=0.18,
                median_wage=45000.0,
                wealth=500_000_000.0,
                foreclosure_rate=0.08,
                eviction_rate=0.05,
                displacement_rate=0.03,
                concentrated_ownership=0.15,
                absentee_landlord_share=0.20,
            ),
            # Oakland County — lower unemployment, lower dispossession
            "T002": Territory(
                id="T002",
                name="Oakland County",
                sector_type=SectorType.RESIDENTIAL,
                reserve_ratio=0.08,
                median_wage=62000.0,
                wealth=800_000_000.0,
                foreclosure_rate=0.03,
                eviction_rate=0.01,
                displacement_rate=0.01,
                concentrated_ownership=0.08,
                absentee_landlord_share=0.10,
            ),
            # Macomb County — moderate
            "T003": Territory(
                id="T003",
                name="Macomb County",
                sector_type=SectorType.RESIDENTIAL,
                reserve_ratio=0.12,
                median_wage=50000.0,
                wealth=300_000_000.0,
                foreclosure_rate=0.05,
                eviction_rate=0.03,
                displacement_rate=0.02,
                concentrated_ownership=0.10,
                absentee_landlord_share=0.15,
            ),
        },
    )
    return state.to_graph()


class TestReserveArmyWageFeedback:
    """Test reserve army → median_wage feedback loop."""

    def test_wage_suppression_proportional_to_reserve_ratio(self) -> None:
        """Higher reserve ratio produces larger wage reduction."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = ReserveArmySystem()

        wayne_wage_before = graph.nodes["T001"]["median_wage"]
        oakland_wage_before = graph.nodes["T002"]["median_wage"]

        system.step(graph, services, {"tick": 1})

        wayne_wage_after = graph.nodes["T001"]["median_wage"]
        oakland_wage_after = graph.nodes["T002"]["median_wage"]

        # Wayne (18% reserve) should have larger wage reduction than Oakland (8%)
        wayne_reduction = (wayne_wage_before - wayne_wage_after) / wayne_wage_before
        oakland_reduction = (oakland_wage_before - oakland_wage_after) / oakland_wage_before

        assert wayne_reduction > oakland_reduction
        assert wayne_reduction > 0.0
        assert oakland_reduction > 0.0

    def test_multi_tick_wage_suppression_compounds(self) -> None:
        """Wage pressure compounds over multiple ticks."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = ReserveArmySystem()

        initial_wage = graph.nodes["T001"]["median_wage"]

        system.step(graph, services, {"tick": 1})
        after_tick_1 = graph.nodes["T001"]["median_wage"]

        system.step(graph, services, {"tick": 2})
        after_tick_2 = graph.nodes["T001"]["median_wage"]

        assert initial_wage > after_tick_1 > after_tick_2
        assert after_tick_2 > 0.0  # Never reaches zero

    def test_all_territories_get_wage_pressure(self) -> None:
        """All three Detroit metro counties receive wage pressure."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = ReserveArmySystem()

        system.step(graph, services, {"tick": 1})

        for node_id in ["T001", "T002", "T003"]:
            assert "wage_pressure" in graph.nodes[node_id]
            assert graph.nodes[node_id]["wage_pressure"] > 0.0


class TestDispossessionValueTransfer:
    """Test dispossession → value transfer feedback loop."""

    def test_wayne_loses_more_wealth_than_oakland(self) -> None:
        """Wayne County (higher dispossession) loses more wealth."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = DispossessionEventSystem()

        wayne_wealth_before = graph.nodes["T001"]["wealth"]
        oakland_wealth_before = graph.nodes["T002"]["wealth"]

        system.step(graph, services, {"tick": 1})

        wayne_loss = wayne_wealth_before - graph.nodes["T001"]["wealth"]
        oakland_loss = oakland_wealth_before - graph.nodes["T002"]["wealth"]

        # Wayne has higher dispossession intensity → loses more
        assert wayne_loss > oakland_loss
        assert wayne_loss > 0.0

    def test_dispossession_intensity_reflects_rates(self) -> None:
        """Wayne County intensity exceeds Oakland County."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = DispossessionEventSystem()

        system.step(graph, services, {"tick": 1})

        assert (
            graph.nodes["T001"]["dispossession_intensity"]
            > graph.nodes["T002"]["dispossession_intensity"]
        )

    def test_value_transfer_events_published(self) -> None:
        """VALUE_TRANSFER events are published for all active territories."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        system = DispossessionEventSystem()

        events: list[Event] = []
        services.event_bus.subscribe(EventType.VALUE_TRANSFER, lambda e: events.append(e))

        system.step(graph, services, {"tick": 1})

        # All three have dispossession rates > 0 and wealth > 0
        assert len(events) == 3


class TestExploitationModeVisibility:
    """Test exploitation mode → consciousness visibility."""

    def test_absolute_exploitation_more_visible(self) -> None:
        """ABSOLUTE_DOMINANT has higher visibility than RELATIVE_DOMINANT."""
        classifier = DefaultWorkingDayClassifier()

        warehouse = WorkingDayState(
            fips_code="26163",
            naics_sector="48",
            year=2019,
            avg_weekly_hours=50.0,
            labor_intensity_index=0.9,
        )
        software = WorkingDayState(
            fips_code="26163",
            naics_sector="51",
            year=2019,
            avg_weekly_hours=37.0,
            labor_intensity_index=2.0,
        )

        assert classifier.classify(warehouse) == ExploitationMode.ABSOLUTE_DOMINANT
        assert classifier.classify(software) == ExploitationMode.RELATIVE_DOMINANT
        assert classifier.compute_visibility_modifier(
            warehouse
        ) > classifier.compute_visibility_modifier(software)

    def test_detroit_gig_economy_is_absolute(self) -> None:
        """Detroit gig economy: long hours, low intensity = ABSOLUTE."""
        classifier = DefaultWorkingDayClassifier()
        gig = WorkingDayState(
            fips_code="26163",
            naics_sector="48",
            year=2019,
            avg_weekly_hours=55.0,
            labor_intensity_index=0.8,
        )
        assert classifier.classify(gig) == ExploitationMode.ABSOLUTE_DOMINANT
        assert classifier.compute_visibility_modifier(gig) == 1.0


class TestCombinedFeedbackLoop:
    """Test all three mechanisms running together."""

    def test_sequential_system_execution(self) -> None:
        """Reserve army then dispossession produces cumulative effects."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        reserve_system = ReserveArmySystem()
        dispossession_system = DispossessionEventSystem()

        initial_wage = graph.nodes["T001"]["median_wage"]
        initial_wealth = graph.nodes["T001"]["wealth"]

        # Reserve army suppresses wages
        reserve_system.step(graph, services, {"tick": 1})
        assert graph.nodes["T001"]["median_wage"] < initial_wage

        # Dispossession transfers wealth
        dispossession_system.step(graph, services, {"tick": 1})
        assert graph.nodes["T001"]["wealth"] < initial_wealth

    def test_five_tick_simulation(self) -> None:
        """Run both systems for 5 ticks — wages and wealth decline."""
        graph = _make_detroit_graph()
        services = ServiceContainer.create()
        reserve_system = ReserveArmySystem()
        dispossession_system = DispossessionEventSystem()

        initial_wage = graph.nodes["T001"]["median_wage"]
        initial_wealth = graph.nodes["T001"]["wealth"]

        for tick in range(5):
            reserve_system.step(graph, services, {"tick": tick})
            dispossession_system.step(graph, services, {"tick": tick})

        assert graph.nodes["T001"]["median_wage"] < initial_wage
        assert graph.nodes["T001"]["wealth"] < initial_wealth
        # Values should still be positive
        assert graph.nodes["T001"]["median_wage"] > 0.0
        assert graph.nodes["T001"]["wealth"] > 0.0
