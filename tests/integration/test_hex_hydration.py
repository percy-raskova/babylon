"""Integration tests for hex graph hydration at session init (Spec-063 closure).

Verifies the new ``hydrate_hex_state`` path produces a populated
``dynamic_hex_state`` table at tick 0 for the Detroit tri-county scope,
unblocking spec-063 T013/T014/T036/T046/T052/T055.

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN).
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
    pytest.mark.skipif(
        not Path("data/tiger/county/tl_2024_us_county.shp").exists(),
        reason="TIGER county shapefile not present at data/tiger/county/",
    ),
    pytest.mark.skipif(
        not Path("data/sqlite/marxist-data-3NF.sqlite").exists(),
        reason="SQLite reference DB not present at data/sqlite/",
    ),
]


DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]
DETROIT_TRI_COUNTY_SET = frozenset(DETROIT_TRI_COUNTY)


@pytest.fixture
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def apply_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture
def tiger_geometries_ingested(pg_pool, apply_migrations):  # type: ignore[no-untyped-def]
    """Ingest TIGER county geometries into Postgres (idempotent).

    Spec-063 follow-up requirement (2026-05-14): hex hydration relies on
    Postgres-resident TIGER geometries, not on-the-fly shapefile reads.
    """
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties

    ingest_tiger_counties(
        pg_pool,
        Path("data/tiger/county/tl_2024_us_county.shp"),
    )


@pytest.fixture
def runtime(pg_pool, apply_migrations, tiger_geometries_ingested):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def test_hex_count_populated_for_tri_county_scope(runtime) -> None:  # type: ignore[no-untyped-def]
    """Spec-063 closure: report.hex_count > 0 when hex_hydration_counties supplied."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
        runtime=runtime,
        defines=GameDefines.load_default(),
        start_year=2010,
        scenario_length_years=1,
        counties=DETROIT_TRI_COUNTY,
        hex_hydration_counties=DETROIT_TRI_COUNTY_SET,
    )
    assert report.hex_count > 0, "Hex hydration did not produce any rows"
    # Detroit tri-county at H3 res-7 should be in the 800–1500 range.
    assert 500 < report.hex_count < 3000, (
        f"hex_count {report.hex_count} outside expected tri-county range"
    )


def test_dynamic_hex_state_rows_match_report_count(runtime) -> None:  # type: ignore[no-untyped-def]
    """The actual Postgres row count must match InitializationReport.hex_count."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
        runtime=runtime,
        defines=GameDefines.load_default(),
        start_year=2010,
        scenario_length_years=1,
        counties=DETROIT_TRI_COUNTY,
        hex_hydration_counties=DETROIT_TRI_COUNTY_SET,
    )
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM dynamic_hex_state WHERE session_id = %s AND tick = 0",
            (sid,),
        )
        result = cur.fetchone()
        actual_count = result[0] if result else 0
    assert actual_count == report.hex_count


def test_hex_rows_satisfy_invariants(runtime) -> None:  # type: ignore[no-untyped-def]
    """Per-row invariants: FIPS prefix matches state, bounded fields in [0,1], v ≥ 0."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    initialize_session(
        session_id=sid,
        sqlite_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
        runtime=runtime,
        defines=GameDefines.load_default(),
        start_year=2010,
        scenario_length_years=1,
        counties=DETROIT_TRI_COUNTY,
        hex_hydration_counties=DETROIT_TRI_COUNTY_SET,
    )
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            """
            SELECT county_fips, state_fips, region_id, c, v, s, k,
                   biocapacity_stock, energy_stock, raw_material_stock,
                   internet_access_pct, surveillance_coupling
            FROM dynamic_hex_state
            WHERE session_id = %s AND tick = 0
            """,
            (sid,),
        )
        rows = cur.fetchall()
    assert rows, "No hex rows fetched — hydration likely failed"

    counties_seen: set[str] = set()
    for row in rows:
        county_fips, state_fips, region_id, c, v, s, k, bio, energy, raw, internet, surveil = row
        # State prefix invariant (spec-062 FR-023).
        assert state_fips == county_fips[:2]
        # Region must be from the canonical set.
        assert region_id == "east_north_central", f"Unexpected region: {region_id}"
        # Marx primitives non-negative.
        assert float(c) >= 0
        assert float(v) >= 0
        assert float(s) >= 0
        assert float(k) >= 0
        # Substrate stocks non-negative.
        assert float(bio) >= 0
        assert float(energy) >= 0
        assert float(raw) >= 0
        # Bounded fields in [0, 1].
        assert 0.0 <= float(internet) <= 1.0
        assert 0.0 <= float(surveil) <= 1.0
        counties_seen.add(county_fips)
    # All three tri-county FIPS must appear.
    assert counties_seen == DETROIT_TRI_COUNTY_SET, (
        f"Expected {DETROIT_TRI_COUNTY_SET}, got {counties_seen}"
    )


def test_no_hex_hydration_when_kwarg_omitted(runtime) -> None:  # type: ignore[no-untyped-def]
    """Back-compat: omitting hex_hydration_counties → report.hex_count == 0."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
        runtime=runtime,
        defines=GameDefines.load_default(),
        start_year=2010,
        scenario_length_years=1,
        counties=DETROIT_TRI_COUNTY,
        # No hex_hydration_counties → legacy back-compat path
    )
    assert report.hex_count == 0
