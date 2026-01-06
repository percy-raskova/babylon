"""Scenario tests for long-run entity decay and zombie prevention.

Sprint 1.X Deliverable 2: High-Fidelity State.
Pain Point #6: "Zombie" bugs where entities decay asymptotically but never die.

These tests verify that entities with consumption > production will
eventually die, and not persist indefinitely in a zombie state.
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SocialClass, SocialRole
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState

# Maximum ticks before we consider the test a failure
MAX_TICKS_STARVATION = 1000


@pytest.mark.scenario
class TestStarvationChamber:
    """Tests for entity death under pure starvation conditions.

    The "Starvation Chamber" scenario isolates an entity with:
    - No production (no income edges)
    - Consumption > 0 (s_bio + s_class > 0)
    - Starting wealth > 0

    The entity MUST die within a reasonable number of ticks.
    If it survives indefinitely, that's a zombie bug.
    """

    @pytest.mark.red_phase  # TDD RED: Test assumptions don't match VitalitySystem
    def test_isolated_entity_eventually_dies(self) -> None:
        """Entity with consumption > production must die eventually.

        Starvation Chamber scenario:
        - Single entity with no income (no relationships)
        - Consumption needs > 0 (s_bio=0.05, s_class=0.05 = 0.10 per tick)
        - Starting wealth = 10.0 (enough for ~100 ticks at base_subsistence)
        - Should be marked inactive (dead) before MAX_TICKS

        This is the primary test for Pain Point #6.

        TDD RED PHASE NOTE:
        Test assumes s_bio+s_class is the burn rate, but VitalitySystem actually uses
        base_subsistence × population (0.0005 × 10 = 0.005/tick). Additionally, death
        only triggers for population=1 entities (starvation check). This test needs
        redesign to align with actual VitalitySystem behavior.
        """
        # Create isolated entity with consumption needs
        prisoner = SocialClass(
            id="C001",
            name="Prisoner",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=10.0,  # Starting wealth
            s_bio=0.05,  # Biological consumption
            s_class=0.05,  # Social consumption
            population=10,
            inequality=0.0,  # Equal distribution
            active=True,
        )

        state = WorldState(
            tick=0,
            entities={"C001": prisoner},
            # No relationships = no income
        )
        config = SimulationConfig()
        sim = Simulation(state, config)

        death_tick: int | None = None

        for tick in range(MAX_TICKS_STARVATION):
            current_state = sim.step()
            entity = current_state.entities.get("C001")

            if entity is None or not entity.active:
                death_tick = tick
                break

        assert death_tick is not None, (
            f"Entity should have died from starvation within {MAX_TICKS_STARVATION} ticks. "
            f"Final wealth: {current_state.entities.get('C001').wealth if current_state.entities.get('C001') else 'N/A'}"
        )

        # Death should happen within reasonable time (not instant, but not too long)
        assert death_tick < 500, f"Death took too long: {death_tick} ticks"

    def test_zero_consumption_entity_survives(self) -> None:
        """Entity with s_bio=0 and s_class=0 should NOT be considered a zombie.

        If an entity has zero consumption needs, it is in equilibrium -
        not a zombie. This is intentional behavior for dormant entities.
        """
        dormant = SocialClass(
            id="C001",
            name="Dormant",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=0.0,
            s_bio=0.0,
            s_class=0.0,
            population=0,  # Dormant
            active=False,  # Already inactive
        )

        state = WorldState(tick=0, entities={"C001": dormant})
        G = state.to_graph()

        # Dormant entities should remain in stable inactive state
        assert G.nodes["C001"]["active"] is False

    def test_near_zero_wealth_triggers_death(self) -> None:
        """Entity with wealth below death threshold must die.

        This tests the DEATH_THRESHOLD failsafe:
        - Wealth < 0.001 should trigger death for population=1 entities
        - Prevents asymptotic decay where single-population entities
          never quite reach 0 wealth

        Note: For population>1, attrition naturally reduces population to 1
        before the zombie trap kicks in.
        """
        starving = SocialClass(
            id="C001",
            name="Starving",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.0001,  # Below death threshold (0.001)
            s_bio=0.01,
            s_class=0.01,
            population=1,  # Zombie trap applies to population=1 only
            active=True,
        )

        state = WorldState(tick=0, entities={"C001": starving})
        config = SimulationConfig()
        sim = Simulation(state, config)

        # Run one tick - should trigger death
        new_state = sim.step()
        entity = new_state.entities.get("C001")

        # Entity should be dead after one tick
        assert entity is None or entity.active is False, (
            f"Entity with near-zero wealth should die. "
            f"active={entity.active if entity else 'None'}, "
            f"wealth={entity.wealth if entity else 'None'}"
        )

    def test_entity_without_territory_produces_nothing(self) -> None:
        """Entity without TENANCY edge produces zero wealth.

        Production requires a Territory attachment. An entity without
        one should see wealth only decrease (subsistence burn), never
        increase (no production).

        This is a key validation for the Material Reality physics:
        No Territory = No Life (or at least, no income).
        """
        # Create entity WITHOUT territory/TENANCY
        landless = SocialClass(
            id="C001",
            name="Landless Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=10.0,  # Starting wealth
            s_bio=0.05,
            s_class=0.05,
            population=1,
            active=True,
        )

        state = WorldState(
            tick=0,
            entities={"C001": landless},
            # NO territories
            # NO relationships (especially no TENANCY)
        )
        config = SimulationConfig()
        sim = Simulation(state, config)

        previous_wealth = 10.0
        wealth_increased = False

        for _tick in range(10):
            current_state = sim.step()
            entity = current_state.entities.get("C001")

            if entity is None or not entity.active:
                break

            if entity.wealth > previous_wealth:
                wealth_increased = True
                break
            previous_wealth = entity.wealth

        # Wealth should never increase without production
        assert not wealth_increased, (
            "Entity without territory should not gain wealth. Started at 10.0, found increase."
        )

        # Wealth should have decreased (subsistence burn)
        final_entity = current_state.entities.get("C001")
        if final_entity and final_entity.active:
            assert final_entity.wealth < 10.0, (
                f"Entity should lose wealth to subsistence. Final wealth: {final_entity.wealth}"
            )


@pytest.mark.scenario
class TestPopulationAttrition:
    """Tests for population decline under resource constraints."""

    def test_population_declines_under_scarcity(self) -> None:
        """Population should decline when coverage ratio is insufficient.

        When wealth_per_capita < subsistence_needs * (1 + inequality),
        the Grinding Attrition formula should reduce population.
        """
        crowded = SocialClass(
            id="C001",
            name="Crowded Camp",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=50.0,  # Not enough for everyone
            s_bio=0.1,
            s_class=0.1,  # consumption_needs = 0.2 per person
            population=1000,  # Way too many for the wealth
            inequality=0.5,  # Unequal distribution
            active=True,
        )

        state = WorldState(tick=0, entities={"C001": crowded})
        config = SimulationConfig()
        sim = Simulation(state, config)

        initial_population = crowded.population

        # Run for a few ticks
        for _ in range(10):
            state = sim.step()

        entity = state.entities.get("C001")

        # Population should have declined due to attrition
        if entity is not None and entity.active:
            assert entity.population < initial_population, (
                f"Population should decline under scarcity. "
                f"Initial: {initial_population}, Current: {entity.population}"
            )
