"""Fixtures for Gamma Visibility Tensor unit tests.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05
"""

from __future__ import annotations

import pytest

from babylon.economics.gamma.data_sources import (
    ERDISource,
    PaidCareHoursSource,
    UnpaidCareHoursSource,
)
from babylon.economics.gamma.types import GammaBasket, GammaIII

# =============================================================================
# Mock Data Sources
# =============================================================================


class MockUnpaidCareHoursSource:
    """Mock ATUS unpaid care hours source for testing.

    Provides configurable unpaid care hours by year.
    Default: 33.0 billion hours (2022 ATUS estimate for US).
    """

    DEFAULT_HOURS_BY_YEAR: dict[int, float] = {
        2010: 31.0,
        2015: 32.0,
        2020: 34.0,
        2022: 33.0,
        2024: 32.5,
    }

    def __init__(self, hours_by_year: dict[int, float] | None = None) -> None:
        """Initialize with optional hours by year.

        Args:
            hours_by_year: Dict mapping year to unpaid care hours (billions).
                Pass None for defaults, pass {} for no data.
        """
        if hours_by_year is None:
            self._hours_by_year = self.DEFAULT_HOURS_BY_YEAR.copy()
        else:
            self._hours_by_year = hours_by_year

    def get_unpaid_care_hours(self, year: int) -> float | None:
        """Get unpaid care hours for a given year."""
        return self._hours_by_year.get(year)


class MockPaidCareHoursSource:
    """Mock QCEW paid care hours source for testing.

    Provides configurable paid care hours by year.
    Default: 16.5 billion hours (2022 QCEW estimate for US care sectors).
    """

    DEFAULT_HOURS_BY_YEAR: dict[int, float] = {
        2010: 14.0,
        2015: 15.0,
        2020: 15.5,
        2022: 16.5,
        2024: 17.0,
    }

    def __init__(self, hours_by_year: dict[int, float] | None = None) -> None:
        """Initialize with optional hours by year.

        Args:
            hours_by_year: Dict mapping year to paid care hours (billions).
                Pass None for defaults, pass {} for no data.
        """
        if hours_by_year is None:
            self._hours_by_year = self.DEFAULT_HOURS_BY_YEAR.copy()
        else:
            self._hours_by_year = hours_by_year

    def get_paid_care_hours(self, year: int) -> float | None:
        """Get paid care hours for a given year."""
        return self._hours_by_year.get(year)


class MockERDISource:
    """Mock ERDI data source for testing.

    Provides configurable ERDI values and import shares.
    """

    DEFAULT_ERDI: dict[str, float] = {
        "CHN": 1.80,
        "MEX": 1.50,
        "CAN": 1.10,
        "VNM": 2.50,
        "DEU": 1.00,
    }

    DEFAULT_IMPORT_SHARES: dict[str, float] = {
        "CHN": 0.30,
        "MEX": 0.20,
        "CAN": 0.20,
        "VNM": 0.10,
        "DEU": 0.20,
    }

    def __init__(
        self,
        erdi_values: dict[str, float] | None = None,
        import_shares: dict[int, dict[str, float]] | None = None,
    ) -> None:
        """Initialize with optional ERDI values and import shares."""
        self._erdi = erdi_values if erdi_values is not None else self.DEFAULT_ERDI.copy()
        self._import_shares = import_shares or {}

    def get_erdi(self, country_code: str) -> float | None:
        """Get ERDI for a country."""
        return self._erdi.get(country_code)

    def get_import_shares(self, year: int) -> dict[str, float] | None:
        """Get import shares for a year."""
        return self._import_shares.get(year)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_unpaid_source() -> MockUnpaidCareHoursSource:
    """Provide a mock ATUS unpaid care hours source with defaults."""
    return MockUnpaidCareHoursSource()


@pytest.fixture
def mock_paid_source() -> MockPaidCareHoursSource:
    """Provide a mock QCEW paid care hours source with defaults."""
    return MockPaidCareHoursSource()


@pytest.fixture
def mock_erdi_source() -> MockERDISource:
    """Provide a mock ERDI data source with defaults."""
    return MockERDISource()


@pytest.fixture
def sample_gamma_iii() -> GammaIII:
    """Provide a sample GammaIII result for 2022.

    Values: paid=16.5B, unpaid=33.0B, gamma_III=0.333, Fortunati=2.003
    """
    return GammaIII(
        year=2022,
        paid_care_hours=16.5,
        unpaid_care_hours=33.0,
        gamma_iii=0.333,
        fortunati_exploitation=2.003,
    )


@pytest.fixture
def sample_gamma_basket() -> GammaBasket:
    """Provide a sample GammaBasket result for 2022.

    Values: alpha=0.35, gamma_import=0.65, gamma_basket=0.74
    """
    return GammaBasket(
        year=2022,
        alpha=0.35,
        gamma_import=0.65,
        gamma_basket=0.74,
    )


# Ensure mock classes satisfy protocols (runtime check)
def _check_protocol_compliance() -> None:
    """Verify mock classes satisfy their respective protocols."""
    _u: UnpaidCareHoursSource = MockUnpaidCareHoursSource()
    _p: PaidCareHoursSource = MockPaidCareHoursSource()
    _e: ERDISource = MockERDISource()


_check_protocol_compliance()
