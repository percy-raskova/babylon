#!/usr/bin/env python3
"""Load raw QCEW 2022 employment/wage data into SQLite research database.

Ingests the full BLS singlefile CSV (494MB, 3.6M rows) into a denormalized
table for fast class composition queries. Unlike the normalized QCEW tables,
this preserves raw data structure without dimension tables.

Also optionally loads labor hours Excel data for quarterly granularity.

Usage:
    poetry run python tools/ingest_qcew_full.py                    # Load CSV
    poetry run python tools/ingest_qcew_full.py --reset            # Drop and reload
    poetry run python tools/ingest_qcew_full.py --xlsx             # Also load Excel
    poetry run python tools/ingest_qcew_full.py --validate-only    # Just print class composition
    poetry run python tools/ingest_qcew_full.py --quiet            # Suppress progress

Tables loaded:
    qcew_raw_2022    - Raw 2022 annual data with all original columns
    labor_hours_2022 - Excel data with quarterly granularity (optional)

Output includes Class Composition validation:
    - Goods Producing employment (NAICS domain 101)
    - Service Providing employment (NAICS domain 102)
    - Government employment (own_code 1, 2, 3)
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Entry point for raw QCEW 2022 data loading."""
    parser = argparse.ArgumentParser(
        description="Load raw QCEW 2022 data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate raw tables before loading",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Skip loading, just print class composition from existing data",
    )
    parser.add_argument(
        "--xlsx",
        action="store_true",
        help="Also load labor hours Excel files",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=Path("data/mass_labor_hours/2022.annual.singlefile.csv"),
        help="Path to raw CSV file (default: data/mass_labor_hours/2022.annual.singlefile.csv)",
    )
    parser.add_argument(
        "--xlsx-dir",
        type=Path,
        default=Path("data/mass_labor_hours"),
        help="Path to Excel files directory (default: data/mass_labor_hours)",
    )

    args = parser.parse_args()

    # Import here to avoid circular imports during setup
    from babylon.data.census.database import RESEARCH_DB_PATH
    from babylon.data.qcew import (
        load_labor_hours_data,
        load_raw_2022_data,
        print_class_composition,
    )

    # Validate-only mode
    if args.validate_only:
        if not args.quiet:
            print("Validate-only mode: printing class composition from existing data")
        print_class_composition(verbose=not args.quiet)
        return 0

    # Validate CSV path exists
    if not args.csv_path.exists():
        print(f"Error: CSV file not found: {args.csv_path}", file=sys.stderr)
        return 1

    if not args.quiet:
        csv_size_mb = args.csv_path.stat().st_size / (1024 * 1024)
        print(f"CSV file: {args.csv_path} ({csv_size_mb:.1f} MB)")
        print(f"Database path: {RESEARCH_DB_PATH}")
        if args.reset:
            print("Reset mode: dropping raw tables")
        if args.xlsx:
            xlsx_files = list(args.xlsx_dir.glob("allhlcn*.xlsx"))
            print(f"Excel files: {len(xlsx_files)} files in {args.xlsx_dir}")
        print()

    try:
        # Load CSV data
        csv_stats = load_raw_2022_data(
            csv_path=args.csv_path,
            reset=args.reset,
            verbose=not args.quiet,
        )

        # Optionally load Excel data
        xlsx_stats = {}
        if args.xlsx:
            if not args.xlsx_dir.exists():
                print(f"Error: Excel directory not found: {args.xlsx_dir}", file=sys.stderr)
                return 1

            xlsx_stats = load_labor_hours_data(
                data_dir=args.xlsx_dir,
                reset=args.reset,
                verbose=not args.quiet,
            )

        # Print class composition validation
        if not args.quiet:
            print_class_composition(verbose=True)

        if not args.quiet:
            print(f"\n{'=' * 50}")
            print("Data loaded successfully!")
            print(f"{'=' * 50}")
            print(f"CSV rows loaded:        {csv_stats['total_rows']:,}")
            print(f"Chunks processed:       {csv_stats['chunks_processed']:,}")
            if xlsx_stats:
                print(f"Excel rows loaded:      {xlsx_stats['total_rows']:,}")
                print(f"Excel files processed:  {xlsx_stats['files_processed']:,}")
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
