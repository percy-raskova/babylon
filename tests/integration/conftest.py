"""Postgres integration test fixtures (Feature 037).

Provides per-test transaction isolation and pre-configured
PostgresRuntime instances for integration testing.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from psycopg import Connection
    from psycopg_pool import ConnectionPool


class PinnedPool:
    r"""Test isolation helper (#18): pin all ``pool.connection()`` calls to
    one transaction-scoped connection so GLOBAL table mutations (TRUNCATE,
    DELETE, INSERT) are invisible to concurrent sessions on the shared
    ``babylon_test`` database.

    The wrapped connection runs with ``autocommit=False``; the owning
    fixture issues ``ROLLBACK`` on teardown. Unlike psycopg3's
    ``ConnectionPool.connection()`` context manager -- which auto-commits
    on successful exit -- this wrapper NEVER commits, leaving transaction
    control entirely to the fixture.

    This fixes the hex_spatial_map contention bug (spec-088 S3) at its
    source: previously, ``fresh_tiger_table`` truncated
    ``immutable_reference_tiger_county`` with ``autocommit=True``, making
    the empty table visible to any concurrent lane (E2E regression, sim
    run) that depends on TIGER geometry for hex hydration. A concurrent
    hydrator would find zero counties, produce zero hex rows, and
    ``hex_spatial_map`` would silently lack entries -- yielding
    ``counties_alive=0`` terminal aggregates (the silent-zero bug that
    spec-102's STEP-0 guard catches after the fact).
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """Yield the pinned connection without committing.

        psycopg3's ``ConnectionPool.connection()`` commits on context
        exit; this wrapper intentionally does NOT, so the owning fixture's
        ``ROLLBACK`` undoes every mutation.
        """
        yield self._conn


@pytest.fixture
def pg_transaction(pg_pool: ConnectionPool) -> Generator[Any, None, None]:
    """Per-test transaction with automatic ROLLBACK for isolation.

    Each test runs inside a savepoint. On teardown the savepoint is
    rolled back so tests never pollute each other's data.
    """
    with pg_pool.connection() as conn:
        conn.autocommit = False
        conn.execute("BEGIN")
        try:
            yield conn
        finally:
            conn.execute("ROLLBACK")


@pytest.fixture
def pg_connection(pg_pool: ConnectionPool) -> Generator[Connection[Any], None, None]:
    """Per-test connection with autocommit for DDL operations.

    Unlike pg_transaction, this connection uses autocommit mode
    so DDL statements (CREATE TABLE, etc.) are immediately visible.
    Data is cleaned up via explicit DELETE rather than ROLLBACK.
    """
    with pg_pool.connection() as conn:
        conn.autocommit = True
        yield conn
