"""Read-only SQL query builders + executors for the Observatory (spec-096).

Every query reads the simulation runner's declared interfaces ONLY:
- the value-aggregate views (``v_{national,state,county}_value_aggregate``),
- the as-of hex view (``v_hex_state_asof``),
- the commit-marker table (``tick_commit``),
- and, best-effort, the product ``game_session`` table for metadata.

The raw sparse ``dynamic_hex_state`` table is NEVER read directly (it is
delta-persisted; per-tick reads must go through ``v_hex_state_asof``). Values
are always passed as bound parameters; only whitelisted view/column names are
formatted into SQL (see :data:`SCOPE_VIEWS`). This satisfies Constitution II.11
(cross-subsystem reads via declared interfaces).

Executor functions take an open DB cursor (``connections["sim"].cursor()``) and
return plain dicts ready for the response envelope.
"""

from __future__ import annotations

from typing import Any

#: Whitelisted scope -> (view, id-column, default id). The view/column names
#: are the ONLY identifiers ever interpolated into SQL; everything else is a
#: bound parameter.
SCOPE_VIEWS: dict[str, tuple[str, str, str | None]] = {
    "national": ("v_national_value_aggregate", "national_id", "USA"),
    "state": ("v_state_value_aggregate", "state_fips", None),
    "county": ("v_county_value_aggregate", "county_fips", None),
}

#: Safety cap so a series request cannot return an unbounded window. The
#: aggregate views only yield committed ticks, so this is a guard, not a norm.
DEFAULT_MAX_TICK_SPAN = 5000

# --------------------------------------------------------------------------- #
# SQL (parameterized) — session/tick discovery, series, commits, hex frame
# --------------------------------------------------------------------------- #

SESSIONS_SQL = """
SELECT session_id,
       MIN(tick) AS min_tick,
       MAX(tick) AS max_tick,
       COUNT(*) AS tick_count,
       COUNT(*) FILTER (WHERE is_checkpoint) AS checkpoint_count,
       (ARRAY_AGG(determinism_hash ORDER BY tick DESC))[1] AS latest_hash
FROM tick_commit
GROUP BY session_id
ORDER BY max_tick DESC, session_id
"""

TICK_RANGE_SQL = """
SELECT MIN(tick) AS min_tick,
       MAX(tick) AS max_tick,
       COUNT(*) AS tick_count,
       COALESCE(
           ARRAY_AGG(tick ORDER BY tick) FILTER (WHERE is_checkpoint),
           ARRAY[]::int[]
       ) AS checkpoint_ticks
FROM tick_commit
WHERE session_id = %s
"""

COMMITS_SQL = """
SELECT tick, determinism_hash, hex_rows_written, is_checkpoint, created_at_utc
FROM tick_commit
WHERE session_id = %s
ORDER BY tick
"""

HEX_FRAME_SQL = """
SELECT h3_index, county_fips, state_fips, region_id,
       c, v, s, k,
       biocapacity_stock, energy_stock, raw_material_stock,
       internet_access_pct, surveillance_coupling, written_at_tick
FROM v_hex_state_asof
WHERE session_id = %s AND tick = %s{county_clause}
ORDER BY h3_index
"""

_SESSION_META_SQL = """
SELECT id, scenario, status, created_at
FROM game_session
WHERE id = ANY(%s)
"""

_GAME_SESSION_EXISTS_SQL = "SELECT to_regclass('public.game_session')"


def build_series_query(
    scope: str,
    session_id: str,
    scope_id: str,
    from_tick: int,
    to_tick: int,
) -> tuple[str, tuple[Any, ...]]:
    """Build the value-aggregate series query for a scope.

    Args:
        scope: One of ``national`` / ``state`` / ``county``.
        session_id: Session UUID (string).
        scope_id: ``USA`` for national, a state/county FIPS otherwise.
        from_tick: Inclusive lower tick bound.
        to_tick: Inclusive upper tick bound.

    Returns:
        ``(sql, params)`` with the view/column chosen from the whitelist and
        every value bound as a parameter.

    Raises:
        ValueError: If ``scope`` is not a known scope.
    """
    if scope not in SCOPE_VIEWS:
        raise ValueError(f"unknown scope: {scope!r}")
    view, id_column, _default = SCOPE_VIEWS[scope]
    sql = (
        f"SELECT tick, c_sum, v_sum, s_sum, k_sum, biocapacity_sum, hex_count "  # noqa: S608 — view/column from whitelist, values bound
        f"FROM {view} "
        f"WHERE session_id = %s AND {id_column} = %s AND tick BETWEEN %s AND %s "
        f"ORDER BY tick"
    )
    return sql, (session_id, scope_id, from_tick, to_tick)


def build_hex_query(
    session_id: str,
    tick: int,
    county_fips: str | None,
) -> tuple[str, tuple[Any, ...]]:
    """Build the as-of hex-frame query, optionally filtered by county.

    Args:
        session_id: Session UUID (string).
        tick: The committed tick to reconstruct the frame at.
        county_fips: Optional 5-digit county filter.

    Returns:
        ``(sql, params)`` reading ``v_hex_state_asof`` only.
    """
    if county_fips:
        sql = HEX_FRAME_SQL.format(county_clause=" AND county_fips = %s")
        return sql, (session_id, tick, county_fips)
    sql = HEX_FRAME_SQL.format(county_clause="")
    return sql, (session_id, tick)


# --------------------------------------------------------------------------- #
# Executors
# --------------------------------------------------------------------------- #


def _num(value: Any) -> float:
    """Coalesce a possibly-``NULL`` numeric to a float (views may emit NULL)."""
    return float(value) if value is not None else 0.0


def fetch_sessions(cursor: Any) -> list[dict[str, Any]]:
    """Return every session with at least one committed tick.

    Session metadata (scenario/status/created_at) is enriched from
    ``game_session`` when that table exists in the sim DB; its absence (e.g. a
    migrations-only test DB) is fine — FR-007 makes metadata optional.
    """
    cursor.execute(SESSIONS_SQL)
    rows = cursor.fetchall()
    sessions = [
        {
            "session_id": str(r[0]),
            "min_tick": r[1],
            "max_tick": r[2],
            "tick_count": r[3],
            "checkpoint_count": r[4],
            "latest_hash": r[5],
            "scenario": None,
            "status": None,
            "created_at": None,
        }
        for r in rows
    ]
    _enrich_with_metadata(cursor, sessions)
    return sessions


def _enrich_with_metadata(cursor: Any, sessions: list[dict[str, Any]]) -> None:
    """Best-effort scenario/status/created_at enrichment from ``game_session``."""
    if not sessions:
        return
    cursor.execute(_GAME_SESSION_EXISTS_SQL)
    if cursor.fetchone()[0] is None:
        return  # no game_session table in this sim DB — metadata stays null.
    # game_session.id is CHAR(32) hex (no dashes); session_id is a UUID.
    keys = [s["session_id"].replace("-", "") for s in sessions]
    cursor.execute(_SESSION_META_SQL, (keys,))
    meta = {str(r[0]).strip(): (r[1], r[2], r[3]) for r in cursor.fetchall()}
    for s in sessions:
        hit = meta.get(s["session_id"].replace("-", ""))
        if hit is not None:
            s["scenario"], s["status"], created = hit
            s["created_at"] = created.isoformat() if created is not None else None


def fetch_tick_range(cursor: Any, session_id: str) -> dict[str, Any] | None:
    """Return committed tick range + checkpoint ticks, or ``None`` if empty."""
    cursor.execute(TICK_RANGE_SQL, (session_id,))
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return None
    return {
        "session_id": session_id,
        "min_tick": row[0],
        "max_tick": row[1],
        "tick_count": row[2],
        "checkpoint_ticks": list(row[3]) if row[3] is not None else [],
    }


def fetch_series(
    cursor: Any,
    scope: str,
    session_id: str,
    scope_id: str,
    from_tick: int,
    to_tick: int,
) -> list[dict[str, Any]]:
    """Return value-aggregate points for a scope over an inclusive tick range."""
    sql, params = build_series_query(scope, session_id, scope_id, from_tick, to_tick)
    cursor.execute(sql, params)
    return [
        {
            "tick": r[0],
            "c_sum": _num(r[1]),
            "v_sum": _num(r[2]),
            "s_sum": _num(r[3]),
            "k_sum": _num(r[4]),
            "biocapacity_sum": _num(r[5]),
            "hex_count": r[6] or 0,
        }
        for r in cursor.fetchall()
    ]


def fetch_commits(cursor: Any, session_id: str) -> list[dict[str, Any]]:
    """Return the per-tick commit chain summary, ordered by tick."""
    cursor.execute(COMMITS_SQL, (session_id,))
    return [
        {
            "tick": r[0],
            "determinism_hash": r[1],
            "hex_rows_written": r[2],
            "is_checkpoint": bool(r[3]),
            "created_at_utc": r[4].isoformat() if r[4] is not None else None,
        }
        for r in cursor.fetchall()
    ]


def fetch_hex_frame(
    cursor: Any,
    session_id: str,
    tick: int,
    county_fips: str | None = None,
) -> list[dict[str, Any]]:
    """Return the reconstructed hex frame at a committed tick (as-of view)."""
    sql, params = build_hex_query(session_id, tick, county_fips)
    cursor.execute(sql, params)
    return [
        {
            "h3_index": r[0],
            "county_fips": r[1],
            "state_fips": r[2],
            "region_id": r[3],
            "c": _num(r[4]),
            "v": _num(r[5]),
            "s": _num(r[6]),
            "k": _num(r[7]),
            "biocapacity_stock": _num(r[8]),
            "energy_stock": _num(r[9]),
            "raw_material_stock": _num(r[10]),
            "internet_access_pct": _num(r[11]),
            "surveillance_coupling": _num(r[12]),
            "written_at_tick": r[13],
        }
        for r in cursor.fetchall()
    ]


__all__ = [
    "SCOPE_VIEWS",
    "DEFAULT_MAX_TICK_SPAN",
    "build_series_query",
    "build_hex_query",
    "fetch_sessions",
    "fetch_tick_range",
    "fetch_series",
    "fetch_commits",
    "fetch_hex_frame",
]
