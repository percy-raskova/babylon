"""Data source protocols for MELT and Basket Visibility module.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module defines the data source protocols for:
- BEA GDP data (for MELT computation)
- QCEW employment data (for MELT computation)
- CPI data (for V_reproduction inflation adjustment) [CHK044]

CPI Data Source Specification (CHK044):
    V_reproduction is anchored at $12/hour in 2024 dollars (Census poverty methodology).
    To adjust for other years, use BLS CPI-U (All Urban Consumers) series CUUR0000SA0.

    Formula: V_reproduction(year) = $12 × (CPI_2024 / CPI_year)

    Example:
        If CPI_2024 = 308.4 and CPI_2020 = 258.8, then:
        V_reproduction(2020) = $12 × (308.4 / 258.8) = $14.30/hour

    Note: This CPI adjustment is for historical comparison only. For simulation
    purposes, use current-year dollars (TSSI methodology).
"""

from __future__ import annotations

from typing import Protocol


class BEADataSource(Protocol):
    """Protocol for BEA (Bureau of Economic Analysis) GDP data.

    This protocol defines the interface for retrieving national GDP values
    from BEA NIPA (National Income and Product Accounts) data.

    Data Source:
        BEA NIPA Table 1.1.5 (Gross Domestic Product)
        https://apps.bea.gov/iTable/index_nipa.cfm

    Units:
        Current dollars (billions). Converted to full dollars in implementation.

    Example:
        >>> source = SQLiteBEASource("path/to/data.sqlite")
        >>> gdp = source.get_gdp(2022)
        >>> print(f"2022 GDP: ${gdp:,.0f}")
        2022 GDP: $25,462,700,000,000
    """

    def get_gdp(self, year: int) -> float | None:
        """Get national GDP for a given year.

        Args:
            year: Calendar year (typically 2010-2024)

        Returns:
            GDP in current dollars, or None if data unavailable

        Example:
            >>> source.get_gdp(2022)
            25462700000000.0  # ~$25.5 trillion
        """
        ...


class QCEWDataSource(Protocol):
    """Protocol for QCEW (Quarterly Census of Employment and Wages) data.

    This protocol defines the interface for retrieving national employment
    totals from BLS QCEW data.

    Data Source:
        BLS QCEW (Quarterly Census of Employment and Wages)
        https://www.bls.gov/cew/

    Units:
        Employment is in persons (headcount, not FTE).

    Example:
        >>> source = SQLiteQCEWSource("path/to/data.sqlite")
        >>> employment = source.get_national_employment(2022)
        >>> print(f"2022 employment: {employment:,} workers")
        2022 employment: 155,000,000 workers
    """

    def get_national_employment(self, year: int) -> int | None:
        """Get national employment total for a given year.

        Args:
            year: Calendar year (typically 2010-2024)

        Returns:
            Employment count (persons), or None if data unavailable

        Example:
            >>> source.get_national_employment(2022)
            155000000  # ~155 million workers
        """
        ...


class CPIDataSource(Protocol):
    """Protocol for CPI (Consumer Price Index) data.

    This protocol defines the interface for retrieving CPI values for
    inflation adjustment of V_reproduction.

    Data Source (CHK044):
        BLS CPI-U (All Urban Consumers) series CUUR0000SA0
        https://www.bls.gov/cpi/

    Base Year:
        2024 for $12/hour subsistence floor (Census poverty methodology)

    Formula:
        V_reproduction(year) = $12 × (CPI_2024 / CPI_year)

    Example:
        >>> source = BLSCPISource()
        >>> cpi_2022 = source.get_cpi(2022)
        >>> cpi_2024 = source.get_cpi(2024)
        >>> v_repro_2022 = 12.0 * (cpi_2024 / cpi_2022)
        >>> print(f"V_reproduction(2022): ${v_repro_2022:.2f}/hour")
        V_reproduction(2022): $12.84/hour
    """

    def get_cpi(self, year: int) -> float | None:
        """Get CPI-U index value for a given year.

        Args:
            year: Calendar year (typically 2010-2024)

        Returns:
            CPI-U index value, or None if data unavailable

        Example:
            >>> source.get_cpi(2024)
            308.4  # CPI-U index (base 1982-84=100)
        """
        ...


# Base year for V_reproduction calculation
CPI_BASE_YEAR: int = 2024
V_REPRODUCTION_BASE: float = 12.0  # $/hour in base year


def compute_v_reproduction(
    year: int,
    cpi_source: CPIDataSource,
) -> float | None:
    """Compute inflation-adjusted V_reproduction for a given year.

    Formula: V_reproduction(year) = $12 × (CPI_2024 / CPI_year)

    Args:
        year: Calendar year for which to compute V_reproduction
        cpi_source: Data source for CPI values

    Returns:
        V_reproduction in $/hour (current-year dollars), or None if CPI unavailable

    Example:
        >>> v_repro = compute_v_reproduction(2022, cpi_source)
        >>> print(f"V_reproduction(2022): ${v_repro:.2f}/hour")
        V_reproduction(2022): $12.84/hour
    """
    cpi_base = cpi_source.get_cpi(CPI_BASE_YEAR)
    cpi_year = cpi_source.get_cpi(year)

    if cpi_base is None or cpi_year is None:
        return None

    return V_REPRODUCTION_BASE * (cpi_base / cpi_year)


__all__ = [
    "BEADataSource",
    "CPIDataSource",
    "QCEWDataSource",
    "compute_v_reproduction",
]
