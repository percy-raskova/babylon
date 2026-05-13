"""FR-002 enforcement test: SQLite handle closed after initialization (T025).

After :func:`initialize_session` returns, opening the SQLite file with an
exclusive ``flock`` MUST succeed — proving no Babylon code is still holding
a read lock on it.

Skips cleanly when Postgres is unavailable, when the SQLite file is missing,
or on platforms where ``flock`` is not available (e.g., Windows).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")

if sys.platform == "win32":
    pytest.skip("flock-based lock test not portable to Windows", allow_module_level=True)

try:
    import fcntl
except ImportError:  # pragma: no cover
    pytest.skip("fcntl not available on this platform", allow_module_level=True)


SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite").resolve()


@pytest.fixture
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
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


def test_sqlite_lockable_after_initialize_session(runtime, sqlite_path):  # type: ignore[no-untyped-def]
    """After initialize_session returns, SQLite file can be flock'd exclusively."""
    from babylon.config.defines import GameDefines
    from babylon.persistence.postgres_initialization import initialize_session

    defines = GameDefines()
    initialize_session(
        session_id=uuid4(),
        sqlite_path=sqlite_path,
        runtime=runtime,
        defines=defines,
        start_year=2010,
        scenario_length_years=15,
        # Scope to Detroit tri-county so QCEW hydration stays fast for CI.
        counties=["26163", "26125", "26099"],
    )

    fd = os.open(str(sqlite_path), os.O_RDWR)
    try:
        # If init left a read lock behind, LOCK_EX | LOCK_NB raises BlockingIOError.
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
