"""Fixtures for surplus value distribution unit tests."""

from __future__ import annotations

import pytest


class MockRentalIncomeSource:
    """Mock BEA rental income source with configurable county data."""

    DEFAULT_RENTAL_INCOME: dict[tuple[str, int], float] = {
        ("26163", 2020): 2_500_000_000.0,  # Wayne County ~$2.5B
        ("26125", 2020): 4_200_000_000.0,  # Oakland County ~$4.2B
        ("26163", 2022): 2_800_000_000.0,
        ("26125", 2022): 4_600_000_000.0,
    }

    def __init__(self, data: dict[tuple[str, int], float] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_RENTAL_INCOME.copy()
        else:
            self._data = data

    def get_rental_income(self, fips: str, year: int) -> float | None:
        return self._data.get((fips, year))


class MockTaxOnSurplusSource:
    """Mock IRS/BEA corporate tax source with configurable county data."""

    DEFAULT_TAX: dict[tuple[str, int], float] = {
        ("26163", 2020): 1_200_000_000.0,  # Wayne County ~$1.2B
        ("26125", 2020): 2_100_000_000.0,  # Oakland County ~$2.1B
        ("26163", 2022): 1_400_000_000.0,
        ("26125", 2022): 2_300_000_000.0,
    }

    def __init__(self, data: dict[tuple[str, int], float] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_TAX.copy()
        else:
            self._data = data

    def get_corporate_tax(self, fips: str, year: int) -> float | None:
        return self._data.get((fips, year))


class MockInterestIncomeSource:
    """Mock FRED/BEA net interest source with configurable national data."""

    DEFAULT_INTEREST: dict[int, float] = {
        2020: 2_800_000_000_000.0,  # ~$2.8T national net interest
        2022: 3_200_000_000_000.0,  # ~$3.2T
    }

    def __init__(self, data: dict[int, float] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_INTEREST.copy()
        else:
            self._data = data

    def get_national_net_interest(self, year: int) -> float | None:
        return self._data.get(year)


@pytest.fixture
def mock_rental_source() -> MockRentalIncomeSource:
    return MockRentalIncomeSource()


@pytest.fixture
def mock_tax_source() -> MockTaxOnSurplusSource:
    return MockTaxOnSurplusSource()


@pytest.fixture
def mock_interest_source() -> MockInterestIncomeSource:
    return MockInterestIncomeSource()


def _check_protocol_compliance() -> None:
    from babylon.domain.economics.distribution.data_sources import (
        InterestIncomeSource,
        RentalIncomeSource,
        TaxOnSurplusSource,
    )

    _r: RentalIncomeSource = MockRentalIncomeSource()
    _t: TaxOnSurplusSource = MockTaxOnSurplusSource()
    _i: InterestIncomeSource = MockInterestIncomeSource()


_check_protocol_compliance()
