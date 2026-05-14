"""TIGER county geometry ingestion into Postgres (Spec-063 follow-up, 2026-05-14).

Loads the TIGER ``tl_<year>_us_county.shp`` shapefile (US Census Bureau
2024 vintage by default) into the ``immutable_reference_tiger_county``
table as WKT in a TEXT column. The ingestion is **idempotent**: re-running
against an already-populated table is a no-op (``ON CONFLICT DO NOTHING``).

The TEXT-WKT representation is chosen for portability — it works on any
Postgres deployment without PostGIS. Downstream readers load WKT back
into Shapely via ``shapely.wkt.loads()``.

**Two sources supported**:

- ``sqlite`` (canonical, default since 2026-05-14): reads from the
  reference DB at ``data/sqlite/marxist-data-3NF.sqlite``, joining
  ``dim_county`` ⨝ ``dim_county_geometry`` ⨝ ``dim_state``. The reference
  DB itself was populated from the 2024 TIGER shapefile via
  ``scripts/load_county_geometry_and_h3.py``. Covers 50 states + DC +
  Puerto Rico (3,222 rows).
- ``shapefile`` (back-compat): reads ``tl_<year>_us_county.shp`` directly
  via geopandas. Covers 50 states + DC + Puerto Rico + 4 Pacific
  territories (American Samoa, Guam, NMI, USVI — 3,235 rows total).

**Reproducibility**::

    # Default: load from SQLite reference DB (no 132 MB shapefile dependency)
    poetry run python -m babylon.persistence.tiger_ingestion

    # Or explicit:
    poetry run python -m babylon.persistence.tiger_ingestion --source sqlite

    # Legacy path (still supported):
    poetry run python -m babylon.persistence.tiger_ingestion --source shapefile

    # Programmatic:
    from babylon.persistence.tiger_ingestion import (
        ingest_tiger_counties_from_sqlite,
        ingest_tiger_counties_from_shapefile,
    )

See Also:
    ``src/babylon/persistence/migrations/0018_tiger_county_geometry.sql``
    :func:`babylon.persistence.hex_hydrator.hydrate_hex_state`
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_DEFAULT_TIGER_PATH = Path("data/tiger/county/tl_2024_us_county.shp")
_DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")
_DEFAULT_TIGER_VINTAGE = "2024"

_INSERT_SQL = """
    INSERT INTO immutable_reference_tiger_county
        (geoid, state_fips, county_fips, name, namelsad,
         geometry_wkt, tiger_vintage)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (geoid) DO NOTHING
"""

# Suffix-strip table for deriving TIGER short ``NAME`` from the ``NAMELSAD``-style
# value stored as ``dim_county.county_name`` in the reference DB. Order matters:
# longer suffixes must come first ("City and Borough" before "Borough").
_NAMELSAD_SUFFIXES_FOR_NAME_STRIP: tuple[str, ...] = (
    " City and Borough",  # Alaska (e.g., "Yakutat City and Borough" → "Yakutat")
    " Census Area",  # Alaska
    " Planning Region",  # Connecticut (replaced counties in 2022)
    " Municipality",  # Alaska
    " Municipio",  # Puerto Rico
    " Borough",  # Alaska
    " Parish",  # Louisiana
    " County",  # 48 contiguous states + most of AK/HI
    " city",  # Virginia / Nevada independent cities (lowercase 'c')
)


def _short_name_from_namelsad(namelsad: str) -> str:
    """Derive TIGER short ``NAME`` from ``NAMELSAD`` by stripping the type suffix.

    Returns the input unchanged when no recognized suffix matches (e.g.,
    "District of Columbia"). Exact for all 3,222 SQLite-resident rows as
    of 2026-05-14.
    """
    for suffix in _NAMELSAD_SUFFIXES_FOR_NAME_STRIP:
        if namelsad.endswith(suffix):
            return namelsad[: -len(suffix)]
    return namelsad


def _insert_tiger_rows(
    pool: ConnectionPool,
    payload: list[tuple[str, str, str, str, str, str, str]],
) -> int:
    """Apply ``ON CONFLICT DO NOTHING`` INSERTs and return rows actually inserted."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
        result = cur.fetchone()
        before = int(result[0]) if result else 0
        cur.executemany(_INSERT_SQL, payload)
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
        result = cur.fetchone()
        after = int(result[0]) if result else 0
    inserted = after - before
    logger.info(
        "TIGER ingestion: %d rows already present, %d rows inserted, %d total",
        before,
        inserted,
        after,
    )
    return inserted


def ingest_tiger_counties_from_shapefile(
    pool: ConnectionPool,
    shapefile_path: Path | None = None,
    *,
    tiger_vintage: str = _DEFAULT_TIGER_VINTAGE,
) -> int:
    """Load TIGER county polygons into Postgres directly from the shapefile.

    Args:
        pool: Postgres connection pool (psycopg_pool.ConnectionPool).
        shapefile_path: Path to ``tl_<year>_us_county.shp``. Defaults to
            ``data/tiger/county/tl_2024_us_county.shp`` relative to CWD.
        tiger_vintage: Census vintage year string (stored alongside each row
            for auditability — e.g., ``"2024"``).

    Returns:
        Number of rows actually inserted (existing rows skipped via
        ``ON CONFLICT (geoid) DO NOTHING``).
    """
    import geopandas as gpd  # type: ignore[import-untyped]

    path = shapefile_path or _DEFAULT_TIGER_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"TIGER county shapefile not found at {path}; "
            "place the file or pass shapefile_path= explicitly"
        )

    logger.info("Reading TIGER county shapefile from %s ...", path)
    gdf = gpd.read_file(
        path, columns=["GEOID", "STATEFP", "COUNTYFP", "NAME", "NAMELSAD", "geometry"]
    )
    logger.info("Loaded %d TIGER county rows; preparing INSERT payload", len(gdf))

    payload: list[tuple[str, str, str, str, str, str, str]] = [
        (
            row["GEOID"],
            row["STATEFP"],
            row["COUNTYFP"],
            row["NAME"],
            row["NAMELSAD"],
            row["geometry"].wkt,
            tiger_vintage,
        )
        for _, row in gdf.iterrows()
    ]
    return _insert_tiger_rows(pool, payload)


def ingest_tiger_counties_from_sqlite(
    pool: ConnectionPool,
    sqlite_path: Path | None = None,
    *,
    tiger_vintage: str = _DEFAULT_TIGER_VINTAGE,
) -> int:
    """Load TIGER county polygons into Postgres from the SQLite reference DB.

    Reads ``dim_county`` ⨝ ``dim_county_geometry`` ⨝ ``dim_state``, where
    ``dim_county.county_name`` holds the canonical ``NAMELSAD`` value
    (e.g., "Autauga County", "Yakutat City and Borough"). The TIGER
    short ``NAME`` is derived via :func:`_short_name_from_namelsad`.

    Args:
        pool: Postgres connection pool (psycopg_pool.ConnectionPool).
        sqlite_path: Path to ``marxist-data-3NF.sqlite``. Defaults to
            ``data/sqlite/marxist-data-3NF.sqlite`` relative to CWD.
        tiger_vintage: Census vintage year string stored alongside each row.
            Must match the vintage of the shapefile originally loaded into
            SQLite (``scripts/load_county_geometry_and_h3.py`` uses 2024).

    Returns:
        Number of rows actually inserted (existing rows skipped via
        ``ON CONFLICT (geoid) DO NOTHING``).
    """
    path = sqlite_path or _DEFAULT_SQLITE_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"SQLite reference DB not found at {path}; run "
            "scripts/load_county_geometry_and_h3.py first to populate it"
        )

    logger.info("Reading TIGER county geometries from SQLite at %s ...", path)
    query = """
        SELECT
            c.fips           AS geoid,
            s.state_fips     AS state_fips,
            c.county_fips    AS county_fips,
            c.county_name    AS namelsad,
            cg.geometry_wkt  AS geometry_wkt
        FROM dim_county_geometry cg
        JOIN dim_county c ON cg.county_id = c.county_id
        JOIN dim_state  s ON c.state_id  = s.state_id
        WHERE cg.geometry_wkt IS NOT NULL
        ORDER BY c.fips
    """
    with sqlite3.connect(path) as sqlite_conn:
        rows = sqlite_conn.execute(query).fetchall()
    logger.info("Loaded %d SQLite TIGER rows; preparing INSERT payload", len(rows))

    payload: list[tuple[str, str, str, str, str, str, str]] = [
        (
            geoid,
            state_fips,
            county_fips,
            _short_name_from_namelsad(namelsad),
            namelsad,
            geometry_wkt,
            tiger_vintage,
        )
        for (geoid, state_fips, county_fips, namelsad, geometry_wkt) in rows
    ]
    return _insert_tiger_rows(pool, payload)


def ingest_tiger_counties(
    pool: ConnectionPool,
    shapefile_path: Path | None = None,
    *,
    tiger_vintage: str = _DEFAULT_TIGER_VINTAGE,
) -> int:
    """Back-compat alias for :func:`ingest_tiger_counties_from_shapefile`.

    Preserved so existing callers (notably ``tests/integration/test_hex_hydration.py``'s
    ``tiger_geometries_ingested`` fixture) keep working. New code should call
    :func:`ingest_tiger_counties_from_sqlite` directly.
    """
    return ingest_tiger_counties_from_shapefile(pool, shapefile_path, tiger_vintage=tiger_vintage)


def fetch_county_geometry_wkt(pool: ConnectionPool, geoid: str) -> str | None:
    """Return the WKT geometry for a single county FIPS, or None if absent."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT geometry_wkt FROM immutable_reference_tiger_county WHERE geoid = %s",
            (geoid,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def fetch_county_geometries_wkt(pool: ConnectionPool, geoids: frozenset[str]) -> dict[str, str]:
    """Return ``{geoid: wkt}`` for the requested counties."""
    if not geoids:
        return {}
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT geoid, geometry_wkt
            FROM immutable_reference_tiger_county
            WHERE geoid = ANY(%s)
            """,
            (sorted(geoids),),
        )
        rows = cur.fetchall()
    return dict(rows)


def _cli() -> int:
    """Entry point for ``python -m babylon.persistence.tiger_ingestion``."""
    parser = argparse.ArgumentParser(
        description=(
            "Ingest TIGER county geometries into immutable_reference_tiger_county. "
            "Default source is the SQLite reference DB; pass --source shapefile to "
            "read the raw TIGER shapefile instead. Idempotent."
        )
    )
    parser.add_argument(
        "--source",
        choices=("sqlite", "shapefile"),
        default="sqlite",
        help="Where to read TIGER rows from (default: %(default)s)",
    )
    parser.add_argument(
        "--shapefile",
        type=Path,
        default=_DEFAULT_TIGER_PATH,
        help="Path to tl_<year>_us_county.shp (used when --source=shapefile, default: %(default)s)",
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=_DEFAULT_SQLITE_PATH,
        help="Path to marxist-data-3NF.sqlite (used when --source=sqlite, default: %(default)s)",
    )
    parser.add_argument(
        "--vintage",
        default=_DEFAULT_TIGER_VINTAGE,
        help="Census vintage year string (default: %(default)s)",
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get(
            "BABYLON_PG_DSN",
            os.environ.get(
                "BABYLON_TEST_PG_DSN",
                "dbname=babylon_test host=localhost port=5433 user=test password=test",
            ),
        ),
        help="Postgres DSN (defaults to BABYLON_PG_DSN env var)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from psycopg_pool import ConnectionPool

    with ConnectionPool(args.dsn, min_size=1, max_size=2, open=True) as pool:
        # Apply migration first (idempotent via IF NOT EXISTS in the SQL).
        migration_path = Path(__file__).parent / "migrations" / "0018_tiger_county_geometry.sql"
        with pool.connection() as conn:
            conn.autocommit = True
            conn.execute(migration_path.read_text())
        if args.source == "sqlite":
            inserted = ingest_tiger_counties_from_sqlite(
                pool, args.sqlite_path, tiger_vintage=args.vintage
            )
        else:
            inserted = ingest_tiger_counties_from_shapefile(
                pool, args.shapefile, tiger_vintage=args.vintage
            )
        print(f"Inserted {inserted} new TIGER county rows (source={args.source}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = [
    "fetch_county_geometries_wkt",
    "fetch_county_geometry_wkt",
    "ingest_tiger_counties",
    "ingest_tiger_counties_from_shapefile",
    "ingest_tiger_counties_from_sqlite",
]
