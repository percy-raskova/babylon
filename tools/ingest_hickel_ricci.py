#!/usr/bin/env python3
"""Ingest Hickel and Ricci Unequal Exchange calibration data.

Reads the final calibration CSVs and populates the 3NF database
FactHickelDrain and FactRicciUnequalExchange tables.

Usage:
    poetry run python tools/ingest_hickel_ricci.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from babylon.reference.database import NormalizedBase
from babylon.reference.schema import (
    DimCountry,
    DimTime,
    FactHickelDrain,
    FactRicciUnequalExchange,
)

HICKEL_FILE = Path("/media/user/data/babylon-data/babylon_hickel_final.csv")
RICCI_FILE = Path("/media/user/data/babylon-data/babylon_ricci_final.csv")
DB_URL = "sqlite:///marxist-data-3NF.sqlite"


def get_or_create_time(session: Session, year: int) -> DimTime:
    """Get or create DimTime entry for a given year."""
    time_entry = session.execute(
        select(DimTime).where(DimTime.year == year, DimTime.is_annual == True)  # noqa: E712
    ).scalar_one_or_none()

    if not time_entry:
        time_entry = DimTime(year=year, is_annual=True)
        session.add(time_entry)
        session.flush()

    return time_entry


def get_or_create_country(session: Session, name: str, world_system_tier: str) -> DimCountry:
    """Get or create DimCountry entry."""
    country = session.execute(
        select(DimCountry).where(DimCountry.country_name == name)
    ).scalar_one_or_none()

    if not country:
        # Give it a faux code if not exists
        faux_code = name[:3].upper() + "_UE"
        tier = world_system_tier.lower()
        if tier not in ("core", "semi_periphery", "periphery"):
            tier = "periphery"

        country = DimCountry(
            cty_code=faux_code,
            country_name=name,
            world_system_tier=tier,
            is_region=True,
        )
        session.add(country)
        session.flush()

    return country


def ingest_hickel(session: Session) -> None:
    """Ingest Hickel Drain data."""
    if not HICKEL_FILE.exists():
        print(f"Skipping Hickel: {HICKEL_FILE} not found.")
        return

    print(f"Ingesting Hickel data from {HICKEL_FILE}...")
    count = 0
    with HICKEL_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            drain_usd = float(row["annual_drain_usd_billions"])

            time_entry = get_or_create_time(session, year)

            # Map Hickel summary info
            drain = FactHickelDrain(
                time_id=time_entry.time_id,
                drain_direction="South to North",
                resource_type="TOTAL_AGGREGATE",
                net_appropriation=drain_usd,
                units="USD Billions",
                monetary_value_billions=drain_usd,
            )
            session.add(drain)
            count += 1

    print(f"  Inserted {count} Hickel rows.")


def ingest_ricci(session: Session) -> None:
    """Ingest Ricci Unequal Exchange data."""
    if not RICCI_FILE.exists():
        print(f"Skipping Ricci: {RICCI_FILE} not found.")
        return

    print(f"Ingesting Ricci data from {RICCI_FILE}...")
    count = 0
    with RICCI_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # We only track TOTAL transfers to avoid double counting GVC
            if row.get("transfer_type", "") != "TOTAL":
                continue

            year = int(row["year"])
            region = row["region_name"]
            tier = row.get("region_type", "PERIPHERY")
            value_usd = float(row["value_usd_billions"])
            signed_ue = float(row["signed_value"])

            time_entry = get_or_create_time(session, year)
            country_entry = get_or_create_country(session, region, tier)

            ue = FactRicciUnequalExchange(
                time_id=time_entry.time_id,
                country_id=country_entry.country_id,
                trade_volume_billions=value_usd,
                ue_transfer_billions=signed_ue,
            )
            session.add(ue)
            count += 1

    print(f"  Inserted {count} Ricci rows.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Hickel and Ricci data to 3NF DB")
    parser.add_argument("--db-url", default=DB_URL, help="Database URL")
    args = parser.parse_args(argv)

    engine = create_engine(args.db_url)
    NormalizedBase.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            ingest_hickel(session)
            ingest_ricci(session)
            session.commit()
            print("Successfully ingested all Unequal Exchange calibration data.")
        except Exception as e:
            session.rollback()
            print(f"Error ingesting data: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
