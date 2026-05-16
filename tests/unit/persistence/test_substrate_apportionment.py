"""Unit tests for Bug C — substrate apportionment (spec-066 US5).

Spec: 066-marx-coherence-fixes (T061-T063).

Energy reserves follow population (where consumption + storage happens).
Raw material stocks follow geological / land area (where mining happens).
Currently both substrate stocks fall back to the per-hex default value
(symmetric across counties); the spec-066 fix introduces per-county
population-weighted vs area-weighted apportionment factors.

Verifies the mean-normalized apportionment math + the graceful fallback
when area data is missing.
"""

from __future__ import annotations

import sqlite3

import pytest

from babylon.persistence.hex_hydrator import (
    _CalibrationAlarm,
    _fetch_per_county_substrate_apportionment,
)

pytestmark = [pytest.mark.unit]


def _build_minimal_sqlite(
    *,
    counties_with_pop_area: list[tuple[str, float, float]],
    year: int = 2010,
) -> sqlite3.Connection:
    """In-memory SQLite mirroring the schema needed by
    _fetch_per_county_substrate_apportionment.

    Each tuple is (fips, population, area_sq_km). Pass area_sq_km<=0 to
    simulate missing-area fallback.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE dim_county (county_id INTEGER PRIMARY KEY, fips TEXT);
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER);
        CREATE TABLE dim_county_geometry (
            county_id INTEGER PRIMARY KEY,
            area_sq_km REAL
        );
        CREATE TABLE fact_census_income (
            county_id INTEGER, source_id INTEGER, bracket_id INTEGER,
            time_id INTEGER, race_id INTEGER, household_count INTEGER
        );
        """
    )
    conn.execute("INSERT INTO dim_time VALUES (?, ?)", (1, year))
    for i, (fips, pop, area) in enumerate(counties_with_pop_area, start=1):
        conn.execute("INSERT INTO dim_county VALUES (?, ?)", (i, fips))
        if area > 0:
            conn.execute("INSERT INTO dim_county_geometry VALUES (?, ?)", (i, area))
        if pop > 0:
            conn.execute(
                "INSERT INTO fact_census_income VALUES (?, ?, ?, ?, ?, ?)",
                (i, 1, 1, 1, 1, int(pop)),
            )
    conn.commit()
    return conn


def test_energy_population_weighted() -> None:
    """T061: energy_stock follows population_share.

    For a 2-county scenario with populations (700K, 300K) and equal area,
    the pop_factor should be (1.4, 0.6) — i.e., the high-population
    county gets a 1.4× multiplier on initial_energy_per_hex.
    """
    conn = _build_minimal_sqlite(
        counties_with_pop_area=[
            ("26163", 700_000, 1000.0),
            ("26099", 300_000, 1000.0),
        ],
    )
    apportionment = _fetch_per_county_substrate_apportionment(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
    )
    wayne_pop, _ = apportionment["26163"]
    macomb_pop, _ = apportionment["26099"]

    # mean_pop = 500_000; factors = (700/500, 300/500) = (1.4, 0.6)
    assert wayne_pop == pytest.approx(1.4, rel=1e-9)
    assert macomb_pop == pytest.approx(0.6, rel=1e-9)
    # Mean must be 1.0 across the scope.
    assert (wayne_pop + macomb_pop) / 2 == pytest.approx(1.0, rel=1e-9)


def test_raw_material_area_weighted() -> None:
    """T062: raw_material_stock follows area_share.

    For a 2-county scenario with equal population and areas (400, 600),
    the area_factor should be (0.8, 1.2).
    """
    conn = _build_minimal_sqlite(
        counties_with_pop_area=[
            ("26163", 500_000, 400.0),
            ("26099", 500_000, 600.0),
        ],
    )
    apportionment = _fetch_per_county_substrate_apportionment(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
    )
    _, wayne_area = apportionment["26163"]
    _, macomb_area = apportionment["26099"]

    # mean_area = 500; factors = (400/500, 600/500) = (0.8, 1.2)
    assert wayne_area == pytest.approx(0.8, rel=1e-9)
    assert macomb_area == pytest.approx(1.2, rel=1e-9)
    assert (wayne_area + macomb_area) / 2 == pytest.approx(1.0, rel=1e-9)


def test_missing_area_falls_back_to_population_share() -> None:
    """T067: graceful fallback when area_sq_km is unpopulated.

    The county receives area_factor == pop_factor AND a calibration
    alarm is appended.
    """
    conn = _build_minimal_sqlite(
        counties_with_pop_area=[
            ("26163", 700_000, 0.0),  # missing area
            ("26099", 300_000, 1000.0),
        ],
    )
    alarms: list[_CalibrationAlarm] = []
    apportionment = _fetch_per_county_substrate_apportionment(
        conn=conn,
        counties=frozenset({"26163", "26099"}),
        year=2010,
        audit_alarms=alarms,
    )
    wayne_pop, wayne_area = apportionment["26163"]
    # Fallback: area_factor == pop_factor for the area-missing county.
    assert wayne_pop == pytest.approx(1.4, rel=1e-9)
    assert wayne_area == pytest.approx(wayne_pop, rel=1e-9)
    # Alarm was emitted.
    assert any(a.invariant_name == "county_area_missing_falls_back_to_population" for a in alarms)
    assert any(a.county_fips == "26163" for a in alarms)


def test_energy_neq_raw_material_when_counties_differ() -> None:
    """T063 / SC-008: counties with population_share ≠ area_share produce
    distinct (pop_factor, area_factor) pairs.

    For a 3-county scenario where pop and area distributions differ, every
    county should show (pop_factor, area_factor) with distinct values.
    """
    conn = _build_minimal_sqlite(
        counties_with_pop_area=[
            ("26163", 700_000, 200.0),  # high pop, low area (urban)
            ("26083", 50_000, 5000.0),  # low pop, huge area (rural)
            ("26099", 250_000, 800.0),  # medium-medium
        ],
    )
    apportionment = _fetch_per_county_substrate_apportionment(
        conn=conn,
        counties=frozenset({"26163", "26083", "26099"}),
        year=2010,
    )
    distinct_count = sum(
        1 for (pop_f, area_f) in apportionment.values() if abs(pop_f - area_f) > 0.01
    )
    assert distinct_count == 3, (
        f"expected all 3 counties to have distinct pop/area factors, "
        f"got {distinct_count}: {apportionment}"
    )
