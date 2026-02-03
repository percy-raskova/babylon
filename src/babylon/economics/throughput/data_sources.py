"""Data source protocols for throughput position analysis.

This module defines the protocols for county-level GDP and employment data
sources. Implementations may use BEA API, SQLite, or mock data.

Feature: 014-throughput-position
Date: 2026-02-02

Database Schema Reference (marxist-data-3NF.sqlite):
    BEA GDP: FactBEACountyGDP joined with DimCounty, DimTime, DimBEAIndustry
    QCEW: FactQcewAnnual joined with DimCounty, DimTime, DimIndustry, DimOwnership

Critical Aggregation Notes:
    - BEA GDP: MUST filter to bea_industry_id where line_number=1 (All industries)
      to avoid double-counting from industry subtotals
    - QCEW: MUST filter to own_code='0' (Total All) and naics_code='10' (Total)
      to get total covered employment, not sum of all industry rows
"""

from __future__ import annotations

from typing import Protocol


class BEACountyGDPSource(Protocol):
    """Protocol for BEA county-level GDP data.

    Data Source:
        BEA CAGDP2 (County GDP by Industry) loaded via mise run data:bea-county
        Stored in: FactBEACountyGDP table

    Database Schema:
        - FactBEACountyGDP: county_id, bea_industry_id, time_id, gdp_millions
        - DimCounty: county_id, fips (5-char string)
        - DimTime: time_id, year
        - DimBEAIndustry: bea_industry_id, bea_code, industry_name, line_number

    CRITICAL: For total county GDP, filter to line_number=1 ("All industries").
    Summing all rows produces ~4.5x overcounting due to industry subtotals.

    Units:
        GDP in millions of dollars (gdp_millions column).
        Data years: 2001-2023 (as of Feb 2026 load).

    Example:
        >>> source = SQLiteBEACountyGDPSource(session_factory)
        >>> gdp = source.get_county_gdp("26163", 2022)
        >>> print(f"Wayne County 2022 GDP: ${gdp:,.0f}")
        Wayne County 2022 GDP: $113,826,760,000
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
        Loaded via mise run data:qcew
        Stored in: FactQcewAnnual table

    Database Schema:
        - FactQcewAnnual: county_id, industry_id, ownership_id, time_id,
          employment, total_wages_usd, avg_weekly_wage_usd, avg_annual_pay_usd,
          disclosure_code
        - DimCounty: county_id, fips (5-char string)
        - DimTime: time_id, year
        - DimIndustry: industry_id, naics_code, industry_title, naics_level
        - DimOwnership: ownership_id, own_code, own_title

    CRITICAL Aggregation Rules:
        - For TOTAL employment: filter own_code='0' AND naics_code='10'
        - For sector employment: filter own_code='0' AND specific naics_code
        - Do NOT sum all rows - this causes massive overcounting

    Units:
        Employment in persons (annual average).
        Wages in dollars (avg_weekly_wage_usd, avg_annual_pay_usd).
        Data years: 2010-2024 (as of Feb 2026 load).

    Note:
        QCEW has ~60% suppression rate at county-NAICS level due to
        disclosure restrictions (typically <3 establishments).
        Check disclosure_code for suppression status.

    Example:
        >>> source = SQLiteQCEWCountyNAICSSource(session_factory)
        >>> emp = source.get_county_total_employment("26163", 2022)
        >>> print(f"Wayne County total employment: {emp:,}")
        Wayne County total employment: 714,597
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
