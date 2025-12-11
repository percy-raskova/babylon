"""Integration tests for Sprint 3.4.3 - The George Jackson Refactor.

This module tests the multi-dimensional ideological model where:
- Class Consciousness (Axis A): Relationship to Capital [0.0 = False, 1.0 = Revolutionary]
- National Identity (Axis B): Relationship to State/Tribe [0.0 = Internationalist, 1.0 = Nativist/Fascist]
- Agitation (Energy): Raw political energy created by crisis (falling wages)

Key Insight: "Fascism is the defensive form of capitalism."
- Agitation + Solidarity -> Class Consciousness (Revolutionary Path)
- Agitation + No Solidarity -> National Identity (Fascist Path)
"""

import pytest

from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState
from babylon.models.entities.social_class import IdeologicalProfile


@pytest.mark.integration
class TestFascistBifurcationMultiDimensional:
    """Tests for the George Jackson Refactor - Multi-Dimensional Ideology Model."""

    def test_revolutionary_path_class_consciousness_increases(self) -> None:
        """Test Case A: The Revolutionary Path.

        Setup: Worker with falling wages AND solidarity_strength=1.0
        Expectation: class_consciousness increases, national_identity stays flat

        This tests the core routing mechanic:
        - Agitation (from wage fall) + High Solidarity = Class Consciousness increase
        """
        # Create a core worker who will experience wage cuts
        # Start with neutral ideology (class_consciousness=0.5)
        core_worker = create_proletariat(
            id="C001",
            name="Core Worker (with solidarity)",
            wealth=100.0,
            ideology=0.0,  # Neutral starting point (consciousness 0.5)
        )

        # Periphery worker with revolutionary consciousness to provide solidarity
        periphery_worker = create_proletariat(
            id="C002",
            name="Periphery Worker",
            wealth=20.0,
            ideology=-0.8,  # Revolutionary consciousness (0.9)
        )

        # Core bourgeoisie who pays wages
        core_bourgeoisie = create_bourgeoisie(
            id="C003",
            name="Core Bourgeoisie",
            wealth=500.0,
        )

        # WAGES edge from bourgeoisie to worker (high initial wages)
        wages_edge = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,  # High super-wages initially
        )

        # KEY: Strong SOLIDARITY edge from periphery to core worker
        solidarity_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=1.0,  # Maximum solidarity infrastructure
        )

        # Create initial state
        state = WorldState(
            tick=0,
            entities={
                "C001": core_worker,
                "C002": periphery_worker,
                "C003": core_bourgeoisie,
            },
            relationships=[wages_edge, solidarity_edge],
        )
        config = SimulationConfig()

        # Run first tick to establish wage baseline
        sim = Simulation(state, config)
        state_after_tick_1 = sim.run(1)

        # Get the ideology profile from the worker after tick 1
        worker_tick1 = state_after_tick_1.entities["C001"]

        # The ideology should be an IdeologicalProfile with the new fields
        ideology_profile = worker_tick1.ideology

        assert hasattr(ideology_profile, "class_consciousness"), (
            "IdeologicalProfile should have class_consciousness field"
        )
        assert hasattr(ideology_profile, "national_identity"), (
            "IdeologicalProfile should have national_identity field"
        )
        assert hasattr(ideology_profile, "agitation"), (
            "IdeologicalProfile should have agitation field"
        )

        # Record initial values (after first tick establishes baseline)
        initial_class_consciousness = ideology_profile.class_consciousness
        initial_national_identity = ideology_profile.national_identity

        # Now simulate wage CUT by updating the state with reduced wages
        reduced_wages_edge = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # 20 unit wage cut (40% reduction)
        )

        # Create new state with reduced wages but same entities
        state_with_wage_cut = WorldState(
            tick=state_after_tick_1.tick,
            entities=state_after_tick_1.entities,
            relationships=[reduced_wages_edge, solidarity_edge],
        )

        # Use update_state to preserve persistent context (previous_wages)
        sim.update_state(state_with_wage_cut)

        # Run second tick with wage cut - this triggers bifurcation routing
        final_state = sim.run(1)

        # Get final ideology profile
        final_worker = final_state.entities["C001"]
        final_profile = final_worker.ideology

        # ASSERTIONS for Revolutionary Path:
        # 1. Class consciousness should INCREASE (agitation routed to class axis)
        assert final_profile.class_consciousness > initial_class_consciousness, (
            f"With high solidarity, class_consciousness should increase. "
            f"Initial: {initial_class_consciousness}, Final: {final_profile.class_consciousness}"
        )

        # 2. National identity should stay FLAT or decrease (not absorb agitation)
        # Allow small tolerance since solidarity transmission might affect it slightly
        assert final_profile.national_identity <= initial_national_identity + 0.05, (
            f"With high solidarity, national_identity should stay flat or decrease. "
            f"Initial: {initial_national_identity}, Final: {final_profile.national_identity}"
        )

    def test_fascist_path_national_identity_spikes(self) -> None:
        """Test Case B: The Fascist Path.

        Setup: Worker with falling wages AND solidarity_strength=0.0 (no solidarity)
        Expectation: class_consciousness stays flat, national_identity spikes

        This tests the core routing mechanic:
        - Agitation (from wage fall) + No Solidarity = National Identity increase
        """
        # Create a core worker who will experience wage cuts (isolated, no solidarity)
        core_worker = create_proletariat(
            id="C001",
            name="Core Worker (isolated)",
            wealth=100.0,
            ideology=0.0,  # Neutral starting point (class_consciousness 0.5)
        )

        # Core bourgeoisie who pays wages
        core_bourgeoisie = create_bourgeoisie(
            id="C002",
            name="Core Bourgeoisie",
            wealth=500.0,
        )

        # WAGES edge from bourgeoisie to worker (high initial wages)
        wages_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,  # High super-wages initially
        )

        # NO SOLIDARITY EDGE - this is the key difference

        # Create initial state
        state = WorldState(
            tick=0,
            entities={
                "C001": core_worker,
                "C002": core_bourgeoisie,
            },
            relationships=[wages_edge],
        )
        config = SimulationConfig()

        # Run first tick to establish wage baseline
        sim = Simulation(state, config)
        state_after_tick_1 = sim.run(1)

        # Get the ideology profile from the worker after tick 1
        worker_tick1 = state_after_tick_1.entities["C001"]
        ideology_profile = worker_tick1.ideology

        # Record initial values (after first tick to establish baseline)
        initial_class_consciousness = ideology_profile.class_consciousness
        initial_national_identity = ideology_profile.national_identity

        # Now simulate wage CUT
        reduced_wages_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # 20 unit wage cut (40% reduction)
        )

        # Create new state with reduced wages
        state_with_wage_cut = WorldState(
            tick=state_after_tick_1.tick,
            entities=state_after_tick_1.entities,
            relationships=[reduced_wages_edge],
        )

        # Use update_state to preserve persistent context
        sim.update_state(state_with_wage_cut)

        # Run second tick with wage cut - this triggers bifurcation routing
        final_state = sim.run(1)

        # Get final ideology profile
        final_worker = final_state.entities["C001"]
        final_profile = final_worker.ideology

        # ASSERTIONS for Fascist Path:
        # 1. National identity should INCREASE (agitation routed to nation axis)
        assert final_profile.national_identity > initial_national_identity, (
            f"Without solidarity, national_identity should increase. "
            f"Initial: {initial_national_identity}, Final: {final_profile.national_identity}"
        )

        # 2. Class consciousness should stay FLAT (not absorb agitation)
        assert abs(final_profile.class_consciousness - initial_class_consciousness) < 0.1, (
            f"Without solidarity, class_consciousness should stay flat. "
            f"Initial: {initial_class_consciousness}, Final: {final_profile.class_consciousness}"
        )

    def test_ideological_profile_has_correct_structure(self) -> None:
        """Test that IdeologicalProfile has all required fields.

        The IdeologicalProfile should have:
        - class_consciousness: [0.0, 1.0]
        - national_identity: [0.0, 1.0]
        - agitation: [0.0, inf)
        """
        # Create a fresh worker with explicit IdeologicalProfile
        profile = IdeologicalProfile(
            class_consciousness=0.3,
            national_identity=0.6,
            agitation=0.5,
        )

        assert profile.class_consciousness == 0.3
        assert profile.national_identity == 0.6
        assert profile.agitation == 0.5

        # Test default values
        default_profile = IdeologicalProfile()
        assert default_profile.class_consciousness == 0.0
        assert default_profile.national_identity == 0.5
        assert default_profile.agitation == 0.0

        # Test legacy conversion
        legacy_profile = IdeologicalProfile.from_legacy_ideology(-0.8)
        assert legacy_profile.class_consciousness == 0.9  # (1 - (-0.8)) / 2 = 0.9
        assert abs(legacy_profile.national_identity - 0.1) < 0.001  # (1 + (-0.8)) / 2 = 0.1
        assert legacy_profile.agitation == 0.0

    def test_bifurcation_symmetry(self) -> None:
        """Test that the same wage cut produces opposite effects based on solidarity.

        Two identical workers experience the same wage cut.
        - Worker A: With solidarity -> class_consciousness rises
        - Worker B: Without solidarity -> national_identity rises

        The total agitation should be the same, just routed differently.
        """
        # Worker A (with solidarity)
        worker_a = create_proletariat(
            id="C001",
            name="Worker A (with solidarity)",
            wealth=100.0,
            ideology=0.0,
        )

        # Worker B (without solidarity)
        worker_b = create_proletariat(
            id="C002",
            name="Worker B (isolated)",
            wealth=100.0,
            ideology=0.0,
        )

        # Periphery worker to provide solidarity to Worker A only
        periphery_worker = create_proletariat(
            id="C003",
            name="Periphery Worker",
            wealth=20.0,
            ideology=-0.8,  # Revolutionary consciousness
        )

        # Core bourgeoisie
        core_bourgeoisie = create_bourgeoisie(
            id="C004",
            name="Core Bourgeoisie",
            wealth=500.0,
        )

        # WAGES edges to both workers (identical)
        wages_to_a = Relationship(
            source_id="C004",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,
        )
        wages_to_b = Relationship(
            source_id="C004",
            target_id="C002",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,
        )

        # SOLIDARITY only to Worker A
        solidarity_edge = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=1.0,
        )

        # Initial state
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

        # Run first tick to establish wage baseline
        sim = Simulation(state, config)
        state_after_tick_1 = sim.run(1)

        # Record initial profiles
        profile_a_initial = state_after_tick_1.entities["C001"].ideology
        profile_b_initial = state_after_tick_1.entities["C002"].ideology

        # Now apply identical wage cuts
        reduced_wages_to_a = Relationship(
            source_id="C004",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # Same 20 unit cut
        )
        reduced_wages_to_b = Relationship(
            source_id="C004",
            target_id="C002",
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # Same 20 unit cut
        )

        # State with wage cuts
        state_with_cuts = WorldState(
            tick=state_after_tick_1.tick,
            entities=state_after_tick_1.entities,
            relationships=[reduced_wages_to_a, reduced_wages_to_b, solidarity_edge],
        )

        # Use update_state to preserve context
        sim.update_state(state_with_cuts)

        # Run second tick
        final_state = sim.run(1)

        # Get final profiles
        profile_a_final = final_state.entities["C001"].ideology
        profile_b_final = final_state.entities["C002"].ideology

        # Calculate deltas
        a_class_delta = profile_a_final.class_consciousness - profile_a_initial.class_consciousness
        a_nation_delta = profile_a_final.national_identity - profile_a_initial.national_identity
        b_class_delta = profile_b_final.class_consciousness - profile_b_initial.class_consciousness
        b_nation_delta = profile_b_final.national_identity - profile_b_initial.national_identity

        # SYMMETRY ASSERTIONS:
        # Worker A: class consciousness should increase more than national identity
        assert a_class_delta > a_nation_delta, (
            f"Worker A (with solidarity): class_delta ({a_class_delta}) "
            f"should exceed nation_delta ({a_nation_delta})"
        )

        # Worker B: national identity should increase more than class consciousness
        assert b_nation_delta > b_class_delta, (
            f"Worker B (isolated): nation_delta ({b_nation_delta}) "
            f"should exceed class_delta ({b_class_delta})"
        )

        # The key bifurcation: opposite routing of the same crisis energy
        # Worker A became more class conscious, Worker B became more nationalist
        assert profile_a_final.class_consciousness > profile_b_final.class_consciousness, (
            "Worker A should be more class conscious than Worker B after identical wage cuts"
        )
        assert profile_b_final.national_identity > profile_a_final.national_identity, (
            "Worker B should be more nationalist than Worker A after identical wage cuts"
        )
