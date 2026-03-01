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
    from babylon.economics.melt.adapters import (
        SQLiteBEANationalGDPSource,
        SQLiteQCEWNationalEmploymentSource,
    )

    session_factory = get_normalized_session_factory()
    bea = SQLiteBEANationalGDPSource(session_factory)
    qcew = SQLiteQCEWNationalEmploymentSource(session_factory)

    gdp = bea.get_gdp(2022)    # ~$26 trillion
    emp = qcew.get_national_employment(2022)  # ~151 million

See Also:
    :mod:`babylon.economics.melt.data_sources`: BEADataSource, QCEWDataSource protocols
    :mod:`babylon.economics.throughput.adapters`: County-level adapter pattern reference
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import func

from babylon.reference.schema import (
    DimBEAIndustry,
    DimIndustry,
    DimOwnership,
    DimTime,
    FactBEANationalIndustry,
    FactQcewAnnual,
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

        Args:
            year: Calendar year (typically 2010-2023).

        Returns:
            GDP in current dollars, or None if data unavailable.
        """
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
            return None


class SQLiteQCEWNationalEmploymentSource:
    """SQLite adapter implementing QCEWDataSource protocol for national employment.

    Queries FactQcewAnnual with own_code='0' (total all ownerships) and
    naics_code='10' (total all industries) to retrieve total employment,
    then SUMs across all counties to produce the national aggregate.

    CRITICAL: own_code='0' + naics_code='10' is the QCEW convention for
    total-of-all employment at the county level. We SUM across counties
    to produce the national aggregate.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        self._total_ownership_id: int | None = None
        self._total_industry_id: int | None = None

    def _get_total_ownership_id(self, session: Session) -> int | None:
        """Get ownership_id for 'Total All' (own_code='0').

        Caches the result for efficiency.
        """
        if self._total_ownership_id is None:
            total_own = session.query(DimOwnership).filter(DimOwnership.own_code == "0").first()
            if total_own:
                self._total_ownership_id = total_own.ownership_id
        return self._total_ownership_id

    def _get_total_industry_id(self, session: Session) -> int | None:
        """Get industry_id for 'Total' industry (naics_code='10').

        Caches the result for efficiency.
        """
        if self._total_industry_id is None:
            total_ind = session.query(DimIndustry).filter(DimIndustry.naics_code == "10").first()
            if total_ind:
                self._total_industry_id = total_ind.industry_id
        return self._total_industry_id

    def get_national_employment(self, year: int) -> int | None:
        """Get national employment total for a given year.

        SUMs employment across all counties where own_code='0' and
        naics_code='10' to produce the national aggregate.

        Args:
            year: Calendar year (typically 2010-2023).

        Returns:
            Employment count (persons), or None if data unavailable.
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

            time_dim = (
                session.query(DimTime).filter(DimTime.year == year, DimTime.is_annual == 1).first()
            )
            if time_dim is None:
                return None

            result = (
                session.query(func.sum(FactQcewAnnual.employment))
                .filter(
                    FactQcewAnnual.ownership_id == total_ownership_id,
                    FactQcewAnnual.industry_id == total_industry_id,
                    FactQcewAnnual.time_id == time_dim.time_id,
                )
                .scalar()
            )

            if result is not None:
                return int(result)
            return None


__all__ = [
    "SQLiteBEANationalGDPSource",
    "SQLiteQCEWNationalEmploymentSource",
]
