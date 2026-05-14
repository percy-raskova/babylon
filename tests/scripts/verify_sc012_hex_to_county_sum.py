#!/usr/bin/env python3
"""SC-012 verification script (T049).

Inserts a known 3-hex distribution into ``dynamic_hex_state``, queries
``v_county_value_aggregate``, and prints ``match=True`` if the residual
between the view sum and the offline Python sum is ≤ 1e-10.

Used as a CI smoke test. Skips cleanly when Postgres is unavailable.

Usage::

    BABYLON_TEST_PG_DSN="dbname=babylon_test host=localhost port=5433 user=test password=test" \\
        poetry run python tests/scripts/verify_sc012_hex_to_county_sum.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    try:
        from psycopg_pool import ConnectionPool
    except ImportError:
        print("psycopg_pool unavailable; skipping SC-012 verification", file=sys.stderr)
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
        print(f"Postgres unavailable ({exc}); skipping SC-012 verification", file=sys.stderr)
        return 0

    try:
        # Apply spec-062 migrations idempotently
        migrations_dir = Path("src/babylon/persistence/migrations").resolve()
        with pool.connection() as conn:
            conn.autocommit = True
            for sql_file in sorted(migrations_dir.glob("00*.sql")):
                conn.execute(sql_file.read_text())

        from babylon.persistence import PostgresRuntime
        from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
        from babylon.persistence.envelope import PerTickTransactionEnvelope
        from babylon.persistence.hex_state import DynamicHexState

        runtime = PostgresRuntime(pool=pool)
        sid = uuid4()

        # Seed three Wayne County hexes with known c values
        hexes = [
            DynamicHexState(
                session_id=sid,
                tick=0,
                h3_index=f"872d34a{i:02x}ffffff"[:15],
                county_fips="26163",
                state_fips="26",
                region_id="east_north_central",
                c=10.0 * (i + 1),
                v=5.0,
                s=3.0,
                k=100.0,
                biocapacity_stock=20.0,
                energy_stock=10.0,
                raw_material_stock=5.0,
                internet_access_pct=0.5,
                surveillance_coupling=0.5,
            )
            for i in range(3)
        ]
        audit = ConservationAuditRow(
            session_id=sid,
            tick=0,
            scale="county",
            invariant_name="hex_to_county_sum_c",
            computed_value=60.0,
            expected_value=60.0,
            residual=0.0,
            severity=AuditSeverity.OK,
            determinism_hash="f" * 64,
            created_at_utc=datetime.now(tz=UTC),
        )
        envelope = PerTickTransactionEnvelope(
            session_id=sid,
            tick=0,
            hex_state_rows=hexes,
            audit_log_rows=[audit],
            determinism_hash="f" * 64,
        )
        runtime.persist_tick_atomic(envelope)

        # Compute Python sum
        python_sum = sum(h.c for h in hexes)

        # Query view sum
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT c_sum FROM v_county_value_aggregate "
                "WHERE session_id = %s AND tick = 0 AND county_fips = '26163'",
                (str(sid),),
            ).fetchone()

        if row is None:
            print("match=False (view returned no row)")
            return 1

        view_sum = float(row[0])
        residual = abs(view_sum - python_sum)
        match = residual <= 1e-10
        print(
            f"match={match} (python_sum={python_sum}, view_sum={view_sum}, residual={residual:.2e})"
        )
        return 0 if match else 1
    finally:
        pool.close()


if __name__ == "__main__":
    sys.exit(main())
