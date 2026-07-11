"""Integration test: Detroit-Windsor routing via synthetic injection (Spec 063 T032).

Quickstart §5 / FR-023 / FR-027 / SC-012 (first half): a synthetic
Canadian-coded Census block (state-prefix 99) injected into a real
session's persisted LODES OD matrix routes to ``dest_node_id='canada'``
at emission time through :class:`CrossBorderCommuteClassifier`; without
the injection the same session emits zero canada rows.

Both runs happen inside one module fixture in a fixed sequence
(pre-injection run first), so the tests stay order-independent under
pytest-randomly.

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN) + LODES data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from babylon.domain.economics.node_kinds import BoundaryEdgeKind, NodeKind
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
# Synthetic Canadian-coded Census block (state 99 is outside US FIPS range) —
# the injection convention pinned by test_vol2_classifier_routing.py.
_CANADIAN_BLOCK = "990001234567890"


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
    """Tick-0 hex frame → BabylonGraph (full frame per spec-089; never MAX(tick))."""
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


def _run_readback_tick(runtime, session_id: UUID, graph):  # type: ignore[no-untyped-def]
    """One circulation tick fed by the session's PERSISTED OD matrix.

    A fresh loader per call — ``load_year_from_postgres`` caches by year on
    the instance, so reuse would mask the post-injection matrix.
    """
    from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.domain.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
    from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep

    real_loader = LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_LODES_XWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
    )

    class _PgLoader:
        def load_year(self, year: int):  # type: ignore[no-untyped-def]
            return real_loader.load_year_from_postgres(runtime, session_id, year)

    classifier = CrossBorderCommuteClassifier(
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
        domestic_states=US_DOMESTIC_FIPS_STATES,
    )
    step = Vol2CirculationStep(od_loader=_PgLoader(), classifier=classifier)  # type: ignore[arg-type]
    register = BoundaryFlowRegister()
    step.step(
        graph=graph,
        register=register,
        session_id=session_id,
        tick=1,
        simulated_year=_YEAR,
    )
    return register.flush()


@pytest.fixture(scope="module")
def routing_runs(runtime) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """One session, two runs: pre-injection (negative control) then injected."""
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

    # Negative-control run BEFORE any injection (fresh graph, fresh loader).
    pre_rows = _run_readback_tick(runtime, sid, _hex_graph_from_session(runtime, sid))

    # Pick a deterministic origin hex with v > 0 from the tick-0 frame; the
    # injected OD row makes it a matrix origin with a Canadian-coded dest.
    graph = _hex_graph_from_session(runtime, sid)
    origin = min(
        node.id
        for node in graph.query_nodes(node_type="hex")
        if float(node.attributes.get("v", 0.0)) > 0.0
    )
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            """
            INSERT INTO immutable_reference_lodes_od_matrix
                (session_id, year, home_hex, workplace_dest, workplace_dest_kind, s000_workers)
            VALUES (%s, %s, %s, %s, 'external', 50)
            ON CONFLICT (session_id, year, home_hex, workplace_dest) DO NOTHING
            """,
            (sid, _YEAR, origin, _CANADIAN_BLOCK),
        )
    post_rows = _run_readback_tick(runtime, sid, graph)
    return {"sid": sid, "origin": origin, "pre_rows": pre_rows, "post_rows": post_rows}


def test_no_canada_rows_without_injection(routing_runs: dict[str, Any]) -> None:
    """SC-012 first half: canonical LODES yields zero canada COMMUTE_OUT rows."""
    canada = [
        r
        for r in routing_runs["pre_rows"]
        if r.flow_type is BoundaryEdgeKind.COMMUTE_OUT and r.dest_node_id == "canada"
    ]
    assert canada == []


def test_synthetic_canadian_row_routes_to_canada(routing_runs: dict[str, Any]) -> None:
    """FR-023/FR-027: exactly one COMMUTE_OUT lands on dest_node_id='canada'."""
    canada = [
        r
        for r in routing_runs["post_rows"]
        if r.flow_type is BoundaryEdgeKind.COMMUTE_OUT and r.dest_node_id == "canada"
    ]
    assert len(canada) == 1
    row = canada[0]
    assert row.dest_kind is NodeKind.EXTERNAL
    assert row.source_node_id == routing_runs["origin"]
    assert row.magnitude > 0.0
