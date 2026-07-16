"""Reference-DB ↔ in-repo CSV sync guards for the unequal-exchange tables.

The shipped CSVs (``src/babylon/data/reference/``) are the source of truth;
``tools/ingest/hickel_erdi.py`` / ``tools/ingest/ricci_unequal.py`` load them
into the reference SQLite. These tests prove the DB actually carries what the
CSVs say — catching partial ingests, silent re-ingest drift, and the
schema-only-table failure mode this data sat in until 2026-07-16
(``fact_ricci_unequal_exchange`` existed with 0 rows for months while the
raw CSV waited in the trove).
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
_REFERENCE_DIR = Path(__file__).resolve().parents[3] / "src" / "babylon" / "data" / "reference"
HICKEL_CSV = _REFERENCE_DIR / "babylon_hickel_final.csv"
RICCI_CSV = _REFERENCE_DIR / "babylon_ricci_final.csv"

pytestmark = [
    pytest.mark.requires_reference_db,
    pytest.mark.skipif(not SQLITE_REF.exists(), reason=f"reference DB missing at {SQLITE_REF}"),
]


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{SQLITE_REF}?mode=ro", uri=True)


def test_hickel_erdi_table_matches_csv() -> None:
    """fact_hickel_erdi_annual carries every CSV row, keyed (year, scale_type)."""
    with HICKEL_CSV.open() as fh:
        expected = {
            (int(r["year"]), r["scale_type"].strip()): (
                float(r["erdi"]),
                float(r["annual_drain_usd_billions"]),
            )
            for r in csv.DictReader(fh)
        }
    with _connect() as conn:
        rows = conn.execute(
            "SELECT dt.year, h.scale_type, h.erdi, h.annual_drain_usd_billions "
            "FROM fact_hickel_erdi_annual h JOIN dim_time dt ON dt.time_id = h.time_id"
        ).fetchall()
    actual = {(int(y), str(s)): (float(e), float(d)) for y, s, e, d in rows}
    assert set(actual) == set(expected), (
        f"key drift: db-only={sorted(set(actual) - set(expected))[:3]} "
        f"csv-only={sorted(set(expected) - set(actual))[:3]}"
    )
    for key, (erdi, drain) in expected.items():
        db_erdi, db_drain = actual[key]
        assert abs(db_erdi - erdi) <= 1e-9 and abs(db_drain - drain) <= 1e-6, (
            f"{key}: DB ({db_erdi}, {db_drain}) != CSV ({erdi}, {drain})"
        )


def test_ricci_table_matches_csv_total_rows() -> None:
    """fact_ricci_unequal_exchange == the CSV's TOTAL rows, signed values intact."""
    with RICCI_CSV.open() as fh:
        expected = {
            (int(r["year"]), r["region_name"].strip()): float(r["signed_value"])
            for r in csv.DictReader(fh)
            if r["transfer_type"].strip() == "TOTAL"
        }
    assert expected, "CSV must carry TOTAL rows"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT dt.year, c.country_name, f.ue_transfer_billions "
            "FROM fact_ricci_unequal_exchange f "
            "JOIN dim_time dt ON dt.time_id = f.time_id "
            "JOIN dim_country c ON c.country_id = f.country_id"
        ).fetchall()
    actual = {(int(y), str(n)): float(v) for y, n, v in rows}
    assert actual == pytest.approx(expected), "fact_ricci_unequal_exchange drifted from the CSV"


def test_ricci_regions_carry_world_system_tiers() -> None:
    """Every Ricci partner row is tier-classified (the CHECK-constrained axis
    the extraction-direction law reads from)."""
    with _connect() as conn:
        untiered = conn.execute(
            "SELECT DISTINCT c.country_name "
            "FROM fact_ricci_unequal_exchange f "
            "JOIN dim_country c ON c.country_id = f.country_id "
            "WHERE c.world_system_tier IS NULL"
        ).fetchall()
    assert not untiered, f"Ricci partners missing world_system_tier: {untiered}"


def test_ricci_sign_semantics_match_tier() -> None:
    """In the DB as in the source: core transfers positive (appropriation),
    (semi-)periphery negative (drain), every (year, partner) row."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT dt.year, c.country_name, c.world_system_tier, f.ue_transfer_billions "
            "FROM fact_ricci_unequal_exchange f "
            "JOIN dim_time dt ON dt.time_id = f.time_id "
            "JOIN dim_country c ON c.country_id = f.country_id"
        ).fetchall()
    assert rows, "fact_ricci_unequal_exchange is empty — run tools/ingest/ricci_unequal.py"
    for year, name, tier, transfer in rows:
        if tier == "core":
            assert transfer > 0, f"{year} {name}: core transfer {transfer} not positive"
        else:
            assert transfer < 0, f"{year} {name}: {tier} transfer {transfer} not negative"
