#!/usr/bin/env python3
"""Ingest Ricci (2021) unequal-exchange transfer estimates.

Reads ``babylon_ricci_final.csv`` (shipped in-repo at
``src/babylon/data/reference/``; region-level value-transfer estimates from
Ricci Table 6.2) and inserts the ``transfer_type == "TOTAL"`` rows into
``fact_ricci_unequal_exchange`` in the reference SQLite — the table existed
schema-only (0 rows) since spec-057; this loader finally lands the data.
Idempotent — drops + recreates the fact table on each run.

Mapping notes (deliberate, reviewed 2026-07-16):

* One fact row per (year, region): the CSV's ``TOTAL`` transfer rows.
  ``ue_transfer_billions`` = ``signed_value`` (positive = INFLOW to the
  region, i.e. core appropriation; negative = OUTFLOW, periphery drain) —
  exactly the semantics the column was designed for. The GVC-only subset,
  flow direction, and granularity metadata stay fully available in the
  shipped CSV (pinned by ``tests/unit/reference/test_unequal_exchange_artifacts.py``).
* ``trade_volume_billions`` stays NULL — the CSV carries transfer estimates,
  not bilateral volumes; shoehorning the GVC subset in there would relabel
  data (the honest-Φ rule).
* Regions absent from ``dim_country`` are created with ``is_region=True``,
  a synthesized ``RICnn`` cty_code, and ``world_system_tier`` mapped from
  the CSV's CORE/SEMI_PERIPHERY/PERIPHERY. Existing rows (China, India,
  North America) are never re-tiered unless their tier is NULL.

Usage::

    poetry run python -m tools.ingest.ricci_unequal
    # or with custom paths:
    poetry run python -m tools.ingest.ricci_unequal \\
        --csv /path/to/babylon_ricci_final.csv \\
        --db sqlite:////absolute/path/to/marxist-data-3NF.sqlite
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from babylon.reference.schema import (
    DimCountry,
    DimTime,
    FactRicciUnequalExchange,
    NormalizedBase,
)

DEFAULT_CSV = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "babylon"
    / "data"
    / "reference"
    / "babylon_ricci_final.csv"
)
DEFAULT_DB_URL = "sqlite:///data/sqlite/marxist-data-3NF.sqlite"

#: CSV ``region_type`` → ``dim_country.world_system_tier`` (CHECK-constrained).
_TIER_BY_REGION_TYPE = {
    "CORE": "core",
    "SEMI_PERIPHERY": "semi_periphery",
    "PERIPHERY": "periphery",
}

#: CSV region names that are sovereign countries, not aggregates.
_NON_REGION_NAMES = frozenset({"China", "India"})


def get_or_create_time(session: Session, year: int) -> DimTime:
    time_entry = session.execute(
        select(DimTime).where(DimTime.year == year, DimTime.is_annual.is_(True))
    ).scalar_one_or_none()
    if not time_entry:
        time_entry = DimTime(year=year, is_annual=True)
        session.add(time_entry)
        session.flush()
    return time_entry


def _next_ric_code(session: Session) -> str:
    """Synthesize the next free RICnn cty_code (cty_code is UNIQUE)."""
    existing = session.execute(
        select(func.count()).select_from(DimCountry).where(DimCountry.cty_code.like("RIC%"))
    ).scalar_one()
    return f"RIC{existing + 1:02d}"


def get_or_create_country(session: Session, name: str, region_type: str) -> DimCountry:
    tier = _TIER_BY_REGION_TYPE[region_type]
    country = session.execute(
        select(DimCountry).where(DimCountry.country_name == name)
    ).scalar_one_or_none()
    if country:
        if country.world_system_tier is None:
            # Additive fill only — never re-tier an already-classified row.
            country.world_system_tier = tier
        return country
    country = DimCountry(
        cty_code=_next_ric_code(session),
        country_name=name,
        is_region=name not in _NON_REGION_NAMES,
        world_system_tier=tier,
    )
    session.add(country)
    session.flush()
    return country


def ingest_ricci_unequal(csv_path: Path, db_url: str) -> int:
    """Ingest the Ricci TOTAL transfer rows into ``fact_ricci_unequal_exchange``.

    Returns:
        Number of rows inserted.
    """
    if not csv_path.exists():
        msg = f"Ricci CSV not found at {csv_path}"
        raise FileNotFoundError(msg)

    engine = create_engine(db_url)

    # Drop + recreate the target table for idempotency.
    FactRicciUnequalExchange.__table__.drop(engine, checkfirst=True)
    NormalizedBase.metadata.create_all(engine, tables=[FactRicciUnequalExchange.__table__])

    inserted = 0
    with Session(engine) as session, csv_path.open() as fh:
        for row in csv.DictReader(fh):
            if row["transfer_type"].strip() != "TOTAL":
                continue
            time = get_or_create_time(session, int(row["year"]))
            country = get_or_create_country(
                session, row["region_name"].strip(), row["region_type"].strip()
            )
            session.add(
                FactRicciUnequalExchange(
                    time_id=time.time_id,
                    country_id=country.country_id,
                    trade_volume_billions=None,
                    ue_transfer_billions=float(row["signed_value"]),
                )
            )
            inserted += 1
        session.commit()

    return inserted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--db", type=str, default=DEFAULT_DB_URL)
    args = parser.parse_args(argv)

    n = ingest_ricci_unequal(args.csv, args.db)
    print(f"Inserted {n} rows into fact_ricci_unequal_exchange from {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
