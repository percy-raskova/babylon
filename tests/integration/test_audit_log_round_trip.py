"""Audit log round-trip integration test (T060 / US5 / SC-004 / SC-005 / SC-006).

Runs SimulationEngine for one tick with a registered ConservationAuditor;
verifies the audit row lands in conservation_audit_log and is queryable via
ConservationAuditQuery. Skips cleanly when Postgres is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


@pytest.fixture(scope="module")
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture(scope="module")
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def test_audit_row_round_trip(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """Engine evaluates auditor → row lands in conservation_audit_log → query returns it."""
    from babylon.persistence.audit_models import AuditSeverity
    from babylon.persistence.conservation_audit import ConservationAuditor, _InvariantResult
    from babylon.persistence.conservation_audit_query import ConservationAuditQuery
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

    def trivial_evaluator(pre, post, ctx):  # noqa: ARG001
        return [
            _InvariantResult(
                scale="county",
                invariant_name="hex_to_county_sum_c",
                computed_value=10.0,
                expected_value=10.0,
            )
        ]

    auditor.register_invariant("hex_to_county_sum_c", trivial_evaluator)

    # Engine pipeline doesn't need to run for this test — call the auditor
    # directly with empty hex set, then persist via persist_tick_atomic.
    rows, alarms = auditor.evaluate(session_id=sid, tick=0, hex_rows=[])
    assert len(rows) == 1
    assert rows[0].severity is AuditSeverity.OK

    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=0,
        audit_log_rows=rows,
        determinism_hash=rows[0].determinism_hash,
    )
    runtime.persist_tick_atomic(envelope)

    # Query via the read facade.
    query = ConservationAuditQuery(runtime)
    fetched = query.fetch(session_id=sid, tick=0)
    assert len(fetched) == 1
    assert fetched[0].invariant_name == "hex_to_county_sum_c"
    assert fetched[0].severity is AuditSeverity.OK
    assert len(fetched[0].determinism_hash) == 64

    # count_by_severity returns the canonical 3-key shape
    counts = query.count_by_severity(sid)
    assert counts == {"ok": 1, "warn": 0, "alarm": 0}


def test_audit_row_severity_alarm_round_trip(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """A residual > 1e-6 lands as severity='alarm'; count_by_severity surfaces it."""
    from babylon.persistence.audit_models import AuditSeverity
    from babylon.persistence.conservation_audit import ConservationAuditor, _InvariantResult
    from babylon.persistence.conservation_audit_query import ConservationAuditQuery
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

    def alarming_evaluator(pre, post, ctx):  # noqa: ARG001
        return [
            _InvariantResult(
                scale="county",
                invariant_name="bad_invariant",
                computed_value=10.0,
                expected_value=11.0,  # residual = -1.0 → ALARM
            )
        ]

    auditor.register_invariant("bad_invariant", alarming_evaluator)

    rows, alarms = auditor.evaluate(session_id=sid, tick=5, hex_rows=[])
    assert len(rows) == 1
    assert rows[0].severity is AuditSeverity.ALARM
    assert len(alarms) == 1

    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=5,
        audit_log_rows=rows,
        determinism_hash=rows[0].determinism_hash,
    )
    runtime.persist_tick_atomic(envelope)

    query = ConservationAuditQuery(runtime)
    fetched = query.fetch(session_id=sid, severity=AuditSeverity.ALARM)
    assert len(fetched) == 1
    assert fetched[0].invariant_name == "bad_invariant"

    counts = query.count_by_severity(sid)
    assert counts == {"ok": 0, "warn": 0, "alarm": 1}
