"""Behavioral contract for the digest-stamped DDL applier (2026-07-16).

:func:`babylon.persistence.postgres_schema.ensure_ddl_applied` exists because
the advisory lock alone could not stop re-applies from deadlocking against
live readers: migration ``0030_views_current.sql`` re-executes view DDL on
every pass, and its AccessExclusiveLock deadlocked against sibling xdist
workers' tests reading those views (12-error ``DeadlockDetected`` family,
proof run 2026-07-16). The contract pinned here:

1. First apply executes the set and stamps it; a repeat call executes
   NOTHING (observable: a side-effecting INSERT in the set does not re-run).
2. Any change to the set is a new digest and re-executes the whole set.
3. A failed apply leaves no stamp, so the next call retries execution
   instead of fast-pathing (the self-heal contract).

These are cross-implementation behavioral guarantees (what the applier DOES
against a real database), not implementation pins — a rewrite in another
language must satisfy exactly these three observations.
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
import pytest

from babylon.persistence.postgres_schema import (
    SCHEMA_STAMP_TABLE,
    ddl_digest,
    ensure_ddl_applied,
)

pytestmark = pytest.mark.integration


def test_ddl_digest_is_order_sensitive() -> None:
    """Apply order matters (tables before indexes), so permutations differ."""
    assert ddl_digest(["CREATE TABLE a ()", "CREATE TABLE b ()"]) != ddl_digest(
        ["CREATE TABLE b ()", "CREATE TABLE a ()"]
    )
    assert ddl_digest(["CREATE TABLE a ()"]) == ddl_digest(["CREATE TABLE a ()"])


@pytest.fixture()
def scratch_table(pg_pool: Any) -> Any:
    """A unique scratch table name, dropped (with its stamp rows) afterward."""
    name = f"stamp_scratch_{uuid.uuid4().hex[:12]}"
    yield name
    with pg_pool.connection() as conn:
        conn.autocommit = True
        conn.execute(f"DROP TABLE IF EXISTS {name}")
        row = conn.execute("SELECT to_regclass(%s)", (SCHEMA_STAMP_TABLE,)).fetchone()
        if row is not None and row[0] is not None:
            conn.execute(
                f"DELETE FROM {SCHEMA_STAMP_TABLE} WHERE applied_at >= now() - interval '1 hour' "
                "AND digest = ANY(%s)",
                (_digests_for(name),),
            )


def _chunks_v1(table: str) -> list[str]:
    return [
        f"CREATE TABLE IF NOT EXISTS {table} (marker TEXT NOT NULL)",
        f"INSERT INTO {table} (marker) VALUES ('v1')",
    ]


def _chunks_v2(table: str) -> list[str]:
    return [*_chunks_v1(table), f"INSERT INTO {table} (marker) VALUES ('v2')"]


def _chunks_broken(table: str) -> list[str]:
    return [
        f"CREATE TABLE IF NOT EXISTS {table} (marker TEXT NOT NULL)",
        f"CREATE TABLERR {table}_broken ()",
    ]


def _digests_for(table: str) -> list[str]:
    return [
        ddl_digest(_chunks_v1(table)),
        ddl_digest(_chunks_v2(table)),
        ddl_digest(_chunks_broken(table)),
    ]


def _row_count(pg_pool: Any, table: str) -> int:
    with pg_pool.connection() as conn:
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        assert row is not None
        return int(row[0])


def test_second_apply_of_same_set_executes_nothing(pg_pool: Any, scratch_table: str) -> None:
    """The fast path is observable: the set's INSERT does not re-run."""
    with pg_pool.connection() as conn:
        conn.autocommit = True
        assert ensure_ddl_applied(conn, _chunks_v1(scratch_table)) is True
        assert ensure_ddl_applied(conn, _chunks_v1(scratch_table)) is False
    assert _row_count(pg_pool, scratch_table) == 1


def test_changed_set_reapplies_in_full(pg_pool: Any, scratch_table: str) -> None:
    """A new digest re-executes the WHOLE new set, not a delta."""
    with pg_pool.connection() as conn:
        conn.autocommit = True
        assert ensure_ddl_applied(conn, _chunks_v1(scratch_table)) is True
        assert ensure_ddl_applied(conn, _chunks_v2(scratch_table)) is True
    # v1 pass inserted 1 row; v2 pass re-ran its v1 prefix (+1) and v2 (+1).
    assert _row_count(pg_pool, scratch_table) == 3


def test_failed_apply_leaves_no_stamp_and_retries(pg_pool: Any, scratch_table: str) -> None:
    """No stamp on failure: the next call must retry execution, not fast-path."""
    with pg_pool.connection() as conn:
        conn.autocommit = True
        with pytest.raises(psycopg.errors.SyntaxError):
            ensure_ddl_applied(conn, _chunks_broken(scratch_table))
        # A fast path would return False without raising; a real retry hits
        # the same broken statement again.
        with pytest.raises(psycopg.errors.SyntaxError):
            ensure_ddl_applied(conn, _chunks_broken(scratch_table))
