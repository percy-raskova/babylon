"""Tests for babylon.engine.simulation_engine.

TDD Red Phase: These tests define the contract for the step() function.
The step() function is the heart of Phase 2 - it transforms WorldState
deterministically through one simulation tick.

Sprint 5: SimulationEngine for Phase 2 game loop.
"""

import pytest

from babylon.engine.simulation_engine import step
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,  # Neutral
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Core Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=0.5,
        ideology=0.0,
        organization=0.8,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.0,
    )


@pytest.fixture
def two_node_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


# =============================================================================
# TICK INCREMENT TESTS
# =============================================================================


@pytest.mark.integration
class TestStepTickIncrement:
    """step() should increment the tick counter."""

    def test_step_increments_tick(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() increments tick by 1."""
        new_state = step(two_node_state, config)
        assert new_state.tick == 1

    def test_step_increments_from_nonzero(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """step() increments from any starting tick."""
        state = WorldState(
            tick=42,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
        )
        new_state = step(state, config)
        assert new_state.tick == 43

    def test_step_returns_new_state(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() returns a new WorldState, not mutating original."""
        new_state = step(two_node_state, config)
        assert new_state is not two_node_state
        assert two_node_state.tick == 0  # Original unchanged


# =============================================================================
# IMPERIAL RENT EXTRACTION TESTS
# =============================================================================


@pytest.mark.integration
class TestStepImperialRent:
    """step() should extract imperial rent from exploitation edges."""

    def test_step_extracts_rent_from_worker(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Worker loses wealth through imperial rent extraction."""
        initial_worker_wealth = two_node_state.entities["C001"].wealth
        new_state = step(two_node_state, config)
        assert new_state.entities["C001"].wealth < initial_worker_wealth

    def test_step_transfers_rent_to_owner(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Owner gains wealth from imperial rent extraction."""
        initial_owner_wealth = two_node_state.entities["C002"].wealth
        new_state = step(two_node_state, config)
        assert new_state.entities["C002"].wealth > initial_owner_wealth

    def test_step_rent_is_zero_sum(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Total wealth is conserved (rent is transferred, not created)."""
        initial_total = sum(e.wealth for e in two_node_state.entities.values())
        new_state = step(two_node_state, config)
        final_total = sum(e.wealth for e in new_state.entities.values())
        assert final_total == pytest.approx(initial_total)

    def test_step_records_value_flow(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() records value_flow on the exploitation edge."""
        new_state = step(two_node_state, config)
        assert len(new_state.relationships) == 1
        assert new_state.relationships[0].value_flow > 0

    def test_step_higher_extraction_means_more_rent(
        self,
        two_node_state: WorldState,
    ) -> None:
        """Higher extraction efficiency extracts more rent."""
        low_config = SimulationConfig(extraction_efficiency=0.3)
        high_config = SimulationConfig(extraction_efficiency=0.9)

        low_state = step(two_node_state, low_config)
        high_state = step(two_node_state, high_config)

        low_rent = low_state.relationships[0].value_flow
        high_rent = high_state.relationships[0].value_flow

        assert high_rent > low_rent


# =============================================================================
# SURVIVAL PROBABILITY TESTS
# =============================================================================


@pytest.mark.integration
class TestStepSurvivalProbabilities:
    """step() should update survival probabilities."""

    def test_step_updates_p_acquiescence(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() calculates P(S|A) for each entity."""
        new_state = step(two_node_state, config)
        # Worker should have some acquiescence probability
        assert new_state.entities["C001"].p_acquiescence > 0

    def test_step_updates_p_revolution(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() calculates P(S|R) for each entity."""
        new_state = step(two_node_state, config)
        # Worker should have some revolution probability
        assert new_state.entities["C001"].p_revolution > 0

    def test_step_wealthy_has_high_acquiescence(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Wealthy entities have high P(S|A)."""
        rich_worker = SocialClass(
            id="C001",
            name="Rich Worker",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.9,  # Very wealthy
            subsistence_threshold=0.3,
            organization=0.1,
            repression_faced=0.5,
        )
        state = WorldState(
            tick=0,
            entities={"C001": rich_worker, "C002": owner},
            relationships=[exploitation_edge],
        )
        new_state = step(state, config)
        # High wealth -> high acquiescence probability
        assert new_state.entities["C001"].p_acquiescence > 0.7


# =============================================================================
# CONTRADICTION TENSION TESTS
# =============================================================================


@pytest.mark.integration
class TestStepContradictionTension:
    """step() should update contradiction tension on edges."""

    def test_step_increases_tension(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Extraction increases tension on the exploitation edge."""
        new_state = step(two_node_state, config)
        assert new_state.relationships[0].tension > 0

    def test_step_tension_accumulates(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Tension accumulates over multiple ticks."""
        state = two_node_state
        for _ in range(10):
            state = step(state, config)

        assert state.relationships[0].tension > 0


# =============================================================================
# DETERMINISM TESTS
# =============================================================================


@pytest.mark.integration
class TestStepDeterminism:
    """step() should be deterministic: same inputs -> same outputs."""

    def test_single_step_deterministic(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Single step produces identical results."""
        result1 = step(two_node_state, config)
        result2 = step(two_node_state, config)

        assert result1.tick == result2.tick
        assert result1.entities["C001"].wealth == pytest.approx(result2.entities["C001"].wealth)
        assert result1.entities["C002"].wealth == pytest.approx(result2.entities["C002"].wealth)

    def test_hundred_turns_deterministic(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """100 turns produce identical results."""
        # Run 1
        result1 = two_node_state
        for _ in range(100):
            result1 = step(result1, config)

        # Run 2 (same starting state)
        result2 = two_node_state
        for _ in range(100):
            result2 = step(result2, config)

        # Compare final states
        assert result1.tick == result2.tick == 100
        assert result1.entities["C001"].wealth == pytest.approx(result2.entities["C001"].wealth)
        assert result1.entities["C002"].wealth == pytest.approx(result2.entities["C002"].wealth)
        assert result1.entities["C001"].ideology == pytest.approx(result2.entities["C001"].ideology)


# =============================================================================
# EVENT LOG TESTS
# =============================================================================


@pytest.mark.integration
class TestStepEventLog:
    """step() should log significant events."""

    def test_step_preserves_existing_events(
        self,
        worker: SocialClass,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """step() preserves existing event log entries."""
        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation_edge],
            event_log=["Previous event"],
        )
        new_state = step(state, config)
        assert "Previous event" in new_state.event_log


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.integration
class TestStepEdgeCases:
    """step() should handle edge cases gracefully."""

    def test_step_empty_state(self, config: SimulationConfig) -> None:
        """step() handles state with no entities."""
        empty_state = WorldState(tick=0)
        new_state = step(empty_state, config)
        assert new_state.tick == 1
        assert len(new_state.entities) == 0

    def test_step_no_relationships(
        self,
        worker: SocialClass,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """step() handles state with entities but no relationships."""
        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[],
        )
        new_state = step(state, config)
        assert new_state.tick == 1
        # Wealth unchanged without extraction edges
        assert new_state.entities["C001"].wealth == worker.wealth

    def test_step_wealth_cannot_go_negative(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Worker wealth cannot go below 0."""
        poor_worker = SocialClass(
            id="C001",
            name="Poor Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.01,  # Nearly broke
            ideology=0.0,
            organization=0.1,
            repression_faced=0.5,
        )
        state = WorldState(
            tick=0,
            entities={"C001": poor_worker, "C002": owner},
            relationships=[exploitation_edge],
        )
        # Run multiple steps
        for _ in range(100):
            state = step(state, config)

        assert state.entities["C001"].wealth >= 0


# =============================================================================
# CONSCIOUSNESS DRIFT TESTS
# =============================================================================


@pytest.mark.integration
class TestStepConsciousnessDrift:
    """step() should update ideology based on consciousness drift formula.

    Consciousness drift models how material conditions affect ideology:
    dPsi/dt = k(1 - W/V) - lambda * Psi

    Where:
    - W = wages (worker wealth)
    - V = value produced (sum of value_flow on outgoing EXPLOITATION edges)
    - k = consciousness_sensitivity
    - lambda = consciousness_decay_lambda
    - Psi = consciousness, mapped from ideology: Psi = (1 - ideology) / 2

    When W < V (exploitation), consciousness increases (ideology drifts toward -1).
    """

    def test_exploited_worker_drifts_revolutionary(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Worker ideology decreases (toward -1) after step() due to exploitation.

        The worker is being exploited (wealth extracted), so their consciousness
        should increase, which means ideology should drift toward -1.
        """
        initial_ideology = two_node_state.entities["C001"].ideology

        # Run one step - extraction happens, then consciousness drift
        new_state = step(two_node_state, config)

        # Worker should be drifting revolutionary (ideology decreasing)
        assert new_state.entities["C001"].ideology < initial_ideology

    def test_owner_ideology_unchanged(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Owner has no outgoing exploitation edges, so ideology stays same.

        The owner is at the receiving end of exploitation (target, not source).
        They have no outgoing EXPLOITATION edges, so value_produced = 0.
        Consciousness drift should skip them.
        """
        initial_owner_ideology = two_node_state.entities["C002"].ideology

        new_state = step(two_node_state, config)

        # Owner ideology unchanged (no outgoing exploitation edges)
        assert new_state.entities["C002"].ideology == pytest.approx(initial_owner_ideology)

    def test_no_edges_no_drift(
        self,
        worker: SocialClass,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Without exploitation edges, ideology is unchanged.

        If there are no exploitation edges, no value is being extracted,
        so there's no basis for consciousness drift.
        """
        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[],  # No edges
        )
        initial_worker_ideology = state.entities["C001"].ideology

        new_state = step(state, config)

        # No drift without exploitation edges
        assert new_state.entities["C001"].ideology == pytest.approx(initial_worker_ideology)

    def test_ideology_clamped_lower_bound(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Ideology cannot go below -1.0 even over 1000 ticks.

        The ideology field is constrained to [-1, 1]. Even with continuous
        drift, ideology must be clamped to prevent validation errors.
        """
        # Start already revolutionary to stress test the lower bound
        revolutionary_worker = SocialClass(
            id="C001",
            name="Revolutionary Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=-0.9,  # Already very revolutionary
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        state = WorldState(
            tick=0,
            entities={"C001": revolutionary_worker, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Run 1000 ticks
        for _ in range(1000):
            state = step(state, config)

        # Ideology must stay >= -1.0
        assert state.entities["C001"].ideology >= -1.0

    def test_ideology_clamped_upper_bound(
        self,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Ideology cannot exceed +1.0 (use labor aristocrat scenario).

        A labor aristocrat receiving more than they produce should have
        consciousness decay, but ideology must stay <= 1.0.
        """
        # Labor aristocrat with high (reactionary) ideology
        labor_aristocrat = SocialClass(
            id="C001",
            name="Labor Aristocrat",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.9,  # High wages
            ideology=0.9,  # Already very reactionary
            organization=0.1,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )
        # Labor aristocrat exploiting periphery
        exploitation_edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )
        state = WorldState(
            tick=0,
            entities={"C001": labor_aristocrat, "C002": owner},
            relationships=[exploitation_edge],
        )

        # Run 1000 ticks
        for _ in range(1000):
            state = step(state, config)

        # Ideology must stay <= 1.0
        assert state.entities["C001"].ideology <= 1.0

    def test_higher_sensitivity_faster_drift(
        self,
        two_node_state: WorldState,
    ) -> None:
        """Higher consciousness_sensitivity = faster ideological change.

        The sensitivity parameter k controls how quickly material conditions
        translate into consciousness change. Higher k = faster drift.
        """
        low_sensitivity_config = SimulationConfig(consciousness_sensitivity=0.1)
        high_sensitivity_config = SimulationConfig(consciousness_sensitivity=0.9)

        low_state = step(two_node_state, low_sensitivity_config)
        high_state = step(two_node_state, high_sensitivity_config)

        low_drift = abs(
            low_state.entities["C001"].ideology - two_node_state.entities["C001"].ideology
        )
        high_drift = abs(
            high_state.entities["C001"].ideology - two_node_state.entities["C001"].ideology
        )

        # Higher sensitivity should produce larger drift
        assert high_drift > low_drift

    def test_thousand_tick_stability(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Ideology stays bounded [-1, 1] over 1000 ticks.

        This is a stability test to ensure no numerical drift causes
        ideology to escape valid bounds over long simulations.
        """
        state = two_node_state
        for _ in range(1000):
            state = step(state, config)

        # All ideologies must be in valid range
        for entity_id, entity in state.entities.items():
            assert (
                -1.0 <= entity.ideology <= 1.0
            ), f"Entity {entity_id} ideology {entity.ideology} out of bounds"


# =============================================================================
# TENSION RATE TESTS
# =============================================================================


@pytest.mark.integration
class TestStepTensionRate:
    """step() tension accumulation should be configurable."""

    def test_default_tension_rate(
        self,
        config: SimulationConfig,
    ) -> None:
        """Default tension rate should be 0.05."""
        assert config.tension_accumulation_rate == 0.05

    def test_higher_rate_faster_tension(
        self,
        two_node_state: WorldState,
    ) -> None:
        """Higher tension rate means faster accumulation."""
        low_rate = SimulationConfig(tension_accumulation_rate=0.01)
        high_rate = SimulationConfig(tension_accumulation_rate=0.1)

        # Run same starting state with both rates
        state_low = two_node_state
        state_high = two_node_state

        for _ in range(10):
            state_low = step(state_low, low_rate)
            state_high = step(state_high, high_rate)

        # Higher rate should accumulate more tension
        assert state_high.relationships[0].tension > state_low.relationships[0].tension

    def test_zero_rate_no_tension_accumulation(
        self,
        two_node_state: WorldState,
    ) -> None:
        """Zero tension rate means no accumulation (frozen)."""
        config = SimulationConfig(tension_accumulation_rate=0.0)
        initial_tension = two_node_state.relationships[0].tension

        state = step(two_node_state, config)

        assert state.relationships[0].tension == initial_tension
