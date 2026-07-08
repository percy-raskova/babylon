"""Integration test: FR-014 circulation determinism across sessions (Spec 063 T014).

Quickstart §7 / SC-005: two fresh sessions with identical inputs produce
bit-identical post-step ``v`` vectors, bit-identical boundary rows (modulo
``session_id``), and equal determinism hashes.

The quickstart's ``runtime.fetch_tick_determinism_hash`` helper does not
exist; the hash identity is asserted through the REAL hash function
(:func:`babylon.persistence.conservation_audit.compute_determinism_hash`)
over each session's post-step hex vector. LODES kwargs are deliberately
omitted from ``initialize_session`` — the circulation harness reads the
OD matrix from disk with a fresh loader per session, so the parse path
itself is inside the determinism claim.

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN) + LODES data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pytest

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
_RNG_SEED = 42


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
    from babylon.engine.graph import BabylonGraph

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


def _one_fresh_run(runtime) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Initialize a fresh session + run one circulation tick with a fresh loader."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
    from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep
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
    )
    graph = _hex_graph_from_session(runtime, sid)
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
        session_id=sid,
        tick=1,
        simulated_year=_YEAR,
    )
    post_v = sorted(
        (node.id, float(node.attributes.get("v", 0.0)))
        for node in graph.query_nodes(node_type="hex")
    )
    return {"sid": sid, "result": result, "rows": register.flush(), "post_v": post_v}


@pytest.fixture(scope="module")
def two_runs(runtime) -> tuple[dict[str, Any], dict[str, Any]]:  # type: ignore[no-untyped-def]
    return _one_fresh_run(runtime), _one_fresh_run(runtime)


def test_post_step_v_vectors_bit_identical(
    two_runs: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """FR-014: identical inputs → bit-identical post-step v vectors."""
    a, b = two_runs
    ids_a = [nid for nid, _ in a["post_v"]]
    ids_b = [nid for nid, _ in b["post_v"]]
    assert ids_a == ids_b
    va = np.array([v for _, v in a["post_v"]], dtype=np.float64)
    vb = np.array([v for _, v in b["post_v"]], dtype=np.float64)
    assert np.array_equal(va, vb)  # bit-identical, not approx


def test_boundary_rows_bit_identical_modulo_session(
    two_runs: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """FR-014: boundary rows identical apart from the session UUID."""
    a, b = two_runs
    rows_a = [r.model_dump(exclude={"session_id"}) for r in a["rows"]]
    rows_b = [r.model_dump(exclude={"session_id"}) for r in b["rows"]]
    assert rows_a == rows_b
    assert rows_a, "expected non-empty boundary rows for tri-county Detroit"


def test_determinism_hash_equal_across_sessions(
    two_runs: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """SC-005: the III.7 hash over post-step hex state matches across sessions."""
    from babylon.persistence.conservation_audit import compute_determinism_hash

    hashes = [
        compute_determinism_hash(
            tick=1,
            rng_seed=_RNG_SEED,
            hex_rows=[{"h3_index": nid, "v": v} for nid, v in run["post_v"]],
        )
        for run in two_runs
    ]
    assert hashes[0] == hashes[1]
    assert len(hashes[0]) == 64
