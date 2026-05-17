"""Audit-report types for the spec-068 BEA I-O ingest.

Matches the spec-067 audit-report convention: JSON + Markdown both
written to ``reports/ingest/bea_io_<timestamp>.{json,md}``. JSON is
machine-readable; Markdown is the operator-facing surface.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_REPORT_DIR_DEFAULT = Path("reports/ingest")


class AccountingViolation(BaseModel):
    """A row that failed FR-002 accounting identity (II + VA = GO ± 1 %)."""

    model_config = ConfigDict(frozen=True)

    bea_industry_id: int
    year: int
    gross_output: Decimal | None
    intermediate_inputs: Decimal | None
    value_added: Decimal | None
    residual_fraction: float


class ColumnSumViolation(BaseModel):
    """A (target_industry, year) pair that failed FR-004 column-sum identity."""

    model_config = ConfigDict(frozen=True)

    target_industry_id: int
    year: int
    column_sum: float
    expected_share: float
    residual_fraction: float


class IndustrySnapshot(BaseModel):
    """Top-N / bottom-N entry for the intermediate-inputs-share leaderboard."""

    model_config = ConfigDict(frozen=True)

    bea_industry_id: int
    bea_industry_name: str
    year: int
    intermediate_inputs_share: float


class ConcordanceCoverageReport(BaseModel):
    """NAICS→BEA concordance coverage summary (SC-008)."""

    model_config = ConfigDict(frozen=True)

    total_naics_codes_in_qcew: int
    covered_by_direct_concordance: int
    covered_by_naics_2_digit_fallback: int
    uncovered: int
    coverage_fraction_full: float = Field(ge=0.0, le=1.0)
    coverage_fraction_with_fallback: float = Field(ge=0.0, le=1.0)


class StaleShareFallbackSummary(BaseModel):
    """Summary of forward-fill + global-default fallbacks (Clarification Q3)."""

    model_config = ConfigDict(frozen=True)

    total_county_year_lookups: int
    forward_filled_lookups: int
    global_default_lookups: int
    affected_employment_fraction: float = Field(ge=0.0, le=1.0)


class VintageSupersession(BaseModel):
    """A row whose existing vintage was superseded by a newer one (Q2)."""

    model_config = ConfigDict(frozen=True)

    table_name: str
    bea_industry_id: int
    year: int
    old_vintage: date | None
    new_vintage: date


class BEAIngestAuditReport(BaseModel):
    """Top-level spec-068 ingest audit report.

    Schema version 1.0. Written to disk in both JSON and Markdown.
    """

    model_config = ConfigDict(frozen=False)  # mutated as stages populate fields

    schema_version: Literal["1.0"] = "1.0"
    timestamp: datetime
    duration_seconds: float = 0.0
    sim_years_in_scope: tuple[int, ...]
    dry_run: bool = False

    rows_inserted: dict[str, int] = Field(default_factory=dict)
    rows_superseded: dict[str, int] = Field(default_factory=dict)
    rows_unchanged: dict[str, int] = Field(default_factory=dict)

    accounting_identity_violations: list[AccountingViolation] = Field(default_factory=list)
    column_sum_identity_violations: list[ColumnSumViolation] = Field(default_factory=list)

    intermediate_inputs_share_top10: list[IndustrySnapshot] = Field(default_factory=list)
    intermediate_inputs_share_bottom10: list[IndustrySnapshot] = Field(default_factory=list)

    naics_bea_concordance_coverage: ConcordanceCoverageReport | None = None
    stale_share_fallback_summary: StaleShareFallbackSummary | None = None
    vintage_supersessions: list[VintageSupersession] = Field(default_factory=list)

    sc_001_pass: bool | None = None
    sc_002_pass: bool | None = None
    sc_003_pass: bool | None = None
    sc_004_pass: bool | None = None
    sc_005_pass: bool | None = None
    sc_006_pass: bool | None = None
    sc_007_pass: bool | None = None
    sc_008_pass: bool | None = None
    sc_007_wallclock_seconds: float = 0.0

    def write_to_disk(self, report_dir: Path | None = None) -> tuple[Path, Path]:
        """Write the JSON and Markdown forms.

        Args:
            report_dir: Directory to write into (default ``reports/ingest/``).
                Created if absent.

        Returns:
            ``(json_path, md_path)`` — absolute Paths of the written files.
        """
        report_dir = report_dir or _REPORT_DIR_DEFAULT
        report_dir.mkdir(parents=True, exist_ok=True)
        stem_kind = "bea_io_dryrun" if self.dry_run else "bea_io"
        stem = f"{stem_kind}_{self.timestamp.strftime('%Y%m%dT%H%M%SZ')}"
        json_path = (report_dir / f"{stem}.json").resolve()
        md_path = (report_dir / f"{stem}.md").resolve()

        json_path.write_text(self.model_dump_json(indent=2))
        md_path.write_text(self._render_markdown())
        return json_path, md_path

    def _render_markdown(self) -> str:
        """Render the operator-facing Markdown form of the report."""
        lines: list[str] = []
        lines.append(f"# BEA I-O Ingest Audit — {self.timestamp.isoformat()}")
        lines.append("")
        lines.append(f"- **Schema version**: {self.schema_version}")
        lines.append(f"- **Dry run**: {self.dry_run}")
        lines.append(f"- **Duration**: {self.duration_seconds:.2f}s")
        lines.append(
            f"- **Sim years in scope**: {self.sim_years_in_scope[0]}-{self.sim_years_in_scope[-1]}"
        )
        lines.append("")
        lines.append("## Validation Gates")
        lines.append("")
        for sc_label, sc_value in [
            ("SC-001 (≥800 national rows)", self.sc_001_pass),
            ("SC-002 (≥50K coefficient rows)", self.sc_002_pass),
            ("SC-003 (FR-002 100% pass)", self.sc_003_pass),
            ("SC-004 (FR-004 100% pass)", self.sc_004_pass),
            ("SC-005 (stddev c/v ≥ 0.2)", self.sc_005_pass),
            ("SC-006 (Shaikh ±50% bands)", self.sc_006_pass),
            ("SC-007 (<15 min wallclock)", self.sc_007_pass),
            ("SC-008 (<1% uncovered employment)", self.sc_008_pass),
        ]:
            status = "PASS" if sc_value else ("FAIL" if sc_value is False else "—")
            lines.append(f"- `{sc_label}`: **{status}**")
        lines.append("")
        if self.rows_inserted:
            lines.append("## Rows Inserted")
            lines.append("")
            for tbl, n in self.rows_inserted.items():
                lines.append(f"- `{tbl}`: {n}")
            lines.append("")
        if self.accounting_identity_violations:
            lines.append("## FR-002 Accounting-Identity Violations")
            lines.append("")
            lines.append(f"Count: {len(self.accounting_identity_violations)}")
            lines.append("")
            for v in self.accounting_identity_violations[:25]:
                lines.append(
                    f"- industry={v.bea_industry_id} year={v.year} "
                    f"residual={v.residual_fraction:+.4f}"
                )
            if len(self.accounting_identity_violations) > 25:
                lines.append(f"- ... ({len(self.accounting_identity_violations) - 25} more)")
            lines.append("")
        if self.column_sum_identity_violations:
            lines.append("## FR-004 Column-Sum-Identity Violations")
            lines.append("")
            lines.append(f"Count: {len(self.column_sum_identity_violations)}")
            lines.append("")
            for cv in self.column_sum_identity_violations[:25]:
                lines.append(
                    f"- target={cv.target_industry_id} year={cv.year} "
                    f"sum={cv.column_sum:.6f} expected={cv.expected_share:.6f}"
                )
            lines.append("")
        if self.vintage_supersessions:
            lines.append("## Vintage Supersessions")
            lines.append("")
            for s in self.vintage_supersessions:
                lines.append(
                    f"- `{s.table_name}` industry={s.bea_industry_id} year={s.year}: "
                    f"{s.old_vintage} → {s.new_vintage}"
                )
            lines.append("")
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        """Serialize the report to a stable JSON form (used by tests)."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, data: str) -> BEAIngestAuditReport:
        """Inverse of :meth:`to_json` — round-trip safe."""
        return cls.model_validate_json(data)

    @classmethod
    def from_json_file(cls, path: Path) -> BEAIngestAuditReport:
        """Load a report from a previously-written JSON file."""
        return cls.from_json(path.read_text())


__all__ = [
    "AccountingViolation",
    "BEAIngestAuditReport",
    "ColumnSumViolation",
    "ConcordanceCoverageReport",
    "IndustrySnapshot",
    "StaleShareFallbackSummary",
    "VintageSupersession",
]
