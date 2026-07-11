"""Fixtures for ground rent unit tests."""

from __future__ import annotations

import pytest


class MockHousingDataSource:
    """Mock Census/ACS housing data source."""

    DEFAULT_HOME_VALUES: dict[tuple[str, int], float] = {
        ("26163", 2020): 52_000.0,  # Wayne County median ~$52K
        ("26125", 2020): 235_000.0,  # Oakland County median ~$235K
        ("26163", 2022): 68_000.0,
        ("26125", 2022): 275_000.0,
    }

    DEFAULT_GROSS_RENT: dict[tuple[str, int], float] = {
        ("26163", 2020): 850.0,  # Wayne County monthly
        ("26125", 2020): 1_100.0,  # Oakland County monthly
        ("26163", 2022): 950.0,
        ("26125", 2022): 1_250.0,
    }

    DEFAULT_CONSTRUCTION_INDEX: dict[int, float] = {
        2020: 100.0,
        2022: 118.0,
    }

    def __init__(
        self,
        home_values: dict[tuple[str, int], float] | None = None,
        gross_rent: dict[tuple[str, int], float] | None = None,
        construction_index: dict[int, float] | None = None,
    ) -> None:
        self._home_values = (
            home_values if home_values is not None else self.DEFAULT_HOME_VALUES.copy()
        )
        self._gross_rent = gross_rent if gross_rent is not None else self.DEFAULT_GROSS_RENT.copy()
        self._construction_index = (
            construction_index
            if construction_index is not None
            else self.DEFAULT_CONSTRUCTION_INDEX.copy()
        )

    def get_median_home_value(self, fips: str, year: int) -> float | None:
        return self._home_values.get((fips, year))

    def get_median_gross_rent(self, fips: str, year: int) -> float | None:
        return self._gross_rent.get((fips, year))

    def get_construction_cost_index(self, year: int) -> float | None:
        return self._construction_index.get(year)


class MockCountyRentalIncomeSource:
    """Mock BEA rental income by category source."""

    DEFAULT_RENTS: dict[tuple[str, int], tuple[float, float, float]] = {
        # (fips, year): (agricultural, resource, urban)
        ("26163", 2020): (50_000_000.0, 10_000_000.0, 2_400_000_000.0),
        ("26125", 2020): (120_000_000.0, 5_000_000.0, 4_100_000_000.0),
        ("26163", 2022): (55_000_000.0, 12_000_000.0, 2_700_000_000.0),
        ("26125", 2022): (130_000_000.0, 6_000_000.0, 4_500_000_000.0),
    }

    def __init__(
        self, data: dict[tuple[str, int], tuple[float, float, float]] | None = None
    ) -> None:
        if data is None:
            self._data = self.DEFAULT_RENTS.copy()
        else:
            self._data = data

    def get_agricultural_rent(self, fips: str, year: int) -> float | None:
        entry = self._data.get((fips, year))
        return entry[0] if entry else None

    def get_resource_rent(self, fips: str, year: int) -> float | None:
        entry = self._data.get((fips, year))
        return entry[1] if entry else None

    def get_urban_rent(self, fips: str, year: int) -> float | None:
        entry = self._data.get((fips, year))
        return entry[2] if entry else None


@pytest.fixture
def mock_housing_source() -> MockHousingDataSource:
    return MockHousingDataSource()


@pytest.fixture
def mock_county_rental_source() -> MockCountyRentalIncomeSource:
    return MockCountyRentalIncomeSource()


def _check_protocol_compliance() -> None:
    from babylon.domain.economics.rent.data_sources import (
        CountyRentalIncomeSource,
        HousingDataSource,
    )

    _h: HousingDataSource = MockHousingDataSource()
    _c: CountyRentalIncomeSource = MockCountyRentalIncomeSource()


_check_protocol_compliance()
