"""Unit tests for DuckDB -> SQLite export helpers."""

from __future__ import annotations

from babylon.data.export_sqlite import build_export_plan


def test_build_export_plan_excludes_internal_tables() -> None:
    plan = build_export_plan(
        ["dim_state", "alembic_version", "fact_qcew_annual"],
        source_schema="main",
        target_schema="sqlite_db",
    )

    plan_text = "\n".join(plan)
    assert "alembic_version" not in plan_text
    assert "sqlite_db.dim_state" in plan_text
    assert "sqlite_db.fact_qcew_annual" in plan_text
