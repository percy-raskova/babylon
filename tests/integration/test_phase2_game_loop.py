"""Integration tests for Phase 2 game loop.

These tests prove that the feedback loops work correctly over multiple ticks.
They verify the core thesis: Graph + Math = History.

Sprint 6: Phase 2 integration testing.
"""

import pytest

from babylon.engine.scenarios import (
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
)
from babylon.engine.simulation_engine import step

# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


@pytest.mark.integration
class TestCreateTwoNodeScenario:
    """Tests for the two-node factory function."""

    def test_creates_state_and_config(self) -> None:
        """Factory returns both state and config."""
        state, config = create_two_node_scenario()
        assert state is not None
        assert config is not None

    def test_state_has_two_entities(self) -> None:
        """State has exactly two entities."""
        state, _ = create_two_node_scenario()
        assert len(state.entities) == 2
        assert "C001" in state.entities  # Worker
        assert "C002" in state.entities  # Owner

    def test_state_has_one_relationship(self) -> None:
        """State has exactly one relationship (exploitation edge)."""
        state, _ = create_two_node_scenario()
        assert len(state.relationships) == 1
        assert state.relationships[0].source_id == "C001"
        assert state.relationships[0].target_id == "C002"

    def test_custom_parameters_applied(self) -> None:
        """Custom parameters are applied correctly."""
        state, config = create_two_node_scenario(
            worker_wealth=0.3,
            owner_wealth=0.7,
            extraction_efficiency=0.6,
        )
        assert state.entities["C001"].wealth == 0.3
        assert state.entities["C002"].wealth == 0.7
        assert config.extraction_efficiency == 0.6

    def test_state_starts_at_tick_zero(self) -> None:
        """State starts at tick 0."""
        state, _ = create_two_node_scenario()
        assert state.tick == 0


# =============================================================================
# RENT SPIRAL FEEDBACK LOOP TESTS
# =============================================================================


@pytest.mark.integration
class TestRentSpiralFeedbackLoop:
    """Tests for the Rent Spiral feedback loop.

    Over time, extraction should impoverish the worker:
    Economy extracts rent → Worker wealth drops → P(S|A) drops →
    Revolution becomes rational → Tension rises
    """

    def test_rent_extraction_impoverishes_worker(self) -> None:
        """Worker wealth decreases over time due to extraction.

        Note: With consciousness drift active, extraction slows as the worker
        becomes more class-conscious and resists. The worker still loses wealth,
        but the rate depends on how quickly consciousness develops.
        """
        state, config = create_two_node_scenario()
        initial_wealth = state.entities["C001"].wealth

        for _ in range(50):
            state = step(state, config)

        # Worker should be poorer (less than initial, accounting for resistance)
        assert state.entities["C001"].wealth < initial_wealth

    def test_rent_extraction_enriches_owner(self) -> None:
        """Owner wealth increases over time from extraction.

        Note: With consciousness drift active, extraction slows as workers
        develop class consciousness. The owner still gains wealth, but the
        amount depends on how quickly workers resist.
        """
        state, config = create_two_node_scenario()
        initial_wealth = state.entities["C002"].wealth

        for _ in range(50):
            state = step(state, config)

        # Owner should be richer (more than initial, accounting for resistance)
        assert state.entities["C002"].wealth > initial_wealth

    def test_acquiescence_drops_as_wealth_drops(self) -> None:
        """P(S|A) drops as worker becomes poorer."""
        state, config = create_two_node_scenario()

        # Initial acquiescence
        state = step(state, config)
        initial_p_acq = state.entities["C001"].p_acquiescence

        # Run until worker is poor
        for _ in range(50):
            state = step(state, config)

        # Acquiescence should drop (harder to survive through compliance)
        assert state.entities["C001"].p_acquiescence < initial_p_acq

    def test_tension_increases_with_wealth_gap(self) -> None:
        """Tension on exploitation edge increases as wealth gap grows."""
        state, config = create_two_node_scenario()

        for _ in range(50):
            state = step(state, config)

        # Tension should have accumulated
        assert state.relationships[0].tension > 0.1


# =============================================================================
# REPRESSION TRAP FEEDBACK LOOP TESTS
# =============================================================================


@pytest.mark.integration
class TestRepressionTrapFeedbackLoop:
    """Tests for the Repression Trap feedback loop.

    High repression delays revolution but doesn't prevent it:
    Repression increases → P(S|R) drops → Workers comply short-term →
    But extraction continues → Eventually P(S|A) < P(S|R)
    """

    def test_high_repression_keeps_p_revolution_low(self) -> None:
        """High repression keeps P(S|R) low."""
        state, config = create_two_node_scenario(repression_level=0.9)
        state = step(state, config)

        # P(S|R) should be low with high repression
        assert state.entities["C001"].p_revolution < 0.3

    def test_low_repression_allows_higher_p_revolution(self) -> None:
        """Low repression allows higher P(S|R)."""
        state, config = create_two_node_scenario(
            repression_level=0.1,
            worker_organization=0.5,  # Better organized
        )
        state = step(state, config)

        # P(S|R) should be higher with low repression
        assert state.entities["C001"].p_revolution > 0.5

    def test_repression_delays_crossover(self) -> None:
        """High repression delays the crossover point (P(S|R) > P(S|A))."""
        # Low repression scenario
        state_low, config_low = create_two_node_scenario(
            repression_level=0.2,
            worker_organization=0.3,
        )

        # High repression scenario
        state_high, config_high = create_two_node_scenario(
            repression_level=0.8,
            worker_organization=0.3,
        )

        crossover_tick_low = None
        crossover_tick_high = None

        for tick in range(200):
            state_low = step(state_low, config_low)
            state_high = step(state_high, config_high)

            worker_low = state_low.entities["C001"]
            worker_high = state_high.entities["C001"]

            if crossover_tick_low is None and worker_low.p_revolution > worker_low.p_acquiescence:
                crossover_tick_low = tick

            if (
                crossover_tick_high is None
                and worker_high.p_revolution > worker_high.p_acquiescence
            ):
                crossover_tick_high = tick

            if crossover_tick_low is not None and crossover_tick_high is not None:
                break

        # If crossover happens, high repression should delay it
        if crossover_tick_low is not None and crossover_tick_high is not None:
            assert crossover_tick_high > crossover_tick_low


# =============================================================================
# DETERMINISM TESTS
# =============================================================================


@pytest.mark.integration
class TestGameLoopDeterminism:
    """Tests proving the game loop is deterministic."""

    def test_identical_trajectories(self) -> None:
        """Two runs with same initial state produce identical results."""
        state1, config = create_two_node_scenario()
        state2 = state1  # Same starting point

        # Run both for 100 ticks
        for _ in range(100):
            state1 = step(state1, config)
            state2 = step(state2, config)

        # Should be identical
        assert state1.tick == state2.tick == 100
        assert state1.entities["C001"].wealth == pytest.approx(state2.entities["C001"].wealth)
        assert state1.entities["C002"].wealth == pytest.approx(state2.entities["C002"].wealth)
        assert state1.relationships[0].tension == pytest.approx(state2.relationships[0].tension)

    def test_parameter_changes_cause_different_trajectories(self) -> None:
        """Different parameters produce different outcomes."""
        state_base, config_base = create_two_node_scenario(extraction_efficiency=0.3)
        state_high, config_high = create_two_node_scenario(extraction_efficiency=0.9)

        # Run 5 ticks to see differences in worker wealth
        for _ in range(5):
            state_base = step(state_base, config_base)
            state_high = step(state_high, config_high)

        # Different extraction rates should lead to different worker wealth
        # (worker with low extraction should have more wealth remaining)
        worker_base = state_base.entities["C001"].wealth
        worker_high = state_high.entities["C001"].wealth

        # Worker under high extraction should have less wealth
        assert (
            worker_base > worker_high * 1.5
        ), f"Expected worker_base ({worker_base}) > worker_high ({worker_high}) * 1.5"


# =============================================================================
# LONG-RUN STABILITY TESTS
# =============================================================================


@pytest.mark.integration
class TestLongRunStability:
    """Tests proving the simulation remains stable over long runs."""

    def test_no_nan_or_inf_after_1000_ticks(self) -> None:
        """No NaN or Inf values appear after 1000 ticks."""
        state, config = create_two_node_scenario()

        for _ in range(1000):
            state = step(state, config)

            # Check for NaN/Inf in all numeric fields
            for entity in state.entities.values():
                assert entity.wealth >= 0, "Wealth went negative"
                assert entity.wealth < float("inf"), "Wealth is infinite"
                # Check class_consciousness is in valid range [0, 1]
                assert (
                    0 <= entity.ideology.class_consciousness <= 1
                ), "class_consciousness out of bounds"
                assert 0 <= entity.p_acquiescence <= 1, "P(S|A) out of bounds"
                assert 0 <= entity.p_revolution <= 1, "P(S|R) out of bounds"

            for rel in state.relationships:
                assert rel.value_flow >= 0, "Value flow negative"
                assert 0 <= rel.tension <= 1, "Tension out of bounds"

    def test_wealth_conserved_over_1000_ticks(self) -> None:
        """Total wealth is conserved over 1000 ticks."""
        state, config = create_two_node_scenario()
        initial_total = sum(e.wealth for e in state.entities.values())

        for _ in range(1000):
            state = step(state, config)

        final_total = sum(e.wealth for e in state.entities.values())
        assert final_total == pytest.approx(initial_total, rel=0.001)


# =============================================================================
# SCENARIO VARIANT TESTS
# =============================================================================


@pytest.mark.integration
class TestScenarioVariants:
    """Tests for specialized scenario factories."""

    def test_high_tension_scenario_starts_tensioned(self) -> None:
        """High tension scenario starts with elevated tension."""
        state, _ = create_high_tension_scenario()
        assert state.relationships[0].tension >= 0.7

    def test_high_tension_scenario_near_rupture(self) -> None:
        """High tension scenario can reach rupture quickly."""
        state, config = create_high_tension_scenario()

        for _ in range(100):
            state = step(state, config)
            if state.relationships[0].tension >= 1.0:
                break

        # Should reach rupture within 100 ticks
        assert state.relationships[0].tension >= 0.9

    def test_labor_aristocracy_scenario_worker_wealthy(self) -> None:
        """Labor aristocracy scenario has wealthy worker."""
        state, _ = create_labor_aristocracy_scenario()
        assert state.entities["C001"].wealth >= 0.7


# =============================================================================
# SUCCESS CRITERIA TEST (THE BIG ONE)
# =============================================================================


@pytest.mark.integration
class TestPhase2SuccessCriteria:
    """The ultimate test: proving Phase 2 works as designed.

    Success Criteria from the plan:
    1. Run 100 turns with deterministic outcomes
    2. Observe predictable state transitions based on parameters
    3. Verify feedback loops produce compounding effects
    """

    def test_phase2_success_criteria(self) -> None:
        """THE CORE TEST: Run 100 turns, verify deterministic outcomes."""
        # Setup scenario
        state, config = create_two_node_scenario(
            worker_wealth=0.5,
            owner_wealth=0.5,
            extraction_efficiency=0.8,
            repression_level=0.5,
        )

        # Run 100 turns
        for _ in range(100):
            state = step(state, config)

        # Verify determinism (can re-run from same state)
        state2, _ = create_two_node_scenario(
            worker_wealth=0.5,
            owner_wealth=0.5,
            extraction_efficiency=0.8,
            repression_level=0.5,
        )
        for _ in range(100):
            state2 = step(state2, config)

        # Same inputs -> Same outputs
        assert state.tick == state2.tick == 100
        assert state.entities["C001"].wealth == pytest.approx(state2.entities["C001"].wealth)
        assert state.entities["C002"].wealth == pytest.approx(state2.entities["C002"].wealth)

        # Verify predictable state transitions
        # After 100 ticks of extraction, worker should be poorer, owner richer
        assert state.entities["C001"].wealth < 0.5  # Worker lost wealth
        assert state.entities["C002"].wealth > 0.5  # Owner gained wealth

        # Tension should have accumulated
        assert state.relationships[0].tension > 0

        # Probabilities should be calculated
        assert state.entities["C001"].p_acquiescence > 0
        assert state.entities["C001"].p_revolution > 0

        # Print summary for human verification
        print("\n=== PHASE 2 SUCCESS CRITERIA MET ===")
        print(f"Final tick: {state.tick}")
        print(f"Worker wealth: {state.entities['C001'].wealth:.4f}")
        print(f"Owner wealth: {state.entities['C002'].wealth:.4f}")
        print(f"Tension: {state.relationships[0].tension:.4f}")
        print(f"P(S|A): {state.entities['C001'].p_acquiescence:.4f}")
        print(f"P(S|R): {state.entities['C001'].p_revolution:.4f}")
        print("=====================================")


# =============================================================================
# CONSCIOUSNESS FEEDBACK LOOP TESTS
# =============================================================================


@pytest.mark.integration
class TestConsciousnessFeedbackLoop:
    """Tests for the Consciousness feedback loop.

    Revolutionary workers resist extraction more effectively:
    Extraction -> Consciousness rises -> Future extraction reduced
    """

    def test_revolutionary_worker_resists_extraction(self) -> None:
        """Revolutionary worker (-1 ideology) loses less wealth than reactionary."""
        # Revolutionary worker scenario
        rev_state, config = create_two_node_scenario(
            worker_wealth=0.5,
            worker_ideology=-0.9,  # Near revolutionary
        )

        # Reactionary worker scenario
        react_state, _ = create_two_node_scenario(
            worker_wealth=0.5,
            worker_ideology=0.9,  # Near reactionary
        )

        # Run both for same number of ticks
        for _ in range(10):
            rev_state = step(rev_state, config)
            react_state = step(react_state, config)

        # Revolutionary worker should have MORE wealth remaining
        # (they resisted extraction via consciousness)
        assert rev_state.entities["C001"].wealth > react_state.entities["C001"].wealth

    def test_consciousness_drift_reduces_future_extraction(self) -> None:
        """As worker becomes more revolutionary, extraction decreases.

        Sprint 3.4.3: This test verifies that revolutionary workers (high
        class_consciousness) resist extraction more effectively than
        reactionary workers (low class_consciousness).
        """
        # Revolutionary worker (high consciousness) should lose less wealth
        rev_state, config = create_two_node_scenario(
            worker_ideology=-0.9,  # Revolutionary (class_consciousness ~0.95)
        )

        # Reactionary worker (low consciousness) should lose more wealth
        react_state, _ = create_two_node_scenario(
            worker_ideology=0.9,  # Reactionary (class_consciousness ~0.05)
        )

        # Run both for 100 ticks
        for _ in range(100):
            rev_state = step(rev_state, config)
            react_state = step(react_state, config)

        # Revolutionary worker should have retained more wealth
        # because consciousness affects extraction resistance
        rev_wealth = rev_state.entities["C001"].wealth
        react_wealth = react_state.entities["C001"].wealth

        assert rev_wealth > react_wealth, (
            f"Revolutionary worker ({rev_wealth}) should retain more wealth "
            f"than reactionary worker ({react_wealth})"
        )
