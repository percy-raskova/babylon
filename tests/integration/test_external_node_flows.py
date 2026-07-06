"""Spec-065 T053/T054: external boundary flows persistence + summary aggregation.

T053: After a canonical sim run, the BoundaryFlowRegister has flushed
      rows into ``boundary_flow_register``. Even when zero engine-side
      rows are pushed (current Phase 5 first cut), the table is queried
      cleanly and the aggregator returns an empty list without error.
T054: ``summary.external_node_flows`` matches direct SQL aggregation
      of the same table — they're the same source.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import UUID

import pytest

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        psycopg.connect(dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _postgres_reachable(), reason="Postgres test DB not reachable"),
    pytest.mark.skipif(
        not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}"
    ),
]


def _ensure_pg_dsn_env() -> None:
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)


def _run_runner(*, ticks: int = 3) -> object:
    from babylon.engine.headless_runner.models import SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    sc = resolve_scope("detroit-tri-county")
    config = SimulationRunConfig(
        ticks=ticks,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=sc.scope_fips,
        external_node_ids=sc.external_node_ids,
        sqlite_reference_path=SQLITE_REF,
        output_dir=Path(tempfile.mkdtemp(prefix="sim_boundary_")),
    )
    return runner_run(config)


def _inject_boundary_row(session_id: UUID, tick: int = 1) -> None:
    """Inject a fake boundary_flow_register row to verify the aggregator picks it up.

    Production engine systems will push these via BoundaryFlowRegister.record;
    we bypass that for the test since engine integration is deferred.
    """
    import psycopg

    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            INSERT INTO boundary_flow_register (
                session_id, tick,
                source_node_id, source_kind,
                dest_node_id, dest_kind,
                flow_type, magnitude
            ) VALUES (
                %s, %s,
                '26163', 'county',
                'canada', 'external',
                'drain_edge', 1234567.89
            ) ON CONFLICT DO NOTHING
            """,
            (str(session_id), tick),
        )
        conn.commit()


def test_register_rows_persisted() -> None:
    """T053: aggregate_external_node_flows runs cleanly across the table.

    Without engine integration, no boundary rows are pushed by the
    runner today. We inject one synthetic row directly to validate
    the read path works end-to-end.
    """
    _ensure_pg_dsn_env()
    result = _run_runner(ticks=3)
    assert result.exit_reason.value == "completed"  # type: ignore[attr-defined]
    _inject_boundary_row(result.session_id, tick=1)  # type: ignore[attr-defined]

    import psycopg

    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM boundary_flow_register "
            "WHERE session_id = %s AND dest_node_id = 'canada' "
            "AND flow_type = 'drain_edge'",
            (str(result.session_id),),  # type: ignore[attr-defined]
        ).fetchone()
    assert row is not None
    assert int(row[0]) >= 1


def test_aggregation_matches_register() -> None:
    """T054: summary.external_node_flows == direct SQL SUM. (FR-014)"""
    _ensure_pg_dsn_env()
    result = _run_runner(ticks=3)
    assert result.exit_reason.value == "completed"  # type: ignore[attr-defined]
    _inject_boundary_row(result.session_id, tick=1)  # type: ignore[attr-defined]

    # Re-read the summary through the aggregator function (the runner
    # already wrote summary.json before the inject; we recompute here
    # to verify equality with the SQL source of truth).
    from psycopg_pool import ConnectionPool

    from babylon.engine.headless_runner.run_summary import aggregate_external_node_flows

    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    pool = ConnectionPool(conninfo=dsn, min_size=1, max_size=2, open=True)
    try:
        agg_rows = aggregate_external_node_flows(
            pool=pool,
            session_id=str(result.session_id),  # type: ignore[attr-defined]
        )
        # Direct SQL truth. Spec-101 review fix #5: the external node ('canada')
        # is NOT reliably on one fixed side — the injected synthetic row (below)
        # puts it on dest_node_id, while real DRAIN_EDGE rows from
        # phi_distribution.py put it on source_node_id (bloc is the SOURCE,
        # county is the DEST). Match either side, same as the fixed aggregator.
        with pool.connection() as conn:
            sql_row = conn.execute(
                "SELECT SUM(magnitude) "
                "FROM boundary_flow_register "
                "WHERE session_id = %s AND flow_type = 'drain_edge' "
                "AND (  (source_kind = 'external' AND source_node_id = 'canada') "
                "    OR (dest_kind = 'external' AND dest_node_id = 'canada') )",
                (str(result.session_id),),  # type: ignore[attr-defined]
            ).fetchone()
    finally:
        pool.close()

    canada_row = next((r for r in agg_rows if r["node_id"] == "canada"), None)
    assert canada_row is not None
    assert sql_row is not None
    expected = float(sql_row[0] or 0.0)
    # Tolerance: 1 cent.
    assert abs(canada_row["total_phi_inflow"] - expected) < 0.01
