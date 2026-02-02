"""Data source protocols for throughput position analysis.

This module defines the protocols for county-level GDP and employment data
sources. Implementations may use BEA API, SQLite, or mock data.

Feature: 014-throughput-position
Date: 2026-02-02
"""

from __future__ import annotations

from typing import Protocol


class BEACountyGDPSource(Protocol):
    """Protocol for BEA county-level GDP data (CAGDP1).

    Data Source:
        BEA CAGDP1 (County Annual GDP Summary)
        https://apps.bea.gov/api/data/

    Units:
        GDP in chained 2017 dollars (real GDP, LineCode 1).

    Important:
        All GDP values MUST use "chained 2017 dollars" to ensure consistent
        purchasing power comparisons. Nominal GDP values MUST NOT be mixed
        with chained values in ratio calculations.

    Example:
        >>> source = SQLiteBEACountyGDPSource("path/to/data.sqlite")
        >>> gdp = source.get_county_gdp("26163", 2022)
        >>> print(f"Wayne County 2022 GDP: ${gdp:,.0f}")
        Wayne County 2022 GDP: $95,000,000,000
    """

    def get_county_gdp(self, fips: str, year: int) -> float | None:
        """Get county GDP for a given FIPS code and year.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year (2001-2023 for available data)

        Returns:
            GDP in chained 2017 dollars, or None if data unavailable
        """
        ...

    def get_all_counties(self, year: int) -> dict[str, float]:
        """Get GDP for all counties in a given year.

        Args:
            year: Calendar year

        Returns:
            Dict mapping FIPS codes to GDP values (chained 2017 dollars)
        """
        ...


class QCEWCountyNAICSSource(Protocol):
    """Protocol for QCEW county employment by NAICS sector.

    Data Source:
        BLS QCEW (Quarterly Census of Employment and Wages)
        https://www.bls.gov/cew/

    Units:
        Employment in persons (headcount, not FTE).
        Wages in dollars per week.

    Note:
        QCEW has ~60% suppression rate at county-NAICS level due to
        disclosure restrictions (typically <3 establishments).

    Example:
        >>> source = SQLiteQCEWCountyNAICSSource("path/to/data.sqlite")
        >>> emp = source.get_county_naics_employment("26163", "52", 2022)
        >>> print(f"Wayne County Finance employment: {emp:,}")
        Wayne County Finance employment: 25,000
    """

    def get_county_naics_employment(self, fips: str, naics: str, year: int) -> int | None:
        """Get employment for a county-NAICS combination.

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            Employment count (persons), or None if suppressed/unavailable
        """
        ...

    def get_county_employment_by_naics(self, fips: str, year: int) -> dict[str, int]:
        """Get employment by NAICS sector for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Dict mapping NAICS codes to employment counts
            (suppressed sectors excluded)
        """
        ...

    def get_county_total_employment(self, fips: str, year: int) -> int | None:
        """Get total employment for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Total employment count, or None if unavailable
        """
        ...

    def get_county_naics_wages(self, fips: str, naics: str, year: int) -> float | None:
        """Get average weekly wage for a county-NAICS combination.

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            Average weekly wage ($/week), or None if suppressed/unavailable
        """
        ...


__all__ = ["BEACountyGDPSource", "QCEWCountyNAICSSource"]
