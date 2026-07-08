"""Integration test: FR-026 canada-required fail-fast invariant (Spec 063 T033).

Quickstart §5 / FR-026 / SC-006: when a caller both removes canada from the
external-node registry (``external_node_overrides``) AND requests synthetic
Canadian LODES rows (``synthetic_lodes_canadian_rows=True``),
``initialize_session`` raises :class:`InitializationError` BEFORE any
reference hydration — fast enough to meet the SC-006 ``< 5s`` fail-fast
budget. The positive control: canada present (default registry) + synthetic
rows completes and the synthetic canada OD row is persisted.

This exercises the ``external_node_overrides`` / ``synthetic_lodes_canadian_rows``
seams added in remediation lane 6.2. Before this branch the raising branch
was unreachable — ``INTERNATIONAL_NODES`` always contained canada and no
registry override existed (see the now-superseded note in
``test_paired_cross_border_emission.py::test_fr_026_canada_registry_always_present``).

Unlike the other spec-063 integration suites this file needs NO LODES/TIGER
data — the fail-fast path is data-free (it raises before any SQLite read),
and the positive path injects the synthetic canada row directly. Requires
only the live Postgres test pool (BABYLON_TEST_PG_DSN) + the SQLite reference
DB. Rows are scoped by ``session_id`` (the babylon_test DB is shared).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import UUID, uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cross_scale,
    pytest.mark.skipif(
        not os.environ.get("BABYLON_TEST_PG_DSN"),
        reason="BABYLON_TEST_PG_DSN env var not set; integration suite skipped",
    ),
    pytest.mark.skipif(
        not Path("data/sqlite/marxist-data-3NF.sqlite").exists(),
        reason="SQLite reference DB not present at data/sqlite/",
    ),
]

_SQLITE = Path("data/sqlite/marxist-data-3NF.sqlite")
_YEAR = 2010
_DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]


@pytest.fixture(scope="module")
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    dsn = os.environ["BABYLON_TEST_PG_DSN"]
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def runtime(pg_pool):  # type: ignore[no-untyped-def]
    """Construct the runtime, skipping if babylon_test is not yet migrated.

    The wave harness provisions + migrates the shared babylon_test DB, so this
    suite verifies the tables it touches rather than re-applying all 23
    migrations (an idempotent ~14s no-op on an already-migrated DB).
    """
    from babylon.persistence import PostgresRuntime

    required = ("immutable_reference_lodes_od_matrix", "dynamic_external_node_state")
    with pg_pool.connection() as conn:
        for table in required:
            got = conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
            if got is None or got[0] is None:
                pytest.skip(f"required table {table} absent; babylon_test not migrated")
    return PostgresRuntime(pool=pg_pool)


def test_canada_missing_with_synthetic_rows_fails_fast(runtime) -> None:  # type: ignore[no-untyped-def]
    """FR-026 / SC-006: canada absent from registry + synthetic rows raises < 5s."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import (
        InitializationError,
        initialize_session,
    )

    start = time.perf_counter()
    with pytest.raises(InitializationError, match=r"canada.*not present"):
        initialize_session(
            session_id=uuid4(),
            sqlite_path=_SQLITE,
            runtime=runtime,
            defines=GameDefines(),
            start_year=_YEAR,
            scenario_length_years=1,
            counties=_DETROIT_TRI_COUNTY,
            external_node_overrides=frozenset(["china", "eu"]),
            synthetic_lodes_canadian_rows=True,
        )
    elapsed = time.perf_counter() - start
    # SC-006 fail-fast wall-time budget — the check runs before any SQLite /
    # Postgres work, so this is comfortably sub-second in practice.
    assert elapsed < 5.0, f"FR-026 fail-fast took {elapsed:.3f}s (SC-006 budget: < 5s)"


def test_canada_present_with_synthetic_rows_completes_and_persists_row(runtime) -> None:  # type: ignore[no-untyped-def]
    """Positive control: default registry (canada present) + synthetic rows succeeds."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=GameDefines(),
        start_year=_YEAR,
        scenario_length_years=1,
        counties=_DETROIT_TRI_COUNTY,
        synthetic_lodes_canadian_rows=True,  # default registry keeps canada
    )
    assert "canada" in report.external_node_ids

    with runtime._pool.connection() as pg, pg.cursor() as cur:  # noqa: SLF001
        cur.execute(
            "SELECT COUNT(*) FROM immutable_reference_lodes_od_matrix "
            "WHERE session_id = %s AND workplace_dest = 'canada'",
            (sid,),
        )
        row = cur.fetchone()
    assert row is not None and row[0] == 1, "synthetic canada OD row not persisted"


def test_canada_override_including_canada_permits_synthetic_rows(runtime) -> None:  # type: ignore[no-untyped-def]
    """An explicit override that INCLUDES canada passes the FR-026 guard."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    sid: UUID = uuid4()
    report = initialize_session(
        session_id=sid,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=GameDefines(),
        start_year=_YEAR,
        scenario_length_years=1,
        counties=_DETROIT_TRI_COUNTY,
        external_node_overrides=frozenset(["canada", "china", "eu"]),
        synthetic_lodes_canadian_rows=True,
    )
    # Only the overridden international set (+ rest_of_usa) is declared.
    assert report.external_node_ids == {"canada", "china", "eu", "rest_of_usa"}
    assert report.external_node_count == 4
