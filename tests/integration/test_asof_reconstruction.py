"""Property test: as-of reconstruction ≡ dense frame (spec-089 SC-003).

Drives a seeded-random sparse write history through the REAL persistence
path (``select_hex_rows_for_emission`` → ``persist_tick_atomic``) while
maintaining the dense frame in memory, then asserts ``v_hex_state_asof``
reproduces the dense frame exactly at every committed tick — including
ticks where nothing was written.
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

import pytest

from babylon.engine.headless_runner.runner import _apply_migrations
from babylon.persistence.delta import select_hex_rows_for_emission
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.partitioning import drop_session_partitions, ensure_session_partitions

pytestmark = pytest.mark.integration

_H3S = [
    "872a91055ffffff",
    "872a9105bffffff",
    "872a91050ffffff",
    "872a91051ffffff",
]
_TICKS = 8  # small but crosses several no-write ticks


@pytest.fixture(scope="module")
def migrated_pool(pg_pool: Any) -> Any:
    _apply_migrations(pg_pool)
    return pg_pool


def _row(session: Any, tick: int, h3: str, v: float, k: float) -> DynamicHexState:
    return DynamicHexState(
        session_id=session,
        tick=tick,
        h3_index=h3,
        county_fips="26163",
        state_fips="26",
        region_id="midwest",
        c=1.0,
        v=v,
        s=3.0,
        k=k,
        biocapacity_stock=5.0,
        energy_stock=6.0,
        raw_material_stock=7.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.25,
    )


def test_asof_view_reproduces_dense_frame_at_every_tick(migrated_pool: Any) -> None:
    rng = random.Random(42)
    session = uuid4()
    ensure_session_partitions(pool=migrated_pool, session_id=session)

    from babylon.persistence.postgres_runtime import PostgresRuntime

    runtime = PostgresRuntime(pool=migrated_pool)

    # In-memory ground truth: (v, k) per hex per tick.
    dense: dict[int, dict[str, tuple[float, float]]] = {}
    values: dict[str, tuple[float, float]] = dict.fromkeys(_H3S, (10.0, 100.0))
    last_emitted: dict[str, tuple[float, ...]] = {}

    try:
        for tick in range(_TICKS):
            # Randomly mutate a random subset of hexes (possibly none).
            for h3 in _H3S:
                if tick > 0 and rng.random() < 0.35:
                    v, k = values[h3]
                    values[h3] = (round(v + rng.random(), 6), round(k + rng.random(), 6))
            dense[tick] = dict(values)

            frame = [_row(session, tick, h3, *values[h3]) for h3 in _H3S]
            emitted = select_hex_rows_for_emission(
                tick=tick, candidate_rows=frame, last_emitted=last_emitted
            )
            runtime.persist_tick_atomic(
                PerTickTransactionEnvelope(
                    session_id=session,
                    tick=tick,
                    hex_state_rows=emitted,
                    determinism_hash=f"{tick:064d}"[:64],
                )
            )

        # Reconstruction must equal the dense ground truth at EVERY tick.
        with migrated_pool.connection() as conn:
            rows = conn.execute(
                "SELECT tick, h3_index, v, k FROM v_hex_state_asof "
                "WHERE session_id = %s ORDER BY tick, h3_index",
                (str(session),),
            ).fetchall()

        reconstructed: dict[int, dict[str, tuple[float, float]]] = {}
        for tick, h3, v, k in rows:
            reconstructed.setdefault(int(tick), {})[str(h3)] = (float(v), float(k))

        assert set(reconstructed) == set(range(_TICKS)), "every committed tick reconstructs"
        for tick in range(_TICKS):
            assert reconstructed[tick] == dense[tick], f"tick {tick} diverged"

        # Sanity: the sparse table holds strictly fewer rows than dense would.
        with migrated_pool.connection() as conn:
            n = conn.execute(
                "SELECT count(*) FROM dynamic_hex_state WHERE session_id = %s",
                (str(session),),
            ).fetchone()
        assert n is not None and int(n[0]) < _TICKS * len(_H3S)
    finally:
        drop_session_partitions(pool=migrated_pool, session_id=session)
