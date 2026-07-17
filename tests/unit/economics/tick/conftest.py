"""Fixtures for Simulation Tick Dynamics unit tests.

Feature: 017-simulation-tick-dynamics
Task: T009

Provides mock calculators and domain fixtures for testing the tick pipeline.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.domain.economics.dynamics.types import ClassDistribution, EconomicConditions
from babylon.domain.economics.gamma.types import GammaIII
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.throughput.types import ThroughputMetrics
from babylon.domain.economics.tick.types import (
    CountyEconomicState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)
from babylon.topology.graph import BabylonGraph

# Wayne County MI
WAYNE_FIPS: str = "26163"


# =============================================================================
# Mock Calculators
# =============================================================================


class MockMELTCalculator:
    """Mock MELTCalculator returning known tau values.

    Args:
        tau: Fixed tau value to return.
        force_sentinel: If True, always return NoDataSentinel regardless of year.
        accept_any_year: If True, skip year-range validation (return tau for any year).
    """

    def __init__(
        self,
        tau: float = 62.0,
        *,
        force_sentinel: bool = False,
        accept_any_year: bool = False,
    ) -> None:
        self._tau = tau
        self._force_sentinel = force_sentinel
        self._accept_any_year = accept_any_year

    def get_melt(self, year: int) -> float | NoDataSentinel:
        """Return fixed tau."""
        if self._force_sentinel:
            return NoDataSentinel(fips="USA", year=year, reason="Forced sentinel for testing")
        if not self._accept_any_year and (year < 2007 or year > 2040):
            return NoDataSentinel(fips="USA", year=year, reason=f"Year {year} out of range")
        return self._tau

    def validate_melt(self, tau: float) -> tuple[bool, str | None]:
        """Always valid."""
        return (True, None)

    @property
    def data_range(self) -> tuple[int, int]:
        """Return test range."""
        return (2007, 2040)


class MockBasketVisibilityCalculator:
    """Mock BasketVisibilityCalculator returning known gamma_basket."""

    def __init__(self, gamma_basket: float = 0.68, estimated: bool = True) -> None:
        self._gamma_basket = gamma_basket
        self._estimated = estimated

    def get_gamma_basket(
        self,
        year: int,
        alpha: float | None = None,
        gamma_import: float | None = None,
    ) -> tuple[float, bool]:
        """Return fixed gamma_basket."""
        return (self._gamma_basket, self._estimated)

    def validate_gamma_basket(self, gamma: float) -> tuple[bool, str | None]:
        """Always valid."""
        return (True, None)

    @property
    def mvp_gamma_basket(self) -> float:
        return self._gamma_basket

    @property
    def mvp_alpha(self) -> float:
        return 0.25

    @property
    def mvp_gamma_import(self) -> float:
        return 0.35


class MockGammaIIICalculator:
    """Mock GammaIIICalculator returning known GammaIII."""

    def __init__(self, gamma_iii: float = 0.33) -> None:
        self._gamma_iii = gamma_iii

    def compute(self, year: int) -> GammaIII | NoDataSentinel:
        """Return fixed GammaIII."""
        if year < 2007 or year > 2040:
            return NoDataSentinel(fips="USA", year=year, reason=f"Year {year} out of range")
        return GammaIII(
            year=year,
            paid_care_hours=10.0,
            unpaid_care_hours=20.0,
            gamma_iii=self._gamma_iii,
            fortunati_exploitation=(1.0 - self._gamma_iii) / self._gamma_iii,
        )

    def get_paid_care_hours(self, year: int) -> float | NoDataSentinel:
        return 10.0

    def get_unpaid_care_hours(self, year: int) -> float | NoDataSentinel:
        return 20.0


class MockCapitalStockCalculator:
    """Mock CapitalStockCalculator returning known K values."""

    def __init__(self, k_value: float = 1_000_000_000.0) -> None:
        self._k_value = k_value

    def get_K(self, fips: str, year: int) -> float | NoDataSentinel:  # noqa: N802
        """Return fixed K."""
        return self._k_value

    def get_metrics(self, fips: str, year: int) -> Any:
        """Return None (not needed for tick dynamics)."""
        return None


class MockThroughputCalculator:
    """Mock ThroughputCalculator returning known metrics."""

    def __init__(
        self,
        pi: float = 0.90,
        supply_chain_depth: float = 2.1,
    ) -> None:
        self._pi = pi
        self._supply_chain_depth = supply_chain_depth

    def compute_throughput_intensity(self, fips: str, year: int) -> float | NoDataSentinel:
        return 55.8

    def compute_throughput_position(self, fips: str, year: int) -> float | NoDataSentinel:
        return self._pi

    def compute_metrics(self, fips: str, year: int) -> ThroughputMetrics | NoDataSentinel:
        """Return fixed ThroughputMetrics."""
        return ThroughputMetrics(
            fips=fips,
            year=year,
            tau_through=55.8,
            pi=self._pi,
            supply_chain_depth=self._supply_chain_depth,
            is_estimated=False,
            data_quality="high",
        )


class MockClassTransitionEngine:
    """Mock ClassTransitionEngine returning known distributions."""

    def __init__(self, delta_la: float = -0.001) -> None:
        self._delta_la = delta_la

    def simulate_transitions(
        self,
        dist: ClassDistribution,
        conditions: EconomicConditions,
        crisis_phase: Any = None,
    ) -> ClassDistribution | NoDataSentinel:
        """Return distribution with small LA shift."""
        la = dist.labor_aristocracy_share + self._delta_la
        prol = dist.proletariat_share - self._delta_la
        return dist.with_updated_dynamics(la=la, prol=prol, lumpen=dist.lumpenproletariat_share)


class MockImperialRentCalculator:
    """Mock ImperialRentCalculator returning known phi_hour."""

    def __init__(self, phi_hour: float = 3.50) -> None:
        self._phi_hour = phi_hour

    def compute_phi_hour(self, wage: float, params: Any) -> float:
        """Return fixed phi_hour."""
        return self._phi_hour

    def compute_labor_commanded(self, wage: float, params: Any) -> float:
        return self._phi_hour + 1.0

    def is_labor_aristocracy(self, wage: float, params: Any) -> bool:
        return self._phi_hour > 0


class MockTensor:
    """Mock tensor with configurable profit_rate attribute."""

    def __init__(self, profit_rate: float | None = None) -> None:
        self.profit_rate = profit_rate


class MockTensorRegistry:
    """Mock TensorRegistry for profit rate lookup tests.

    Args:
        data: Dict mapping (fips, year) tuples to MockTensor objects.
    """

    def __init__(self, data: dict[tuple[str, int], Any] | None = None) -> None:
        self._data = data or {}

    def get(self, fips: str, year: int) -> Any:
        """Return tensor or NoDataSentinel for (fips, year)."""
        return self._data.get(
            (fips, year),
            NoDataSentinel(fips=fips, year=year, reason="no data"),
        )

    def available_years(self, fips: str) -> list[int]:
        """Return sorted list of years with data for this fips."""
        return sorted(y for f, y in self._data if f == fips)

    def all_fips(self) -> list[str]:
        """Return sorted list of all FIPS codes with data."""
        return sorted({f for f, _ in self._data})


class MockEventBus:
    """Captures published events for assertion in tests."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def publish(self, event: Any) -> None:
        """Capture event for later assertion."""
        self.events.append(event)

    def subscribe(self, *args: Any, **kwargs: Any) -> None:
        """No-op for compatibility."""


class CapturingTransitionEngine:
    """Captures transition inputs for assertion, returns dist unchanged."""

    def __init__(self) -> None:
        self.calls: list[tuple[ClassDistribution, EconomicConditions, Any]] = []

    def simulate_transitions(
        self,
        dist: ClassDistribution,
        conditions: EconomicConditions,
        crisis_phase: Any = None,
    ) -> ClassDistribution:
        """Capture call args, return input dist unchanged."""
        self.calls.append((dist, conditions, crisis_phase))
        return dist


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_melt_calculator() -> MockMELTCalculator:
    """Mock MELT calculator returning tau=62.0."""
    return MockMELTCalculator()


@pytest.fixture
def mock_basket_calculator() -> MockBasketVisibilityCalculator:
    """Mock basket visibility calculator returning gamma_basket=0.68."""
    return MockBasketVisibilityCalculator()


@pytest.fixture
def mock_gamma_calculator() -> MockGammaIIICalculator:
    """Mock gamma III calculator returning gamma_iii=0.33."""
    return MockGammaIIICalculator()


@pytest.fixture
def mock_capital_calculator() -> MockCapitalStockCalculator:
    """Mock capital stock calculator returning K=1e9."""
    return MockCapitalStockCalculator()


@pytest.fixture
def mock_throughput_calculator() -> MockThroughputCalculator:
    """Mock throughput calculator returning pi=0.90."""
    return MockThroughputCalculator()


@pytest.fixture
def mock_transition_engine() -> MockClassTransitionEngine:
    """Mock class transition engine with small LA shift."""
    return MockClassTransitionEngine()


@pytest.fixture
def mock_imperial_rent_calculator() -> MockImperialRentCalculator:
    """Mock imperial rent calculator returning phi_hour=3.50."""
    return MockImperialRentCalculator()


@pytest.fixture
def stable_distribution() -> ClassDistribution:
    """Standard US class distribution for testing (Wayne County, 2015)."""
    return ClassDistribution(
        fips=WAYNE_FIPS,
        year=2015,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )


@pytest.fixture
def sample_national_params() -> NationalTickParameters:
    """Sample national tick parameters for year 2015."""
    return NationalTickParameters(
        year=2015,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.33,
        gamma_III_raw=0.33,
        tau_effective=42.16,
        v_reproduction=12.0,
        estimated=True,
    )


@pytest.fixture
def sample_county_state(stable_distribution: ClassDistribution) -> CountyEconomicState:
    """Sample county economic state for Wayne County, 2015."""
    return CountyEconomicState(
        fips=WAYNE_FIPS,
        year=2015,
        capital_stock=1_000_000_000.0,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.053,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=stable_distribution,
        phi_hour=3.50,
    )


@pytest.fixture
def sample_coefficients() -> SmoothedCoefficients:
    """Sample smoothed coefficients."""
    return SmoothedCoefficients(
        alpha=0.3,
        gamma_basket=0.68,
        gamma_III=0.33,
        gamma_import=0.35,
        is_initialized=True,
    )


@pytest.fixture
def sample_tick_state(
    sample_national_params: NationalTickParameters,
    sample_county_state: CountyEconomicState,
    sample_coefficients: SmoothedCoefficients,
) -> SimulationTickState:
    """Sample simulation tick state for year 2015."""
    return SimulationTickState(
        year=2015,
        national_params=sample_national_params,
        county_states={WAYNE_FIPS: sample_county_state},
        coefficients=sample_coefficients,
    )


def build_territory_graph(
    fips_codes: list[str] | None = None,
) -> BabylonGraph:
    """Build a test graph with Territory nodes.

    Args:
        fips_codes: FIPS codes for territory nodes. Defaults to Wayne County.

    Returns:
        DiGraph with territory nodes having _node_type="territory".
    """
    if fips_codes is None:
        fips_codes = [WAYNE_FIPS]

    graph = BabylonGraph()
    for fips in fips_codes:
        graph.add_node(fips, _node_type="territory")
    return graph
