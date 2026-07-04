"""Unit tests for the spec-101 county-exposure map loader.

Uses a synthetic temp SQLite (no external reference DB) so the tests are fast,
deterministic, and encode the D2 scope-renormalisation + bloc-invariance
contract directly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from babylon.economics.county_exposure import (
    CountyExposureUnavailableError,
    load_county_exposure_map,
)

pytestmark = [pytest.mark.unit]

_YEAR = 2010
_ANNUAL_TIME_ID = 14


def _build_reference(path: Path) -> None:
    """Create a minimal reference SQLite with two bloc-invariant exposure maps."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE dim_county (county_id INTEGER PRIMARY KEY, fips TEXT);
        CREATE TABLE fact_county_exposure_by_external (
            time_id INTEGER, external_country_id INTEGER, county_id INTEGER, weight REAL
        );
        """
    )
    conn.execute("INSERT INTO dim_time VALUES (?,?,1)", (_ANNUAL_TIME_ID, _YEAR))
    # a non-annual 2010 row must be ignored by the loader
    conn.execute("INSERT INTO dim_time VALUES (99, ?, 0)", (_YEAR,))
    counties = {1: "26163", 2: "26125", 3: "26099", 4: "36061"}
    for cid, fips in counties.items():
        conn.execute("INSERT INTO dim_county VALUES (?,?)", (cid, fips))
    # Bloc-invariant: blocs 1 and 12 carry IDENTICAL per-county weights that sum to 1.0.
    weights = {1: 0.10, 2: 0.20, 3: 0.30, 4: 0.40}
    for bloc in (1, 12):
        for cid, w in weights.items():
            conn.execute(
                "INSERT INTO fact_county_exposure_by_external VALUES (?,?,?,?)",
                (_ANNUAL_TIME_ID, bloc, cid, w),
            )
    conn.commit()
    conn.close()


@pytest.fixture
def ref_db(tmp_path: Path) -> Path:
    path = tmp_path / "ref.sqlite"
    _build_reference(path)
    return path


def test_full_map_sums_to_one(ref_db: Path) -> None:
    m = load_county_exposure_map(sqlite_path=ref_db, year=_YEAR, scope_fips=None)
    assert set(m) == {"26163", "26125", "26099", "36061"}
    assert abs(sum(m.values()) - 1.0) < 1e-9
    # unchanged national weights (already unit-sum)
    assert m["36061"] == pytest.approx(0.40)


def test_scope_renormalises_to_unit_sum(ref_db: Path) -> None:
    tri = ["26163", "26125", "26099"]  # raw 0.10+0.20+0.30 = 0.60
    m = load_county_exposure_map(sqlite_path=ref_db, year=_YEAR, scope_fips=tri)
    assert set(m) == set(tri)
    assert abs(sum(m.values()) - 1.0) < 1e-9
    # renormalised: 0.30 / 0.60 = 0.5 for the largest of the three
    assert m["26099"] == pytest.approx(0.30 / 0.60)
    assert m["26163"] == pytest.approx(0.10 / 0.60)


def test_bloc_invariant_pick_is_stable(ref_db: Path) -> None:
    # Two calls read the same (smallest-id) bloc → identical map.
    a = load_county_exposure_map(sqlite_path=ref_db, year=_YEAR, scope_fips=None)
    b = load_county_exposure_map(sqlite_path=ref_db, year=_YEAR, scope_fips=None)
    assert a == b
    assert list(a) == sorted(a)  # deterministic sorted-FIPS order


def test_empty_scope_raises(ref_db: Path) -> None:
    with pytest.raises(CountyExposureUnavailableError):
        load_county_exposure_map(sqlite_path=ref_db, year=_YEAR, scope_fips=["99999"])


def test_missing_year_raises(ref_db: Path) -> None:
    with pytest.raises(CountyExposureUnavailableError):
        load_county_exposure_map(sqlite_path=ref_db, year=1999, scope_fips=None)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(CountyExposureUnavailableError):
        load_county_exposure_map(sqlite_path=tmp_path / "nope.sqlite", year=_YEAR, scope_fips=None)
