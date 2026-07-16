"""SQLite adapters for national-level BEA and QCEW data sources.

Feature: 020-detroit-vertical-slice
Date: 2026-02-23

This module provides concrete implementations of the MELT data source
protocols that query the 3NF normalized database (marxist-data-3NF.sqlite).

These adapters provide *national-level* aggregates for MELT (tau) computation:
- BEA GDP: Total value added for all industries (national GDP)
- QCEW Employment: Total employment across all counties

Usage:
    from babylon.reference.database import get_normalized_session_factory
    from babylon.domain.economics.melt.adapters import (
        SQLiteBEANationalGDPSource,
        SQLiteQCEWNationalEmploymentSource,
    )

    session_factory = get_normalized_session_factory()
    bea = SQLiteBEANationalGDPSource(session_factory)
    qcew = SQLiteQCEWNationalEmploymentSource(session_factory)

    gdp = bea.get_gdp(2022)    # ~$26 trillion
    emp = qcew.get_national_employment(2022)  # ~151 million

See Also:
    :mod:`babylon.domain.economics.melt.data_sources`: BEADataSource, QCEWDataSource protocols
    :mod:`babylon.domain.economics.throughput.adapters`: County-level adapter pattern reference
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import func

from babylon.reference.schema import (
    DimBEAIndustry,
    DimFredSeries,
    DimOwnership,
    DimTime,
    FactBEACountyGDP,
    FactBEANationalIndustry,
    FactFredNational,
    FactQcewCountyRollup,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# GDP conversion: BEA stores values in millions of dollars
MILLIONS_TO_DOLLARS = 1_000_000


class SQLiteBEANationalGDPSource:
    """SQLite adapter implementing BEADataSource protocol for national GDP.

    Queries FactBEANationalIndustry for the 'All industries' row
    (line_number=1) to retrieve total value added (GDP).

    CRITICAL: Filters to line_number=1 to avoid double-counting from
    industry subtotals. Also filters to is_annual=1 to exclude quarterly data.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_industry_id: int | None = None
        # 2026-07-15 perf regression fix: get_gdp(year) is called once per
        # territory per tick (throughput calculator -> get_melt(year) for
        # the SAME year, every territory) — without this cache that is N
        # redundant DB round-trips per tick for an identical result. Keyed
        # by year (not a single scalar) so different years each still
        # resolve independently.
        self._gdp_cache: dict[int, float | None] = {}

    def _get_total_industry_id(self, session: Session) -> int | None:
        """Get bea_industry_id for 'All industries' (line_number=1).

        Caches the result for efficiency.
        """
        if self._total_industry_id is None:
            total_bea = (
                session.query(DimBEAIndustry).filter(DimBEAIndustry.line_number == 1).first()
            )
            if total_bea:
                self._total_industry_id = total_bea.bea_industry_id
        return self._total_industry_id

    def get_gdp(self, year: int) -> float | None:
        """Get national GDP for a given year.

        Tries FactBEANationalIndustry first (pre-aggregated national row).
        Falls back to SUM(FactBEACountyGDP.gdp_millions) when the national
        table is empty (common when only county-level BEA data was loaded).

        Cached per year (see ``__init__``) — a second call for a year
        already resolved returns the cached value without touching the
        database.

        Args:
            year: Calendar year (typically 2010-2023).

        Returns:
            GDP in current dollars, or None if data unavailable.
        """
        if year in self._gdp_cache:
            return self._gdp_cache[year]

        result = self._compute_gdp(year)
        self._gdp_cache[year] = result
        return result

    def _compute_gdp(self, year: int) -> float | None:
        """Uncached body of :meth:`get_gdp` — see there for the query strategy."""
        with self._session_factory() as session:
            total_industry_id = self._get_total_industry_id(session)
            if total_industry_id is None:
                logger.warning("BEA 'All industries' (line_number=1) not found")
                return None

            time_dim = (
                session.query(DimTime).filter(DimTime.year == year, DimTime.is_annual == 1).first()
            )
            if time_dim is None:
                return None

            # Primary: pre-aggregated national row
            result = (
                session.query(FactBEANationalIndustry.value_added_millions)
                .filter(
                    FactBEANationalIndustry.bea_industry_id == total_industry_id,
                    FactBEANationalIndustry.time_id == time_dim.time_id,
                )
                .first()
            )

            if result and result[0] is not None:
                return float(result[0]) * MILLIONS_TO_DOLLARS

            # Fallback: sum county GDP for 'All industries' (line_number=1)
            county_total = (
                session.query(func.sum(FactBEACountyGDP.gdp_millions))
                .filter(
                    FactBEACountyGDP.bea_industry_id == total_industry_id,
                    FactBEACountyGDP.time_id == time_dim.time_id,
                )
                .scalar()
            )

            if county_total is not None:
                logger.info(
                    "BEA national GDP derived from county sum for year %d",
                    year,
                )
                return float(county_total) * MILLIONS_TO_DOLLARS
            return None


class SQLiteQCEWNationalEmploymentSource:
    """SQLite adapter implementing QCEWDataSource protocol for national employment.

    Reads the post-spec-086 QCEW layout of ``marxist-data-3NF.sqlite``: the
    county Total-Covered figure (``own_code='0'``) lives in
    ``fact_qcew_county_rollup`` (spec-086), NOT in ``fact_qcew_annual`` (which
    holds 6-digit-leaf-only rows since spec-086). We SUM the rollup's
    per-county totals across all counties to produce the national aggregate.

    CRITICAL: ``fact_qcew_county_rollup`` has no industry dimension (it IS
    the county total row), so no industry filter is needed or possible.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_ownership_id: int | None = None
        # 2026-07-15 perf regression fix — see SQLiteBEANationalGDPSource's
        # identical ``_gdp_cache`` note: get_melt(year) is called once per
        # territory per tick, redundantly re-summing the same national
        # total every time absent this per-year cache.
        self._employment_cache: dict[int, int | None] = {}

    def _get_total_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Total All' (own_code='0').

        Caches the result for efficiency.
        """
        if self._total_ownership_id is None:
            total_own = session.query(DimOwnership).filter(DimOwnership.own_code == "0").first()
            if total_own:
                self._total_ownership_id = total_own.ownership_id
        return self._total_ownership_id

    def get_national_employment(self, year: int) -> int | None:
        """Get national employment total for a given year.

        SUMs the ``fact_qcew_county_rollup`` Total-Covered (own_code='0')
        row across all counties to produce the national aggregate.

        Cached per year (see ``__init__``) — a second call for a year
        already resolved returns the cached value without touching the
        database.

        Args:
            year: Calendar year (typically 2010-2023).

        Returns:
            Employment count (persons), or None if data unavailable.
        """
        if year in self._employment_cache:
            return self._employment_cache[year]

        result = self._compute_national_employment(year)
        self._employment_cache[year] = result
        return result

    def _compute_national_employment(self, year: int) -> int | None:
        """Uncached body of :meth:`get_national_employment` — see there for the query."""
        with self._session_factory() as session:
            total_ownership_id = self._get_total_ownership_id(session)
            if total_ownership_id is None:
                logger.warning("QCEW 'Total All' ownership (own_code='0') not found")
                return None

            time_dim = (
                session.query(DimTime).filter(DimTime.year == year, DimTime.is_annual == 1).first()
            )
            if time_dim is None:
                return None

            result = (
                session.query(func.sum(FactQcewCountyRollup.employment))
                .filter(
                    FactQcewCountyRollup.ownership_id == total_ownership_id,
                    FactQcewCountyRollup.time_id == time_dim.time_id,
                )
                .scalar()
            )

            if result is not None:
                return int(result)
            return None


#: Default deflation base year for :meth:`SQLiteCPISource.get_cpi_deflator`.
#: 2015 matches this codebase's de facto reference year (the example/seed year
#: used throughout ``tick/types.py`` docstrings, ``initializer.py``'s example,
#: and ``gamma/adapters.py``'s care-hours anchor) rather than introducing a new
#: arbitrary base. Distinct from ``melt.data_sources.CPIDataSource``'s 2024
#: ``CPI_BASE_YEAR`` (still unwired) — that protocol serves a different
#: consumer (the $12/hr Census-poverty ``V_reproduction`` floor, anchored to
#: *current* 2024 dollars); this one serves the real-wage series (Wave 6 C4).
CPI_DEFLATOR_BASE_YEAR: int = 2015


class SQLiteCPISource:
    """SQLite adapter for CPIAUCSL-based real-wage deflation (Wave 6 C4).

    Epochs audit Wave 6 item C4 ("Real-wage CPI deflation series — closes the
    'wages never naked' gap"): every wage/wealth figure the tick pipeline has
    produced so far is nominal-only. This adapter reads the FRED CPIAUCSL
    series already loaded in ``fact_fred_national``/``dim_fred_series`` (see
    ``sqlite_hydrator._copy_fred`` for the identical AVG-across-months-in-year
    convention) and exposes a base-year deflator so a nominal county wage can
    be converted to base-year real dollars: ``real = nominal * deflator``.

    Distinct from ``babylon.domain.economics.melt.data_sources.CPIDataSource``
    (a still-unwired protocol for the 2024-based ``V_reproduction`` subsistence
    floor) — this class is the Wave 6 C4-specific, 2015-based real-wage series
    consumer, wired via ``services.cpi_source``.

    Usage:
        >>> cpi = SQLiteCPISource(session_factory)
        >>> cpi.get_annual_cpi(2015)
        237.02  # CPIAUCSL index (base 1982-84=100), avg of monthly rows
        >>> cpi.get_cpi_deflator(2011)
        1.0876...  # multiply a 2011 nominal wage by this for 2015-real dollars
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        # Per-year cache — mirrors SQLiteBEANationalGDPSource/
        # SQLiteQCEWNationalEmploymentSource's caches above (2026-07-15 perf
        # fix): get_cpi_deflator(year) queries both `year` and the base year
        # every call, and the tick pipeline calls it once per county per
        # year-boundary tick — an uncached adapter would re-run the identical
        # AVG query for the base year on every county, every tick.
        self._cpi_cache: dict[int, float | None] = {}

    def get_annual_cpi(self, year: int) -> float | None:
        """Get the annual-average CPIAUCSL index value for a given year.

        Averages every ``fact_fred_national`` CPIAUCSL row joined to
        ``dim_time.year == year`` — the same AVG-across-months convention
        ``sqlite_hydrator._copy_fred`` uses to derive its annual MELT proxy.

        Args:
            year: Calendar year.

        Returns:
            The average CPIAUCSL index value for ``year``, or ``None`` when
            no CPIAUCSL row exists for that year (honest absence, never a
            fabricated index — Constitution III.11).
        """
        if year in self._cpi_cache:
            return self._cpi_cache[year]

        result = self._compute_annual_cpi(year)
        self._cpi_cache[year] = result
        return result

    def _compute_annual_cpi(self, year: int) -> float | None:
        """Uncached body of :meth:`get_annual_cpi` — see there for the query."""
        with self._session_factory() as session:
            avg_value = (
                session.query(func.avg(FactFredNational.value))
                .join(DimFredSeries, DimFredSeries.series_id == FactFredNational.series_id)
                .join(DimTime, DimTime.time_id == FactFredNational.time_id)
                .filter(DimFredSeries.series_code == "CPIAUCSL", DimTime.year == year)
                .scalar()
            )
            if avg_value is None:
                return None
            return float(avg_value)

    def get_cpi_deflator(self, year: int, base_year: int = CPI_DEFLATOR_BASE_YEAR) -> float | None:
        """Get the base-year real-wage deflator for ``year``.

        ``deflator = CPI(base_year) / CPI(year)`` — multiplying a nominal
        ``year``-dollar wage by this converts it to ``base_year``-real dollars
        (a wage that grew only with inflation carries a deflator of 1.0 at
        every year once graphed against itself).

        Args:
            year: Calendar year to deflate.
            base_year: Reference year real dollars are expressed in (default
                :data:`CPI_DEFLATOR_BASE_YEAR`, 2015).

        Returns:
            The deflator ratio, or ``None`` when either year's CPI is
            unavailable or ``CPI(year) == 0`` (division-by-zero guard) —
            honest ``None``, never a fabricated ratio.
        """
        cpi_year = self.get_annual_cpi(year)
        cpi_base = self.get_annual_cpi(base_year)
        if cpi_year is None or cpi_base is None or cpi_year == 0:
            return None
        return cpi_base / cpi_year


__all__ = [
    "CPI_DEFLATOR_BASE_YEAR",
    "SQLiteBEANationalGDPSource",
    "SQLiteCPISource",
    "SQLiteQCEWNationalEmploymentSource",
]
