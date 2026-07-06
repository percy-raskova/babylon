"""Regression tests for hex_spatial_map contention isolation (#18).

Verifies that the transaction-rollback isolation pattern used by
``fresh_tiger_table`` (and other fixtures that mutate GLOBAL TIGER-derived
tables) keeps concurrent sessions on the shared ``babylon_test`` DB
unaffected.

Background (spec-088 S3 / spec-102 STEP-0 guard):
    ``hex_spatial_map`` is a GLOBAL non-session-scoped table on 5433
    (derived from TIGER via the hex hydrator). Some integration tests
    truncate/repopulate TIGER-derived tables without isolation. A
    concurrent run once zeroed a canonical baseline silently. The fix
    (``PinnedPool`` + ``autocommit=False``) keeps the TRUNCATE inside an
    uncommitted transaction so Postgres MVCC hides it from concurrent
    sessions.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
]


def test_tiger_delete_in_transaction_is_hidden_from_concurrent_sessions() -> None:
    """#18: DELETE in an uncommitted transaction must not be visible to
    a concurrent session (Postgres MVCC), and must not block concurrent
    SELECTs.

    Reproduces the isolation property that ``fresh_tiger_table`` relies on:
    the fixture DELETEs all rows from ``immutable_reference_tiger_county``
    inside a pinned transaction (``autocommit=False``) so concurrent lanes
    never see an empty table. Before the fix, the fixture used
    ``conn.autocommit = True`` which committed the mutation immediately
    -- the root cause of the hex_spatial_map silent-zero bug.

    Uses ``DELETE`` (not ``TRUNCATE``) because ``TRUNCATE`` acquires
    ``ACCESS EXCLUSIVE`` which blocks concurrent ``SELECT``s, while
    ``DELETE`` takes only ``ROW EXCLUSIVE`` (compatible with readers).
    """
    import psycopg

    dsn = os.environ["BABYLON_TEST_PG_DSN"]

    concurrent = psycopg.connect(dsn, autocommit=True)
    try:
        # Precondition: TIGER must have data (populated by `mise run data:tiger-counties`).
        with concurrent.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
            row = cur.fetchone()
            before = int(row[0]) if row else 0
        if before == 0:
            pytest.skip(
                "immutable_reference_tiger_county is empty; "
                "run `mise run data:tiger-counties` to populate"
            )

        # Open a transaction and DELETE all rows (the fix's pattern).
        tx = psycopg.connect(dsn, autocommit=False)
        try:
            tx.execute("DELETE FROM immutable_reference_tiger_county")

            # The transaction connection sees 0 rows (its own mutation).
            with tx.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
                row = cur.fetchone()
                tx_count = int(row[0]) if row else 0
            assert tx_count == 0, "DELETE should have zeroed the table within its transaction"

            # The concurrent session STILL sees the pre-DELETE data (MVCC),
            # and the SELECT does NOT block (ROW EXCLUSIVE is compatible
            # with ACCESS SHARE).
            with concurrent.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
                row = cur.fetchone()
                during = int(row[0]) if row else 0
            assert during == before, (
                f"Concurrent session saw {during} rows (expected {before}); "
                "DELETE leaked to concurrent sessions -- #18 regression"
            )
        finally:
            tx.execute("ROLLBACK")
            tx.close()

        # After ROLLBACK, everyone sees the data again.
        with concurrent.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM immutable_reference_tiger_county")
            row = cur.fetchone()
            after = int(row[0]) if row else 0
        assert after == before, f"ROLLBACK did not restore TIGER rows ({after} != {before})"
    finally:
        concurrent.close()


def test_pinned_pool_does_not_commit_on_context_exit() -> None:
    """#18: PinnedPool.connection() must NOT auto-commit (unlike
    psycopg3's ConnectionPool.connection()).

    If PinnedPool committed on context exit, the fixture's TRUNCATE would
    leak to concurrent sessions -- defeating the isolation. This test
    verifies that an INSERT via PinnedPool is NOT visible to a concurrent
    session after the context exits (but before ROLLBACK).
    """
    import psycopg

    from tests.integration.conftest import PinnedPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]

    # Use a throwaway temp table so we don't pollute global state.
    tx = psycopg.connect(dsn, autocommit=False)
    tx.execute("CREATE TEMP TABLE _pinned_pool_test (id int, label text) ON COMMIT DROP")
    pinned = PinnedPool(tx)
    try:
        # Production code pattern: `with pool.connection() as conn:`
        with pinned.connection() as conn:  # type: ignore[attr-defined]
            conn.cursor().execute("INSERT INTO _pinned_pool_test VALUES (1, 'inside')")

        # After context exit, PinnedPool must NOT have committed.
        # The TX connection should still see its own row (transaction
        # still open, not committed). Temp tables are session-local so
        # a concurrent session can't see them regardless; the real
        # check is that the row is still visible to tx after the
        # `with pinned.connection()` block exits.
        with tx.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM _pinned_pool_test")
            row = cur.fetchone()
            tx_rows = int(row[0]) if row else 0
        assert tx_rows == 1, (
            "PinnedPool lost the INSERT on context exit -- it must keep "
            "the transaction open without committing"
        )
    finally:
        tx.execute("ROLLBACK")
        tx.close()
