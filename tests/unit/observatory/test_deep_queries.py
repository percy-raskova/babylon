"""Unit tests for the reader-based deep queries (spec-099 fixes, no DB).

Covers two review findings fixed without touching a real database:

* ``created_at_utc`` must round-trip through :func:`read_commit_chain` as a
  real, non-null, UTC-normalized ISO-8601 string for BOTH backends — even
  though Postgres and DuckDB render a ``CAST(timestamptz AS VARCHAR)`` with
  different offset notations (finding #1).
* ``read_boundary`` / ``read_conservation`` must surface a ``truncated`` flag
  when more rows exist than the row cap (finding #2).
"""

from __future__ import annotations

from typing import Any

import pytest

from observatory.deep_queries import (
    _MAX_AUDIT_ROWS,
    _MAX_BOUNDARY_ROWS,
    read_boundary,
    read_commit_chain,
    read_conservation,
)

pytestmark = pytest.mark.unit


class _FakeReader:
    """Minimal stand-in for ``LiveReader``/``ArchiveReader``.

    ``rows_by_marker`` maps a distinguishing substring of the SQL text to the
    rows ``execute`` should return when that substring appears — enough to
    fake the handful of raw-table queries ``deep_queries`` issues without
    parsing SQL for real.
    """

    def __init__(self, rows_by_marker: dict[str, list[dict[str, Any]]]) -> None:
        self._rows_by_marker = rows_by_marker

    def table_available(self, table: str) -> bool:  # noqa: ARG002
        return True

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        for marker, rows in self._rows_by_marker.items():
            if marker in sql:
                # Only the row-fetch queries (not tick_commit / the GROUP BY
                # summary) carry a trailing ``LIMIT ?`` — fake the DB-side cap.
                if "LIMIT ?" in sql and params:
                    return rows[: params[-1]]
                return rows
        raise AssertionError(f"no fake rows registered for SQL: {sql}")


class TestCommitChainCreatedAtUtc:
    def test_created_at_utc_is_non_null_and_iso(self) -> None:
        reader = _FakeReader(
            {
                "FROM tick_commit": [
                    {
                        "tick": 0,
                        "determinism_hash": "a" * 64,
                        "hex_rows_written": 2,
                        "is_checkpoint": True,
                        # Postgres-style CAST(timestamptz AS text): space
                        # separator, no colon in the offset.
                        "created_at_utc": "2026-07-03 21:48:51.947028-04",
                    }
                ]
            }
        )
        chain = read_commit_chain(reader, "sid", 0, 0)
        assert len(chain) == 1
        assert chain[0]["created_at_utc"] is not None
        assert chain[0]["created_at_utc"] == "2026-07-04T01:48:51.947028+00:00"

    def test_live_and_archive_style_timestamps_normalize_identically(self) -> None:
        # Same absolute instant, rendered by two different backends' CAST
        # (Postgres session TimeZone vs DuckDB's UTC-default rendering).
        postgres_style = "2026-07-03 21:48:51.947028-04"
        duckdb_style = "2026-07-04 01:48:51.947028+00"
        live_reader = _FakeReader(
            {
                "FROM tick_commit": [
                    {
                        "tick": 0,
                        "determinism_hash": "a" * 64,
                        "hex_rows_written": 2,
                        "is_checkpoint": True,
                        "created_at_utc": postgres_style,
                    }
                ]
            }
        )
        archive_reader = _FakeReader(
            {
                "FROM tick_commit": [
                    {
                        "tick": 0,
                        "determinism_hash": "a" * 64,
                        "hex_rows_written": 2,
                        "is_checkpoint": True,
                        "created_at_utc": duckdb_style,
                    }
                ]
            }
        )
        live_chain = read_commit_chain(live_reader, "sid", 0, 0)
        archive_chain = read_commit_chain(archive_reader, "sid", 0, 0)
        assert live_chain[0]["created_at_utc"] == archive_chain[0]["created_at_utc"]

    def test_null_created_at_utc_stays_null(self) -> None:
        reader = _FakeReader(
            {
                "FROM tick_commit": [
                    {
                        "tick": 0,
                        "determinism_hash": "a" * 64,
                        "hex_rows_written": 2,
                        "is_checkpoint": True,
                        "created_at_utc": None,
                    }
                ]
            }
        )
        chain = read_commit_chain(reader, "sid", 0, 0)
        assert chain[0]["created_at_utc"] is None


def _boundary_row(i: int) -> dict[str, Any]:
    return {
        "tick": i,
        "source_node_id": "n",
        "source_kind": "hex",
        "dest_node_id": "m",
        "dest_kind": "hex",
        "flow_type": "drain",
        "magnitude": 1.0,
    }


def _conservation_row(i: int) -> dict[str, Any]:
    return {
        "tick": i,
        "scale": "county",
        "invariant_name": "value",
        "computed_value": 1.0,
        "expected_value": 1.0,
        "residual": 0.0,
        "severity": "ok",
    }


class TestBoundaryTruncation:
    def test_truncated_flagged_over_cap(self) -> None:
        rows = [_boundary_row(i) for i in range(_MAX_BOUNDARY_ROWS + 500)]
        reader = _FakeReader(
            {
                "GROUP BY flow_type": [
                    {"flow_type": "drain", "row_count": len(rows), "total_magnitude": 1.0}
                ],
                "FROM boundary_flow_register": rows,
            }
        )
        result = read_boundary(reader, "sid", 0, 100)
        assert result["truncated"] is True
        assert len(result["rows"]) == _MAX_BOUNDARY_ROWS

    def test_not_truncated_under_cap(self) -> None:
        rows = [_boundary_row(i) for i in range(3)]
        reader = _FakeReader(
            {
                "GROUP BY flow_type": [
                    {"flow_type": "drain", "row_count": len(rows), "total_magnitude": 1.0}
                ],
                "FROM boundary_flow_register": rows,
            }
        )
        result = read_boundary(reader, "sid", 0, 100)
        assert result["truncated"] is False
        assert len(result["rows"]) == 3


class TestConservationTruncation:
    def test_truncated_flagged_over_cap(self) -> None:
        rows = [_conservation_row(i) for i in range(_MAX_AUDIT_ROWS + 500)]
        reader = _FakeReader({"FROM conservation_audit_log": rows})
        result = read_conservation(reader, "sid", 0, 100, non_ok_only=False)
        assert result["truncated"] is True
        assert len(result["rows"]) == _MAX_AUDIT_ROWS

    def test_not_truncated_under_cap(self) -> None:
        rows = [_conservation_row(i) for i in range(3)]
        reader = _FakeReader({"FROM conservation_audit_log": rows})
        result = read_conservation(reader, "sid", 0, 100, non_ok_only=False)
        assert result["truncated"] is False
        assert len(result["rows"]) == 3
