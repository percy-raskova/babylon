"""SQLite adapters for throughput position data sources.

This module provides concrete implementations of the data source protocols
that query the 3NF normalized database (marxist-data-3NF.sqlite).

Feature: 014-throughput-position
Date: 2026-02-02

Usage:
    from babylon.reference.database import get_normalized_session_factory
    from babylon.domain.economics.throughput.adapters import (
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

from babylon.formulas.constants import HOURS_PER_YEAR, WEEKS_PER_YEAR
from babylon.reference.schema import (
    DimBEAIndustry,
    DimCounty,
    DimIncomeBracket,
    DimIndustry,
    DimOwnership,
    DimRace,
    DimTime,
    FactBEACountyGDP,
    FactBLSUnemploymentDecomposition,
    FactCensusIncome,
    FactQcewAnnual,
    FactQcewCountyRollup,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Constants for GDP conversion
MILLIONS_TO_DOLLARS = 1_000_000
# QCEW average weekly wage = annual total wages / employment / 52 weeks.


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

            # 2026-07-15 perf regression fix: filtering ``ownership_id`` as a
            # SQL equality predicate (alongside county_id/time_id) makes
            # SQLite's planner favor the low-selectivity single-column
            # ``idx_qcew_ownership`` over the far more selective
            # ``idx_qcew_county_time`` — a ~1.3s scan per call on the
            # 14.6M-row table instead of <1ms (measured; own_code='5'/'0'
            # alone each cover millions of rows nationwide). Filtering
            # ownership + sector client-side over the tiny (county, time)
            # row set (~hundreds of rows) sidesteps the ambiguous index
            # choice entirely rather than depending on planner heuristics.
            sector_codes = set(_sector_codes_for(naics))
            rows = (
                session.query(
                    FactQcewAnnual.ownership_id,
                    DimIndustry.sector_code,
                    FactQcewAnnual.employment,
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(sector_codes),
                )
                .all()
            )

        non_null_emp = [
            int(emp)
            for own_id, sector_code, emp in rows
            if own_id == private_ownership_id and sector_code in sector_codes and emp is not None
        ]
        # Mirrors SQL SUM(): NULL (-> None) only when there is nothing to
        # sum, never conflated with a real zero (spec-098 regression class).
        return sum(non_null_emp) if non_null_emp else None

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

            # 2026-07-15 perf regression fix: see the identical note in
            # get_county_naics_employment() above — filtering ownership_id
            # in SQL here misled SQLite into the same ~1.3s-per-call bad
            # index choice (81 territories x this call was the dominant
            # cost of the ~300s resolve-tick regression). Group in Python
            # instead, over the small (county, time) row set.
            rows = (
                session.query(
                    FactQcewAnnual.ownership_id,
                    DimIndustry.sector_code,
                    FactQcewAnnual.employment,
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(list(code_to_label)),
                )
                .all()
            )

        result: dict[str, int] = {}
        for own_id, sector_code, emp in rows:
            if own_id != private_ownership_id or emp is None:
                continue
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

            # 2026-07-15 perf regression fix: see the identical note in
            # get_county_naics_employment() above.
            sector_codes = set(_sector_codes_for(naics))
            rows = (
                session.query(
                    FactQcewAnnual.ownership_id,
                    DimIndustry.sector_code,
                    FactQcewAnnual.total_wages_usd,
                    FactQcewAnnual.employment,
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.sector_code.in_(sector_codes),
                )
                .all()
            )

        matching = [
            (w, e)
            for own_id, sector_code, w, e in rows
            if own_id == private_ownership_id and sector_code in sector_codes
        ]
        non_null_wages = [w for w, _e in matching if w is not None]
        non_null_emp = [e for _w, e in matching if e is not None]
        # Mirrors the original two independent SQL SUM()s: NULL (-> None)
        # only when there is nothing to sum.
        wages = sum(non_null_wages) if non_null_wages else None
        employment = sum(non_null_emp) if non_null_emp else None

        if wages is None or not employment:
            return None
        return float(wages) / float(employment) / WEEKS_PER_YEAR

    def get_county_median_hourly_wage(self, fips: str, year: int) -> float | None:
        """Employment-weighted median hourly wage across 6-digit industries.

        Owner-queue item 60: the p50 of the county's employment distribution
        sorted by industry mean wage — walk the QCEW leaves from
        lowest-paid to highest-paid and take the industry where cumulative
        employment crosses 50%. A genuine median ESTIMATOR (within-industry
        dispersion is invisible; every worker is assigned their industry's
        mean), the same p50 the class-shares hydration computes
        (``engine.hydration.reference.hydrate_class_shares``) — unlike the
        raw county mean, which is not a median at all.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            Median hourly wage ($/hr), or None when the county, year, or
            usable leaves are absent (honest None, Constitution III.11).
        """
        with self._session_factory() as session:
            county_id = self._get_county_id(session, fips)
            if county_id is None:
                return None

            time_id = self._get_time_id(session, year)
            if time_id is None:
                return None

            rows = (
                session.query(
                    FactQcewAnnual.total_wages_usd,
                    FactQcewAnnual.employment,
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .filter(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.time_id == time_id,
                    DimIndustry.naics_level == 6,
                    FactQcewAnnual.employment > 0,
                    FactQcewAnnual.total_wages_usd.isnot(None),
                )
                .order_by((FactQcewAnnual.total_wages_usd / FactQcewAnnual.employment).asc())
                .all()
            )

        total_emp = sum(float(e) for _w, e in rows)
        if total_emp <= 0.0:
            return None
        cumulative = 0.0
        for wages_usd, emp in rows:
            cumulative += float(emp)
            if cumulative / total_emp >= 0.5:
                return float(wages_usd) / float(emp) / HOURS_PER_YEAR
        return None


__all__ = [
    "SQLiteBEACountyGDPSource",
    "SQLiteBLSUnemploymentSource",
    "SQLiteCensusIncomeSource",
    "SQLiteQCEWCountyNAICSSource",
    "NAICS_2DIGIT_SECTORS",
]


class SQLiteBLSUnemploymentSource:
    """County U-3 unemployment rate from BLS LAUS (labor-data wire, 2026-07-15).

    Mirrors :class:`SQLiteQCEWCountyNAICSSource`'s Fix-C pattern: real
    per-county data behind an optional services override
    (``services.unemployment_source``), consumed by the tick pipeline in
    place of the frozen ``0.05`` placeholder. Honest ``None`` when the
    county-year row is absent — never a fabricated rate (Constitution
    III.11). Only the U-3 column is trustworthy in the reference DB (the
    U-6/PTER/discouraged decomposition columns are all zero); this source
    deliberately exposes U-3 alone.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Store the SQLAlchemy session factory (shared with the other adapters)."""
        self._session_factory = session_factory

    def get_county_unemployment_rate(self, fips: str, year: int) -> float | None:
        """U-3 rate = ``unemployed_u3 / labor_force`` for a county-year.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            The U-3 unemployment rate in [0, 1], or ``None`` when the
            county, year, or row is absent or the labor force is zero.
        """
        with self._session_factory() as session:
            county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
            if county is None:
                return None
            time_dim = session.query(DimTime).filter(DimTime.year == year).first()
            if time_dim is None:
                return None

            row = (
                session.query(
                    FactBLSUnemploymentDecomposition.unemployed_u3,
                    FactBLSUnemploymentDecomposition.labor_force,
                )
                .filter(
                    FactBLSUnemploymentDecomposition.county_id == county.county_id,
                    FactBLSUnemploymentDecomposition.time_id == time_dim.time_id,
                )
                .first()
            )
            if row is None or row[1] is None or row[1] <= 0 or row[0] is None:
                return None
            return float(row[0]) / float(row[1])


# Wave 6 C3 (epochs audit item 167): fact_census_income (ACS table B19001,
# household income distribution) has 16 real brackets
# (dim_income_bracket.bracket_order 1-16, fine-grained — no natural
# top-decile/bottom-decile split) plus a 17th "NAM" ("Geographic Area Name")
# metadata row that is never a household count. Per the audit's guidance for
# fine-grained brackets, the ratio uses the top ~2 vs bottom ~2 bands — see
# SQLiteCensusIncomeSource's docstring for the full rationale.
_BOTTOM_BRACKET_ORDERS: tuple[int, ...] = (1, 2)  # "<$10,000", "$10,000-$14,999"
_TOP_BRACKET_ORDERS: tuple[int, ...] = (15, 16)  # "$150,000-$199,999", "$200,000+"


class SQLiteCensusIncomeSource:
    """County top/bottom income-bracket household ratio from ACS B19001 (Wave 6 C3).

    ``fact_census_income`` stores ACS household-income-distribution counts
    per (county, bracket, year, race); the epochs audit (item 167) flagged
    that this table had been "collapsed to SUM" with no bracket-aware reader.
    This adapter computes an inequality PROXY: the ratio of households in the
    TOP income band to households in the BOTTOM income band.

    Band choice (documented per the audit's instruction to choose deliberately
    when brackets are fine-grained):

    - The reference DB carries 16 real brackets (``dim_income_bracket
      .bracket_order`` 1-16, ACS table B19001) plus a 17th ``NAM``
      ("Geographic Area Name") row that is metadata, not a household count —
      excluded by construction since only orders 1/2/15/16 are ever queried.
    - BOTTOM band = bracket_order ``{1, 2}``: "Less than $10,000" +
      "$10,000 to $14,999".
    - TOP band = bracket_order ``{15, 16}``: "$150,000 to $199,999" +
      "$200,000 or more".
    - 16 bands is too fine-grained for a natural top-decile/bottom-decile
      split, so this reader takes the top ~2 / bottom ~2 bands (a symmetric
      2-band window at each extreme) — wide enough that a single narrow
      bracket doesn't dominate the ratio, narrow enough to stay a genuine
      "extremes" comparison rather than a median-adjacent one.

    Race handling: ``fact_census_income`` carries one row per ``dim_race``
    category (10 total) per county-bracket-year. This adapter filters to
    ``race_code='T'`` ("Total (all races, base table)" — the Census-provided
    CROSS-RACE aggregate already computed upstream) rather than summing all
    10 race rows: race_id 2-8 (the mutually-exclusive "alone" categories)
    already sum to the Total, and race_id 9-10 (Hispanic-ethnicity-crossed
    views) overlap 2-8, so a naive SUM over every race row would double- or
    triple-count. This mirrors :class:`SQLiteQCEWCountyNAICSSource`'s own
    convention of reading the designated "Total" dimension member
    (``own_code='0'``) rather than summing every category.

    Note: this is a household-COUNT ratio (relative population sizes in each
    band), a distinct notion from an income-LEVEL percentile ratio (e.g.
    P90/P10) — it answers "how many top-band households per bottom-band
    household", not "how many times richer is the top decile than the
    bottom". That is the audit's chosen proxy (item 167); flagged here
    rather than silently presented as the latter.

    Query shape: filters SQL-side only on ``county_id``/``time_id`` (both
    individually indexed and, combined, narrow ``fact_census_income`` down to
    ~170 rows — 17 brackets x 10 races) and filters ``race_id``/bracket band
    in Python from that small fetched set. ``race_id`` is deliberately NOT a
    SQL equality predicate: with only 10 distinct values across 7.2M rows
    (the largest census table), it is exactly the low-selectivity-index
    hazard :meth:`SQLiteQCEWCountyNAICSSource.get_county_naics_employment`
    was fixed for (2026-07-15 perf regression: SQLite's planner favors a
    low-selectivity single-column index over a more selective one when it
    appears as an equality predicate) — a value like ``race_code='T'``
    covers roughly 720k rows nationwide, the same order of magnitude as the
    QCEW ``own_code`` hazard.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Store the SQLAlchemy session factory (shared with the other adapters)."""
        self._session_factory = session_factory
        self._total_race_id: int | None = None
        self._bracket_order_by_id: dict[int, int] | None = None

    def _get_total_race_id(self, session: Session) -> int | None:
        """Get race_id for 'Total (all races)' (race_code='T'). Caches the result."""
        if self._total_race_id is None:
            race_total = session.query(DimRace).filter(DimRace.race_code == "T").first()
            if race_total is not None:
                self._total_race_id = race_total.race_id
        return self._total_race_id

    def _get_bracket_order_by_id(self, session: Session) -> dict[int, int]:
        """Get the ``bracket_id -> bracket_order`` map. Caches the result."""
        if self._bracket_order_by_id is None:
            self._bracket_order_by_id = {
                int(bracket_id): int(bracket_order)
                for bracket_id, bracket_order in session.query(
                    DimIncomeBracket.bracket_id, DimIncomeBracket.bracket_order
                ).all()
            }
        return self._bracket_order_by_id

    def get_county_bracket_ratio(self, fips: str, year: int) -> float | None:
        """Top-band / bottom-band household ratio for a county-year.

        Args:
            fips: 5-character county FIPS code.
            year: Calendar year.

        Returns:
            The top/bottom household-count ratio, or ``None`` when the
            county, year, or race="Total" row is absent, or when the
            bottom-band count is zero or absent (undefined ratio).
        """
        with self._session_factory() as session:
            county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
            if county is None:
                return None
            time_dim = session.query(DimTime).filter(DimTime.year == year).first()
            if time_dim is None:
                return None
            total_race_id = self._get_total_race_id(session)
            if total_race_id is None:
                return None
            bracket_order_by_id = self._get_bracket_order_by_id(session)

            rows = (
                session.query(
                    FactCensusIncome.race_id,
                    FactCensusIncome.bracket_id,
                    FactCensusIncome.household_count,
                )
                .filter(
                    FactCensusIncome.county_id == county.county_id,
                    FactCensusIncome.time_id == time_dim.time_id,
                )
                .all()
            )

        bottom = 0
        top = 0
        for race_id, bracket_id, household_count in rows:
            if race_id != total_race_id or household_count is None:
                continue
            order = bracket_order_by_id.get(bracket_id)
            if order in _BOTTOM_BRACKET_ORDERS:
                bottom += int(household_count)
            elif order in _TOP_BRACKET_ORDERS:
                top += int(household_count)

        if bottom <= 0:
            return None
        return float(top) / float(bottom)
