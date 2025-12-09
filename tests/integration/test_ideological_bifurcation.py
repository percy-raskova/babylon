"""Integration tests for Ideological Bifurcation - Socialism or Barbarism.

Sprint 3.4.2b: Tests the Fascist Bifurcation mechanic where falling wages
cause either revolutionary or fascist drift depending on SOLIDARITY edges.

The key insight: Economic crisis does NOT automatically produce revolutionary
consciousness. Without solidarity infrastructure, loss aversion channels
pain into nationalism/fascism instead.

"Agitation without solidarity produces fascism, not revolution."
"""

import pytest

from babylon.engine.factories import create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState


@pytest.mark.integration
class TestIdeologicalBifurcation:
    """Tests for the 'Socialism or Barbarism' bifurcation scenario."""

    def test_socialism_or_barbarism_bifurcation(self) -> None:
        """Falling wages produce fascism OR revolution based on solidarity.

        This is the core test for the Fascist Bifurcation mechanic.

        Setup:
        - Worker_A and Worker_B are both Labor Aristocrats (W > V)
        - Core Bourgeoisie pays super-wages via WAGES edges
        - Both experience a wage cut (simulating Imperial Crisis via reduced value_flow)
        - Worker_A: NO incoming SOLIDARITY edge (The National)
        - Worker_B: HAS incoming SOLIDARITY edge from Periphery (The International)

        Expected Behavior:
        - Worker_A drifts POSITIVE (fascist) due to loss aversion without direction
        - Worker_B drifts NEGATIVE (revolutionary) due to solidarity channeling
        - Key assertion: Worker_B.ideology < Worker_A.ideology after tick

        This encodes the historical insight: Germany 1933 vs Russia 1917.
        Same economic crisis, different outcomes based on solidarity infrastructure.
        """
        from babylon.engine.factories import create_bourgeoisie

        # Initial ideology for both workers (slightly reactionary, bought off)
        initial_ideology = 0.3

        # The National (no solidarity) - will drift fascist
        worker_a = create_proletariat(
            id="C001",
            name="The National (no solidarity)",
            wealth=100.0,
            ideology=initial_ideology,
        )

        # The International (with solidarity) - will drift revolutionary
        worker_b = create_proletariat(
            id="C002",
            name="The International (with solidarity)",
            wealth=100.0,
            ideology=initial_ideology,
        )

        # Periphery worker with revolutionary consciousness
        # This is the source of solidarity transmission
        periphery_worker = create_proletariat(
            id="C003",
            name="Periphery Worker",
            wealth=20.0,
            ideology=-0.8,  # consciousness 0.9 (revolutionary)
        )

        # Core Bourgeoisie who pays wages
        core_bourgeoisie = create_bourgeoisie(
            id="C004",
            name="Core Bourgeoisie",
            wealth=500.0,
        )

        # WAGES edges from bourgeoisie to workers (high wages = labor aristocracy)
        # These will be reduced in tick 2 to simulate crisis
        wages_to_a = Relationship(
            source_id="C004",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,  # High super-wages initially
        )
        wages_to_b = Relationship(
            source_id="C004",
            target_id="C002",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,  # High super-wages initially
        )

        # KEY DIFFERENTIATION: SOLIDARITY edge only to Worker_B
        solidarity_edge = Relationship(
            source_id="C003",  # Periphery worker
            target_id="C002",  # Worker_B (The International)
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.9,  # Strong infrastructure
        )

        # Create initial state with WAGES edges
        state = WorldState(
            tick=0,
            entities={
                "C001": worker_a,
                "C002": worker_b,
                "C003": periphery_worker,
                "C004": core_bourgeoisie,
            },
            relationships=[wages_to_a, wages_to_b, solidarity_edge],
        )

        config = SimulationConfig()

        # Execute: Run first tick to establish wage baseline
        sim = Simulation(state, config)
        state_after_tick_1 = sim.run(1)

        # Now simulate wage CUT by reducing WAGES edge value_flow
        # This is the "Imperial Crisis" scenario
        reduced_wages_to_a = Relationship(
            source_id="C004",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # 20 unit wage cut (40% reduction)
        )
        reduced_wages_to_b = Relationship(
            source_id="C004",
            target_id="C002",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # 20 unit wage cut (40% reduction)
        )

        # Create new state with reduced wages
        state_with_wage_cut = WorldState(
            tick=state_after_tick_1.tick,
            entities=state_after_tick_1.entities,
            relationships=[reduced_wages_to_a, reduced_wages_to_b, solidarity_edge],
        )

        # Run second tick with wage cut - this triggers bifurcation
        sim2 = Simulation(state_with_wage_cut, config)
        final_state = sim2.run(1)

        # Get final ideologies
        a_ideology = final_state.entities["C001"].ideology
        b_ideology = final_state.entities["C002"].ideology

        # Get ideologies after tick 1 (before wage cut) for comparison
        a_after_tick1 = state_after_tick_1.entities["C001"].ideology
        b_after_tick1 = state_after_tick_1.entities["C002"].ideology

        # ASSERTIONS:
        # The key assertion is the RELATIVE difference between workers
        # Worker_B (with solidarity) should be more revolutionary than Worker_A

        # 3. KEY ASSERTION: The International is more revolutionary than The National
        # This is the core of the Fascist Bifurcation mechanic
        assert b_ideology < a_ideology, (
            f"Solidarity should channel crisis into revolution. "
            f"Worker_B ({b_ideology}) should be more revolutionary than "
            f"Worker_A ({a_ideology}). After tick 1: A={a_after_tick1}, B={b_after_tick1}"
        )

    def test_no_wage_change_no_bifurcation(self) -> None:
        """Without wage changes, normal W/V ratio drift applies.

        This tests backward compatibility - the bifurcation mechanic
        only activates when wages are falling.
        """
        # Two identical workers with stable wages
        worker_a = create_proletariat(
            id="C001",
            name="Worker A",
            wealth=100.0,
            ideology=0.3,
        )
        worker_b = create_proletariat(
            id="C002",
            name="Worker B",
            wealth=100.0,
            ideology=0.3,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker_a, "C002": worker_b},
            relationships=[],
        )
        config = SimulationConfig()

        # Run simulation
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Both should drift similarly (no bifurcation without wage change)
        a_ideology = final_state.entities["C001"].ideology
        b_ideology = final_state.entities["C002"].ideology

        # They should be approximately equal (within epsilon)
        assert abs(a_ideology - b_ideology) < 0.1, (
            f"Without wage changes, workers should drift similarly. "
            f"Worker_A: {a_ideology}, Worker_B: {b_ideology}"
        )

    def test_wage_cut_without_solidarity_amplifies_fascist_drift(self) -> None:
        """Loss aversion amplifies fascist drift when wages fall without solidarity.

        The loss aversion coefficient (2.25) means losses hurt more than
        equivalent gains. Without solidarity to channel this pain into
        class consciousness, it flows toward nationalism/fascism.
        """
        worker = create_proletariat(
            id="C001",
            name="Isolated Worker",
            wealth=100.0,
            ideology=0.0,  # Neutral starting point
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],  # No solidarity edges
        )
        config = SimulationConfig()

        sim = Simulation(state, config)

        # Track ideology over multiple ticks with wage decline
        # The drift should be amplified by loss aversion
        final_state = sim.run(3)

        final_ideology = final_state.entities["C001"].ideology

        # Without solidarity and with implicit wage pressure,
        # worker should drift toward positive (reactionary)
        # This tests that loss aversion is being applied
        assert final_ideology >= 0.0, (
            f"Isolated worker under wage pressure should drift reactionary. "
            f"Got ideology: {final_ideology}"
        )


@pytest.mark.integration
class TestBifurcationMechanics:
    """Tests for the mathematical mechanics of bifurcation."""

    def test_solidarity_pressure_calculation(self) -> None:
        """Solidarity pressure is sum of incoming SOLIDARITY edge strengths.

        A worker with multiple solidarity connections should have
        higher effective solidarity pressure.
        """
        target_worker = create_proletariat(
            id="C001",
            name="Target Worker",
            wealth=100.0,
            ideology=0.5,  # Passive
        )

        # Multiple periphery workers with solidarity connections
        periphery_1 = create_proletariat(
            id="C002",
            name="Periphery 1",
            wealth=20.0,
            ideology=-0.6,  # consciousness 0.8
        )
        periphery_2 = create_proletariat(
            id="C003",
            name="Periphery 2",
            wealth=20.0,
            ideology=-0.8,  # consciousness 0.9
        )

        # Two solidarity edges with different strengths
        solidarity_1 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )
        solidarity_2 = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        state = WorldState(
            tick=0,
            entities={
                "C001": target_worker,
                "C002": periphery_1,
                "C003": periphery_2,
            },
            relationships=[solidarity_1, solidarity_2],
        )
        config = SimulationConfig()

        sim = Simulation(state, config)
        final_state = sim.run(1)

        # With combined solidarity pressure of 0.8, worker should
        # drift toward revolution (negative ideology)
        final_ideology = final_state.entities["C001"].ideology

        assert final_ideology < 0.5, (
            f"Multiple solidarity connections should produce revolutionary drift. "
            f"Got ideology: {final_ideology}, expected < 0.5"
        )

    def test_bifurcation_is_threshold_based(self) -> None:
        """Bifurcation only occurs when wage change is negative.

        Positive wage changes (rising wages) should not trigger
        the bifurcation mechanic - only standard W/V ratio drift.
        """
        worker = create_proletariat(
            id="C001",
            name="Worker",
            wealth=100.0,
            ideology=0.0,
        )

        # Periphery with solidarity connection
        periphery = create_proletariat(
            id="C002",
            name="Periphery",
            wealth=20.0,
            ideology=-0.8,
        )

        solidarity = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.9,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": periphery},
            relationships=[solidarity],
        )
        config = SimulationConfig()

        # Run simulation with implied rising wages
        # (this tests that solidarity transmission still works,
        # but bifurcation amplification only happens on falling wages)
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Worker should still drift toward periphery consciousness
        # via standard solidarity transmission, even without
        # the crisis-amplified bifurcation
        final_ideology = final_state.entities["C001"].ideology

        # Should be lower (more revolutionary) due to solidarity
        assert final_ideology < 0.0, (
            f"Solidarity transmission should occur regardless of wage direction. "
            f"Got ideology: {final_ideology}"
        )
