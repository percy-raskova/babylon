"""Integration tests for the tick_commit marker + hash chain (spec-089 S1a).

The marker makes "a committed tick" first-class: crash recovery no longer
depends on the (now false) invariant that every envelope writes at least
one hex row, and the Constitution-III.7 hash chain becomes queryable.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from babylon.engine.headless_runner.runner import _apply_migrations
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.partitioning import drop_session_partitions, ensure_session_partitions

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_pool(pg_pool: Any) -> Any:
    _apply_migrations(pg_pool)
    return pg_pool


@pytest.fixture()
def runtime(migrated_pool: Any) -> Any:
    from babylon.persistence.postgres_runtime import PostgresRuntime

    return PostgresRuntime(pool=migrated_pool)


def _hex_row(session: UUID, tick: int, v: float = 2.0) -> DynamicHexState:
    return DynamicHexState(
        session_id=session,
        tick=tick,
        h3_index="872a91055ffffff",
        county_fips="26163",
        state_fips="26",
        region_id="midwest",
        c=1.0,
        v=v,
        s=3.0,
        k=4.0,
        biocapacity_stock=5.0,
        energy_stock=6.0,
        raw_material_stock=7.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.25,
    )


def _envelope(session: UUID, tick: int, hex_rows: list[DynamicHexState]) -> Any:
    return PerTickTransactionEnvelope(
        session_id=session,
        tick=tick,
        hex_state_rows=hex_rows,
        determinism_hash=f"{tick:064d}"[:64],
    )


def _commit_rows(pool: Any, session: UUID) -> list[tuple[int, int, bool]]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT tick, hex_rows_written, is_checkpoint FROM tick_commit "
            "WHERE session_id = %s ORDER BY tick",
            (str(session),),
        ).fetchall()
    return [(int(t), int(n), bool(cp)) for t, n, cp in rows]


class TestTickCommitMarker:
    def test_marker_written_in_same_transaction(self, migrated_pool: Any, runtime: Any) -> None:
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            runtime.persist_tick_atomic(_envelope(session, 0, [_hex_row(session, 0)]))
            runtime.persist_tick_atomic(_envelope(session, 1, []))  # zero-hex tick
            assert _commit_rows(migrated_pool, session) == [(0, 1, True), (1, 0, False)]
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_last_committed_tick_survives_zero_hex_ticks(
        self, migrated_pool: Any, runtime: Any
    ) -> None:
        """FR-002: the old MAX(hex.tick) heuristic would report 0 here."""
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            runtime.persist_tick_atomic(_envelope(session, 0, [_hex_row(session, 0)]))
            runtime.persist_tick_atomic(_envelope(session, 1, []))
            runtime.persist_tick_atomic(_envelope(session, 2, []))
            assert runtime.get_last_committed_tick(session) == 2
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_redelivery_is_idempotent(self, migrated_pool: Any, runtime: Any) -> None:
        """FR-006 / spec-056 monotonicity: same envelope twice = no change."""
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            env = _envelope(session, 0, [_hex_row(session, 0)])
            runtime.persist_tick_atomic(env)
            runtime.persist_tick_atomic(env)
            assert _commit_rows(migrated_pool, session) == [(0, 1, True)]
            with migrated_pool.connection() as conn:
                n = conn.execute(
                    "SELECT count(*) FROM dynamic_hex_state WHERE session_id = %s",
                    (str(session),),
                ).fetchone()
            assert n is not None and int(n[0]) == 1
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)

    def test_hydrator_style_persist_skips_marker(self, migrated_pool: Any, runtime: Any) -> None:
        """FR-003: the tick-0 hydration envelope carries a placeholder hash;
        the bridge's re-delivery writes the real marker."""
        session = uuid4()
        ensure_session_partitions(pool=migrated_pool, session_id=session)
        try:
            runtime.persist_tick_atomic(
                _envelope(session, 0, [_hex_row(session, 0)]),
                write_commit_marker=False,
            )
            assert _commit_rows(migrated_pool, session) == []
            assert runtime.get_last_committed_tick(session) == 0  # hex fallback
        finally:
            drop_session_partitions(pool=migrated_pool, session_id=session)
