"""Fixtures for Class Dynamics Engine unit tests.

Feature: 016-class-dynamics-engine
Task: T012
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.dynamics.data_sources import (
    CrisisAmplifier,
    DispossessionDataSource,
    SavingsRateSource,
)
from babylon.domain.economics.dynamics.types import (
    ClassDistribution,
    EconomicConditions,
    TransitionRates,
)
from babylon.domain.economics.melt.types import ClassPosition

# =============================================================================
# Mock Data Sources
# =============================================================================


class MockDispossessionDataSource:
    """Mock dispossession data source for testing.

    Returns configurable rates by year. Defaults mimic stable conditions.
    """

    DEFAULT_FORECLOSURE: dict[int, float] = {
        2010: 0.046,
        2015: 0.006,
        2018: 0.005,
    }
    DEFAULT_BANKRUPTCY: dict[int, float] = {
        2010: 0.013,
        2015: 0.006,
        2018: 0.006,
    }
    DEFAULT_EVICTION: dict[int, float] = {
        2010: 0.070,
        2015: 0.063,
        2018: 0.062,
    }

    def __init__(
        self,
        foreclosure: dict[int, float] | None = None,
        bankruptcy: dict[int, float] | None = None,
        eviction: dict[int, float] | None = None,
    ) -> None:
        """Initialize with optional rate overrides.

        Args:
            foreclosure: Year -> foreclosure rate. None for defaults.
            bankruptcy: Year -> bankruptcy rate. None for defaults.
            eviction: Year -> eviction rate. None for defaults.
        """
        self._foreclosure = (
            foreclosure if foreclosure is not None else self.DEFAULT_FORECLOSURE.copy()
        )
        self._bankruptcy = bankruptcy if bankruptcy is not None else self.DEFAULT_BANKRUPTCY.copy()
        self._eviction = eviction if eviction is not None else self.DEFAULT_EVICTION.copy()

    def get_foreclosure_rate(self, fips: str, year: int) -> float | None:
        """Get foreclosure rate for a year."""
        return self._foreclosure.get(year)

    def get_bankruptcy_rate(self, fips: str, year: int) -> float | None:
        """Get bankruptcy rate for a year."""
        return self._bankruptcy.get(year)

    def get_eviction_rate(self, fips: str, year: int) -> float | None:
        """Get eviction rate for a year."""
        return self._eviction.get(year)


class MockSavingsRateSource:
    """Mock savings rate source for testing.

    Returns fixed rates per class position.
    """

    DEFAULT_RATES: dict[ClassPosition, float] = {
        ClassPosition.BOURGEOISIE: 0.38,
        ClassPosition.PETIT_BOURGEOISIE: 0.20,
        ClassPosition.LABOR_ARISTOCRACY: 0.12,
        ClassPosition.PROLETARIAT: 0.03,
        ClassPosition.LUMPENPROLETARIAT: 0.00,
    }

    def __init__(
        self,
        rates: dict[ClassPosition, float] | None = None,
        phi_adjustment: float = 0.0,
    ) -> None:
        """Initialize with optional rate overrides.

        Args:
            rates: ClassPosition -> savings rate. None for defaults.
            phi_adjustment: Fixed phi adjustment to return.
        """
        self._rates = rates if rates is not None else self.DEFAULT_RATES.copy()
        self._phi_adjustment = phi_adjustment

    def get_savings_rate(self, class_position: ClassPosition) -> float:
        """Get savings rate for a class position."""
        return self._rates[class_position]

    def get_phi_adjustment(self, phi_hour: float, wage: float) -> float:
        """Get phi adjustment (returns fixed value for testing)."""
        return self._phi_adjustment


class MockCrisisAmplifier:
    """Mock crisis amplifier for testing (passthrough by default).

    Returns rates unchanged unless crisis=True and amplify_factor is set.
    """

    def __init__(
        self,
        crisis_amplifier: float = 1.0,
        recovery_dampener: float = 1.0,
    ) -> None:
        """Initialize with optional amplification factors.

        Args:
            crisis_amplifier: Multiplier for downward rates during crisis.
            recovery_dampener: Multiplier for upward rates during crisis.
        """
        self._crisis_amplifier = crisis_amplifier
        self._recovery_dampener = recovery_dampener

    def amplify(
        self,
        rates: TransitionRates,
        crisis: bool,
    ) -> TransitionRates:
        """Amplify rates (passthrough when factors are 1.0)."""
        if not crisis:
            return rates
        return TransitionRates(
            fips=rates.fips,
            year=rates.year,
            dispossession=min(rates.dispossession * self._crisis_amplifier, 1.0),
            accumulation=min(rates.accumulation * self._recovery_dampener, 1.0),
            precaritization=min(rates.precaritization * self._crisis_amplifier, 1.0),
            stabilization=min(rates.stabilization * self._recovery_dampener, 1.0),
        )


# =============================================================================
# Protocol Compliance Verification
# =============================================================================


def _check_protocol_compliance() -> None:
    """Verify mock classes satisfy their respective protocols."""
    _d: DispossessionDataSource = MockDispossessionDataSource()
    _s: SavingsRateSource = MockSavingsRateSource()
    _c: CrisisAmplifier = MockCrisisAmplifier()


_check_protocol_compliance()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def stable_distribution() -> ClassDistribution:
    """Standard US class distribution for testing."""
    return ClassDistribution(
        fips="26163",
        year=2015,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )


@pytest.fixture
def stable_conditions() -> EconomicConditions:
    """Stable (non-crisis) economic conditions for testing."""
    return EconomicConditions(
        fips="26163",
        year=2015,
        unemployment_rate=0.05,
        median_wage=45000.0,
        melt=62.0,
        phi_hour=3.50,
        foreclosure_rate=0.006,
        bankruptcy_rate=0.006,
        eviction_rate=0.063,
        crisis=False,
    )


@pytest.fixture
def crisis_conditions() -> EconomicConditions:
    """Crisis economic conditions (2010-like) for testing."""
    return EconomicConditions(
        fips="26163",
        year=2010,
        unemployment_rate=0.15,
        median_wage=35000.0,
        melt=58.0,
        phi_hour=3.00,
        foreclosure_rate=0.046,
        bankruptcy_rate=0.013,
        eviction_rate=0.070,
        crisis=True,
    )


@pytest.fixture
def mock_dispossession_source() -> MockDispossessionDataSource:
    """Mock dispossession data source with defaults."""
    return MockDispossessionDataSource()


@pytest.fixture
def mock_savings_source() -> MockSavingsRateSource:
    """Mock savings rate source with defaults."""
    return MockSavingsRateSource()


@pytest.fixture
def mock_crisis_amplifier() -> MockCrisisAmplifier:
    """Passthrough crisis amplifier (no amplification)."""
    return MockCrisisAmplifier()


# =============================================================================
# Historical Data Fixtures (T027)
# =============================================================================

# Plausible national economic conditions 2007-2020.
# Unemployment: BLS LAUS annual averages.
# Wages: BLS OES national median approximations.
# MELT/phi_hour: Plausible values from Feature 013 calibration range.
# Dispossession rates: Match hardcoded_data.py source tables.
# Crisis flags: Great Recession 2008-2012 per SC-002 definition.
_HISTORICAL_CONDITIONS: dict[int, dict[str, float | bool]] = {
    2007: {
        "unemployment_rate": 0.046,
        "median_wage": 40000.0,
        "melt": 60.0,
        "phi_hour": 3.30,
        "foreclosure_rate": 0.018,
        "bankruptcy_rate": 0.007,
        "eviction_rate": 0.064,
        "crisis": False,
    },
    2008: {
        "unemployment_rate": 0.058,
        "median_wage": 39000.0,
        "melt": 59.0,
        "phi_hour": 3.20,
        "foreclosure_rate": 0.023,
        "bankruptcy_rate": 0.008,
        "eviction_rate": 0.065,
        "crisis": True,
    },
    2009: {
        "unemployment_rate": 0.093,
        "median_wage": 37000.0,
        "melt": 58.0,
        "phi_hour": 3.00,
        "foreclosure_rate": 0.028,
        "bankruptcy_rate": 0.010,
        "eviction_rate": 0.064,
        "crisis": True,
    },
    2010: {
        "unemployment_rate": 0.096,
        "median_wage": 35000.0,
        "melt": 58.0,
        "phi_hour": 3.00,
        "foreclosure_rate": 0.046,
        "bankruptcy_rate": 0.013,
        "eviction_rate": 0.070,
        "crisis": True,
    },
    2011: {
        "unemployment_rate": 0.089,
        "median_wage": 36000.0,
        "melt": 59.0,
        "phi_hour": 3.10,
        "foreclosure_rate": 0.035,
        "bankruptcy_rate": 0.011,
        "eviction_rate": 0.072,
        "crisis": True,
    },
    2012: {
        "unemployment_rate": 0.081,
        "median_wage": 37000.0,
        "melt": 60.0,
        "phi_hour": 3.20,
        "foreclosure_rate": 0.025,
        "bankruptcy_rate": 0.009,
        "eviction_rate": 0.070,
        "crisis": True,
    },
    2013: {
        "unemployment_rate": 0.074,
        "median_wage": 39000.0,
        "melt": 61.0,
        "phi_hour": 3.30,
        "foreclosure_rate": 0.015,
        "bankruptcy_rate": 0.008,
        "eviction_rate": 0.067,
        "crisis": False,
    },
    2014: {
        "unemployment_rate": 0.062,
        "median_wage": 41000.0,
        "melt": 62.0,
        "phi_hour": 3.40,
        "foreclosure_rate": 0.010,
        "bankruptcy_rate": 0.007,
        "eviction_rate": 0.066,
        "crisis": False,
    },
    2015: {
        "unemployment_rate": 0.053,
        "median_wage": 43000.0,
        "melt": 62.0,
        "phi_hour": 3.50,
        "foreclosure_rate": 0.006,
        "bankruptcy_rate": 0.006,
        "eviction_rate": 0.063,
        "crisis": False,
    },
    2016: {
        "unemployment_rate": 0.049,
        "median_wage": 44000.0,
        "melt": 63.0,
        "phi_hour": 3.60,
        "foreclosure_rate": 0.005,
        "bankruptcy_rate": 0.006,
        "eviction_rate": 0.061,
        "crisis": False,
    },
    2017: {
        "unemployment_rate": 0.044,
        "median_wage": 45000.0,
        "melt": 63.0,
        "phi_hour": 3.60,
        "foreclosure_rate": 0.005,
        "bankruptcy_rate": 0.006,
        "eviction_rate": 0.062,
        "crisis": False,
    },
    2018: {
        "unemployment_rate": 0.039,
        "median_wage": 46000.0,
        "melt": 64.0,
        "phi_hour": 3.70,
        "foreclosure_rate": 0.005,
        "bankruptcy_rate": 0.006,
        "eviction_rate": 0.062,
        "crisis": False,
    },
    2019: {
        "unemployment_rate": 0.037,
        "median_wage": 48000.0,
        "melt": 65.0,
        "phi_hour": 3.80,
        "foreclosure_rate": 0.004,
        "bankruptcy_rate": 0.006,
        "eviction_rate": 0.060,
        "crisis": False,
    },
}


@pytest.fixture
def historical_conditions_2007_2020() -> list[EconomicConditions]:
    """Historical economic conditions 2007-2019 for multi-period validation.

    Returns EconomicConditions for each year from 2007 through 2019,
    using plausible national values derived from BLS/BEA sources.
    """
    conditions: list[EconomicConditions] = []
    for year in range(2007, 2020):
        data = _HISTORICAL_CONDITIONS[year]
        conditions.append(
            EconomicConditions(
                fips="26163",
                year=year,
                unemployment_rate=float(data["unemployment_rate"]),
                median_wage=float(data["median_wage"]),
                melt=float(data["melt"]),
                phi_hour=float(data["phi_hour"]),
                foreclosure_rate=float(data["foreclosure_rate"]),
                bankruptcy_rate=float(data["bankruptcy_rate"]),
                eviction_rate=float(data["eviction_rate"]),
                crisis=bool(data["crisis"]),
            )
        )
    return conditions
