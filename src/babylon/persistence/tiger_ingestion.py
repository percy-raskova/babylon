"""Read-only TIGER county-geometry access for Python data periphery.

Rust owns installation of the digest-pinned reference bundle. Python may read
either the source SQLite artifact or an already-installed PostgreSQL relation,
but this module exposes no ingestion or mutation command.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")


def fetch_county_geometries_wkt_from_sqlite(
    geoids: frozenset[str],
    sqlite_path: Path | None = None,
) -> dict[str, str]:
    """Read county WKT from the canonical SQLite reference artifact."""
    if not geoids:
        return {}
    path = sqlite_path or _DEFAULT_SQLITE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"SQLite reference DB not found at {path}")
    placeholders = ",".join("?" for _ in geoids)
    query = (
        "SELECT c.fips, cg.geometry_wkt "  # noqa: S608
        "FROM dim_county_geometry cg "
        "JOIN dim_county c ON cg.county_id = c.county_id "
        f"WHERE cg.geometry_wkt IS NOT NULL AND c.fips IN ({placeholders}) "
        "ORDER BY c.fips"
    )
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        rows = connection.execute(query, sorted(geoids)).fetchall()
    return {str(geoid): str(wkt) for geoid, wkt in rows}


__all__ = [
    "fetch_county_geometries_wkt_from_sqlite",
]
