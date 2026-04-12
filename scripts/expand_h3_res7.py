"""Expand H3 hex inventory from res-5 to res-7 for Michigan counties.

Reads county geometries from dim_county_geometry, generates H3 res-7 cells
using the existing h3_utils module, and inserts into bridge_county_h3.

Expected output: ~28,000 new rows (31× the existing ~900 res-5 Michigan cells).

Usage::

    poetry run python scripts/expand_h3_res7.py

Idempotent: skips counties that already have res-7 cells.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from decimal import Decimal  # noqa: E402

from sqlalchemy import func  # noqa: E402

from babylon.economics.substrate.h3_utils import generate_h3_cells, wkt_to_geometry  # noqa: E402
from babylon.reference.database import get_normalized_session, init_normalized_db  # noqa: E402
from babylon.reference.schema import (  # noqa: E402
    BridgeCountyH3,
    DimCounty,
    DimCountyGeometry,
    DimState,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

H3_RESOLUTION = 7
STATE_FIPS = "26"  # Michigan


def expand_h3_res7() -> None:
    """Generate H3 res-7 cells for all Michigan county geometries."""
    init_normalized_db()

    with get_normalized_session() as session:
        # Get Michigan state_id
        mi_state = session.query(DimState).filter(DimState.state_fips == STATE_FIPS).first()
        if not mi_state:
            logger.error("Michigan (state_fips=%s) not found in dim_state", STATE_FIPS)
            raise SystemExit(1)

        # Check existing res-7 count for Michigan
        existing_count = (
            session.query(func.count(BridgeCountyH3.h3_index))
            .join(DimCounty, BridgeCountyH3.county_id == DimCounty.county_id)
            .filter(
                DimCounty.state_id == mi_state.state_id,
                BridgeCountyH3.resolution == H3_RESOLUTION,
            )
            .scalar()
        )
        if existing_count and existing_count > 1000:
            logger.info(
                "Already have %d res-%d cells for Michigan. Skipping.",
                existing_count,
                H3_RESOLUTION,
            )
            return

        # Get all Michigan county geometries
        county_geoms = (
            session.query(
                DimCounty.county_id,
                DimCounty.fips,
                DimCounty.county_name,
                DimCountyGeometry.geometry_wkt,
            )
            .join(DimCountyGeometry, DimCounty.county_id == DimCountyGeometry.county_id)
            .filter(
                DimCounty.state_id == mi_state.state_id,
                DimCounty.fips != "26999",  # Skip state-level aggregate
            )
            .all()
        )

        logger.info(
            "Processing %d Michigan counties for H3 res-%d", len(county_geoms), H3_RESOLUTION
        )

        total_cells = 0
        for county_id, fips, name, wkt in county_geoms:
            geom = wkt_to_geometry(wkt)
            if geom is None:
                logger.warning("  %s (%s): no valid geometry, skipping", name, fips)
                continue

            cells = generate_h3_cells(geom, H3_RESOLUTION)
            if not cells:
                logger.warning("  %s (%s): generated 0 cells", name, fips)
                continue

            for h3_index in cells:
                # Check if already exists (h3_index is PK)
                exists = (
                    session.query(BridgeCountyH3.h3_index)
                    .filter(BridgeCountyH3.h3_index == h3_index)
                    .first()
                )
                if exists:
                    continue

                bridge = BridgeCountyH3(
                    h3_index=h3_index,
                    county_id=county_id,
                    resolution=H3_RESOLUTION,
                    coverage_pct=Decimal("100.00"),  # Approximate
                )
                session.add(bridge)

            total_cells += len(cells)
            logger.info("  %s (%s): %d cells", name, fips, len(cells))

            # Flush periodically to avoid OOM on large batches
            if total_cells % 5000 == 0:
                session.flush()

        session.flush()
        logger.info("Total H3 res-%d cells generated: %d", H3_RESOLUTION, total_cells)

    logger.info("Done. H3 expansion complete.")


if __name__ == "__main__":
    expand_h3_res7()
