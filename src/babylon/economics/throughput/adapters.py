"""SQLite adapters for throughput position data sources.

This module provides concrete implementations of the data source protocols
that query the 3NF normalized database (marxist-data-3NF.sqlite).

Feature: 014-throughput-position
Date: 2026-02-02

Usage:
    from babylon.data.reference.database import get_normalized_session_factory
    from babylon.economics.throughput.adapters import (
        SQLiteBEACountyGDPSource,
        SQLiteQCEWCountyNAICSSource,
    )

    session_factory = get_normalized_session_factory()
    bea_source = SQLiteBEACountyGDPSource(session_factory)
    qcew_source = SQLiteQCEWCountyNAICSSource(session_factory)

    gdp = bea_source.get_county_gdp("26163", 2022)
    emp = qcew_source.get_county_total_employment("26163", 2022)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from babylon.data.reference.schema import (
    DimBEAIndustry,
    DimCounty,
    DimIndustry,
    DimOwnership,
    DimTime,
    FactBEACountyGDP,
    FactQcewAnnual,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Constants for GDP conversion
MILLIONS_TO_DOLLARS = 1_000_000

# NAICS codes for 2-digit sectors used in supply chain depth calculation
NAICS_2DIGIT_SECTORS = [
    "11",  # Agriculture
    "21",  # Mining
    "22",  # Utilities
    "23",  # Construction
    "31-33",  # Manufacturing (combined)
    "42",  # Wholesale
    "44-45",  # Retail (combined)
    "48-49",  # Transportation (combined)
    "51",  # Information
    "52",  # Finance
    "53",  # Real Estate
    "54",  # Professional Services
    "55",  # Management
    "56",  # Admin/Support
    "61",  # Education
    "62",  # Healthcare
    "71",  # Entertainment
    "72",  # Accommodation/Food
    "81",  # Other Services
    "92",  # Government
]


class SQLiteBEACountyGDPSource:
    """SQLite adapter implementing BEACountyGDPSource protocol.

    Queries FactBEACountyGDP table with proper filtering to avoid
    double-counting from industry subtotals.

    CRITICAL: Always filters to line_number=1 (All industries) for totals.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_industry_id: int | None = None

    def _get_total_industry_id(self, session: Session) -> int | None:
        """Get the bea_industry_id for 'All industries' (line_number=1).

        Caches the result for efficiency.
        """
        if self._total_industry_id is None:
            total_bea = (
                session.query(DimBEAIndustry).filter(DimBEAIndustry.line_number == 1).first()
            )
            if total_bea:
                self._total_industry_id = total_bea.bea_industry_id
        return self._total_industry_id

    def _get_county_id(self, session: Session, fips: str) -> int | None:
        """Get county_id for a FIPS code."""
        county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
        return county.county_id if county else None

    def _get_time_id(self, session: Session, year: int) -> int | None:
        """Get time_id for a year."""
        time_dim = session.query(DimTime).filter(DimTime.year == year).first()
        return time_dim.time_id if time_dim else None

    def get_county_gdp(self, fips: str, year: int) -> float | None:
        """Get county GDP for a given FIPS code and year.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year (2001-2023 for available data).

        Returns:
            GDP in dollars, or None if data unavailable.
        """
        with self._session_factory() as session:
            total_industry_id = self._get_total_industry_id(session)
            if total_industry_id is None:
                logger.warning("BEA 'All industries' (line_number=1) not found")
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            result = (
                session.query(FactBEACountyGDP.gdp_millions)
                .filter(
                    FactBEACountyGDP.county_id == county_id,
                    FactBEACountyGDP.bea_industry_id == total_industry_id,
                    FactBEACountyGDP.time_id == time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return float(result[0]) * MILLIONS_TO_DOLLARS
            return None

    def get_all_counties(self, year: int) -> dict[str, float]:
        """Get GDP for all counties in a given year.

        Args:
            year: Calendar year.

        Returns:
            Dict mapping FIPS codes to GDP values in dollars.
        """
        with self._session_factory() as session:
            total_industry_id = self._get_total_industry_id(session)
            if total_industry_id is None:
                logger.warning("BEA 'All industries' (line_number=1) not found")
                return {}

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return {}

            results = (
                session.query(DimCounty.fips, FactBEACountyGDP.gdp_millions)
                .join(DimCounty, FactBEACountyGDP.county_id == DimCounty.county_id)
                .filter(
                    FactBEACountyGDP.bea_industry_id == total_industry_id,
                    FactBEACountyGDP.time_id == time_id,
                )
                .all()
            )

            return {
                fips: float(gdp_millions) * MILLIONS_TO_DOLLARS
                for fips, gdp_millions in results
                if gdp_millions is not None
            }


class SQLiteQCEWCountyNAICSSource:
    """SQLite adapter implementing QCEWCountyNAICSSource protocol.

    Queries FactQcewAnnual table with proper filtering for ownership
    and industry codes to avoid overcounting.

    Ownership Codes:
        - own_code='0': Total all ownerships (only has naics_code='10' totals)
        - own_code='5': Private sector (has sector-level breakdowns)

    For TOTAL employment: use own_code='0' + naics_code='10'
    For SECTOR employment: use own_code='5' + specific naics_code
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_ownership_id: int | None = None  # own_code='0'
        self._private_ownership_id: int | None = None  # own_code='5'
        self._total_industry_id: int | None = None
        self._naics_to_industry_id: dict[str, int] = {}

    def _get_total_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Total All' (own_code='0').

        Used for total employment queries (naics_code='10').
        Caches the result for efficiency.
        """
        if self._total_ownership_id is None:
            total_own = session.query(DimOwnership).filter(DimOwnership.own_code == "0").first()
            if total_own:
                self._total_ownership_id = total_own.ownership_id
        return self._total_ownership_id

    def _get_private_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Private' (own_code='5').

        Used for sector-level employment queries since total ownership
        only has aggregate data (naics_code='10').
        Caches the result for efficiency.
        """
        if self._private_ownership_id is None:
            private_own = session.query(DimOwnership).filter(DimOwnership.own_code == "5").first()
            if private_own:
                self._private_ownership_id = private_own.ownership_id
        return self._private_ownership_id

    def _get_total_industry_id(self, session: Session) -> int | None:
        """Get industry_id for 'Total' industry (naics_code='10').

        Caches the result for efficiency.
        """
        if self._total_industry_id is None:
            total_ind = session.query(DimIndustry).filter(DimIndustry.naics_code == "10").first()
            if total_ind:
                self._total_industry_id = total_ind.industry_id
        return self._total_industry_id

    def _get_industry_id(self, session: Session, naics: str) -> int | None:
        """Get industry_id for a NAICS code.

        Caches results for efficiency.
        """
        if naics not in self._naics_to_industry_id:
            industry = session.query(DimIndustry).filter(DimIndustry.naics_code == naics).first()
            if industry:
                self._naics_to_industry_id[naics] = industry.industry_id
        return self._naics_to_industry_id.get(naics)

    def _get_county_id(self, session: Session, fips: str) -> int | None:
        """Get county_id for a FIPS code."""
        county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
        return county.county_id if county else None

    def _get_time_id(self, session: Session, year: int) -> int | None:
        """Get time_id for a year."""
        time_dim = session.query(DimTime).filter(DimTime.year == year).first()
        return time_dim.time_id if time_dim else None

    def get_county_naics_employment(self, fips: str, naics: str, year: int) -> int | None:
        """Get employment for a county-NAICS combination.

        Uses private sector (own_code='5') for sector-level data since
        total ownership only has aggregate totals (naics_code='10').

        Args:
            fips: 5-character county FIPS code.
            naics: 2-digit NAICS sector code.
            year: Calendar year.

        Returns:
            Employment count (persons), or None if suppressed/unavailable.
        """
        with self._session_factory() as session:
            private_ownership_id = self._get_private_ownership_id(session)
            if private_ownership_id is None:
                logger.warning("QCEW 'Private' ownership (own_code='5') not found")
                return None

            industry_id = self._get_industry_id(session, naics)
            if industry_id is None:
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            result = (
                session.query(FactQcewAnnual.employment)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == private_ownership_id,
                    FactQcewAnnual.industry_id == industry_id,
                    FactQcewAnnual.time_id == time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return int(result[0])
            return None

    def get_county_employment_by_naics(self, fips: str, year: int) -> dict[str, int]:
        """Get employment by NAICS sector for a county.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            Dict mapping NAICS codes to employment counts.
            Suppressed/unavailable sectors are excluded.
        """
        result: dict[str, int] = {}
        for naics in NAICS_2DIGIT_SECTORS:
            emp = self.get_county_naics_employment(fips, naics, year)
            if emp is not None:
                result[naics] = emp
        return result

    def get_county_total_employment(self, fips: str, year: int) -> int | None:
        """Get total employment for a county.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            Total employment count, or None if unavailable.
        """
        with self._session_factory() as session:
            total_ownership_id = self._get_total_ownership_id(session)
            if total_ownership_id is None:
                logger.warning("QCEW 'Total All' ownership (own_code='0') not found")
                return None

            total_industry_id = self._get_total_industry_id(session)
            if total_industry_id is None:
                logger.warning("QCEW 'Total' industry (naics_code='10') not found")
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            result = (
                session.query(FactQcewAnnual.employment)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == total_ownership_id,
                    FactQcewAnnual.industry_id == total_industry_id,
                    FactQcewAnnual.time_id == time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return int(result[0])
            return None

    def get_county_naics_wages(self, fips: str, naics: str, year: int) -> float | None:
        """Get average weekly wage for a county-NAICS combination.

        Uses private sector (own_code='5') for sector-level data.

        Args:
            fips: 5-character county FIPS code.
            naics: 2-digit NAICS sector code.
            year: Calendar year.

        Returns:
            Average weekly wage ($/week), or None if suppressed/unavailable.
        """
        with self._session_factory() as session:
            private_ownership_id = self._get_private_ownership_id(session)
            if private_ownership_id is None:
                return None

            industry_id = self._get_industry_id(session, naics)
            if industry_id is None:
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            result = (
                session.query(FactQcewAnnual.avg_weekly_wage_usd)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == private_ownership_id,
                    FactQcewAnnual.industry_id == industry_id,
                    FactQcewAnnual.time_id == time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return float(result[0])
            return None


__all__ = [
    "SQLiteBEACountyGDPSource",
    "SQLiteQCEWCountyNAICSSource",
    "NAICS_2DIGIT_SECTORS",
]
