"""Tests for Spec 057 / US1 — End-to-end imperial-rent pipeline integration.

Acceptance criteria from
``specs/057-leontief-rent-integration/contracts/imperial_rent_pipeline.md``.

These tests use synthetic in-memory fixtures (Mock-everything pattern) to
verify the orchestration logic in :mod:`babylon.domain.economics.tick.system.imperial_rent`
without hitting the 8.8GB reference SQLite. The Wayne County baseline
integration test (SC-002) lives in a separate file (test_wayne_baseline.py)
which DOES hit real data; AC1 + AC2 in this file use mock sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.types import (
    DecomposedFlow,
    ImportShareVector,
    InterIndustryFlow,
    PeripheryLaborCoefficients,
    ProductionChainRentResult,
)
from babylon.domain.economics.tick.system.imperial_rent import compute
from babylon.domain.economics.tick.types import CountyEconomicState
from babylon.kernel.event_bus import EventBus

# =============================================================================
# Mock data + fixtures
# =============================================================================


def _county(fips: str, phi_hour: float = 0.0) -> CountyEconomicState:
    """Build a minimal CountyEconomicState fixture."""
    from babylon.domain.economics.dynamics.types import ClassDistribution
    from babylon.domain.economics.tick.types import CountyEconomicState

    return CountyEconomicState(
        fips=fips,
        year=2015,
        capital_stock=1e9,
        throughput_position=0.9,
        supply_chain_depth=2.1,
        unemployment_rate=0.05,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=ClassDistribution(
            fips=fips,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.04,
            labor_aristocracy_share=0.10,
            proletariat_share=0.80,
            lumpenproletariat_share=0.05,
        ),
        phi_hour=phi_hour,
    )


@pytest.fixture
def county_states() -> dict[str, CountyEconomicState]:
    return {
        "11111": _county("11111", phi_hour=0.0),
        "22222": _county("22222", phi_hour=0.0),
    }


@pytest.fixture
def national_params() -> Any:
    from babylon.domain.economics.tick.types import NationalTickParameters

    return NationalTickParameters(
        year=2015,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.55,
        gamma_III_raw=0.55,
        tau_effective=42.16,
        v_reproduction=15.0,
        estimated=True,
    )


# =============================================================================
# Mock services
# =============================================================================


@dataclass
class MockPeripheryLaborCoefficientsSource:
    """Fakes the new PeripheryLaborCoefficientsSource Protocol."""

    return_value: PeripheryLaborCoefficients | NoDataSentinel
    industries: list[str] = field(default_factory=list)

    def get_coefficients(self, year: int) -> PeripheryLaborCoefficients | NoDataSentinel:
        return self.return_value


@dataclass
class MockFinalDemandSource:
    return_value: np.ndarray | None = None
    raise_value: ValueError | None = None

    def get_final_demand(self, year: int) -> np.ndarray:
        if self.raise_value is not None:
            raise self.raise_value
        if self.return_value is None:
            raise ValueError(f"No final-demand data for year {year}")
        return self.return_value


@dataclass
class MockFlowSource:
    return_value: InterIndustryFlow | NoDataSentinel

    def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel:
        return self.return_value


@dataclass
class MockImportSharesSource:
    return_value: ImportShareVector

    def get_import_shares(self, year: int) -> ImportShareVector:
        return self.return_value


@dataclass
class MockDecomposer:
    return_value: DecomposedFlow

    def decompose(self, flow: InterIndustryFlow, shares: ImportShareVector) -> DecomposedFlow:
        return self.return_value


@dataclass
class MockProductionChainCalculator:
    return_value: ProductionChainRentResult

    def calculate(self, **kwargs: Any) -> ProductionChainRentResult:
        return self.return_value


@dataclass
class MockProductionChainBundle:
    """Bundle of (flow_source, import_shares_source, decomposer, calculator)
    matching the attribute access pattern in imperial_rent.compute."""

    flow_source: Any
    import_shares_source: Any
    decomposer: Any
    calculator: Any


@dataclass
class MockAllocator:
    return_value: dict[str, float] | NoDataSentinel

    def allocate(
        self,
        phi_vector: np.ndarray,
        bea_industries: list[str],
        year: int,
    ) -> dict[str, float] | NoDataSentinel:
        return self.return_value


def _build_services(
    *,
    periphery_labor_source: Any = None,
    final_demand_source: Any = None,
    industry_county_allocator: Any = None,
    production_chain_calculator: Any = None,
    bea_industries: list[str] | None = None,
) -> Any:
    """Build a minimal ServiceContainer-like with just what compute() reads."""
    from types import SimpleNamespace

    return SimpleNamespace(
        periphery_labor_source=periphery_labor_source,
        final_demand_source=final_demand_source,
        industry_county_allocator=industry_county_allocator,
        production_chain_calculator=production_chain_calculator,
        bea_industries=bea_industries,
        event_bus=EventBus(),
    )


def _basic_industries() -> list[str]:
    return ["B1", "B2"]


def _wired_services(
    *,
    bea_industries: list[str] | None = None,
    periphery_ratios: np.ndarray | None = None,
    final_demand_vector: np.ndarray | None = None,
    allocation: dict[str, float] | None = None,
) -> Any:
    """Build a fully-wired services namespace with sensible defaults."""
    industries = bea_industries or _basic_industries()
    n = len(industries)
    pratios = (
        periphery_ratios if periphery_ratios is not None else np.full(n, 5.0, dtype=np.float64)
    )
    fd = (
        final_demand_vector
        if final_demand_vector is not None
        else np.full(n, 1000.0, dtype=np.float64)
    )
    alloc = allocation if allocation is not None else {"11111": 0.5, "22222": 0.3}

    from babylon.domain.economics.tensor_hierarchy.types import IOTableType

    flow = InterIndustryFlow(
        year=2015,
        table_type=IOTableType.USE,
        industries=industries,
        coefficients=np.zeros((n, n), dtype=np.float64),
    )
    shares = ImportShareVector(
        year=2015, industries=industries, shares=np.zeros(n, dtype=np.float64)
    )
    decomposed = DecomposedFlow(
        year=2015,
        industries=industries,
        A_d=np.zeros((n, n), dtype=np.float64),
        A_m=np.zeros((n, n), dtype=np.float64),
        L_d=np.eye(n, dtype=np.float64),
    )
    rent_result = ProductionChainRentResult(
        year=2015,
        industries=industries,
        phi_vector=np.full(n, 100.0, dtype=np.float64),
        total_phi=100.0 * n,
        dept_phi={},
    )
    bundle = MockProductionChainBundle(
        flow_source=MockFlowSource(return_value=flow),
        import_shares_source=MockImportSharesSource(return_value=shares),
        decomposer=MockDecomposer(return_value=decomposed),
        calculator=MockProductionChainCalculator(return_value=rent_result),
    )
    return _build_services(
        periphery_labor_source=MockPeripheryLaborCoefficientsSource(
            return_value=PeripheryLaborCoefficients(
                year=2015, industries=industries, wage_ratios=pratios
            ),
            industries=industries,
        ),
        final_demand_source=MockFinalDemandSource(return_value=fd),
        industry_county_allocator=MockAllocator(return_value=alloc),
        production_chain_calculator=bundle,
        bea_industries=industries,
    )


# =============================================================================
# AC6 (FR-001) — Facade returns dict[str, CountyEconomicState]
# =============================================================================


@pytest.mark.integration
def test_facade_returns_dict_str_county_state(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    services = _wired_services()
    result = compute(county_states, national_params, services)
    assert isinstance(result, dict)
    for fips, state in result.items():
        assert isinstance(fips, str)
        assert isinstance(state, CountyEconomicState)


# =============================================================================
# Pipeline produces non-zero phi_hour for counties present in allocation
# =============================================================================


@pytest.mark.integration
def test_pipeline_writes_nonzero_phi_hour(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    services = _wired_services(allocation={"11111": 0.7, "22222": 0.3})
    result = compute(county_states, national_params, services)
    assert result["11111"].phi_hour == 0.7
    assert result["22222"].phi_hour == 0.3


# =============================================================================
# AC4 (FR-006) — Industry-list misalignment raises ValueError
# =============================================================================


@pytest.mark.integration
def test_industry_misalignment_raises(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    industries = ["B1", "B2"]
    # Build periphery source with a DIFFERENT industry list
    services = _wired_services(bea_industries=industries)
    bad_periphery_industries = ["B1", "B2", "B3"]  # Length mismatch
    services.periphery_labor_source = MockPeripheryLaborCoefficientsSource(
        return_value=PeripheryLaborCoefficients(
            year=2015,
            industries=bad_periphery_industries,
            wage_ratios=np.array([5.0, 5.0, 5.0]),
        ),
        industries=bad_periphery_industries,
    )
    with pytest.raises(ValueError, match=r"BEA industry list mismatch.*periphery"):
        compute(county_states, national_params, services)


# =============================================================================
# AC5 (FR-007) — Sentinel propagation: periphery source returns NoDataSentinel
# =============================================================================


@pytest.mark.integration
def test_sentinel_periphery_wage_skips_step(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    services = _wired_services()
    services.periphery_labor_source = MockPeripheryLaborCoefficientsSource(
        return_value=NoDataSentinel(fips="", year=2015, reason="test"),
    )
    # Set non-zero phi_hour on input — must be preserved (not silently zeroed).
    county_states["11111"] = _county("11111", phi_hour=0.5)
    result = compute(county_states, national_params, services)
    # phi_hour preserved
    assert result["11111"].phi_hour == 0.5
    # Exactly one wildcard QcewCarryForwardEvent fired
    history = services.event_bus.get_history()
    cf_events = [e for e in history if e.type == "calibration_warning.qcew_carry_forward"]
    assert len(cf_events) >= 1
    wildcards = [e for e in cf_events if e.payload["county_fips"] == "*"]
    assert len(wildcards) >= 1


# =============================================================================
# AC5 — Final demand source ValueError → graceful degradation
# =============================================================================


@pytest.mark.integration
def test_sentinel_final_demand_skips_step(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    services = _wired_services()
    services.final_demand_source = MockFinalDemandSource(
        raise_value=ValueError("No final-demand data for year 2015")
    )
    county_states["11111"] = _county("11111", phi_hour=0.5)
    result = compute(county_states, national_params, services)
    assert result["11111"].phi_hour == 0.5
    history = services.event_bus.get_history()
    wildcards = [
        e
        for e in history
        if e.type == "calibration_warning.qcew_carry_forward" and e.payload["county_fips"] == "*"
    ]
    assert len(wildcards) >= 1


# =============================================================================
# Pipeline-not-wired graceful degradation
# =============================================================================


@pytest.mark.integration
def test_pipeline_not_wired_falls_back_to_stub(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    """When ServiceContainer has None for any of the 4 Spec 057 fields,
    compute() returns county_states unchanged + emits a sentinel event."""
    services = _build_services(
        periphery_labor_source=None,
        final_demand_source=None,
        industry_county_allocator=None,
        production_chain_calculator=None,
        bea_industries=None,
    )
    county_states["11111"] = _county("11111", phi_hour=0.5)
    result = compute(county_states, national_params, services)
    # County A's phi_hour preserved (graceful degradation, not silent zero)
    assert result["11111"].phi_hour == 0.5
    history = services.event_bus.get_history()
    cf_events = [e for e in history if e.type == "calibration_warning.qcew_carry_forward"]
    assert len(cf_events) == 1
    assert cf_events[0].payload["county_fips"] == "*"


# =============================================================================
# Allocator returning NoDataSentinel → graceful degradation
# =============================================================================


@pytest.mark.integration
def test_allocator_no_data_sentinel_falls_back(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    services = _wired_services()
    services.industry_county_allocator = MockAllocator(
        return_value=NoDataSentinel(fips="", year=2015, reason="empty window")
    )
    county_states["11111"] = _county("11111", phi_hour=0.42)
    result = compute(county_states, national_params, services)
    assert result["11111"].phi_hour == 0.42


# =============================================================================
# Counties absent from allocation pass through unchanged (no silent zero)
# =============================================================================


@pytest.mark.integration
def test_county_absent_from_allocation_preserved(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    """If allocator returns {only_one_county: ...}, the others keep prior phi_hour."""
    services = _wired_services(allocation={"11111": 0.7})  # 22222 absent
    county_states["22222"] = _county("22222", phi_hour=0.99)
    result = compute(county_states, national_params, services)
    assert result["11111"].phi_hour == 0.7  # updated
    assert result["22222"].phi_hour == 0.99  # preserved


# =============================================================================
# AC2 — Reproducibility (same input → same output, same event order)
# =============================================================================


@pytest.mark.integration
def test_reproducibility_same_inputs(
    county_states: dict[str, CountyEconomicState], national_params: Any
) -> None:
    s1 = _wired_services()
    s2 = _wired_services()
    r1 = compute(county_states, national_params, s1)
    r2 = compute(county_states, national_params, s2)
    # Same phi_hour values
    for fips in r1:
        assert r1[fips].phi_hour == r2[fips].phi_hour
    # Same event-bus history shape
    h1 = [(e.type, e.payload) for e in s1.event_bus.get_history()]
    h2 = [(e.type, e.payload) for e in s2.event_bus.get_history()]
    assert h1 == h2
