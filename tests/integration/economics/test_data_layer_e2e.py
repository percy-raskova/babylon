"""End-to-end integration tests proving the data layer works as a pipeline.

Feature: 019-data-layer-hardening

These tests exercise 6 layers of the data stack using real QCEW data where
available and mock sources where database tables are empty (BEA, ATUS):

    1. Data Access   - SQLiteQCEWSource queries fact_qcew_annual
    2. Transformation - MarxianHydrator -> ValueTensor4x3
    3. Initialization - DefaultTickInitializer seeds state
    4. Graph Round-Trip - write/read_tick_state_to/from_graph
    5. System Evolution - TickDynamicsSystem.step() at year boundary
    6. Multi-County   - 3-county Detroit metro pipeline

Tests skip gracefully when the QCEW database is not populated.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.domain.economics.tick.graph_bridge import (
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.domain.economics.tick.initializer import DefaultTickInitializer
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from tests.unit.economics.tick.conftest import (
    MockBasketVisibilityCalculator,
    MockCapitalStockCalculator,
    MockClassTransitionEngine,
    MockGammaIIICalculator,
    MockMELTCalculator,
    MockThroughputCalculator,
    build_territory_graph,
)

# Wayne County MI (Detroit core)
WAYNE_FIPS: str = "26163"
# Oakland County MI (affluent suburb)
OAKLAND_FIPS: str = "26125"
# Macomb County MI (working-class suburb)
MACOMB_FIPS: str = "26099"
# Test year (QCEW data is populated for 2010-2019+)
TEST_YEAR: int = 2015

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

WEEKS_PER_YEAR: int = 52


def _make_services(**kwargs: Any) -> ServiceContainer:
    """Create ServiceContainer with mock calculators.

    Args:
        **kwargs: Override any mock calculator.

    Returns:
        ServiceContainer with all mock calculators configured.
    """
    defaults: dict[str, Any] = {
        "melt_calculator": MockMELTCalculator(),
        "basket_calculator": MockBasketVisibilityCalculator(),
        "gamma_calculator": MockGammaIIICalculator(),
        "capital_calculator": MockCapitalStockCalculator(),
        "throughput_calculator": MockThroughputCalculator(),
        "transition_engine": MockClassTransitionEngine(),
    }
    defaults.update(kwargs)
    return ServiceContainer.create(**defaults)


@pytest.mark.integration
class TestDataLayerEndToEnd:
    """Prove the data layer works end-to-end from database to graph."""

    def test_qcew_data_accessible(self, real_qcew_source: Any) -> None:
        """Layer 1: Real QCEW data is queryable from the 3NF schema.

        Queries Wayne County (26163) for year 2015 and verifies:
        - Records are returned (>0)
        - Each record has a NAICS code (str), wages (float > 0), employment (int >= 0)
        """
        records = real_qcew_source.fetch_county_wages(WAYNE_FIPS, TEST_YEAR)

        assert len(records) > 0, "Expected QCEW records for Wayne County 2015"

        positive_wage_count = 0
        for naics_code, wages, employment in records:
            assert isinstance(naics_code, str), f"NAICS code should be str, got {type(naics_code)}"
            assert isinstance(wages, float), f"Wages should be float, got {type(wages)}"
            assert wages >= 0, f"Wages should be non-negative, got {wages} for NAICS {naics_code}"
            assert isinstance(employment, int), f"Employment should be int, got {type(employment)}"
            assert employment >= 0, (
                f"Employment should be non-negative, got {employment} for NAICS {naics_code}"
            )
            if wages > 0:
                positive_wage_count += 1

        assert positive_wage_count > 0, "At least some records should have positive wages"

    def test_hydrator_produces_tensor_from_real_data(self, production_hydrator: Any) -> None:
        """Layer 2: QCEW data transforms into typed economic tensors.

        Hydrates Wayne County 2015 via production hydrator and verifies:
        - Dept IIa (necessary consumption) has real wage data (v > 0)
        - Total variable capital is non-zero
        - All department values are non-negative
        """
        tensor = production_hydrator.hydrate(WAYNE_FIPS, TEST_YEAR)

        # Wayne County should have substantial necessary consumption (IIa)
        assert tensor.dept_IIa.v > 0, "Dept IIa should have real wage data"
        assert tensor.total_v > 0, "Total variable capital should be non-zero"

        # All department values must be non-negative
        for dept_name in ("dept_I", "dept_IIa", "dept_IIb", "dept_III"):
            dept_row = getattr(tensor, dept_name)
            assert dept_row.c >= 0, f"{dept_name}.c should be non-negative"
            assert dept_row.v >= 0, f"{dept_name}.v should be non-negative"
            assert dept_row.s >= 0, f"{dept_name}.s should be non-negative"

    def test_initializer_seeds_state(self) -> None:
        """Layer 3: DefaultTickInitializer wires calculator results into typed state.

        Creates ServiceContainer with mock calculators, runs initializer,
        and verifies state is correctly seeded.
        """
        services = _make_services()
        initializer = DefaultTickInitializer()

        state = initializer.initialize(TEST_YEAR, [WAYNE_FIPS], services)

        # National params come from mock calculators
        assert state.national_params.tau == 62.0, "tau should match MockMELTCalculator"
        assert state.national_params.gamma_basket == 0.68, (
            "gamma_basket should match MockBasketVisibilityCalculator"
        )

        # County state should exist
        assert WAYNE_FIPS in state.county_states, "Wayne County should be in state"

        # Capital stock from MockCapitalStockCalculator
        assert state.county_states[WAYNE_FIPS].capital_stock == 1_000_000_000.0, (
            "capital_stock should match MockCapitalStockCalculator"
        )

        # Year should match
        assert state.year == TEST_YEAR

    def test_graph_bridge_round_trip_preserves_state(self) -> None:
        """Layer 4: Graph bridge serialization is lossless.

        Initializes state, writes to graph, reads back, and verifies
        all critical fields are preserved.
        """
        services = _make_services()
        initializer = DefaultTickInitializer()
        state = initializer.initialize(TEST_YEAR, [WAYNE_FIPS], services)

        # Write to graph
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, state)

        # Read back
        restored = read_tick_state_from_graph(graph)
        assert restored is not None, "Should be able to read state from graph"

        # Verify national params round-trip
        assert restored.year == state.year
        assert restored.national_params.tau == state.national_params.tau
        assert restored.national_params.gamma_basket == state.national_params.gamma_basket

        # Verify county state round-trip
        assert WAYNE_FIPS in restored.county_states
        original_county = state.county_states[WAYNE_FIPS]
        restored_county = restored.county_states[WAYNE_FIPS]
        assert restored_county.capital_stock == original_county.capital_stock
        assert restored_county.throughput_position == original_county.throughput_position

        # Verify class distribution round-trip
        orig_dist = original_county.class_distribution
        rest_dist = restored_county.class_distribution
        assert rest_dist.bourgeoisie_share == orig_dist.bourgeoisie_share
        assert rest_dist.labor_aristocracy_share == orig_dist.labor_aristocracy_share
        assert rest_dist.proletariat_share == orig_dist.proletariat_share

    def test_system_step_evolves_state_on_year_boundary(self) -> None:
        """Layer 5: Full 8-step pipeline executes correctly on year boundary.

        Initializes 2015 state, writes to graph, runs system.step at tick 52
        (year boundary), and verifies state evolution.
        """
        services = _make_services()
        initializer = DefaultTickInitializer()
        system = TickDynamicsSystem()

        state = initializer.initialize(TEST_YEAR, [WAYNE_FIPS], services)
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, state)

        # Step at year boundary (tick 52)
        system.step(graph, services, TickContext(tick=WEEKS_PER_YEAR))

        tick_data = graph.graph.get("tick_dynamics", {})

        # Year should advance to 2016
        assert tick_data.get("year") == TEST_YEAR + 1, "Year should advance to 2016"

        # Class distribution should sum to ~1.0
        dist = graph.nodes[WAYNE_FIPS].get("tick_class_distribution", {})
        assert dist, "Class distribution should be present"
        total = sum(dist.values())
        assert abs(total - 1.0) < 0.01, f"Class distribution sum={total}, expected ~1.0"

        # phi_hour should be set (imperial rent computed)
        phi_hour = graph.nodes[WAYNE_FIPS].get("tick_phi_hour")
        assert phi_hour is not None, "phi_hour should be computed"

        # Coefficients should be initialized
        coefficients = tick_data.get("coefficients")
        assert coefficients is not None, "Coefficients should be present"
        assert coefficients.is_initialized is True, "Coefficients should be initialized"

    def test_multi_county_detroit_metro(self) -> None:
        """Layer 6: Pipeline scales to multi-county with state isolation.

        Initializes 3 Detroit metro counties, runs 3 year boundaries,
        and verifies each county has independent valid state.
        """
        county_fips = [WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS]
        services = _make_services()
        initializer = DefaultTickInitializer()
        system = TickDynamicsSystem()

        state = initializer.initialize(TEST_YEAR, county_fips, services)
        graph = build_territory_graph(fips_codes=county_fips)
        write_tick_state_to_graph(graph, state)

        expected_years = [TEST_YEAR + 1, TEST_YEAR + 2, TEST_YEAR + 3]
        max_ticks = 3

        for i in range(1, max_ticks + 1):
            tick = i * WEEKS_PER_YEAR
            system.step(graph, services, TickContext(tick=tick))

            tick_data = graph.graph.get("tick_dynamics", {})
            assert tick_data.get("year") == expected_years[i - 1], (
                f"Year should be {expected_years[i - 1]} at tick {tick}"
            )

            # All 3 counties should have valid state
            for fips in county_fips:
                dist = graph.nodes[fips].get("tick_class_distribution", {})
                assert dist, f"County {fips} should have class distribution at tick {tick}"
                total = sum(dist.values())
                assert abs(total - 1.0) < 0.01, (
                    f"County {fips} distribution sum={total} at tick {tick}"
                )
