"""SubstrateSystem pipeline integration test (T083 / US7; retired-hex note #39 T6).

Drives SubstrateSystem through one tick against a live Postgres pool.

#39 T6 rewrote SubstrateSystem to run real depletion dynamics on
county-grain ``Territory`` nodes (``county_fips`` + ``raw_material_stock``),
never ``NodeType.HEX`` (no production code path ever stamps a hex node onto
the engine graph -- confirmed dead vocabulary,
``sentinels/vocabulary/registry.py``'s ``UNSTAMPED_QUERY_ALLOWLIST``). The
hex-node graphs below therefore now exercise the NO-OP path (zero eligible
Territory nodes -- SubstrateSystem never even touches
``services.defines``): a live-pool smoke test that step() runs cleanly
inside a real engine tick, and that a no-op System still lets the
auditor/persistence pipeline complete end-to-end.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import pytest

from babylon.engine.context import TickContext
from babylon.topology.graph import BabylonGraph

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


def test_substrate_runs_in_default_pipeline_with_live_pool(runtime, caplog):  # type: ignore[no-untyped-def]
    """SubstrateSystem.step() executes cleanly against a live runtime when
    the graph has zero Territory nodes (a hex-only graph, e.g.).

    #39 T6: this is the no-op path by construction (no NodeType.TERRITORY
    nodes at all, so the eligibility query is empty and the system returns
    before ever touching services.defines) -- the ``services`` stub below
    deliberately carries no ``defines`` attribute, which would raise if
    SubstrateSystem tried to read it. Passing here is itself the assertion
    that the no-op path never reaches that read.
    """
    from babylon.engine.simulation_engine import SimulationEngine
    from babylon.engine.systems.substrate import SubstrateSystem

    graph = BabylonGraph()
    graph.add_node(
        "872d34a89ffffff",
        _node_type="hex",
        county_fips="26163",
        state_fips="26",
        c=10.0,
        v=5.0,
        s=3.0,
        k=100.0,
        biocapacity_stock=20.0,
        energy_stock=10.0,
        raw_material_stock=0.0,  # Zero at tick start
    )
    # Run substrate alone (Territory has heavy fixture requirements; the
    # integration test only needs to prove substrate.step() executes
    # against a graph that holds real pre-tick values).
    engine = SimulationEngine(systems=[SubstrateSystem()])
    services = type("S", (), {"event_bus": None})()
    with caplog.at_level(logging.DEBUG):
        engine.run_tick(graph, services, TickContext(tick=1))

    # No Territory nodes -> SubstrateSystem never touches this hex node's
    # attributes at all (untouched, not "pass-through processed").
    assert graph.nodes["872d34a89ffffff"]["raw_material_stock"] == 0.0
    assert graph.nodes["872d34a89ffffff"]["energy_stock"] == 10.0
    assert graph.nodes["872d34a89ffffff"]["biocapacity_stock"] == 20.0


def test_engine_with_auditor_persists_audit_row_to_live_pool(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """End-to-end: engine.run_tick → auditor → audit_log row persists.

    SubstrateSystem is the driver System here purely as a harmless no-op
    (the hex-only graph has zero Territory nodes) -- the auditor's canned
    evaluator, not SubstrateSystem's own math, is what this test exercises.
    """
    from babylon.engine.simulation_engine import SimulationEngine
    from babylon.engine.systems.substrate import SubstrateSystem
    from babylon.persistence.audit_models import AuditSeverity
    from babylon.persistence.conservation_audit import ConservationAuditor, _InvariantResult
    from babylon.persistence.conservation_audit_query import ConservationAuditQuery
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

    def ok_evaluator(pre, post, ctx):  # noqa: ARG001
        return [
            _InvariantResult(
                scale="county",
                invariant_name="hex_to_county_sum_c",
                computed_value=10.0,
                expected_value=10.0,
            )
        ]

    auditor.register_invariant("hex_to_county_sum_c", ok_evaluator)
    engine = SimulationEngine(systems=[SubstrateSystem()], auditor=auditor)

    graph = BabylonGraph()
    graph.add_node(
        "872d34a89ffffff",
        _node_type="hex",
        c=10.0,
        v=5.0,
        s=3.0,
        k=100.0,
        biocapacity_stock=20.0,
        energy_stock=10.0,
        raw_material_stock=5.0,
    )
    services = type("S", (), {"event_bus": None})()
    context = TickContext(tick=0, session_id=sid)
    engine.run_tick(graph, services, context)

    # Auditor stashed audit_rows into context. Persist them.
    audit_rows = context.get("audit_rows", [])
    assert len(audit_rows) == 1
    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=0,
        audit_log_rows=audit_rows,
        determinism_hash=audit_rows[0].determinism_hash,
    )
    runtime.persist_tick_atomic(envelope)

    # Round-trip query
    query = ConservationAuditQuery(runtime)
    fetched = query.fetch(session_id=sid)
    assert len(fetched) == 1
    assert fetched[0].severity is AuditSeverity.OK
