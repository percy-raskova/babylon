"""Contract tests for the sqlite-backed county-WKT provider (M5 Task 37).

Fixture-fed (CI's unit shard has no reference DB): a synthetic SQLite
with the three joined tables proves the query shape; the real-DB
nationwide pin rides the ``requires_reference_db`` tier.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from babylon.persistence.tiger_ingestion import fetch_county_geometries_wkt_from_sqlite

pytestmark = pytest.mark.unit


def _synthetic_db(path: Path) -> Path:
    db = path / "ref.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE dim_state (state_id INTEGER PRIMARY KEY, state_fips TEXT);
            CREATE TABLE dim_county (
                county_id INTEGER PRIMARY KEY, state_id INTEGER,
                fips TEXT, county_fips TEXT, county_name TEXT);
            CREATE TABLE dim_county_geometry (
                county_id INTEGER PRIMARY KEY, geometry_wkt TEXT);
            INSERT INTO dim_state VALUES (1, '26');
            INSERT INTO dim_county VALUES (10, 1, '26163', '163', 'Wayne County');
            INSERT INTO dim_county VALUES (11, 1, '26125', '125', 'Oakland County');
            INSERT INTO dim_county VALUES (12, 1, '26099', '099', 'Macomb County');
            INSERT INTO dim_county_geometry VALUES (10, 'POLYGON((0 0,1 0,1 1,0 0))');
            INSERT INTO dim_county_geometry VALUES (11, NULL);
            """
        )
    return db


def test_fetches_requested_counties_and_skips_null_geometry(tmp_path: Path) -> None:
    db = _synthetic_db(tmp_path)

    out = fetch_county_geometries_wkt_from_sqlite(
        frozenset({"26163", "26125", "26099", "99999"}), db
    )

    # 26163 has WKT; 26125's row is NULL (skipped); 26099 has no geometry
    # row; 99999 does not exist — all three absences are simply absent.
    assert out == {"26163": "POLYGON((0 0,1 0,1 1,0 0))"}


def test_empty_geoids_is_empty_without_touching_the_db(tmp_path: Path) -> None:
    assert fetch_county_geometries_wkt_from_sqlite(frozenset(), tmp_path / "nope.sq") == {}


def test_missing_db_raises_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        fetch_county_geometries_wkt_from_sqlite(frozenset({"26163"}), tmp_path / "absent.sqlite")


@pytest.mark.requires_reference_db
def test_real_reference_db_serves_nationwide_wkt() -> None:
    """The checked-in DB serves real geometry for the tri-county set (the
    3,222-row nationwide estate's spot pin)."""
    out = fetch_county_geometries_wkt_from_sqlite(
        frozenset({"26163", "26125", "26099"}),
        Path("data/sqlite/marxist-data-3NF.sqlite"),
    )

    assert set(out) == {"26163", "26125", "26099"}
    assert all(wkt.startswith(("POLYGON", "MULTIPOLYGON")) for wkt in out.values())
