"""Fixtures for MELT and Basket Visibility unit tests.

Feature: 013-melt-basket-visibility
Date: 2026-02-01
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.economics.melt import NationalParameters
from babylon.economics.melt.data_sources import BEADataSource, CPIDataSource, QCEWDataSource

if TYPE_CHECKING:
    pass


# =============================================================================
# Mock Data Sources
# =============================================================================


class MockBEADataSource:
    """Mock BEA data source for testing.

    Provides configurable GDP values for testing MELT computation.
    """

    # Default values based on BEA NIPA data
    DEFAULT_GDP_BY_YEAR: dict[int, float] = {
        2010: 14_992_100_000_000.0,  # ~$15.0 trillion
        2015: 18_219_300_000_000.0,  # ~$18.2 trillion
        2020: 21_060_500_000_000.0,  # ~$21.1 trillion
        2022: 25_462_700_000_000.0,  # ~$25.5 trillion
        2024: 28_200_000_000_000.0,  # ~$28.2 trillion (estimate)
    }

    def __init__(self, gdp_by_year: dict[int, float] | None = None) -> None:
        """Initialize with optional GDP values by year.

        Args:
            gdp_by_year: Dict mapping year to GDP in dollars.
                         Pass None for defaults, pass {} for no data.
        """
        if gdp_by_year is None:
            self._gdp_by_year = self.DEFAULT_GDP_BY_YEAR.copy()
        else:
            self._gdp_by_year = gdp_by_year

    def get_gdp(self, year: int) -> float | None:
        """Get GDP for a given year."""
        return self._gdp_by_year.get(year)


class MockQCEWDataSource:
    """Mock QCEW data source for testing.

    Provides configurable employment values for testing MELT computation.
    """

    # Default values based on BLS QCEW data
    DEFAULT_EMPLOYMENT_BY_YEAR: dict[int, int] = {
        2010: 129_818_000,  # ~130 million workers
        2015: 141_824_000,  # ~142 million workers
        2020: 142_180_000,  # ~142 million workers (COVID impact)
        2022: 152_900_000,  # ~153 million workers
        2024: 157_000_000,  # ~157 million workers (estimate)
    }

    def __init__(self, employment_by_year: dict[int, int] | None = None) -> None:
        """Initialize with optional employment values by year.

        Args:
            employment_by_year: Dict mapping year to employment count.
                                Pass None for defaults, pass {} for no data.
        """
        if employment_by_year is None:
            self._employment_by_year = self.DEFAULT_EMPLOYMENT_BY_YEAR.copy()
        else:
            self._employment_by_year = employment_by_year

    def get_national_employment(self, year: int) -> int | None:
        """Get national employment for a given year."""
        return self._employment_by_year.get(year)


class MockCPIDataSource:
    """Mock CPI data source for testing.

    Provides configurable CPI values for V_reproduction adjustment.
    """

    # Default values based on BLS CPI-U (base 1982-84=100)
    DEFAULT_CPI_BY_YEAR: dict[int, float] = {
        2010: 218.1,
        2015: 237.0,
        2020: 258.8,
        2022: 292.7,
        2024: 308.4,  # Estimate
    }

    def __init__(self, cpi_by_year: dict[int, float] | None = None) -> None:
        """Initialize with optional CPI values by year.

        Args:
            cpi_by_year: Dict mapping year to CPI-U index.
                         Pass None for defaults, pass {} for no data.
        """
        if cpi_by_year is None:
            self._cpi_by_year = self.DEFAULT_CPI_BY_YEAR.copy()
        else:
            self._cpi_by_year = cpi_by_year

    def get_cpi(self, year: int) -> float | None:
        """Get CPI-U index for a given year."""
        return self._cpi_by_year.get(year)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_bea_source() -> MockBEADataSource:
    """Provide a mock BEA data source with default GDP values."""
    return MockBEADataSource()


@pytest.fixture
def mock_qcew_source() -> MockQCEWDataSource:
    """Provide a mock QCEW data source with default employment values."""
    return MockQCEWDataSource()


@pytest.fixture
def mock_cpi_source() -> MockCPIDataSource:
    """Provide a mock CPI data source with default CPI values."""
    return MockCPIDataSource()


@pytest.fixture
def sample_national_params() -> NationalParameters:
    """Provide sample NationalParameters for 2022.

    Values based on:
    - τ ≈ $65/hour (GDP / employment × 2080)
    - γ_basket = 0.68 (MVP value)
    - τ_effective = τ × γ_basket ≈ $44.2/hour
    - V_reproduction = $12/hour (Census poverty methodology)
    """
    return NationalParameters(
        year=2022,
        tau=65.0,
        alpha=0.25,
        gamma_import=0.35,
        gamma_basket=0.68,
        tau_effective=44.2,
        v_reproduction=12.0,
        estimated=True,
    )


@pytest.fixture
def mvp_params() -> NationalParameters:
    """Provide MVP mode NationalParameters.

    Uses hardcoded γ_basket = 0.68 with estimated=True.
    """
    return NationalParameters(
        year=2022,
        tau=65.0,
        alpha=0.25,
        gamma_import=0.35,
        gamma_basket=0.68,
        tau_effective=44.2,  # 65 × 0.68
        v_reproduction=12.0,
        estimated=True,
    )


# Ensure mock classes satisfy protocols (runtime check)
def _check_protocol_compliance() -> None:
    """Verify mock classes satisfy their respective protocols."""
    _: BEADataSource = MockBEADataSource()
    _: QCEWDataSource = MockQCEWDataSource()  # type: ignore[no-redef]
    _: CPIDataSource = MockCPIDataSource()  # type: ignore[no-redef]


_check_protocol_compliance()
