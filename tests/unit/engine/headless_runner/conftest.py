"""Shared fixtures for headless-runner unit tests.

Spec: 069-sqlite-cache-optimization (used by Phase 3 cache tests).

Provides ``build_test_sqlite``: a helper that constructs a minimal
SQLite reference DB at a caller-supplied path with the four tables the
cache hydrate path queries (``dim_county``, ``dim_time``,
``fact_census_income``, ``fact_qcew_annual``) plus the small set of
parent dim tables FK declarations reference. Pre-spec-067 schema
(canonical-leaf-only ``fact_qcew_annual``) is preserved.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path

import pytest


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create the subset of tables the cache hydrate path needs.

    FK enforcement is off by default in SQLite; we still declare the
    constraints so the schema mirrors production. Tables not touched
    by the cache (``dim_industry``, ``dim_ownership``,
    ``dim_data_source``, ``dim_income_bracket``, ``dim_race``,
    ``dim_state``) are omitted — joins in the cache SQL only reach
    ``dim_county`` and ``dim_time``.
    """
    conn.executescript(
        """
        CREATE TABLE dim_county (
            county_id INTEGER PRIMARY KEY,
            fips VARCHAR(5) NOT NULL UNIQUE,
            state_id INTEGER NOT NULL,
            county_fips VARCHAR(3) NOT NULL,
            county_name VARCHAR(200) NOT NULL,
            h3_res4 VARCHAR(15)
        );
        CREATE TABLE dim_time (
            time_id INTEGER PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER,
            quarter INTEGER,
            is_annual BOOLEAN NOT NULL
        );
        CREATE TABLE fact_census_income (
            county_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            bracket_id INTEGER NOT NULL,
            time_id INTEGER NOT NULL,
            race_id INTEGER NOT NULL,
            household_count INTEGER NOT NULL,
            PRIMARY KEY (county_id, source_id, bracket_id, time_id, race_id)
        );
        CREATE TABLE fact_qcew_annual (
            county_id INTEGER,
            industry_id INTEGER,
            ownership_id INTEGER,
            time_id INTEGER,
            establishments INTEGER,
            employment INTEGER,
            total_wages_usd NUMERIC,
            avg_weekly_wage_usd INTEGER,
            avg_annual_pay_usd INTEGER,
            lq_employment NUMERIC,
            lq_annual_pay NUMERIC,
            disclosure_code TEXT
        );
        """
    )


def build_test_sqlite(
    path: Path,
    *,
    census_rows: Mapping[tuple[str, int], int] | None = None,
    qcew_rows: Mapping[tuple[str, int], int] | None = None,
) -> Path:
    """Build a minimal SQLite reference DB at ``path``.

    Args:
        path:         Target file path (use ``tmp_path / "ref.sqlite"``).
        census_rows:  ``{(fips, year): household_count}``. Each entry
                      becomes one row in ``fact_census_income`` summed by
                      `(county_id, time_id)`; the cache's primary
                      population SUM recovers it.
        qcew_rows:    ``{(fips, year): employment}``. Each entry becomes
                      one row in ``fact_qcew_annual`` summed by
                      `(county_id, time_id)`; the cache uses this both
                      as employment proxy AND (×0.33) as population
                      fallback when Census is missing.

    Returns:
        ``path`` (for fluent ``build_test_sqlite(...).exists()`` chains).
    """
    census_rows = census_rows or {}
    qcew_rows = qcew_rows or {}

    fips_set = sorted({fips for fips, _ in (*census_rows.keys(), *qcew_rows.keys())})
    year_set = sorted({year for _, year in (*census_rows.keys(), *qcew_rows.keys())})

    fips_to_id = {fips: i for i, fips in enumerate(fips_set, start=1)}
    year_to_id = {year: i for i, year in enumerate(year_set, start=1)}

    conn = sqlite3.connect(path)
    try:
        _create_schema(conn)

        conn.executemany(
            "INSERT INTO dim_county (county_id, fips, state_id, county_fips, county_name) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (fips_to_id[fips], fips, int(fips[:2]), fips[2:], f"Test County {fips}")
                for fips in fips_set
            ],
        )
        conn.executemany(
            "INSERT INTO dim_time (time_id, year, is_annual) VALUES (?, ?, 1)",
            [(year_to_id[year], year) for year in year_set],
        )
        conn.executemany(
            "INSERT INTO fact_census_income "
            "(county_id, source_id, bracket_id, time_id, race_id, household_count) "
            "VALUES (?, 1, 1, ?, 1, ?)",
            [
                (fips_to_id[fips], year_to_id[year], count)
                for (fips, year), count in census_rows.items()
            ],
        )
        conn.executemany(
            "INSERT INTO fact_qcew_annual "
            "(county_id, industry_id, ownership_id, time_id, employment) "
            "VALUES (?, 1, 1, ?, ?)",
            [(fips_to_id[fips], year_to_id[year], emp) for (fips, year), emp in qcew_rows.items()],
        )
        conn.commit()
    finally:
        conn.close()
    return path


@pytest.fixture
def simple_ref_sqlite(tmp_path: Path) -> Path:
    """A tiny reference DB with 2 counties × 2 years (4 tuples).

    - 26163 / 2010: Census=100, QCEW=50  → pop=100, emp=50.0
    - 26163 / 2011: Census=200, QCEW=60  → pop=200, emp=60.0
    - 26125 / 2010: Census=0,   QCEW=70  → pop=int(70*0.33)=23, emp=70.0 (Census fallback)
    - 26125 / 2011: Census missing entirely, QCEW missing → pop=None, emp=None
    """
    return build_test_sqlite(
        tmp_path / "simple_ref.sqlite",
        census_rows={
            ("26163", 2010): 100,
            ("26163", 2011): 200,
            # 26125/2010 omitted (Census fallback to QCEW)
            # 26125/2011 omitted (no data either source)
        },
        qcew_rows={
            ("26163", 2010): 50,
            ("26163", 2011): 60,
            ("26125", 2010): 70,
            # 26125/2011 omitted (both missing)
        },
    )
