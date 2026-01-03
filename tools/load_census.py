#!/usr/bin/env python3
"""Load Census ACS data into SQLite research database.

Supports two ingestion modes:
1. API mode (recommended): Fetches county-level data directly from Census Bureau API
2. CSV mode (legacy): Ingests from downloaded CSV files in data/census/

Usage:
    # API mode (recommended)
    poetry run python tools/load_census.py --from-api           # All 16 tables
    poetry run python tools/load_census.py --from-api --year 2022 --reset
    poetry run python tools/load_census.py --from-api --tables B19001,B23020

    # CSV mode (legacy)
    poetry run python tools/load_census.py                      # From CSV files
    poetry run python tools/load_census.py --reset              # Drop and reload

Tables (API mode supports all 16):
    Original 8:
        B19001 - Household Income Distribution
        B19013 - Median Household Income
        B23025 - Employment Status
        B24080 - Class of Worker
        B25003 - Housing Tenure
        B25064 - Median Gross Rent
        B25070 - Rent Burden
        C24010 - Occupation by Gender

    Marxian Analysis 8:
        B23020 - Hours Worked (labor time proxy)
        B17001 - Poverty Status (reserve army metric)
        B15003 - Educational Attainment (skills reproduction)
        B19083 - GINI Coefficient (inequality measure)
        B08301 - Commute Mode (unproductive labor time)
        B19052 - Wage Income (proletariat flag)
        B19053 - Self-Employment Income (petty bourgeois flag)
        B19054 - Investment Income (bourgeoisie flag)

Environment:
    CENSUS_API_KEY - API key for Census Bureau (higher rate limits)
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Entry point for census data loading."""
    parser = argparse.ArgumentParser(
        description="Load Census ACS data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Fetch data from Census Bureau API (recommended)",
    )

    # API mode options
    parser.add_argument(
        "--year",
        type=int,
        default=2022,
        help="ACS data year (default: 2022 for 2018-2022 5-year estimates)",
    )
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to load (default: all 16)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Census API key (or set CENSUS_API_KEY env var)",
    )

    # CSV mode options
    parser.add_argument(
        "--census-dir",
        type=Path,
        default=Path("data/census"),
        help="Path to census CSV data directory (default: data/census)",
    )

    # Common options
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all census tables before loading",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress bars and verbose output",
    )

    args = parser.parse_args()

    # Import here to avoid circular imports during setup
    from babylon.data.census import CENSUS_DB_PATH

    if args.from_api:
        return _load_from_api(args, CENSUS_DB_PATH)
    else:
        return _load_from_csv(args, CENSUS_DB_PATH)


def _load_from_api(args: argparse.Namespace, db_path: Path) -> int:
    """Load census data from Census Bureau API."""
    from babylon.data.census import ALL_TABLES, load_census_from_api

    # Parse tables argument
    tables = None
    if args.tables:
        tables = [t.strip().upper() for t in args.tables.split(",")]
        # Validate tables
        invalid = [t for t in tables if t not in ALL_TABLES]
        if invalid:
            print(f"Error: Unknown tables: {', '.join(invalid)}", file=sys.stderr)
            print(f"Valid tables: {', '.join(ALL_TABLES)}", file=sys.stderr)
            return 1

    if not args.quiet:
        print("Mode: Census Bureau API")
        print(f"Year: ACS {args.year} 5-Year Estimates")
        print(f"Tables: {len(tables) if tables else 16}")
        print(f"Database: {db_path}")
        if args.reset:
            print("Reset: dropping existing census tables")
        print()

    try:
        stats = load_census_from_api(
            year=args.year,
            tables=tables,
            api_key=args.api_key,
            reset=args.reset,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print(f"\nDatabase ready: {db_path}")
            total_records = sum(stats.values())
            print(f"Total records: {total_records:,}")

        return 0

    except Exception as e:
        print(f"Error during API ingestion: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


def _load_from_csv(args: argparse.Namespace, db_path: Path) -> int:
    """Load census data from CSV files (legacy mode)."""
    from babylon.data.census import load_census_data

    # Validate census directory exists
    if not args.census_dir.exists():
        print(f"Error: Census directory not found: {args.census_dir}", file=sys.stderr)
        print("Use --from-api to fetch data directly from Census Bureau API", file=sys.stderr)
        return 1

    if not args.quiet:
        print("Mode: CSV files (legacy)")
        print(f"Census data directory: {args.census_dir}")
        print(f"Database: {db_path}")
        if args.reset:
            print("Reset: dropping existing tables")
        print()

    try:
        stats = load_census_data(
            census_dir=args.census_dir,
            reset=args.reset,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print(f"\nDatabase ready: {db_path}")
            total_records = sum(stats.values())
            print(f"Total records: {total_records:,}")

        return 0

    except Exception as e:
        print(f"Error during CSV ingestion: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
