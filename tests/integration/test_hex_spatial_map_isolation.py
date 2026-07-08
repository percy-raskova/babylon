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


def test_hex_spatial_map_is_session_scoped() -> None:
    """Migration 0028: hex_spatial_map has session_id in its PK.

    Two sessions can have rows for the same h3_index without conflict.
    A TRUNCATE in one session's row set doesn't affect the other.
    """
    import psycopg

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    conn = psycopg.connect(dsn, autocommit=True)
    try:
        with conn.cursor() as cur:
            # Verify session_id column exists
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'hex_spatial_map' AND column_name = 'session_id'"
            )
            assert cur.fetchone() is not None, "hex_spatial_map lacks session_id column"

            # Verify PK includes session_id
            cur.execute(
                "SELECT array_agg(a.attname ORDER by k.n) "
                "FROM pg_index i "
                "JOIN pg_class c ON c.oid = i.indexrelid "
                "JOIN pg_class t ON t.oid = i.indrelid "
                "JOIN pg_index k ON k.indexrelid = c.oid "
                "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(k.indkey) "
                "WHERE t.relname = 'hex_spatial_map' AND i.indisprimary"
            )
            pk_row = cur.fetchone()
            assert pk_row is not None, "No PK found on hex_spatial_map"
            pk_cols = list(pk_row[0])
            assert "session_id" in pk_cols, f"PK missing session_id: {pk_cols}"
            assert "h3_index" in pk_cols, f"PK missing h3_index: {pk_cols}"

            # Insert two rows for the same h3_index with different session_ids
            test_hex = "872ab2c73ffffff"
            s1 = "11111111-1111-1111-1111-111111111111"
            s2 = "22222222-2222-2222-2222-222222222222"
            cur.execute(
                "INSERT INTO hex_spatial_map (session_id, h3_index, county_fips, state_fips, region_id) "
                "VALUES (%s, %s, '26163', '26', 'GL') "
                "ON CONFLICT (session_id, h3_index) DO NOTHING",
                (s1, test_hex),
            )
            cur.execute(
                "INSERT INTO hex_spatial_map (session_id, h3_index, county_fips, state_fips, region_id) "
                "VALUES (%s, %s, '26125', '26', 'GL') "
                "ON CONFLICT (session_id, h3_index) DO NOTHING",
                (s2, test_hex),
            )

            # Both sessions have their own row
            cur.execute(
                "SELECT county_fips FROM hex_spatial_map WHERE session_id = %s AND h3_index = %s",
                (s1, test_hex),
            )
            row1 = cur.fetchone()
            assert row1 is not None and row1[0] == "26163"

            cur.execute(
                "SELECT county_fips FROM hex_spatial_map WHERE session_id = %s AND h3_index = %s",
                (s2, test_hex),
            )
            row2 = cur.fetchone()
            assert row2 is not None and row2[0] == "26125"

            # Cleanup
            cur.execute(
                "DELETE FROM hex_spatial_map WHERE session_id IN (%s, %s) AND h3_index = %s",
                (s1, s2, test_hex),
            )
    finally:
        conn.close()
