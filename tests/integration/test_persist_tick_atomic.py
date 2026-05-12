"""Spec 061 T023 / SC-011: ``persist_full_tick`` is all-or-nothing.

When any of the seven snapshot helpers raises mid-call, NO rows are
committed to ANY of the seven tables for that tick. This is the
atomic-write invariant required by FR-003 + research.md R2.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.persistence.postgres_runtime import PostgresRuntime

pytestmark = pytest.mark.integration


_SNAPSHOT_TABLES = (
    "territory_snapshot",
    "org_snapshot",
    "edge_snapshot",
    "community_snapshot",
    "hex_activity",
    "economic_summary",
    "tick_event",
)


@pytest.fixture
def runtime(pg_pool) -> PostgresRuntime:
    return PostgresRuntime(pg_pool)


@pytest.fixture
def session_id(runtime: PostgresRuntime):
    return runtime.create_session(
        scenario="spec-061-t023",
        config_json={},
        game_defines_json={},
        rng_seed=0,
    )


def _payloads(game_id) -> dict[str, Any]:
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
                # Note: tick_event.severity column is currently VARCHAR(12); the
                # full "informational" enum string overflows. Spec 061 US3 (T047)
                # will widen the column when severity becomes part of the
                # serialized event contract. For this atomicity test the
                # severity literal value is irrelevant — use a short marker.
                "event_type": "TEST_EVENT",
                "severity": "info",
                "summary": "spec 061 T023 atomicity probe",
            }
        ],
    }


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


class TestPersistFullTickAtomic:
    """SC-011: rollback verification for the spec 061 transactional wrap."""

    def test_clean_persist_writes_all_seven_tables(
        self, runtime: PostgresRuntime, pg_pool, session_id
    ) -> None:
        """Sanity check: a successful persist commits to every table."""
        runtime.persist_full_tick(session_id, tick=0, **_payloads(session_id))
        counts = _row_counts(pg_pool, session_id, 0)
        for table in _SNAPSHOT_TABLES:
            assert counts[table] >= 1, f"{table} had {counts[table]} rows after clean persist"

    def test_helper_failure_rolls_back_all_tables(
        self,
        runtime: PostgresRuntime,
        pg_pool,
        session_id,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Force ``persist_economic_summary`` to raise mid-transaction.

        Per FR-003: every prior write inside the same ``persist_full_tick``
        call must roll back. Asserts 0 rows in every snapshot table for
        the failed tick.
        """

        def boom(self, *args, **kwargs) -> None:
            raise RuntimeError("spec 061 T023 deliberate failure mid-tick")

        monkeypatch.setattr(
            PostgresRuntime,
            "persist_economic_summary",
            boom,
        )

        with pytest.raises(RuntimeError, match="spec 061 T023 deliberate failure"):
            runtime.persist_full_tick(session_id, tick=7, **_payloads(session_id))

        counts = _row_counts(pg_pool, session_id, 7)
        for table in _SNAPSHOT_TABLES:
            assert counts[table] == 0, (
                f"{table} had {counts[table]} rows after failed persist — "
                "transaction wrap is broken (FR-003 violation)"
            )

        # The tick_log row from the immutability gate must also have rolled back,
        # otherwise a retry would incorrectly raise TickAlreadyResolved.
        with pg_pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM tick_log WHERE session_id = %s AND tick = %s",
                (session_id, 7),
            )
            row = cur.fetchone()
            assert row is not None
            assert int(row[0]) == 0, "tick_log row leaked across rollback"
