"""Integration test: FR-030a/b/c paired cross-border emission (Spec 063 T035).

Quickstart §6: with a synthetic Canadian-coded row injected into a real
session's persisted OD matrix, every ``COMMUTE_OUT`` with
``dest_kind='external'`` carries a same-tick ``TRADE_EDGE`` with swapped
source/dest and equal magnitude (FR-030a); the pairing is observational
only (FR-030b); and the T043 ``PairedCrossBorderEmissionEvaluator`` grades
the live emission clean while a dropped pair alarms (FR-030c).

T033 pin: this file pins the registry invariant that keeps the FR-026 guard
dormant on the DEFAULT external-node set (canada always present). The raising
path itself is exercised by ``test_canada_required_invariant.py`` (T033), which
the lane-6.2 ``external_node_overrides`` / ``synthetic_lodes_canadian_rows``
seams made reachable — superseding this file's earlier note that the kwargs
"were never built".

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN) + LODES data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pytest

from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind
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


def _snapshot_v(graph) -> list[tuple[str, float]]:  # type: ignore[no-untyped-def]
    return sorted(
        (node.id, float(node.attributes.get("v", 0.0)))
        for node in graph.query_nodes(node_type="hex")
    )


@pytest.fixture(scope="module")
def emission_run(runtime) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Session + Canadian injection + one circulation tick + envelope persist."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
    from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
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

    real_loader = LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_LODES_XWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
    )

    class _PgLoader:
        def load_year(self, year: int):  # type: ignore[no-untyped-def]
            return real_loader.load_year_from_postgres(runtime, sid, year)

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
        session_id=sid,
        tick=1,
        simulated_year=_YEAR,
    )
    v_after_step = _snapshot_v(graph)
    flushed = register.flush()
    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=1,
        boundary_register_rows=flushed,
        determinism_hash="0" * 64,
    )
    runtime.persist_tick_atomic(envelope)
    v_after_persist = _snapshot_v(graph)
    return {
        "sid": sid,
        "report": report,
        "origin": origin,
        "rows": flushed,
        "v_after_step": v_after_step,
        "v_after_persist": v_after_persist,
    }


def test_every_external_commute_out_has_swapped_equal_pair(emission_run: dict[str, Any]) -> None:
    """FR-030a/c: swapped source/dest + exact-equal magnitude, one pair each."""
    rows = emission_run["rows"]
    commutes = [
        r
        for r in rows
        if r.flow_type is BoundaryEdgeKind.COMMUTE_OUT and r.dest_kind is NodeKind.EXTERNAL
    ]
    trades = [r for r in rows if r.flow_type is BoundaryEdgeKind.TRADE_EDGE]
    assert commutes, "expected external COMMUTE_OUT rows (canada injection + rest_of_usa)"
    available = [(t.source_node_id, t.dest_node_id, t.magnitude) for t in trades]
    for c in commutes:
        key = (c.dest_node_id, c.source_node_id, c.magnitude)  # swapped, equal (exact float)
        assert key in available, f"missing TRADE_EDGE pair for {c!r}"
        available.remove(key)  # one-to-one consume
    assert available == [], "orphan TRADE_EDGE rows without a COMMUTE_OUT partner"


def test_fr_030b_pairing_is_observational(emission_run: dict[str, Any]) -> None:
    """FR-030b: persisting the paired rows never re-enters the v arithmetic."""
    ids_step = [nid for nid, _ in emission_run["v_after_step"]]
    ids_persist = [nid for nid, _ in emission_run["v_after_persist"]]
    assert ids_step == ids_persist
    v_step = np.array([v for _, v in emission_run["v_after_step"]], dtype=np.float64)
    v_persist = np.array([v for _, v in emission_run["v_after_persist"]], dtype=np.float64)
    assert np.array_equal(v_step, v_persist)  # bit-identical


def test_evaluator_clean_on_live_emission(emission_run: dict[str, Any]) -> None:
    """T043 integration proof: the live emission satisfies FR-030c exactly."""
    from babylon.persistence.conservation_audit import PairedCrossBorderEmissionEvaluator

    evaluator = PairedCrossBorderEmissionEvaluator()
    assert evaluator(None, None, {"boundary_rows": emission_run["rows"]}) == []


def test_evaluator_alarms_on_dropped_pair(emission_run: dict[str, Any]) -> None:
    """FR-030c: dropping one canada TRADE_EDGE produces one ALARM audit row."""
    from babylon.persistence.audit_models import AuditSeverity
    from babylon.persistence.conservation_audit import (
        ConservationAuditor,
        PairedCrossBorderEmissionEvaluator,
    )

    rows = list(emission_run["rows"])
    drop_index = next(
        i
        for i, r in enumerate(rows)
        if r.flow_type is BoundaryEdgeKind.TRADE_EDGE and r.source_node_id == "canada"
    )
    del rows[drop_index]

    auditor = ConservationAuditor(epsilon=1e-9, rng_seed=42)
    auditor.register_invariant("paired_cross_border_emission", PairedCrossBorderEmissionEvaluator())
    audit_rows, alarms = auditor.evaluate(
        session_id=emission_run["sid"],
        tick=1,
        hex_rows=[],
        context={"boundary_rows": rows},
    )
    assert len(audit_rows) == 1
    assert audit_rows[0].scale == "external:canada"
    assert audit_rows[0].severity is AuditSeverity.ALARM
    assert len(alarms) == 1
    assert alarms[0].invariant_name == "paired_cross_border_emission"


def test_fr_026_canada_registry_always_present(emission_run: dict[str, Any]) -> None:
    """T033 pin: the registry invariant that keeps FR-026's raise dormant.

    The guard fires only when canada is absent from
    ``report.external_node_ids``; the default ``INTERNATIONAL_NODES``
    enumeration always includes canada, so a default session never raises.
    The raising branch (canada removed via ``external_node_overrides`` while
    synthetic Canadian rows are requested) is exercised by
    ``test_canada_required_invariant.py`` (T033); this pins the complementary
    default-registry invariant.
    """
    from babylon.persistence.postgres_initialization import INTERNATIONAL_NODES

    assert "canada" in INTERNATIONAL_NODES
    assert "canada" in emission_run["report"].external_node_ids
