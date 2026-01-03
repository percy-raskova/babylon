"""Bureau of Labor Statistics (BLS) data access module.

Provides ingestion for BLS employment and labor data:
- Union membership by state
- Employment by industry (future)

See brainstorm/data-requirements.md for data collection specifications.
See ai-docs/game-data.yaml for API documentation and variable mappings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from babylon.data.external.base import DataIngester, IngestResult, parse_float, parse_int
from babylon.data.schema import StrategicResource, UnionMembership

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UnionMembershipIngester(DataIngester[UnionMembership]):
    """Ingester for BLS union membership data.

    Expected CSV format:
        state_fips,year,total_employed,union_members,union_pct
        01,2023,2100000,160000,7.6
        ...

    Note: state_fips can be empty for national totals.
    """

    @property
    def model_class(self) -> type[UnionMembership]:
        """Return the UnionMembership model class."""
        return UnionMembership

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a union membership row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not row.get("year"):
            errors.append("Missing required field: year")
        else:
            try:
                year = int(row["year"])
                if year < 1900 or year > 2100:
                    errors.append(f"Year out of range: {year}")
            except ValueError:
                errors.append(f"Invalid year: {row['year']}")

        return errors

    def parse_row(self, row: dict[str, str]) -> UnionMembership | None:
        """Parse a CSV row into a UnionMembership model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            UnionMembership model instance
        """
        state_fips = row.get("state_fips", "").strip()

        return UnionMembership(
            state_fips=state_fips if state_fips else None,
            year=int(row["year"]),
            total_employed=parse_int(row.get("total_employed")),
            union_members=parse_int(row.get("union_members")),
            union_pct=parse_float(row.get("union_pct")),
        )


class StrategicResourceIngester(DataIngester[StrategicResource]):
    """Ingester for strategic resource data.

    Expected CSV format:
        resource_id,resource_name,year,annual_production,production_unit,strategic_reserve,reserve_unit
        R002,Crude Oil,2023,4300000000,barrels,350000000,barrels
        ...
    """

    @property
    def model_class(self) -> type[StrategicResource]:
        """Return the StrategicResource model class."""
        return StrategicResource

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a strategic resource row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not row.get("resource_id"):
            errors.append("Missing required field: resource_id")

        if not row.get("resource_name"):
            errors.append("Missing required field: resource_name")

        if not row.get("year"):
            errors.append("Missing required field: year")
        else:
            try:
                year = int(row["year"])
                if year < 1900 or year > 2100:
                    errors.append(f"Year out of range: {year}")
            except ValueError:
                errors.append(f"Invalid year: {row['year']}")

        return errors

    def parse_row(self, row: dict[str, str]) -> StrategicResource | None:
        """Parse a CSV row into a StrategicResource model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            StrategicResource model instance
        """
        return StrategicResource(
            resource_id=row["resource_id"].strip(),
            resource_name=row["resource_name"].strip(),
            year=int(row["year"]),
            annual_production=parse_float(row.get("annual_production")),
            production_unit=row.get("production_unit", "").strip() or None,
            strategic_reserve=parse_float(row.get("strategic_reserve")),
            reserve_unit=row.get("reserve_unit", "").strip() or None,
        )


def ingest_union_membership(
    session: Session,
    csv_path: Path | str,
) -> IngestResult:
    """Ingest BLS union membership data.

    Args:
        session: SQLAlchemy session
        csv_path: Path to the CSV file

    Returns:
        IngestResult with statistics about the operation
    """
    ingester = UnionMembershipIngester()
    return ingester.ingest_csv(session, csv_path)


def ingest_strategic_resources(
    session: Session,
    csv_path: Path | str,
) -> IngestResult:
    """Ingest strategic resource data.

    Args:
        session: SQLAlchemy session
        csv_path: Path to the CSV file

    Returns:
        IngestResult with statistics about the operation
    """
    ingester = StrategicResourceIngester()
    return ingester.ingest_csv(session, csv_path)


__all__ = [
    "UnionMembershipIngester",
    "StrategicResourceIngester",
    "ingest_union_membership",
    "ingest_strategic_resources",
]
