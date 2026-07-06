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

#: Default / hard-cap page size for the hex-frame endpoint. A national res-7
#: session is hundreds of thousands of hexes; the endpoint MUST page rather
#: than buffer the whole frame (spec-096 CRITICAL review finding; this is
#: spec-105's national verification surface).
DEFAULT_HEX_LIMIT = 5000
MAX_HEX_LIMIT = 50000

#: Cap on the session listing so a DB with thousands of runs cannot return an
#: unbounded list (consistent with the series/hex bounds).
DEFAULT_SESSION_LIMIT = 500

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
LIMIT %s
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
WHERE session_id = %s AND tick BETWEEN %s AND %s
ORDER BY tick
"""

HEX_FRAME_SQL = """
SELECT h3_index, county_fips, state_fips, region_id,
       c, v, s, k,
       biocapacity_stock, energy_stock, raw_material_stock,
       internet_access_pct, surveillance_coupling, written_at_tick
FROM v_hex_state_asof
WHERE session_id = %s AND tick = %s{county_clause}{after_clause}
ORDER BY h3_index
LIMIT %s
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
    after_h3: str | None,
    fetch_limit: int,
) -> tuple[str, tuple[Any, ...]]:
    """Build the bounded, paginated as-of hex-frame query.

    Reads ``v_hex_state_asof`` only, ordered by ``h3_index`` and capped at
    ``fetch_limit`` rows (the caller fetches one extra to detect truncation).
    An ``after_h3`` cursor pages forward by h3 index.

    Args:
        session_id: Session UUID (string).
        tick: The committed tick to reconstruct the frame at.
        county_fips: Optional 5-digit county filter.
        after_h3: Optional h3 cursor — return only ``h3_index > after_h3``.
        fetch_limit: Hard row cap for this page.

    Returns:
        ``(sql, params)`` reading ``v_hex_state_asof`` only.
    """
    params: list[Any] = [session_id, tick]
    county_clause = ""
    if county_fips:
        county_clause = " AND county_fips = %s"
        params.append(county_fips)
    after_clause = ""
    if after_h3:
        after_clause = " AND h3_index > %s"
        params.append(after_h3)
    params.append(fetch_limit)
    sql = HEX_FRAME_SQL.format(county_clause=county_clause, after_clause=after_clause)
    return sql, tuple(params)


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
    cursor.execute(SESSIONS_SQL, (DEFAULT_SESSION_LIMIT,))
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


def fetch_commits(
    cursor: Any,
    session_id: str,
    from_tick: int,
    to_tick: int,
) -> list[dict[str, Any]]:
    """Return the commit chain summary over an inclusive tick range, by tick."""
    cursor.execute(COMMITS_SQL, (session_id, from_tick, to_tick))
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
    limit: int = DEFAULT_HEX_LIMIT,
    after_h3: str | None = None,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Return one bounded page of the reconstructed hex frame (as-of view).

    Fetches ``limit + 1`` rows to detect truncation without a second query.

    Returns:
        ``(hexes, truncated, next_h3)`` — at most ``limit`` rows; ``truncated``
        is True when more rows exist; ``next_h3`` is the pagination cursor for
        the next page (the last h3 returned) or ``None`` when exhausted.
    """
    sql, params = build_hex_query(session_id, tick, county_fips, after_h3, limit + 1)
    cursor.execute(sql, params)
    rows = [
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
    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    next_h3 = rows[-1]["h3_index"] if truncated and rows else None
    return rows, truncated, next_h3


__all__ = [
    "SCOPE_VIEWS",
    "DEFAULT_MAX_TICK_SPAN",
    "DEFAULT_HEX_LIMIT",
    "MAX_HEX_LIMIT",
    "DEFAULT_SESSION_LIMIT",
    "build_series_query",
    "build_hex_query",
    "fetch_sessions",
    "fetch_tick_range",
    "fetch_series",
    "fetch_commits",
    "fetch_hex_frame",
]
