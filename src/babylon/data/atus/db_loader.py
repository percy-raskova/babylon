"""Database-backed ATUS loader implementing ReproductionLoaderProtocol.

This module provides ATUSDBLoader, which reads reproductive labor data from
the normalized 3NF database and satisfies the ReproductionLoaderProtocol
interface for ShadowLaborService.

**Data Flow:**

    seed_data.yaml -> ATUSReferenceLoader -> Database -> ATUSDBLoader -> ShadowLaborService

**Key Differences from MockReproductionLoader:**

1. Reads from database instead of returning hardcoded values
2. Supports year-specific queries (time dimension)
3. Aggregates across ATUS categories to Babylon categories
4. Returns breakdown by category in ATUSHouseholdSummary

**Current Limitation:**

County variation is not implemented (ATUS sample size too small).
All queries return national averages regardless of FIPS code.

See Also:
    :mod:`babylon.data.atus.loader`: ATUSReferenceLoader populates database.
    :mod:`babylon.data.atus.protocol`: Protocol definition.
    :mod:`babylon.economics.shadow_labor`: Consumer of this loader.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func

from babylon.config.defines import GameDefines
from babylon.data.atus.models import ATUSHouseholdSummary
from babylon.data.atus.protocol import ReproductionLoaderProtocol
from babylon.data.reference.schema import (
    DimATUSActivityCategory,
    DimGender,
    DimTime,
    FactATUSReproductiveLabor,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ATUSDBLoader(ReproductionLoaderProtocol):
    """Database-backed ATUS loader for reproductive labor data.

    Reads from fact_atus_reproductive_labor and satisfies the
    ReproductionLoaderProtocol interface for ShadowLaborService.

    **Query Strategy:**

    1. Filter by year (time_id) - matches requested year or closest
    2. Filter by gender (Total) for population averages
    3. Aggregate categories to get total unpaid hours
    4. Return ATUSHouseholdSummary with breakdown

    **Shadow Wage:**

    Returns shadow wage from GameDefines (configurable per simulation).
    Future versions may support regional wage variation.

    Args:
        session: SQLAlchemy session for database queries.
        defines: GameDefines for shadow wage lookup.

    Example:
        >>> from babylon.data.reference.database import get_normalized_session_factory
        >>> from babylon.config.defines import GameDefines
        >>> session_factory = get_normalized_session_factory()
        >>> with session_factory() as session:
        ...     loader = ATUSDBLoader(session, GameDefines())
        ...     summary = loader.load_county_summary("06001", 2022)
        ...     summary.unpaid_care_hours_weekly
        12.95
    """

    def __init__(
        self,
        session: Session,
        defines: GameDefines | None = None,
    ) -> None:
        """Initialize database loader.

        Args:
            session: SQLAlchemy session for queries.
            defines: GameDefines for configuration (default creates new).
        """
        self._session = session
        self._defines = defines if defines is not None else GameDefines()
        self._gender_total_id: int | None = None

    def load_county_summary(
        self,
        fips_code: str,
        year: int,
    ) -> ATUSHouseholdSummary:
        """Load reproductive labor summary from database.

        Returns national averages (county variation not implemented).
        Queries fact_atus_reproductive_labor for the specified year.

        Args:
            fips_code: 5-digit FIPS county code (passed through to result).
            year: Data year for time dimension lookup.

        Returns:
            ATUSHouseholdSummary with aggregated reproductive labor hours.

        Raises:
            ValueError: If year is before ATUS started (2003).
        """
        if year < 2003:
            msg = f"ATUS data not available before 2003 (requested: {year})"
            raise ValueError(msg)

        # Get time_id for the requested year
        time_id = self._get_time_id(year)
        if time_id is None:
            # Fall back to most recent available year
            time_id = self._get_most_recent_time_id()
            if time_id is None:
                # No data loaded - return zeros
                return ATUSHouseholdSummary(
                    fips_code=fips_code,
                    year=year,
                    total_reproductive_hours_weekly=0.0,
                    unpaid_care_hours_weekly=0.0,
                    paid_care_hours_weekly=0.0,
                )

        # Get gender_id for "Total"
        gender_total_id = self._get_gender_total_id()
        if gender_total_id is None:
            # Gender dimension not populated
            return ATUSHouseholdSummary(
                fips_code=fips_code,
                year=year,
                total_reproductive_hours_weekly=0.0,
                unpaid_care_hours_weekly=0.0,
                paid_care_hours_weekly=0.0,
            )

        # Query total hours across all categories for "Total" gender
        total_hours = self._query_total_hours(time_id, gender_total_id)

        # All ATUS hours are unpaid in our model
        # (paid care would come from a different source)
        return ATUSHouseholdSummary(
            fips_code=fips_code,
            year=year,
            total_reproductive_hours_weekly=float(total_hours),
            unpaid_care_hours_weekly=float(total_hours),
            paid_care_hours_weekly=0.0,
        )

    def get_shadow_wage(
        self,
        fips_code: str,  # noqa: ARG002 - future: regional wage variation
        year: int,  # noqa: ARG002 - future: inflation adjustment
    ) -> float:
        """Get shadow wage from GameDefines.

        Returns the shadow wage (replacement cost) for unpaid care work.
        Currently returns a national average from configuration.

        Args:
            fips_code: 5-digit FIPS county code (unused, for future).
            year: Data year (unused, for future inflation adjustment).

        Returns:
            Hourly wage rate for shadow labor valuation (USD/hour).
        """
        return self._defines.economy.shadow_wage_hourly

    def get_hours_by_category(
        self,
        year: int,
        gender_code: str = "T",
    ) -> dict[str, float]:
        """Get reproductive labor hours breakdown by Babylon category.

        Returns hours_per_week for each category (housework, cooking, etc.).
        Useful for detailed analysis beyond the aggregate summary.

        Args:
            year: Data year for time dimension.
            gender_code: Gender code ("T" for total, "M", "F").

        Returns:
            Dict mapping babylon_category to hours_per_week.
        """
        time_id = self._get_time_id(year)
        if time_id is None:
            return {}

        gender_id = self._get_gender_id(gender_code)
        if gender_id is None:
            return {}

        # Query with category breakdown
        results = (
            self._session.query(
                DimATUSActivityCategory.babylon_category,
                func.sum(FactATUSReproductiveLabor.hours_per_week).label("total_hours"),
            )
            .join(
                FactATUSReproductiveLabor,
                DimATUSActivityCategory.category_id == FactATUSReproductiveLabor.category_id,
            )
            .filter(
                FactATUSReproductiveLabor.time_id == time_id,
                FactATUSReproductiveLabor.gender_id == gender_id,
            )
            .group_by(DimATUSActivityCategory.babylon_category)
            .all()
        )

        return {row.babylon_category: float(row.total_hours) for row in results}

    def _get_time_id(self, year: int) -> int | None:
        """Get time_id for a specific year.

        Args:
            year: Calendar year.

        Returns:
            time_id or None if not found.
        """
        result = (
            self._session.query(DimTime.time_id)
            .filter(DimTime.year == year, DimTime.is_annual == True)  # noqa: E712
            .first()
        )
        return result.time_id if result else None

    def _get_most_recent_time_id(self) -> int | None:
        """Get time_id for most recent year with ATUS data.

        Returns:
            time_id or None if no data.
        """
        result = (
            self._session.query(FactATUSReproductiveLabor.time_id)
            .join(DimTime, FactATUSReproductiveLabor.time_id == DimTime.time_id)
            .order_by(DimTime.year.desc())
            .first()
        )
        return result.time_id if result else None

    def _get_gender_total_id(self) -> int | None:
        """Get gender_id for 'Total' category.

        Caches result to avoid repeated queries.

        Returns:
            gender_id for Total or None.
        """
        if self._gender_total_id is not None:
            return self._gender_total_id

        result = (
            self._session.query(DimGender.gender_id).filter(DimGender.gender_code == "T").first()
        )
        if result:
            self._gender_total_id = result.gender_id
        return self._gender_total_id

    def _get_gender_id(self, gender_code: str) -> int | None:
        """Get gender_id for a specific gender code.

        Args:
            gender_code: "T", "M", or "F".

        Returns:
            gender_id or None.
        """
        if gender_code == "T" and self._gender_total_id is not None:
            return self._gender_total_id

        result = (
            self._session.query(DimGender.gender_id)
            .filter(DimGender.gender_code == gender_code)
            .first()
        )
        if result and gender_code == "T":
            self._gender_total_id = result.gender_id
        return result.gender_id if result else None

    def _query_total_hours(self, time_id: int, gender_id: int) -> Decimal:
        """Query total reproductive labor hours across all categories.

        Args:
            time_id: Time dimension ID.
            gender_id: Gender dimension ID.

        Returns:
            Sum of hours_per_week across all categories.
        """
        result = (
            self._session.query(
                func.sum(FactATUSReproductiveLabor.hours_per_week).label("total_hours")
            )
            .filter(
                FactATUSReproductiveLabor.time_id == time_id,
                FactATUSReproductiveLabor.gender_id == gender_id,
            )
            .first()
        )

        if result and result.total_hours is not None:
            return Decimal(str(result.total_hours))
        return Decimal("0")


def create_atus_db_loader(
    session: Session,
    defines: GameDefines | None = None,
) -> ATUSDBLoader:
    """Factory function to create ATUSDBLoader.

    Convenience function for creating loader with default configuration.

    Args:
        session: SQLAlchemy session.
        defines: Optional GameDefines.

    Returns:
        Configured ATUSDBLoader instance.
    """
    return ATUSDBLoader(session, defines)


__all__ = [
    "ATUSDBLoader",
    "create_atus_db_loader",
]
