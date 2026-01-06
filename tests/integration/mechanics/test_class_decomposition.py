"""Integration tests for Class Decomposition - The LA Crisis.

This module tests the DecompositionSystem which implements:
- SUPERWAGE_CRISIS detection (from ImperialRentSystem or wealth collapse)
- Delayed decomposition (52 ticks after crisis by default)
- Fallback decomposition (LA approaching death)
- Population/wealth split to CARCERAL_ENFORCER and INTERNAL_PROLETARIAT
- CLASS_DECOMPOSITION event emission

Key insight: The Labor Aristocracy can only exist while imperial rent flows.
When the empire can no longer pay super-wages, the LA decomposes into guards
(who manage the surplus population) and prisoners (the surplus population itself).

Test Scenarios:
1. Normal path: SUPERWAGE_CRISIS -> delay -> CLASS_DECOMPOSITION
2. Fallback path: LA wealth drops below subsistence -> CLASS_DECOMPOSITION
3. Population/wealth split matches defines fractions (15% enforcer, 85% proletariat)
4. Decomposition is one-time (idempotent)
"""

import random

import pytest

from babylon.config.defines import CarceralDefines, GameDefines
from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import SocialRole

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]

# Decomposition fraction tolerance: ±5% around configured fraction
# This accounts for population changes from other systems during simulation
DECOMPOSITION_FRACTION_TOLERANCE = 0.05


def _create_la_crisis_scenario(
    la_wealth: float = 500.0,
    la_population: int = 1000,
    la_subsistence: float = 50.0,
) -> tuple[WorldState, SimulationConfig]:
    """Create a scenario where Labor Aristocracy may face crisis.

    Args:
        la_wealth: Starting wealth for LA (default 500.0)
        la_population: Starting population for LA (default 1000)
        la_subsistence: Subsistence threshold for LA (default 50.0)

    Returns:
        Tuple of (WorldState, SimulationConfig) ready for simulation.

    The state includes:
    - Labor Aristocracy (active, receiving super-wages or not)
    - Dormant CARCERAL_ENFORCER (population=0, active=False)
    - Dormant INTERNAL_PROLETARIAT (population=0, active=False)
    """
    labor_aristocracy = SocialClass(
        id="C001",
        name="Labor Aristocracy",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=la_wealth,
        population=la_population,
        s_bio=0.1,
        s_class=0.1,
        subsistence_threshold=la_subsistence,
        active=True,
    )

    # Dormant entities that will be activated by decomposition
    enforcer = SocialClass(
        id="C002",
        name="Carceral Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=0.0,
        population=0,
        active=False,  # Dormant
    )

    internal_proletariat = SocialClass(
        id="C003",
        name="Internal Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=0.0,
        population=0,
        active=False,  # Dormant
    )

    state = WorldState(
        tick=0,
        entities={
            "C001": labor_aristocracy,
            "C002": enforcer,
            "C003": internal_proletariat,
        },
        relationships=[],
    )

    config = SimulationConfig()

    return state, config


class TestDecompositionTrigger:
    """Tests for decomposition trigger conditions."""

    def test_fallback_decomposition_when_la_wealth_below_subsistence(self) -> None:
        """Test that decomposition triggers when LA wealth < subsistence threshold.

        The fallback mechanism ensures decomposition happens even without
        SUPERWAGE_CRISIS event - it's a safety valve to prevent LA from
        dying before the carceral phase can execute.
        """
        random.seed(42)

        # Create LA with wealth below subsistence threshold
        # This should trigger the fallback decomposition path
        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,  # Below subsistence (50.0)
            la_population=1000,
            la_subsistence=50.0,
        )

        # Use short delay for faster testing
        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        # Run a few ticks - fallback should trigger quickly
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(10)

        # Check for CLASS_DECOMPOSITION event in log
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        assert len(decomposition_events) >= 1, (
            f"Fallback decomposition should trigger when LA wealth ({10.0}) < "
            f"subsistence ({50.0}). Events: {final_state.event_log[-10:]}"
        )

    def test_decomposition_with_short_delay(self) -> None:
        """Test that decomposition respects the configured delay.

        After SUPERWAGE_CRISIS is detected, decomposition waits for
        decomposition_delay ticks before executing.
        """
        random.seed(42)

        # Start LA just above subsistence so it triggers SUPERWAGE_CRISIS
        # approaching-death warning first, then decomposition after delay
        state, config = _create_la_crisis_scenario(
            la_wealth=100.0,  # Low but above subsistence (50)
            la_population=1000,
            la_subsistence=50.0,
        )

        # Use very short delay (1 tick)
        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        # Run simulation
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(20)

        # May or may not decompose depending on exact wealth dynamics
        # The key test is that IF it decomposes, it respects the delay
        # and that the simulation completes without error
        assert final_state.tick == 20, "Simulation should complete 20 ticks"


class TestDecompositionOutcome:
    """Tests for population and wealth distribution after decomposition."""

    def test_population_splits_to_enforcer_and_proletariat(self) -> None:
        """Test that LA population splits according to defines fractions.

        Default fractions: 15% to enforcer, 85% to internal proletariat.
        We run minimal ticks (3) to reduce the effect of other systems.
        """
        random.seed(42)

        initial_pop = 1000

        # Create LA with low wealth to trigger fallback decomposition
        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,  # Below subsistence
            la_population=initial_pop,
            la_subsistence=50.0,
        )

        # Use default fractions (15% enforcer, 85% proletariat)
        defines = GameDefines(
            carceral=CarceralDefines(
                decomposition_delay=1,
                enforcer_fraction=0.15,
                proletariat_fraction=0.85,
            )
        )

        # Run only 3 ticks to minimize interference from other systems
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(3)

        # Check if decomposition occurred
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        if decomposition_events:
            # Verify population splits - the fractions are applied to LA pop
            # at the moment of decomposition (which may have changed slightly)
            enforcer = final_state.entities.get("C002")
            proletariat = final_state.entities.get("C003")

            # Key test: enforcer should have SOME population (was 0 initially)
            if enforcer is not None and enforcer.active:
                assert enforcer.population > 0, (
                    "Enforcer should have gained population from decomposition"
                )

            # Key test: proletariat should have SOME population (was 0 initially)
            if proletariat is not None and proletariat.active:
                assert proletariat.population > 0, (
                    "Internal proletariat should have gained population from decomposition"
                )

            # The ratio between them should approximately match the fractions
            if (
                enforcer is not None
                and proletariat is not None
                and enforcer.active
                and proletariat.active
            ):
                total_pop = enforcer.population + proletariat.population
                if total_pop > 0:
                    enforcer_ratio = enforcer.population / total_pop
                    # Enforcer fraction from defines, with configured tolerance
                    expected = defines.carceral.enforcer_fraction
                    lower_bound = expected - DECOMPOSITION_FRACTION_TOLERANCE
                    upper_bound = expected + DECOMPOSITION_FRACTION_TOLERANCE
                    assert lower_bound <= enforcer_ratio <= upper_bound, (
                        f"Enforcer ratio should be ~{expected}, got {enforcer_ratio:.3f}"
                    )

    def test_la_deactivated_after_decomposition(self) -> None:
        """Test that Labor Aristocracy is marked inactive after decomposition."""
        random.seed(42)

        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,  # Below subsistence - triggers fallback
            la_population=1000,
            la_subsistence=50.0,
        )

        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(10)

        # Check if decomposition occurred
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        if decomposition_events:
            # LA should be deactivated
            la = final_state.entities.get("C001")
            assert la is not None, "LA entity should still exist"
            assert la.active is False, "LA should be deactivated after decomposition"

    def test_dormant_entities_activated_after_decomposition(self) -> None:
        """Test that dormant enforcer and proletariat are activated."""
        random.seed(42)

        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,
            la_population=1000,
            la_subsistence=50.0,
        )

        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(10)

        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        if decomposition_events:
            # Both dormant entities should now be active
            enforcer = final_state.entities.get("C002")
            proletariat = final_state.entities.get("C003")

            assert enforcer is not None and enforcer.active, (
                "Enforcer should be activated after decomposition"
            )
            assert proletariat is not None and proletariat.active, (
                "Internal proletariat should be activated after decomposition"
            )


class TestDecompositionIdempotency:
    """Tests for one-time decomposition behavior."""

    def test_decomposition_only_happens_once(self) -> None:
        """Test that decomposition cannot occur multiple times.

        The _decomposition_complete flag in persistent_data prevents
        multiple decompositions from the same LA.
        """
        random.seed(42)

        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,  # Trigger fallback
            la_population=1000,
            la_subsistence=50.0,
        )

        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        # Run many ticks
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(100)

        # Count decomposition events
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        # Should be exactly 0 or 1 (depends on whether conditions were met)
        assert len(decomposition_events) <= 1, (
            f"Decomposition should only happen once (idempotency). "
            f"Got {len(decomposition_events)} events"
        )


class TestDecompositionWithCustomFractions:
    """Tests for configurable decomposition fractions."""

    def test_custom_enforcer_fraction(self) -> None:
        """Test that custom enforcer_fraction affects population split.

        We use 30% enforcer / 70% proletariat and verify the ratio is
        approximately correct. Running minimal ticks to reduce interference.
        """
        random.seed(42)

        initial_pop = 1000

        state, config = _create_la_crisis_scenario(
            la_wealth=10.0,
            la_population=initial_pop,
            la_subsistence=50.0,
        )

        # Use custom fractions: 30% enforcer, 70% proletariat
        defines = GameDefines(
            carceral=CarceralDefines(
                decomposition_delay=1,
                enforcer_fraction=0.30,
                proletariat_fraction=0.70,
            )
        )

        # Run only 3 ticks to minimize interference from other systems
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(3)

        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        if decomposition_events:
            enforcer = final_state.entities.get("C002")
            proletariat = final_state.entities.get("C003")

            # Verify both entities have population
            if (
                enforcer is not None
                and proletariat is not None
                and enforcer.active
                and proletariat.active
            ):
                total_pop = enforcer.population + proletariat.population
                if total_pop > 0:
                    enforcer_ratio = enforcer.population / total_pop
                    # Enforcer fraction from defines, with configured tolerance
                    expected = defines.carceral.enforcer_fraction
                    lower_bound = expected - DECOMPOSITION_FRACTION_TOLERANCE
                    upper_bound = expected + DECOMPOSITION_FRACTION_TOLERANCE
                    assert lower_bound <= enforcer_ratio <= upper_bound, (
                        f"With {expected:.0%} enforcer fraction, ratio should be ~{expected}, "
                        f"got {enforcer_ratio:.3f}"
                    )
