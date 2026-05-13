"""Property test: hex → county aggregation conserves c/v/s (T043 / SC-002).

For random hex populations, ``SUM(c) FROM v_county_value_aggregate`` MUST
equal the offline Python ``sum(row.c)`` within ε = 1e-10. Runs against the
live Postgres pool — skips when unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration, pytest.mark.property]

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


def _make_envelope(  # type: ignore[no-untyped-def]
    session_id: UUID, hex_values: list[tuple[str, float, float, float]]
):
    """Build envelope from (h3, c, v, s) tuples — all in Wayne County."""
    from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.hex_state import DynamicHexState

    rows = [
        DynamicHexState(
            session_id=session_id,
            tick=0,
            h3_index=h3,
            county_fips="26163",
            state_fips="26",
            region_id="east_north_central",
            c=c,
            v=v,
            s=s,
            k=10.0,
            biocapacity_stock=5.0,
            energy_stock=2.0,
            raw_material_stock=1.0,
            internet_access_pct=0.5,
            surveillance_coupling=0.5,
        )
        for h3, c, v, s in hex_values
    ]
    audit = ConservationAuditRow(
        session_id=session_id,
        tick=0,
        scale="county",
        invariant_name="hex_to_county_sum_c",
        computed_value=sum(c for _, c, _, _ in hex_values),
        expected_value=sum(c for _, c, _, _ in hex_values),
        residual=0.0,
        severity=AuditSeverity.OK,
        determinism_hash="a" * 64,
        created_at_utc=datetime.now(tz=UTC),
    )
    return PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        hex_state_rows=rows,
        audit_log_rows=[audit],
        determinism_hash="a" * 64,
    )


@given(
    populations=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=10,
    )
)
@settings(
    max_examples=15,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_county_view_conserves_hex_cvs(runtime, pg_pool, populations):  # type: ignore[no-untyped-def]
    """SC-002: view aggregation matches Python sum within ε = 1e-10."""
    sid = uuid4()
    hex_values = [(f"872d34{i:04x}fffff"[:15], c, v, s) for i, (c, v, s) in enumerate(populations)]
    runtime.persist_tick_atomic(_make_envelope(sid, hex_values))

    expected_c = sum(c for _, c, _, _ in hex_values)
    expected_v = sum(v for _, _, v, _ in hex_values)
    expected_s = sum(s for _, _, _, s in hex_values)

    with pg_pool.connection() as conn:
        row = conn.execute(
            "SELECT c_sum, v_sum, s_sum FROM v_county_value_aggregate "
            "WHERE session_id = %s AND tick = 0 AND county_fips = '26163'",
            (str(sid),),
        ).fetchone()

    assert row is not None
    assert abs((row[0] or 0.0) - expected_c) <= max(1e-10, abs(expected_c) * 1e-12)
    assert abs((row[1] or 0.0) - expected_v) <= max(1e-10, abs(expected_v) * 1e-12)
    assert abs((row[2] or 0.0) - expected_s) <= max(1e-10, abs(expected_s) * 1e-12)
