"""T014: Audit-report round-trip + on-disk serialization tests (spec-068)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from babylon.reference.bea.ingest.audit_report import (
    AccountingViolation,
    BEAIngestAuditReport,
    ColumnSumViolation,
    IndustrySnapshot,
    StaleShareFallbackSummary,
    VintageSupersession,
)


@pytest.mark.unit
class TestAuditReportRoundTrip:
    """JSON round-trip equality (FR-008)."""

    def test_minimal_report_round_trips(self) -> None:
        original = BEAIngestAuditReport(
            timestamp=datetime(2026, 5, 17, 14, 30, 0, tzinfo=UTC),
            sim_years_in_scope=(2010, 2011, 2012),
        )
        restored = BEAIngestAuditReport.from_json(original.to_json())
        assert restored == original

    def test_full_report_round_trips(self) -> None:
        from decimal import Decimal

        original = BEAIngestAuditReport(
            timestamp=datetime(2026, 5, 17, 15, 0, 0, tzinfo=UTC),
            duration_seconds=42.5,
            sim_years_in_scope=(2010, 2024),
            rows_inserted={"fact_bea_national_industry": 840},
            rows_superseded={"fact_bea_national_industry": 5},
            accounting_identity_violations=[
                AccountingViolation(
                    bea_industry_id=1,
                    year=2010,
                    gross_output=Decimal("1000.00"),
                    intermediate_inputs=Decimal("500.00"),
                    value_added=Decimal("490.00"),
                    residual_fraction=0.01,
                ),
            ],
            column_sum_identity_violations=[
                ColumnSumViolation(
                    target_industry_id=5,
                    year=2012,
                    column_sum=0.501,
                    expected_share=0.500,
                    residual_fraction=0.002,
                ),
            ],
            intermediate_inputs_share_top10=[
                IndustrySnapshot(
                    bea_industry_id=33,
                    bea_industry_name="Manufacturing",
                    year=2015,
                    intermediate_inputs_share=0.78,
                ),
            ],
            vintage_supersessions=[
                VintageSupersession(
                    table_name="fact_bea_national_industry",
                    bea_industry_id=2,
                    year=2019,
                    old_vintage=date(2021, 6, 1),
                    new_vintage=date(2023, 6, 1),
                ),
            ],
            stale_share_fallback_summary=StaleShareFallbackSummary(
                total_county_year_lookups=10_000,
                forward_filled_lookups=50,
                global_default_lookups=3,
                affected_employment_fraction=0.005,
            ),
            sc_001_pass=True,
            sc_007_wallclock_seconds=120.0,
            sc_007_pass=True,
        )
        restored = BEAIngestAuditReport.from_json(original.to_json())
        assert restored == original


@pytest.mark.unit
class TestAuditReportFilenames:
    """File naming follows the spec-067 `<workload>_<timestamp>` convention."""

    def test_live_run_filename_pattern(self, tmp_path: Path) -> None:
        report = BEAIngestAuditReport(
            timestamp=datetime(2026, 5, 17, 14, 30, 0, tzinfo=UTC),
            sim_years_in_scope=(2010,),
            dry_run=False,
        )
        json_path, md_path = report.write_to_disk(tmp_path)
        assert json_path.name == "bea_io_20260517T143000Z.json"
        assert md_path.name == "bea_io_20260517T143000Z.md"
        assert json_path.exists() and md_path.exists()

    def test_dry_run_filename_pattern(self, tmp_path: Path) -> None:
        report = BEAIngestAuditReport(
            timestamp=datetime(2026, 5, 17, 14, 30, 0, tzinfo=UTC),
            sim_years_in_scope=(2010,),
            dry_run=True,
        )
        json_path, md_path = report.write_to_disk(tmp_path)
        assert json_path.name == "bea_io_dryrun_20260517T143000Z.json"
        assert md_path.name == "bea_io_dryrun_20260517T143000Z.md"

    def test_markdown_contains_validation_gate_section(self, tmp_path: Path) -> None:
        report = BEAIngestAuditReport(
            timestamp=datetime(2026, 5, 17, 14, 30, 0, tzinfo=UTC),
            sim_years_in_scope=(2010,),
            sc_001_pass=True,
            sc_003_pass=False,
        )
        _, md_path = report.write_to_disk(tmp_path)
        body = md_path.read_text()
        assert "## Validation Gates" in body
        assert "SC-001" in body and "**PASS**" in body
        assert "SC-003" in body and "**FAIL**" in body
