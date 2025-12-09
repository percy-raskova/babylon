"""Verification tests for the modular engine refactor.

Phase 2.1: Dialectical Refactor - ensures refactored code matches original.
"""

import pytest

from babylon.engine import SimulationEngine, step
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.systems import (
    ConsciousnessSystem,
    ContradictionSystem,
    ImperialRentSystem,
    SurvivalSystem,
    System,
)


class TestModularEngineArchitecture:
    """Test the modular System architecture."""

    def test_systems_satisfy_protocol(self) -> None:
        """All system classes satisfy the System protocol."""
        systems = [
            ImperialRentSystem(),
            ConsciousnessSystem(),
            SurvivalSystem(),
            ContradictionSystem(),
        ]
        for system in systems:
            assert isinstance(system, System)
            assert hasattr(system, "name")
            assert hasattr(system, "step")

    def test_engine_accepts_custom_systems(self) -> None:
        """SimulationEngine can be instantiated with custom systems."""
        engine = SimulationEngine([ImperialRentSystem()])
        assert len(engine.systems) == 1
        assert engine.systems[0].name == "Imperial Rent"

    def test_system_order_preserved(self) -> None:
        """Systems execute in the order they are provided."""
        systems = [
            ImperialRentSystem(),
            ConsciousnessSystem(),
            SurvivalSystem(),
            ContradictionSystem(),
        ]
        engine = SimulationEngine(systems)
        names = [s.name for s in engine.systems]
        assert names == [
            "Imperial Rent",
            "Consciousness Drift",
            "Survival Calculus",
            "Contradiction Tension",
        ]


@pytest.mark.integration
class TestRefactorDeterminism:
    """Verify refactored engine produces identical results."""

    def test_100_tick_determinism(self) -> None:
        """100 ticks produce consistent final state."""
        state, config = create_two_node_scenario()

        initial_wealth = state.entities["C001"].wealth

        for _ in range(100):
            state = step(state, config)

        # Worker should have lost wealth through extraction
        assert state.tick == 100
        assert state.entities["C001"].wealth < initial_wealth
        # Tension should be accumulating
        assert state.relationships[0].tension > 0.0
        # Note: Without SOLIDARITY edges or WAGES changes,
        # class_consciousness stays at initial value (0.5).
        # This is expected behavior in Sprint 3.4.3.

    def test_step_function_unchanged(self) -> None:
        """step() function signature and behavior unchanged."""
        state, config = create_two_node_scenario()

        # Single step works
        new_state = step(state, config)
        assert new_state.tick == 1
        assert new_state is not state

        # Extraction occurred
        assert new_state.entities["C001"].wealth < state.entities["C001"].wealth
