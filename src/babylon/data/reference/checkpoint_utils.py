"""Checkpoint verification utilities for data ingestion.

These utilities help validate checkpoint state, debug resume behavior,
and verify data loading consistency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func

from babylon.data.reference.schema import IngestCheckpoint

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class CheckpointSummary:
    """Summary of checkpoint state for a data source."""

    source_code: str
    checkpoint_count: int
    total_rows: int
    years: list[int]
    unique_states: int


def count_checkpoints(session: Session, source_code: str) -> int:
    """Count the number of checkpoints for a data source.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier (e.g., "census", "qcew").

    Returns:
        Number of checkpoint records for the source.
    """
    return (
        session.query(IngestCheckpoint).filter(IngestCheckpoint.source_code == source_code).count()
    )


def count_checkpoints_by_year(session: Session, source_code: str, year: int) -> int:
    """Count checkpoints for a specific source and year.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.
        year: Year to filter by.

    Returns:
        Number of checkpoint records for the source and year.
    """
    return (
        session.query(IngestCheckpoint)
        .filter(
            IngestCheckpoint.source_code == source_code,
            IngestCheckpoint.year == year,
        )
        .count()
    )


def get_total_row_count(session: Session, source_code: str) -> int:
    """Get total rows loaded across all checkpoints for a source.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.

    Returns:
        Sum of row_count across all checkpoints for the source.
    """
    result = (
        session.query(func.sum(IngestCheckpoint.row_count))
        .filter(IngestCheckpoint.source_code == source_code)
        .scalar()
    )
    return result or 0


def get_checkpoint_summary(session: Session, source_code: str) -> CheckpointSummary:
    """Get comprehensive summary of checkpoint state for a source.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.

    Returns:
        CheckpointSummary with counts, totals, and year distribution.
    """
    checkpoints = (
        session.query(IngestCheckpoint).filter(IngestCheckpoint.source_code == source_code).all()
    )

    if not checkpoints:
        return CheckpointSummary(
            source_code=source_code,
            checkpoint_count=0,
            total_rows=0,
            years=[],
            unique_states=0,
        )

    years = sorted({cp.year for cp in checkpoints if cp.year != 0})
    unique_states = len({cp.state_fips for cp in checkpoints})
    total_rows = sum(cp.row_count for cp in checkpoints)

    return CheckpointSummary(
        source_code=source_code,
        checkpoint_count=len(checkpoints),
        total_rows=total_rows,
        years=years,
        unique_states=unique_states,
    )


def verify_checkpoint_coverage(session: Session, source_code: str, expected_count: int) -> bool:
    """Verify checkpoint count matches expected value.

    Useful for asserting all expected work units were processed.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.
        expected_count: Expected number of checkpoints.

    Returns:
        True if checkpoint count matches expected, False otherwise.
    """
    actual_count = count_checkpoints(session, source_code)
    return actual_count == expected_count


def get_incomplete_work_units(
    session: Session,
    source_code: str,
    expected_states: list[str],
    year: int,
) -> list[str]:
    """Find state FIPS codes without checkpoints.

    Useful for identifying work units that failed or weren't processed.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.
        expected_states: List of expected state FIPS codes.
        year: Year to check.

    Returns:
        List of state FIPS codes without checkpoints.
    """
    completed_states = {
        cp.state_fips
        for cp in session.query(IngestCheckpoint)
        .filter(
            IngestCheckpoint.source_code == source_code,
            IngestCheckpoint.year == year,
        )
        .all()
    }

    return [s for s in expected_states if s not in completed_states]


def get_checkpoint_details(session: Session, source_code: str) -> list[dict[str, object]]:
    """Get detailed checkpoint records for a source.

    Useful for debugging checkpoint state.

    Args:
        session: SQLAlchemy session.
        source_code: Data source identifier.

    Returns:
        List of checkpoint records as dictionaries.
    """
    checkpoints = (
        session.query(IngestCheckpoint)
        .filter(IngestCheckpoint.source_code == source_code)
        .order_by(IngestCheckpoint.year, IngestCheckpoint.state_fips)
        .all()
    )

    return [
        {
            "checkpoint_id": cp.checkpoint_id,
            "source_code": cp.source_code,
            "year": cp.year,
            "state_fips": cp.state_fips,
            "table_id": cp.table_id,
            "race_code": cp.race_code,
            "row_count": cp.row_count,
            "completed_at": cp.completed_at,
        }
        for cp in checkpoints
    ]


__all__ = [
    "CheckpointSummary",
    "count_checkpoints",
    "count_checkpoints_by_year",
    "get_checkpoint_details",
    "get_checkpoint_summary",
    "get_incomplete_work_units",
    "get_total_row_count",
    "verify_checkpoint_coverage",
]
