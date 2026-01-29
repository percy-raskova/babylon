"""Shared fixtures for economics integration tests.

This module provides fixtures for testing the Marxian value transformation
pipeline, including:

- Mock data sources (QCEW, BEA)
- DepartmentMapper with test configuration
- MarxianHydrator instances (with and without imperial rent)
- PeripheryReproductionBasket and ImperialRentCalculator
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.economics.department_mapper import DepartmentMapper
from babylon.economics.hydrator import MarxianHydrator
from babylon.economics.reproduction import (
    ImperialRentCalculator,
    PeripheryReproductionBasket,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# MOCK DATA SOURCES
# =============================================================================


class MockQCEWDataSource:
    """Mock QCEW data source with predetermined county wage data.

    Implements the QCEWDataSource protocol for testing.
    """

    def __init__(self, data: dict[tuple[str, int], list[tuple[str, float, int]]]) -> None:
        """Initialize with county data.

        Args:
            data: Mapping of (fips_code, year) -> list of (naics_code, wages, employment)
        """
        self._data = data

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year.

        Returns:
            List of (naics_code, wages, employment) tuples.
        """
        return self._data.get((fips_code, year), [])


class MockBEADataSource:
    """Mock BEA data source with predetermined industry ratios.

    Implements the BEADataSource protocol for testing.
    """

    def __init__(
        self,
        sv_ratios: dict[str, float] | None = None,
        cv_ratios: dict[str, float] | None = None,
    ) -> None:
        """Initialize with ratio data.

        Args:
            sv_ratios: NAICS code -> s/v ratio mapping.
            cv_ratios: NAICS code -> c/v ratio mapping.
        """
        self._sv_ratios = sv_ratios or {}
        self._cv_ratios = cv_ratios or {}

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Get s/v ratio for a NAICS code.

        Returns:
            Rate of surplus value, or None if unavailable.
        """
        return self._sv_ratios.get(naics_code)

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Get c/v ratio for a NAICS code.

        Returns:
            Organic composition of capital, or None if unavailable.
        """
        return self._cv_ratios.get(naics_code)


# =============================================================================
# QCEW DATA FIXTURES
# =============================================================================


@pytest.fixture
def wayne_county_qcew() -> list[tuple[str, float, int]]:
    """Wayne County (Detroit area) QCEW data - working class industrial base.

    Wayne County characteristics:
    - Strong manufacturing (auto industry) - Dept IIa
    - Basic retail and services - Dept IIa
    - Limited luxury sector - Dept IIb
    - Government excluded (NAICS 92)
    """
    return [
        # Manufacturing (heavily IIa - necessary consumption)
        ("336111", 500_000_000.0, 50000),  # Auto manufacturing
        ("311", 100_000_000.0, 15000),  # Food manufacturing
        # Retail (mostly IIa)
        ("4451", 80_000_000.0, 20000),  # Grocery stores
        ("4522", 60_000_000.0, 12000),  # Department stores
        # Services (mix)
        ("722513", 40_000_000.0, 25000),  # Fast food (IIa)
        # Healthcare/Education (Dept III - social reproduction)
        ("62", 200_000_000.0, 45000),  # Healthcare
        ("6244", 30_000_000.0, 8000),  # Child day care
        # Government - excluded
        ("921110", 150_000_000.0, 20000),  # Federal government
    ]


@pytest.fixture
def oakland_county_qcew() -> list[tuple[str, float, int]]:
    """Oakland County (affluent suburb) QCEW data - upper middle class consumption.

    Oakland County characteristics:
    - Professional services - Dept I (B2B)
    - Luxury retail and services - Dept IIb
    - Higher proportion of luxury consumption
    - Government excluded (NAICS 92)
    """
    return [
        # Professional services (Dept I - B2B)
        ("54", 300_000_000.0, 40000),  # Professional services
        # Retail (more luxury-oriented)
        ("44831", 50_000_000.0, 3000),  # Jewelry stores (pure IIb)
        ("45111", 40_000_000.0, 5000),  # Sporting goods (IIb-heavy)
        ("4522", 80_000_000.0, 15000),  # Department stores (mix)
        # Services (more luxury)
        ("71391", 30_000_000.0, 2000),  # Golf courses (pure IIb)
        ("722511", 60_000_000.0, 8000),  # Fine dining (IIb-heavy)
        # Healthcare/Education (Dept III)
        ("62", 180_000_000.0, 35000),  # Healthcare
        ("6244", 25_000_000.0, 6000),  # Child day care
        # Government - excluded
        ("921110", 100_000_000.0, 12000),  # Federal government
    ]


# =============================================================================
# DEPARTMENT MAPPER FIXTURE
# =============================================================================


@pytest.fixture
def dept_mapper(tmp_path: Path) -> DepartmentMapper:
    """Create a DepartmentMapper for testing."""
    yaml_content = """
defaults:
  31:
    dept_IIa: 0.70
    dept_IIb: 0.30
  44:
    dept_IIa: 0.75
    dept_IIb: 0.25
  45:
    dept_IIa: 0.65
    dept_IIb: 0.35
  54:
    dept_I: 0.60
    dept_IIa: 0.30
    dept_IIb: 0.10
  62:
    dept_IIa: 0.30
    dept_III: 0.70
  71:
    dept_IIa: 0.30
    dept_IIb: 0.70
  72:
    dept_IIa: 0.60
    dept_IIb: 0.40

overrides:
  336111:
    dept_IIa: 0.65
    dept_IIb: 0.35
  311:
    dept_IIa: 0.85
    dept_IIb: 0.15
  4451:
    dept_IIa: 0.95
    dept_IIb: 0.05
  4522:
    dept_IIa: 0.60
    dept_IIb: 0.40
  44831:
    dept_IIb: 1.0
  45111:
    dept_IIa: 0.30
    dept_IIb: 0.70
  6244:
    dept_III: 1.0
  71391:
    dept_IIb: 1.0
  722511:
    dept_IIa: 0.20
    dept_IIb: 0.80
  722513:
    dept_IIa: 0.90
    dept_IIb: 0.10

excluded:
  - "92"

default_ratios:
  dept_I:
    cv_ratio: 3.0
    sv_ratio: 2.0
  dept_IIa:
    cv_ratio: 1.5
    sv_ratio: 1.0
  dept_IIb:
    cv_ratio: 2.5
    sv_ratio: 3.0
  dept_III:
    cv_ratio: 0.5
    sv_ratio: 0.7
"""
    config_file = tmp_path / "naics_to_dept.yaml"
    config_file.write_text(yaml_content)
    return DepartmentMapper.from_yaml(config_file)


# =============================================================================
# BEA DATA SOURCE FIXTURE
# =============================================================================


@pytest.fixture
def mock_bea_source() -> MockBEADataSource:
    """Create a mock BEA data source with industry ratios."""
    return MockBEADataSource(
        sv_ratios={
            "336111": 1.2,  # Auto manufacturing
            "311": 0.9,  # Food manufacturing
            "4451": 0.8,  # Grocery stores
        },
        cv_ratios={
            "336111": 2.5,  # Capital-intensive auto
            "311": 1.8,  # Food manufacturing
            "4451": 1.2,  # Retail
        },
    )


# =============================================================================
# IMPERIAL RENT FIXTURES
# =============================================================================


@pytest.fixture
def periphery_basket() -> PeripheryReproductionBasket:
    """Default peripheral reproduction basket (~$2000/year)."""
    return PeripheryReproductionBasket.default()


@pytest.fixture
def rent_calculator(periphery_basket: PeripheryReproductionBasket) -> ImperialRentCalculator:
    """Imperial rent calculator with default periphery basket."""
    return ImperialRentCalculator(periphery_basket)


# =============================================================================
# HYDRATOR FIXTURES
# =============================================================================


@pytest.fixture
def hydrator_with_rent(
    wayne_county_qcew: list[tuple[str, float, int]],
    oakland_county_qcew: list[tuple[str, float, int]],
    dept_mapper: DepartmentMapper,
    mock_bea_source: MockBEADataSource,
    rent_calculator: ImperialRentCalculator,
) -> MarxianHydrator:
    """MarxianHydrator configured with imperial rent calculator.

    This fixture provides a hydrator that can serve both Wayne and Oakland
    county data for testing imperial rent stratification.
    """
    # Combine data for both counties
    combined_qcew = MockQCEWDataSource(
        {
            ("26163", 2022): wayne_county_qcew,  # Wayne County, MI
            ("26125", 2022): oakland_county_qcew,  # Oakland County, MI
            # Empty data for edge case testing
            ("99999", 2022): [],
        }
    )

    return MarxianHydrator(
        qcew_source=combined_qcew,
        bea_source=mock_bea_source,
        dept_mapper=dept_mapper,
        rent_calculator=rent_calculator,
    )
