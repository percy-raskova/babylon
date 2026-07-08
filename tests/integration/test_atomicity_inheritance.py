"""Integration test: spec-063 boundary rows inherit FR-008a atomicity (T052).

Spec-063's cross-boundary rows commit through the SAME
:meth:`PostgresRuntime.persist_tick_atomic` envelope as spec-062's five flow
types (FR-022), so they inherit its all-or-nothing guarantee. Three proofs:

- **Part 1** (in-tick abort): a classifier that raises mid-step leaves a
  PARTIAL buffer in the in-memory :class:`BoundaryFlowRegister`, but because
  the buffer is never flushed into an envelope, Postgres holds ZERO rows for
  that tick — the memory register is not a persistence side channel.
- **Part 2** (transaction rollback): an envelope whose boundary rows are
  valid but whose audit row violates the ``conservation_audit_log`` scale
  CHECK (migration 0031) rolls back the WHOLE tick — the boundary rows,
  inserted first (``_spec_062.py`` ordering), vanish with the failed audit
  insert.
- **Part 3** (retry after failure): a subsequent clean envelope for the next
  tick commits normally, proving the failure left no poison state.

Requires only the live Postgres test pool (BABYLON_TEST_PG_DSN) — no LODES /
TIGER / SQLite data. Rows are scoped by ``session_id`` (shared babylon_test).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cross_scale,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
]

_YEAR = 2010
_ORIGIN_HEX = "872ab2c58ffffff"


@pytest.fixture(scope="module")
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def runtime(pg_pool):  # type: ignore[no-untyped-def]
    """Construct the runtime, skipping if babylon_test is not yet migrated.

    The wave harness provisions + migrates the shared babylon_test DB, so this
    suite verifies the handful of tables it touches rather than re-applying all
    23 migrations (an idempotent ~14s no-op on an already-migrated DB).
    """
    from babylon.persistence import PostgresRuntime

    required = ("boundary_flow_register", "conservation_audit_log")
    with pg_pool.connection() as conn:
        for table in required:
            got = conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
            if got is None or got[0] is None:
                pytest.skip(f"required table {table} absent; babylon_test not migrated")
    return PostgresRuntime(pool=pg_pool)


@pytest.fixture(scope="module")
def session_ids() -> dict[str, object]:
    """Distinct sessions per part so parts stay order-independent under pytest-randomly."""
    return {"part1": uuid4(), "part2": uuid4()}


class _StubLoader:
    """Minimal OD loader returning a fixed pre-built matrix."""

    def __init__(self, matrix: object) -> None:
        self._matrix = matrix

    def load_year(self, year: int) -> object:  # noqa: ARG002 — signature parity
        return self._matrix


class _RaisingClassifier:
    """Classifies the 1st external dest, then raises on the 2nd classify call."""

    def __init__(self) -> None:
        self.calls = 0

    def classify(self, dest_node_id: str) -> object:
        self.calls += 1
        if self.calls >= 2:
            raise RuntimeError("synthetic classifier failure on 2nd classify")
        return SimpleNamespace(dest_node_id=dest_node_id)


def _boundary_row(session_id: object, tick: int, magnitude: float):  # type: ignore[no-untyped-def]
    from babylon.economics.boundary_flow_register import BoundaryFlowRegisterRow
    from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind

    return BoundaryFlowRegisterRow(
        session_id=session_id,  # type: ignore[arg-type]
        tick=tick,
        source_node_id=_ORIGIN_HEX,
        source_kind=NodeKind.HEX,
        dest_node_id="canada",
        dest_kind=NodeKind.EXTERNAL,
        flow_type=BoundaryEdgeKind.COMMUTE_OUT,
        magnitude=magnitude,
    )


def _count_boundary_rows(runtime, session_id: object, tick: int) -> int:  # type: ignore[no-untyped-def]
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM boundary_flow_register WHERE session_id = %s AND tick = %s",
            (session_id, tick),
        )
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def test_partial_buffer_never_reaches_postgres_when_step_raises(runtime, session_ids) -> None:  # type: ignore[no-untyped-def]
    """Part 1 (FR-022): a mid-step raise leaves a partial buffer, zero DB rows."""
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.economics.lodes_commute_matrix import build_year_matrix
    from babylon.economics.node_kinds import NodeKind
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep

    sid = session_ids["part1"]
    # One origin, TWO external dests → the classifier is called twice; it
    # raises on the 2nd, after the 1st dest's rows are already buffered.
    matrix = build_year_matrix(
        pair_counts={(_ORIGIN_HEX, "canada"): 10, (_ORIGIN_HEX, "rest_of_usa"): 20},
        boundary_dest_kind={"canada": NodeKind.EXTERNAL, "rest_of_usa": NodeKind.EXTERNAL},
        year=_YEAR,
    )
    graph = BabylonGraph()
    graph.add_node(_ORIGIN_HEX, _node_type="hex", v=1000.0)
    register = BoundaryFlowRegister()
    step = Vol2CirculationStep(
        od_loader=_StubLoader(matrix),  # type: ignore[arg-type]
        classifier=_RaisingClassifier(),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="synthetic classifier failure"):
        step.step(graph=graph, register=register, session_id=sid, tick=1, simulated_year=_YEAR)

    # The 1st dest's COMMUTE_OUT + paired TRADE_EDGE are buffered in memory...
    assert register.buffered_count() > 0
    # ...but nothing was flushed into an envelope, so Postgres holds nothing.
    assert _count_boundary_rows(runtime, sid, 1) == 0


def test_audit_check_violation_rolls_back_boundary_rows(runtime, session_ids) -> None:  # type: ignore[no-untyped-def]
    """Part 2 (FR-008a): a bad audit row rolls back the tick's boundary rows."""
    from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.partitioning import ensure_session_partitions

    sid = session_ids["part2"]
    ensure_session_partitions(pool=runtime._pool, session_id=sid)  # noqa: SLF001

    good_boundary = _boundary_row(sid, tick=1, magnitude=42.0)
    # scale='bogus_scale' passes Pydantic (<=32 chars) but violates the DB
    # CHECK (migration 0031 admits only enumerated scales + 'external:%').
    bad_audit = ConservationAuditRow(
        session_id=sid,  # type: ignore[arg-type]
        tick=1,
        scale="bogus_scale",
        invariant_name="t052_bad_scale",
        computed_value=1.0,
        expected_value=0.0,
        residual=1.0,
        severity=AuditSeverity.ALARM,
        determinism_hash="0" * 64,
        created_at_utc=datetime.now(tz=UTC),
    )
    envelope = PerTickTransactionEnvelope(
        session_id=sid,  # type: ignore[arg-type]
        tick=1,
        boundary_register_rows=[good_boundary],
        audit_log_rows=[bad_audit],
        determinism_hash="0" * 64,
    )

    with pytest.raises(psycopg.errors.CheckViolation):
        runtime.persist_tick_atomic(envelope)

    # The boundary rows insert BEFORE the audit rows (_spec_062.py ordering);
    # the audit CHECK violation rolls the whole tick back, boundary rows too.
    assert _count_boundary_rows(runtime, sid, 1) == 0


def test_clean_envelope_after_failure_commits(runtime, session_ids) -> None:  # type: ignore[no-untyped-def]
    """Part 3: a clean envelope for a later tick commits — no poison state left."""
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.partitioning import ensure_session_partitions

    sid = session_ids["part2"]  # same session as Part 2 → retry-after-failure
    ensure_session_partitions(pool=runtime._pool, session_id=sid)  # noqa: SLF001

    envelope = PerTickTransactionEnvelope(
        session_id=sid,  # type: ignore[arg-type]
        tick=2,
        boundary_register_rows=[_boundary_row(sid, tick=2, magnitude=7.0)],
        determinism_hash="0" * 64,
    )
    runtime.persist_tick_atomic(envelope)
    assert _count_boundary_rows(runtime, sid, 2) == 1
