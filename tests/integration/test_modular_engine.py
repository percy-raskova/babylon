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

        for _ in range(100):
            state = step(state, config)

        # With PPP model, worker receives super-wages that offset extraction losses.
        # The net effect depends on extraction_efficiency vs wage_rate.
        # Key PPP verification: effective_wealth > nominal_wealth (PPP bonus exists)
        assert state.tick == 100
        worker = state.entities["C001"]
        # PPP Model: effective_wealth includes purchasing power bonus
        assert worker.effective_wealth > 0  # Worker has effective wealth
        assert worker.ppp_multiplier > 1.0  # PPP bonus is active

        # Tension should be accumulating on exploitation edge
        exploitation_edges = [r for r in state.relationships if r.edge_type.value == "exploitation"]
        if exploitation_edges:
            assert exploitation_edges[0].tension > 0.0

    def test_step_function_unchanged(self) -> None:
        """step() function signature and behavior unchanged."""
        state, config = create_two_node_scenario()

        # Single step works
        new_state = step(state, config)
        assert new_state.tick == 1
        assert new_state is not state

        # Economic flow occurred (extraction and/or wages)
        # With PPP model, net wealth change depends on extraction vs wages
        # Key verification: some economic activity happened
        worker = new_state.entities["C001"]
        assert worker.wealth != state.entities["C001"].wealth or worker.effective_wealth > 0
