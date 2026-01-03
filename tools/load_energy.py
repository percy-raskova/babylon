#!/usr/bin/env python3
"""Load EIA Monthly Energy Review data into SQLite research database.

Ingests Excel files from data/energy/ into data/sqlite/research.sqlite.
Stores annual energy production, consumption, prices, and emissions
for metabolic rift analysis.

Usage:
    poetry run python tools/load_energy.py           # Load priority tables
    poetry run python tools/load_energy.py --reset   # Drop and reload
    poetry run python tools/load_energy.py --all     # Load all tables
    poetry run python tools/load_energy.py --quiet   # Suppress progress

Tables loaded:
    energy_tables   - EIA table dimension (~20 priority tables)
    energy_series   - Time series dimension (~200 series)
    energy_annual   - Annual observations (1949-2024, ~15,000 rows)

Priority tables (default):
    01.01-01.04    Primary energy overview (production, consumption, trade)
    02.01a-02.06   Sector consumption (residential, commercial, industrial)
    03.01, 03.05   Petroleum (overview, crude production)
    04.01          Natural gas overview
    09.01-09.10    Prices (crude, gasoline, natural gas, electricity)
    11.01-11.05    CO2 emissions (total, by sector, by fuel)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main entry point for energy data loader."""
    parser = argparse.ArgumentParser(
        description="Load EIA energy data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate energy tables before loading",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all tables, not just priority tables",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/energy"),
        help="Path to EIA energy directory (default: data/energy)",
    )

    args = parser.parse_args()

    # Validate data directory
    if not args.data_dir.exists():
        print(f"Error: Energy data directory not found: {args.data_dir}", file=sys.stderr)
        return 1

    # Import and run loader
    from babylon.data.census.database import RESEARCH_DB_PATH
    from babylon.data.energy import load_energy_data

    if not args.quiet:
        print(f"Energy data directory: {args.data_dir}")
        print(f"Database path: {RESEARCH_DB_PATH}")
        if args.all:
            print("Loading ALL tables (not just priority)")

    try:
        stats = load_energy_data(
            energy_dir=args.data_dir,
            reset=args.reset,
            verbose=not args.quiet,
            priority_only=not args.all,
        )

        if not args.quiet:
            print("\nEnergy data loaded successfully!")
            print(f"  Files processed: {stats.files_processed}")
            print(f"  Tables: {stats.tables_loaded}")
            print(f"  Series: {stats.series_loaded}")
            print(f"  Observations: {stats.observations_loaded}")
            if stats.files_skipped:
                print(f"  Files skipped: {stats.files_skipped}")

        if stats.errors:
            print("\nErrors:", file=sys.stderr)
            for error in stats.errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
