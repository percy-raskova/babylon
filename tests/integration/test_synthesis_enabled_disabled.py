"""Integration tests for Option B synthesis enabled vs disabled (Spec 063 T036).

Quickstart §8 / SC-011 + SC-012: an ``enable_border_commute_synthesis=True``
session synthesizes weekly Detroit-Windsor rows from a (synthetic) BTS CSV,
persists them, and merges the us_to_canada direction into the LODES OD
matrix so ``LODESCommuteMatrixLoader.load_year_from_postgres()`` reads back
a ``canada`` destination; a default (disabled) session produces zero canada
rows everywhere.

The circulation leg runs ``Vol2CirculationStep`` WITHOUT a classifier: the
merged matrix stores the already-resolved external node id ``'canada'``, and
``CrossBorderCommuteClassifier.classify("canada")`` falls through to Rule 4
(unrecognized format) → ``rest_of_usa`` — the no-classifier path is the one
that preserves loader-provided dest ids (pinned by
``test_no_classifier_keeps_loader_provided_dest_id``).

Requires the live Postgres test pool (BABYLON_TEST_PG_DSN) + LODES data.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind
from tests.constants_063 import (
    DETROIT_TRI_COUNTY_AGGREGATE_HEX,
    DETROIT_TRI_COUNTY_FIPS,
    DETROIT_TRI_COUNTY_HEXES_RES7,
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


def _write_minimal_bts_csv(path: Path, *, year: int) -> None:
    """Write a minimal BTS Border Crossing CSV with 12 months x 2 ports.

    Same shape as the unit-level builder in
    ``tests/unit/economics/circulation/test_border_commute_synthesis.py``
    (copied, not imported — test modules must not import each other).
    """
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Port Code", "Measure", "Date", "Value"])
        for month in range(1, 13):
            for port in ("3801", "3802"):
                writer.writerow([port, "Personal Vehicles", f"{year:04d}-{month:02d}", 5000])


def _enabled_defines():  # type: ignore[no-untyped-def]
    from babylon.config.defines import GameDefines

    defines = GameDefines.load_default()
    return defines.model_copy(
        update={
            "economy": defines.economy.model_copy(update={"enable_border_commute_synthesis": True})
        }
    )


def _init_session(runtime, defines, **extra):  # type: ignore[no-untyped-def]
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=defines,
        start_year=_YEAR,
        scenario_length_years=1,
        counties=sorted(DETROIT_TRI_COUNTY_FIPS),
        lodes_root=_LODES_ROOT,
        lodes_crosswalk=_LODES_XWALK,
        lodes_study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        lodes_study_area_states=_STUDY_STATES,
        **extra,
    )
    return sid, report


def _hex_graph_from_session(runtime, session_id: UUID):  # type: ignore[no-untyped-def]
    """Build a BabylonGraph of _node_type='hex' nodes from tick-0 hex rows.

    The canonical runner's engine graph carries no hex nodes (spec-063 tail
    brief drift note); Vol2CirculationStep is therefore exercised directly
    against the session's REAL persisted tick-0 hex frame. Tick 0 is a full
    frame per spec-089, so ``WHERE tick = 0`` is safe (never MAX(tick)).
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


def _run_circulation_readback(runtime, session_id: UUID, graph):  # type: ignore[no-untyped-def]
    """One Vol2CirculationStep tick fed by the session's persisted OD matrix.

    No classifier: the persisted matrix carries already-resolved external
    node ids (``canada`` / ``rest_of_usa``) which classify() Rule 4 would
    reroute to rest_of_usa (see module docstring).
    """
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
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

    step = Vol2CirculationStep(od_loader=_PgLoader())  # type: ignore[arg-type]
    register = BoundaryFlowRegister()
    result = step.step(
        graph=graph,
        register=register,
        session_id=session_id,
        tick=1,
        simulated_year=_YEAR,
    )
    return result, register


def test_enabled_session_synthesizes_and_merges(runtime, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """SC-011: enabled session synthesizes 52 weekly rows + merges canada OD."""
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader

    bts = tmp_path / "bts_border_crossings.csv"
    _write_minimal_bts_csv(bts, year=_YEAR)

    sid, report = _init_session(
        runtime,
        _enabled_defines(),
        hex_hydration_counties=DETROIT_TRI_COUNTY_FIPS,
        border_bts_csv=bts,
        border_aggregate_hex=DETROIT_TRI_COUNTY_AGGREGATE_HEX,
    )
    # 52 weeks x 1 direction (BTS-only; no StatCan CSV) x 1 year.
    assert report.border_synthesis_row_count == 52
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM immutable_reference_border_commute_synthesis "
            "WHERE session_id = %s",
            (sid,),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == 52

    # T042 read-back proof: a FRESH loader reads the MERGED matrix back.
    fresh = LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_LODES_XWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
    )
    matrix = fresh.load_year_from_postgres(runtime, sid, _YEAR)
    assert "canada" in matrix.dest_to_col
    assert matrix.dest_kind_by_col[matrix.dest_to_col["canada"]] is NodeKind.EXTERNAL

    # Circulation leg: canada COMMUTE_OUT emission is v-gated — the
    # synthesized origin is the tri-county centroid hex, which hex
    # hydration populates for Wayne County. If the frame ever stops
    # carrying v>0 there, fall back to the matrix-level proof above.
    graph = _hex_graph_from_session(runtime, sid)
    aggregate_v = 0.0
    if graph.has_node(DETROIT_TRI_COUNTY_AGGREGATE_HEX):
        aggregate_v = float(
            graph.get_node(DETROIT_TRI_COUNTY_AGGREGATE_HEX).attributes.get("v", 0.0)
        )
    _result, register = _run_circulation_readback(runtime, sid, graph)
    canada_rows = register.query(flow_type=BoundaryEdgeKind.COMMUTE_OUT, dest_node_id="canada")
    if aggregate_v > 0.0:
        assert canada_rows, "aggregate hex carries v>0 but no canada COMMUTE_OUT emitted"
        assert all(r.magnitude > 0.0 for r in canada_rows)
        assert all(r.dest_kind is NodeKind.EXTERNAL for r in canada_rows)
    else:
        assert canada_rows == []


def test_disabled_session_produces_no_canada_rows(runtime) -> None:  # type: ignore[no-untyped-def]
    """SC-012: default defines produce zero canada rows at every layer."""
    from babylon.config.defines import GameDefines
    from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader

    sid, report = _init_session(
        runtime,
        GameDefines.load_default(),
        hex_hydration_counties=DETROIT_TRI_COUNTY_FIPS,
    )
    assert report.border_synthesis_row_count == 0
    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM immutable_reference_border_commute_synthesis "
            "WHERE session_id = %s",
            (sid,),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == 0

    fresh = LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_LODES_XWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=_STUDY_STATES,
    )
    matrix = fresh.load_year_from_postgres(runtime, sid, _YEAR)
    assert "canada" not in matrix.dest_to_col

    graph = _hex_graph_from_session(runtime, sid)
    _result, register = _run_circulation_readback(runtime, sid, graph)
    assert register.query(flow_type=BoundaryEdgeKind.COMMUTE_OUT, dest_node_id="canada") == []


def test_enabled_without_bts_fails_fast(runtime, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """FR-036 through the init path: enabled + missing BTS CSV fails loud."""
    with pytest.raises(FileNotFoundError, match="BTS Border Crossing CSV required"):
        _init_session(
            runtime,
            _enabled_defines(),
            border_bts_csv=tmp_path / "missing.csv",
            border_aggregate_hex=DETROIT_TRI_COUNTY_AGGREGATE_HEX,
        )


def test_enabled_without_aggregate_hex_raises(runtime, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """enable_border_commute_synthesis=True with no aggregate hex fails loud."""
    from babylon.persistence.postgres_initialization import InitializationError

    bts = tmp_path / "bts_border_crossings.csv"
    _write_minimal_bts_csv(bts, year=_YEAR)
    with pytest.raises(InitializationError, match="border_aggregate_hex"):
        _init_session(
            runtime,
            _enabled_defines(),
            border_bts_csv=bts,
        )
