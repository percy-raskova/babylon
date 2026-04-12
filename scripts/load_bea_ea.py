"""Load BEA Economic Area data from static CSV into the 3NF reference database.

Reads data/bea/michigan_bea_ea.csv and populates:
  - dim_bea_economic_area (8 rows for Michigan-relevant EAs)
  - bridge_county_bea_ea (83 rows for Michigan county assignments)

Usage::

    poetry run python scripts/load_bea_ea.py

Idempotent: safe to run multiple times (uses INSERT OR REPLACE).
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from babylon.reference.database import get_normalized_session, init_normalized_db  # noqa: E402
from babylon.reference.schema import BridgeCountyBEAEA, DimBEAEconomicArea, DimCounty  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CSV_PATH = _REPO_ROOT / "data" / "bea" / "michigan_bea_ea.csv"


def load_bea_ea() -> None:
    """Load BEA Economic Area dimension and county bridge from CSV."""
    if not CSV_PATH.exists():
        logger.error("CSV not found: %s", CSV_PATH)
        raise SystemExit(1)

    # Ensure tables exist
    init_normalized_db()

    with open(CSV_PATH, newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    # Extract unique EAs
    eas: dict[str, dict[str, str]] = {}
    for row in rows:
        code = row["ea_code"]
        if code not in eas:
            eas[code] = {
                "ea_name": row["ea_name"],
                "node_metro_area": row["node_metro_area"],
            }

    logger.info("Found %d unique BEA Economic Areas", len(eas))

    with get_normalized_session() as session:
        # Load dimension table
        ea_id_map: dict[str, int] = {}
        for idx, (code, info) in enumerate(sorted(eas.items()), start=1):
            # Check if already exists
            existing = (
                session.query(DimBEAEconomicArea).filter(DimBEAEconomicArea.ea_code == code).first()
            )
            if existing:
                ea_id_map[code] = existing.bea_ea_id
                logger.info(
                    "  EA exists: %s (%s) → id=%d", code, info["ea_name"], existing.bea_ea_id
                )
            else:
                ea = DimBEAEconomicArea(
                    bea_ea_id=idx,
                    ea_code=code,
                    ea_name=info["ea_name"],
                    node_metro_area=info["node_metro_area"],
                )
                session.add(ea)
                session.flush()
                ea_id_map[code] = ea.bea_ea_id
                logger.info("  Created EA: %s (%s) → id=%d", code, info["ea_name"], ea.bea_ea_id)

        # Load bridge table
        loaded = 0
        skipped = 0
        for row in rows:
            county_fips = row["county_fips"]
            ea_code = row["ea_code"]

            # Look up county_id from fips
            county = session.query(DimCounty).filter(DimCounty.fips == county_fips).first()
            if not county:
                logger.warning("  County FIPS %s not found in dim_county, skipping", county_fips)
                skipped += 1
                continue

            bea_ea_id = ea_id_map[ea_code]

            # Check if bridge row already exists
            existing_bridge = (
                session.query(BridgeCountyBEAEA)
                .filter(
                    BridgeCountyBEAEA.county_id == county.county_id,
                    BridgeCountyBEAEA.bea_ea_id == bea_ea_id,
                )
                .first()
            )
            if existing_bridge:
                skipped += 1
                continue

            bridge = BridgeCountyBEAEA(
                county_id=county.county_id,
                bea_ea_id=bea_ea_id,
            )
            session.add(bridge)
            loaded += 1

        logger.info("Bridge: loaded=%d, skipped=%d", loaded, skipped)

    logger.info("Done. BEA EA data loaded successfully.")


if __name__ == "__main__":
    load_bea_ea()
