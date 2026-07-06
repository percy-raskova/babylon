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

_SQLITE_REF_DB = Path("data/sqlite/marxist-data-3NF.sqlite")
_sqlite_missing = pytest.mark.skipif(
    not _SQLITE_REF_DB.exists(),
    reason="SQLite reference DB not present at data/sqlite/marxist-data-3NF.sqlite",
)


@pytest.fixture
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def fresh_tiger_table(pg_pool):  # type: ignore[no-untyped-def]
    """Apply migrations + isolate TIGER truncation from concurrent sessions (#18).

    The TRUNCATE runs inside a pinned transaction (``autocommit=False``)
    wrapped by :class:`PinnedPool` so that every ``pool.connection()``
    call -- including those inside production code
    (``ingest_tiger_counties``, ``hydrate_hex_state``,
    ``persist_tick_atomic``) -- operates on the SAME transaction-scoped
    connection. Concurrent sessions on the shared ``babylon_test`` DB
    never see the empty table (Postgres MVCC). ``ROLLBACK`` on teardown
    restores all rows.

    Replaces the prior ``conn.autocommit = True; TRUNCATE ...`` pattern
    which committed the truncation immediately and zeroed TIGER for any
    concurrent lane -- the root cause of the hex_spatial_map silent-zero
    bug (spec-088 S3 / spec-102 STEP-0 guard).

    Note: uses ``DELETE`` rather than ``TRUNCATE`` because ``TRUNCATE``
    acquires an ``ACCESS EXCLUSIVE`` lock that blocks concurrent
    ``SELECT``s (defeating the isolation goal). ``DELETE`` takes only
    ``ROW EXCLUSIVE`` which is compatible with the ``ACCESS SHARE`` lock
    of concurrent readers, so a parallel lane's hex hydrator can still
    read TIGER geometry while this test runs.
    """
    import psycopg

    from tests.integration.conftest import PinnedPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]

    # Apply migrations (idempotent, autocommit) to ensure schema is fresh.
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())

    # Open an isolated transaction for the delete + all test operations.
    # autocommit=False + DELETE => the mutation is transactional and
    # invisible to concurrent sessions (Postgres MVCC). ROLLBACK on
    # teardown restores all rows. PinnedPool ensures production code
    # (which calls pool.connection()) operates on this same transaction.
    tx_conn = psycopg.connect(dsn, autocommit=False)
    tx_conn.execute("DELETE FROM immutable_reference_tiger_county")
    try:
        yield PinnedPool(tx_conn)
    finally:
        tx_conn.execute("ROLLBACK")
        tx_conn.close()


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


@_sqlite_missing
def test_ingest_from_sqlite_loads_us_counties_minus_pacific_territories(  # type: ignore[no-untyped-def]
    fresh_tiger_table,
) -> None:
    """Loading from SQLite covers 50 states + DC + PR (~3,222 rows).

    Pacific territories (American Samoa, Guam, NMI, USVI — 13 rows) are
    in the shapefile but not in the SQLite reference DB. Documented as
    expected scope difference between sources.
    """
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties_from_sqlite

    inserted = ingest_tiger_counties_from_sqlite(fresh_tiger_table, _SQLITE_REF_DB)
    assert 3000 < inserted < 3300, f"Expected ~3222 counties from SQLite, got {inserted}"

    with fresh_tiger_table.connection() as pg, pg.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
        total = cur.fetchone()[0]
        # Michigan has 83 counties; Wayne County (26163) MUST be present.
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county WHERE state_fips = '26'")
        michigan_count = cur.fetchone()[0]
        cur.execute(
            "SELECT name, namelsad FROM immutable_reference_tiger_county WHERE geoid = '26163'"
        )
        wayne = cur.fetchone()
    assert total == inserted
    assert michigan_count == 83
    assert wayne == ("Wayne", "Wayne County")


@_sqlite_missing
def test_ingest_from_sqlite_is_idempotent(fresh_tiger_table) -> None:  # type: ignore[no-untyped-def]
    """Running the SQLite-source ingestion twice does not duplicate rows."""
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties_from_sqlite

    first = ingest_tiger_counties_from_sqlite(fresh_tiger_table, _SQLITE_REF_DB)
    second = ingest_tiger_counties_from_sqlite(fresh_tiger_table, _SQLITE_REF_DB)
    assert first > 0
    assert second == 0, "Second SQLite-source ingestion should insert zero rows"


@_sqlite_missing
def test_ingest_from_sqlite_geometries_match_shapefile_for_sampled_fips(  # type: ignore[no-untyped-def]
    fresh_tiger_table,
) -> None:
    """SQLite and shapefile sources produce byte-identical WKT for sampled counties.

    Verifies that the SQLite reference DB faithfully mirrors the TIGER 2024
    shapefile. Samples Wayne (26163, Detroit), Cook (17031, Chicago),
    Los Angeles (06037), Harris (48201, Houston), and DC (11001).
    """
    from babylon.persistence.tiger_ingestion import (
        fetch_county_geometry_wkt,
        ingest_tiger_counties_from_shapefile,
        ingest_tiger_counties_from_sqlite,
    )

    sample_fips = ("26163", "17031", "06037", "48201", "11001")

    # First pass: load from SQLite, capture WKT for each sample
    ingest_tiger_counties_from_sqlite(fresh_tiger_table, _SQLITE_REF_DB)
    sqlite_wkts = {fips: fetch_county_geometry_wkt(fresh_tiger_table, fips) for fips in sample_fips}
    for fips, wkt in sqlite_wkts.items():
        assert wkt is not None, f"SQLite source did not produce WKT for {fips}"

    # Delete + reload from shapefile (within the pinned transaction; the
    # fixture's ROLLBACK on teardown restores the SQLite-loaded rows so
    # no concurrent session ever sees an empty table). Uses DELETE (not
    # TRUNCATE) to avoid blocking concurrent SELECTs with ACCESS EXCLUSIVE.
    with fresh_tiger_table.connection() as conn:
        conn.execute("DELETE FROM immutable_reference_tiger_county")
    ingest_tiger_counties_from_shapefile(
        fresh_tiger_table, Path("data/tiger/county/tl_2024_us_county.shp")
    )
    shapefile_wkts = {
        fips: fetch_county_geometry_wkt(fresh_tiger_table, fips) for fips in sample_fips
    }

    # WKT should be byte-identical (both sources serialize via shapely.wkt)
    for fips in sample_fips:
        assert sqlite_wkts[fips] == shapefile_wkts[fips], (
            f"WKT mismatch for {fips} between SQLite and shapefile sources"
        )


def test_fresh_tiger_table_isolates_truncation_from_concurrent_sessions(  # type: ignore[no-untyped-def]
    fresh_tiger_table,
) -> None:
    """#18 regression: fresh_tiger_table must not leak its TRUNCATE to
    concurrent sessions on the shared ``babylon_test`` database.

    Before the fix, ``fresh_tiger_table`` ran ``TRUNCATE
    immutable_reference_tiger_county`` with ``conn.autocommit = True``,
    committing the empty table immediately. Any concurrent lane (E2E
    regression, sim run, parallel pytest worker) that read TIGER geometry
    during the test window saw zero counties -- the root cause of the
    hex_spatial_map silent-zero bug (spec-088 S3).

    The fix wraps the TRUNCATE (and all test operations) in a pinned
    transaction (``PinnedPool``, ``autocommit=False``) so Postgres MVCC
    hides the mutation from concurrent sessions. This test opens a
    SEPARATE connection simulating a concurrent lane and verifies it
    still sees the TIGER data while the fixture's transaction is open.
    """
    import psycopg

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    concurrent = psycopg.connect(dsn, autocommit=True)
    try:
        with concurrent.cursor() as cur:
            # The fixture has already TRUNCATED (in its pinned transaction).
            # A concurrent session must still see the pre-TRUNCATE rows --
            # MVCC isolates the uncommitted transaction.
            cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
            row = cur.fetchone()
            count = int(row[0]) if row else 0
        assert count > 0, (
            f"Concurrent session sees {count} TIGER rows (expected >0); "
            "fresh_tiger_table leaked its truncation to concurrent sessions "
            "-- #18 regression"
        )
    finally:
        concurrent.close()
