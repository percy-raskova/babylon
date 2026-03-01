"""Unit tests for archival pipeline stubs (Feature 037).

Phase 8 (T043): Verify stub functions raise NotImplementedError
with appropriate context messages.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from babylon.persistence.archival import (
    export_session_to_parquet,
    purge_session,
    query_archived_session,
    upload_to_r2,
)


class TestExportSessionToParquet:
    """Tests for export_session_to_parquet stub."""

    def test_raises_not_implemented(self) -> None:
        """export_session_to_parquet raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Phase 8"):
            export_session_to_parquet(
                pool=None,
                session_id=uuid4(),
                output_dir="/tmp/exports",
            )

    def test_error_includes_session_id(self) -> None:
        """NotImplementedError message includes session_id."""
        sid = uuid4()
        with pytest.raises(NotImplementedError, match=str(sid)):
            export_session_to_parquet(pool=None, session_id=sid, output_dir="/tmp")


class TestUploadToR2:
    """Tests for upload_to_r2 stub."""

    def test_raises_not_implemented(self) -> None:
        """upload_to_r2 raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Phase 8"):
            upload_to_r2(parquet_paths=["/tmp/a.parquet"], bucket="test-bucket")

    def test_error_includes_bucket(self) -> None:
        """NotImplementedError message includes bucket name."""
        with pytest.raises(NotImplementedError, match="my-bucket"):
            upload_to_r2(parquet_paths=[], bucket="my-bucket", prefix="sessions/")


class TestPurgeSession:
    """Tests for purge_session stub."""

    def test_raises_not_implemented(self) -> None:
        """purge_session raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Phase 8"):
            purge_session(pool=None, session_id=uuid4())


class TestQueryArchivedSession:
    """Tests for query_archived_session stub."""

    def test_raises_not_implemented_with_string_path(self) -> None:
        """query_archived_session raises NotImplementedError with str path."""
        with pytest.raises(NotImplementedError, match="Phase 8"):
            query_archived_session(
                parquet_path="/data/session.parquet",
                query="SELECT * FROM node_state",
            )

    def test_raises_not_implemented_with_path_object(self) -> None:
        """query_archived_session raises NotImplementedError with Path object."""
        with pytest.raises(NotImplementedError, match="Phase 8"):
            query_archived_session(
                parquet_path=Path("/data/session.parquet"),
                query="SELECT * FROM node_state",
            )
