"""Archive persistence contracts: session isolation, tick immutability, atomic write.

WO-52b (T1.2 keel) test-port: these three guarantees were pinned by the
spec-061 ("Real Backend Wire-Up") test estate against ``PostgresRuntime``
directly — the web bridge was incidental plumbing around them, not the
behavior under test. Per the WO-52b ledger
(``specs/24-archive/test-port-ledger-wo52b.md``), the guard is ported
verbatim onto the same ``babylon.persistence.postgres_runtime.PostgresRuntime``
the Archive's headless runner uses (``engine/headless_runner/runner.py``
constructs the identical ``PostgresRuntime(pool=pool)``), with every
web-bridge import replaced by the runtime's own public API
(``PostgresRuntime.get_session`` in place of
``web.game.engine_bridge._fetch_session_rng_seed_from_pool``). The
original spec-061 files (``tests/integration/test_tick_immutability.py``,
``test_persist_tick_atomic.py``, ``test_multi_session_distinct.py``) are
untouched and keep gating the web path — this file is the Archive-side twin,
not a replacement.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.protocols import TickAlreadyResolved

pytestmark = pytest.mark.integration


def _skip_if_no_pool(pool: Any) -> None:
    """Belt-and-braces: ``pg_pool`` already auto-skips, but pin the precondition."""
    if pool is None:
        pytest.skip("PostgreSQL not available")


@pytest.fixture
def runtime(pg_pool) -> PostgresRuntime:
    return PostgresRuntime(pg_pool)


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


_SNAPSHOT_TABLES = (
    "territory_snapshot",
    "org_snapshot",
    "edge_snapshot",
    "community_snapshot",
    "hex_activity",
    "economic_summary",
    "tick_event",
)


def _row_counts(pg_pool, session_id, tick: int) -> dict[str, int]:
    """Count rows in every snapshot table for a given (game_id, tick)."""
    counts: dict[str, int] = {}
    with pg_pool.connection() as conn, conn.cursor() as cur:
        for table in _SNAPSHOT_TABLES:
            cur.execute(
                f"SELECT count(*) FROM {table} WHERE game_id = %s AND tick = %s",
                (session_id, tick),
            )
            row = cur.fetchone()
            counts[table] = int(row[0]) if row else 0
    return counts


def _atomicity_payloads(game_id: Any) -> dict[str, Any]:
    """A minimal but non-empty payload for every snapshot table."""
    return {
        "territories": [
            {
                "county_fips": "26163",
                "pop_total": 1_700_000,
                "heat": 0.1,
                "attributes": {"name": "Wayne County"},
            }
        ],
        "orgs": [
            {
                "org_id": "org-test-001",
                "org_type": "civil_society",
                "home_county": "26163",
                "ooda_phase": "observe",
                "attributes": {},
            }
        ],
        "edges": [
            {
                "source_id": "org-test-001",
                "target_id": "org-test-002",
                "edge_type": "SOLIDARITY",
                "edge_mode": "SOLIDARISTIC",
                "attributes": {},
            }
        ],
        "communities": [
            {
                "community_id": "comm-test-001",
                "community_type": "proletariat_county",
                "hyperedge_category": "contradiction_pair",
                "dominant_tendency": "revolutionary",
                "attributes": {},
            }
        ],
        "hex_activities": [
            {
                "h3_index": "8a1fb46622dffff",
                "heat_total": 0.5,
                "actions_taken": 1,
            }
        ],
        "economic_summary": {
            "total_population": 1_700_000,
            "total_orgs": 1,
        },
        "events": [
            {
                "event_type": "TEST_EVENT",
                "severity": "info",
                "summary": "archive contract: atomicity probe",
            }
        ],
    }


class TestTickImmutability:
    """A resolved (session, tick) can never be re-resolved.

    Ported from ``tests/integration/test_tick_immutability.py`` (spec-061
    T024 / FR-005): the immutability guard lives at the persistence layer
    (``tick_log`` PK uniqueness), so it applies uniformly to every caller —
    web bridge or Archive headless runner alike.
    """

    def test_second_resolve_raises_tick_already_resolved(self, runtime: PostgresRuntime) -> None:
        session_id = runtime.create_session(
            scenario="archive-t12-immutability",
            config_json={},
            game_defines_json={},
            rng_seed=0,
        )
        runtime.persist_full_tick(session_id, tick=0, **_minimal_payload())
        with pytest.raises(TickAlreadyResolved) as exc_info:
            runtime.persist_full_tick(session_id, tick=0, **_minimal_payload())
        assert exc_info.value.session_id == session_id
        assert exc_info.value.tick == 0

    def test_first_resolve_data_survives_second_attempt(
        self, runtime: PostgresRuntime, pg_pool
    ) -> None:
        """The rejected second call must not corrupt the first call's data."""
        session_id = runtime.create_session(
            scenario="archive-t12-immutability",
            config_json={},
            game_defines_json={},
            rng_seed=0,
        )
        runtime.persist_full_tick(session_id, tick=1, **_minimal_payload())
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

    def test_concurrent_resolves_one_wins_one_raises(self, runtime: PostgresRuntime) -> None:
        """Race-safe: two threads invoking ``persist_full_tick`` simultaneously
        for the same tick. One commits; the other gets ``TickAlreadyResolved``.
        No partial state."""
        session_id = runtime.create_session(
            scenario="archive-t12-immutability",
            config_json={},
            game_defines_json={},
            rng_seed=0,
        )
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


class TestPersistFullTickAtomic:
    """``persist_full_tick`` is all-or-nothing across its seven snapshot tables.

    Ported from ``tests/integration/test_persist_tick_atomic.py`` (spec-061
    T023 / SC-011).
    """

    def test_clean_persist_writes_all_seven_tables(self, runtime: PostgresRuntime, pg_pool) -> None:
        """Sanity check: a successful persist commits to every table."""
        session_id = runtime.create_session(
            scenario="archive-t12-atomicity",
            config_json={},
            game_defines_json={},
            rng_seed=0,
        )
        runtime.persist_full_tick(session_id, tick=0, **_atomicity_payloads(session_id))
        counts = _row_counts(pg_pool, session_id, 0)
        for table in _SNAPSHOT_TABLES:
            assert counts[table] >= 1, f"{table} had {counts[table]} rows after clean persist"

    def test_helper_failure_rolls_back_all_tables(
        self,
        runtime: PostgresRuntime,
        pg_pool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Force ``persist_economic_summary`` to raise mid-transaction.

        Every prior write inside the same ``persist_full_tick`` call must
        roll back — 0 rows in every snapshot table for the failed tick.
        """
        session_id = runtime.create_session(
            scenario="archive-t12-atomicity",
            config_json={},
            game_defines_json={},
            rng_seed=0,
        )

        def boom(self: Any, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("archive contract: deliberate failure mid-tick")

        monkeypatch.setattr(PostgresRuntime, "persist_economic_summary", boom)

        with pytest.raises(RuntimeError, match="deliberate failure mid-tick"):
            runtime.persist_full_tick(session_id, tick=7, **_atomicity_payloads(session_id))

        counts = _row_counts(pg_pool, session_id, 7)
        for table in _SNAPSHOT_TABLES:
            assert counts[table] == 0, (
                f"{table} had {counts[table]} rows after failed persist — "
                "transaction wrap is broken (FR-003 violation)"
            )

        with pg_pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM tick_log WHERE session_id = %s AND tick = %s",
                (session_id, 7),
            )
            row = cur.fetchone()
            assert row is not None
            assert int(row[0]) == 0, "tick_log row leaked across rollback"


class TestTwoSessionsIsolated:
    """Distinct sessions never share rows in any per-session table.

    Ported from ``tests/integration/test_multi_session_distinct.py``
    (spec-061 T131 / SC-005). The original's RNG-seed sub-test read the
    seed back through a web-bridge-private helper
    (``web.game.engine_bridge._fetch_session_rng_seed_from_pool``); here it
    reads back through ``PostgresRuntime.get_session`` — the runtime's own
    public API, and the one the Archive's headless runner actually calls.
    """

    def test_two_sessions_have_distinct_ids(self, runtime: PostgresRuntime) -> None:
        session_a = runtime.create_session(
            scenario="archive-t12-isolation-a",
            config_json={"variant": "a"},
            game_defines_json={},
            rng_seed=1,
        )
        session_b = runtime.create_session(
            scenario="archive-t12-isolation-b",
            config_json={"variant": "b"},
            game_defines_json={},
            rng_seed=2,
        )
        assert session_a != session_b, (
            "create_session must produce distinct UUIDs for distinct calls"
        )

    def test_distinct_rng_seeds_persisted(self, runtime: PostgresRuntime) -> None:
        """Each session's ``rng_seed`` is recoverable independently."""
        session_a = runtime.create_session(
            scenario="archive-t12-isolation-seedA",
            config_json={},
            game_defines_json={},
            rng_seed=1001,
        )
        session_b = runtime.create_session(
            scenario="archive-t12-isolation-seedB",
            config_json={},
            game_defines_json={},
            rng_seed=2002,
        )

        row_a = runtime.get_session(session_a)
        row_b = runtime.get_session(session_b)
        assert row_a is not None
        assert row_b is not None
        assert row_a["rng_seed"] == 1001
        assert row_b["rng_seed"] == 2002
        assert row_a["rng_seed"] != row_b["rng_seed"]

    def test_action_results_scoped_per_session(self, runtime: PostgresRuntime) -> None:
        """An action_result row written under session A is not visible under session B."""
        session_a = runtime.create_session(
            scenario="archive-t12-isolation-rowsA",
            config_json={},
            game_defines_json={},
            rng_seed=10,
        )
        session_b = runtime.create_session(
            scenario="archive-t12-isolation-rowsB",
            config_json={},
            game_defines_json={},
            rng_seed=20,
        )

        runtime.submit_turn(
            session_id=session_a,
            tick=0,
            org_id="org-1",
            verb="educate",
            action_type=None,
            target_id="terr-1",
            target_community=None,
            params_json={},
        )

        a_pending = runtime.get_pending_turns(session_id=session_a, tick=0)
        b_pending = runtime.get_pending_turns(session_id=session_b, tick=0)

        assert len(a_pending) >= 1, "session A should see its own submitted turn"
        assert len(b_pending) == 0, (
            "session B must not see session A's turn — per-session isolation"
        )

    def test_tick_immutability_is_per_session(self, runtime: PostgresRuntime) -> None:
        """``TickAlreadyResolved`` on session A does not block session B's tick 0."""
        session_a = runtime.create_session(
            scenario="archive-t12-isolation-immA",
            config_json={},
            game_defines_json={},
            rng_seed=100,
        )
        session_b = runtime.create_session(
            scenario="archive-t12-isolation-immB",
            config_json={},
            game_defines_json={},
            rng_seed=200,
        )

        # Smoke: two distinct sessions can both write tick 0 without colliding.
        runtime.persist_full_tick(session_a, tick=0, **_minimal_payload())
        runtime.persist_full_tick(session_b, tick=0, **_minimal_payload())
