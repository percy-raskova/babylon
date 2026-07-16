"""Per-session partition lifecycle for the per-tick dynamic tables.

Spec: 088-storage-partitioning-archival (S2a, FR-004/FR-005).

Migration ``0026_partition_dynamic_tables.sql`` converts the 8 per-tick
table families to ``PARTITION BY LIST (session_id)``. This module owns the
runtime side of that design:

* :func:`ensure_session_partitions` — called by ``initialize_session``
  before any dynamic-table write; creates ``<table>_p_<uuid.hex>``
  partitions. Idempotent; graceful no-op per table on a pre-0026 database
  (the DEFAULT partition also catches writers that skip session init).
* :func:`drop_session_partitions` — the instant-purge primitive used by
  the archival lifecycle (S2b): ``DROP TABLE`` on a partition removes a
  finished session's rows with zero dead tuples and no VACUUM debt.

Rationale: mass ``DELETE`` of a ~25M-row finished session would bloat the
heap and stall autovacuum; partition drop is O(1) catalog work.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from psycopg import sql

_LOG = logging.getLogger(__name__)

#: The per-tick table families partitioned by session. The first 8 were
#: converted by migration 0026 (spec-088 FR-001); tick_commit is born
#: partitioned in migration 0029 (spec-089 FR-001).
PARTITIONED_TABLES: tuple[str, ...] = (
    "dynamic_hex_state",
    "dynamic_external_node_state",
    "boundary_flow_register",
    "conservation_audit_log",
    "dynamic_consciousness_state",
    "dynamic_demographics_state",
    "dynamic_employment_state",
    "dynamic_relationship_state",
    "tick_commit",
)


def partition_name(table: str, session_id: UUID) -> str:
    """Per-session partition identifier: ``<table>_p_<uuid.hex>``.

    The longest family name (27 chars) + ``_p_`` + 32 hex chars = 62
    bytes, inside Postgres's 63-byte identifier limit.
    """
    return f"{table}_p_{session_id.hex}"


def _is_partitioned(conn: Any, table: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM pg_partitioned_table pt
        JOIN pg_class c ON c.oid = pt.partrelid
        WHERE c.relname = %s
        """,
        (table,),
    ).fetchone()
    return row is not None


def ensure_session_partitions(*, pool: Any, session_id: UUID) -> int:
    """Create this session's partition on every partitioned family.

    Args:
        pool: psycopg connection pool.
        session_id: Owning session UUID.

    Returns:
        Number of partitions newly created (0 on a repeat call, and 0 on
        a database where migration 0026 has not run — the flat tables
        still accept writes directly, so this is not an error).
    """
    created = 0
    with pool.connection() as conn:
        # One transaction PER family: each CREATE takes an exclusive lock on
        # its PARENT table, and a single transaction spanning all 9 families
        # accumulates parent locks and deadlocks against concurrent
        # multi-table readers/purges (observed under pytest-xdist
        # 2026-07-16). Holding at most one parent lock at a time makes this
        # loop deadlock-proof: it never holds one relation while waiting on
        # another. (Not autocommit: psycopg_pool does not reset a leaked
        # autocommit flag on return, so mutating it here would bleed into
        # unrelated checkouts.)
        for table in PARTITIONED_TABLES:
            with conn.transaction():
                if not _is_partitioned(conn, table):
                    _LOG.debug("Table %s not partitioned; skipping partition create", table)
                    continue
                name = partition_name(table, session_id)
                exists = conn.execute("SELECT to_regclass(%s)", (name,)).fetchone()
                if exists is not None and exists[0] is not None:
                    continue
                conn.execute(
                    sql.SQL(
                        "CREATE TABLE IF NOT EXISTS {} PARTITION OF {} FOR VALUES IN ({})"
                    ).format(
                        sql.Identifier(name),
                        sql.Identifier(table),
                        sql.Literal(str(session_id)),
                    )
                )
                created += 1
    if created:
        _LOG.info("Created %d session partitions for %s", created, session_id)
    return created


def drop_session_partitions(*, pool: Any, session_id: UUID) -> list[str]:
    """Drop this session's partitions (instant purge primitive, S2b).

    Args:
        pool: psycopg connection pool.
        session_id: Session whose partitions are removed.

    Returns:
        Names of the partitions actually dropped (missing ones skipped).
    """
    dropped: list[str] = []
    with pool.connection() as conn:
        # One transaction PER family: DROP TABLE on a partition
        # exclusive-locks its PARENT — see ensure_session_partitions. One
        # lock at a time means a purge may WAIT behind a long reader but can
        # no longer form a lock cycle with one.
        for table in PARTITIONED_TABLES:
            with conn.transaction():
                name = partition_name(table, session_id)
                exists = conn.execute("SELECT to_regclass(%s)", (name,)).fetchone()
                if exists is None or exists[0] is None:
                    continue
                conn.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier(name)))
                dropped.append(name)
    if dropped:
        _LOG.info("Dropped %d session partitions for %s", len(dropped), session_id)
    return dropped


__all__ = [
    "PARTITIONED_TABLES",
    "drop_session_partitions",
    "ensure_session_partitions",
    "partition_name",
]
