"""Integration tests for Dynamic Balance (Sprint 3.4.4).

The Gas Tank and Driver: Tests verify that finite imperial rent pools
force bourgeoisie agency and eventually trigger economic crisis.

Test Scenarios (see TC.DynamicBalance for constants):
1. The Drain: Pool decreases when outflow > inflow over multiple ticks
2. The Crash: ECONOMIC_CRISIS fires when pool falls below critical threshold
3. Policy Switch: High tension + low pool triggers repression increase

Sprint 1.5: Tolerances relaxed to account for VitalitySystem subsistence entropy.
"""

import pytest

from babylon.config.defines import EconomyDefines, GameDefines, SurvivalDefines
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.world_state import WorldState
from tests.constants import TestConstants

TC = TestConstants

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]


def create_dynamic_balance_scenario(
    initial_pool: float = TC.DynamicBalance.INITIAL_POOL,
    p_w_wealth: float = TC.DynamicBalance.P_W_WEALTH,
    p_c_wealth: float = TC.DynamicBalance.P_C_WEALTH,
    c_b_wealth: float = TC.DynamicBalance.C_B_WEALTH,
    c_w_wealth: float = TC.DynamicBalance.C_W_WEALTH,
    extraction_efficiency: float = TC.DynamicBalance.EXTRACTION_EFFICIENCY_DRAIN,
    comprador_cut: float = TC.ImperialCircuit.COMPRADOR_CUT,
    super_wage_rate: float = TC.DynamicBalance.DRAIN_WAGE_RATE,
    tension: float = TC.EconomicFlow.LOW_TENSION,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create a scenario designed to test pool dynamics.

    Default parameters create a drain scenario where wages outpace tribute.

    Args:
        initial_pool: Starting imperial rent pool
        p_w_wealth: Periphery worker initial wealth
        p_c_wealth: Periphery comprador initial wealth
        c_b_wealth: Core bourgeoisie initial wealth
        c_w_wealth: Core worker initial wealth
        extraction_efficiency: How much rent is extracted (alpha)
        comprador_cut: What fraction the comprador keeps
        super_wage_rate: Starting wage rate (will be dynamic)
        tension: Initial edge tension (affects policy decisions)

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines)
    """
    # Create the 4-node Imperial Circuit
    periphery_worker = SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="Exploited workers",
        wealth=p_w_wealth,
        ideology=0.0,
        organization=0.3,
        repression_faced=0.5,
        subsistence_threshold=0.3,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    periphery_comprador = SocialClass(
        id="C002",
        name="Periphery Comprador",
        role=SocialRole.PETTY_BOURGEOISIE,
        description="Local collaborator class",
        wealth=p_c_wealth,
        ideology=0.5,
        organization=0.5,
        repression_faced=0.3,  # Stable client state (no subsidy)
        subsistence_threshold=0.2,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    core_bourgeoisie = SocialClass(
        id="C003",
        name="Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Imperial capitalist class",
        wealth=c_b_wealth,
        ideology=0.8,
        organization=0.9,
        repression_faced=0.1,
        subsistence_threshold=0.1,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    core_worker = SocialClass(
        id="C004",
        name="Core Worker",
        role=SocialRole.LABOR_ARISTOCRACY,
        description="Labor aristocracy",
        wealth=c_w_wealth,
        ideology=0.3,
        organization=0.2,
        repression_faced=0.2,
        subsistence_threshold=0.3,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    # Create edges with specified tension
    exploitation_edge = Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        description="Imperial rent extraction",
        value_flow=0.0,
        tension=tension,
    )

    tribute_edge = Relationship(
        source_id="C002",
        target_id="C003",
        edge_type=EdgeType.TRIBUTE,
        description="Comprador tribute",
        value_flow=0.0,
        tension=tension,
    )

    wages_edge = Relationship(
        source_id="C003",
        target_id="C004",
        edge_type=EdgeType.WAGES,
        description="Super-wages",
        value_flow=0.0,
        tension=tension,
    )

    client_state_edge = Relationship(
        source_id="C003",
        target_id="C002",
        edge_type=EdgeType.CLIENT_STATE,
        description="Imperial subsidy",
        value_flow=0.0,
        tension=tension,
        subsidy_cap=10.0,
    )

    # Create GlobalEconomy with starting pool and wage rate
    economy = GlobalEconomy(
        imperial_rent_pool=initial_pool,
        current_super_wage_rate=super_wage_rate,
        current_repression_level=0.5,
    )

    # Create world state
    state = WorldState(
        tick=0,
        entities={
            "C001": periphery_worker,
            "C002": periphery_comprador,
            "C003": core_bourgeoisie,
            "C004": core_worker,
        },
        relationships=[
            exploitation_edge,
            tribute_edge,
            wages_edge,
            client_state_edge,
        ],
        event_log=[],
        economy=economy,
    )

    # Create config (now only holds IT-level settings)
    config = SimulationConfig()

    # Create GameDefines with scenario-specific game balance parameters
    # (Paradox Refactor: game math now lives in GameDefines, not SimulationConfig)
    economy_defines = EconomyDefines(
        extraction_efficiency=extraction_efficiency,
        comprador_cut=comprador_cut,
        super_wage_rate=super_wage_rate,
        subsidy_conversion_rate=0.1,
        subsidy_trigger_threshold=0.8,
        initial_rent_pool=initial_pool,
        pool_high_threshold=0.7,
        pool_low_threshold=0.3,
        pool_critical_threshold=0.1,
        min_wage_rate=0.05,
        max_wage_rate=0.35,
    )
    survival_defines = SurvivalDefines(
        default_repression=0.5,
        default_subsistence=0.3,
        steepness_k=10.0,
    )
    defines = GameDefines(
        economy=economy_defines,
        survival=survival_defines,
    )

    return state, config, defines


@pytest.mark.integration
class TestDynamicBalanceDrain:
    """Test: Dynamic Balance - Pool behavior with wages from tribute.

    BUG FIX: Wages now come from tribute_inflow (income), not accumulated wealth.
    This means pool grows when tribute_inflow > wages_outflow + subsidy_outflow.
    Since wages = tribute * rate (rate < 1), pool naturally grows over time.
    """

    def test_pool_receives_extraction_flows(self) -> None:
        """Verify imperial rent pool receives extraction flows.

        Note: Pool may shrink slightly due to rent_pool_decay (TRPF.RENT_POOL_DECAY),
        wage payments, and subsistence burn entropy. We verify pool RECEIVES
        inflows, not that it strictly grows.

        Sprint 1.5: Relaxed from strict growth to ENTROPY_TOLERANCE for entropy.
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            extraction_efficiency=TC.DynamicBalance.EXTRACTION_EFFICIENCY_GROWTH,
            super_wage_rate=TC.DynamicBalance.DRAIN_WAGE_RATE,
        )

        initial_pool = state.economy.imperial_rent_pool

        # Run 5 ticks
        current_state = state
        pool_history = [initial_pool]

        for _ in range(5):
            current_state = step(current_state, config, defines=defines)
            pool_history.append(current_state.economy.imperial_rent_pool)

        # Pool should not collapse - some extraction should flow in
        # Allow ENTROPY_TOLERANCE_TIGHT for subsistence entropy and outflows
        final_pool = current_state.economy.imperial_rent_pool
        tolerance = TC.DynamicBalance.ENTROPY_TOLERANCE_TIGHT
        assert final_pool >= initial_pool * tolerance, (
            f"Pool collapsed too much: {initial_pool} -> {final_pool} "
            f"(expected >= {initial_pool * tolerance:.2f})"
        )

        # Pool should not catastrophically drain
        loose_tolerance = TC.DynamicBalance.ENTROPY_TOLERANCE_LOOSE
        assert pool_history[-1] >= pool_history[0] * loose_tolerance, (
            f"Pool drained too fast: {pool_history}"
        )

    def test_pool_tracked_in_world_state(self) -> None:
        """GlobalEconomy should persist through WorldState."""
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
        )

        new_state = step(state, config, defines=defines)

        # Economy should be present and have expected fields
        assert new_state.economy is not None
        assert hasattr(new_state.economy, "imperial_rent_pool")
        assert hasattr(new_state.economy, "current_super_wage_rate")
        assert hasattr(new_state.economy, "current_repression_level")


@pytest.mark.integration
class TestDynamicBalanceCrash:
    """Test: The Crash - ECONOMIC_CRISIS fires when pool falls below critical."""

    def test_crisis_event_fires_when_pool_critical(self) -> None:
        """ECONOMIC_CRISIS event should fire when pool < POOL_CRITICAL_THRESHOLD.

        Scenario: Start with zero pool - single tick's tribute won't reach 10%.
        The pool_ratio = current_pool / initial_pool, and CRISIS fires when
        pool_ratio < critical_threshold (POOL_CRITICAL_THRESHOLD).
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            extraction_efficiency=TC.DynamicBalance.EXTRACTION_EFFICIENCY_CRISIS,
            super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
        )

        # Manually set pool to 0 so tribute inflow won't reach critical threshold
        critical_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.EMPTY_POOL,
            current_super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.DEFAULT_REPRESSION,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config, defines=defines)

        # Check for ECONOMIC_CRISIS event
        crisis_events = [e for e in new_state.event_log if "ECONOMIC_CRISIS" in e.upper()]
        assert len(crisis_events) >= 1, (
            f"ECONOMIC_CRISIS event should fire. Events: {new_state.event_log}"
        )

    def test_crisis_sets_wage_rate_to_minimum(self) -> None:
        """Crisis decision should reduce wage rate toward minimum.

        When pool is critical, bourgeoisie should slash wages.
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
        )

        # Set pool at critical level (below POOL_CRITICAL_THRESHOLD)
        critical_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.CRISIS_POOL,
            current_super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.DEFAULT_REPRESSION,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config, defines=defines)

        # Wage rate should have decreased
        assert new_state.economy.current_super_wage_rate < state.economy.current_super_wage_rate, (
            f"Wage rate should decrease in crisis: "
            f"{state.economy.current_super_wage_rate} -> {new_state.economy.current_super_wage_rate}"
        )

    def test_crisis_increases_repression(self) -> None:
        """Crisis decision should spike repression.

        When pool is critical, bourgeoisie should increase repression.
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
        )

        # Set pool at critical level (below POOL_CRITICAL_THRESHOLD)
        critical_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.CRISIS_POOL,
            current_super_wage_rate=TC.DynamicBalance.MAX_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.DEFAULT_REPRESSION,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config, defines=defines)

        # Repression should have increased
        assert (
            new_state.economy.current_repression_level > state.economy.current_repression_level
        ), (
            f"Repression should increase in crisis: "
            f"{state.economy.current_repression_level} -> {new_state.economy.current_repression_level}"
        )


@pytest.mark.integration
class TestDynamicBalancePolicySwitch:
    """Test: Policy Switch - Bourgeoisie changes policy based on conditions."""

    def test_low_pool_high_tension_triggers_iron_fist(self) -> None:
        """Low pool + high tension should increase repression (iron fist).

        Pool < POOL_LOW_THRESHOLD + tension > IRON_FIST_TENSION_THRESHOLD = IRON_FIST
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            tension=TC.DynamicBalance.HIGH_TENSION,
        )

        # Set pool in austerity zone (below POOL_LOW_THRESHOLD)
        austerity_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.AUSTERITY_POOL,
            current_super_wage_rate=TC.DynamicBalance.LOW_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.LOW_REPRESSION,
        )
        state = state.model_copy(update={"economy": austerity_economy})

        new_state = step(state, config, defines=defines)

        # Repression should increase
        assert (
            new_state.economy.current_repression_level > state.economy.current_repression_level
        ), (
            f"Repression should increase with iron fist: "
            f"{state.economy.current_repression_level} -> {new_state.economy.current_repression_level}"
        )

    def test_low_pool_low_tension_triggers_austerity(self) -> None:
        """Low pool + low tension should decrease wages (austerity).

        Pool < POOL_LOW_THRESHOLD + tension <= IRON_FIST_TENSION_THRESHOLD = AUSTERITY
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            tension=TC.EconomicFlow.LOW_TENSION,
        )

        # Set pool in austerity zone (below POOL_LOW_THRESHOLD)
        austerity_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.AUSTERITY_POOL,
            current_super_wage_rate=TC.DynamicBalance.MODERATE_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.DEFAULT_REPRESSION,
        )
        state = state.model_copy(update={"economy": austerity_economy})

        new_state = step(state, config, defines=defines)

        # Wages should decrease
        assert new_state.economy.current_super_wage_rate < state.economy.current_super_wage_rate, (
            f"Wages should decrease with austerity: "
            f"{state.economy.current_super_wage_rate} -> {new_state.economy.current_super_wage_rate}"
        )

    def test_high_pool_low_tension_triggers_bribery(self) -> None:
        """High pool + low tension should increase wages (bribery).

        Pool >= POOL_HIGH_THRESHOLD + tension < BRIBERY_TENSION_THRESHOLD = BRIBERY
        """
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.INITIAL_POOL,
            tension=TC.DynamicBalance.VERY_LOW_TENSION,
        )

        # Set pool in prosperity zone (above POOL_HIGH_THRESHOLD)
        prosperity_economy = GlobalEconomy(
            imperial_rent_pool=TC.DynamicBalance.PROSPERITY_POOL,
            current_super_wage_rate=TC.DynamicBalance.LOW_WAGE_RATE,
            current_repression_level=TC.DynamicBalance.DEFAULT_REPRESSION,
        )
        state = state.model_copy(update={"economy": prosperity_economy})

        new_state = step(state, config, defines=defines)

        # Wages should increase (up to max)
        assert new_state.economy.current_super_wage_rate > state.economy.current_super_wage_rate, (
            f"Wages should increase with bribery: "
            f"{state.economy.current_super_wage_rate} -> {new_state.economy.current_super_wage_rate}"
        )


@pytest.mark.integration
class TestDynamicBalanceGraphSerialization:
    """Test that economy survives graph round-trip."""

    def test_economy_persists_through_graph_conversion(self) -> None:
        """GlobalEconomy should serialize to graph and back."""
        state, config, defines = create_dynamic_balance_scenario(
            initial_pool=TC.DynamicBalance.MODERATE_POOL,
            super_wage_rate=TC.DynamicBalance.MODERATE_WAGE_RATE,
        )

        # Run a tick to get updated economy
        new_state = step(state, config, defines=defines)

        # Convert to graph and back
        graph = new_state.to_graph()
        restored_state = WorldState.from_graph(graph, tick=new_state.tick)

        # Economy should be preserved (use APPROX_REL_TOLERANCE)
        tolerance = TC.DynamicBalance.APPROX_REL_TOLERANCE
        assert restored_state.economy.imperial_rent_pool == pytest.approx(
            new_state.economy.imperial_rent_pool, rel=tolerance
        )
        assert restored_state.economy.current_super_wage_rate == pytest.approx(
            new_state.economy.current_super_wage_rate, rel=tolerance
        )
        assert restored_state.economy.current_repression_level == pytest.approx(
            new_state.economy.current_repression_level, rel=tolerance
        )

    def test_economy_in_graph_metadata(self) -> None:
        """Economy should be stored in graph.graph['economy']."""
        state, _, _ = create_dynamic_balance_scenario()

        graph = state.to_graph()

        assert "economy" in graph.graph
        assert graph.graph["economy"]["imperial_rent_pool"] == state.economy.imperial_rent_pool
        assert (
            graph.graph["economy"]["current_super_wage_rate"]
            == state.economy.current_super_wage_rate
        )
