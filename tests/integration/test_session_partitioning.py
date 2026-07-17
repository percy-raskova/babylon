"""Integration tests for LIST(session_id) partitioning (spec-088 S2a).

Requires the isolated Postgres (``mise run db:up``); skips via the
``pg_pool`` fixture (``tests/conftest.py``) when unavailable. Applies the
full migration chain, then exercises partition conversion, per-session
partition lifecycle, and row routing.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from babylon.engine.headless_runner.runner import _apply_migrations
from babylon.persistence.partitioning import (
    PARTITIONED_TABLES,
    drop_session_partitions,
    ensure_session_partitions,
    partition_name,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_pool(pg_pool: Any) -> Any:
    """Apply the full migration chain once for this module."""
    _apply_migrations(pg_pool)
    return pg_pool


def _is_partitioned(pool: Any, table: str) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM pg_partitioned_table pt
            JOIN pg_class c ON c.oid = pt.partrelid
            WHERE c.relname = %s
            """,
            (table,),
        ).fetchone()
    return row is not None


def _tableoid_relname(pool: Any, table: str, session_id: str) -> str:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT tableoid::regclass::text FROM {table} WHERE session_id = %s LIMIT 1",  # noqa: S608
            (session_id,),
        ).fetchone()
    assert row is not None, f"no row found in {table} for session {session_id}"
    return str(row[0])


def _insert_hex_row(pool: Any, session_id: str, tick: int = 0) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO dynamic_hex_state (
                session_id, tick, h3_index, county_fips, state_fips, region_id,
                c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                internet_access_pct, surveillance_coupling
            ) VALUES (%s, %s, '872a91055ffffff', '26163', '26', 'midwest',
                      1, 1, 1, 1, 1, 1, 1, 0.5, 0.5)
            ON CONFLICT DO NOTHING
            """,
            (session_id, tick),
        )


class TestPartitionConversion:
    def test_all_families_partitioned_after_migrations(self, migrated_pool: Any) -> None:
        for table in PARTITIONED_TABLES:
            assert _is_partitioned(migrated_pool, table), f"{table} not partitioned"

    def test_default_partition_exists(self, migrated_pool: Any) -> None:
        with migrated_pool.connection() as conn:
            for table in PARTITIONED_TABLES:
                row = conn.execute("SELECT to_regclass(%s)", (f"{table}_default",)).fetchone()
                assert row is not None and row[0] is not None, f"{table}_default missing"

    def test_dependent_views_survive_the_pass(self, migrated_pool: Any) -> None:
        """0026 drops the 5 views on conversion; 0030 must restore them."""
        with migrated_pool.connection() as conn:
            for view in (
                "v_county_value_aggregate",
                "v_state_value_aggregate",
                "v_national_value_aggregate",
                "v_global_phi_balance",
                "view_runtime_trace_emission",
            ):
                row = conn.execute("SELECT to_regclass(%s)", (view,)).fetchone()
                assert row is not None and row[0] is not None, f"view {view} missing"

    def test_migrations_idempotent_on_second_pass(self, migrated_pool: Any) -> None:
        _apply_migrations(migrated_pool)  # steady-state pass must not raise
        for table in PARTITIONED_TABLES:
            assert _is_partitioned(migrated_pool, table)


class TestSessionPartitionLifecycle:
    def test_ensure_creates_then_idempotent(self, migrated_pool: Any) -> None:
        session = uuid4()
        created_first = ensure_session_partitions(pool=migrated_pool, session_id=session)
        created_second = ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            assert created_first == len(PARTITIONED_TABLES)
            assert created_second == 0
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_session_rows_route_to_session_partition(self, migrated_pool: Any) -> None:
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            _insert_hex_row(migrated_pool, str(session))
            assert _tableoid_relname(migrated_pool, "dynamic_hex_state", str(session)) == (
                partition_name("dynamic_hex_state", session)
            )
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_stray_session_rows_land_in_default_partition(self, migrated_pool: Any) -> None:
        stray = uuid4()  # no ensure_session_partitions call
        _insert_hex_row(migrated_pool, str(stray))
        try:
            assert (
                _tableoid_relname(migrated_pool, "dynamic_hex_state", str(stray))
                == "dynamic_hex_state_default"
            )
        finally:
            with migrated_pool.connection() as conn:
                conn.execute(
                    "DELETE FROM dynamic_hex_state_default WHERE session_id = %s",
                    (str(stray),),
                )

    def test_hex_map_exists_and_views_resolve_spatial_keys(self, migrated_pool: Any) -> None:
        """Spec-088 S3 (FR-006/FR-008): hex_spatial_map is the stored spatial mapping.

        A new-style hex row (NULL fips) resolves its county through
        hex_map; a legacy row (inline fips, no hex_map entry) still
        resolves via COALESCE fallback.
        """
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            with migrated_pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO hex_spatial_map
                        (session_id, h3_index, county_fips, state_fips, region_id)
                    VALUES (%s, '872a91055ffffff', '26163', '26', 'midwest')
                    ON CONFLICT (session_id, h3_index) DO NOTHING
                    """,
                    (str(session),),
                )
                # New-style row: spatial keys NULL, mapping via hex_spatial_map.
                conn.execute(
                    """
                    INSERT INTO dynamic_hex_state (
                        session_id, tick, h3_index, county_fips, state_fips, region_id,
                        c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                        internet_access_pct, surveillance_coupling
                    ) VALUES (%s, 0, '872a91055ffffff', NULL, NULL, NULL,
                              1, 2, 3, 4, 1, 1, 1, 0.5, 0.5)
                    """,
                    (str(session),),
                )
                # Legacy-style row: inline fips, h3 unknown to hex_spatial_map.
                conn.execute(
                    """
                    INSERT INTO dynamic_hex_state (
                        session_id, tick, h3_index, county_fips, state_fips, region_id,
                        c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                        internet_access_pct, surveillance_coupling
                    ) VALUES (%s, 0, '872a9105bffffff', '26125', '26', 'midwest',
                              10, 20, 30, 40, 1, 1, 1, 0.5, 0.5)
                    """,
                    (str(session),),
                )
                rows = conn.execute(
                    """
                    SELECT county_fips, v_sum FROM v_county_value_aggregate
                    WHERE session_id = %s AND tick = 0 ORDER BY county_fips
                    """,
                    (str(session),),
                ).fetchall()
            assert [(r[0], float(r[1])) for r in rows] == [
                ("26125", 20.0),
                ("26163", 2.0),
            ]
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_drop_removes_partitions_and_their_rows_only(self, migrated_pool: Any) -> None:
        keep, drop = uuid4(), uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=keep)
        ensure_session_partitions(pool=migrated_pool, session_id=drop)
        _insert_hex_row(migrated_pool, str(keep))
        _insert_hex_row(migrated_pool, str(drop))
        try:
            dropped = drop_session_partitions(pool=migrated_pool, session_id=drop)
            assert partition_name("dynamic_hex_state", drop) in dropped
            with migrated_pool.connection() as conn:
                gone = conn.execute(
                    "SELECT count(*) FROM dynamic_hex_state WHERE session_id = %s",
                    (str(drop),),
                ).fetchone()
                kept = conn.execute(
                    "SELECT count(*) FROM dynamic_hex_state WHERE session_id = %s",
                    (str(keep),),
                ).fetchone()
            assert gone is not None and int(gone[0]) == 0
            assert kept is not None and int(kept[0]) == 1
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=keep)
