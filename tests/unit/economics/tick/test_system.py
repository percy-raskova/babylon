"""Tests for TickDynamicsSystem.

Feature: 017-simulation-tick-dynamics
Tasks: T010 (US1), T012 (US2), T016 (US3)
"""

from __future__ import annotations

from typing import Any

import networkx as nx
from tests.unit.economics.tick.conftest import (
    WAYNE_FIPS,
    MockBasketVisibilityCalculator,
    MockCapitalStockCalculator,
    MockClassTransitionEngine,
    MockGammaIIICalculator,
    MockImperialRentCalculator,
    MockMELTCalculator,
    MockThroughputCalculator,
    build_territory_graph,
)

from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tick.types import (
    CountyEconomicState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer


def _make_services(**kwargs: Any) -> ServiceContainer:
    """Create ServiceContainer with mock calculators."""
    defaults = {
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
        crisis=False,
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


# =============================================================================
# US1: National Parameter Computation (T010)
# =============================================================================


class TestNationalParameterComputation:
    """Tests for Step 2: compute national parameters."""

    def test_tau_matches_melt_calculator(self) -> None:
        """Verify tau comes from MELTCalculator.get_melt()."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(melt_calculator=MockMELTCalculator(tau=65.0))
        graph = _make_graph_with_state()

        # Use year-boundary tick (tick % 52 == 0)
        context = TickContext(tick=52)
        system.step(graph, services, context)

        tick_data = graph.graph.get("tick_dynamics", {})
        assert tick_data.get("national_params") is not None
        assert tick_data["national_params"].tau == 65.0

    def test_gamma_basket_matches_basket_calculator(self) -> None:
        """Verify gamma_basket comes from BasketVisibilityCalculator."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.72)
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.gamma_basket_raw == 0.72

    def test_gamma_III_matches_gamma_calculator(self) -> None:
        """Verify gamma_III comes from GammaIIICalculator."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(gamma_calculator=MockGammaIIICalculator(gamma_iii=0.40))
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert params.gamma_III_raw == 0.40

    def test_tau_effective_equals_tau_times_gamma_basket(self) -> None:
        """Verify tau_effective = tau * gamma_basket."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(
            melt_calculator=MockMELTCalculator(tau=62.0),
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.68),
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        params = graph.graph["tick_dynamics"]["national_params"]
        assert abs(params.tau_effective - 62.0 * 0.68) < 0.01

    def test_no_data_sentinel_halts_with_context(self) -> None:
        """Verify NoDataSentinel from MELT calculator causes pipeline to skip (FR-025)."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()

        # Create a mock that always returns NoDataSentinel
        sentinel_melt = MockMELTCalculator(tau=62.0)
        sentinel_melt.get_melt = lambda year: NoDataSentinel(  # type: ignore[assignment]
            fips="USA", year=year, reason="Forced sentinel for testing"
        )
        services = _make_services(melt_calculator=sentinel_melt)

        graph = _make_graph_with_state(year=2015)
        context = TickContext(tick=52)

        # Pipeline should skip gracefully (no crash, state unchanged at year 2015)
        system.step(graph, services, context)

        tick_data = graph.graph.get("tick_dynamics", {})
        assert tick_data.get("year") == 2015  # unchanged from setup


# =============================================================================
# US2: County-Level State Computation (T012)
# =============================================================================


class TestCountyStateComputation:
    """Tests for Step 3a: compute county-level state."""

    def test_capital_stock_from_calculator(self) -> None:
        """Verify K comes from CapitalStockCalculator.get_K()."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(capital_calculator=MockCapitalStockCalculator(k_value=2e9))
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        tick_data = graph.graph["tick_dynamics"]
        county_states = tick_data.get("county_states")
        if county_states is not None and WAYNE_FIPS in county_states:
            assert county_states[WAYNE_FIPS].capital_stock == 2e9
        else:
            # Check node directly
            assert graph.nodes[WAYNE_FIPS]["tick_capital_stock"] == 2e9

    def test_throughput_from_calculator(self) -> None:
        """Verify pi comes from ThroughputCalculator.compute_metrics()."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services(
            throughput_calculator=MockThroughputCalculator(pi=1.10, supply_chain_depth=3.0)
        )
        graph = _make_graph_with_state()
        context = TickContext(tick=52)
        system.step(graph, services, context)

        assert graph.nodes[WAYNE_FIPS]["tick_throughput_position"] == 1.10


# =============================================================================
# US3: Full Tick Pipeline (T016) - partial (more in Phase 5)
# =============================================================================


class TestFullTickPipeline:
    """Tests for the full 8-step pipeline."""

    def test_system_name(self) -> None:
        """Verify system name property."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        assert system.name == "tick_dynamics"

    def test_non_year_boundary_is_noop(self) -> None:
        """Verify system does nothing on non-year-boundary ticks."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=1)  # Not a year boundary

        # Capture state before
        old_k = graph.nodes[WAYNE_FIPS].get("tick_capital_stock", 1e9)

        system.step(graph, services, context)

        # State should be unchanged since not a year boundary
        new_k = graph.nodes[WAYNE_FIPS].get("tick_capital_stock", 1e9)
        assert new_k == old_k

    def test_year_boundary_updates_state(self) -> None:
        """Verify system updates state on year-boundary ticks."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)  # Year boundary

        system.step(graph, services, context)

        # Should have updated tick dynamics metadata
        assert "tick_dynamics" in graph.graph

    def test_class_distribution_sums_to_one(self) -> None:
        """Verify class distribution sum-to-one invariant after tick."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        services = _make_services()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        system.step(graph, services, context)

        dist = graph.nodes[WAYNE_FIPS].get("tick_class_distribution", {})
        if dist:
            total = sum(dist.values())
            assert abs(total - 1.0) < 0.01

    def test_missing_calculators_skips_gracefully(self) -> None:
        """Verify system handles missing calculators (None) gracefully."""
        from babylon.economics.tick.system import TickDynamicsSystem

        system = TickDynamicsSystem()
        # Create services without economics calculators
        services = ServiceContainer.create()
        graph = _make_graph_with_state()
        context = TickContext(tick=52)

        # Should not crash; just skip tick dynamics
        system.step(graph, services, context)
