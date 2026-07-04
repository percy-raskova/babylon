"""Reader-based queries for the Observatory deep panes (spec-099).

All functions take a ``reader`` (``LiveReader`` or ``ArchiveReader`` from
:mod:`observatory.sources`) exposing ``execute(sql, params) -> list[dict]`` +
``table_available(table)``. Raw-table SQL is authored with ``?`` placeholders
so the identical statement runs against Postgres (live) and DuckDB (archive).

``verify_chain`` is pure (no I/O): it validates a commit chain's structural
integrity — it never re-runs the engine (Constitution III.7 is *read* here).
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------- #
# Pure verification logic
# --------------------------------------------------------------------------- #

#: Mirrors :data:`babylon.persistence.delta.CHECKPOINT_EVERY_TICKS`. Duplicated
#: (rather than imported) because ``web/`` may only import engine/persistence
#: code from ``game/engine_bridge.py`` (see ``tests/unit/web/test_import_boundary.py``);
#: the observatory app is a read-only bridge and must not cross that boundary.
CHECKPOINT_EVERY_TICKS = 52


def verify_chain(commit_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Structurally verify a commit chain (contiguity, cadence, hash, dups).

    Args:
        commit_rows: Rows with ``tick``, ``determinism_hash``,
            ``hex_rows_written``, ``is_checkpoint`` (ordered or not).

    Returns:
        A verdict dict: ``valid`` (True iff no anomalies), committed range,
        ``checkpoint_ticks``, ``expected_checkpoint_cadence``, and an
        ``anomalies`` list of ``{kind, tick, detail}`` where ``kind`` is one of
        ``gap`` / ``duplicate`` / ``bad_checkpoint`` / ``bad_hash``.
    """
    anomalies: list[dict[str, Any]] = []
    if not commit_rows:
        return {
            "valid": True,
            "min_tick": None,
            "max_tick": None,
            "tick_count": 0,
            "checkpoint_ticks": [],
            "expected_checkpoint_cadence": CHECKPOINT_EVERY_TICKS,
            "anomalies": [],
        }

    ticks = [int(r["tick"]) for r in commit_rows]
    seen: set[int] = set()
    for tick in ticks:
        if tick in seen:
            anomalies.append(
                {"kind": "duplicate", "tick": tick, "detail": "tick appears more than once"}
            )
        seen.add(tick)

    lo, hi = min(ticks), max(ticks)
    for tick in range(lo, hi + 1):
        if tick not in seen:
            anomalies.append({"kind": "gap", "tick": tick, "detail": "committed tick missing"})

    checkpoint_ticks: list[int] = []
    for row in commit_rows:
        tick = int(row["tick"])
        is_ckpt = bool(row["is_checkpoint"])
        if is_ckpt:
            checkpoint_ticks.append(tick)
        expected_ckpt = tick % CHECKPOINT_EVERY_TICKS == 0
        if is_ckpt != expected_ckpt:
            anomalies.append(
                {
                    "kind": "bad_checkpoint",
                    "tick": tick,
                    "detail": f"is_checkpoint={is_ckpt} but expected {expected_ckpt}",
                }
            )
        digest = row.get("determinism_hash") or ""
        if len(str(digest)) != 64:
            anomalies.append(
                {
                    "kind": "bad_hash",
                    "tick": tick,
                    "detail": f"hash length {len(str(digest))} != 64",
                }
            )

    return {
        "valid": not anomalies,
        "min_tick": lo,
        "max_tick": hi,
        "tick_count": len(seen),
        "checkpoint_ticks": sorted(checkpoint_ticks),
        "expected_checkpoint_cadence": CHECKPOINT_EVERY_TICKS,
        "anomalies": anomalies,
    }


# --------------------------------------------------------------------------- #
# Raw-table SQL (?-placeholders; identical on Postgres + DuckDB)
# --------------------------------------------------------------------------- #

COMMIT_CHAIN_SQL = """
SELECT tick, determinism_hash, hex_rows_written, is_checkpoint
FROM tick_commit
WHERE CAST(session_id AS VARCHAR) = ? AND tick BETWEEN ? AND ?
ORDER BY tick
"""

TICK_RANGE_SQL = """
SELECT MIN(tick) AS min_tick, MAX(tick) AS max_tick, COUNT(*) AS tick_count
FROM tick_commit
WHERE CAST(session_id AS VARCHAR) = ?
"""

BOUNDARY_ROWS_SQL = """
SELECT tick, source_node_id, source_kind, dest_node_id, dest_kind,
       flow_type, magnitude
FROM boundary_flow_register
WHERE CAST(session_id AS VARCHAR) = ? AND tick BETWEEN ? AND ?
ORDER BY tick, flow_type, source_node_id
LIMIT ?
"""

BOUNDARY_SUMMARY_SQL = """
SELECT flow_type, COUNT(*) AS row_count, SUM(magnitude) AS total_magnitude
FROM boundary_flow_register
WHERE CAST(session_id AS VARCHAR) = ? AND tick BETWEEN ? AND ?
GROUP BY flow_type
ORDER BY flow_type
"""

CONSERVATION_SQL = """
SELECT tick, scale, invariant_name, computed_value, expected_value,
       residual, severity
FROM conservation_audit_log
WHERE CAST(session_id AS VARCHAR) = ? AND tick BETWEEN ? AND ?{severity_clause}
ORDER BY tick, scale, invariant_name
LIMIT ?
"""

# National value-aggregate reconstruction over the RAW hex + commit tables
# (mirrors 0030 v_national_value_aggregate). References only raw tables, so it
# runs on both Postgres and DuckDB — used for the archive source and diffs.
NATIONAL_RECON_SQL = """
WITH change_ticks AS (
    SELECT DISTINCT session_id, tick FROM dynamic_hex_state
),
intervals AS (
    SELECT h.session_id, h.h3_index, h.tick, h.c, h.v, h.s, h.k, h.biocapacity_stock,
           LEAD(h.tick) OVER (PARTITION BY h.session_id, h.h3_index ORDER BY h.tick) AS next_tick
    FROM dynamic_hex_state h
),
national_events AS (
    SELECT ct.session_id, ct.tick,
           SUM(hi.c) AS c_sum, SUM(hi.v) AS v_sum, SUM(hi.s) AS s_sum, SUM(hi.k) AS k_sum,
           SUM(hi.biocapacity_stock) AS biocapacity_sum, COUNT(*) AS hex_count
    FROM change_ticks ct
    JOIN intervals hi ON hi.session_id = ct.session_id AND hi.tick <= ct.tick
        AND (hi.next_tick IS NULL OR ct.tick < hi.next_tick)
    GROUP BY ct.session_id, ct.tick
),
national_intervals AS (
    SELECT ne.*, LEAD(ne.tick) OVER (PARTITION BY ne.session_id ORDER BY ne.tick) AS next_tick
    FROM national_events ne
),
spine AS (
    SELECT session_id, tick FROM tick_commit
    UNION SELECT DISTINCT session_id, tick FROM dynamic_hex_state
)
SELECT sp.tick, ni.c_sum, ni.v_sum, ni.s_sum, ni.k_sum, ni.biocapacity_sum, ni.hex_count
FROM spine sp
JOIN national_intervals ni ON ni.session_id = sp.session_id AND ni.tick <= sp.tick
    AND (ni.next_tick IS NULL OR sp.tick < ni.next_tick)
WHERE CAST(sp.session_id AS VARCHAR) = ? AND sp.tick BETWEEN ? AND ?
ORDER BY sp.tick
"""

_MAX_BOUNDARY_ROWS = 5000
_MAX_AUDIT_ROWS = 5000


def _num(value: Any) -> float:
    return float(value) if value is not None else 0.0


def read_tick_range(reader: Any, session_id: str) -> tuple[int, int] | None:
    """Committed tick range for a session, or ``None`` if empty/absent."""
    if not reader.table_available("tick_commit"):
        return None
    rows = reader.execute(TICK_RANGE_SQL, (session_id,))
    if not rows or rows[0]["min_tick"] is None:
        return None
    return int(rows[0]["min_tick"]), int(rows[0]["max_tick"])


def read_commit_chain(
    reader: Any, session_id: str, from_tick: int, to_tick: int
) -> list[dict[str, Any]]:
    """Commit chain rows over a tick range (empty if the table is absent)."""
    if not reader.table_available("tick_commit"):
        return []
    rows = reader.execute(COMMIT_CHAIN_SQL, (session_id, from_tick, to_tick))
    return [
        {
            "tick": int(r["tick"]),
            "determinism_hash": r["determinism_hash"],
            "hex_rows_written": int(r["hex_rows_written"]),
            "is_checkpoint": bool(r["is_checkpoint"]),
        }
        for r in rows
    ]


def read_national_series(
    reader: Any, session_id: str, from_tick: int, to_tick: int
) -> list[dict[str, Any]]:
    """National value-aggregate series reconstructed over raw hex + commits."""
    if not reader.table_available("dynamic_hex_state"):
        return []
    rows = reader.execute(NATIONAL_RECON_SQL, (session_id, from_tick, to_tick))
    return [
        {
            "tick": int(r["tick"]),
            "c_sum": _num(r["c_sum"]),
            "v_sum": _num(r["v_sum"]),
            "s_sum": _num(r["s_sum"]),
            "k_sum": _num(r["k_sum"]),
            "biocapacity_sum": _num(r["biocapacity_sum"]),
            "hex_count": int(r["hex_count"]) if r["hex_count"] is not None else 0,
        }
        for r in rows
    ]


def read_boundary(reader: Any, session_id: str, from_tick: int, to_tick: int) -> dict[str, Any]:
    """Boundary flows grouped by flow type + capped raw rows (empty-state-safe)."""
    if not reader.table_available("boundary_flow_register"):
        return {"by_flow_type": [], "rows": []}
    summary = reader.execute(BOUNDARY_SUMMARY_SQL, (session_id, from_tick, to_tick))
    rows = reader.execute(BOUNDARY_ROWS_SQL, (session_id, from_tick, to_tick, _MAX_BOUNDARY_ROWS))
    return {
        "by_flow_type": [
            {
                "flow_type": r["flow_type"],
                "row_count": int(r["row_count"]),
                "total_magnitude": _num(r["total_magnitude"]),
            }
            for r in summary
        ],
        "rows": [
            {
                "tick": int(r["tick"]),
                "source_node_id": r["source_node_id"],
                "source_kind": r["source_kind"],
                "dest_node_id": r["dest_node_id"],
                "dest_kind": r["dest_kind"],
                "flow_type": r["flow_type"],
                "magnitude": _num(r["magnitude"]),
            }
            for r in rows
        ],
    }


def read_conservation(
    reader: Any,
    session_id: str,
    from_tick: int,
    to_tick: int,
    non_ok_only: bool,
) -> list[dict[str, Any]]:
    """Conservation-audit rows over a tick range (optionally non-OK only)."""
    if not reader.table_available("conservation_audit_log"):
        return []
    clause = " AND severity <> 'ok'" if non_ok_only else ""
    sql = CONSERVATION_SQL.format(severity_clause=clause)
    rows = reader.execute(sql, (session_id, from_tick, to_tick, _MAX_AUDIT_ROWS))
    return [
        {
            "tick": int(r["tick"]),
            "scale": r["scale"],
            "invariant_name": r["invariant_name"],
            "computed_value": _num(r["computed_value"]),
            "expected_value": _num(r["expected_value"]),
            "residual": _num(r["residual"]),
            "severity": r["severity"],
        }
        for r in rows
    ]


__all__ = [
    "CHECKPOINT_EVERY_TICKS",
    "verify_chain",
    "read_tick_range",
    "read_commit_chain",
    "read_national_series",
    "read_boundary",
    "read_conservation",
]
