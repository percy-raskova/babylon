"""Unit tests for `tools/inspect_qcew_audit.py` operator helper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.inspect_qcew_audit import main


def _synthetic_audit_report() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "run_metadata": {
            "timestamp_utc": "2026-05-17T00:00:00+00:00",
            "migration_version": "spec-067-v1.0",
            "database_path": "/tmp/test.sqlite",
            "database_sha256_pre": "a" * 64,
            "database_sha256_post": "b" * 64,
            "migration_duration_seconds": 4567.8,
            "git_branch": "067-qcew-ownership-normalization",
            "git_sha": "abc1234",
        },
        "row_counts": {
            "fact_qcew_annual_pre": 43_305_794,
            "fact_qcew_annual_post": 15_097_464,
            "rows_excluded": {
                "naics_only": 28_159_281,
                "ownership_only": 0,
                "both_axes": 49_049,
                "total": 28_208_330,
            },
            "integrity_check_passed": True,
        },
        "naics_vintages": {
            "2010": "2007",
            "2011": "2007",
            "2012": "2012",
            "2017": "2017",
            "2022": "2022",
        },
        "bls_suppressed_county_years": [
            {"county_fips": "26083", "year": 2018, "reason": "low-establishment-count"},
        ],
        "per_county_deltas": {
            "michigan_scope_only": True,
            "summary_stats": {
                "counties_within_5pct_band": 0,
                "counties_within_5pct_band_pct": 0.0,
                "counties_with_delta_gt_10pct": 1236,
                "max_abs_delta_pct": 94.04,
            },
            "outliers": [
                {
                    "county_fips": "26163",
                    "year": 2010,
                    "pre_sum": 657_150.0,
                    "post_sum": 561_173.0,
                    "delta_pct": -14.61,
                    "reason": "rollup-vs-leaves discrepancy (manual review required)",
                },
            ],
        },
    }


def test_inspect_audit_returns_zero_on_explicit_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Helper exits 0 + prints all major sections when given a valid audit JSON."""

    audit_path = tmp_path / "qcew_normalization_20260517-000000.json"
    audit_path.write_text(json.dumps(_synthetic_audit_report()), encoding="utf-8")

    rc = main(["--path", str(audit_path), "--outliers", "3"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "QCEW Normalization Audit" in out
    assert "Row counts" in out
    assert "43,305,794" in out
    assert "15,097,464" in out
    assert "NAICS vintages" in out
    assert "Per-county delta distribution" in out
    assert "Michigan-only" in out
    assert "Top 1 outliers" in out
    assert "26163" in out
    assert "BLS-suppressed county-years" in out


def test_inspect_audit_returns_one_when_no_report_found(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Helper exits 1 + prints a clear stderr error when explicit path missing."""

    rc = main(["--path", str(tmp_path / "missing.json")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "audit report not found" in err
