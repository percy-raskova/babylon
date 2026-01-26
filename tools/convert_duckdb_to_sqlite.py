#!/usr/bin/env python3
"""Seed SQLite ETL database from existing DuckDB data.

This script copies data from an existing DuckDB database into a pre-initialized
SQLite database. The SQLite schema must be created first (via schema-init).

Architecture:
    1. Initialize SQLite schema: poetry run python -m babylon.data.cli schema-init
    2. Seed data from DuckDB:    poetry run python tools/convert_duckdb_to_sqlite.py

    Existing DuckDB --> Seed --> SQLite ETL database
         ^                           ^
    Legacy data                 New ETL target
    (data only)                 (schema + data)

Usage:
    python tools/convert_duckdb_to_sqlite.py [--source PATH] [--dest PATH]

Default paths:
    Source: data/duckdb/marxist-data-3NF.duckdb
    Dest:   data/sqlite/marxist-data-3NF.sqlite
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb


def get_duckdb_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get list of all tables in the DuckDB database."""
    result = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """).fetchall()
    return [row[0] for row in result]


def get_sqlite_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get list of all tables in the attached SQLite database."""
    result = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sqlite_db'
          AND table_schema = 'main'
        ORDER BY table_name
    """).fetchall()
    return [row[0] for row in result]


def get_row_count(conn: duckdb.DuckDBPyConnection, table: str, schema: str = "main") -> int:
    """Get row count for a table."""
    return conn.execute(f'SELECT COUNT(*) FROM {schema}."{table}"').fetchone()[0]


def seed_sqlite_from_duckdb(
    source_path: Path,
    dest_path: Path,
    verbose: bool = True,
) -> None:
    """Seed SQLite database with data from DuckDB.

    Uses DuckDB's ATTACH command to mount SQLite and
    INSERT INTO SELECT to copy data efficiently.

    The SQLite database must already have the schema created.

    Args:
        source_path: Path to source DuckDB database.
        dest_path: Path to destination SQLite database (must exist with schema).
        verbose: Whether to print progress.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source database not found: {source_path}")

    if not dest_path.exists():
        raise FileNotFoundError(
            f"Destination SQLite database not found: {dest_path}\n"
            "Run 'poetry run python -m babylon.data.cli schema-init' first."
        )

    # Connect to source DuckDB database
    conn = duckdb.connect(str(source_path), read_only=False)

    try:
        # Load SQLite extension
        conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Get table list from DuckDB
        duckdb_tables = set(get_duckdb_tables(conn))
        if verbose:
            print(f"Found {len(duckdb_tables)} tables in DuckDB")

        if not duckdb_tables:
            raise ValueError("No tables found in source DuckDB database")

        # Attach destination SQLite database
        conn.execute(f"ATTACH '{dest_path}' AS sqlite_db (TYPE SQLITE);")

        # Get table list from SQLite
        sqlite_tables = set(get_sqlite_tables(conn))
        if verbose:
            print(f"Found {len(sqlite_tables)} tables in SQLite schema")

        # Find common tables
        common_tables = sorted(duckdb_tables & sqlite_tables)
        if verbose:
            print(f"Will seed {len(common_tables)} matching tables")

        if not common_tables:
            raise ValueError("No matching tables between DuckDB and SQLite")

        # Seed each table
        total_rows = 0
        start_time = time.time()

        for i, table in enumerate(common_tables, 1):
            # Check if SQLite table already has data
            sqlite_count = get_row_count(conn, table, "sqlite_db")
            if sqlite_count > 0:
                if verbose:
                    print(
                        f"[{i}/{len(common_tables)}] Skipping {table} (already has {sqlite_count:,} rows)"
                    )
                continue

            duckdb_count = get_row_count(conn, table, "main")
            if duckdb_count == 0:
                if verbose:
                    print(f"[{i}/{len(common_tables)}] Skipping {table} (empty in DuckDB)")
                continue

            total_rows += duckdb_count

            if verbose:
                print(
                    f"[{i}/{len(common_tables)}] Seeding {table} ({duckdb_count:,} rows)...",
                    end=" ",
                    flush=True,
                )

            table_start = time.time()

            # Insert data from DuckDB into SQLite
            conn.execute(f'INSERT INTO sqlite_db."{table}" SELECT * FROM main."{table}"')

            if verbose:
                elapsed = time.time() - table_start
                print(f"done ({elapsed:.1f}s)")

        # Detach SQLite database
        conn.execute("DETACH sqlite_db")

        total_time = time.time() - start_time

        if verbose:
            print("\nSeeding complete!")
            print(f"  Tables seeded: {len(common_tables)}")
            print(f"  Rows copied: {total_rows:,}")
            print(f"  Time: {total_time:.1f}s")
            print(f"  Output: {dest_path}")
            print(f"  Size: {dest_path.stat().st_size / (1024**3):.2f} GB")

    finally:
        conn.close()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed SQLite ETL database from existing DuckDB data"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/duckdb/marxist-data-3NF.duckdb"),
        help="Source DuckDB database path",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/sqlite/marxist-data-3NF.sqlite"),
        help="Destination SQLite database path",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    try:
        seed_sqlite_from_duckdb(
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
