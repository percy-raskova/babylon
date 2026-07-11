"""Fixtures for value basis conversion unit tests."""

from __future__ import annotations

import pytest


class MockPriceIndexSource:
    """Mock CPI and GDP deflator source."""

    DEFAULT_DATA: dict[int, tuple[float, float, float, float]] = {
        # year: (cpi, gdp_deflator, total_labor_hours, nominal_gdp)
        2020: (258.81, 113.648, 234_000_000_000.0, 21_060_500_000_000.0),
        2022: (292.66, 124.828, 248_000_000_000.0, 25_462_700_000_000.0),
        2010: (218.06, 100.000, 225_000_000_000.0, 14_992_100_000_000.0),  # Base year
    }

    def __init__(self, data: dict[int, tuple[float, float, float, float]] | None = None) -> None:
        if data is None:
            self._data = self.DEFAULT_DATA.copy()
        else:
            self._data = data

    def get_cpi(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[0] if entry else None

    def get_gdp_deflator(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[1] if entry else None

    def get_total_labor_hours(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[2] if entry else None

    def get_nominal_gdp(self, year: int) -> float | None:
        entry = self._data.get(year)
        return entry[3] if entry else None


@pytest.fixture
def mock_price_index_source() -> MockPriceIndexSource:
    return MockPriceIndexSource()


def _check_protocol_compliance() -> None:
    from babylon.domain.economics.monetary.data_sources import PriceIndexSource

    _p: PriceIndexSource = MockPriceIndexSource()


_check_protocol_compliance()
