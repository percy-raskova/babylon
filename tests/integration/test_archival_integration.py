"""Integration tests for Parquet archival pipeline (Feature 037/044).

This module is a placeholder for Phase 8 testing. Currently verifies
the stub implementations raise NotImplementedError as expected.
Requires BABYLON_TEST_PG_DSN to be set.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from babylon.persistence.archival import (
    export_session_to_parquet,
    purge_session,
    query_archived_session,
    upload_to_r2,
)

pytestmark = pytest.mark.integration


def test_t044_export_session_not_implemented(pg_pool: object) -> None:
    """T044: Verify Parquet export stub raises NotImplementedError."""
    session_id = uuid.uuid4()
    with pytest.raises(NotImplementedError, match="Phase 8, T045"):
        export_session_to_parquet(
            pool=pg_pool,
            session_id=session_id,
            output_dir="/tmp/exports",
        )


def test_t047_purge_session_not_implemented(pg_pool: object) -> None:
    """T047: Verify purge_session stub raises NotImplementedError."""
    session_id = uuid.uuid4()
    with pytest.raises(NotImplementedError, match="Phase 8, T047"):
        purge_session(
            pool=pg_pool,
            session_id=session_id,
        )


def test_t046_upload_to_r2_not_implemented() -> None:
    """T046: Verify upload_to_r2 stub raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Phase 8, T046"):
        upload_to_r2(
            parquet_paths=["/tmp/data.parquet"],
            bucket="babylon-exports",
        )


def test_t048_query_archived_session_not_implemented() -> None:
    """T048: Verify query_archived_session stub raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Phase 8, T048"):
        query_archived_session(
            parquet_path=Path("/tmp/data.parquet"),
            query="SELECT * FROM node_state",
        )
