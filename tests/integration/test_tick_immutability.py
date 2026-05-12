"""Spec 061 T024 / FR-005: resolved ticks are immutable.

A second ``persist_full_tick`` for the same ``(session_id, tick)`` must
raise :class:`TickAlreadyResolved` and leave the original snapshot
untouched. Includes a race-condition variant using two threads invoking
the same tick simultaneously.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.protocols import TickAlreadyResolved

pytestmark = pytest.mark.integration


@pytest.fixture
def runtime(pg_pool) -> PostgresRuntime:
    return PostgresRuntime(pg_pool)


@pytest.fixture
def session_id(runtime: PostgresRuntime):
    return runtime.create_session(
        scenario="spec-061-t024",
        config_json={},
        game_defines_json={},
        rng_seed=0,
    )


def _minimal_payload() -> dict[str, Any]:
    return {
        "territories": [{"county_fips": "26163", "pop_total": 100, "attributes": {}}],
        "orgs": [],
        "edges": [],
        "communities": [],
        "hex_activities": [],
        "economic_summary": {"total_population": 100},
        "events": [],
    }


class TestTickImmutability:
    """FR-005: resolved ticks cannot be re-resolved."""

    def test_second_resolve_raises_tick_already_resolved(
        self, runtime: PostgresRuntime, session_id
    ) -> None:
        runtime.persist_full_tick(session_id, tick=0, **_minimal_payload())
        with pytest.raises(TickAlreadyResolved) as exc_info:
            runtime.persist_full_tick(session_id, tick=0, **_minimal_payload())
        assert exc_info.value.session_id == session_id
        assert exc_info.value.tick == 0

    def test_first_resolve_data_survives_second_attempt(
        self, runtime: PostgresRuntime, pg_pool, session_id
    ) -> None:
        """The rejected second call must not corrupt the first call's data."""
        runtime.persist_full_tick(session_id, tick=1, **_minimal_payload())
        # Note: rejected because tick==1 is already in tick_log.
        with pytest.raises(TickAlreadyResolved):
            runtime.persist_full_tick(
                session_id,
                tick=1,
                territories=[{"county_fips": "26163", "pop_total": 999_999, "attributes": {}}],
                orgs=[],
                edges=[],
                communities=[],
                hex_activities=[],
                economic_summary={"total_population": 999_999},
                events=[],
            )
        with pg_pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pop_total FROM territory_snapshot "
                "WHERE game_id = %s AND tick = %s AND county_fips = %s",
                (session_id, 1, "26163"),
            )
            row = cur.fetchone()
            assert row is not None
            assert int(row[0]) == 100, "rejected re-resolve corrupted original"

    def test_concurrent_resolves_one_wins_one_raises(
        self, runtime: PostgresRuntime, session_id
    ) -> None:
        """Race-safe per research.md R2: two threads invoking persist_full_tick
        simultaneously for the same tick. One commits; the other gets
        TickAlreadyResolved. No partial state."""
        results: list[BaseException | None] = [None, None]
        barrier = threading.Barrier(2)

        def attempt(slot: int) -> None:
            try:
                barrier.wait(timeout=5)
                runtime.persist_full_tick(session_id, tick=2, **_minimal_payload())
                results[slot] = None
            except BaseException as exc:  # noqa: BLE001 — capture for assertion
                results[slot] = exc

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        successes = [r for r in results if r is None]
        rejections = [r for r in results if isinstance(r, TickAlreadyResolved)]
        assert len(successes) == 1, f"expected exactly 1 success, got {len(successes)}"
        assert len(rejections) == 1, (
            f"expected exactly 1 TickAlreadyResolved, got {[type(r).__name__ for r in results]}"
        )
