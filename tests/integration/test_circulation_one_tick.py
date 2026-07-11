"""Integration test: end-to-end one-tick Vol II circulation (Spec 063 T013).

Quickstart §3 / FR-009 / FR-010 / FR-030a / SC-002: hydrate a real Detroit
tri-county session via ``initialize_session()``, drive ``Vol2CirculationStep``
directly against the session's persisted tick-0 hex frame, and verify value
conservation plus the FR-008a boundary-row round trip.

The step is exercised directly (not via ``engine.run_tick``) because the
canonical runner's engine graph carries no ``_node_type='hex'`` nodes —
vol2 runner wiring is Phase 5.2 scope, not this test's. The quickstart's
``runtime.fetch_v_total_in_study_area()`` helper does not exist; totals
come from :class:`CirculationStepResult` + the graph.

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN) + LODES data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from babylon.economics.node_kinds import BoundaryEdgeKind
from tests.constants_063 import (
    DETROIT_TRI_COUNTY_FIPS,
    DETROIT_TRI_COUNTY_HEXES_RES7,
    US_DOMESTIC_FIPS_STATES,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
    pytest.mark.skipif(
        not Path("data/sqlite/marxist-data-3NF.sqlite").exists(),
        reason="SQLite reference DB not present at data/sqlite/",
    ),
    pytest.mark.skipif(
        not Path("data/lodes/od").exists() or not Path("data/lodes/us_xwalk.csv.gz").exists(),
        reason="LODES OD data not present at data/lodes/",
    ),
    pytest.mark.skipif(
        not Path("data/tiger/county/tl_2024_us_county.shp").exists(),
        reason="TIGER county shapefile not present at data/tiger/county/",
    ),
]

_SQLITE = Path("data/sqlite/marxist-data-3NF.sqlite")
_LODES_ROOT = Path("data/lodes")
_LODES_XWALK = Path("data/lodes/us_xwalk.csv.gz")
_STUDY_STATES = frozenset({"26"})
_YEAR = 2010


@pytest.fixture(scope="module")
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def apply_migrations(pg_pool):  # type: ignore[no-untyped-def]
    """Apply migrations, retrying the specific catalog races.

    The shared babylon_test DB receives concurrent migration applies from
    sibling test runs; ``CREATE ... IF NOT EXISTS`` is not race-proof at
    the pg_catalog level, so one bounded retry loop absorbs the transient
    DDL collisions without masking real failures.
    """
    import time as _time

    from psycopg import errors as _pg_errors

    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    last_error: Exception | None = None
    for _attempt in range(3):  # fixed upper bound
        try:
            with pg_pool.connection() as conn:
                conn.autocommit = True
                for sql_file in sorted(migrations_dir.glob("00*.sql")):
                    conn.execute(sql_file.read_text())
            return
        except (
            _pg_errors.UniqueViolation,
            _pg_errors.DuplicateTable,
            _pg_errors.DuplicateObject,
            _pg_errors.UndefinedTable,
        ) as exc:
            last_error = exc
            _time.sleep(2.0)
    raise AssertionError(f"migration apply kept racing after 3 attempts: {last_error}")


@pytest.fixture(scope="module")
def tiger_geometries_ingested(pg_pool, apply_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence.tiger_ingestion import ingest_tiger_counties

    ingest_tiger_counties(
        pg_pool,
        Path("data/tiger/county/tl_2024_us_county.shp"),
    )


@pytest.fixture(scope="module")
def runtime(pg_pool, apply_migrations, tiger_geometries_ingested):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def _hex_graph_from_session(runtime, session_id: UUID):  # type: ignore[no-untyped-def]
    """Build a BabylonGraph of _node_type='hex' nodes from tick-0 hex rows.

    Tick 0 is a full frame per spec-089, so ``WHERE tick = 0`` is safe
    (never ``MAX(tick)`` — dynamic_hex_state is sparse from tick 1 on).
    """
    from babylon.topology.graph import BabylonGraph

    graph = BabylonGraph()
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT h3_index, v FROM dynamic_hex_state WHERE session_id = %s AND tick = 0",
            (session_id,),
        )
        rows = cur.fetchall()
    frame = {h3_index: float(v) for h3_index, v in rows}
    # Pad to the SPEC's full study area: polygon-envelope cells that the
    # county-based hydration does not populate enter at v=0.0. Without the
    # padding, v routed to in-study-but-unhydrated HEX dest columns is
    # dropped by the step and the FR-010 guard aborts the tick (observed
    # 2026-07-08: residual ~0.14% of pre_total_v — a real pre-wiring hazard
    # for remediation Phase 5.2's runner integration).
    for hex_id in sorted(DETROIT_TRI_COUNTY_HEXES_RES7 | frozenset(frame)):
        graph.add_node(hex_id, _node_type="hex", v=frame.get(hex_id, 0.0))
    return graph


def _run_one_circulation_tick(session_id: UUID, graph, *, tick: int = 1):  # type: ignore[no-untyped-def]
    """One Vol2CirculationStep tick against the on-disk LODES matrix."""
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
    from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep

    loader = LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_LODES_XWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
    )
    classifier = CrossBorderCommuteClassifier(
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
        domestic_states=US_DOMESTIC_FIPS_STATES,
    )
    step = Vol2CirculationStep(od_loader=loader, classifier=classifier)
    register = BoundaryFlowRegister()
    result = step.step(
        graph=graph,
        register=register,
        session_id=session_id,
        tick=tick,
        simulated_year=_YEAR,
    )
    return result, register


@pytest.fixture(scope="module")
def circulation_run(runtime) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Initialize one real session and run one circulation tick."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    initialize_session(
        session_id=sid,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=GameDefines.load_default(),
        start_year=_YEAR,
        scenario_length_years=1,
        counties=sorted(DETROIT_TRI_COUNTY_FIPS),
        hex_hydration_counties=DETROIT_TRI_COUNTY_FIPS,
        lodes_root=_LODES_ROOT,
        lodes_crosswalk=_LODES_XWALK,
        lodes_study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        lodes_study_area_states=_STUDY_STATES,
    )
    graph = _hex_graph_from_session(runtime, sid)
    pre_total = sum(
        float(node.attributes.get("v", 0.0)) for node in graph.query_nodes(node_type="hex")
    )
    result, register = _run_one_circulation_tick(sid, graph)
    rows = register.flush()
    return {"sid": sid, "pre_total": pre_total, "result": result, "rows": rows}


def test_one_tick_circulation_conserves_v(circulation_run: dict[str, Any]) -> None:
    """FR-010 / SC-002: pre_v == post_in_area_v + boundary_out_v within 1e-9 rel."""
    pre = circulation_run["pre_total"]
    result = circulation_run["result"]
    assert result.pre_total_v == pytest.approx(pre)
    assert result.conservation_residual <= 1e-9 * max(result.pre_total_v, 1.0)
    assert abs(pre - (result.post_total_v_in_area + result.boundary_out_total_v)) <= 1e-9 * max(
        pre, 1.0
    )


def test_boundary_rows_round_trip_postgres(runtime, circulation_run: dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
    """FR-008a: flushed boundary rows commit atomically and read back exactly."""
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = circulation_run["sid"]
    rows = circulation_run["rows"]
    result = circulation_run["result"]
    assert len(rows) == result.rows_emitted

    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=1,
        boundary_register_rows=rows,
        determinism_hash="0" * 64,
    )
    runtime.persist_tick_atomic(envelope)
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM boundary_flow_register WHERE session_id = %s AND tick = 1",
            (sid,),
        )
        fetched = cur.fetchone()
    assert fetched is not None and fetched[0] == result.rows_emitted


def test_commute_out_paired_with_trade_edge_counts(circulation_run: dict[str, Any]) -> None:
    """FR-030a: every COMMUTE_OUT is paired — even row count, equal type counts."""
    result = circulation_run["result"]
    rows = circulation_run["rows"]
    assert result.rows_emitted > 0, "expected out-of-area LODES flows for tri-county Detroit"
    assert result.rows_emitted % 2 == 0
    commute_count = sum(1 for r in rows if r.flow_type is BoundaryEdgeKind.COMMUTE_OUT)
    trade_count = sum(1 for r in rows if r.flow_type is BoundaryEdgeKind.TRADE_EDGE)
    assert commute_count == trade_count
    assert commute_count + trade_count == result.rows_emitted
