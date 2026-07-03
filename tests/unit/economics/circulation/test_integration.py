"""Integration tests for circulation state in tick system.

Feature: 023-capital-volume-ii (Phase 10)

Tests that CirculationCrisisState integrates correctly with
CountyEconomicState and the graph bridge serialization layer.
"""

from __future__ import annotations

import pytest

from babylon.economics.circulation.types import (
    CircuitState,
    CirculationCrisisAssessment,
    CirculationCrisisState,
    DepreciationFundState,
    InventoryDiagnosis,
    InventoryState,
    ReplacementCyclePosition,
)
from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisState,
)
from babylon.engine.graph import BabylonGraph
from babylon.models.types import Currency

# =============================================================================
# Fixtures
# =============================================================================


def _make_class_distribution(fips: str = "26163", year: int = 2022) -> ClassDistribution:
    """Create a standard class distribution for testing."""
    return ClassDistribution(
        fips=fips,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )


def _make_county_state(
    fips: str = "26163",
    year: int = 2022,
    circulation: CirculationCrisisState | None = None,
) -> CountyEconomicState:
    """Create a standard CountyEconomicState for testing."""
    return CountyEconomicState(
        fips=fips,
        year=year,
        capital_stock=1_000_000.0,
        throughput_position=0.9,
        supply_chain_depth=2.0,
        unemployment_rate=0.05,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=_make_class_distribution(fips, year),
        phi_hour=3.5,
        crisis_state=CrisisState.normal(),
        bifurcation_risk=BifurcationRiskMetric.neutral(),
        **({"circulation_state": circulation} if circulation is not None else {}),
    )


# =============================================================================
# T071: circulation_state field on CountyEconomicState
# =============================================================================


class TestCirculationStateField:
    """Verify circulation_state field on CountyEconomicState."""

    def test_field_exists_with_default(self) -> None:
        """CountyEconomicState has circulation_state with factory default."""
        state = _make_county_state()
        assert hasattr(state, "circulation_state")
        assert isinstance(state.circulation_state, CirculationCrisisState)

    def test_default_has_zeroed_circuit(self) -> None:
        """Default circulation_state has zero capital in all forms."""
        state = _make_county_state()
        circuit = state.circulation_state.circuit_state
        assert circuit.total_capital == pytest.approx(0.0)

    def test_default_has_no_assessment(self) -> None:
        """Default circulation_state has no crisis assessment."""
        state = _make_county_state()
        assert state.circulation_state.latest_assessment is None

    def test_frozen_model_still_valid(self) -> None:
        """CountyEconomicState remains frozen after adding circulation_state."""
        state = _make_county_state()
        with pytest.raises(Exception):  # noqa: B017
            state.circulation_state = CirculationCrisisState.default()  # type: ignore[misc]

    def test_existing_fields_unaffected(self) -> None:
        """Adding circulation_state does not break existing fields."""
        state = _make_county_state()
        assert state.fips == "26163"
        assert state.year == 2022
        assert state.capital_stock == pytest.approx(1_000_000.0)
        assert state.crisis_state.phase.value == "normal"
        assert state.bifurcation_risk.score == pytest.approx(0.0)

    def test_custom_circulation_state(self) -> None:
        """Can construct CountyEconomicState with custom circulation_state."""
        custom_circuit = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(30.0),
            productive_capital=Currency(50.0),
            commodity_capital=Currency(20.0),
            fixed_capital=Currency(35.0),
            circulating_capital=Currency(15.0),
        )
        custom_inventory = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(10.0),
            work_in_progress=Currency(5.0),
            finished_goods=Currency(15.0),
            days_inventory_raw=20.0,
            days_inventory_finished=40.0,
        )
        custom_depreciation = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(500.0),
            accumulated_depreciation=Currency(100.0),
            annual_depreciation_flow=Currency(50.0),
            replacement_expenditure=Currency(60.0),
        )
        custom = CirculationCrisisState(
            circuit_state=custom_circuit,
            inventory_state=custom_inventory,
            depreciation_fund=custom_depreciation,
            latest_assessment=None,
        )
        state = _make_county_state(circulation=custom)
        assert state.circulation_state.circuit_state.total_capital == pytest.approx(100.0)
        assert state.circulation_state.circuit_state.liquidity_ratio == pytest.approx(0.3)


# =============================================================================
# T072: Graph bridge serialization
# =============================================================================


class TestGraphBridgeSerialization:
    """Verify circulation attributes written to territory nodes."""

    def test_write_circulation_attributes(self) -> None:
        """write_tick_state_to_graph writes tick_liquidity_ratio etc."""

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph
        from babylon.economics.tick.types import (
            NationalTickParameters,
            SimulationTickState,
            SmoothedCoefficients,
        )

        g = BabylonGraph()
        g.add_node("26163", node_type="territory")
        graph = g

        national = NationalTickParameters(
            year=2022,
            tau=62.0,
            gamma_basket=0.68,
            gamma_basket_raw=0.68,
            gamma_III=0.33,
            gamma_III_raw=0.33,
            tau_effective=42.16,
            v_reproduction=12.0,
            estimated=True,
        )
        coefficients = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=True,
        )
        county = _make_county_state()
        tick_state = SimulationTickState(
            year=2022,
            national_params=national,
            county_states={"26163": county},
            coefficients=coefficients,
        )

        write_tick_state_to_graph(graph, tick_state)

        node = graph.get_node("26163")
        assert node is not None
        attrs = node.attributes

        # Verify circulation attributes exist
        assert "tick_liquidity_ratio" in attrs
        assert "tick_commodity_overhang" in attrs
        assert "tick_replacement_cycle" in attrs
        assert "tick_inventory_diagnosis" in attrs
        assert "tick_realization_crisis" in attrs
        assert "tick_turnover_crisis" in attrs
        assert "tick_reproduction_crisis" in attrs

    def test_write_circulation_values_correct(self) -> None:
        """Written circulation attribute values match the source state."""

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph
        from babylon.economics.tick.types import (
            NationalTickParameters,
            SimulationTickState,
            SmoothedCoefficients,
        )

        g = BabylonGraph()
        g.add_node("26163", node_type="territory")
        graph = g

        # Create county with custom circulation state
        custom_circuit = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(30.0),
            productive_capital=Currency(50.0),
            commodity_capital=Currency(20.0),
            fixed_capital=Currency(35.0),
            circulating_capital=Currency(15.0),
        )
        custom_inventory = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(10.0),
            work_in_progress=Currency(5.0),
            finished_goods=Currency(15.0),
            days_inventory_raw=20.0,
            days_inventory_finished=40.0,
        )
        custom_depreciation = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(500.0),
            accumulated_depreciation=Currency(100.0),
            annual_depreciation_flow=Currency(50.0),
            replacement_expenditure=Currency(60.0),
        )
        custom = CirculationCrisisState(
            circuit_state=custom_circuit,
            inventory_state=custom_inventory,
            depreciation_fund=custom_depreciation,
            latest_assessment=CirculationCrisisAssessment(
                fips_code="26163",
                year=2022,
                realization_crisis=True,
                turnover_crisis=False,
                reproduction_crisis=False,
                vulnerabilities=["REALIZATION_CRISIS"],
            ),
        )
        county = _make_county_state(circulation=custom)

        national = NationalTickParameters(
            year=2022,
            tau=62.0,
            gamma_basket=0.68,
            gamma_basket_raw=0.68,
            gamma_III=0.33,
            gamma_III_raw=0.33,
            tau_effective=42.16,
            v_reproduction=12.0,
            estimated=True,
        )
        coefficients = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=True,
        )
        tick_state = SimulationTickState(
            year=2022,
            national_params=national,
            county_states={"26163": county},
            coefficients=coefficients,
        )

        write_tick_state_to_graph(graph, tick_state)

        node = graph.get_node("26163")
        assert node is not None
        attrs = node.attributes

        assert attrs["tick_liquidity_ratio"] == pytest.approx(0.3)
        assert attrs["tick_commodity_overhang"] == pytest.approx(0.2)
        assert attrs["tick_replacement_cycle"] == ReplacementCyclePosition.EXPANSION.value
        assert attrs["tick_inventory_diagnosis"] == InventoryDiagnosis.NORMAL.value
        assert attrs["tick_realization_crisis"] is True
        assert attrs["tick_turnover_crisis"] is False
        assert attrs["tick_reproduction_crisis"] is False
