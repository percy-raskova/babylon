"""Fixtures for credit dynamics unit tests."""

from __future__ import annotations

import pytest


class MockInterestRateSource:
    """Mock FRED interest rate source."""

    DEFAULT_RATES: dict[int, tuple[float, float, float]] = {
        # year: (fed_funds, treasury_10y, baa_spread)
        2020: (0.0036, 0.0089, 0.0234),  # Near-zero rates, moderate spread
        2022: (0.0133, 0.0295, 0.0193),  # Rising rates
        2007: (0.0502, 0.0463, 0.0155),  # Pre-crisis
        2008: (0.0193, 0.0366, 0.0349),  # Crisis: low funds, wide spread
    }

    def __init__(self, data: dict[int, tuple[float, float, float]] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_RATES.copy()
        else:
            self._data = data

    def get_federal_funds_rate(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[0] if entry else None

    def get_treasury_10y(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[1] if entry else None

    def get_baa_spread(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[2] if entry else None


class MockCreditAggregateSource:
    """Mock FRED credit aggregate source."""

    DEFAULT_AGGREGATES: dict[int, tuple[float, float, float]] = {
        # year: (total_credit, govt_debt, equity_market_cap)
        2020: (83_000_000_000_000.0, 27_000_000_000_000.0, 36_000_000_000_000.0),
        2022: (92_000_000_000_000.0, 31_000_000_000_000.0, 33_000_000_000_000.0),
        2007: (51_000_000_000_000.0, 9_000_000_000_000.0, 15_000_000_000_000.0),
        2008: (53_000_000_000_000.0, 10_000_000_000_000.0, 9_000_000_000_000.0),
    }

    def __init__(self, data: dict[int, tuple[float, float, float]] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_AGGREGATES.copy()
        else:
            self._data = data

    def get_total_credit(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[0] if entry else None

    def get_government_debt(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[1] if entry else None

    def get_equity_market_cap(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[2] if entry else None


class MockZ1Source:
    """Mock Fed Z.1 Financial Accounts source."""

    DEFAULT_Z1: dict[int, tuple[float, float, float]] = {
        # year: (corporate_debt, household_debt, derivatives_notional)
        2020: (11_000_000_000_000.0, 16_000_000_000_000.0, 600_000_000_000_000.0),
        2022: (12_500_000_000_000.0, 18_000_000_000_000.0, 630_000_000_000_000.0),
        2007: (7_000_000_000_000.0, 14_000_000_000_000.0, 595_000_000_000_000.0),
        2008: (7_500_000_000_000.0, 13_800_000_000_000.0, 592_000_000_000_000.0),
    }

    def __init__(self, data: dict[int, tuple[float, float, float]] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_Z1.copy()
        else:
            self._data = data

    def get_corporate_debt(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[0] if entry else None

    def get_household_debt(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[1] if entry else None

    def get_derivatives_notional(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[2] if entry else None


@pytest.fixture
def mock_interest_rate_source() -> MockInterestRateSource:
    return MockInterestRateSource()


@pytest.fixture
def mock_credit_aggregate_source() -> MockCreditAggregateSource:
    return MockCreditAggregateSource()


@pytest.fixture
def mock_z1_source() -> MockZ1Source:
    return MockZ1Source()


def _check_protocol_compliance() -> None:
    from babylon.economics.credit.data_sources import (
        CreditAggregateSource,
        InterestRateSource,
        Z1FinancialAccountsSource,
    )

    _i: InterestRateSource = MockInterestRateSource()
    _c: CreditAggregateSource = MockCreditAggregateSource()
    _z: Z1FinancialAccountsSource = MockZ1Source()


_check_protocol_compliance()
