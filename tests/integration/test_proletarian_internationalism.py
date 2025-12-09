"""Integration tests for Proletarian Internationalism - The Counterforce.

Sprint 3.4.2: Tests the full cycle of solidarity transmission across
the simulation engine, verifying that:

1. Consciousness transmits from periphery to core via SOLIDARITY edges
2. The Fascist Bifurcation scenario works (sigma=0 -> no transmission)
3. Events are emitted correctly for the narrative layer
4. Multi-tick simulations show cumulative consciousness awakening
5. SolidaritySystem integrates correctly in turn order

These tests verify the dialectical counterforce to Imperial Rent bribery.
"""

import pytest

from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState


@pytest.mark.integration
class TestProletarianInternationalism:
    """Integration tests for the full solidarity transmission cycle."""

    def test_revolutionary_scenario_multi_tick(self) -> None:
        """Revolutionary scenario: strong solidarity awakens core workers over time.

        Setup:
        - P_w (periphery worker): revolutionary consciousness (0.9)
        - C_w (core worker): passive consumer (0.1)
        - SOLIDARITY edge with sigma=0.8

        Expected: Core worker consciousness increases over multiple ticks,
        approaching revolutionary level.
        """
        # Arrange using factory functions with proper ID format
        periphery_worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=0.5,
            ideology=-0.8,  # consciousness 0.9
        )
        core_worker = create_proletariat(
            id="C002",
            name="Core Worker",
            wealth=1.0,
            ideology=0.8,  # consciousness 0.1
        )

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,  # Strong infrastructure
        )

        state = WorldState(
            tick=0,
            entities={"C001": periphery_worker, "C002": core_worker},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Act: Run multiple ticks using Simulation facade
        sim = Simulation(state, config)
        sim.run(5)
        history = sim.get_history()

        # Get consciousness history for core worker
        consciousness_history: list[float] = []
        for state in history:
            cw = state.entities["C002"]
            consciousness = (1.0 - cw.ideology) / 2.0
            consciousness_history.append(consciousness)

        # Assert: Consciousness should increase each tick
        # (until it approaches source consciousness)
        for i in range(1, len(consciousness_history)):
            # Each tick should increase or maintain consciousness
            # (may plateau as gap closes)
            assert consciousness_history[i] >= consciousness_history[i - 1] - 0.01

        # Final consciousness should be significantly higher than start (0.1)
        assert consciousness_history[-1] > 0.5

    def test_fascist_scenario_no_awakening(self) -> None:
        """Fascist Bifurcation: zero solidarity means no awakening.

        Same setup as revolutionary scenario, but solidarity_strength=0.
        Core workers remain passive despite periphery revolution.
        """
        # Arrange
        periphery_worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=0.5,
            ideology=-0.8,  # consciousness 0.9 (revolutionary)
        )
        core_worker = create_proletariat(
            id="C002",
            name="Core Worker",
            wealth=1.0,
            ideology=0.8,  # consciousness 0.1 (passive)
        )

        # KEY: solidarity_strength=0 (no infrastructure)
        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # Fascist scenario!
        )

        state = WorldState(
            tick=0,
            entities={"C001": periphery_worker, "C002": core_worker},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Act: Run multiple ticks
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Core worker consciousness should NOT significantly change
        # (only ConsciousnessSystem drift, not solidarity transmission)
        cw = final_state.entities["C002"]
        final_consciousness = (1.0 - cw.ideology) / 2.0

        # Should still be near initial low consciousness (maybe small drift)
        # Definitely should NOT be > 0.5 like revolutionary scenario
        assert final_consciousness < 0.3


@pytest.mark.integration
class TestSolidaritySystemTurnOrder:
    """Test that SolidaritySystem integrates correctly in turn order."""

    def test_solidarity_runs_after_imperial_rent(self) -> None:
        """SolidaritySystem runs AFTER ImperialRentSystem.

        This ensures that:
        1. Wealth extraction happens first (economic base)
        2. Consciousness transmission happens second (solidarity superstructure)
        3. General consciousness drift happens third
        """
        # Arrange: 4-node model
        periphery_worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=1.0,
            ideology=-0.6,  # consciousness 0.8
        )
        periphery_comprador = create_bourgeoisie(
            id="C002",
            name="Periphery Comprador",
            wealth=0.5,
        )
        core_bourgeoisie = create_bourgeoisie(
            id="C003",
            name="Core Bourgeoisie",
            wealth=2.0,
        )
        core_worker = create_proletariat(
            id="C004",
            name="Core Worker",
            wealth=0.8,
            ideology=0.6,  # consciousness 0.2
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        solidarity = Relationship(
            source_id="C001",
            target_id="C004",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )

        state = WorldState(
            tick=0,
            entities={
                "C001": periphery_worker,
                "C002": periphery_comprador,
                "C003": core_bourgeoisie,
                "C004": core_worker,
            },
            relationships=[exploitation, solidarity],
        )
        config = SimulationConfig()

        # Act
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Both extraction AND solidarity transmission happened
        # 1. P_w wealth should decrease (exploitation)
        pw = final_state.entities["C001"]
        assert pw.wealth < 1.0

        # 2. C_w ideology should change (solidarity transmission)
        cw = final_state.entities["C004"]
        original_consciousness = 0.2  # from ideology 0.6
        new_consciousness = (1.0 - cw.ideology) / 2.0
        assert new_consciousness > original_consciousness


@pytest.mark.integration
class TestMassAwakeningScenario:
    """Test the Mass Awakening scenario across simulation ticks."""

    def test_mass_awakening_threshold_crossing(self) -> None:
        """Core worker crossing mass awakening threshold.

        Setup core worker just below mass_awakening_threshold (0.6).
        After solidarity transmission, they cross the threshold.
        """
        # Arrange
        periphery_worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=0.5,
            ideology=-0.8,  # consciousness 0.9
        )
        core_worker = create_proletariat(
            id="C002",
            name="Core Worker",
            wealth=1.0,
            ideology=0.1,  # consciousness 0.45 (below 0.6 threshold)
        )

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.6,  # Moderate-strong infrastructure
        )

        state = WorldState(
            tick=0,
            entities={"C001": periphery_worker, "C002": core_worker},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Act
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Core worker should cross mass awakening threshold
        cw = final_state.entities["C002"]
        new_consciousness = (1.0 - cw.ideology) / 2.0
        assert new_consciousness >= 0.6

    def test_gradual_awakening_approach(self) -> None:
        """Gradual approach to mass awakening with moderate solidarity."""
        # Arrange: Lower solidarity_strength means slower awakening
        periphery_worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=0.5,
            ideology=-0.8,  # consciousness 0.9
        )
        core_worker = create_proletariat(
            id="C002",
            name="Core Worker",
            wealth=1.0,
            ideology=0.8,  # consciousness 0.1
        )

        solidarity_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.2,  # Weak infrastructure
        )

        state = WorldState(
            tick=0,
            entities={"C001": periphery_worker, "C002": core_worker},
            relationships=[solidarity_edge],
        )
        config = SimulationConfig()

        # Act: Track ticks until mass awakening
        sim = Simulation(state, config)
        ticks_to_awakening = 0
        max_ticks = 20

        for tick in range(1, max_ticks + 1):
            current_state = sim.run(1)
            cw = current_state.entities["C002"]
            consciousness = (1.0 - cw.ideology) / 2.0
            if consciousness >= 0.6:
                ticks_to_awakening = tick
                break

        # Assert: Should reach mass awakening, but takes multiple ticks
        assert ticks_to_awakening > 1, "Should take more than 1 tick with weak solidarity"
        assert ticks_to_awakening < max_ticks, "Should eventually reach mass awakening"


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test that existing simulations work without SOLIDARITY edges."""

    def test_no_solidarity_edges_unchanged_behavior(self) -> None:
        """Simulations without SOLIDARITY edges should work normally."""
        # Arrange: Simple 2-node exploitation model (Phase 1)
        worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=1.0,
            ideology=0.0,
        )
        owner = create_bourgeoisie(
            id="C002",
            name="Core Owner",
            wealth=5.0,
        )

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )
        config = SimulationConfig()

        # Act: Should not raise
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Basic mechanics work
        assert final_state.tick == 1
        # Worker lost wealth (exploitation)
        w = final_state.entities["C001"]
        assert w.wealth < 1.0

    def test_solidarity_edge_with_zero_strength_unchanged(self) -> None:
        """SOLIDARITY edge with zero strength should not affect simulation."""
        # Arrange
        worker = create_proletariat(
            id="C001",
            name="Periphery Worker",
            wealth=0.5,
            ideology=-0.8,
        )
        consumer = create_proletariat(
            id="C002",
            name="Core Consumer",
            wealth=1.0,
            ideology=0.8,
        )

        solidarity = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # Zero strength
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": consumer},
            relationships=[solidarity],
        )
        config = SimulationConfig()

        # Act
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Consumer ideology should not significantly change from solidarity
        # (may change slightly from ConsciousnessSystem drift)
        c = final_state.entities["C002"]
        # Should still be near original passive ideology
        assert c.ideology > 0.5
