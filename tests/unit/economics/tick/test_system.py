"""Tests for TickDynamicsSystem — comprehensive mutation-killing tests.

Feature: 017-simulation-tick-dynamics
Tasks: T010 (US1), T012 (US2), T016 (US3)

Strategy: Call private methods directly with controlled inputs to kill
mutations that survive indirect testing via step(). Each test targets
specific mutation clusters identified by mutmut analysis.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest
from tests.unit.economics.tick.conftest import (
    WAYNE_FIPS,
    CapturingTransitionEngine,
    MockBasketVisibilityCalculator,
    MockCapitalStockCalculator,
    MockClassTransitionEngine,
    MockGammaIIICalculator,
    MockImperialRentCalculator,
    MockMELTCalculator,
    MockTensor,
    MockTensorRegistry,
    MockThroughputCalculator,
    build_territory_graph,
)

from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.system import (
    DEFAULT_V_REPRODUCTION,
    WEEKS_PER_YEAR,
    TickDynamicsSystem,
)
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer

# Secondary FIPS for multi-county tests
OAKLAND_FIPS: str = "26125"


# =============================================================================
# Helpers
# =============================================================================


def _make_services(**kwargs: Any) -> ServiceContainer:
    """Create ServiceContainer with mock calculators."""
    defaults: dict[str, Any] = {
        "melt_calculator": MockMELTCalculator(),
        "basket_calculator": MockBasketVisibilityCalculator(),
        "gamma_calculator": MockGammaIIICalculator(),
        "capital_calculator": MockCapitalStockCalculator(),
        "throughput_calculator": MockThroughputCalculator(),
        "transition_engine": MockClassTransitionEngine(),
        "imperial_rent_calculator": MockImperialRentCalculator(),
    }
    defaults.update(kwargs)
    return ServiceContainer.create(**defaults)


def _make_graph_with_state(year: int = 2015) -> nx.DiGraph[str]:
    """Build graph with tick dynamics state pre-loaded."""
    graph = build_territory_graph()
    dist = ClassDistribution(
        fips=WAYNE_FIPS,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )
    county = CountyEconomicState(
        fips=WAYNE_FIPS,
        year=year,
        capital_stock=1e9,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.053,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=dist,
        phi_hour=3.50,
    )
    params = NationalTickParameters(
        year=year,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.33,
        gamma_III_raw=0.33,
        tau_effective=42.16,
        v_reproduction=12.0,
        estimated=True,
    )
    coeff = SmoothedCoefficients(
        alpha=0.3,
        gamma_basket=0.68,
        gamma_III=0.33,
        gamma_import=0.35,
        is_initialized=True,
    )
    state = SimulationTickState(
        year=year,
        national_params=params,
        county_states={WAYNE_FIPS: county},
        coefficients=coeff,
    )
    from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

    write_tick_state_to_graph(graph, state)
    return graph


def _make_county(
    fips: str = WAYNE_FIPS,
    year: int = 2015,
    median_wage: float = 21.0,
    employment: float = 500_000.0,
    unemployment_rate: float = 0.053,
    capital_stock: float = 1e9,
    phi_hour: float = 3.50,
    crisis_state: CrisisState | None = None,
    class_distribution: ClassDistribution | None = None,
    **kwargs: Any,
) -> CountyEconomicState:
    """Create a CountyEconomicState with sensible defaults."""
    if class_distribution is None:
        class_distribution = ClassDistribution(
            fips=fips,
            year=min(max(year, 2007), 2030),
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
    if crisis_state is None:
        crisis_state = CrisisState.normal()

    return CountyEconomicState(
        fips=fips,
        year=year,
        capital_stock=capital_stock,
        throughput_position=kwargs.get("throughput_position", 0.90),
        supply_chain_depth=kwargs.get("supply_chain_depth", 2.1),
        unemployment_rate=unemployment_rate,
        u6_rate=kwargs.get("u6_rate", 0.10),
        pter_rate=kwargs.get("pter_rate", 0.04),
        nilf_rate=kwargs.get("nilf_rate", 0.06),
        median_wage=median_wage,
        employment=employment,
        class_distribution=class_distribution,
        phi_hour=phi_hour,
        crisis_state=crisis_state,
    )


def _make_national_params(
    year: int = 2015,
    tau: float = 62.0,
    gamma_basket: float = 0.68,
    gamma_III: float = 0.33,
    **kwargs: Any,
) -> NationalTickParameters:
    """Create NationalTickParameters with sensible defaults."""
    return NationalTickParameters(
        year=year,
        tau=tau,
        gamma_basket=gamma_basket,
        gamma_basket_raw=kwargs.get("gamma_basket_raw", gamma_basket),
        gamma_III=gamma_III,
        gamma_III_raw=kwargs.get("gamma_III_raw", gamma_III),
        tau_effective=kwargs.get("tau_effective", tau * gamma_basket),
        v_reproduction=kwargs.get("v_reproduction", 12.0),
        estimated=kwargs.get("estimated", True),
    )


def _deep_crisis_state(
    duration: int = 6,
    cumulative_wage_compression: float = 0.0,
) -> CrisisState:
    """Create a CrisisState in DEEP phase."""
    return CrisisState(
        phase=CrisisPhase.DEEP,
        consecutive_below=5,
        consecutive_recovery=0,
        crisis_start_period=3,
        crisis_duration=duration,
        peak_severity=0.03,
        cumulative_wage_compression=cumulative_wage_compression,
    )


# =============================================================================
# US1: National Parameter Computation (T010) — strengthened
# =============================================================================


class TestNationalParameterComputation:
    """Tests for Step 2: compute national parameters."""

    def test_tau_matches_melt_calculator(self) -> None:
        """Verify tau comes from MELTCalculator.get_melt()."""
        system = TickDynamicsSystem()
        services = _make_services(melt_calculator=MockMELTCalculator(tau=65.0))
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.tau == pytest.approx(65.0)

    def test_gamma_basket_matches_basket_calculator(self) -> None:
        """Verify gamma_basket_raw comes from BasketVisibilityCalculator."""
        system = TickDynamicsSystem()
        services = _make_services(
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.72)
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.gamma_basket_raw == pytest.approx(0.72)

    def test_gamma_III_matches_gamma_calculator(self) -> None:
        """Verify gamma_III_raw comes from GammaIIICalculator."""
        system = TickDynamicsSystem()
        services = _make_services(gamma_calculator=MockGammaIIICalculator(gamma_iii=0.40))
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.gamma_III_raw == pytest.approx(0.40)

    def test_tau_effective_equals_tau_times_gamma_basket(self) -> None:
        """Verify tau_effective = tau * gamma_basket."""
        system = TickDynamicsSystem()
        services = _make_services(
            melt_calculator=MockMELTCalculator(tau=62.0),
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.68),
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.tau_effective == pytest.approx(62.0 * 0.68, abs=1e-9)

    def test_no_data_sentinel_halts_with_context(self) -> None:
        """Verify NoDataSentinel from MELT calculator causes pipeline to skip."""
        system = TickDynamicsSystem()

        sentinel_melt = MockMELTCalculator(tau=62.0, force_sentinel=True)
        services = _make_services(melt_calculator=sentinel_melt)
        graph = _make_graph_with_state(year=2015)
        context = TickContext(tick=52)

        system.step(graph, services, context)

        tick_data = graph.graph.get("tick_dynamics", {})
        assert tick_data.get("year") == 2015  # unchanged


# =============================================================================
# US2: County-Level State Computation (T012) — strengthened
# =============================================================================


class TestCountyStateComputation:
    """Tests for Step 3a: compute county-level state."""

    def test_capital_stock_from_calculator(self) -> None:
        """Verify K comes from CapitalStockCalculator.get_K()."""
        system = TickDynamicsSystem()
        services = _make_services(capital_calculator=MockCapitalStockCalculator(k_value=2e9))
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        county_states = graph.graph["tick_dynamics"]["county_states"]
        assert county_states[WAYNE_FIPS].capital_stock == pytest.approx(2e9)

    def test_throughput_from_calculator(self) -> None:
        """Verify pi comes from ThroughputCalculator.compute_metrics()."""
        system = TickDynamicsSystem()
        services = _make_services(
            throughput_calculator=MockThroughputCalculator(pi=1.10, supply_chain_depth=3.0)
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        assert graph.nodes[WAYNE_FIPS]["tick_throughput_position"] == pytest.approx(1.10)


# =============================================================================
# US3: Full Tick Pipeline (T016) — strengthened
# =============================================================================


class TestFullTickPipeline:
    """Tests for the full 8-step pipeline."""

    def test_system_name(self) -> None:
        """Verify system name property."""
        system = TickDynamicsSystem()
        assert system.name == "tick_dynamics"

    def test_non_year_boundary_is_noop(self) -> None:
        """Verify system does nothing on non-year-boundary ticks."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=1)

        old_k = graph.nodes[WAYNE_FIPS].get("tick_capital_stock", 1e9)
        system.step(graph, services, context)
        new_k = graph.nodes[WAYNE_FIPS].get("tick_capital_stock", 1e9)
        assert new_k == pytest.approx(old_k)

    def test_year_boundary_updates_state(self) -> None:
        """Verify system updates state on year-boundary ticks."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        tick_data = graph.graph["tick_dynamics"]
        assert tick_data["year"] == 2016
        assert tick_data["national_params"].tau == pytest.approx(62.0)

    def test_class_distribution_sums_to_one(self) -> None:
        """Verify class distribution sum-to-one invariant after tick."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        dist = graph.nodes[WAYNE_FIPS].get("tick_class_distribution", {})
        assert dist, "Distribution should be written to graph"
        total = sum(dist.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_missing_calculators_skips_gracefully(self) -> None:
        """Verify system handles missing calculators (None) gracefully."""
        system = TickDynamicsSystem()
        services = ServiceContainer.create()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        # Should not crash; state unchanged because melt_calculator is None
        system.step(graph, services, context)
        assert graph.graph["tick_dynamics"]["year"] == 2015


# =============================================================================
# _bootstrap_county_states — kills ~185 no_test mutations
# =============================================================================


class TestBootstrapCountyStates:
    """Tests for _bootstrap_county_states (zero prior coverage)."""

    def test_bootstrap_empty_graph(self) -> None:
        """Empty graph produces empty dict."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        result = system._bootstrap_county_states(graph, 2015)
        assert result == {}

    def test_bootstrap_non_territory_skipped(self) -> None:
        """Non-territory nodes are skipped."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("proletariat_26163", _node_type="social_class")
        result = system._bootstrap_county_states(graph, 2015)
        assert result == {}

    def test_bootstrap_territory_without_tick_data(self) -> None:
        """Territory without tick_capital_stock is skipped."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        # No tick_ attributes on node
        result = system._bootstrap_county_states(graph, 2015)
        assert result == {}

    def test_bootstrap_territory_with_tick_data(self) -> None:
        """Territory with tick_capital_stock produces correct CountyEconomicState."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 5e8
        graph.nodes[WAYNE_FIPS]["tick_throughput_position"] = 0.85
        graph.nodes[WAYNE_FIPS]["tick_supply_chain_depth"] = 1.5
        graph.nodes[WAYNE_FIPS]["tick_unemployment_rate"] = 0.07
        graph.nodes[WAYNE_FIPS]["tick_median_wage"] = 25.0
        graph.nodes[WAYNE_FIPS]["tick_employment"] = 200_000.0
        graph.nodes[WAYNE_FIPS]["tick_phi_hour"] = 2.0

        result = system._bootstrap_county_states(graph, 2015)

        assert WAYNE_FIPS in result
        county = result[WAYNE_FIPS]
        assert county.fips == WAYNE_FIPS
        assert county.capital_stock == pytest.approx(5e8)
        assert county.throughput_position == pytest.approx(0.85)
        assert county.supply_chain_depth == pytest.approx(1.5)
        assert county.unemployment_rate == pytest.approx(0.07)
        assert county.median_wage == pytest.approx(25.0)
        assert county.employment == pytest.approx(200_000.0)
        assert county.phi_hour == pytest.approx(2.0)

    def test_bootstrap_default_values(self) -> None:
        """Missing tick_ attributes use correct defaults."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9

        result = system._bootstrap_county_states(graph, 2015)
        county = result[WAYNE_FIPS]

        assert county.throughput_position == pytest.approx(1.0)
        assert county.supply_chain_depth == pytest.approx(2.0)
        assert county.unemployment_rate == pytest.approx(0.05)
        assert county.u6_rate == pytest.approx(0.10)
        assert county.pter_rate == pytest.approx(0.04)
        assert county.nilf_rate == pytest.approx(0.06)
        assert county.median_wage == pytest.approx(21.0)
        assert county.employment == pytest.approx(100_000.0)
        assert county.phi_hour == pytest.approx(0.0)

    def test_bootstrap_year_clamping_distribution(self) -> None:
        """Distribution year clamped to [2007, 2030]."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9

        result = system._bootstrap_county_states(graph, 2035)
        county = result[WAYNE_FIPS]
        assert county.class_distribution.year == 2030

    def test_bootstrap_year_clamping_county_state(self) -> None:
        """CountyEconomicState year clamped to [2007, 2040]."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9

        result = system._bootstrap_county_states(graph, 2045)
        county = result[WAYNE_FIPS]
        assert county.year == 2040

    def test_bootstrap_year_clamping_below_minimum(self) -> None:
        """Year below 2007 clamped to 2007 for both dist and county."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9

        result = system._bootstrap_county_states(graph, 2000)
        county = result[WAYNE_FIPS]
        assert county.year == 2007
        assert county.class_distribution.year == 2007

    def test_bootstrap_class_distribution_defaults(self) -> None:
        """Default class shares match expected values."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9

        result = system._bootstrap_county_states(graph, 2015)
        dist = result[WAYNE_FIPS].class_distribution

        assert dist.bourgeoisie_share == pytest.approx(0.01)
        assert dist.petit_bourgeoisie_share == pytest.approx(0.09)
        assert dist.labor_aristocracy_share == pytest.approx(0.40)
        assert dist.proletariat_share == pytest.approx(0.35)
        assert dist.lumpenproletariat_share == pytest.approx(0.15)

    def test_bootstrap_class_distribution_from_graph(self) -> None:
        """Reads existing class distribution from graph data."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9
        graph.nodes[WAYNE_FIPS]["tick_class_distribution"] = {
            "bourgeoisie": 0.02,
            "petit_bourgeoisie": 0.08,
            "labor_aristocracy": 0.38,
            "proletariat": 0.37,
            "lumpenproletariat": 0.15,
        }

        result = system._bootstrap_county_states(graph, 2015)
        dist = result[WAYNE_FIPS].class_distribution

        assert dist.bourgeoisie_share == pytest.approx(0.02)
        assert dist.petit_bourgeoisie_share == pytest.approx(0.08)
        assert dist.labor_aristocracy_share == pytest.approx(0.38)
        assert dist.proletariat_share == pytest.approx(0.37)

    def test_bootstrap_multiple_territories(self) -> None:
        """Multiple territory nodes each produce a CountyEconomicState."""
        system = TickDynamicsSystem()
        graph = build_territory_graph(fips_codes=[WAYNE_FIPS, OAKLAND_FIPS])
        graph.nodes[WAYNE_FIPS]["tick_capital_stock"] = 1e9
        graph.nodes[OAKLAND_FIPS]["tick_capital_stock"] = 2e9

        result = system._bootstrap_county_states(graph, 2015)

        assert len(result) == 2
        assert result[WAYNE_FIPS].capital_stock == pytest.approx(1e9)
        assert result[OAKLAND_FIPS].capital_stock == pytest.approx(2e9)


# =============================================================================
# _determine_year — kills ~13 no_test mutations
# =============================================================================


class TestDetermineYear:
    """Tests for _determine_year (zero prior coverage)."""

    def test_determine_year_from_graph_metadata(self) -> None:
        """Graph with base_year metadata uses it."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.graph["base_year"] = 2010
        result = system._determine_year(tick=52, graph=graph)
        assert result == 2011

    def test_determine_year_default_base(self) -> None:
        """Graph without base_year uses default 2010."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        result = system._determine_year(tick=104, graph=graph)
        assert result == 2012

    def test_determine_year_none_graph(self) -> None:
        """None graph uses default base_year 2010."""
        system = TickDynamicsSystem()
        result = system._determine_year(tick=0, graph=None)
        assert result == 2010

    def test_determine_year_tick_zero(self) -> None:
        """Tick 0 returns base_year itself."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.graph["base_year"] = 2015
        result = system._determine_year(tick=0, graph=graph)
        assert result == 2015

    def test_determine_year_custom_base_year(self) -> None:
        """Custom base_year in graph metadata is respected."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.graph["base_year"] = 2007
        # 3 years of ticks
        result = system._determine_year(tick=3 * WEEKS_PER_YEAR, graph=graph)
        assert result == 2010


# =============================================================================
# _get_territory_fips — kills ~11 no_test mutations
# =============================================================================


class TestGetTerritoryFips:
    """Tests for _get_territory_fips (zero prior coverage)."""

    def test_returns_territory_nodes(self) -> None:
        """Territory nodes yield their FIPS codes."""
        system = TickDynamicsSystem()
        graph = build_territory_graph(fips_codes=[WAYNE_FIPS, OAKLAND_FIPS])
        result = system._get_territory_fips(graph)
        assert sorted(result) == sorted([WAYNE_FIPS, OAKLAND_FIPS])

    def test_skips_non_territory(self) -> None:
        """Non-territory nodes are excluded."""
        system = TickDynamicsSystem()
        graph = build_territory_graph()
        graph.add_node("proletariat_26163", _node_type="social_class")
        result = system._get_territory_fips(graph)
        assert result == [WAYNE_FIPS]

    def test_empty_graph(self) -> None:
        """Empty graph returns empty list."""
        system = TickDynamicsSystem()
        graph: nx.DiGraph[str] = nx.DiGraph()
        result = system._get_territory_fips(graph)
        assert result == []


# =============================================================================
# _get_profit_rate — kills ~44 survivors, resolves 2 suspicious
# =============================================================================


class TestGetProfitRate:
    """Tests for _get_profit_rate (8.3% score → should approach 80%+)."""

    def test_no_registry_returns_none(self) -> None:
        """No tensor_registry in services returns None."""
        system = TickDynamicsSystem()
        services = _make_services()  # No tensor_registry
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result is None

    def test_current_year_available(self) -> None:
        """Returns profit_rate from tensor when current year is available."""
        system = TickDynamicsSystem()
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): MockTensor(profit_rate=0.12),
            }
        )
        services = _make_services(tensor_registry=registry)
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result == pytest.approx(0.12)

    def test_carry_forward_to_most_recent(self) -> None:
        """Falls back to most recent year <= target when current unavailable."""
        system = TickDynamicsSystem()
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2013): MockTensor(profit_rate=0.10),
                (WAYNE_FIPS, 2014): MockTensor(profit_rate=0.11),
            }
        )
        services = _make_services(tensor_registry=registry)
        # Request 2015, but only 2013 and 2014 available
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result == pytest.approx(0.11)

    def test_all_sentinel_returns_none(self) -> None:
        """All years return NoDataSentinel → returns None."""
        system = TickDynamicsSystem()
        registry = MockTensorRegistry()  # Empty: all lookups return sentinel
        services = _make_services(tensor_registry=registry)
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result is None

    def test_tensor_without_profit_rate_attr(self) -> None:
        """Tensor exists but has no profit_rate attribute → returns None."""
        system = TickDynamicsSystem()

        class TensorNoProfitRate:
            """Tensor without profit_rate."""

        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): TensorNoProfitRate(),
            }
        )
        services = _make_services(tensor_registry=registry)
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result is None

    def test_carry_forward_skips_future_years(self) -> None:
        """Carry-forward ignores years > target year."""
        system = TickDynamicsSystem()
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2016): MockTensor(profit_rate=0.15),
                (WAYNE_FIPS, 2013): MockTensor(profit_rate=0.09),
            }
        )
        services = _make_services(tensor_registry=registry)
        # Request 2015, only 2013 is <= 2015
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result == pytest.approx(0.09)

    def test_profit_rate_none_on_tensor(self) -> None:
        """Tensor with profit_rate=None returns None."""
        system = TickDynamicsSystem()
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): MockTensor(profit_rate=None),
            }
        )
        services = _make_services(tensor_registry=registry)
        result = system._get_profit_rate(WAYNE_FIPS, 2015, services)
        assert result is None


# =============================================================================
# _check_crisis_triggers — kills ~57 survivors, resolves 1 suspicious
# =============================================================================


class TestCheckCrisisTriggers:
    """Tests for _check_crisis_triggers (24.0% score)."""

    def test_normal_stays_normal_above_threshold(self) -> None:
        """Profit rate above threshold keeps NORMAL phase."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        # Profit rate 0.10 > default r_threshold 0.05
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): MockTensor(profit_rate=0.10),
            }
        )
        services = _make_services(tensor_registry=registry)

        result = system._check_crisis_triggers(states, services, tick=0)
        assert result[WAYNE_FIPS].crisis_state.phase == CrisisPhase.NORMAL

    def test_deep_phase_applies_wage_compression(self) -> None:
        """DEEP phase applies wage compression 4 times (quarterly)."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis, median_wage=21.0)
        states = {WAYNE_FIPS: county}
        services = _make_services()  # No tensor_registry → profit_rate = None

        result = system._check_crisis_triggers(states, services, tick=0)

        wage_compression_rate = 0.02  # default
        expected_wage = 21.0 * (1.0 - wage_compression_rate) ** 4
        assert result[WAYNE_FIPS].median_wage == pytest.approx(expected_wage, rel=1e-9)

    def test_cumulative_wage_compression_formula(self) -> None:
        """Cumulative compression formula: 1 - (1-rate)^4 after 4 quarters."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state(cumulative_wage_compression=0.0)
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        services = _make_services()

        result = system._check_crisis_triggers(states, services, tick=0)

        # 4 quarterly evaluations, each applying 0.02 rate
        expected_cumulative = 1.0 - (1.0 - 0.02) ** 4
        actual = result[WAYNE_FIPS].crisis_state.cumulative_wage_compression
        assert actual == pytest.approx(expected_cumulative, rel=1e-9)

    def test_quarterly_evals_count(self) -> None:
        """Exactly 4 quarterly evaluations per annual pipeline run."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state(duration=6)
        county = _make_county(crisis_state=crisis, median_wage=100.0)
        states = {WAYNE_FIPS: county}
        services = _make_services()

        result = system._check_crisis_triggers(states, services, tick=0)

        # 4 quarters of compression at 2% each
        expected = 100.0 * (1.0 - 0.02) ** 4
        assert result[WAYNE_FIPS].median_wage == pytest.approx(expected, rel=1e-9)

    def test_lazy_init_from_defines(self) -> None:
        """Crisis detector initialized lazily from GameDefines."""
        system = TickDynamicsSystem()
        assert system._crisis_detector is None

        county = _make_county()
        states = {WAYNE_FIPS: county}
        services = _make_services()

        system._check_crisis_triggers(states, services, tick=0)

        assert system._crisis_detector is not None

    def test_event_on_phase_change(self) -> None:
        """Phase transitions emit crisis events."""
        system = TickDynamicsSystem()
        # Start NORMAL, profit rate below threshold → will accumulate toward ONSET
        county = _make_county(
            crisis_state=CrisisState(
                phase=CrisisPhase.NORMAL,
                consecutive_below=2,  # One more below triggers ONSET (n_consecutive=3)
            ),
        )
        states = {WAYNE_FIPS: county}
        # Low profit rate → below threshold (0.05)
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): MockTensor(profit_rate=0.01),
            }
        )
        services = _make_services(tensor_registry=registry)

        system._check_crisis_triggers(states, services, tick=52)

        # Should have emitted at least one phase transition event
        assert len(services.event_bus.get_history()) > 0

    def test_no_compression_in_normal_phase(self) -> None:
        """NORMAL phase does not apply wage compression."""
        system = TickDynamicsSystem()
        county = _make_county(median_wage=21.0)
        states = {WAYNE_FIPS: county}
        registry = MockTensorRegistry(
            {
                (WAYNE_FIPS, 2015): MockTensor(profit_rate=0.10),
            }
        )
        services = _make_services(tensor_registry=registry)

        result = system._check_crisis_triggers(states, services, tick=0)
        assert result[WAYNE_FIPS].median_wage == pytest.approx(21.0)


# =============================================================================
# _simulate_transitions — kills ~64 survivors, resolves timeout + 3 suspicious
# =============================================================================


class TestSimulateTransitions:
    """Tests for _simulate_transitions (43.9% score)."""

    def test_no_engine_returns_unchanged(self) -> None:
        """transition_engine=None returns county_states unchanged."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        services = _make_services(transition_engine=None)

        result = system._simulate_transitions(states, params, services)
        assert result[WAYNE_FIPS] is county

    def test_effective_wage_hourly_to_annual(self) -> None:
        """Effective wage = median_wage * 2080 (hourly → annual)."""
        system = TickDynamicsSystem()
        county = _make_county(median_wage=25.0)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        assert len(engine.calls) == 1
        conditions = engine.calls[0][1]
        assert conditions.median_wage == pytest.approx(25.0 * 2080)

    def test_halt_accumulation_below_floor(self) -> None:
        """Wage below floor → effective_wage = 0.0."""
        system = TickDynamicsSystem()
        # floor = 12.0 * 0.8 = 9.6; median_wage 5.0 < 9.6
        county = _make_county(median_wage=5.0)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.median_wage == pytest.approx(0.0)

    def test_result_updates_distribution(self) -> None:
        """ClassDistribution result replaces county's distribution."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        # Mock shifts LA down by 0.01
        engine = MockClassTransitionEngine(delta_la=-0.01)
        services = _make_services(transition_engine=engine)

        result = system._simulate_transitions(states, params, services)

        new_dist = result[WAYNE_FIPS].class_distribution
        # LA was 0.40, shifted by -0.01 = 0.39
        assert new_dist.labor_aristocracy_share == pytest.approx(0.39)
        # Proletariat was 0.35, shifted by +0.01 = 0.36
        assert new_dist.proletariat_share == pytest.approx(0.36)

    def test_invalid_result_preserves_county(self) -> None:
        """Non-ClassDistribution result preserves original county."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        class NoneReturningEngine:
            """Returns None from simulate_transitions."""

            def simulate_transitions(
                self, dist: Any, conditions: Any, crisis_phase: Any = None
            ) -> None:
                return None

        services = _make_services(transition_engine=NoneReturningEngine())
        result = system._simulate_transitions(states, params, services)

        # Original county preserved when result is not ClassDistribution
        assert result[WAYNE_FIPS].class_distribution.labor_aristocracy_share == pytest.approx(0.40)

    def test_crisis_flag_set_during_crisis(self) -> None:
        """Crisis phase != NORMAL sets crisis=True in EconomicConditions."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.crisis is True

    def test_normal_phase_crisis_false(self) -> None:
        """NORMAL phase sets crisis=False in EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county()  # Default: NORMAL phase
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.crisis is False

    def test_year_clamping_in_conditions(self) -> None:
        """Year clamped to [2007, 2030] for EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county(year=2035)
        states = {WAYNE_FIPS: county}
        params = _make_national_params(year=2035)
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.year == 2030

    def test_fips_passed_to_conditions(self) -> None:
        """FIPS code correctly passed to EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.fips == WAYNE_FIPS

    def test_melt_passed_to_conditions(self) -> None:
        """National tau (MELT) correctly passed to EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params(tau=70.0)
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.melt == pytest.approx(70.0)

    def test_phi_hour_passed_to_conditions(self) -> None:
        """County phi_hour correctly passed to EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county(phi_hour=5.0)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.phi_hour == pytest.approx(5.0)

    def test_unemployment_passed_to_conditions(self) -> None:
        """County unemployment_rate passed to EconomicConditions."""
        system = TickDynamicsSystem()
        county = _make_county(unemployment_rate=0.09)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.unemployment_rate == pytest.approx(0.09)


# =============================================================================
# _simulate_transitions — mutation killers for boundary/type/multi-county
# =============================================================================


class TestSimulateTransitionsMutationKillers:
    """Targeted tests to kill mutation survivors in _simulate_transitions."""

    def test_year_clamped_at_lower_bound(self) -> None:
        """county year=2007 (minimum valid) → stays 2007 in conditions."""
        system = TickDynamicsSystem()
        county = _make_county(year=2007)
        states = {WAYNE_FIPS: county}
        params = _make_national_params(year=2007)
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.year == 2007

    def test_year_within_range_unchanged(self) -> None:
        """county year=2015 → stays 2015 (no clamping applied)."""
        system = TickDynamicsSystem()
        county = _make_county(year=2015)
        states = {WAYNE_FIPS: county}
        params = _make_national_params(year=2015)
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        conditions = engine.calls[0][1]
        assert conditions.year == 2015

    def test_distribution_year_reclamped_when_mismatched(self) -> None:
        """county.year=2035 → clamped=2030; dist.year=2015 → reclamped to 2030."""
        system = TickDynamicsSystem()
        # County year=2035 (valid in CountyEconomicState: ge=2007, le=2040)
        # But dist must have year in [2007,2030], so create at 2015
        dist = ClassDistribution(
            fips=WAYNE_FIPS,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        county = _make_county(year=2035, class_distribution=dist)
        states = {WAYNE_FIPS: county}
        params = _make_national_params(year=2035)
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        # Engine receives dist with clamped year=2030 (from county.year clamp)
        passed_dist = engine.calls[0][0]
        assert passed_dist.year == 2030

    def test_distribution_year_matching_no_reclamp(self) -> None:
        """dist.year already == clamped_year → no reconstruction."""
        system = TickDynamicsSystem()
        county = _make_county(year=2015)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        passed_dist = engine.calls[0][0]
        assert passed_dist.year == 2015
        # Shares should be unchanged
        assert passed_dist.labor_aristocracy_share == pytest.approx(0.40)

    def test_sentinel_result_preserves_county(self) -> None:
        """NoDataSentinel result (falsy) preserves original county."""
        from babylon.economics.tensor import NoDataSentinel

        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        class SentinelReturningEngine:
            """Returns NoDataSentinel from simulate_transitions."""

            def simulate_transitions(
                self, dist: Any, conditions: Any, crisis_phase: Any = None
            ) -> NoDataSentinel:
                return NoDataSentinel(fips=WAYNE_FIPS, year=2015, reason="test sentinel")

        services = _make_services(transition_engine=SentinelReturningEngine())
        result = system._simulate_transitions(states, params, services)

        # Original county preserved
        assert result[WAYNE_FIPS].class_distribution.labor_aristocracy_share == pytest.approx(0.40)

    def test_crisis_phase_passed_to_engine(self) -> None:
        """crisis_phase from county.crisis_state.phase passed to engine."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        engine = CapturingTransitionEngine()
        services = _make_services(transition_engine=engine)

        system._simulate_transitions(states, params, services)

        crisis_phase_arg = engine.calls[0][2]
        assert crisis_phase_arg == CrisisPhase.DEEP

    def test_multiple_counties_mixed_results(self) -> None:
        """2 counties: one succeeds, one gets None → mixed output."""
        system = TickDynamicsSystem()
        county_wayne = _make_county(fips=WAYNE_FIPS)
        county_oakland = _make_county(fips=OAKLAND_FIPS)
        states = {WAYNE_FIPS: county_wayne, OAKLAND_FIPS: county_oakland}
        params = _make_national_params()

        call_count = 0

        class AlternatingEngine:
            """Returns valid result for first county, None for second."""

            def simulate_transitions(
                self, dist: Any, conditions: Any, crisis_phase: Any = None
            ) -> ClassDistribution | None:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return dist  # Valid ClassDistribution
                return None  # Second county fails

        services = _make_services(transition_engine=AlternatingEngine())
        result = system._simulate_transitions(states, params, services)

        # Both counties should be present in result
        assert WAYNE_FIPS in result
        assert OAKLAND_FIPS in result

    def test_result_year_matches_clamped_year(self) -> None:
        """Engine returns dist with in-range year=2020; verify result preserved."""
        system = TickDynamicsSystem()
        county = _make_county(year=2020)
        states = {WAYNE_FIPS: county}
        params = _make_national_params(year=2020)

        class YearShiftEngine:
            """Returns ClassDistribution with shifted shares."""

            def simulate_transitions(
                self, dist: Any, conditions: Any, crisis_phase: Any = None
            ) -> ClassDistribution:
                return ClassDistribution(
                    fips=WAYNE_FIPS,
                    year=2020,
                    bourgeoisie_share=dist.bourgeoisie_share,
                    petit_bourgeoisie_share=dist.petit_bourgeoisie_share,
                    labor_aristocracy_share=0.38,
                    proletariat_share=0.37,
                    lumpenproletariat_share=dist.lumpenproletariat_share,
                )

        services = _make_services(transition_engine=YearShiftEngine())
        result = system._simulate_transitions(states, params, services)

        # Result should use the engine output
        assert result[WAYNE_FIPS].class_distribution.year == 2020
        assert result[WAYNE_FIPS].class_distribution.labor_aristocracy_share == pytest.approx(0.38)


# =============================================================================
# step() context extraction — kills ~62 survivors
# =============================================================================


class TestStepContextExtraction:
    """Tests for step() context handling and pipeline gating."""

    def test_tick_context_extracts_tick(self) -> None:
        """TickContext.tick is extracted correctly."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        # tick=52 → year boundary, will execute pipeline
        context = TickContext(tick=52)
        system.step(graph, services, context)

        assert graph.graph["tick_dynamics"]["year"] == 2016

    def test_dict_context_extracts_tick(self) -> None:
        """Dict with 'tick' key is extracted correctly."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = {"tick": 52}
        system.step(graph, services, context)

        assert graph.graph["tick_dynamics"]["year"] == 2016

    def test_unknown_context_defaults_to_zero(self) -> None:
        """Unknown context type → tick=0 (year boundary, pipeline runs)."""
        system = TickDynamicsSystem()
        services = _make_services()
        # No existing state → fresh graph (first tick at tick=0)
        graph = build_territory_graph()
        context: Any = 42  # Not TickContext or dict
        system.step(graph, services, context)

        # tick=0 is year boundary, pipeline should execute
        assert "tick_dynamics" in graph.graph

    def test_no_melt_calculator_returns_early(self) -> None:
        """services.melt_calculator=None causes early return."""
        system = TickDynamicsSystem()
        services = ServiceContainer.create()
        graph = _make_graph_with_state(year=2015)
        context = TickContext(tick=52)

        system.step(graph, services, context)

        # Year should not change (pipeline skipped)
        assert graph.graph["tick_dynamics"]["year"] == 2015

    def test_existing_state_increments_year(self) -> None:
        """Existing state → year = prev_year + 1."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state(year=2018)
        context = TickContext(tick=52)

        system.step(graph, services, context)

        assert graph.graph["tick_dynamics"]["year"] == 2019

    def test_first_tick_bootstraps(self) -> None:
        """No existing state → _determine_year + _bootstrap called."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = build_territory_graph()
        graph.graph["base_year"] = 2010
        context = TickContext(tick=0)

        system.step(graph, services, context)

        assert "tick_dynamics" in graph.graph
        assert graph.graph["tick_dynamics"]["year"] == 2010

    def test_non_year_boundary_returns_immediately(self) -> None:
        """tick % 52 != 0 returns without executing pipeline."""
        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state(year=2015)
        context = TickContext(tick=25)

        system.step(graph, services, context)

        # Year unchanged
        assert graph.graph["tick_dynamics"]["year"] == 2015


# =============================================================================
# _update_coefficients — kills ~18 survivors
# =============================================================================


class TestUpdateCoefficients:
    """Tests for _update_coefficients (33.3% score)."""

    def test_first_tick_uses_raw_values(self) -> None:
        """First tick (prev=None) uses raw values and marks initialized."""
        system = TickDynamicsSystem()
        params = _make_national_params(gamma_basket=0.72, gamma_III=0.35)

        result = system._update_coefficients(params, prev_coefficients=None)

        assert result.gamma_basket == pytest.approx(0.72)
        assert result.gamma_III == pytest.approx(0.35)
        assert result.is_initialized is True

    def test_uninitialized_prev_uses_raw(self) -> None:
        """Prev exists but is_initialized=False → uses raw values."""
        system = TickDynamicsSystem()
        params = _make_national_params(gamma_basket=0.72, gamma_III=0.35)
        prev = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=False,
        )

        result = system._update_coefficients(params, prev_coefficients=prev)

        assert result.gamma_basket == pytest.approx(0.72)
        assert result.gamma_III == pytest.approx(0.35)
        assert result.is_initialized is True

    def test_subsequent_tick_preserves_alpha(self) -> None:
        """Initialized prev → preserves alpha from prev."""
        system = TickDynamicsSystem()
        params = _make_national_params()
        prev = SmoothedCoefficients(
            alpha=0.5,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.40,
            is_initialized=True,
        )

        result = system._update_coefficients(params, prev_coefficients=prev)

        assert result.alpha == pytest.approx(0.5)

    def test_subsequent_tick_preserves_gamma_import(self) -> None:
        """Initialized prev → preserves gamma_import from prev."""
        system = TickDynamicsSystem()
        params = _make_national_params()
        prev = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.42,
            is_initialized=True,
        )

        result = system._update_coefficients(params, prev_coefficients=prev)

        assert result.gamma_import == pytest.approx(0.42)

    def test_default_alpha_when_no_prev(self) -> None:
        """No prev → default alpha=0.3."""
        system = TickDynamicsSystem()
        params = _make_national_params()

        result = system._update_coefficients(params, prev_coefficients=None)

        assert result.alpha == pytest.approx(0.3)

    def test_default_gamma_import_first_tick(self) -> None:
        """First tick → default gamma_import=0.35."""
        system = TickDynamicsSystem()
        params = _make_national_params()

        result = system._update_coefficients(params, prev_coefficients=None)

        assert result.gamma_import == pytest.approx(0.35)

    def test_preserves_alpha_from_uninitialized_prev(self) -> None:
        """Uninitialized prev with custom alpha → alpha preserved."""
        system = TickDynamicsSystem()
        params = _make_national_params()
        prev = SmoothedCoefficients(
            alpha=0.7,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=False,
        )

        result = system._update_coefficients(params, prev_coefficients=prev)

        assert result.alpha == pytest.approx(0.7)


# =============================================================================
# _compute_bifurcation_risk — kills ~29 survivors
# =============================================================================


class TestComputeBifurcationRisk:
    """Tests for _compute_bifurcation_risk (31.0% score)."""

    def test_no_prev_states_returns_unchanged(self) -> None:
        """prev_county_states=None returns county_states unchanged."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        services = _make_services()
        graph = build_territory_graph()

        result = system._compute_bifurcation_risk(
            states, prev_county_states=None, graph=graph, services=services, tick=0
        )

        assert result[WAYNE_FIPS] is county

    def test_normal_phase_returns_neutral_score(self) -> None:
        """NORMAL crisis → neutral bifurcation (score=0)."""
        system = TickDynamicsSystem()
        county = _make_county()  # NORMAL phase
        states = {WAYNE_FIPS: county}
        prev_states = {WAYNE_FIPS: county}
        services = _make_services()
        graph = build_territory_graph()

        result = system._compute_bifurcation_risk(states, prev_states, graph, services, tick=0)

        metric = result[WAYNE_FIPS].bifurcation_risk
        assert metric.score == pytest.approx(0.0)

    def test_lazy_init_from_defines(self) -> None:
        """Calculator initialized lazily from GameDefines."""
        system = TickDynamicsSystem()
        assert system._bifurcation_calculator is None

        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        prev_states = {WAYNE_FIPS: county}
        services = _make_services()
        graph = build_territory_graph()

        system._compute_bifurcation_risk(states, prev_states, graph, services, tick=0)

        assert system._bifurcation_calculator is not None

    def test_metric_stored_on_county(self) -> None:
        """Computed metric stored in county.bifurcation_risk."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        prev_states = {WAYNE_FIPS: county}
        services = _make_services()
        graph = build_territory_graph()

        result = system._compute_bifurcation_risk(states, prev_states, graph, services, tick=0)

        metric = result[WAYNE_FIPS].bifurcation_risk
        # Should have a score (may be 0 due to no solidarity edges)
        assert metric.score is not None
        assert -1.0 <= metric.score <= 1.0

    def test_missing_prev_county_preserves_current(self) -> None:
        """County without matching prev_county → preserved unchanged."""
        system = TickDynamicsSystem()
        crisis = _deep_crisis_state()
        county = _make_county(crisis_state=crisis)
        states = {WAYNE_FIPS: county}
        prev_states: dict[str, CountyEconomicState] = {}  # No prev for Wayne
        services = _make_services()
        graph = build_territory_graph()

        result = system._compute_bifurcation_risk(states, prev_states, graph, services, tick=0)

        assert result[WAYNE_FIPS] is county


# =============================================================================
# _compute_tick_summary — kills ~34 survivors
# =============================================================================


class TestComputeTickSummary:
    """Tests for _compute_tick_summary (66.0% score)."""

    def test_aggregates_phi(self) -> None:
        """phi_aggregate computed from county phi_hour * employment * 2080."""
        system = TickDynamicsSystem()
        county = _make_county(phi_hour=3.50, employment=500_000.0)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        result = system._compute_tick_summary(2015, states, params)

        expected_phi = 3.50 * 500_000.0 * 2080
        assert result.phi_aggregate == pytest.approx(expected_phi)

    def test_weighted_national_distribution(self) -> None:
        """National distribution is employment-weighted average."""
        system = TickDynamicsSystem()
        dist1 = ClassDistribution(
            fips=WAYNE_FIPS,
            year=2015,
            bourgeoisie_share=0.02,
            petit_bourgeoisie_share=0.08,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        dist2 = ClassDistribution(
            fips=OAKLAND_FIPS,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.30,
            proletariat_share=0.40,
            lumpenproletariat_share=0.20,
        )
        c1 = _make_county(fips=WAYNE_FIPS, employment=300_000.0, class_distribution=dist1)
        c2 = _make_county(fips=OAKLAND_FIPS, employment=200_000.0, class_distribution=dist2)
        states = {WAYNE_FIPS: c1, OAKLAND_FIPS: c2}
        params = _make_national_params()

        result = system._compute_tick_summary(2015, states, params)

        # Weighted LA: (0.40*300k + 0.30*200k) / 500k = (120k + 60k) / 500k = 0.36
        assert result.national_class_distribution["labor_aristocracy"] == pytest.approx(0.36)

    def test_empty_rates_default_zero(self) -> None:
        """Empty profit rates yield mean 0.0."""
        system = TickDynamicsSystem()
        # County with zero employment → profit_rate will be None from rate calculator
        county = _make_county(employment=0.0, capital_stock=0.0, phi_hour=0.0)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        result = system._compute_tick_summary(2015, states, params)

        assert result.mean_profit_rate == pytest.approx(0.0)

    def test_year_clamping(self) -> None:
        """Year outside [2007, 2040] is clamped."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        result = system._compute_tick_summary(2050, states, params)
        assert result.year == 2040

    def test_counties_processed_count(self) -> None:
        """counties_processed equals number of county states."""
        system = TickDynamicsSystem()
        c1 = _make_county(fips=WAYNE_FIPS)
        c2 = _make_county(fips=OAKLAND_FIPS)
        states = {WAYNE_FIPS: c1, OAKLAND_FIPS: c2}
        params = _make_national_params()

        result = system._compute_tick_summary(2015, states, params)
        assert result.counties_processed == 2

    def test_national_melt_from_params(self) -> None:
        """national_melt equals params.tau."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params(tau=70.0)

        result = system._compute_tick_summary(2015, states, params)
        assert result.national_melt == pytest.approx(70.0)

    def test_summary_year_below_minimum(self) -> None:
        """Year below 2007 clamped to 2007."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()

        result = system._compute_tick_summary(2000, states, params)
        assert result.year == 2007


# =============================================================================
# _compute_imperial_rent — kills ~11 survivors
# =============================================================================


class TestComputeImperialRent:
    """Tests for _compute_imperial_rent (76.1% score)."""

    def test_no_calculator_returns_unchanged(self) -> None:
        """imperial_rent_calculator=None returns states unchanged."""
        system = TickDynamicsSystem()
        county = _make_county(phi_hour=3.50)
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        services = _make_services(imperial_rent_calculator=None)

        result = system._compute_imperial_rent(states, params, services)
        assert result[WAYNE_FIPS].phi_hour == pytest.approx(3.50)

    def test_phi_hour_clamped_to_zero(self) -> None:
        """Negative phi_hour from calculator clamped to 0.0."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        services = _make_services(
            imperial_rent_calculator=MockImperialRentCalculator(phi_hour=-2.0)
        )

        result = system._compute_imperial_rent(states, params, services)
        assert result[WAYNE_FIPS].phi_hour == pytest.approx(0.0)

    def test_positive_phi_hour_stored(self) -> None:
        """Positive phi_hour from calculator stored on county."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params()
        services = _make_services(imperial_rent_calculator=MockImperialRentCalculator(phi_hour=5.0))

        result = system._compute_imperial_rent(states, params, services)
        assert result[WAYNE_FIPS].phi_hour == pytest.approx(5.0)

    def test_national_params_passed_correctly(self) -> None:
        """NationalParameters built with correct values from NationalTickParameters."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        params = _make_national_params(tau=65.0, gamma_basket=0.72)

        class CapturingRentCalc:
            """Captures input params for assertion."""

            def __init__(self) -> None:
                self.captured_params: Any = None

            def compute_phi_hour(self, wage: float, params: Any) -> float:
                self.captured_params = params
                return 0.0

        calc = CapturingRentCalc()
        services = _make_services(imperial_rent_calculator=calc)

        system._compute_imperial_rent(states, params, services)

        assert calc.captured_params.tau == pytest.approx(65.0)
        assert calc.captured_params.gamma_basket == pytest.approx(0.72)


# =============================================================================
# _derive_precarity — kills ~7 survivors
# =============================================================================


class TestDerivePrecarity:
    """Tests for _derive_precarity (53.3% score)."""

    def test_uses_lumpenproletariat_share(self) -> None:
        """Precaritization rate is lumpenproletariat_share."""
        system = TickDynamicsSystem()
        dist = ClassDistribution(
            fips=WAYNE_FIPS,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.30,
            lumpenproletariat_share=0.20,
        )
        county = _make_county(class_distribution=dist, unemployment_rate=0.05)
        states = {WAYNE_FIPS: county}

        result = system._derive_precarity(states)

        # u6 = unemployment_rate + lumpenproletariat_share = 0.05 + 0.20 = 0.25
        assert result[WAYNE_FIPS].u6_rate == pytest.approx(0.25)

    def test_updates_u6_pter_nilf(self) -> None:
        """All three precarity indicators are updated."""
        system = TickDynamicsSystem()
        dist = ClassDistribution(
            fips=WAYNE_FIPS,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        county = _make_county(class_distribution=dist, unemployment_rate=0.053)
        states = {WAYNE_FIPS: county}

        result = system._derive_precarity(states)

        c = result[WAYNE_FIPS]
        # u6 = 0.053 + 0.15 = 0.203
        assert c.u6_rate == pytest.approx(0.203)
        # pter = 0.15 * 0.4 = 0.06
        assert c.pter_rate == pytest.approx(0.06)
        # nilf = 0.15 * 0.6 = 0.09
        assert c.nilf_rate == pytest.approx(0.09)


# =============================================================================
# _validate_distributions — kills ~4 survivors
# =============================================================================


class TestValidateDistributions:
    """Tests for _validate_distributions (69.2% score)."""

    def test_passes_within_tolerance(self) -> None:
        """Sum = 1.0 within tolerance (0.001) passes."""
        system = TickDynamicsSystem()
        county = _make_county()  # Default dist sums to 1.0
        states = {WAYNE_FIPS: county}

        # Should not raise
        system._validate_distributions(states)

    def test_fails_outside_tolerance(self) -> None:
        """Sum outside tolerance raises ValueError."""
        system = TickDynamicsSystem()
        # Use model_construct to bypass Pydantic validation for invalid dist
        invalid_dist = ClassDistribution.model_construct(
            fips=WAYNE_FIPS,
            year=2015,
            bourgeoisie_share=0.02,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.41,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        county = CountyEconomicState.model_construct(
            fips=WAYNE_FIPS,
            year=2015,
            capital_stock=1e9,
            throughput_position=0.90,
            supply_chain_depth=2.1,
            unemployment_rate=0.053,
            u6_rate=0.10,
            pter_rate=0.04,
            nilf_rate=0.06,
            median_wage=21.0,
            employment=500_000.0,
            class_distribution=invalid_dist,
            phi_hour=3.50,
            crisis_state=CrisisState.normal(),
            bifurcation_risk=BifurcationRiskMetric(),
        )
        states = {WAYNE_FIPS: county}

        with pytest.raises(ValueError, match="class shares sum to"):
            system._validate_distributions(states)

    def test_exact_one_passes(self) -> None:
        """Exactly 1.0 passes validation."""
        system = TickDynamicsSystem()
        county = _make_county()
        states = {WAYNE_FIPS: county}
        # Sum is exactly 0.01+0.09+0.40+0.35+0.15 = 1.00
        system._validate_distributions(states)


# =============================================================================
# _compute_national_params (direct) — kills remaining ~21 survivors
# =============================================================================


class TestComputeNationalParams:
    """Direct tests for _compute_national_params (74.1% score)."""

    def test_returns_none_for_sentinel_melt(self) -> None:
        """NoDataSentinel from MELT calculator returns None."""
        system = TickDynamicsSystem()
        sentinel_melt = MockMELTCalculator(tau=62.0, force_sentinel=True)
        services = _make_services(melt_calculator=sentinel_melt)

        result = system._compute_national_params(2015, services, prev_coefficients=None)
        assert result is None

    def test_v_reproduction_matches_default(self) -> None:
        """v_reproduction equals DEFAULT_V_REPRODUCTION."""
        system = TickDynamicsSystem()
        services = _make_services()

        result = system._compute_national_params(2015, services, prev_coefficients=None)

        assert result is not None
        assert result.v_reproduction == pytest.approx(DEFAULT_V_REPRODUCTION)

    def test_gamma_basket_default_without_calculator(self) -> None:
        """No basket_calculator → gamma_basket defaults to 0.68."""
        system = TickDynamicsSystem()
        services = _make_services(basket_calculator=None)

        result = system._compute_national_params(2015, services, prev_coefficients=None)

        assert result is not None
        assert result.gamma_basket_raw == pytest.approx(0.68)

    def test_gamma_III_default_without_calculator(self) -> None:
        """No gamma_calculator → gamma_III defaults to 0.33."""
        system = TickDynamicsSystem()
        services = _make_services(gamma_calculator=None)

        result = system._compute_national_params(2015, services, prev_coefficients=None)

        assert result is not None
        assert result.gamma_III_raw == pytest.approx(0.33)

    def test_year_clamping_to_2040(self) -> None:
        """Year > 2040 clamped to 2040."""
        system = TickDynamicsSystem()
        melt = MockMELTCalculator(tau=62.0, accept_any_year=True)
        services = _make_services(melt_calculator=melt)

        result = system._compute_national_params(2050, services, prev_coefficients=None)

        assert result is not None
        assert result.year == 2040

    def test_year_clamping_to_2007(self) -> None:
        """Year < 2007 clamped to 2007."""
        system = TickDynamicsSystem()
        melt = MockMELTCalculator(tau=62.0, accept_any_year=True)
        services = _make_services(melt_calculator=melt)

        result = system._compute_national_params(2000, services, prev_coefficients=None)

        assert result is not None
        assert result.year == 2007

    def test_estimated_flag_from_basket_calculator(self) -> None:
        """estimated flag comes from basket calculator."""
        system = TickDynamicsSystem()
        services = _make_services(
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.70, estimated=False)
        )

        result = system._compute_national_params(2015, services, prev_coefficients=None)

        assert result is not None
        assert result.estimated is False

    def test_estimated_default_true_without_basket(self) -> None:
        """No basket_calculator → estimated defaults to True."""
        system = TickDynamicsSystem()
        services = _make_services(basket_calculator=None)

        result = system._compute_national_params(2015, services, prev_coefficients=None)

        assert result is not None
        assert result.estimated is True


# =============================================================================
# _compute_county_states (direct) — kills remaining ~57 survivors
# =============================================================================


class TestComputeCountyStates:
    """Direct tests for _compute_county_states (61.7% score)."""

    def test_capital_stock_from_calculator(self) -> None:
        """K comes from capital_calculator.get_K()."""
        system = TickDynamicsSystem()
        services = _make_services(capital_calculator=MockCapitalStockCalculator(k_value=5e9))

        result = system._compute_county_states(
            2015, [WAYNE_FIPS], services, prev_county_states=None
        )

        assert result[WAYNE_FIPS].capital_stock == pytest.approx(5e9)

    def test_preserves_previous_state(self) -> None:
        """Previous county state values carried forward."""
        system = TickDynamicsSystem()
        services = _make_services(
            capital_calculator=None,
            throughput_calculator=None,
        )
        prev = _make_county(
            unemployment_rate=0.08,
            median_wage=25.0,
            employment=300_000.0,
            phi_hour=4.0,
            capital_stock=2e9,
        )
        prev_states = {WAYNE_FIPS: prev}

        result = system._compute_county_states(
            2016, [WAYNE_FIPS], services, prev_county_states=prev_states
        )

        county = result[WAYNE_FIPS]
        assert county.unemployment_rate == pytest.approx(0.08)
        assert county.median_wage == pytest.approx(25.0)
        assert county.employment == pytest.approx(300_000.0)
        assert county.phi_hour == pytest.approx(4.0)
        assert county.capital_stock == pytest.approx(2e9)

    def test_year_clamping(self) -> None:
        """Year clamped to [2007, 2040]."""
        system = TickDynamicsSystem()
        # Use None for throughput_calculator (ThroughputMetrics rejects year>2040)
        services = _make_services(throughput_calculator=None)

        result = system._compute_county_states(
            2050, [WAYNE_FIPS], services, prev_county_states=None
        )

        assert result[WAYNE_FIPS].year == 2040

    def test_default_distribution_no_prev(self) -> None:
        """No previous state → default class distribution shares."""
        system = TickDynamicsSystem()
        services = _make_services()

        result = system._compute_county_states(
            2015, [WAYNE_FIPS], services, prev_county_states=None
        )

        dist = result[WAYNE_FIPS].class_distribution
        assert dist.bourgeoisie_share == pytest.approx(0.01)
        assert dist.petit_bourgeoisie_share == pytest.approx(0.09)
        assert dist.labor_aristocracy_share == pytest.approx(0.40)
        assert dist.proletariat_share == pytest.approx(0.35)
        assert dist.lumpenproletariat_share == pytest.approx(0.15)

    def test_default_values_no_prev(self) -> None:
        """No previous state → defaults for all numeric fields."""
        system = TickDynamicsSystem()
        services = _make_services(
            capital_calculator=None,
            throughput_calculator=None,
        )

        result = system._compute_county_states(
            2015, [WAYNE_FIPS], services, prev_county_states=None
        )

        county = result[WAYNE_FIPS]
        assert county.capital_stock == pytest.approx(0.0)
        assert county.throughput_position == pytest.approx(1.0)
        assert county.supply_chain_depth == pytest.approx(2.0)
        assert county.unemployment_rate == pytest.approx(0.05)
        assert county.u6_rate == pytest.approx(0.10)
        assert county.pter_rate == pytest.approx(0.04)
        assert county.nilf_rate == pytest.approx(0.06)
        assert county.median_wage == pytest.approx(21.0)
        assert county.employment == pytest.approx(100_000.0)
        assert county.phi_hour == pytest.approx(0.0)

    def test_throughput_from_calculator(self) -> None:
        """Throughput metrics from calculator override defaults."""
        system = TickDynamicsSystem()
        services = _make_services(
            throughput_calculator=MockThroughputCalculator(pi=1.20, supply_chain_depth=3.5)
        )

        result = system._compute_county_states(
            2015, [WAYNE_FIPS], services, prev_county_states=None
        )

        county = result[WAYNE_FIPS]
        assert county.throughput_position == pytest.approx(1.20)
        assert county.supply_chain_depth == pytest.approx(3.5)

    def test_distribution_year_updated_on_year_change(self) -> None:
        """Previous distribution's year updated when county year changes."""
        system = TickDynamicsSystem()
        services = _make_services()
        prev = _make_county(year=2015)
        prev_states = {WAYNE_FIPS: prev}

        result = system._compute_county_states(
            2016, [WAYNE_FIPS], services, prev_county_states=prev_states
        )

        assert result[WAYNE_FIPS].class_distribution.year == 2016

    def test_crisis_state_preserved_from_prev(self) -> None:
        """Crisis state carried forward from previous state."""
        system = TickDynamicsSystem()
        services = _make_services()
        crisis = _deep_crisis_state()
        prev = _make_county(crisis_state=crisis)
        prev_states = {WAYNE_FIPS: prev}

        result = system._compute_county_states(
            2016, [WAYNE_FIPS], services, prev_county_states=prev_states
        )

        assert result[WAYNE_FIPS].crisis_state.phase == CrisisPhase.DEEP


# =============================================================================
# _write_hex_substrate — hex-to-graph bridge integration
# =============================================================================


class TestWriteHexSubstrate:
    """Tests for Step 9: hex substrate → graph bridge.

    Verifies that when a HexGrid is available on ServiceContainer,
    the tick pipeline writes hex_* attributes to territory nodes.
    """

    def test_no_hex_grid_is_noop(self) -> None:
        """Pipeline completes without error when hex_grid is None."""
        system = TickDynamicsSystem()
        services = _make_services()  # hex_grid=None by default
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        # No hex_ attributes on territory node
        node_data = graph.nodes[WAYNE_FIPS]
        hex_attrs = [k for k in node_data if k.startswith("hex_")]
        assert hex_attrs == []

    def test_hex_grid_writes_hex_attributes(self) -> None:
        """When hex_grid is provided, hex_ attributes appear on territory nodes."""

        from babylon.economics.substrate.types import HexEconomicState

        system = TickDynamicsSystem()

        # Build a HexGrid where the R6 parent matches WAYNE_FIPS territory ID
        # The mock uses "86<fips>ffffff" as R6 parent, but our graph uses WAYNE_FIPS
        # as the territory node ID. We need to align them.
        hex_ids = ["872830828ffffff", "872830829ffffff", "87283082affffff"]
        hexes = {}
        for i, h3_id in enumerate(hex_ids):
            hexes[h3_id] = HexEconomicState(
                h3_index=h3_id,
                county_fips=WAYNE_FIPS,
                constant_capital=100.0 + i * 10,
                variable_capital=80.0 + i * 5,
                surplus_value=40.0 + i * 3,
                employment=1000.0 + i * 100,
                dept_shares=(0.20, 0.35, 0.25, 0.20),
            )

        from babylon.economics.substrate.types import HexGrid

        # Use WAYNE_FIPS as the R6 parent so it matches the territory node ID
        grid = HexGrid(
            hexes=hexes,
            county_hex_ids={WAYNE_FIPS: frozenset(hex_ids)},
            res6_parents=dict.fromkeys(hex_ids, WAYNE_FIPS),
            res5_parents=dict.fromkeys(hex_ids, f"85{WAYNE_FIPS}fffffff"),
            res6_children={WAYNE_FIPS: frozenset(hex_ids)},
            res5_children={f"85{WAYNE_FIPS}fffffff": frozenset(hex_ids)},
        )

        services = _make_services(hex_grid=grid)
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        # hex_ attributes should be on the territory node
        node_data = graph.nodes[WAYNE_FIPS]
        assert "hex_total_capital" in node_data
        assert "hex_profit_rate" in node_data
        assert "hex_employment" in node_data
        assert "hex_exploitation_rate" in node_data
        assert "hex_organic_composition" in node_data

        # Verify conservation: hex total capital equals c+v+s of all children
        expected_total = sum(
            h.constant_capital + h.variable_capital + h.surplus_value for h in hexes.values()
        )
        assert node_data["hex_total_capital"] == pytest.approx(expected_total)

    def test_hex_and_tick_attributes_coexist(self) -> None:
        """Both hex_ and tick_ attributes present on same territory node."""
        from babylon.economics.substrate.types import HexEconomicState, HexGrid

        system = TickDynamicsSystem()

        hex_ids = ["872830828ffffff"]
        hexes = {
            hex_ids[0]: HexEconomicState(
                h3_index=hex_ids[0],
                county_fips=WAYNE_FIPS,
                constant_capital=100.0,
                variable_capital=80.0,
                surplus_value=40.0,
                employment=1000.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            ),
        }
        grid = HexGrid(
            hexes=hexes,
            county_hex_ids={WAYNE_FIPS: frozenset(hex_ids)},
            res6_parents={hex_ids[0]: WAYNE_FIPS},
            res5_parents={hex_ids[0]: f"85{WAYNE_FIPS}fffffff"},
            res6_children={WAYNE_FIPS: frozenset(hex_ids)},
            res5_children={f"85{WAYNE_FIPS}fffffff": frozenset(hex_ids)},
        )

        services = _make_services(hex_grid=grid)
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        node_data = graph.nodes[WAYNE_FIPS]
        # tick_ attributes from county-level pipeline
        assert "tick_capital_stock" in node_data
        assert "tick_profit_rate" in node_data or "tick_median_wage" in node_data
        # hex_ attributes from substrate bridge
        assert "hex_total_capital" in node_data
        assert "hex_profit_rate" in node_data

    def test_invalid_hex_grid_type_is_noop(self) -> None:
        """Non-HexGrid object for hex_grid logs warning, no crash."""
        system = TickDynamicsSystem()
        services = _make_services(hex_grid="not_a_hex_grid")
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        # Should not crash — just log a warning and skip
        system.step(graph, services, context)

        node_data = graph.nodes[WAYNE_FIPS]
        hex_attrs = [k for k in node_data if k.startswith("hex_")]
        assert hex_attrs == []
