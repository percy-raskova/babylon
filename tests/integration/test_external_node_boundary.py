"""External node boundary integration test (T071 / US6 / SC-010).

Verifies that initialize_session populates dynamic_external_node_state with
all 9 canonical nodes (8 international + rest_of_usa), then exercises
boundary register flow types via persist_tick_atomic.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite").resolve()
DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]


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


@pytest.fixture(scope="module")
def hydrated_session(runtime):  # type: ignore[no-untyped-def]
    if not SQLITE_PATH.is_file():
        pytest.skip(f"SQLite reference DB not found at {SQLITE_PATH}")
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    initialize_session(
        session_id=sid,
        sqlite_path=SQLITE_PATH,
        runtime=runtime,
        defines=GameDefines(),
        start_year=2010,
        scenario_length_years=15,
        counties=DETROIT_TRI_COUNTY,
    )
    return sid


def test_all_nine_external_nodes_present(runtime, pg_pool, hydrated_session):  # type: ignore[no-untyped-def]
    """FR-036: 8 international + 1 domestic_rest = 9 nodes per session."""
    with pg_pool.connection() as conn:
        rows = conn.execute(
            "SELECT node_id, kind FROM dynamic_external_node_state "
            "WHERE session_id = %s ORDER BY node_id",
            (str(hydrated_session),),
        ).fetchall()
    assert len(rows) == 9
    node_ids = {r[0] for r in rows}
    assert node_ids == {
        "canada",
        "china",
        "eu",
        "india",
        "latin_america",
        "rest_of_usa",
        "russia_csi",
        "southeast_asia",
        "sub_saharan_africa",
    }
    # rest_of_usa is the only domestic_rest node
    domestic = [r for r in rows if r[1] == "domestic_rest"]
    assert len(domestic) == 1 and domestic[0][0] == "rest_of_usa"
    international = [r for r in rows if r[1] == "international"]
    assert len(international) == 8


def test_canada_carries_real_bilateral_trade(runtime, pg_pool, hydrated_session):  # type: ignore[no-untyped-def]
    """R4 / GATE-5: Canada is a first-class node and carries 2010 bilateral trade."""
    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT bilateral_trade_value FROM dynamic_external_node_state "
            "WHERE session_id = %s AND node_id = 'canada'",
            (str(hydrated_session),),
        ).fetchone()
    assert row is not None
    # 2010 US-Canada bilateral trade was ~$525B; we're forgiving on the lower bound.
    assert row[0] > 1e11, f"Canada bilateral trade looks too small: {row[0]}"


def test_boundary_register_round_trip(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """A DRAIN_EDGE row from external→county persists and round-trips."""
    from babylon.domain.economics.boundary_flow_register import (
        BoundaryEdgeKind,
        BoundaryFlowRegisterRow,
        NodeKind,
    )
    from babylon.persistence.envelope import PerTickTransactionEnvelope

    sid = uuid4()
    row = BoundaryFlowRegisterRow(
        session_id=sid,
        tick=0,
        source_node_id="china",
        source_kind=NodeKind.EXTERNAL,
        dest_node_id="26163",
        dest_kind=NodeKind.COUNTY,
        flow_type=BoundaryEdgeKind.DRAIN_EDGE,
        magnitude=1_000_000.0,
    )
    envelope = PerTickTransactionEnvelope(
        session_id=sid,
        tick=0,
        boundary_register_rows=[row],
        determinism_hash="b" * 64,
    )
    runtime.persist_tick_atomic(envelope)

    with pg_pool.connection() as conn:
        rows = conn.execute(
            "SELECT source_node_id, source_kind, dest_node_id, dest_kind, "
            "       flow_type, magnitude FROM boundary_flow_register "
            "WHERE session_id = %s",
            (str(sid),),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0] == ("china", "external", "26163", "county", "drain_edge", 1_000_000.0)
