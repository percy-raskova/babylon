"""Collect the run's storage footprint for the manifest ``storage`` block.

Spec: 087-storage-foundations (FR-009/FR-010).

Two layers, mirroring :mod:`babylon.engine.headless_runner.run_summary`:

* :func:`build_storage_block` — pure builder; callers feed pre-shaped
  per-table stats, unit tests exercise the math.
* :func:`query_storage_footprint` — Postgres-backed collector run once at
  artifact-emission time. Best-effort by contract: a completed simulation
  MUST NOT fail because observability could not be collected (FR-010), so
  any collection error logs a warning and yields ``None`` (the manifest
  simply omits the block).

Semantics note: ``total_bytes`` is the whole relation (indexes included)
and may contain other sessions' rows in a shared database; ``session_rows``
is exact for this session. Rows/tick is therefore the deterministic
regression signal (``tools/storage_budget.py``); bytes are informational.
"""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

#: Per-tick append-only table families written by ``persist_tick_atomic``
#: (spec-062 migrations 0011-0025). ``to_regclass`` guards absence, so
#: older databases probe cleanly.
PER_TICK_TABLES: tuple[str, ...] = (
    "dynamic_hex_state",
    "boundary_flow_register",
    "conservation_audit_log",
    "dynamic_consciousness_state",
    "dynamic_demographics_state",
    "dynamic_employment_state",
    "dynamic_external_node_state",
    "dynamic_relationship_state",
    "contradiction_field",
    "tick_commit",
)


def build_storage_block(
    *,
    db_total_bytes: int,
    ticks_persisted: int,
    tables: list[dict[str, Any]],
) -> dict[str, Any]:
    """Shape the manifest ``storage`` block from pre-collected stats.

    Args:
        db_total_bytes: ``pg_database_size`` of the runtime database.
        ticks_persisted: Fully-persisted tick count (0 for errored runs;
            rows/tick then falls back to the raw row count).
        tables: One entry per probed table with ``table``, ``total_bytes``,
            and ``session_rows`` keys.

    Returns:
        Dict ready to embed under the manifest's top-level ``storage`` key,
        tables sorted by ``total_bytes`` descending.
    """
    denominator = max(ticks_persisted, 1)
    shaped = [
        {
            "table": str(entry["table"]),
            "total_bytes": int(entry["total_bytes"]),
            "session_rows": int(entry["session_rows"]),
            "session_rows_per_tick": round(int(entry["session_rows"]) / denominator, 2),
        }
        for entry in sorted(tables, key=lambda t: (-int(t["total_bytes"]), str(t["table"])))
    ]
    return {
        "db_total_bytes": int(db_total_bytes),
        "ticks_persisted": int(ticks_persisted),
        "tables": shaped,
    }


def query_storage_footprint(
    *,
    pool: Any,
    session_id: Any,
    ticks_persisted: int,
) -> dict[str, Any] | None:
    """Collect per-table sizes + session row counts from Postgres.

    Args:
        pool: psycopg connection pool (``connection()`` context manager).
        session_id: This run's session UUID (str or UUID).
        ticks_persisted: Fully-persisted tick count for rows/tick math.

    Returns:
        The :func:`build_storage_block` dict, or ``None`` when collection
        fails for any reason (FR-010 best-effort contract — the run's
        success must never depend on observability, so this is a declared
        broad-catch exemption; the failure is logged at WARNING).
    """
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_database_size(current_database())")
            db_total_bytes = int(cur.fetchone()[0])

            tables: list[dict[str, Any]] = []
            for table in PER_TICK_TABLES:
                cur.execute("SELECT to_regclass(%s)", (table,))
                if cur.fetchone()[0] is None:
                    continue
                # Table names come from the fixed PER_TICK_TABLES tuple
                # above, never from input — safe to interpolate.
                # pg_partition_tree covers partitioned parents (whose own
                # relation size is 0 — data lives in the partitions) and
                # degenerates to the single relation for plain tables.
                cur.execute(
                    "SELECT COALESCE(SUM(pg_total_relation_size(relid)), 0) "  # noqa: S608
                    f"FROM pg_partition_tree('{table}')"
                )
                total_bytes = int(cur.fetchone()[0])
                cur.execute(
                    f"SELECT count(*) FROM {table} WHERE session_id = %s",  # noqa: S608
                    (str(session_id),),
                )
                session_rows = int(cur.fetchone()[0])
                tables.append(
                    {
                        "table": table,
                        "total_bytes": total_bytes,
                        "session_rows": session_rows,
                    }
                )
    except Exception as exc:  # noqa: BLE001 — FR-010: observability must never fail the run
        _LOG.warning("Storage footprint collection failed (manifest omits block): %s", exc)
        return None

    return build_storage_block(
        db_total_bytes=db_total_bytes,
        ticks_persisted=ticks_persisted,
        tables=tables,
    )


__all__ = ["PER_TICK_TABLES", "build_storage_block", "query_storage_footprint"]
