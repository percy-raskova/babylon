"""Tests for TickDynamicsSystem's Volume II circulation layer wiring.

Feature: 023-capital-volume-ii, U3 (vol2-circulation-engine program, 2026-07-21)

Covers ``_compute_circulation_layer`` / ``_compute_county_circulation_state``:
real reproduction-schema calculators fed by the tensor registry (replacing
the always-balanced hardcode), real cross-tick accumulation via
``update_depreciation_fund`` and ``advance_circuit`` (replacing the
re-initialize-from-scratch-every-tick stubs), and the honest-absence
fallback when no tensor department data exists for a county-year.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import CapitalVolumeIIDefines, GameDefines
from babylon.domain.economics.circulation.defaults import FALLBACK_PROFILE
from babylon.domain.economics.circulation.types import TurnoverProfile
from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.domain.economics.tick.types import CountyEconomicState
from babylon.engine.services import ServiceContainer
from tests.unit.economics.tick.conftest import MockTensorRegistry

FIPS = "26163"


class _FixedTurnoverSource:
    """Test double returning a fixed TurnoverProfile regardless of input.

    Decoupled from DefaultTurnoverProfileSource's NAICS-prefix resolution
    (the production call site passes a 2-digit STATE fips, not a NAICS
    code — a pre-existing, out-of-scope quirk) so these tests only depend
    on the turnover math itself.
    """

    def __init__(self, profile: TurnoverProfile) -> None:
        self._profile = profile

    def get_turnover_profile(self, naics_code: str) -> TurnoverProfile:
        return self._profile


def _make_county(
    fips: str = FIPS,
    year: int = 2015,
    capital_stock: float = 1000.0,
) -> CountyEconomicState:
    dist = ClassDistribution(
        fips=fips,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )
    return CountyEconomicState(
        fips=fips,
        year=year,
        capital_stock=capital_stock,
        throughput_position=0.9,
        supply_chain_depth=2.0,
        unemployment_rate=0.05,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=dist,
        phi_hour=3.5,
    )


def _make_services(**kwargs: Any) -> ServiceContainer:
    defaults: dict[str, Any] = {
        "turnover_profile_source": _FixedTurnoverSource(FALLBACK_PROFILE),
    }
    defaults.update(kwargs)
    return ServiceContainer.create(**defaults)


def _balanced_tensor(fips: str = FIPS, year: int = 2015) -> ValueTensor4x3:
    """Marx's own simple-reproduction numerical illustration (Capital Vol.

    II, Ch. 20 SS II), with a Dept III large enough to be sustainable:
    I = 4000c+1000v+1000s = 6000, II = 2000c+500v+500s = 3000 (split
    1000c+250v+250s per IIa/IIb), III = 1000c+1000v+1000s = 3000.
    I(v+s) = 2000 = IIc = 2000 -> BALANCED. dept_I share of (I+II) =
    6000/9000 = 0.6667 -> matches CapitalVolumeIIDefines.dept_i_share_required
    default exactly -> BALANCED disproportionality too. total_s = 2500.
    """
    return ValueTensor4x3(
        fips_code=fips,
        year=year,
        dept_I=DepartmentRow(c=4000.0, v=1000.0, s=1000.0),
        dept_IIa=DepartmentRow(c=1000.0, v=250.0, s=250.0),
        dept_IIb=DepartmentRow(c=1000.0, v=250.0, s=250.0),
        dept_III=DepartmentRow(c=1000.0, v=1000.0, s=1000.0),
        naics_granularity=1.0,
        excluded_wages=0.0,
    )


class TestReproductionRealCalculators:
    """U3: ReproductionBalance/ReproductionAnalysis/DisproportionalityCrisis
    come from the designated calculators fed real tensor department data,
    not a hardcoded always-balanced stub."""

    def test_uses_real_tensor_data_when_available(self) -> None:
        tensor = _balanced_tensor()
        registry = MockTensorRegistry({(FIPS, 2015): tensor})
        # Exact 6000/9000 (not the defines' 4-decimal-rounded 0.6667
        # default) so this Marx-schema fixture comes out perfectly
        # BALANCED rather than off by float-rounding noise.
        exact_share_defines = GameDefines(
            capital_vol2=CapitalVolumeIIDefines(dept_i_share_required=6000.0 / 9000.0)
        )
        services = _make_services(tensor_registry=registry, defines=exact_share_defines)
        system = TickDynamicsSystem()

        result = system._compute_circulation_layer({FIPS: _make_county()}, services, 2015)
        circ = result[FIPS].circulation_state

        # Not the old hardcoded stub literal.
        assert circ.latest_assessment is not None
        balance = system._compute_reproduction_state(FIPS, 2015, services)[0]
        assert balance.interpretation != "Default reproduction balance"
        assert balance.interpretation == "BALANCED"
        assert balance.condition_met is True
        assert balance.gap == pytest.approx(0.0)

        analysis = system._compute_reproduction_state(FIPS, 2015, services)[1]
        assert analysis.sustainability is True
        assert analysis.labor_power_demand == pytest.approx(1000.0 + 500.0 + 1000.0)
        assert analysis.reproduction_capacity == pytest.approx(3000.0)

        assert circ.disproportionality is not None
        assert circ.disproportionality.imbalance_direction == "BALANCED"
        assert circ.disproportionality.actual_i_share == pytest.approx(6000.0 / 9000.0)
        assert circ.disproportionality.year == 2015

        assert circ.latest_assessment.reproduction_crisis is False

    def test_honest_fallback_without_tensor_data(self) -> None:
        """No tensor department data -> cited exemption, never a lie."""
        services = _make_services(tensor_registry=MockTensorRegistry({}))
        system = TickDynamicsSystem()

        result = system._compute_circulation_layer({FIPS: _make_county()}, services, 2015)
        circ = result[FIPS].circulation_state

        assert circ.disproportionality is None
        balance, analysis, disprop = system._compute_reproduction_state(FIPS, 2015, services)
        assert balance.interpretation == "No tensor department data for this county-year"
        assert balance.condition_met is True
        assert analysis.sustainability is True
        assert disprop is None

    def test_no_tensor_registry_service_at_all(self) -> None:
        """tensor_registry service unwired (None) is likewise honest absence."""
        services = _make_services()
        system = TickDynamicsSystem()

        balance, _analysis, disprop = system._compute_reproduction_state(FIPS, 2015, services)
        assert balance.interpretation == "No tensor department data for this county-year"
        assert disprop is None


class TestDepreciationFundCrossTickAccumulation:
    """U3: update_depreciation_fund genuinely accumulates across ticks."""

    def test_second_tick_accumulates_onto_first(self) -> None:
        services = _make_services()
        system = TickDynamicsSystem()

        result1 = system._compute_circulation_layer({FIPS: _make_county(year=2015)}, services, 2015)
        fund1 = result1[FIPS].circulation_state.depreciation_fund
        # No depreciation_data_source wired -> county_depr=0.0, safe floor=1.0.
        assert fund1.accumulated_depreciation == pytest.approx(1.0)
        assert fund1.annual_depreciation_flow == pytest.approx(1.0)

        result2 = system._compute_circulation_layer({FIPS: _make_county(year=2016)}, services, 2016)
        fund2 = result2[FIPS].circulation_state.depreciation_fund

        # update_depreciation_fund: new_accumulated = previous + annual.
        assert fund2.accumulated_depreciation == pytest.approx(2.0)
        assert fund2.year == 2016


class TestCircuitAdvancesAcrossTicks:
    """U3: advance_circuit is actually called on tick 2+, not
    re-initialize_circuit_state from capital_stock every tick."""

    def test_second_tick_advances_first_ticks_circuit(self) -> None:
        tensor = _balanced_tensor()  # total_s = 1000+250+250+1000 = 2500
        registry = MockTensorRegistry({(FIPS, 2015): tensor})
        services = _make_services(tensor_registry=registry)
        system = TickDynamicsSystem()

        result1 = system._compute_circulation_layer(
            {FIPS: _make_county(year=2015, capital_stock=1000.0)}, services, 2015
        )
        circuit1 = result1[FIPS].circulation_state.circuit_state
        # initialize_circuit_state proportions for FALLBACK_PROFILE
        # (purchase=10, production=25, sale=15, turnover_time=50):
        assert circuit1.money_capital == pytest.approx(200.0)
        assert circuit1.productive_capital == pytest.approx(500.0)
        assert circuit1.commodity_capital == pytest.approx(300.0)
        assert circuit1.total_capital == pytest.approx(1000.0)

        # Second tick: capital_stock changes, but the circuit's evolution
        # must come from advance_circuit(circuit1, ...), not a fresh
        # initialize_circuit_state(new capital_stock).
        result2 = system._compute_circulation_layer(
            {FIPS: _make_county(year=2016, capital_stock=999_999.0)}, services, 2016
        )
        circuit2 = result2[FIPS].circulation_state.circuit_state

        # elapsed_days (364, default TimescaleDefines) exceeds every
        # FALLBACK_PROFILE phase duration (10/25/15 days), so every phase
        # fraction clips to 1.0: each form's balance fully rotates to the
        # next, and the full surplus is created.
        assert circuit2.money_capital == pytest.approx(300.0)  # old commodity
        assert circuit2.productive_capital == pytest.approx(200.0)  # old money
        assert circuit2.commodity_capital == pytest.approx(
            500.0 + 2500.0
        )  # old productive + surplus
        assert circuit2.total_capital == pytest.approx(1000.0 + 2500.0)
        assert circuit2.year == 2016

        # Proof this is NOT a fresh initialize_circuit_state(999_999.0, ...):
        assert circuit2.total_capital != pytest.approx(999_999.0)
