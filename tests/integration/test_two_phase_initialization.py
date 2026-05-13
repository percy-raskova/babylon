"""Two-phase initialization integration tests (T024 / US1 / SC-001).

Skips cleanly when Postgres is unavailable. Uses a real SQLite reference
file from the canonical location ``data/sqlite/marxist-data-3NF.sqlite``;
if that file is missing the tests skip (they are not blocking unit-test
gates — they validate the persistence contract).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

# Skip cleanly if psycopg / runtime stack is missing.
pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite").resolve()


@pytest.fixture
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    """Apply the spec-062 schema to the test database (idempotent)."""
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


@pytest.fixture
def sqlite_path() -> Path:
    if not SQLITE_PATH.is_file():
        pytest.skip(f"SQLite reference DB not found at {SQLITE_PATH}")
    return SQLITE_PATH


def test_initialize_session_completes_and_returns_report(  # type: ignore[no-untyped-def]
    runtime, sqlite_path
):
    """User Story 1 acceptance scenario 1.

    Initializing a session opens the SQLite reference, hydrates Postgres,
    and returns a populated :class:`InitializationReport`.
    """
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    defines = GameDefines()
    session_id = uuid4()

    report = initialize_session(
        session_id=session_id,
        sqlite_path=sqlite_path,
        runtime=runtime,
        defines=defines,
        start_year=2010,
        scenario_length_years=15,
    )

    assert report.session_id == session_id
    # The fixed external-node set is locked at nine values per FR-036.
    assert "canada" in report.external_node_ids
    assert "rest_of_usa" in report.external_node_ids
    assert len(report.external_node_ids) == 9
    # At least the core BEA + MELT + Hickel series should be in copied set.
    assert "bea_io_imports" in report.copied_series
    assert "hickel_drain" in report.copied_series


def test_alpha_weekly_startup_invariant_enforced(  # type: ignore[no-untyped-def]
    runtime, sqlite_path
):
    """FR-029a: initialization fails if alpha_weekly >= 1/52."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import (
        InitializationError,
        initialize_session,
    )

    # Build a GameDefines with alpha_annual large enough to violate the
    # invariant: alpha_annual such that 1 - (1-x)^(1/52) >= 1/52, i.e.,
    # x >= 1 - (1 - 1/52)^52 ≈ 0.636.
    defines = GameDefines.model_validate(
        {
            **GameDefines().model_dump(),
            "economy": {
                **GameDefines().economy.model_dump(),
                "alpha_annual": 0.7,
            },
        }
    )
    with pytest.raises(InitializationError, match="FR-029a"):
        initialize_session(
            session_id=uuid4(),
            sqlite_path=sqlite_path,
            runtime=runtime,
            defines=defines,
            start_year=2010,
            scenario_length_years=15,
        )
