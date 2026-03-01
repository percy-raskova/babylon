"""Postgres integration test fixtures (Feature 037).

Provides per-test transaction isolation and pre-configured
PostgresRuntime instances for integration testing.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from psycopg import Connection
    from psycopg_pool import ConnectionPool


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
