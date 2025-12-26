"""Tests for babylon.engine.simulation_engine.

TDD Red Phase: These tests define the contract for the step() function.
The step() function is the heart of Phase 2 - it transforms WorldState
deterministically through one simulation tick.

Sprint 5: SimulationEngine for Phase 2 game loop.
"""

import pytest
from tests.assertions import Assert
from tests.factories import DomainFactory

from babylon.config.defines import EconomyDefines, GameDefines
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
        new_state = step(two_node_state, config)
        Assert(new_state).entity("C001").is_poorer_than(two_node_state)

    def test_step_transfers_rent_to_owner(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Owner gains wealth from imperial rent extraction."""
        new_state = step(two_node_state, config)
        Assert(new_state).entity("C002").is_richer_than(two_node_state)

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
        Assert(new_state).relationship("C001", "C002").has_value_flow()

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
        Assert(new_state).entity("C001").has_p_acquiescence(0.0)

    def test_step_updates_p_revolution(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() calculates P(S|R) for each entity."""
        new_state = step(two_node_state, config)
        # Worker should have some revolution probability
        Assert(new_state).entity("C001").has_p_revolution(0.0)

    def test_step_wealthy_has_high_acquiescence(
        self,
        owner: SocialClass,
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
        # No exploitation edge - just test wealth -> acquiescence relationship
        state = WorldState(
            tick=0,
            entities={"C001": rich_worker, "C002": owner},
            relationships=[],  # No edges - wealth stays constant
        )
        new_state = step(state, config)
        # High wealth -> high acquiescence probability
        Assert(new_state).entity("C001").has_p_acquiescence(0.7)


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
        Assert(new_state).relationship("C001", "C002").has_tension_increased(two_node_state)

    def test_step_tension_accumulates(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Tension accumulates over multiple ticks."""
        state = two_node_state
        for _ in range(10):
            state = step(state, config)

        Assert(state).relationship("C001", "C002").has_tension_increased(two_node_state)


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
        # Compare class_consciousness from IdeologicalProfile
        assert result1.entities["C001"].ideology.class_consciousness == pytest.approx(
            result2.entities["C001"].ideology.class_consciousness
        )


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
        Assert(new_state).tick_is(1)
        # Wealth unchanged without extraction edges
        Assert(new_state).entity("C001").wealth_unchanged_from(state)

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
            id="C001",
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
            id="C003",
            name="Solidarity Source",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.2,
            ideology=IdeologicalProfile(
                class_consciousness=0.9, national_identity=0.1, agitation=0.0
            ),
        )

        # WAGES edge from owner to worker (will be cut next tick)
        wages_edge = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.WAGES,
            value_flow=50.0,
        )

        # SOLIDARITY edge from periphery to worker
        solidarity_edge = Relationship(
            source_id="C003",
            target_id="C001",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner, "C003": periphery_worker},
            relationships=[wages_edge, solidarity_edge],
        )

        # Run first tick to establish wage baseline
        state = step(state, config)
        initial_consciousness = state.entities["C001"].ideology.class_consciousness

        # Cut wages and run another tick
        reduced_wages = Relationship(
            source_id="C002",
            target_id="C001",
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
        assert final_state.entities["C001"].ideology.class_consciousness > initial_consciousness

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
        Assert(new_state).entity("C002").consciousness_unchanged_from(two_node_state)

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
            entities={"C001": worker, "C002": owner},
            relationships=[],  # No edges
        )

        new_state = step(state, config)

        # No drift without exploitation edges
        Assert(new_state).entity("C001").consciousness_unchanged_from(state)

    def test_ideology_clamped_lower_bound(
        self,
        owner: SocialClass,
        exploitation_edge: Relationship,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness cannot exceed 1.0 even over 1000 ticks.

        The class_consciousness field is constrained to [0, 1]. Even with continuous
        drift, it must be clamped to prevent validation errors.
        """
        # Start already revolutionary to stress test the upper bound
        revolutionary_worker = SocialClass(
            id="C001",
            name="Revolutionary Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=-0.9,  # Already very revolutionary (consciousness 0.95)
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

        # Class consciousness must stay <= 1.0
        assert state.entities["C001"].ideology.class_consciousness <= 1.0

    def test_ideology_clamped_upper_bound(
        self,
        owner: SocialClass,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness cannot go below 0.0 (use labor aristocrat scenario).

        A labor aristocrat receiving more than they produce should have
        consciousness decay, but class_consciousness must stay >= 0.0.
        """
        # Labor aristocrat with low (reactionary) consciousness
        labor_aristocrat = SocialClass(
            id="C001",
            name="Labor Aristocrat",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=0.9,  # High wages
            ideology=0.9,  # Already very reactionary (consciousness 0.05)
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

        # Class consciousness must stay >= 0.0
        assert state.entities["C001"].ideology.class_consciousness >= 0.0

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
                id="C001",
                name="Worker",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=0.5,
                ideology=IdeologicalProfile(
                    class_consciousness=0.1, national_identity=0.9, agitation=0.0
                ),
            )
            # Periphery worker has high consciousness (source of transmission)
            periphery = SocialClass(
                id="C003",
                name="Periphery",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=0.2,
                ideology=IdeologicalProfile(
                    class_consciousness=0.9, national_identity=0.1, agitation=0.0
                ),
            )
            solidarity = Relationship(
                source_id="C003",
                target_id="C001",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=strength,
            )
            return WorldState(
                tick=0,
                entities={"C001": worker, "C002": owner, "C003": periphery},
                relationships=[solidarity],
            )

        initial_consciousness = 0.1

        # Run one tick with different solidarity strengths
        low_state = step(create_state_with_solidarity(0.2), config)
        high_state = step(create_state_with_solidarity(0.8), config)

        low_drift = low_state.entities["C001"].ideology.class_consciousness - initial_consciousness
        high_drift = (
            high_state.entities["C001"].ideology.class_consciousness - initial_consciousness
        )

        # Higher solidarity strength should produce larger consciousness drift
        assert high_drift > low_drift
        # Both should have increased from initial
        assert low_drift > 0
        assert high_drift > 0

    def test_thousand_tick_stability(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Class consciousness stays bounded [0, 1] over 1000 ticks.

        This is a stability test to ensure no numerical drift causes
        consciousness to escape valid bounds over long simulations.
        """
        state = two_node_state
        for _ in range(1000):
            state = step(state, config)

        # All class consciousness values must be in valid range
        for entity_id, entity in state.entities.items():
            consciousness = entity.ideology.class_consciousness
            assert 0.0 <= consciousness <= 1.0, (
                f"Entity {entity_id} class_consciousness {consciousness} out of bounds"
            )


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


# =============================================================================
# METABOLISM SYSTEM REGISTRATION TESTS (Sprint 1.4C)
# =============================================================================


@pytest.mark.red_phase  # TDD RED phase - intentionally failing until GREEN phase
class TestMetabolismSystemRegistration:
    """Test that MetabolismSystem is registered in DEFAULT_SYSTEMS.

    Sprint 1.4C: The Wiring - MetabolismSystem must be included in the
    default system list for the metabolic rift feedback loop to function.
    """

    def test_metabolism_system_in_default_systems(self) -> None:
        """MetabolismSystem should be registered in _DEFAULT_SYSTEMS.

        The metabolic rift dynamics (biocapacity regeneration, overshoot
        detection) only run if MetabolismSystem is in the engine's system list.
        """
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_types = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        assert "MetabolismSystem" in system_types, (
            "MetabolismSystem not found in _DEFAULT_SYSTEMS. "
            "Import and register it in simulation_engine.py after TerritorySystem."
        )

    def test_metabolism_system_runs_after_territory_system(self) -> None:
        """MetabolismSystem should run after TerritorySystem.

        Ecological dynamics depend on territory state, so MetabolismSystem
        must be ordered after TerritorySystem in the system list.
        """
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS
        from babylon.engine.systems.metabolism import MetabolismSystem
        from babylon.engine.systems.territory import TerritorySystem

        # Find positions of both systems
        territory_idx = None
        metabolism_idx = None

        for i, system in enumerate(_DEFAULT_SYSTEMS):
            if isinstance(system, TerritorySystem):
                territory_idx = i
            if isinstance(system, MetabolismSystem):
                metabolism_idx = i

        assert territory_idx is not None, "TerritorySystem not in _DEFAULT_SYSTEMS"
        assert metabolism_idx is not None, "MetabolismSystem not in _DEFAULT_SYSTEMS"
        assert metabolism_idx > territory_idx, (
            f"MetabolismSystem (idx={metabolism_idx}) should run after "
            f"TerritorySystem (idx={territory_idx})"
        )


# =============================================================================
# COST-CHECKING TESTS (Epoch 1: Political Economy of Liquidity)
# =============================================================================


@pytest.mark.ledger
class TestCostChecking:
    """Test fiscal cost-checking in step().

    Epoch 1: The Ledger - Political Economy of Liquidity.
    When a state's treasury falls below its burn_rate, the step() function
    should log a warning. This is the first step toward fiscal crisis mechanics.
    """

    def test_step_logs_warning_when_treasury_below_burn_rate(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() logs warning when state treasury < burn_rate.

        StateFinance defaults:
        - treasury: 100.0
        - police_budget: 10.0
        - social_reproduction_budget: 15.0
        - burn_rate (computed): 25.0

        When treasury (5.0) < burn_rate (25.0), a warning should be logged.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # StateFinance with treasury (5.0) < burn_rate (25.0)
        insolvent_finance = StateFinance(treasury=5.0)
        state = two_node_state.model_copy(update={"state_finances": {"USA": insolvent_finance}})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # Verify warning was logged about USA's fiscal situation
        assert "USA" in caplog.text
        assert "treasury" in caplog.text.lower() or "burn_rate" in caplog.text.lower()

    def test_step_no_warning_when_treasury_sufficient(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() does not warn when treasury >= burn_rate.

        When treasury (100.0) >= burn_rate (25.0), no warning should be logged.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # StateFinance with treasury (100.0) >= burn_rate (25.0)
        solvent_finance = StateFinance(treasury=100.0)
        state = two_node_state.model_copy(update={"state_finances": {"USA": solvent_finance}})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # Should not contain warning about USA treasury
        # (there may be other warnings, so we check specifically for fiscal terms)
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        fiscal_warnings = [
            r
            for r in warning_records
            if "USA" in r.message
            and ("treasury" in r.message.lower() or "burn" in r.message.lower())
        ]
        assert len(fiscal_warnings) == 0

    def test_step_handles_empty_state_finances(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() handles empty state_finances dict without errors.

        Backward compatibility: states without any state_finances should
        continue to work normally without raising exceptions.
        """
        # Default two_node_state has no state_finances (empty dict)
        # This should not raise an exception
        new_state = step(two_node_state, config)

        # Verify step completed normally
        assert new_state.tick == 1

    def test_step_logs_warning_for_each_insolvent_state(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() logs warnings for each state where treasury < burn_rate.

        If multiple states are insolvent, each should get its own warning.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # USA is insolvent, UK is solvent
        finances = {
            "USA": StateFinance(treasury=5.0),  # < burn_rate (25.0)
            "UK": StateFinance(treasury=100.0),  # >= burn_rate (25.0)
            "FRANCE": StateFinance(treasury=10.0),  # < burn_rate (25.0)
        }
        state = two_node_state.model_copy(update={"state_finances": finances})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # USA and FRANCE should have warnings, UK should not
        assert "USA" in caplog.text
        assert "FRANCE" in caplog.text
        # UK should not appear in warnings about insolvency
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        uk_fiscal_warnings = [
            r
            for r in warning_records
            if "UK" in r.message
            and ("treasury" in r.message.lower() or "burn" in r.message.lower())
        ]
        assert len(uk_fiscal_warnings) == 0

    def test_step_preserves_state_finances_in_output(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() preserves state_finances in the output WorldState.

        The state_finances dict should flow through the graph transformation
        and be present in the returned WorldState.
        """
        from babylon.models.entities.state_finance import StateFinance

        finances = {"USA": StateFinance(treasury=500.0, police_budget=30.0)}
        state = two_node_state.model_copy(update={"state_finances": finances})

        new_state = step(state, config)

        # state_finances should be preserved
        assert "USA" in new_state.state_finances
        assert new_state.state_finances["USA"].treasury == 500.0
        assert new_state.state_finances["USA"].police_budget == 30.0
