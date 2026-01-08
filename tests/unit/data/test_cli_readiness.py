"""Unit tests for ingest readiness orchestration."""

from __future__ import annotations

from babylon.data import cli
from babylon.data.normalize import schema_check
from babylon.data.preflight import PreflightCheck, PreflightResult


def test_ingest_readiness_applies_repairs(monkeypatch) -> None:
    preflight = PreflightResult(
        checks=[PreflightCheck(check_id="module:duckdb", status="ok", message="duckdb ok")]
    )
    report = schema_check.SchemaRepairReport(
        applied=[
            schema_check.SchemaRepairAction(
                op="add_table",
                table="dim_test",
                status="applied",
            )
        ],
        remaining_diffs=[],
    )

    monkeypatch.setattr("babylon.data.preflight.run_preflight", lambda *_a, **_k: preflight)
    monkeypatch.setattr(schema_check, "get_schema_repair_report", lambda **_k: report)

    result = cli._run_ingest_readiness(
        config=cli.LoaderConfig(),
        selected=["census"],
        online=False,
        strict=False,
        repair=True,
    )

    assert result.ok
    assert result.schema_report is report


def test_ingest_readiness_strict_warn_fails(monkeypatch) -> None:
    preflight = PreflightResult(
        checks=[PreflightCheck(check_id="env:FRED_API_KEY", status="warn", message="missing")]
    )
    report = schema_check.SchemaRepairReport(remaining_diffs=[])

    monkeypatch.setattr("babylon.data.preflight.run_preflight", lambda *_a, **_k: preflight)
    monkeypatch.setattr(schema_check, "get_schema_repair_report", lambda **_k: report)

    result = cli._run_ingest_readiness(
        config=cli.LoaderConfig(),
        selected=["census"],
        online=False,
        strict=True,
        repair=True,
    )

    assert not result.ok
