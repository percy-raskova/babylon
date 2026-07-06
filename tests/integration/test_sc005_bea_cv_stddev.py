"""SC-005 integration test: per-county c/v standard deviation across 83 Michigan
counties after BEA I-O share wiring (spec-068 T058).

Pre-wiring baseline (spec-066/067): every county gets the same 0.5
intermediate-inputs fraction. The c/v ratio is ``0.5 * GDP / wages``,
which varies across counties due to GDP-to-wage ratio differences —
but the II *share* is uniform.

Post-wiring (spec-068 T056): the per-county share is looked up via the
BEAShareLookupService (QCEW-employment-weighted concordance →
fact_bea_national_industry). Counties with different industry mixes
get different II shares → additional c/v variation on top of the
GDP/wages variation.

The SC-005 gate (spec.md §Success Criteria) requires stddev(c/v) >= 0.2
across 83 Michigan counties. This test measures that at tick-0 hydration
time (no 520-tick simulation needed — c/v is set at hydration) and
verifies the BEA service adds non-trivial variation beyond the
constant-share baseline.

Requires:
  - Postgres on 5433 (BABYLON_TEST_PG_DSN)
  - SQLite reference DB (data/sqlite/marxist-data-3NF.sqlite) with
    fact_bea_national_industry + bridge_naics_bea ingested (spec-068 US1/US3)
  - TIGER county geometries in immutable_reference_tiger_county (Postgres)
"""

from __future__ import annotations

import os
import statistics
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
    pytest.mark.skipif(
        not Path("data/sqlite/marxist-data-3NF.sqlite").exists(),
        reason="SQLite reference DB not present at data/sqlite/",
    ),
]


@pytest.fixture
def pg_pool():
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def apply_migrations(pg_pool):
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture
def mi_county_fips(pg_pool, apply_migrations):
    """Return the frozenset of 83 Michigan county FIPS from the TIGER table."""
    with pg_pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT geoid FROM immutable_reference_tiger_county "
            "WHERE state_fips = '26' ORDER BY geoid"
        )
        fips = frozenset(r[0] for r in cur.fetchall())
    assert len(fips) == 83, f"Expected 83 MI counties, got {len(fips)}"
    return fips


@pytest.fixture
def runtime(pg_pool):
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def _compute_per_county_cv(pool, session_id) -> dict[str, float]:
    """Query tick-0 hex state (joined through hex_spatial_map) and compute
    per-county c/v = SUM(c) / SUM(v)."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT hsm.county_fips, SUM(d.c) AS total_c, SUM(d.v) AS total_v
            FROM dynamic_hex_state d
            JOIN hex_spatial_map hsm ON hsm.h3_index = d.h3_index
            WHERE d.session_id = %s AND d.tick = 0
            GROUP BY hsm.county_fips
            """,
            (session_id,),
        )
        rows = cur.fetchall()
    cv_by_county = {}
    for fips, total_c, total_v in rows:
        v = float(total_v)
        if v > 0:
            cv_by_county[fips] = float(total_c) / v
    return cv_by_county


def _hydrate_and_measure_cv(runtime, pg_pool, mi_county_fips, bea_service) -> dict[str, float]:
    """Run hydrate_hex_state and return per-county c/v dict."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.hex_hydrator import hydrate_hex_state
    from babylon.persistence.partitioning import ensure_session_partitions

    sid = uuid4()
    ensure_session_partitions(pool=pg_pool, session_id=sid)
    n_rows = hydrate_hex_state(
        runtime=runtime,
        session_id=sid,
        counties=mi_county_fips,
        start_year=2010,
        defines=GameDefines.load_default(),
        bea_share_service=bea_service,
    )
    assert n_rows > 0, "Hydration produced no rows"
    return _compute_per_county_cv(pg_pool, sid)


def test_sc005_bea_service_raises_cv_stddev_above_threshold(
    runtime, pg_pool, mi_county_fips
) -> None:
    """SC-005: stddev(c/v) >= 0.2 across 83 MI counties with BEA service wired.

    The BEA share service looks up per-county intermediate-inputs shares via
    the QCEW-employment-weighted concordance. The resulting c/v distribution
    must clear the 0.2 directional threshold.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from babylon.reference.bea import DefaultBEAShareLookupService

    bea_engine = create_engine("sqlite:///data/sqlite/marxist-data-3NF.sqlite")
    bea_session = Session(bea_engine)
    try:
        svc = DefaultBEAShareLookupService(bea_session)
        cv_by_county = _hydrate_and_measure_cv(runtime, pg_pool, mi_county_fips, svc)
    finally:
        bea_session.close()
        bea_engine.dispose()

    assert len(cv_by_county) >= 83, f"Expected >=83 counties with c/v, got {len(cv_by_county)}"
    cv_values = list(cv_by_county.values())
    stddev = statistics.stdev(cv_values)
    mean_cv = statistics.mean(cv_values)
    assert stddev >= 0.2, (
        f"SC-005 FAIL: stddev(c/v)={stddev:.6f} < 0.2 threshold. "
        f"mean={mean_cv:.4f} min={min(cv_values):.4f} max={max(cv_values):.4f}"
    )


def test_sc005_bea_service_adds_variation_beyond_constant_share(
    runtime, pg_pool, mi_county_fips
) -> None:
    """The BEA service adds non-trivial c/v variation beyond the constant-share
    baseline.

    Without the service (share=0.5 for all counties), c/v = 0.5 * GDP / wages,
    which varies due to GDP-to-wage ratio differences. With the service, the
    II share also varies by industry mix → strictly greater stddev.

    This test proves the wiring is the cause of the additional variation, not
    a coincidental side effect.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from babylon.reference.bea import DefaultBEAShareLookupService

    # 1. Without service (constant 0.5 share)
    cv_without = _hydrate_and_measure_cv(runtime, pg_pool, mi_county_fips, None)
    stddev_without = statistics.stdev(cv_without.values())

    # 2. With service (per-county BEA share)
    bea_engine = create_engine("sqlite:///data/sqlite/marxist-data-3NF.sqlite")
    bea_session = Session(bea_engine)
    try:
        svc = DefaultBEAShareLookupService(bea_session)
        cv_with = _hydrate_and_measure_cv(runtime, pg_pool, mi_county_fips, svc)
    finally:
        bea_session.close()
        bea_engine.dispose()
    stddev_with = statistics.stdev(cv_with.values())

    assert stddev_with > stddev_without, (
        f"BEA service did not increase c/v stddev: "
        f"with={stddev_with:.6f} <= without={stddev_without:.6f}. "
        f"The wiring may not be taking effect."
    )
