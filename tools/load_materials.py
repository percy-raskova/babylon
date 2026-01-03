#!/usr/bin/env python3
"""Load USGS Mineral Commodity Summaries into SQLite research database.

Ingests CSV files from data/raw_mats/ into data/sqlite/research.sqlite.
Stores strategic material production, trade, and dependency data
for imperial economics analysis.

Usage:
    poetry run python tools/load_materials.py           # Load all data
    poetry run python tools/load_materials.py --reset   # Drop and reload
    poetry run python tools/load_materials.py --quiet   # Suppress progress

Tables loaded:
    commodities             - Mineral/material dimension (~85)
    commodity_metrics       - Measurement types (~15)
    commodity_observations  - Annual observations (EAV, ~2,000 rows)
    materials_states        - US states for geographic joins (51)
    state_minerals          - State production values (~51 rows)
    mineral_trends          - Industry aggregates (~5 rows)

Key metrics:
    NIR_pct   - Net Import Reliance (imperial vulnerability index)
    USprod_*  - US production (strategic autonomy metric)
    Imports_* - Materials from periphery (unequal exchange)

Critical minerals tracked:
    Lithium, Cobalt, Rare Earths, Graphite, Manganese, Nickel, etc.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main entry point for materials data loader."""
    parser = argparse.ArgumentParser(
        description="Load USGS materials data into SQLite research database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate materials tables before loading",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw_mats"),
        help="Path to USGS materials directory (default: data/raw_mats)",
    )

    args = parser.parse_args()

    # Validate data directory
    if not args.data_dir.exists():
        print(
            f"Error: Materials data directory not found: {args.data_dir}",
            file=sys.stderr,
        )
        return 1

    # Import and run loader
    from babylon.data.census.database import RESEARCH_DB_PATH
    from babylon.data.materials import load_materials_data

    if not args.quiet:
        print(f"Materials data directory: {args.data_dir}")
        print(f"Database path: {RESEARCH_DB_PATH}")

    try:
        stats = load_materials_data(
            materials_dir=args.data_dir,
            reset=args.reset,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print("\nMaterials data loaded successfully!")
            print(f"  Files processed: {stats.files_processed}")
            print(f"  Commodities: {stats.commodities_loaded}")
            print(f"  Metrics: {stats.metrics_loaded}")
            print(f"  Observations: {stats.observations_loaded}")
            print(f"  States: {stats.states_loaded}")
            print(f"  State minerals: {stats.state_minerals_loaded}")
            print(f"  Trends: {stats.trends_loaded}")
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
