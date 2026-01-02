#!/usr/bin/env python3
"""Load BLS Industry Productivity data into SQLite research database.

Ingests labor productivity, hours worked, employment, and compensation
metrics by NAICS industry for Marxian value analysis.

Usage:
    poetry run python tools/load_productivity.py           # Load 2022 data
    poetry run python tools/load_productivity.py --year 2021
    poetry run python tools/load_productivity.py --reset   # Drop and reload
    poetry run python tools/load_productivity.py --all-years  # Load all available

Metrics loaded:
    - Labor productivity index (output per hour)
    - Hours worked (millions of hours)
    - Employment (thousands of jobs)
    - Hourly compensation index
    - Unit labor costs index (labor share proxy)
    - Real sectoral output index
    - Labor compensation (millions $)
    - Sectoral output (millions $)

Join with QCEW:
    productivity_industries.naics_code -> qcew_industries.industry_code

Rate of surplus value calculation:
    S' = (sectoral_output_millions - labor_compensation_millions)
         / labor_compensation_millions
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Entry point for productivity data loading."""
    parser = argparse.ArgumentParser(
        description="Load BLS Industry Productivity data into SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--productivity-dir",
        type=Path,
        default=Path("data/productivity"),
        help="Path to productivity Excel files directory (default: data/productivity)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2022,
        help="Year to load (default: 2022)",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Load all available years (1987-2024)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate productivity tables before loading",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress verbose output",
    )

    args = parser.parse_args()

    # Validate productivity directory
    if not args.productivity_dir.exists():
        print(f"Error: Productivity directory not found: {args.productivity_dir}", file=sys.stderr)
        return 1

    # Import here to avoid circular imports during setup
    from babylon.data.census import CENSUS_DB_PATH
    from babylon.data.productivity import (
        discover_available_years,
        load_multi_year_productivity,
        load_productivity_data,
    )

    if not args.quiet:
        print(f"Productivity data directory: {args.productivity_dir}")
        print(f"Database: {CENSUS_DB_PATH}")

        # Show available years
        try:
            available_years = discover_available_years(args.productivity_dir)
            print(f"Available years: {available_years[0]}-{available_years[-1]}")
        except Exception as e:
            print(f"Warning: Could not discover years: {e}")

        if args.all_years:
            print("Mode: Loading all years")
        else:
            print(f"Year: {args.year}")

        if args.reset:
            print("Reset: dropping existing productivity tables")
        print()

    try:
        if args.all_years:
            stats = load_multi_year_productivity(
                productivity_dir=args.productivity_dir,
                years=None,  # All available
                reset=args.reset,
            )
        else:
            stats = load_productivity_data(
                productivity_dir=args.productivity_dir,
                year=args.year,
                reset=args.reset,
            )

        if not args.quiet:
            print(f"\nLoaded {stats.industries_loaded:,} industries")
            print(f"Loaded {stats.records_loaded:,} annual records")
            print(f"Year: {stats.year}")
            print(f"\nDatabase ready: {CENSUS_DB_PATH}")

            # Show sample query
            print("\nSample Marxian analysis query:")
            print("  SELECT pi.industry_title,")
            print("         pa.sectoral_output_millions - pa.labor_compensation_millions")
            print("           AS surplus_value_millions,")
            print("         (pa.sectoral_output_millions - pa.labor_compensation_millions)")
            print("           / NULLIF(pa.labor_compensation_millions, 0)")
            print("           AS rate_of_surplus_value")
            print("  FROM productivity_annual pa")
            print("  JOIN productivity_industries pi ON pa.industry_id = pi.id")
            print("  WHERE pa.year = 2022 AND pa.sectoral_output_millions IS NOT NULL;")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
