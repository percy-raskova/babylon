#!/usr/bin/env python3
"""Spec-062 quickstart walkthrough script (T088).

Executes the five sections of ``specs/062-cross-scale-integration/quickstart.md``
end-to-end against a live Postgres pool. Each section prints ``OK`` on success.
Used as a CI smoke test that exercises:

  1. Initialize a session (sqlite_hydrator + external-node bootstrap)
  2. Advance one tick (SimulationEngine + persist_tick_atomic)
  3. Query county / state / national / global-Φ aggregates
  4. Inspect audit log via ConservationAuditQuery
  5. Add (and verify) a new immutable reference series via lookup

Skips cleanly when Postgres is unavailable. Exits 0 on full success.

Usage::

    BABYLON_TEST_PG_DSN="dbname=babylon_test host=localhost port=5433 user=test password=test" \\
        poetry run python tests/scripts/quickstart_062_walkthrough.py
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from uuid import uuid4

DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]
SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite").resolve()


def main() -> int:
    try:
        from psycopg_pool import ConnectionPool
    except ImportError:
        print("psycopg_pool unavailable; skipping quickstart walkthrough", file=sys.stderr)
        return 0

    dsn = os.environ.get(
        "BABYLON_TEST_PG_DSN",
        "dbname=babylon_test host=localhost port=5433 user=test password=test",
    )

    try:
        pool = ConnectionPool(conninfo=dsn, min_size=1, max_size=2, open=True)
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        print(f"Postgres unavailable ({exc}); skipping", file=sys.stderr)
        return 0

    if not SQLITE_PATH.is_file():
        print(f"SQLite reference DB not found at {SQLITE_PATH}; skipping", file=sys.stderr)
        return 0

    try:
        # Apply spec-062 migrations idempotently
        migrations_dir = Path("src/babylon/persistence/migrations").resolve()
        with pool.connection() as conn:
            conn.autocommit = True
            for sql_file in sorted(migrations_dir.glob("00*.sql")):
                conn.execute(sql_file.read_text())

        from babylon.config.defines import GameDefines
        from babylon.engine.simulation_engine import SimulationEngine
        from babylon.engine.systems.substrate import SubstrateSystem
        from babylon.persistence import PostgresRuntime
        from babylon.persistence.conservation_audit import (
            ConservationAuditor,
            _InvariantResult,
        )
        from babylon.persistence.conservation_audit_query import ConservationAuditQuery
        from babylon.persistence.envelope import PerTickTransactionEnvelope
        from babylon.persistence.hex_state import DynamicHexState
        from babylon.persistence.postgres_aggregation import (
            fetch_county_aggregate,
            fetch_global_phi_balance,
            fetch_national_aggregate,
            fetch_state_aggregate,
        )
        from babylon.persistence.postgres_initialization import initialize_session
        from babylon.persistence.postgres_reference import ImmutableReferenceLookup

        runtime = PostgresRuntime(pool=pool)

        # ─── Section 1: Initialize a session ────────────────────────
        sid = uuid4()
        report = initialize_session(
            session_id=sid,
            sqlite_path=SQLITE_PATH,
            runtime=runtime,
            defines=GameDefines(),
            start_year=2010,
            scenario_length_years=15,
            counties=DETROIT_TRI_COUNTY,
        )
        assert report.external_node_count == 9
        assert "canada" in report.external_node_ids
        assert "hickel_drain" in report.copied_series
        print(
            f"§1 OK: session {sid}, {report.external_node_count} external nodes, "
            f"{len(report.copied_series)} reference series copied"
        )

        # ─── Section 2: Advance one tick ────────────────────────────
        # Set up a minimal hex graph + auditor + engine.
        import networkx as nx

        graph: nx.DiGraph[str] = nx.DiGraph()
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
            raw_material_stock=5.0,
        )
        auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)

        def _ok_evaluator(_pre, _post, _ctx):
            return [
                _InvariantResult(
                    scale="county",
                    invariant_name="hex_to_county_sum_c",
                    computed_value=10.0,
                    expected_value=10.0,
                )
            ]

        auditor.register_invariant("hex_to_county_sum_c", _ok_evaluator)
        engine = SimulationEngine(systems=[SubstrateSystem()], auditor=auditor)

        services = type("S", (), {"event_bus": None})()
        ctx: dict[str, object] = {"tick": 1, "session_id": sid}
        engine.run_tick(graph, services, ctx)

        # Persist a hex_state row + the audit row
        hex_row = DynamicHexState(
            session_id=sid,
            tick=1,
            h3_index="872d34a89ffffff",
            county_fips="26163",
            state_fips="26",
            region_id="east_north_central",
            c=10.0,
            v=5.0,
            s=3.0,
            k=100.0,
            biocapacity_stock=20.0,
            energy_stock=10.0,
            raw_material_stock=5.0,
            internet_access_pct=0.5,
            surveillance_coupling=0.5,
        )
        audit_rows = ctx.get("audit_rows", [])
        env = PerTickTransactionEnvelope(
            session_id=sid,
            tick=1,
            hex_state_rows=[hex_row],
            audit_log_rows=audit_rows,
            determinism_hash=audit_rows[0].determinism_hash if audit_rows else "0" * 64,
        )
        runtime.persist_tick_atomic(env)
        last_committed = runtime.get_last_committed_tick(sid)
        assert last_committed == 1
        print(f"§2 OK: tick {last_committed} committed; substrate ran in pipeline")

        # ─── Section 3: Query an aggregate ──────────────────────────
        county = fetch_county_aggregate(
            runtime=runtime, session_id=sid, tick=1, county_fips="26163"
        )
        assert county is not None and county.c_sum == 10.0
        state = fetch_state_aggregate(runtime=runtime, session_id=sid, tick=1, state_fips="26")
        assert state is not None and state.c_sum == 10.0
        nationals = fetch_national_aggregate(runtime=runtime, session_id=sid, tick_range=(0, 5))
        assert any(n.c_sum == 10.0 for n in nationals)
        phi_balance = fetch_global_phi_balance(runtime=runtime, session_id=sid, annual_only=False)
        # Phi balance may be empty when no drain edges exist; that's fine.
        print(
            f"§3 OK: county c_sum={county.c_sum}, state c_sum={state.c_sum}, "
            f"national rows={len(nationals)}, phi_balance rows={len(phi_balance)}"
        )

        # ─── Section 4: Inspect the audit log ───────────────────────
        query = ConservationAuditQuery(runtime)
        rows = query.fetch(session_id=sid)
        counts = query.count_by_severity(sid)
        assert counts["ok"] >= 1
        assert counts["alarm"] == 0
        print(f"§4 OK: {len(rows)} audit row(s); severity counts {counts}")

        # ─── Section 5: Add a new reference series (lookup contract) ─
        # Using a real hydrated series (CPI) to demonstrate the lookup;
        # the registration step is documentation in defines.py.
        lookup = ImmutableReferenceLookup(runtime, sid, 2010, 2024)

        def cpi_provider(series_id: str, year: int) -> float:  # noqa: ARG001
            with pool.connection() as conn:
                row = conn.execute(
                    "SELECT rate FROM immutable_reference_fred_rates "
                    "WHERE session_id = %s AND year = %s AND series_id = 'CPIAUCSL'",
                    (str(sid), year),
                ).fetchone()
            if row is None or row[0] is None:
                raise KeyError(f"No CPI for {year}")
            return float(row[0])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cpi_2010 = lookup.get(
                "cpi", tick=0, policy="slowly_varying", value_provider=cpi_provider
            )
        assert cpi_2010.value > 0
        print(
            f"§5 OK: CPI lookup for 2010 returned {cpi_2010.value:.2f} "
            f"({cpi_2010.lookup_method.value})"
        )

        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    sys.exit(main())
