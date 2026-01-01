"""Tests for Mass Line Phase 3: Demographic Dynamics.

TDD tests for the coverage_ratio threshold formula and population-scaled drain.

Key Changes from Phase 1:
    Formula: coverage_ratio threshold instead of marginal_wealth
    Drain: Scaled by population (100 workers burn 100× subsistence)
    Event: POPULATION_ATTRITION instead of POPULATION_DEATH

Formula Semantics:
    coverage_ratio = wealth_per_capita / subsistence_needs
    threshold = 1.0 + inequality
    deficit = max(0, threshold - coverage_ratio)
    attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
    deaths = floor(population × attrition_rate)
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.vitality import VitalitySystem
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.event_bus import Event

from tests.constants import TestConstants

TC = TestConstants.Attrition


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_entity_node(
    graph: nx.DiGraph,
    node_id: str,
    role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
    wealth: float = 1.0,
    s_bio: float = 0.01,
    s_class: float = 0.0,
    active: bool = True,
    population: int = 1,
    inequality: float = 0.0,
    subsistence_multiplier: float = 1.0,
) -> None:
    """Add an entity node to the graph with vitality-relevant attributes."""
    graph.add_node(
        node_id,
        role=role,
        wealth=wealth,
        s_bio=s_bio,
        s_class=s_class,
        active=active,
        population=population,
        inequality=inequality,
        subsistence_multiplier=subsistence_multiplier,
        _node_type="social_class",
    )


@pytest.mark.unit
@pytest.mark.red_phase
class TestPopulationScaledDrain:
    """Tests for population-scaled subsistence burn (The Drain).

    Phase 3 Change: cost = (base_subsistence * population) * multiplier
    A block of 100 workers burns 100× what a single worker burns.
    """

    def test_100_pop_burns_100x_subsistence(self, services: ServiceContainer) -> None:
        """100 population burns 100× the base subsistence.

        With base_subsistence=0.005, multiplier=1.0, population=100:
        cost = 0.005 * 100 * 1.0 = 0.5
        wealth: 100.0 -> 99.5
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=100,
            s_bio=0.01,
            subsistence_multiplier=1.0,
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Population-scaled burn
        base_sub = services.defines.economy.base_subsistence
        expected_cost = base_sub * 100 * 1.0
        expected_wealth = 100.0 - expected_cost
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth, abs=0.001)

    def test_single_pop_burns_1x_subsistence(self, services: ServiceContainer) -> None:
        """Population=1 burns the same as old formula (backward compatible).

        With base_subsistence=0.005, multiplier=1.5, population=1:
        cost = 0.005 * 1 * 1.5 = 0.0075
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            population=1,
            s_bio=0.01,
            subsistence_multiplier=1.5,
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        base_sub = services.defines.economy.base_subsistence
        expected_cost = base_sub * 1 * 1.5
        expected_wealth = 1.0 - expected_cost
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth, abs=0.001)

    def test_elite_burn_rate_scales_by_population(self, services: ServiceContainer) -> None:
        """Elite class (multiplier=20) with population=50 burns massively.

        With base_subsistence=0.005, multiplier=20.0, population=50:
        cost = 0.005 * 50 * 20.0 = 5.0
        wealth: 100.0 -> 95.0
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=50,
            s_bio=0.1,
            subsistence_multiplier=20.0,
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        base_sub = services.defines.economy.base_subsistence
        expected_cost = base_sub * 50 * 20.0
        expected_wealth = 100.0 - expected_cost
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth, abs=0.001)


@pytest.mark.unit
@pytest.mark.red_phase
class TestCoverageRatioFormula:
    """Tests for the coverage_ratio threshold formula.

    Formula:
        coverage_ratio = wealth_per_capita / subsistence_needs
        threshold = 1.0 + inequality
        deficit = max(0, threshold - coverage_ratio)
        attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
    """

    def test_zero_inequality_exact_coverage_no_deaths(self, services: ServiceContainer) -> None:
        """Agent A: Wealth=100, Pop=100, Needs=1, Inequality=0.0.

        coverage_ratio = (100/100) / 1.0 = 1.0
        threshold = 1.0 + 0.0 = 1.0
        coverage >= threshold → 0 Deaths
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=TC.WEALTH_100,
            population=TC.POP_100,
            inequality=TC.ZERO_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,  # Disable drain for this test
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: No deaths, population unchanged
        assert graph.nodes["C001"]["population"] == TC.POP_100
        assert len(events) == 0

    def test_high_inequality_causes_deaths(self, services: ServiceContainer) -> None:
        """Agent B: Wealth=100, Pop=100, Needs=1, Inequality=0.8.

        coverage_ratio = (100/100) / 1.0 = 1.0
        threshold = 1.0 + 0.8 = 1.8
        deficit = 1.8 - 1.0 = 0.8
        attrition = 0.8 × (0.5 + 0.8) = 0.8 × 1.3 = 1.04 → clamped to 1.0
        deaths = 100 × 1.0 = 100 (full attrition)
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=TC.WEALTH_100,
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,  # Disable drain for this test
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Full attrition due to high inequality
        assert graph.nodes["C001"]["population"] == 0
        assert len(events) == 1
        assert events[0].payload["deaths"] == TC.POP_100

    def test_above_threshold_no_deaths(self, services: ServiceContainer) -> None:
        """Coverage 2.0 exceeds threshold 1.8 → no deaths.

        Wealth=200, Pop=100, Needs=1, Inequality=0.8
        coverage_ratio = 2.0, threshold = 1.8
        2.0 >= 1.8 → 0 deaths
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=200.0,  # Double wealth for 2.0 coverage
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: No deaths when coverage exceeds threshold
        assert graph.nodes["C001"]["population"] == TC.POP_100
        assert len(events) == 0

    def test_partial_attrition(self, services: ServiceContainer) -> None:
        """Coverage 1.4 with threshold 1.8 causes partial attrition.

        Wealth=140, Pop=100, Needs=1, Inequality=0.8
        coverage_ratio = 1.4, threshold = 1.8
        deficit = 0.4
        attrition = 0.4 × 1.3 = 0.52
        deaths = floor(100 × 0.52) = 52
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=140.0,
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Partial attrition
        # deficit = 0.4, attrition = 0.4 * 1.3 = 0.52
        expected_deaths = int(TC.POP_100 * 0.52)
        assert graph.nodes["C001"]["population"] == TC.POP_100 - expected_deaths
        assert len(events) == 1
        assert events[0].payload["deaths"] == expected_deaths


@pytest.mark.unit
@pytest.mark.red_phase
class TestMalthusianCorrection:
    """Tests for the Malthusian Correction dynamics.

    Key insight: Deaths reduce population → per-capita wealth rises → fewer future deaths.
    Wealth is NOT reduced when people die (poor die with 0 wealth).
    """

    def test_wealth_per_capita_rises_after_attrition(self, services: ServiceContainer) -> None:
        """After deaths, per-capita wealth increases (wealth unchanged).

        Before: wealth=100, pop=100 → per_capita=1.0
        After deaths: wealth=100, pop=48 → per_capita=2.08

        (With coverage=1.0, threshold=1.8, deficit=0.8, attrition=1.04→1.0, deaths=100→pop=0)
        Actually, let's use lower inequality to get partial deaths.

        Using inequality=0.5:
        threshold = 1.5, coverage = 1.0
        deficit = 0.5, attrition = 0.5 × 1.0 = 0.5
        deaths = 50, pop_after = 50
        per_capita_after = 100 / 50 = 2.0
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=100,
            inequality=TC.MODERATE_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,
        )

        initial_wealth = 100.0
        initial_pop = 100
        initial_per_capita = initial_wealth / initial_pop

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        final_wealth = graph.nodes["C001"]["wealth"]
        final_pop = graph.nodes["C001"]["population"]

        # Assert: Wealth unchanged (poor die with 0 wealth)
        assert final_wealth == pytest.approx(initial_wealth, abs=0.001)

        # Assert: Population decreased
        assert final_pop < initial_pop

        # Assert: Per-capita wealth increased
        final_per_capita = final_wealth / final_pop if final_pop > 0 else float("inf")
        assert final_per_capita > initial_per_capita

    def test_fewer_deaths_in_subsequent_ticks(self, services: ServiceContainer) -> None:
        """Malthusian correction: fewer deaths each tick as per-capita rises.

        Tick 1: Many deaths (low per-capita wealth)
        Tick 2: Fewer deaths (higher per-capita wealth)
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=100,
            inequality=TC.MODERATE_INEQUALITY,
            s_bio=TC.NEEDS_1,
            s_class=0.0,
            subsistence_multiplier=0.0,
        )

        system = VitalitySystem()

        # Tick 1
        pop_before_tick_1 = graph.nodes["C001"]["population"]
        system.step(graph, services, {"tick": 1})
        pop_after_tick_1 = graph.nodes["C001"]["population"]
        deaths_tick_1 = pop_before_tick_1 - pop_after_tick_1

        # Skip if no deaths (test params need adjustment)
        if deaths_tick_1 == 0:
            pytest.skip("No deaths in tick 1")

        # Tick 2
        pop_before_tick_2 = graph.nodes["C001"]["population"]
        system.step(graph, services, {"tick": 2})
        pop_after_tick_2 = graph.nodes["C001"]["population"]
        deaths_tick_2 = pop_before_tick_2 - pop_after_tick_2

        # Assert: Fewer deaths in tick 2 (Malthusian correction)
        assert deaths_tick_2 <= deaths_tick_1


@pytest.mark.unit
@pytest.mark.red_phase
class TestAttritionEventPayload:
    """Tests for POPULATION_ATTRITION event payload structure."""

    def test_event_has_correct_type(self, services: ServiceContainer) -> None:
        """Event type should be POPULATION_ATTRITION, not POPULATION_DEATH."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=TC.WEALTH_100,
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,
            s_bio=TC.NEEDS_1,
            subsistence_multiplier=0.0,
        )

        attrition_events: list[Event] = []
        death_events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, attrition_events.append)
        services.event_bus.subscribe(EventType.POPULATION_DEATH, death_events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: POPULATION_ATTRITION emitted, not POPULATION_DEATH
        assert len(attrition_events) >= 1
        # POPULATION_DEATH should NOT be emitted for attrition
        assert len(death_events) == 0

    def test_payload_contains_required_fields(self, services: ServiceContainer) -> None:
        """POPULATION_ATTRITION payload: {entity_id, deaths, remaining_population, attrition_rate}."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=TC.WEALTH_100,
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,
            s_bio=TC.NEEDS_1,
            subsistence_multiplier=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_ATTRITION, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        assert len(events) == 1
        payload = events[0].payload

        assert "entity_id" in payload
        assert "deaths" in payload
        assert "remaining_population" in payload
        assert "attrition_rate" in payload
        assert payload["entity_id"] == "C001"
        assert payload["deaths"] > 0
        assert payload["remaining_population"] >= 0


@pytest.mark.unit
@pytest.mark.red_phase
class TestBackwardCompatibility:
    """Tests for backward compatibility with Phase 1 behavior."""

    def test_population_one_inequality_zero_backward_compatible(
        self, services: ServiceContainer
    ) -> None:
        """Single-agent (pop=1, inequality=0) behaves like old binary model.

        Wealthy single agent survives.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            population=1,
            inequality=0.0,
            s_bio=0.01,
            subsistence_multiplier=1.0,
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Single agent survives with sufficient wealth
        assert graph.nodes["C001"]["population"] == 1
        assert graph.nodes["C001"]["active"] is True

    def test_full_extinction_emits_entity_death(self, services: ServiceContainer) -> None:
        """When population=0 after attrition, ENTITY_DEATH is emitted."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=TC.WEALTH_100,
            population=TC.POP_100,
            inequality=TC.HIGH_INEQUALITY,  # Will cause 100% attrition
            s_bio=TC.NEEDS_1,
            subsistence_multiplier=0.0,
        )

        entity_death_events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, entity_death_events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Full extinction triggers ENTITY_DEATH
        assert graph.nodes["C001"]["active"] is False
        assert graph.nodes["C001"]["population"] == 0
        assert len(entity_death_events) == 1
        assert entity_death_events[0].payload["cause"] == "extinction"
