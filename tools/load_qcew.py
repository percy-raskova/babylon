#!/usr/bin/env python3
"""Load BLS QCEW employment/wage data into SQLite research database.

Ingests CSV data from data/employment_industry/2024.annual.by_area/
into data/sqlite/research.sqlite. Stores US employment and wage data
by geography, industry, and ownership for labor aristocracy analysis.

Usage:
    poetry run python tools/load_qcew.py           # Load all data
    poetry run python tools/load_qcew.py --reset   # Drop and reload QCEW tables only
    poetry run python tools/load_qcew.py --quiet   # Suppress progress output

Tables loaded:
    qcew_areas      - Geographic dimension (counties, states, CSAs)
    qcew_industries - NAICS industry hierarchy
    qcew_ownership  - Ownership sector types
    qcew_annual     - Annual employment/wage metrics
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Entry point for QCEW data loading."""
    parser = argparse.ArgumentParser(
        description="Load BLS QCEW employment/wage data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate QCEW tables before loading (other tables preserved)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/employment_industry/2024.annual.by_area"),
        help="Path to QCEW by_area directory (default: data/employment_industry/2024.annual.by_area)",
    )

    args = parser.parse_args()

    # Validate data directory exists
    if not args.data_dir.exists():
        print(f"Error: QCEW data directory not found: {args.data_dir}", file=sys.stderr)
        return 1

    if not args.data_dir.is_dir():
        print(f"Error: Not a directory: {args.data_dir}", file=sys.stderr)
        return 1

    # Check for CSV files
    csv_count = len(list(args.data_dir.glob("*.csv")))
    if csv_count == 0:
        print(f"Error: No CSV files found in {args.data_dir}", file=sys.stderr)
        return 1

    # Import here to avoid circular imports during setup
    from babylon.data.census.database import RESEARCH_DB_PATH
    from babylon.data.qcew import load_qcew_data

    if not args.quiet:
        print(f"QCEW data directory: {args.data_dir}")
        print(f"CSV files found: {csv_count}")
        print(f"Database path: {RESEARCH_DB_PATH}")
        if args.reset:
            print("Reset mode: dropping QCEW tables only (other tables preserved)")
        print()

    try:
        stats = load_qcew_data(
            data_dir=args.data_dir,
            reset=args.reset,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print(f"\n{'=' * 50}")
            print("QCEW data loaded successfully!")
            print(f"{'=' * 50}")
            print(f"Files processed:    {stats['files']:,}")
            print(f"Records parsed:     {stats['records_parsed']:,}")
            print(f"Areas:              {stats['areas']:,}")
            print(f"Industries:         {stats['industries']:,}")
            print(f"Ownership types:    {stats['ownership_types']:,}")
            print(f"Annual facts:       {stats['annual_facts']:,}")
            print(f"\nDatabase ready: {RESEARCH_DB_PATH}")

        return 0

    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
