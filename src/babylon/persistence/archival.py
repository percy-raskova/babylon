"""Parquet archival pipeline for simulation sessions (Feature 037).

Implements session export to Parquet, upload to Cloudflare R2,
and DuckDB-based cross-game analytics over archived data.

This module is a stub for Phase 8 implementation (T043-T049).

Usage::

    from babylon.persistence.archival import export_session_to_parquet

    paths = export_session_to_parquet(
        pool=pool, session_id=session_id, output_dir=Path("/tmp/exports")
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID


def export_session_to_parquet(
    pool: Any,
    session_id: UUID,
    output_dir: str,
) -> list[str]:
    """Export a session's data to Parquet files.

    Args:
        pool: psycopg ConnectionPool instance.
        session_id: Session to export.
        output_dir: Directory to write Parquet files to.

    Returns:
        List of paths to generated Parquet files.

    Raises:
        NotImplementedError: Always (stub for Phase 8).
    """
    raise NotImplementedError(
        "Archival pipeline not yet implemented (Phase 8, T045). "
        f"session_id={session_id}, output_dir={output_dir}"
    )


def upload_to_r2(
    parquet_paths: list[str],
    bucket: str,
    prefix: str = "",
) -> list[str]:
    """Upload Parquet files to Cloudflare R2.

    Args:
        parquet_paths: Local Parquet file paths.
        bucket: R2 bucket name.
        prefix: Key prefix within bucket.

    Returns:
        List of R2 object keys.

    Raises:
        NotImplementedError: Always (stub for Phase 8).
    """
    raise NotImplementedError(
        f"R2 upload not yet implemented (Phase 8, T046). bucket={bucket}, prefix={prefix}"
    )


def purge_session(
    pool: Any,
    session_id: UUID,
) -> None:
    """Delete session data from Postgres after verified export.

    Args:
        pool: psycopg ConnectionPool instance.
        session_id: Session to purge.

    Raises:
        NotImplementedError: Always (stub for Phase 8).
    """
    raise NotImplementedError(
        f"Session purge not yet implemented (Phase 8, T047). session_id={session_id}"
    )


def query_archived_session(
    parquet_path: str | Path,
    query: str,
) -> list[dict[str, Any]]:
    """Query archived session data via DuckDB.

    Args:
        parquet_path: Path to Parquet file or R2 URL.
        query: SQL query to execute against the Parquet data.

    Returns:
        List of result dictionaries.

    Raises:
        NotImplementedError: Always (stub for Phase 8).
    """
    raise NotImplementedError(
        f"Archived query not yet implemented (Phase 8, T048). path={parquet_path}"
    )


__all__ = [
    "export_session_to_parquet",
    "purge_session",
    "query_archived_session",
    "upload_to_r2",
]
