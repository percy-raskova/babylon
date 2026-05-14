"""TIGER county geometry ingestion into Postgres (Spec-063 follow-up, 2026-05-14).

Loads the TIGER ``tl_<year>_us_county.shp`` shapefile (US Census Bureau
2024 vintage by default) into the ``immutable_reference_tiger_county``
table as WKT in a TEXT column. The ingestion is **idempotent**: re-running
against an already-populated table is a no-op (``ON CONFLICT DO NOTHING``).

The TEXT-WKT representation is chosen for portability — it works on any
Postgres deployment without PostGIS. Downstream readers load WKT back
into Shapely via ``shapely.wkt.loads()``.

**Reproducibility**:

    # Operator one-shot ingestion (after Postgres is up):
    poetry run python -m babylon.persistence.tiger_ingestion

    # Or programmatically from tests / scripts:
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties
    count = ingest_tiger_counties(pool, shapefile_path)

See Also:
    ``src/babylon/persistence/migrations/0018_tiger_county_geometry.sql``
    :func:`babylon.persistence.hex_hydrator.hydrate_hex_state`
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_DEFAULT_TIGER_PATH = Path("data/tiger/county/tl_2024_us_county.shp")
_DEFAULT_TIGER_VINTAGE = "2024"


def ingest_tiger_counties(
    pool: ConnectionPool,
    shapefile_path: Path | None = None,
    *,
    tiger_vintage: str = _DEFAULT_TIGER_VINTAGE,
) -> int:
    """Load TIGER county polygons into ``immutable_reference_tiger_county``.

    Idempotent: rows present in the table are skipped via
    ``ON CONFLICT (geoid) DO NOTHING``. Re-running after a partial load
    safely completes; explicit re-load requires a manual ``TRUNCATE``.

    Args:
        pool: Postgres connection pool (psycopg_pool.ConnectionPool).
        shapefile_path: Path to ``tl_<year>_us_county.shp``. Defaults to
            ``data/tiger/county/tl_2024_us_county.shp`` relative to CWD.
        tiger_vintage: Census vintage year string (stored alongside each row
            for auditability — e.g., ``"2024"``).

    Returns:
        Number of rows actually inserted (existing rows are not counted).
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

    with pool.connection() as conn, conn.cursor() as cur:
        # Count rows before insert so we can report actual inserts.
        cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
        result = cur.fetchone()
        before = int(result[0]) if result else 0
        cur.executemany(
            """
            INSERT INTO immutable_reference_tiger_county
                (geoid, state_fips, county_fips, name, namelsad,
                 geometry_wkt, tiger_vintage)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (geoid) DO NOTHING
            """,
            payload,
        )
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
            "Ingest the TIGER county shapefile into immutable_reference_tiger_county. Idempotent."
        )
    )
    parser.add_argument(
        "--shapefile",
        type=Path,
        default=_DEFAULT_TIGER_PATH,
        help="Path to tl_<year>_us_county.shp (default: %(default)s)",
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
        inserted = ingest_tiger_counties(pool, args.shapefile, tiger_vintage=args.vintage)
        print(f"Inserted {inserted} new TIGER county rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = [
    "fetch_county_geometries_wkt",
    "fetch_county_geometry_wkt",
    "ingest_tiger_counties",
]
