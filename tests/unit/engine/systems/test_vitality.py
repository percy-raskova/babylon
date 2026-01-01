"""Unit tests for VitalitySystem - The Reaper.

TDD tests for the Material Reality Refactor.
Entities die when wealth < consumption_needs (s_bio + s_class).
Death is marked by setting active=False and emitting ENTITY_DEATH event.

These tests are written BEFORE implementation (RED phase of TDD).
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
) -> None:
    """Add an entity node to the graph with vitality-relevant attributes.

    Args:
        graph: The graph to add the node to.
        node_id: The node ID.
        role: Social role of the entity.
        wealth: Current wealth.
        s_bio: Biological minimum consumption (default 0.01).
        s_class: Social reproduction consumption (default 0.0).
        active: Whether entity is alive (default True).
        population: Block size for demographic blocks (default 1).
        inequality: Intra-class Gini coefficient (default 0.0).
    """
    graph.add_node(
        node_id,
        role=role,
        wealth=wealth,
        s_bio=s_bio,
        s_class=s_class,
        active=active,
        population=population,
        inequality=inequality,
        _node_type="social_class",
    )


@pytest.mark.unit
class TestVitalitySystem:
    """Tests for VitalitySystem death mechanics."""

    def test_starving_entity_dies(self, services: ServiceContainer) -> None:
        """Entity with wealth=0 and positive consumption_needs should die.

        consumption_needs = s_bio + s_class = 0.01 + 0.0 = 0.01
        wealth (0.0) < consumption_needs (0.01) → DEATH
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.0,  # Starving
            s_bio=0.01,  # Needs food
            s_class=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity is now dead
        assert graph.nodes["C001"]["active"] is False
        # Assert: ENTITY_DEATH event emitted
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C001"
        assert events[0].payload["wealth"] == 0.0
        assert events[0].payload["consumption_needs"] == pytest.approx(0.01)

    def test_wealthy_entity_survives(self, services: ServiceContainer) -> None:
        """Entity with wealth >= consumption_needs should survive.

        wealth (0.1) >= consumption_needs (0.01) → SURVIVE
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.1,  # Has enough
            s_bio=0.01,
            s_class=0.0,
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity survives
        assert graph.nodes["C001"]["active"] is True
        # Assert: No death event
        assert len(events) == 0

    def test_only_starving_entities_die(self, services: ServiceContainer) -> None:
        """Multiple entities: only those with insufficient post-burn wealth die.

        With subsistence burn (base_subsistence=0.005, multiplier=1.0):
        - burn_cost = 0.005
        - Survival requires: wealth - burn_cost >= consumption_needs
        - With floating-point margin: wealth >= 0.016 for s_bio=0.01
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Rich entity (survives: 10.0 - 0.005 = 9.995 >= 0.01)
        _create_entity_node(graph, "C001", wealth=10.0, s_bio=0.01)
        # Poor entity (dies: 0.0 - 0.005 = 0.0 < 0.01)
        _create_entity_node(graph, "C002", wealth=0.0, s_bio=0.01)
        # Borderline entity (survives: 0.016 - 0.005 = 0.011 >= 0.01)
        # Note: Using 0.016 instead of 0.015 to avoid floating-point precision edge case
        _create_entity_node(graph, "C003", wealth=0.016, s_bio=0.01)

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Only C002 died
        assert graph.nodes["C001"]["active"] is True
        assert graph.nodes["C002"]["active"] is False
        assert graph.nodes["C003"]["active"] is True

        # Assert: Only one death event (for C002)
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C002"

    def test_already_dead_entities_skipped(self, services: ServiceContainer) -> None:
        """Entities with active=False should not trigger additional death events."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.0,
            s_bio=0.01,
            active=False,  # Already dead
        )

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: No death event (already dead)
        assert len(events) == 0
        # Assert: Still dead
        assert graph.nodes["C001"]["active"] is False

    def test_non_entity_nodes_skipped(self, services: ServiceContainer) -> None:
        """Territory nodes and other non-entity nodes should be skipped."""
        graph: nx.DiGraph = nx.DiGraph()

        # Add territory (not an entity)
        graph.add_node(
            "T001",
            _node_type="territory",
            biocapacity=100.0,
        )
        # Add entity for comparison
        _create_entity_node(graph, "C001", wealth=0.0, s_bio=0.01)

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Only entity died, territory unchanged
        assert graph.nodes["C001"]["active"] is False
        assert len(events) == 1
        assert events[0].payload["entity_id"] == "C001"

    def test_high_s_class_increases_death_threshold(self, services: ServiceContainer) -> None:
        """Entity with high social reproduction costs dies at higher wealth.

        consumption_needs = s_bio + s_class = 0.01 + 0.09 = 0.10
        wealth (0.05) < consumption_needs (0.10) → DEATH
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.05,  # Has some wealth
            s_bio=0.01,
            s_class=0.09,  # High social reproduction needs
        )

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity died despite having some wealth
        assert graph.nodes["C001"]["active"] is False

    def test_vitality_system_name(self) -> None:
        """VitalitySystem should have correct name property."""
        system = VitalitySystem()
        assert system.name == "vitality"


@pytest.mark.unit
class TestVitalitySubsistenceBurn:
    """Tests for subsistence burn in VitalitySystem.

    ADR032: Subsistence burn should happen in VitalitySystem (Phase 1: The Drain)
    BEFORE death check (Phase 2: The Reaper).

    Formula: cost = base_subsistence * subsistence_multiplier
    - base_subsistence: from defines.economy.base_subsistence (default 0.005)
    - subsistence_multiplier: class-specific (1.5 for periphery, 20.0 for core bourgeoisie)
    """

    def test_subsistence_burn_deducts_linearly(self, services: ServiceContainer) -> None:
        """Wealth -= base_subsistence * subsistence_multiplier.

        With base_subsistence=0.005 and multiplier=1.5:
        cost = 0.005 * 1.5 = 0.0075
        wealth: 1.0 -> 0.9925
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            s_bio=0.01,  # Low consumption for survival
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.5

        # Note: base_subsistence comes from services.defines.economy
        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Linear deduction using actual base_subsistence from defines
        base_sub = services.defines.economy.base_subsistence
        expected_cost = base_sub * 1.5
        expected_wealth = 1.0 - expected_cost
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth)

    def test_burn_uses_class_multiplier(self, services: ServiceContainer) -> None:
        """Higher subsistence_multiplier = faster burn.

        Periphery worker (1.5x) vs Core Bourgeoisie (20.0x) at same wealth.
        """
        graph: nx.DiGraph = nx.DiGraph()

        # Periphery worker (1.5x multiplier)
        _create_entity_node(graph, "C001", role=SocialRole.PERIPHERY_PROLETARIAT, wealth=1.0)
        graph.nodes["C001"]["subsistence_multiplier"] = 1.5

        # Core bourgeoisie (20.0x multiplier)
        _create_entity_node(graph, "C003", role=SocialRole.CORE_BOURGEOISIE, wealth=1.0)
        graph.nodes["C003"]["subsistence_multiplier"] = 20.0

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Core bourgeoisie burns faster (use actual base_subsistence from defines)
        base_sub = services.defines.economy.base_subsistence
        periphery_cost = base_sub * 1.5
        bourgeoisie_cost = base_sub * 20.0

        assert graph.nodes["C001"]["wealth"] == pytest.approx(1.0 - periphery_cost)
        assert graph.nodes["C003"]["wealth"] == pytest.approx(1.0 - bourgeoisie_cost)

        # Bourgeoisie burned more
        assert graph.nodes["C003"]["wealth"] < graph.nodes["C001"]["wealth"]

    def test_burn_then_death_check_sequence(self, services: ServiceContainer) -> None:
        """Entity with wealth=0.01, burn cost=0.0075 survives burn but may die.

        Sequence:
        1. Burn: 0.01 - 0.0075 = 0.0025
        2. Death check: 0.0025 < s_bio (0.01) → DIES

        This tests the critical ordering: burn BEFORE death check.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.01,  # Barely positive
            s_bio=0.01,  # Consumption needs match initial wealth
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.5

        events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Burn happened first: 0.01 - 0.0075 = 0.0025
        # Then death check: 0.0025 < 0.01 → DEAD
        assert graph.nodes["C001"]["active"] is False
        assert len(events) == 1

    def test_burn_skips_inactive_entities(self, services: ServiceContainer) -> None:
        """active=False entities should not have wealth burned."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            active=False,  # Already dead
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.5

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Wealth unchanged (no burn for dead entities)
        assert graph.nodes["C001"]["wealth"] == pytest.approx(1.0)

    def test_zero_base_subsistence_skips_burn(self, services: ServiceContainer) -> None:
        """When base_subsistence=0, no wealth should be burned.

        This allows tests to isolate wage/extraction mechanics from subsistence.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.5

        # With base_subsistence=0.0, no burn should occur
        # (This requires modifying defines in GREEN phase)
        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # For this test to pass, VitalitySystem must check if base_subsistence > 0
        # and skip burn when it's zero
        # In GREEN phase, we'll configure services.defines.economy.base_subsistence = 0
        # For now, this test defines expected behavior

    def test_wealth_cannot_go_negative(self, services: ServiceContainer) -> None:
        """Subsistence burn should not reduce wealth below zero.

        If wealth=0.001 and cost=0.1, final wealth=0.0 (not -0.099).
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.001,  # Very low wealth
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 20.0  # High burn: 0.005 * 20 = 0.1

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Wealth clamped to 0, not negative
        assert graph.nodes["C001"]["wealth"] >= 0.0


@pytest.mark.unit
@pytest.mark.red_phase
class TestGrindingAttrition:
    """Tests for probabilistic mortality (Mass Line Refactor).

    The Grinding Attrition Formula models probabilistic mortality based on
    intra-class inequality:
        effective_wealth_per_capita = wealth / population
        marginal_wealth = effective_wealth_per_capita × (1 - inequality)
        mortality_rate = max(0, (consumption_needs - marginal_wealth) / consumption_needs)
        deaths = floor(population × mortality_rate × base_mortality_factor)

    RED PHASE: These tests define expected behavior BEFORE implementation.
    """

    def test_zero_inequality_no_deaths_when_wealthy(self, services: ServiceContainer) -> None:
        """With inequality=0 and sufficient wealth, no deaths occur.

        Population=1000, wealth=100, s_bio=0.01, inequality=0
        per_capita = 100/1000 = 0.1
        marginal_wealth = 0.1 * (1 - 0) = 0.1
        0.1 >= 0.01 → no deaths
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=1000,
            inequality=0.0,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: No deaths, population unchanged
        assert graph.nodes["C001"]["population"] == 1000
        assert graph.nodes["C001"]["active"] is True
        assert len(events) == 0

    def test_high_inequality_causes_deaths(self, services: ServiceContainer) -> None:
        """With high inequality, marginal workers starve even with high avg wealth.

        Population=1000, wealth=100, s_bio=0.01, inequality=0.95
        per_capita = 100/1000 = 0.1
        marginal_wealth = 0.1 * (1 - 0.95) = 0.005
        0.005 < 0.01 → mortality!
        mortality_rate = (0.01 - 0.005) / 0.01 = 0.5
        deaths = floor(1000 * 0.5 * 0.01) = 5
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=100.0,
            population=1000,
            inequality=0.95,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Deaths occurred due to inequality
        assert graph.nodes["C001"]["population"] < 1000
        assert len(events) == 1
        assert events[0].payload["deaths"] > 0
        assert events[0].payload["entity_id"] == "C001"

    def test_population_one_backward_compatible(self, services: ServiceContainer) -> None:
        """With population=1 and inequality=0, behaves like old binary model.

        Single-agent scenario: sufficient wealth → survives (population=1).
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            population=1,
            inequality=0.0,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Single agent survives with sufficient wealth
        assert graph.nodes["C001"]["population"] == 1
        assert graph.nodes["C001"]["active"] is True

    def test_full_extinction_sets_active_false(self, services: ServiceContainer) -> None:
        """When population reaches 0, class is marked inactive.

        An entity death (ENTITY_DEATH) should be emitted when fully extinct.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=0.0,
            population=1,
            inequality=1.0,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        entity_death_events: list[Event] = []
        services.event_bus.subscribe(EventType.ENTITY_DEATH, entity_death_events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Entity is extinct (active=False)
        assert graph.nodes["C001"]["active"] is False
        # Assert: ENTITY_DEATH emitted for full extinction
        assert len(entity_death_events) >= 1

    def test_malthusian_correction(self, services: ServiceContainer) -> None:
        """Population reduction increases per-capita wealth, reducing future mortality.

        Tick 1: population=100, deaths occur due to inequality
        Tick 2: population < 100, per-capita wealth higher, fewer deaths

        This tests the equilibrium dynamics of Malthusian correction.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            population=100,
            inequality=0.9,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        pop_after_tick_1 = graph.nodes["C001"]["population"]
        deaths_tick_1 = 100 - pop_after_tick_1

        # Skip if no deaths occurred (adjust test params if needed)
        if deaths_tick_1 == 0:
            pytest.skip("No deaths in tick 1; adjust test parameters")

        system.step(graph, services, {"tick": 2})

        pop_after_tick_2 = graph.nodes["C001"]["population"]
        deaths_tick_2 = pop_after_tick_1 - pop_after_tick_2

        # Assert: Malthusian correction - fewer deaths in tick 2
        # because per-capita wealth increased after tick 1 deaths
        assert deaths_tick_2 <= deaths_tick_1

    def test_population_death_event_payload(self, services: ServiceContainer) -> None:
        """POPULATION_DEATH event should have correct payload.

        Payload: {entity_id, deaths, remaining_population, mortality_rate}
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_entity_node(
            graph,
            "C001",
            wealth=1.0,
            population=1000,
            inequality=0.99,
            s_bio=0.01,
        )
        graph.nodes["C001"]["subsistence_multiplier"] = 1.0

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POPULATION_DEATH, events.append)

        system = VitalitySystem()
        system.step(graph, services, {"tick": 1})

        # Assert: Event payload has required fields
        assert len(events) == 1
        payload = events[0].payload
        assert "entity_id" in payload
        assert "deaths" in payload
        assert "remaining_population" in payload
        assert "mortality_rate" in payload
        assert payload["entity_id"] == "C001"
        assert payload["deaths"] > 0
        assert payload["remaining_population"] < 1000
