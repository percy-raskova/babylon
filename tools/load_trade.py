#!/usr/bin/env python3
"""Load UN trade data into SQLite research database.

Ingests Excel data from data/imperial_rent/country.xlsx into data/sqlite/research.sqlite.
Stores US import/export data by country for imperial rent analysis.

Usage:
    poetry run python tools/load_trade.py           # Load all data
    poetry run python tools/load_trade.py --reset   # Drop and reload trade tables only
    poetry run python tools/load_trade.py --quiet   # Suppress progress bars

Tables loaded:
    trade_countries - Country/region dimension (259 entities)
    trade_monthly   - Monthly import/export values
    trade_annual    - Annual aggregates with trade balance
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Entry point for trade data loading."""
    parser = argparse.ArgumentParser(
        description="Load UN trade data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate trade tables before loading (census tables preserved)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress bars and verbose output",
    )
    parser.add_argument(
        "--xlsx-path",
        type=Path,
        default=Path("data/imperial_rent/country.xlsx"),
        help="Path to trade data Excel file (default: data/imperial_rent/country.xlsx)",
    )

    args = parser.parse_args()

    # Validate Excel file exists
    if not args.xlsx_path.exists():
        print(f"Error: Trade data file not found: {args.xlsx_path}", file=sys.stderr)
        return 1

    # Import here to avoid circular imports during setup
    from babylon.data.census.database import RESEARCH_DB_PATH
    from babylon.data.trade import load_trade_data

    if not args.quiet:
        print(f"Trade data file: {args.xlsx_path}")
        print(f"Database path: {RESEARCH_DB_PATH}")
        if args.reset:
            print("Reset mode: dropping trade tables only (census tables preserved)")
        print()

    try:
        stats = load_trade_data(
            xlsx_path=args.xlsx_path,
            reset=args.reset,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print(f"\nDatabase ready: {RESEARCH_DB_PATH}")
            total_records = sum(stats.values())
            print(f"Total trade records: {total_records:,}")

        return 0

    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
