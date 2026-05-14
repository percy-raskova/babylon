"""Integration tests for TIGER county geometry ingestion (Spec-063 follow-up)."""

from __future__ import annotations

import os
from pathlib import Path

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
]


@pytest.fixture
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def fresh_tiger_table(pg_pool):  # type: ignore[no-untyped-def]
    """Apply migrations + truncate immutable_reference_tiger_county for a clean test."""
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())
        conn.execute("TRUNCATE immutable_reference_tiger_county")
    return pg_pool


def test_ingest_loads_all_us_counties(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """Loading TIGER 2024 produces ~3,235 county rows (all US counties + territories)."""
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties

    inserted = ingest_tiger_counties(
        fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp")
    )
    assert 3000 < inserted < 4000, f"Expected ~3235 counties, got {inserted}"

    with fresh_tiger_table.connection() as pg, pg.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county WHERE state_fips = '26'")
        michigan_count = cur.fetchone()[0]
    assert total == inserted
    # Michigan has 83 counties (FIPS state code 26)
    assert michigan_count == 83


def test_ingest_is_idempotent(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """Running the ingestion twice does not duplicate rows (ON CONFLICT DO NOTHING)."""
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties

    first = ingest_tiger_counties(
        fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp")
    )
    second = ingest_tiger_counties(
        fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp")
    )
    assert first > 0
    assert second == 0, "Second ingestion should insert zero rows (idempotent)"


def test_fetch_county_geometry_returns_wkt_for_known_fips(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """Wayne County, Detroit (26163) round-trips via fetch_county_geometry_wkt."""
    from babylon.persistence.tiger_ingestion import (
        fetch_county_geometry_wkt,
        ingest_tiger_counties,
    )

    ingest_tiger_counties(fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp"))
    wkt = fetch_county_geometry_wkt(fresh_tiger_table, "26163")
    assert wkt is not None
    assert wkt.startswith("MULTIPOLYGON") or wkt.startswith("POLYGON")

    # Round-trip through shapely confirms valid WKT
    import shapely.wkt

    geom = shapely.wkt.loads(wkt)
    assert not geom.is_empty
    # Wayne County is in the Detroit area (lat ~42.3, lon ~-83.2)
    centroid = geom.centroid
    assert 42.0 < centroid.y < 43.0
    assert -84.0 < centroid.x < -82.5


def test_fetch_county_geometry_returns_none_for_unknown_fips(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """fetch_county_geometry_wkt('99999') returns None (no exception)."""
    from babylon.persistence.tiger_ingestion import (
        fetch_county_geometry_wkt,
        ingest_tiger_counties,
    )

    ingest_tiger_counties(fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp"))
    assert fetch_county_geometry_wkt(fresh_tiger_table, "99999") is None


def test_hex_hydrator_uses_postgres_resident_geometry(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """The hex hydrator queries the Postgres table, not the on-disk shapefile.

    Tests this by pointing the shapefile path at a nonexistent file: the
    hydrator should still succeed because the Postgres rows are populated.
    """
    from uuid import uuid4

    from babylon.config.defines import GameDefines
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.hex_hydrator import hydrate_hex_state
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties

    ingest_tiger_counties(fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp"))
    runtime = PostgresRuntime(pool=fresh_tiger_table)

    rows = hydrate_hex_state(
        runtime=runtime,
        session_id=uuid4(),
        counties=frozenset({"26163", "26125", "26099"}),
        start_year=2010,
        defines=GameDefines.load_default(),
        tiger_county_shapefile=Path("/tmp/nonexistent-shapefile.shp"),  # Postgres path wins
    )
    assert rows > 500, "Postgres-resident geometry query failed; expected ~1000 cells"
