"""SQLite adapter for LODES commuter flow data.

This module provides the concrete implementation of LODESCommuterFlowSource
that queries the FactLodesCommuterFlow table in the 3NF database.

Feature: 014-throughput-position (T034-T036)
Date: 2026-02-03

Usage:
    from babylon.data.reference.database import get_normalized_session_factory
    from babylon.economics.throughput.adapters_lodes import SQLiteLODESCommuterFlowSource

    session_factory = get_normalized_session_factory()
    lodes_source = SQLiteLODESCommuterFlowSource(session_factory)

    # Get net commuter balance for Oakland County
    balance = lodes_source.get_net_commuter_balance("26125", 2022)
    if balance is not None:
        print(f"Oakland County is a job {'importer' if balance > 0 else 'exporter'}")
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from babylon.data.reference.schema import (
    DimCounty,
    DimTime,
    FactLodesCommuterFlow,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Flag to log the missing-table warning only once per process
_LODES_TABLE_MISSING_WARNED: bool = False


class SQLiteLODESCommuterFlowSource:
    """SQLite adapter implementing LODESCommuterFlowSource protocol.

    Queries FactLodesCommuterFlow table for county-to-county commuter flows.
    Pre-aggregated at load time for query performance.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory
        # Cache lookups for efficiency
        self._county_id_cache: dict[str, int | None] = {}
        self._time_id_cache: dict[int, int | None] = {}

    def _handle_missing_table(self) -> None:
        """Log a warning once if the LODES table is missing."""
        global _LODES_TABLE_MISSING_WARNED  # noqa: PLW0603
        if not _LODES_TABLE_MISSING_WARNED:
            logger.warning(
                "fact_lodes_commuter_flow table not found. "
                "Run 'mise run data:lodes-od' to load LODES data."
            )
            _LODES_TABLE_MISSING_WARNED = True

    def _get_county_id(self, session: Session, fips: str) -> int | None:
        """Get county_id for a FIPS code, with caching."""
        if fips not in self._county_id_cache:
            county = session.query(DimCounty).filter(DimCounty.fips == fips).first()
            self._county_id_cache[fips] = county.county_id if county else None
        return self._county_id_cache[fips]

    def _get_time_id(self, session: Session, year: int) -> int | None:
        """Get time_id for a year (annual), with caching."""
        if year not in self._time_id_cache:
            time_dim = (
                session.query(DimTime)
                .filter(DimTime.year == year, DimTime.is_annual.is_(True))
                .first()
            )
            self._time_id_cache[year] = time_dim.time_id if time_dim else None
        return self._time_id_cache[year]

    def get_inbound_commuters(self, work_fips: str, year: int) -> int | None:
        """Get total workers commuting INTO this county for work.

        Sums flows where work_county = this county AND home_county != this county.

        Args:
            work_fips: 5-character FIPS code of work county
            year: Calendar year

        Returns:
            Count of inbound commuters, or None if no data available
        """
        try:
            with self._session_factory() as session:
                work_county_id = self._get_county_id(session, work_fips)
                if work_county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                result = (
                    session.query(func.sum(FactLodesCommuterFlow.total_jobs))
                    .filter(
                        FactLodesCommuterFlow.work_county_id == work_county_id,
                        FactLodesCommuterFlow.home_county_id != work_county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None

    def get_outbound_commuters(self, home_fips: str, year: int) -> int | None:
        """Get total workers commuting OUT of this county for work.

        Sums flows where home_county = this county AND work_county != this county.

        Args:
            home_fips: 5-character FIPS code of residence county
            year: Calendar year

        Returns:
            Count of outbound commuters, or None if no data available
        """
        try:
            with self._session_factory() as session:
                home_county_id = self._get_county_id(session, home_fips)
                if home_county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                result = (
                    session.query(func.sum(FactLodesCommuterFlow.total_jobs))
                    .filter(
                        FactLodesCommuterFlow.home_county_id == home_county_id,
                        FactLodesCommuterFlow.work_county_id != home_county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None

    def get_internal_workers(self, fips: str, year: int) -> int | None:
        """Get workers who both live and work in this county.

        Queries flow where home_county = work_county = this county.

        Args:
            fips: 5-character FIPS code
            year: Calendar year

        Returns:
            Count of internal workers, or None if no data available
        """
        try:
            with self._session_factory() as session:
                county_id = self._get_county_id(session, fips)
                if county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                result = (
                    session.query(FactLodesCommuterFlow.total_jobs)
                    .filter(
                        FactLodesCommuterFlow.home_county_id == county_id,
                        FactLodesCommuterFlow.work_county_id == county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None

    def get_net_commuter_balance(self, fips: str, year: int) -> int | None:
        """Get net commuter balance for a county.

        Formula: Inbound - Outbound
        - Positive: County is a NET JOB IMPORTER (more workers commute in)
        - Negative: County is a NET JOB EXPORTER (more workers commute out)

        Args:
            fips: 5-character FIPS code
            year: Calendar year

        Returns:
            Net commuter balance (can be negative), or None if unavailable
        """
        inbound = self.get_inbound_commuters(fips, year)
        outbound = self.get_outbound_commuters(fips, year)

        if inbound is None or outbound is None:
            return None

        return inbound - outbound

    def get_residence_employment(self, fips: str, year: int) -> int | None:
        """Get employment based on worker residence (not workplace).

        Formula: Internal + Outbound = workers who LIVE in this county.
        This differs from QCEW employment which counts jobs LOCATED in county.

        Args:
            fips: 5-character FIPS code
            year: Calendar year

        Returns:
            Residence-based employment count, or None if unavailable
        """
        try:
            with self._session_factory() as session:
                home_county_id = self._get_county_id(session, fips)
                if home_county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                # Sum all jobs where this county is the HOME county (worker lives here)
                result = (
                    session.query(func.sum(FactLodesCommuterFlow.total_jobs))
                    .filter(
                        FactLodesCommuterFlow.home_county_id == home_county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None

    def get_workplace_employment(self, fips: str, year: int) -> int | None:
        """Get employment based on workplace location.

        Formula: Internal + Inbound = jobs LOCATED in this county.
        This should match QCEW employment conceptually (both count jobs by location).

        Args:
            fips: 5-character FIPS code
            year: Calendar year

        Returns:
            Workplace-based employment count, or None if unavailable
        """
        try:
            with self._session_factory() as session:
                work_county_id = self._get_county_id(session, fips)
                if work_county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                # Sum all jobs where this county is the WORK county (job is here)
                result = (
                    session.query(func.sum(FactLodesCommuterFlow.total_jobs))
                    .filter(
                        FactLodesCommuterFlow.work_county_id == work_county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None

    def get_commuter_flows(self, home_fips: str, work_fips: str, year: int) -> int | None:
        """Get commuter flow between specific county pair.

        Args:
            home_fips: 5-character FIPS code of residence county
            work_fips: 5-character FIPS code of work county
            year: Calendar year

        Returns:
            Count of workers living in home_fips working in work_fips,
            or None if unavailable
        """
        try:
            with self._session_factory() as session:
                home_county_id = self._get_county_id(session, home_fips)
                if home_county_id is None:
                    return None

                work_county_id = self._get_county_id(session, work_fips)
                if work_county_id is None:
                    return None

                time_id = self._get_time_id(session, year)
                if time_id is None:
                    return None

                result = (
                    session.query(FactLodesCommuterFlow.total_jobs)
                    .filter(
                        FactLodesCommuterFlow.home_county_id == home_county_id,
                        FactLodesCommuterFlow.work_county_id == work_county_id,
                        FactLodesCommuterFlow.time_id == time_id,
                    )
                    .scalar()
                )

                return int(result) if result is not None else None
        except OperationalError:
            self._handle_missing_table()
            return None


__all__ = ["SQLiteLODESCommuterFlowSource"]
