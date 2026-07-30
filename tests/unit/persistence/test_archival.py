"""Unit tests for the local archival lifecycle surface (spec-088 S2b).

Replaces the spec-037 Phase-8 stub-assertion tests: the pipeline is now
implemented local-only (Parquet + DuckDB; no cloud code paths). Pure /
no-database behaviors only — the Postgres roundtrip lives in
``tests/integration/test_archival_integration.py``.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from babylon.persistence.archival import (
    EXPORT_TABLES,
    ArchiveVerificationError,
    _verify_manifest_against_live,
    purge_session,
    query_archived_session,
    upload_to_r2,
)
from babylon.persistence.partitioning import PARTITIONED_TABLES


class TestExportRegistry:
    def test_export_covers_every_partitioned_family(self) -> None:
        """A table family that partitions must also archive."""
        assert set(PARTITIONED_TABLES) <= set(EXPORT_TABLES)

    def test_export_includes_session_keyed_extras(self) -> None:
        assert "contradiction_field" in EXPORT_TABLES
        assert "simulation_event" in EXPORT_TABLES


class TestPurgeSafety:
    def test_purge_refuses_without_manifest(self, tmp_path: Path) -> None:
        """No verified manifest ⇒ nothing is deleted (FR-011)."""
        with pytest.raises(ArchiveVerificationError, match="manifest not found"):
            purge_session(
                pool=None,  # never reached: manifest check precedes any DB touch
                session_id=uuid4(),
                manifest_path=tmp_path / "missing_manifest.json",
            )


class _MissingTableConn:
    """Fake conn whose every ``to_regclass`` probe reports the table GONE.

    The count query must never run for a missing table — reaching it would
    mean the gate probed a table it already knows does not exist.
    """

    def execute(self, sql: str, params: object = None) -> _MissingTableConn:
        assert "to_regclass" in sql, "count query must never run for a missing table"
        return self

    def fetchone(self) -> tuple[None]:
        return (None,)


class TestVerifyManifestFailClosed:
    def test_missing_live_table_is_an_error_not_a_skip(self) -> None:
        """A manifest table absent from the live database FAILS the purge
        gate (ADR176 ruling 28, P-J defect 2/3; postgres brief item 15).

        The gate's entire job is proving the archive complete before
        destroying the original. A table that existed at export time and is
        gone at purge time is schema drift between export and purge — the
        old ``continue`` passed the gate on exactly the rows it could no
        longer verify."""
        session_id = uuid4()
        manifest = {
            "session_id": str(session_id),
            "tables": {"node_state": {"rows": 42}},
        }
        with pytest.raises(ArchiveVerificationError, match="node_state"):
            _verify_manifest_against_live(_MissingTableConn(), session_id, manifest)


class TestQueryArchivedSession:
    def test_missing_archive_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            query_archived_session(tmp_path / "nope", "SELECT 1")

    def test_empty_archive_dir_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            query_archived_session(tmp_path, "SELECT 1")


class TestUploadToR2Retired:
    def test_raises_local_only_ruling(self) -> None:
        """Owner ruling 2026-07-03: archives are local only, period."""
        with pytest.raises(NotImplementedError, match="local-only"):
            upload_to_r2(["/tmp/data.parquet"], bucket="babylon-exports")
