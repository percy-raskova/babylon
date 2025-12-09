"""Integration tests for Dynamic Balance (Sprint 3.4.4).

The Gas Tank and Driver: Tests verify that finite imperial rent pools
force bourgeoisie agency and eventually trigger economic crisis.

Test Scenarios:
1. The Drain: Pool decreases when outflow > inflow over multiple ticks
2. The Crash: ECONOMIC_CRISIS fires when pool falls below critical threshold
3. Policy Switch: High tension + low pool triggers repression increase
"""

import pytest

from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.world_state import WorldState


def create_dynamic_balance_scenario(
    initial_pool: float = 100.0,
    p_w_wealth: float = 50.0,
    p_c_wealth: float = 0.0,
    c_b_wealth: float = 50.0,
    c_w_wealth: float = 0.0,
    extraction_efficiency: float = 0.3,  # Lower extraction = less tribute inflow
    comprador_cut: float = 0.15,
    super_wage_rate: float = 0.40,  # High wages = faster drain
    tension: float = 0.3,
) -> tuple[WorldState, SimulationConfig]:
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
        Tuple of (WorldState, SimulationConfig)
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

    # Create config with Dynamic Balance parameters
    config = SimulationConfig(
        extraction_efficiency=extraction_efficiency,
        comprador_cut=comprador_cut,
        super_wage_rate=super_wage_rate,
        subsidy_conversion_rate=0.1,
        subsidy_trigger_threshold=0.8,
        repression_level=0.5,
        subsistence_threshold=0.3,
        survival_steepness=10.0,
        consciousness_sensitivity=0.5,
        # Dynamic Balance parameters (Sprint 3.4.4)
        initial_rent_pool=initial_pool,
        pool_high_threshold=0.7,
        pool_low_threshold=0.3,
        pool_critical_threshold=0.1,
        min_wage_rate=0.05,
        max_wage_rate=0.35,
    )

    return state, config


@pytest.mark.integration
class TestDynamicBalanceDrain:
    """Test: The Drain - Pool decreases when expenditure exceeds extraction."""

    def test_pool_decreases_over_multiple_ticks(self) -> None:
        """Pool should decrease when wages outpace tribute inflow.

        Scenario: Low extraction (0.3) + high wages (0.4) = drain
        Over 5 ticks, pool should visibly decrease.
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            extraction_efficiency=0.3,  # Low extraction
            super_wage_rate=0.40,  # High wages
        )

        initial_pool = state.economy.imperial_rent_pool

        # Run 5 ticks
        current_state = state
        pool_history = [initial_pool]

        for _ in range(5):
            current_state = step(current_state, config)
            pool_history.append(current_state.economy.imperial_rent_pool)

        # Pool should have decreased
        final_pool = current_state.economy.imperial_rent_pool
        assert final_pool < initial_pool, f"Pool should decrease: {initial_pool} -> {final_pool}"

        # Pool should trend downward (not all values need to decrease due to inflow)
        assert pool_history[-1] < pool_history[0], f"Pool should trend down: {pool_history}"

    def test_pool_tracked_in_world_state(self) -> None:
        """GlobalEconomy should persist through WorldState."""
        state, config = create_dynamic_balance_scenario(initial_pool=100.0)

        new_state = step(state, config)

        # Economy should be present and have expected fields
        assert new_state.economy is not None
        assert hasattr(new_state.economy, "imperial_rent_pool")
        assert hasattr(new_state.economy, "current_super_wage_rate")
        assert hasattr(new_state.economy, "current_repression_level")


@pytest.mark.integration
class TestDynamicBalanceCrash:
    """Test: The Crash - ECONOMIC_CRISIS fires when pool falls below critical."""

    def test_crisis_event_fires_when_pool_critical(self) -> None:
        """ECONOMIC_CRISIS event should fire when pool < 10% of initial.

        Scenario: Start with very low pool (5) + high wages = immediate crisis
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            super_wage_rate=0.35,  # Max wage rate
        )

        # Manually set pool near critical
        critical_economy = GlobalEconomy(
            imperial_rent_pool=8.0,  # Below 10% of initial 100
            current_super_wage_rate=0.35,
            current_repression_level=0.5,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config)

        # Check for ECONOMIC_CRISIS event
        crisis_events = [e for e in new_state.event_log if "ECONOMIC_CRISIS" in e.upper()]
        assert (
            len(crisis_events) >= 1
        ), f"ECONOMIC_CRISIS event should fire. Events: {new_state.event_log}"

    def test_crisis_sets_wage_rate_to_minimum(self) -> None:
        """Crisis decision should reduce wage rate toward minimum.

        When pool is critical, bourgeoisie should slash wages.
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            super_wage_rate=0.35,  # Max wage rate
        )

        # Set pool at critical level
        critical_economy = GlobalEconomy(
            imperial_rent_pool=5.0,  # Below 10% critical
            current_super_wage_rate=0.35,
            current_repression_level=0.5,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config)

        # Wage rate should have decreased
        assert new_state.economy.current_super_wage_rate < state.economy.current_super_wage_rate, (
            f"Wage rate should decrease in crisis: "
            f"{state.economy.current_super_wage_rate} -> {new_state.economy.current_super_wage_rate}"
        )

    def test_crisis_increases_repression(self) -> None:
        """Crisis decision should spike repression.

        When pool is critical, bourgeoisie should increase repression.
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            super_wage_rate=0.35,
        )

        # Set pool at critical level
        critical_economy = GlobalEconomy(
            imperial_rent_pool=5.0,  # Below 10% critical
            current_super_wage_rate=0.35,
            current_repression_level=0.5,
        )
        state = state.model_copy(update={"economy": critical_economy})

        new_state = step(state, config)

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

        Pool < 30% + tension > 50% = IRON_FIST decision
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            tension=0.7,  # High tension
        )

        # Set pool in austerity zone (between critical and low threshold)
        austerity_economy = GlobalEconomy(
            imperial_rent_pool=20.0,  # 20% - below 30% low threshold
            current_super_wage_rate=0.20,
            current_repression_level=0.4,
        )
        state = state.model_copy(update={"economy": austerity_economy})

        new_state = step(state, config)

        # Repression should increase
        assert (
            new_state.economy.current_repression_level > state.economy.current_repression_level
        ), (
            f"Repression should increase with iron fist: "
            f"{state.economy.current_repression_level} -> {new_state.economy.current_repression_level}"
        )

    def test_low_pool_low_tension_triggers_austerity(self) -> None:
        """Low pool + low tension should decrease wages (austerity).

        Pool < 30% + tension <= 50% = AUSTERITY decision
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            tension=0.3,  # Low tension
        )

        # Set pool in austerity zone
        austerity_economy = GlobalEconomy(
            imperial_rent_pool=20.0,  # 20% - below 30% low threshold
            current_super_wage_rate=0.25,
            current_repression_level=0.5,
        )
        state = state.model_copy(update={"economy": austerity_economy})

        new_state = step(state, config)

        # Wages should decrease
        assert new_state.economy.current_super_wage_rate < state.economy.current_super_wage_rate, (
            f"Wages should decrease with austerity: "
            f"{state.economy.current_super_wage_rate} -> {new_state.economy.current_super_wage_rate}"
        )

    def test_high_pool_low_tension_triggers_bribery(self) -> None:
        """High pool + low tension should increase wages (bribery).

        Pool >= 70% + tension < 30% = BRIBERY decision
        """
        state, config = create_dynamic_balance_scenario(
            initial_pool=100.0,
            tension=0.2,  # Low tension
        )

        # Set pool in prosperity zone
        prosperity_economy = GlobalEconomy(
            imperial_rent_pool=80.0,  # 80% - above 70% high threshold
            current_super_wage_rate=0.20,
            current_repression_level=0.5,
        )
        state = state.model_copy(update={"economy": prosperity_economy})

        new_state = step(state, config)

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
        state, config = create_dynamic_balance_scenario(
            initial_pool=75.0,
            super_wage_rate=0.25,
        )

        # Run a tick to get updated economy
        new_state = step(state, config)

        # Convert to graph and back
        graph = new_state.to_graph()
        restored_state = WorldState.from_graph(graph, tick=new_state.tick)

        # Economy should be preserved
        assert restored_state.economy.imperial_rent_pool == pytest.approx(
            new_state.economy.imperial_rent_pool, rel=0.01
        )
        assert restored_state.economy.current_super_wage_rate == pytest.approx(
            new_state.economy.current_super_wage_rate, rel=0.01
        )
        assert restored_state.economy.current_repression_level == pytest.approx(
            new_state.economy.current_repression_level, rel=0.01
        )

    def test_economy_in_graph_metadata(self) -> None:
        """Economy should be stored in graph.graph['economy']."""
        state, _ = create_dynamic_balance_scenario()

        graph = state.to_graph()

        assert "economy" in graph.graph
        assert graph.graph["economy"]["imperial_rent_pool"] == state.economy.imperial_rent_pool
        assert (
            graph.graph["economy"]["current_super_wage_rate"]
            == state.economy.current_super_wage_rate
        )
