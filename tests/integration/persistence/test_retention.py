"""Retention enforcement tests (ADR176 ruling 32 — 1 live session, in code).

The law: at most ONE session holds live runtime rows; every other session
is exported (fail-closed verified) and purged, its archive landing under
``archive_root/<session_id>/``. Enforcement never destroys what it cannot
verify — an ``ArchiveVerificationError`` bubbles and nothing is deleted.
Purged campaigns remain rebuildable from their catalog replay identity
(``rng_seed``, ruling 28).

Same pg_pool gating as the sibling suites: integration-marked, skips
cleanly when Postgres is unavailable.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest

from babylon.persistence import archival
from babylon.persistence.archival import ArchiveVerificationError
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.retention import enforce_single_live_session
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.integration]


@pytest.fixture
def migrated(pg_pool: Any) -> None:
    from babylon.persistence.postgres_schema import ensure_ddl_applied

    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    sql_files = sorted(migrations_dir.glob("00*.sql"))
    assert sql_files
    with pg_pool.connection() as conn:
        conn.autocommit = True
        ensure_ddl_applied(conn, [f.read_text() for f in sql_files])


@pytest.fixture
def runtime(pg_pool: Any, migrated: None) -> PostgresRuntime:
    return PostgresRuntime(pg_pool)


def _boot_session(runtime: PostgresRuntime, marker: str) -> uuid.UUID:
    """Mint a session with live adjudicating rows (topology + marker)."""
    session_id = runtime.create_session(
        scenario="ruling32-retention",
        config_json={},
        game_defines_json={},
        rng_seed=7,
    )
    graph = BabylonGraph()
    graph.add_node("payload_node", type="Test", marker=marker)
    runtime.persist_tick_atomic(
        PerTickTransactionEnvelope(session_id=session_id, tick=1, determinism_hash="0" * 64),
        graph=graph,
    )
    return session_id


def _live(runtime: PostgresRuntime, session_id: uuid.UUID) -> bool:
    with runtime._pool.connection() as conn:  # noqa: SLF001 - forensic read
        row = conn.execute(
            "SELECT (SELECT count(*) FROM tick_commit WHERE session_id = %s)"
            " + (SELECT count(*) FROM node_state WHERE session_id = %s)",
            (str(session_id), str(session_id)),
        ).fetchone()
    return row is not None and int(row[0]) > 0


class TestEnforceSingleLiveSession:
    def test_other_sessions_are_exported_then_purged(
        self, runtime: PostgresRuntime, pg_pool: Any, tmp_path: Path
    ) -> None:
        keep = _boot_session(runtime, "keep")
        other = _boot_session(runtime, "other")
        try:
            purged = enforce_single_live_session(pg_pool, keep=keep, archive_root=tmp_path)
            assert other in purged
            assert keep not in purged
            assert (tmp_path / str(other) / "archive_manifest.json").exists()
            assert (tmp_path / str(other) / "node_state.parquet").exists()
            assert not _live(runtime, other)
            assert _live(runtime, keep)
        finally:
            enforce_single_live_session(pg_pool, keep=uuid.uuid4(), archive_root=tmp_path)

    def test_single_live_session_is_a_no_op(
        self, runtime: PostgresRuntime, pg_pool: Any, tmp_path: Path
    ) -> None:
        keep = _boot_session(runtime, "solo")
        try:
            assert enforce_single_live_session(pg_pool, keep=keep, archive_root=tmp_path) == ()
            assert _live(runtime, keep)
        finally:
            enforce_single_live_session(pg_pool, keep=uuid.uuid4(), archive_root=tmp_path)

    def test_verification_failure_deletes_nothing(
        self,
        runtime: PostgresRuntime,
        pg_pool: Any,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fail-closed: a session whose archive cannot be verified survives,
        and the enforcement raises rather than quietly continuing."""
        keep = _boot_session(runtime, "keep")
        other = _boot_session(runtime, "other")

        def _refuse(conn: Any, session_id: uuid.UUID, manifest: dict[str, Any]) -> None:
            raise ArchiveVerificationError("synthetic verification failure")

        monkeypatch.setattr(archival, "_verify_manifest_against_live", _refuse)
        try:
            with pytest.raises(ArchiveVerificationError):
                enforce_single_live_session(pg_pool, keep=keep, archive_root=tmp_path)
            assert _live(runtime, other), "verification failed but rows were destroyed"
        finally:
            monkeypatch.undo()
            enforce_single_live_session(pg_pool, keep=uuid.uuid4(), archive_root=tmp_path)
