"""SQLite adapters for throughput position data sources.

This module provides concrete implementations of the data source protocols
that query the 3NF normalized database (marxist-data-3NF.sqlite).

Feature: 014-throughput-position
Date: 2026-02-02

Usage:
    from babylon.reference.database import get_normalized_session_factory
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

from sqlalchemy import func

from babylon.reference.schema import (
    DimBEAIndustry,
    DimCounty,
    DimIndustry,
    DimOwnership,
    DimTime,
    FactBEACountyGDP,
    FactQcewAnnual,
    FactQcewCountyRollup,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Constants for GDP conversion
MILLIONS_TO_DOLLARS = 1_000_000
# QCEW average weekly wage = annual total wages / employment / 52 weeks.
WEEKS_PER_YEAR = 52.0


def _sector_codes_for(naics_2digit: str) -> list[str]:
    """Expand an adapter 2-digit NAICS label to ``dim_industry.sector_code`` values.

    Since spec-086 normalized ``fact_qcew_annual`` to 6-digit leaves only, a
    2-digit sector's employment is aggregated from the leaves whose
    ``sector_code`` matches. The three combined labels expand to their component
    sector codes.

    Args:
        naics_2digit: A 2-digit sector label from :data:`NAICS_2DIGIT_SECTORS`
            (e.g. ``"52"`` or a range like ``"31-33"``).

    Returns:
        The list of ``dim_industry.sector_code`` values that roll up to it.
    """
    ranges = {"31-33": ["31", "32", "33"], "44-45": ["44", "45"], "48-49": ["48", "49"]}
    return ranges.get(naics_2digit, [naics_2digit])


# NAICS codes for 2-digit sectors used in supply chain depth calculation
#
# Known pre-existing coverage gap (spec-098 review, unchanged by this PR):
# sector_code='99' ("Nonclassifiable establishments") is a real, populated
# QCEW sector (22k+ leaf rows) that is NOT included here, so its employment
# is silently excluded from get_county_employment_by_naics()/sector coverage
# metrics. This predates the spec-086/098 adapter fixes and is left as-is.
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

    Reads the post-spec-086 QCEW layout of ``marxist-data-3NF.sqlite``:

    - ``fact_qcew_annual`` holds ONLY 6-digit-NAICS leaves per ownership
      (spec-086 canonical grain). Sector employment/wages are therefore
      aggregated up from the leaves via ``dim_industry.sector_code``.
    - The county Total-Covered figure (``own_code='0'``) lives in the
      ``fact_qcew_county_rollup`` reconciliation table (spec-086), NOT in
      ``fact_qcew_annual`` — so ``get_county_total_employment`` reads the rollup.

    Ownership Codes:
        - own_code='0': Total all ownerships (in ``fact_qcew_county_rollup``).
        - own_code='5': Private sector (leaf breakdowns in ``fact_qcew_annual``).
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_ownership_id: int | None = None  # own_code='0'
        self._private_ownership_id: int | None = None  # own_code='5'

    def _get_total_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Total All' (own_code='0').

        Used for the county Total-Covered rollup lookup. Caches the result.
        """
        if self._total_ownership_id is None:
            total_own = session.query(DimOwnership).filter(DimOwnership.own_code == "0").first()
            if total_own:
                self._total_ownership_id = total_own.ownership_id
        return self._total_ownership_id

    def _get_private_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Private' (own_code='5').

        Used for sector-level leaf aggregation. Caches the result.
        """
        if self._private_ownership_id is None:
            private_own = session.query(DimOwnership).filter(DimOwnership.own_code == "5").first()
            if private_own:
                self._private_ownership_id = private_own.ownership_id
        return self._private_ownership_id

    def _get_county_id(self, session: Session, fips: str) -> int | None:
        """Get county_id for a FIPS code."""
        county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
        return county.county_id if county else None

    def _get_time_id(self, session: Session, year: int) -> int | None:
        """Get time_id for a year."""
        time_dim = session.query(DimTime).filter(DimTime.year == year).first()
        return time_dim.time_id if time_dim else None

    def get_county_naics_employment(self, fips: str, naics: str, year: int) -> int | None:
        """Get private-sector employment for a county-NAICS-sector combination.

        Aggregates the 6-digit leaves (own_code='5') whose
        ``dim_industry.sector_code`` rolls up to ``naics``, since spec-086 made
        ``fact_qcew_annual`` leaf-only. Combined labels (31-33, 44-45, 48-49)
        sum their component sectors.

        Args:
            fips: 5-character county FIPS code.
            naics: 2-digit NAICS sector label.
            year: Calendar year.

        Returns:
            Summed employment (persons), or None if unavailable.
        """
        with self._session_factory() as session:
            private_ownership_id = self._get_private_ownership_id(session)
            if private_ownership_id is None:
                logger.warning("QCEW 'Private' ownership (own_code='5') not found")
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            total = (
                session.query(func.sum(FactQcewAnnual.employment))
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == private_ownership_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(_sector_codes_for(naics)),
                )
                .scalar()
            )

            return int(total) if total is not None else None

    def get_county_employment_by_naics(self, fips: str, year: int) -> dict[str, int]:
        """Get private-sector employment by NAICS sector for a county.

        One grouped query over the 6-digit leaves (own_code='5'), folding each
        ``dim_industry.sector_code`` into its adapter label (combined labels
        31-33 / 44-45 / 48-49 sum their components).

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            Dict mapping NAICS sector labels to summed employment counts.
            A confirmed zero (a real SUM(employment)=0 leaf) is included
            with value 0; only sectors with no matching rows at all are
            excluded.
        """
        # sector_code -> adapter label (e.g. "31" -> "31-33")
        code_to_label = {
            code: label for label in NAICS_2DIGIT_SECTORS for code in _sector_codes_for(label)
        }
        with self._session_factory() as session:
            private_ownership_id = self._get_private_ownership_id(session)
            if private_ownership_id is None:
                return {}
            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return {}
            time_id = self._get_time_id(session, year)
            if time_id is None:
                return {}

            rows = (
                session.query(
                    DimIndustry.sector_code,
                    func.sum(FactQcewAnnual.employment),
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == private_ownership_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(list(code_to_label)),
                )
                .group_by(DimIndustry.sector_code)
                .all()
            )

        result: dict[str, int] = {}
        for sector_code, emp in rows:
            if emp is not None:
                label = code_to_label[sector_code]
                result[label] = result.get(label, 0) + int(emp)
        return result

    def get_county_total_employment(self, fips: str, year: int) -> int | None:
        """Get total (all-ownership) employment for a county.

        Reads the county Total-Covered figure (own_code='0') from
        ``fact_qcew_county_rollup`` — where spec-086 moved it out of the now
        leaf-only ``fact_qcew_annual``.

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

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            result = (
                session.query(FactQcewCountyRollup.employment)
                .filter(
                    FactQcewCountyRollup.county_id == county_id,
                    FactQcewCountyRollup.ownership_id == total_ownership_id,
                    FactQcewCountyRollup.time_id == time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return int(result[0])
            return None

    def get_county_naics_wages(self, fips: str, naics: str, year: int) -> float | None:
        """Get average weekly wage for a county-NAICS-sector combination.

        Computed as ``Σ(annual total wages) / Σ(employment) / 52`` over the
        private-sector (own_code='5') 6-digit leaves that roll up to ``naics``.
        This uses the fully-populated ``total_wages_usd`` + ``employment``
        columns, so it is robust to spec-086 imputation (which nulls the
        per-leaf ``avg_weekly_wage_usd``).

        Args:
            fips: 5-character county FIPS code.
            naics: 2-digit NAICS sector label.
            year: Calendar year.

        Returns:
            Average weekly wage ($/week), or None if unavailable.
        """
        with self._session_factory() as session:
            private_ownership_id = self._get_private_ownership_id(session)
            if private_ownership_id is None:
                return None

            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            wages, employment = (
                session.query(
                    func.sum(FactQcewAnnual.total_wages_usd),
                    func.sum(FactQcewAnnual.employment),
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.ownership_id == private_ownership_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(_sector_codes_for(naics)),
                )
                .one()
            )

            if wages is None or not employment:
                return None
            return float(wages) / float(employment) / WEEKS_PER_YEAR


__all__ = [
    "SQLiteBEACountyGDPSource",
    "SQLiteQCEWCountyNAICSSource",
    "NAICS_2DIGIT_SECTORS",
]
