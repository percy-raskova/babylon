#!/usr/bin/env python
"""CLI tool to run ETL pipeline from research.sqlite to marxist-data-3NF.sqlite.

This tool creates a properly normalized 3NF database from the denormalized
research.sqlite database, with Marxian classifications applied during ETL.

Usage:
    poetry run python tools/normalize_research_db.py
    poetry run python tools/normalize_research_db.py --reset
    poetry run python tools/normalize_research_db.py --views-only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.data.normalize import (
    NORMALIZED_DB_PATH,
    create_views,
    drop_views,
    get_normalized_engine,
    run_etl,
)


def main() -> int:
    """Run the normalization ETL pipeline."""
    parser = argparse.ArgumentParser(
        description="Normalize research.sqlite into marxist-data-3NF.sqlite"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before loading",
    )
    parser.add_argument(
        "--views-only",
        action="store_true",
        help="Only create/recreate views (skip dimension and fact loading)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Babylon Research Database Normalization ETL")
    logger.info("=" * 60)
    logger.info(f"Target: {NORMALIZED_DB_PATH}")

    if args.views_only:
        logger.info("Mode: Views only")
        engine = get_normalized_engine()

        # Drop and recreate views
        logger.info("Dropping existing views...")
        dropped = drop_views(engine)
        logger.info(f"  Dropped {dropped} views")

        logger.info("Creating views...")
        created = create_views(engine)
        logger.info(f"  Created {created} views")

        logger.info("Done!")
        return 0

    # Full ETL
    logger.info(f"Mode: {'Reset' if args.reset else 'Incremental'}")
    logger.info("")

    try:
        stats = run_etl(reset=args.reset)

        logger.info("")
        logger.info("=" * 60)
        logger.info("ETL Complete")
        logger.info("=" * 60)
        logger.info(str(stats))

        if stats.errors:
            logger.warning(f"\n{len(stats.errors)} errors occurred during ETL")
            return 1

        # Create views after ETL
        logger.info("\nCreating analytical views...")
        engine = get_normalized_engine()
        view_count = create_views(engine)
        logger.info(f"  Created {view_count} analytical views")

        logger.info("\nDatabase ready at:")
        logger.info(f"  {NORMALIZED_DB_PATH}")
        logger.info(
            f"\nTotal: {stats.total_dimensions} dimension rows, "
            f"{stats.total_facts} fact rows, {view_count} views"
        )

        return 0

    except Exception as e:
        logger.error(f"ETL failed: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
