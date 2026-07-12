"""Integration tests for babylon.engine.simulation_engine.

Tests the step() function through full simulation engine execution with
all Systems (ImperialRent, Solidarity, Consciousness, Survival, etc.)
running in sequence.

Extracted from tests/unit/engine/test_simulation_engine.py
"""

import pytest

from babylon.config.defines import EconomyDefines, GameDefines, TensionDefines
from babylon.engine.simulation_engine import step
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    PERIPHERY_WORKER_ID,
)
from tests.assertions import Assert
from tests.factories import DomainFactory

# =============================================================================
# FIXTURES (using DomainFactory)
# =============================================================================

_factory = DomainFactory()


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return _factory.create_worker(name="Periphery Worker")


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class.

    CRITICAL: This fixture uses non-standard values from the original test:
    - wealth=0.5 (DomainFactory default is 10.0)
    - ideology=0.0 (DomainFactory default is 0.5)
    - organization=0.8 (DomainFactory default is 0.7)
    """
    return _factory.create_owner(
        name="Core Owner",
        wealth=0.5,
        ideology=0.0,
        organization=0.8,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return _factory.create_relationship()


@pytest.fixture
def two_node_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return _factory.create_world_state(
        entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
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
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
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
        new_state = step(two_node_state, config)
        Assert(new_state).entity(PERIPHERY_WORKER_ID).is_poorer_than(two_node_state)

    def test_step_transfers_rent_to_owner(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Owner gains wealth from imperial rent extraction.

        Uses base_subsistence=0.0 to isolate rent transfer mechanics
        from subsistence costs (The Calorie Check).
        """
        # Isolate rent mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))
        new_state = step(two_node_state, config, defines=no_subsistence_defines)
        Assert(new_state).entity(COMPRADOR_ID).is_richer_than(two_node_state)

    def test_step_rent_is_zero_sum(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Total wealth is conserved when testing rent transfer in isolation.

        Uses base_subsistence=0.0 to test that rent transfer is zero-sum.
        With subsistence > 0, total wealth decreases each tick (The Calorie Check).
        """
        # Isolate rent mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))
        initial_total = sum(e.wealth for e in two_node_state.entities.values())
        new_state = step(two_node_state, config, defines=no_subsistence_defines)
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
        Assert(new_state).relationship(PERIPHERY_WORKER_ID, COMPRADOR_ID).has_value_flow()

    def test_step_higher_extraction_means_more_rent(
        self,
        two_node_state: WorldState,
    ) -> None:
        """Higher extraction efficiency extracts more rent."""
        config = SimulationConfig()
        # Paradox Refactor: extraction_efficiency now in GameDefines, not SimulationConfig
        low_defines = GameDefines(economy=EconomyDefines(extraction_efficiency=0.3))
        high_defines = GameDefines(economy=EconomyDefines(extraction_efficiency=0.9))

        low_state = step(two_node_state, config, defines=low_defines)
        high_state = step(two_node_state, config, defines=high_defines)

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
        Assert(new_state).entity(PERIPHERY_WORKER_ID).has_p_acquiescence(0.0)

    def test_step_updates_p_revolution(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() calculates P(S|R) for each entity."""
        new_state = step(two_node_state, config)
        # Worker should have some revolution probability
        Assert(new_state).entity(PERIPHERY_WORKER_ID).has_p_revolution(0.0)

    def test_step_wealthy_has_high_acquiescence(
        self,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Wealthy entities have high P(S|A)."""
        rich_worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Rich Worker",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.9,  # Very wealthy
            subsistence_threshold=0.3,
            organization=0.1,
            repression_faced=0.5,
        )
        # No exploitation edge - just test wealth -> acquiescence relationship
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: rich_worker, COMPRADOR_ID: owner},
            relationships=[],  # No edges - wealth stays constant
        )
        new_state = step(state, config)
        # High wealth -> high acquiescence probability
        Assert(new_state).entity(PERIPHERY_WORKER_ID).has_p_acquiescence(0.7)


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
        Assert(new_state).relationship(PERIPHERY_WORKER_ID, COMPRADOR_ID).has_tension_increased(
            two_node_state
        )

    def test_step_tension_accumulates(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Tension accumulates over multiple ticks."""
        state = two_node_state
        for _ in range(10):
            state = step(state, config)

        Assert(state).relationship(PERIPHERY_WORKER_ID, COMPRADOR_ID).has_tension_increased(
            two_node_state
        )


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
        assert result1.entities[PERIPHERY_WORKER_ID].wealth == pytest.approx(
            result2.entities[PERIPHERY_WORKER_ID].wealth
        )
        assert result1.entities[COMPRADOR_ID].wealth == pytest.approx(
            result2.entities[COMPRADOR_ID].wealth
        )

    # NOTE: test_hundred_turns_deterministic moved to
    # tests/integration/system/test_simulation_stability.py (slow test)


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
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
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
        """step() handles state with entities but no relationships.

        Uses base_subsistence=0.0 to test that wealth is unchanged without
        extraction edges. With subsistence > 0, entities lose wealth each tick
        regardless of relationships (The Calorie Check).
        """
        # Isolate relationship mechanics from subsistence deductions
        no_subsistence_defines = GameDefines(economy=EconomyDefines(base_subsistence=0.0))
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
            relationships=[],
        )
        new_state = step(state, config, defines=no_subsistence_defines)
        Assert(new_state).tick_is(1)
        # Wealth unchanged without extraction edges (subsistence disabled)
        Assert(new_state).entity(PERIPHERY_WORKER_ID).wealth_unchanged_from(state)

    @pytest.mark.slow
    def test_step_wealth_cannot_go_negative(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Worker wealth cannot go below 0."""
        poor_worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Poor Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.01,  # Nearly broke
            ideology=0.0,
            organization=0.1,
            repression_faced=0.5,
        )
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: poor_worker, COMPRADOR_ID: owner},
            relationships=[exploitation_edge],
        )
        # Run multiple steps
        for _ in range(100):
            state = step(state, config)

        assert state.entities[PERIPHERY_WORKER_ID].wealth >= 0


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
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Worker class_consciousness increases after step() due to falling wages.

        Sprint 3.4.3: Consciousness drift now uses WAGES edges and wage_change,
        not direct exploitation. This test verifies that falling wages cause
        revolutionary drift when there's solidarity infrastructure.
        """
        from babylon.models import IdeologicalProfile

        # Create worker with initial WAGES that will be cut
        worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=IdeologicalProfile(
                class_consciousness=0.5, national_identity=0.5, agitation=0.0
            ),
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )

        # Create a solidarity source (periphery worker with high consciousness)
        periphery_worker = SocialClass(
            id=CORE_BOURGEOISIE_ID,
            name="Solidarity Source",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.2,
            ideology=IdeologicalProfile(
                class_consciousness=0.9, national_identity=0.1, agitation=0.0
            ),
        )

        # WAGES edge from owner to worker (will be cut next tick)
        wages_edge = Relationship(
            source_id=COMPRADOR_ID,
            target_id=PERIPHERY_WORKER_ID,
            edge_type=EdgeType.WAGES,
            value_flow=50.0,
        )

        # SOLIDARITY edge from periphery to worker
        solidarity_edge = Relationship(
            source_id=CORE_BOURGEOISIE_ID,
            target_id=PERIPHERY_WORKER_ID,
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        state = WorldState(
            tick=0,
            entities={
                PERIPHERY_WORKER_ID: worker,
                COMPRADOR_ID: owner,
                CORE_BOURGEOISIE_ID: periphery_worker,
            },
            relationships=[wages_edge, solidarity_edge],
        )

        # Run first tick to establish wage baseline
        state = step(state, config)
        initial_consciousness = state.entities[PERIPHERY_WORKER_ID].ideology.class_consciousness

        # Cut wages and run another tick
        reduced_wages = Relationship(
            source_id=COMPRADOR_ID,
            target_id=PERIPHERY_WORKER_ID,
            edge_type=EdgeType.WAGES,
            value_flow=30.0,  # 40% wage cut
        )
        state_with_cut = WorldState(
            tick=state.tick,
            entities=state.entities,
            relationships=[reduced_wages, solidarity_edge],
        )
        final_state = step(state_with_cut, config)

        # Worker should drift revolutionary (class_consciousness increasing) with solidarity
        assert (
            final_state.entities[PERIPHERY_WORKER_ID].ideology.class_consciousness
            > initial_consciousness
        )

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
        new_state = step(two_node_state, config)

        # Owner class_consciousness unchanged (no outgoing exploitation edges)
        Assert(new_state).entity(COMPRADOR_ID).consciousness_unchanged_from(two_node_state)

    def test_no_edges_no_drift(
        self,
        worker: SocialClass,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Without exploitation edges, class_consciousness is unchanged.

        If there are no exploitation edges, no value is being extracted,
        so there's no basis for consciousness drift.
        """
        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
            relationships=[],  # No edges
        )

        new_state = step(state, config)

        # No drift without exploitation edges
        Assert(new_state).entity(PERIPHERY_WORKER_ID).consciousness_unchanged_from(state)

    # NOTE: test_ideology_clamped_lower_bound and test_ideology_clamped_upper_bound
    # moved to tests/integration/system/test_simulation_stability.py (slow tests)

    def test_higher_solidarity_strength_faster_transmission(
        self,
        owner: SocialClass,
    ) -> None:
        """Higher solidarity_strength = faster consciousness transmission.

        The SolidaritySystem transmits consciousness from revolutionary periphery
        workers to core workers. Higher solidarity_strength means more transmission.
        """
        from babylon.models import IdeologicalProfile

        config = SimulationConfig()

        def create_state_with_solidarity(strength: float) -> WorldState:
            # Core worker starts with low consciousness
            worker = SocialClass(
                id=PERIPHERY_WORKER_ID,
                name="Worker",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=0.5,
                ideology=IdeologicalProfile(
                    class_consciousness=0.1, national_identity=0.9, agitation=0.0
                ),
            )
            # Periphery worker has high consciousness (source of transmission)
            periphery = SocialClass(
                id=CORE_BOURGEOISIE_ID,
                name="Periphery",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=0.2,
                ideology=IdeologicalProfile(
                    class_consciousness=0.9, national_identity=0.1, agitation=0.0
                ),
            )
            solidarity = Relationship(
                source_id=CORE_BOURGEOISIE_ID,
                target_id=PERIPHERY_WORKER_ID,
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=strength,
            )
            return WorldState(
                tick=0,
                entities={
                    PERIPHERY_WORKER_ID: worker,
                    COMPRADOR_ID: owner,
                    CORE_BOURGEOISIE_ID: periphery,
                },
                relationships=[solidarity],
            )

        initial_consciousness = 0.1

        # Run one tick with different solidarity strengths
        low_state = step(create_state_with_solidarity(0.2), config)
        high_state = step(create_state_with_solidarity(0.8), config)

        low_drift = (
            low_state.entities[PERIPHERY_WORKER_ID].ideology.class_consciousness
            - initial_consciousness
        )
        high_drift = (
            high_state.entities[PERIPHERY_WORKER_ID].ideology.class_consciousness
            - initial_consciousness
        )

        # Higher solidarity strength should produce larger consciousness drift
        assert high_drift > low_drift
        # Both should have increased from initial
        assert low_drift > 0
        assert high_drift > 0

    # NOTE: test_thousand_tick_stability moved to
    # tests/integration/system/test_simulation_stability.py (slow test)


# =============================================================================
# TENSION RATE TESTS
# =============================================================================


@pytest.mark.integration
class TestStepTensionRate:
    """step() tension accumulation should be configurable."""

    def test_tension_decoupled_from_accumulation_rate(
        self,
        two_node_state: WorldState,
    ) -> None:
        """C1.3: per-edge tension is the FRESH wealth-asymmetry gap, not an
        add-only accumulator, so it no longer depends on
        ``tension.accumulation_rate`` — two rates yield identical tension."""
        config = SimulationConfig()
        low_rate_defines = GameDefines(tension=TensionDefines(accumulation_rate=0.01))
        high_rate_defines = GameDefines(tension=TensionDefines(accumulation_rate=0.1))

        # Run same starting state with both rates
        state_low = two_node_state
        state_high = two_node_state

        for _ in range(10):
            state_low = step(state_low, config, defines=low_rate_defines)
            state_high = step(state_high, config, defines=high_rate_defines)

        # Decoupled: the rate no longer moves the fresh-gap tension.
        assert state_high.relationships[0].tension == pytest.approx(
            state_low.relationships[0].tension
        )

    def test_zero_rate_does_not_freeze_tension(
        self,
        two_node_state: WorldState,
    ) -> None:
        """C1.3: tension is recomputed each tick as the live wealth-asymmetry
        gap, so ``accumulation_rate == 0`` does NOT freeze it at its initial
        value — it tracks the (non-zero) gap between the two poles."""
        config = SimulationConfig()
        defines = GameDefines(tension=TensionDefines(accumulation_rate=0.0))
        initial_tension = two_node_state.relationships[0].tension  # seeded at 0.0

        state = step(two_node_state, config, defines=defines)

        new_tension = state.relationships[0].tension
        assert new_tension != initial_tension  # moved off the frozen initial
        assert 0.0 < new_tension <= 1.0  # a real, bounded wealth-asymmetry gap
