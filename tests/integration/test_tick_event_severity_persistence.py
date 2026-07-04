"""Spec 092 review — Defect D: real-Postgres round-trip for tick_event severity.

Defect A found that ``tick_event.severity`` was ``VARCHAR(12)`` while the
serialization boundary's default severity string is ``"informational"``
(13 chars — see ``web/game/engine_bridge.py``'s ``_classify_event``, the
fallback bucket for ~56 of the ~70 ``EventType`` members). Against a REAL
Postgres backend this raised ``StringDataRightTruncation`` and, because
``persist_tick_events`` writes a tick's events as one batch, silently
rolled back the ENTIRE tick's ``tick_event`` rows. All 7 existing spec-092
backend tests (``tests/unit/web/test_engine_bridge.py``) mock
``RuntimePersistence`` and could never have caught this.

This test exercises the real ``PostgresRuntime`` against the W lane's
PRODUCT Postgres instance (port 5432 — NOT the runner's 5433 test
container; see worktree ``CLAUDE.md``) rather than an ephemeral
container, because the landmine lives in a table already created there
via ``CREATE TABLE IF NOT EXISTS`` under the old ``VARCHAR(12)`` DDL — a
fresh container would just pick up the widened DDL from
``postgres_schema.py`` on first ``CREATE TABLE`` and never exercise the
forward migration. Only ``migrations/0031_widen_tick_event_severity.sql``
fixes an *existing* column.

Confirmed RED against the unmigrated product DB (StringDataRightTruncation
surfacing as zero persisted rows), GREEN after applying migration 0031 —
see the spec-092 review fix report (``.superpowers/sdd/reports/092.md``).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def product_pg_pool() -> Generator[ConnectionPool[Any], None, None]:
    """Connection pool against the PRODUCT Postgres instance (port 5432).

    Defaults match ``web/babylon_web/settings/base.py``'s ``DATABASES``
    config (the same instance Django's ``manage.py runserver`` talks to).
    Override via the standard ``POSTGRES_*`` env vars if needed.
    """
    from psycopg import OperationalError
    from psycopg_pool import ConnectionPool

    dsn = (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon')} "
        f"user={os.environ.get('POSTGRES_USER', 'babylon')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'babylon')}"
    )
    try:
        pool: ConnectionPool[Any] = ConnectionPool(conninfo=dsn, min_size=1, max_size=2, open=True)
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except (OperationalError, OSError):
        pytest.skip("Product PostgreSQL (5432) not available (set POSTGRES_* env vars)")
        return

    yield pool
    pool.close()


@pytest.fixture
def runtime(product_pg_pool: ConnectionPool[Any]) -> Any:
    from babylon.persistence.postgres_runtime import PostgresRuntime

    return PostgresRuntime(product_pg_pool)


@pytest.fixture
def session_id(
    runtime: Any, product_pg_pool: ConnectionPool[Any]
) -> Generator[uuid.UUID, None, None]:
    sid: uuid.UUID = runtime.create_session(
        scenario="spec-092-defect-a-probe",
        config_json={},
        game_defines_json={},
        rng_seed=0,
    )
    yield sid
    # Cascades to tick_event via `ON DELETE CASCADE`.
    with product_pg_pool.connection() as conn:
        conn.execute("DELETE FROM game_session WHERE id = %s", (sid,))


class TestTickEventSeverityRoundTrip:
    """Defect A/D: an informational-severity event must actually persist
    and read back through the REAL Postgres ``tick_event`` table."""

    def test_informational_severity_event_round_trips(
        self, runtime: Any, session_id: uuid.UUID
    ) -> None:
        events: list[dict[str, Any]] = [
            {
                "event_type": "surplus_extraction",
                "severity": "informational",
                "source_id": "org-test-001",
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Routine surplus extraction — spec 092 Defect A probe",
                "detail": {"probe": True},
            }
        ]

        runtime.persist_tick_events(session_id, 1, events)

        rows = runtime.query_session_events(session_id, limit=10)

        assert len(rows) == 1, (
            "tick_event row missing — the informational-severity VARCHAR(12) "
            "overflow (Defect A) silently dropped the whole batch"
        )
        assert rows[0]["severity"] == "informational"
        assert rows[0]["event_type"] == "surplus_extraction"
