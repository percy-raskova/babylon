#!/usr/bin/env python3
"""Convert SQLite ETL database to DuckDB for in-game use.

This script exports all tables from the SQLite normalized database to DuckDB,
enabling fast OLAP queries during simulation. The SQLite database is used for
ETL/loading operations where reliable UPSERT is needed.

Architecture:
    ETL/Loading (SQLite) --> Convert --> In-Game Ledger (DuckDB)
         ^                                      ^
    Reliable UPSERT                       Fast OLAP queries
    Idempotent ops                        Read-only in-game

Usage:
    python tools/convert_sqlite_to_duckdb.py [--source PATH] [--dest PATH]

Default paths:
    Source: data/sqlite/marxist-data-3NF.sqlite
    Dest:   data/duckdb/marxist-data-3NF.duckdb
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb


def get_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get list of all tables in the attached SQLite database."""
    result = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sqlite_db'
          AND table_schema = 'main'
        ORDER BY table_name
    """).fetchall()
    return [row[0] for row in result]


def get_row_count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    """Get row count for a table in the attached SQLite database."""
    return conn.execute(f'SELECT COUNT(*) FROM sqlite_db."{table}"').fetchone()[0]


def convert_sqlite_to_duckdb(
    source_path: Path,
    dest_path: Path,
    verbose: bool = True,
) -> None:
    """Convert SQLite database to DuckDB.

    Uses DuckDB's ATTACH command to mount the SQLite database and
    CREATE TABLE AS SELECT to copy data efficiently.

    Args:
        source_path: Path to source SQLite database.
        dest_path: Path to destination DuckDB database.
        verbose: Whether to print progress.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source database not found: {source_path}")

    # Ensure destination directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing destination if present
    if dest_path.exists():
        if verbose:
            print(f"Removing existing DuckDB database: {dest_path}")
        dest_path.unlink()

    # Connect to new DuckDB database
    conn = duckdb.connect(str(dest_path))

    try:
        # Load SQLite extension
        conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Attach source SQLite database (read-only)
        conn.execute(f"ATTACH '{source_path}' AS sqlite_db (TYPE SQLITE, READ_ONLY);")

        # Get table list from SQLite
        tables = get_tables(conn)
        if verbose:
            print(f"Found {len(tables)} tables to convert")

        if not tables:
            raise ValueError("No tables found in source SQLite database")

        # Convert each table
        total_rows = 0
        start_time = time.time()

        for i, table in enumerate(tables, 1):
            row_count = get_row_count(conn, table)
            total_rows += row_count

            if verbose:
                print(
                    f"[{i}/{len(tables)}] Converting {table} ({row_count:,} rows)...",
                    end=" ",
                    flush=True,
                )

            table_start = time.time()

            # Create table and copy data from SQLite to DuckDB main schema
            conn.execute(f'CREATE TABLE main."{table}" AS SELECT * FROM sqlite_db."{table}"')

            if verbose:
                elapsed = time.time() - table_start
                print(f"done ({elapsed:.1f}s)")

        # Detach SQLite database
        conn.execute("DETACH sqlite_db")

        total_time = time.time() - start_time

        if verbose:
            print("\nConversion complete!")
            print(f"  Tables: {len(tables)}")
            print(f"  Rows: {total_rows:,}")
            print(f"  Time: {total_time:.1f}s")
            print(f"  Output: {dest_path}")
            print(f"  Size: {dest_path.stat().st_size / (1024**3):.2f} GB")

    finally:
        conn.close()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert SQLite database to DuckDB")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/sqlite/marxist-data-3NF.sqlite"),
        help="Source SQLite database path",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/duckdb/marxist-data-3NF.duckdb"),
        help="Destination DuckDB database path",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    try:
        convert_sqlite_to_duckdb(
            source_path=args.source,
            dest_path=args.dest,
            verbose=not args.quiet,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
