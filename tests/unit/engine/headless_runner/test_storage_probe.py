"""Unit tests for the manifest ``storage`` block builder (spec-087 FR-009/FR-010).

The builder is pure (decoupled from Postgres, same pattern as
``run_summary.build_summary``): callers feed pre-shaped per-table stats and
get the manifest-ready dict back. The pool-backed collector
(``query_storage_footprint``) is exercised by the e2e gate, not unit tests.
"""

from __future__ import annotations

from babylon.engine.headless_runner.storage_probe import (
    PER_TICK_TABLES,
    build_storage_block,
)


class TestPerTickTableRegistry:
    """The probed table set covers the spec-062 per-tick write families."""

    def test_dominant_tables_registered(self) -> None:
        assert "dynamic_hex_state" in PER_TICK_TABLES
        assert "boundary_flow_register" in PER_TICK_TABLES
        assert "conservation_audit_log" in PER_TICK_TABLES


class TestBuildStorageBlock:
    """Shape + math of the manifest ``storage`` block."""

    def test_rows_per_tick_math(self) -> None:
        block = build_storage_block(
            db_total_bytes=13_000_000,
            ticks_persisted=5,
            tables=[
                {
                    "table": "dynamic_hex_state",
                    "total_bytes": 1_500_000,
                    "session_rows": 5225,
                }
            ],
        )
        assert block["db_total_bytes"] == 13_000_000
        assert block["ticks_persisted"] == 5
        entry = block["tables"][0]
        assert entry["table"] == "dynamic_hex_state"
        assert entry["total_bytes"] == 1_500_000
        assert entry["session_rows"] == 5225
        assert entry["session_rows_per_tick"] == 1045.0

    def test_tables_sorted_by_total_bytes_desc(self) -> None:
        block = build_storage_block(
            db_total_bytes=1,
            ticks_persisted=1,
            tables=[
                {"table": "small", "total_bytes": 10, "session_rows": 1},
                {"table": "big", "total_bytes": 999, "session_rows": 1},
                {"table": "mid", "total_bytes": 100, "session_rows": 1},
            ],
        )
        assert [t["table"] for t in block["tables"]] == ["big", "mid", "small"]

    def test_zero_ticks_does_not_divide_by_zero(self) -> None:
        """An errored run with 0 persisted ticks must still build a block."""
        block = build_storage_block(
            db_total_bytes=0,
            ticks_persisted=0,
            tables=[{"table": "dynamic_hex_state", "total_bytes": 0, "session_rows": 7}],
        )
        assert block["ticks_persisted"] == 0
        assert block["tables"][0]["session_rows_per_tick"] == 7.0

    def test_empty_tables_list_is_valid(self) -> None:
        block = build_storage_block(db_total_bytes=42, ticks_persisted=5, tables=[])
        assert block["tables"] == []
        assert block["db_total_bytes"] == 42
