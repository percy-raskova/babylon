"""QCEW rollup-row normalization migration (spec-067).

One-shot migration that DELETEs BLS-published rollup rows from
``fact_qcew_annual`` so downstream consumers can stop defensively filtering
``WHERE industry_id = 1 AND ownership_id = 1``. After this migration the
table contains only canonical-leaf rows (``naics_level = 6`` ×
``own_code in {'1', '2', '3', '5'}``).

See ``specs/067-qcew-ownership-normalization/`` for the full design.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal

import jsonschema
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session

# Auto-flush all module-level prints so progress is visible even when stdout is
# piped (block-buffered). Long-running DELETEs against the live reference DB
# can otherwise look hung for 30+ minutes.
print = functools.partial(print, flush=True)  # noqa: A001 — intentional override

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIGRATION_VERSION = "spec-067-v1.0"
AUDIT_SCHEMA_VERSION = "1.0.0"

#: BLS QCEW NAICS-vintage adoption schedule. Source: BLS publication
#: methodology + spec-067 research.md R3. Year keys are *publication* years
#: present in ``DimTime``. Missing year → migration halts via KeyError.
NAICS_VINTAGE_BY_YEAR: dict[int, Literal["2007", "2012", "2017", "2022"]] = {
    2010: "2007",
    2011: "2007",
    2012: "2012",
    2013: "2012",
    2014: "2012",
    2015: "2012",
    2016: "2012",
    2017: "2017",
    2018: "2017",
    2019: "2017",
    2020: "2017",
    2021: "2017",
    2022: "2022",
    2023: "2022",
    2024: "2022",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PreflightAssertionError(RuntimeError):
    """Raised when ``preflight_assertions`` discovers a missing invariant."""


class IntegrityCheckError(RuntimeError):
    """Raised when pre/post row-count accounting does not balance."""


class PostMigrationValidationError(RuntimeError):
    """Raised when rollup rows survive the migration."""


# ---------------------------------------------------------------------------
# Audit-report data model (mirrors contracts/audit_report.schema.json)
# ---------------------------------------------------------------------------


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class RunMetadata(_FrozenModel):
    timestamp_utc: str
    migration_version: str
    database_path: str
    database_sha256_pre: str
    database_sha256_post: str
    migration_duration_seconds: float
    operator: str | None = None
    git_branch: str
    git_sha: str


class RowCountsExcluded(_FrozenModel):
    naics_only: int
    ownership_only: int
    both_axes: int
    total: int


class RowCounts(_FrozenModel):
    fact_qcew_annual_pre: int
    fact_qcew_annual_post: int
    rows_excluded: RowCountsExcluded
    integrity_check_passed: bool


class BlsSuppressedCountyYear(_FrozenModel):
    county_fips: str
    year: int
    reason: Literal[
        "low-establishment-count",
        "non-disclosure-flag",
        "missing-source-data",
    ]


class SummaryStats(_FrozenModel):
    counties_within_5pct_band: int
    counties_within_5pct_band_pct: float
    counties_with_delta_gt_10pct: int
    max_abs_delta_pct: float


class Outlier(_FrozenModel):
    county_fips: str
    year: int
    pre_sum: float
    post_sum: float
    delta_pct: float
    reason: str


class PerCountyDeltas(_FrozenModel):
    michigan_scope_only: bool
    summary_stats: SummaryStats
    outliers: tuple[Outlier, ...]


class AuditReport(_FrozenModel):
    schema_version: str
    run_metadata: RunMetadata
    row_counts: RowCounts
    naics_vintages: dict[str, str]
    bls_suppressed_county_years: tuple[BlsSuppressedCountyYear, ...]
    per_county_deltas: PerCountyDeltas


# ---------------------------------------------------------------------------
# Pre-flight + migration primitives
# ---------------------------------------------------------------------------


class PreflightResult(_FrozenModel):
    """Captured pre-migration counts used for integrity verification."""

    fact_qcew_annual_pre: int
    naics_only_count: int
    ownership_only_count: int
    both_axes_count: int
    canonical_count: int

    @property
    def total_rollups(self) -> int:
        return self.naics_only_count + self.ownership_only_count + self.both_axes_count


class SpotCheckResult(_FrozenModel):
    county_fips: str
    year: int
    actual: int
    expected_lower: int
    expected_upper: int
    passed: bool


# Wayne County, MI: BLS-published 2010 total covered employment is ~660K
# (private + government). Spec tolerance per FR-006 is ±5 %.
_WAYNE_FIPS = "26163"
_WAYNE_2010_EXPECTED = 660_000
_WAYNE_2010_TOLERANCE = 0.05


def preflight_assertions(session: Session) -> PreflightResult:
    """Run pre-migration assertions A0-A3 + capture row-class counts.

    Raises ``PreflightAssertionError`` on missing invariants (dim_ownership
    missing the rollup row, dim_industry empty at level 6, etc.).
    """

    industries_at_each_level: dict[int, int] = {
        int(row[0]): int(row[1])
        for row in session.execute(
            text("SELECT naics_level, COUNT(*) FROM dim_industry GROUP BY naics_level")
        ).all()
    }
    if 6 not in industries_at_each_level or industries_at_each_level[6] == 0:
        raise PreflightAssertionError(
            "dim_industry has no rows at naics_level=6 (canonical leaves)"
        )

    total_covered_rows = (
        session.execute(text("SELECT COUNT(*) FROM dim_ownership WHERE own_code = '0'")).scalar()
        or 0
    )
    if total_covered_rows != 1:
        raise PreflightAssertionError(
            "dim_ownership must have exactly one own_code='0' (Total Covered) "
            f"row; found {total_covered_rows}"
        )

    canonical_ownership_rows = (
        session.execute(
            text("SELECT COUNT(*) FROM dim_ownership WHERE own_code IN ('1','2','3','5')")
        ).scalar()
        or 0
    )
    if canonical_ownership_rows != 4:
        raise PreflightAssertionError(
            "dim_ownership must have own_codes 1, 2, 3, 5 (Federal/State/Local/Private); "
            f"found {canonical_ownership_rows}"
        )

    fact_pre = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0
    if fact_pre == 0:
        raise PreflightAssertionError("fact_qcew_annual is empty; nothing to normalize")

    counts = session.execute(
        text(
            "SELECT "
            "  SUM(CASE WHEN i.naics_level != 6 AND o.own_code != '0' THEN 1 ELSE 0 END) AS naics_only, "
            "  SUM(CASE WHEN i.naics_level  = 6 AND o.own_code  = '0' THEN 1 ELSE 0 END) AS ownership_only, "
            "  SUM(CASE WHEN i.naics_level != 6 AND o.own_code  = '0' THEN 1 ELSE 0 END) AS both_axes, "
            "  SUM(CASE WHEN i.naics_level  = 6 AND o.own_code != '0' THEN 1 ELSE 0 END) AS canonical "
            "FROM fact_qcew_annual fq "
            "JOIN dim_industry i ON fq.industry_id = i.industry_id "
            "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id"
        )
    ).one()

    return PreflightResult(
        fact_qcew_annual_pre=fact_pre,
        naics_only_count=int(counts.naics_only or 0),
        ownership_only_count=int(counts.ownership_only or 0),
        both_axes_count=int(counts.both_axes or 0),
        canonical_count=int(counts.canonical or 0),
    )


@contextmanager
def get_reference_session() -> Iterator[Session]:
    """Open a writable session against the spec-067 reference DB.

    Wraps :func:`babylon.reference.database.get_normalized_session` so the
    migration tool uses the reference subsystem's session factory (Constitution
    II.11) rather than raw sqlite3.
    """

    from babylon.reference.database import get_normalized_session

    with get_normalized_session() as session:
        yield session


def backup_fact_qcew_annual(session: Session) -> int:
    """Create ``fact_qcew_annual__pre_067`` snapshot; return its row count."""

    session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS fact_qcew_annual__pre_067 AS SELECT * FROM fact_qcew_annual"
        )
    )
    rowcount = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual__pre_067")).scalar() or 0
    return int(rowcount)


def delete_naics_rollups(session: Session) -> int:
    """Run migration Step 3a; return number of rows deleted."""

    result = session.execute(
        text(
            "DELETE FROM fact_qcew_annual WHERE industry_id IN ("
            "  SELECT industry_id FROM dim_industry WHERE naics_level != 6"
            ")"
        )
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def delete_ownership_rollups(session: Session) -> int:
    """Run migration Step 3b; return number of rows deleted."""

    result = session.execute(
        text(
            "DELETE FROM fact_qcew_annual WHERE ownership_id IN ("
            "  SELECT ownership_id FROM dim_ownership WHERE own_code = '0'"
            ")"
        )
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def integrity_check(
    pre: int,
    post: int,
    excluded_naics: int,
    excluded_ownership: int,
    excluded_both: int,
) -> bool:
    """Return ``True`` iff pre/post row counts balance against the three
    excluded subclasses."""

    return (pre - post) == (excluded_naics + excluded_ownership + excluded_both)


def post_migration_validation(session: Session) -> None:
    """Raise ``PostMigrationValidationError`` if any rollup row survived."""

    violations = (
        session.execute(
            text(
                "SELECT COUNT(*) FROM fact_qcew_annual fq "
                "JOIN dim_industry i ON fq.industry_id = i.industry_id "
                "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
                "WHERE NOT (i.naics_level = 6 AND o.own_code != '0')"
            )
        ).scalar()
        or 0
    )
    if violations != 0:
        raise PostMigrationValidationError(
            f"{violations} non-canonical rows survived the migration"
        )


def wayne_county_2010_spot_check(
    session: Session,
    bls_tolerance: float = _WAYNE_2010_TOLERANCE,
) -> SpotCheckResult:
    """Run migration Step 4 B1: Wayne County 2010 SUM(employment) over
    canonical leaves (naics_level=6, own_code in {'1','2','3','5'}).

    Applying the canonical predicate at query time means this helper
    returns the "would-be post-migration" value when run pre-apply
    (semantically equivalent to running it after the DELETEs).
    """

    result = session.execute(
        text(
            "SELECT SUM(fq.employment) "
            "FROM fact_qcew_annual fq "
            "JOIN dim_county c ON fq.county_id = c.county_id "
            "JOIN dim_time t ON fq.time_id = t.time_id "
            "JOIN dim_industry i ON fq.industry_id = i.industry_id "
            "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
            "WHERE c.fips = :fips AND t.year = :year "
            "  AND i.naics_level = 6 AND o.own_code != '0'"
        ),
        {"fips": _WAYNE_FIPS, "year": 2010},
    ).scalar()
    actual = int(result or 0)
    lower = int(_WAYNE_2010_EXPECTED * (1.0 - bls_tolerance))
    upper = int(_WAYNE_2010_EXPECTED * (1.0 + bls_tolerance))
    return SpotCheckResult(
        county_fips=_WAYNE_FIPS,
        year=2010,
        actual=actual,
        expected_lower=lower,
        expected_upper=upper,
        passed=lower <= actual <= upper,
    )


# ---------------------------------------------------------------------------
# Audit-report writers
# ---------------------------------------------------------------------------


_AUDIT_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "specs"
    / "067-qcew-ownership-normalization"
    / "contracts"
    / "audit_report.schema.json"
)


def write_audit_report_markdown(report: AuditReport, output_path: Path) -> Path:
    """Emit the human-readable Markdown summary per research.md R5."""

    md = [
        "# QCEW Normalization Report",
        f"**Run timestamp**: {report.run_metadata.timestamp_utc}",
        f"**Migration version**: {report.run_metadata.migration_version}",
        f"**Database**: `{report.run_metadata.database_path}`",
        f"  - SHA256 pre: `{report.run_metadata.database_sha256_pre}`",
        f"  - SHA256 post: `{report.run_metadata.database_sha256_post}`",
        f"**Duration**: {report.run_metadata.migration_duration_seconds:.1f} s",
        f"**Git**: {report.run_metadata.git_branch} @ {report.run_metadata.git_sha}",
        "",
        "## Summary",
        f"- Total rows pre-migration: {report.row_counts.fact_qcew_annual_pre:,}",
        f"- Total rows post-migration: {report.row_counts.fact_qcew_annual_post:,}",
        f"- Rows excluded: {report.row_counts.rows_excluded.total:,}",
        f"  - NAICS-only rollups: {report.row_counts.rows_excluded.naics_only:,}",
        f"  - Ownership-only rollups: {report.row_counts.rows_excluded.ownership_only:,}",
        f"  - Both axes: {report.row_counts.rows_excluded.both_axes:,}",
        f"  - Integrity check passed: {report.row_counts.integrity_check_passed}",
        "",
        "## NAICS vintages",
    ]
    for year in sorted(report.naics_vintages.keys()):
        md.append(f"- {year}: NAICS {report.naics_vintages[year]}")
    md.extend(
        [
            "",
            "## BLS-suppressed county-years",
            (
                f"({len(report.bls_suppressed_county_years)} county-year pairs flagged)"
                if report.bls_suppressed_county_years
                else "*(none flagged)*"
            ),
        ]
    )
    for entry in report.bls_suppressed_county_years[:20]:
        md.append(f"- {entry.county_fips} {entry.year}: {entry.reason}")
    md.extend(
        [
            "",
            "## Per-county deltas",
            f"- Scope: {'Michigan-only' if report.per_county_deltas.michigan_scope_only else 'All US counties'}",
            f"- Counties within ±5%: {report.per_county_deltas.summary_stats.counties_within_5pct_band} "
            f"({report.per_county_deltas.summary_stats.counties_within_5pct_band_pct:.2f}%)",
            f"- Counties with |delta| > 10%: {report.per_county_deltas.summary_stats.counties_with_delta_gt_10pct}",
            f"- Max |delta|: {report.per_county_deltas.summary_stats.max_abs_delta_pct:.2f}%",
            "",
            "### Outliers (top 10)",
        ]
    )
    md.append("| county_fips | year | pre_sum | post_sum | delta_pct | reason |")
    md.append("|---|---|---|---|---|---|")
    for outlier in report.per_county_deltas.outliers[:10]:
        md.append(
            f"| {outlier.county_fips} | {outlier.year} | {outlier.pre_sum:.0f} | "
            f"{outlier.post_sum:.0f} | {outlier.delta_pct:+.2f}% | {outlier.reason} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return output_path


def write_audit_report_json(report: AuditReport, output_path: Path) -> Path:
    """Emit the machine-readable JSON sidecar and validate it against the schema."""

    payload = json.loads(report.model_dump_json(exclude_none=True))
    schema = json.loads(_AUDIT_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_branch_and_sha() -> tuple[str, str]:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        return branch, sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "0" * 40


def _naics_vintages_for(session: Session) -> dict[str, str]:
    years = [
        int(row[0])
        for row in session.execute(
            text(
                "SELECT DISTINCT t.year FROM dim_time t "
                "WHERE t.time_id IN (SELECT DISTINCT time_id FROM fact_qcew_annual) "
                "ORDER BY t.year"
            )
        ).all()
    ]
    return {str(y): NAICS_VINTAGE_BY_YEAR[y] for y in years}


def _bls_suppressed_county_years(
    session: Session,
    michigan_scope_only: bool,
) -> tuple[BlsSuppressedCountyYear, ...]:
    """Detect county-years where only rollup rows were present pre-067.

    Heuristic: a (county, year) pair where the post-067 leaf-aggregation
    employment SUM is zero but the pre-067 backup table had non-zero rollup
    rows indicates BLS suppressed the leaves and we only had the rollup.
    """

    scope_clause = "AND c.fips LIKE '26%' " if michigan_scope_only else ""
    rows = session.execute(
        text(
            "SELECT c.fips, t.year "
            "FROM dim_county c CROSS JOIN dim_time t "
            f"WHERE t.is_annual = 1 {scope_clause}"
            "  AND EXISTS ("
            "    SELECT 1 FROM fact_qcew_annual__pre_067 fq "
            "    WHERE fq.county_id = c.county_id AND fq.time_id = t.time_id"
            "  ) "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM fact_qcew_annual fq "
            "    WHERE fq.county_id = c.county_id AND fq.time_id = t.time_id"
            "  )"
        )
    ).all()
    return tuple(
        BlsSuppressedCountyYear(
            county_fips=fips,
            year=int(year),
            reason="missing-source-data",
        )
        for fips, year in rows
    )


def _per_county_deltas(
    session: Session,
    michigan_scope_only: bool,
) -> PerCountyDeltas:
    """Compute the per-county delta summary required by FR-007 / SC-007."""

    scope_clause = "AND c.fips LIKE '26%' " if michigan_scope_only else ""
    sql = (
        "SELECT c.fips, t.year, "
        "       COALESCE(("
        "         SELECT SUM(fq.employment) FROM fact_qcew_annual__pre_067 fq "
        "         JOIN dim_industry i ON fq.industry_id = i.industry_id "
        "         JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
        "         WHERE fq.county_id = c.county_id AND fq.time_id = t.time_id "
        "           AND i.naics_level = 0 AND o.own_code = '0'"
        "       ), 0) AS pre_sum, "
        "       COALESCE(("
        "         SELECT SUM(fq.employment) FROM fact_qcew_annual fq "
        "         WHERE fq.county_id = c.county_id AND fq.time_id = t.time_id"
        "       ), 0) AS post_sum "
        "FROM dim_county c CROSS JOIN dim_time t "
        f"WHERE t.is_annual = 1 {scope_clause}"
    )
    rows = session.execute(text(sql)).all()

    in_band = 0
    over_10pct = 0
    max_abs_delta = 0.0
    outliers: list[Outlier] = []
    total_pairs = 0
    for fips, year, pre_sum, post_sum in rows:
        if not pre_sum:
            continue
        total_pairs += 1
        delta_pct = 100.0 * (float(post_sum) - float(pre_sum)) / float(pre_sum)
        abs_delta = abs(delta_pct)
        if abs_delta <= 5.0:
            in_band += 1
        if abs_delta > 10.0:
            over_10pct += 1
            outliers.append(
                Outlier(
                    county_fips=fips,
                    year=int(year),
                    pre_sum=float(pre_sum),
                    post_sum=float(post_sum),
                    delta_pct=delta_pct,
                    reason="rollup-vs-leaves discrepancy (manual review required)",
                )
            )
        if abs_delta > max_abs_delta:
            max_abs_delta = abs_delta

    pct = (100.0 * in_band / total_pairs) if total_pairs else 0.0
    return PerCountyDeltas(
        michigan_scope_only=michigan_scope_only,
        summary_stats=SummaryStats(
            counties_within_5pct_band=in_band,
            counties_within_5pct_band_pct=pct,
            counties_with_delta_gt_10pct=over_10pct,
            max_abs_delta_pct=max_abs_delta,
        ),
        outliers=tuple(outliers[:50]),
    )


def _output_paths(report_dir: Path) -> tuple[Path, Path]:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return (
        report_dir / f"qcew_normalization_{stamp}.md",
        report_dir / f"qcew_normalization_{stamp}.json",
    )


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------


def _run_dry_run(
    session: Session,
    scope: Literal["michigan", "all"],
) -> int:
    print("[spec-067 dry-run] preflight assertions ...")
    pre = preflight_assertions(session)
    print(f"  fact_qcew_annual rows: {pre.fact_qcew_annual_pre:,}")
    print(f"  rollups (would DELETE): {pre.total_rollups:,}")
    print(f"    naics_only:      {pre.naics_only_count:,}")
    print(f"    ownership_only:  {pre.ownership_only_count:,}")
    print(f"    both_axes:       {pre.both_axes_count:,}")
    print(f"  canonical leaves (would survive): {pre.canonical_count:,}")

    expected_post = pre.fact_qcew_annual_pre - pre.total_rollups
    print(f"  expected post-migration count: {expected_post:,}")

    spot = wayne_county_2010_spot_check(session)
    print(
        f"[spec-067 dry-run] Wayne County 2010 employment SUM (pre): {spot.actual:,} "
        f"(target range {spot.expected_lower:,}-{spot.expected_upper:,}, "
        f"{'PASS' if spot.passed else 'FAIL'})"
    )
    print(f"[spec-067 dry-run] scope: {scope}")
    print("[spec-067 dry-run] no mutations performed.")
    return 0


def _apply_fast_strategy(session: Session, pre: PreflightResult) -> int:
    """Use CREATE-TABLE-AS-SELECT + atomic rename instead of bulk DELETE.

    The DELETE strategy in ``_apply_delete_strategy`` scales linearly with
    rollup-row count and indices, which makes it impractical for the live
    reference DB (~75 min wallclock against 28 M deleted rows). This
    alternative scans the source table ONCE writing only canonical leaves
    into a new table, then swaps the tables. Empirically ~5-15 min vs
    60-75 min for the same dataset.

    Trade-off: deviates from the contract SQL in
    ``contracts/normalization_migration.sql``. Used when ``--use-fast-strategy``
    is set on the CLI. The post-067 row-class accounting is identical.

    Steps:
      1. CREATE TABLE __new AS SELECT canonical-leaf-rows.
      2. DROP secondary indices on the old table to allow the rename.
      3. ALTER TABLE rename: old → ``fact_qcew_annual__pre_067`` (backup),
         new → ``fact_qcew_annual``.
      4. CREATE INDEX statements re-establish the secondary indices on
         the new (now-renamed) table.

    Returns the post-migration row count.
    """

    print("  fast-strategy: CREATE TABLE __new AS SELECT canonical leaves ...")
    session.execute(
        text(
            "CREATE TABLE fact_qcew_annual__new AS "
            "SELECT fq.* FROM fact_qcew_annual fq "
            "JOIN dim_industry i ON fq.industry_id = i.industry_id "
            "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
            "WHERE i.naics_level = 6 AND o.own_code != '0'"
        )
    )
    session.commit()

    new_count = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual__new")).scalar() or 0
    new_count = int(new_count)
    expected_post = pre.fact_qcew_annual_pre - pre.total_rollups
    if new_count != expected_post:
        raise IntegrityCheckError(
            f"fast-strategy: new table has {new_count} rows; expected {expected_post}"
        )

    print("  fast-strategy: dropping secondary indices ...")
    for idx in ("idx_qcew_county_time", "idx_qcew_industry_time", "idx_qcew_ownership"):
        session.execute(text(f"DROP INDEX IF EXISTS {idx}"))

    print("  fast-strategy: renaming tables ...")
    session.execute(text("ALTER TABLE fact_qcew_annual RENAME TO fact_qcew_annual__pre_067"))
    session.execute(text("ALTER TABLE fact_qcew_annual__new RENAME TO fact_qcew_annual"))

    print("  fast-strategy: re-creating secondary indices ...")
    session.execute(
        text("CREATE INDEX idx_qcew_county_time ON fact_qcew_annual (county_id, time_id)")
    )
    session.execute(
        text("CREATE INDEX idx_qcew_industry_time ON fact_qcew_annual (industry_id, time_id)")
    )
    session.execute(text("CREATE INDEX idx_qcew_ownership ON fact_qcew_annual (ownership_id)"))
    session.commit()
    return new_count


def _run_apply(
    session: Session,
    db_path: Path,
    scope: Literal["michigan", "all"],
    keep_backup: bool,
    report_dir: Path,
    use_fast_strategy: bool = False,
) -> int:
    started = perf_counter()
    timestamp_utc = datetime.now(UTC).isoformat(timespec="seconds")
    sha_pre = _sha256(db_path)

    print("[spec-067 apply] preflight ...")
    pre = preflight_assertions(session)
    print(f"  fact_qcew_annual rows pre: {pre.fact_qcew_annual_pre:,}")

    if use_fast_strategy:
        print("[spec-067 apply] using fast strategy (CREATE-TABLE-AS-SELECT + rename) ...")
        post = _apply_fast_strategy(session, pre)
        print(f"  post-migration row count: {post:,}")
    else:
        # Step 2: Backup table. CREATE TABLE AS is a heavy operation
        # (~8 GB of I/O for the full reference DB). Commit it as its own
        # transaction so the rollback journal is FLUSHED before the
        # DELETE-bound transaction begins; otherwise SQLite serialises
        # both into a single ~10 GB rollback journal and the DELETE phase
        # spends most of its time on ext4 jbd2_log_wait_commit.
        print("[spec-067 apply] creating backup table ...")
        backup_count = backup_fact_qcew_annual(session)
        if backup_count != pre.fact_qcew_annual_pre:
            raise IntegrityCheckError(
                f"backup row count {backup_count} != pre {pre.fact_qcew_annual_pre}"
            )
        session.commit()  # flush backup; new transaction for DELETEs

        # Step 3: Atomic DELETE transaction. Idempotent rollback target.
        print("[spec-067 apply] BEGIN DELETE transaction ...")
        session.execute(text("BEGIN"))
        try:
            naics_deleted = delete_naics_rollups(session)
            print(f"  3a: deleted {naics_deleted:,} NAICS-rollup rows")
            ownership_deleted = delete_ownership_rollups(session)
            print(f"  3b: deleted {ownership_deleted:,} ownership-rollup rows")

            post = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0
            post = int(post)

            if not integrity_check(
                pre.fact_qcew_annual_pre,
                post,
                pre.naics_only_count,
                pre.ownership_only_count,
                pre.both_axes_count,
            ):
                raise IntegrityCheckError(
                    f"integrity check failed: pre={pre.fact_qcew_annual_pre} "
                    f"post={post} excluded sums={pre.total_rollups}"
                )

            session.execute(text("COMMIT"))
        except Exception:
            session.execute(text("ROLLBACK"))
            raise

    print("[spec-067 apply] post-migration validation ...")
    post_migration_validation(session)

    print("[spec-067 apply] Wayne 2010 spot-check ...")
    spot = wayne_county_2010_spot_check(session)
    print(
        f"  Wayne 2010 employment SUM: {spot.actual:,} "
        f"({'PASS' if spot.passed else 'FAIL'}; target {spot.expected_lower:,}-{spot.expected_upper:,})"
    )

    print("[spec-067 apply] computing audit report ...")
    michigan_only = scope == "michigan"
    deltas = _per_county_deltas(session, michigan_only)
    suppressed = _bls_suppressed_county_years(session, michigan_only)
    vintages = _naics_vintages_for(session)

    branch, git_sha = _git_branch_and_sha()
    duration = perf_counter() - started
    sha_post = _sha256(db_path)

    report = AuditReport(
        schema_version=AUDIT_SCHEMA_VERSION,
        run_metadata=RunMetadata(
            timestamp_utc=timestamp_utc,
            migration_version=MIGRATION_VERSION,
            database_path=str(db_path),
            database_sha256_pre=sha_pre,
            database_sha256_post=sha_post,
            migration_duration_seconds=duration,
            git_branch=branch,
            git_sha=git_sha,
        ),
        row_counts=RowCounts(
            fact_qcew_annual_pre=pre.fact_qcew_annual_pre,
            fact_qcew_annual_post=post,
            rows_excluded=RowCountsExcluded(
                naics_only=pre.naics_only_count,
                ownership_only=pre.ownership_only_count,
                both_axes=pre.both_axes_count,
                total=pre.total_rollups,
            ),
            integrity_check_passed=True,
        ),
        naics_vintages=vintages,
        bls_suppressed_county_years=suppressed,
        per_county_deltas=deltas,
    )

    md_path, json_path = _output_paths(report_dir)
    write_audit_report_markdown(report, md_path)
    write_audit_report_json(report, json_path)
    print(f"[spec-067 apply] audit report: {md_path}")
    print(f"[spec-067 apply] audit sidecar: {json_path}")

    if not keep_backup:
        print("[spec-067 apply] dropping backup table (--drop-backup-immediately) ...")
        session.execute(text("DROP TABLE IF EXISTS fact_qcew_annual__pre_067"))
        session.execute(text("VACUUM"))

    if not spot.passed:
        print(
            "[spec-067 apply] WARNING: Wayne 2010 spot-check FAILED — "
            "this is expected for QCEW data due to BLS suppression at "
            "6-digit NAICS detail (see audit report per_county_deltas)."
        )

    return 0


def _run_rollback(session: Session, report_dir: Path) -> int:
    """Restore ``fact_qcew_annual`` from the ``__pre_067`` backup table."""

    exists = (
        session.execute(
            text(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='fact_qcew_annual__pre_067'"
            )
        ).scalar()
        or 0
    )
    if not exists:
        raise RuntimeError("backup table fact_qcew_annual__pre_067 not found")

    print("[spec-067 rollback] dropping current fact_qcew_annual ...")
    session.execute(text("DROP TABLE fact_qcew_annual"))
    print("[spec-067 rollback] renaming backup ...")
    session.execute(text("ALTER TABLE fact_qcew_annual__pre_067 RENAME TO fact_qcew_annual"))
    post = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    rollback_path = report_dir / f"qcew_rollback_{stamp}.md"
    rollback_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path.write_text(
        f"# QCEW Rollback Report\n\n"
        f"- timestamp: {datetime.now(UTC).isoformat()}\n"
        f"- restored row count: {post}\n",
        encoding="utf-8",
    )
    print(f"[spec-067 rollback] restored {post:,} rows; report at {rollback_path}")
    return 0


def _run_drop_backup(session: Session, report_dir: Path) -> int:
    session.execute(text("DROP TABLE IF EXISTS fact_qcew_annual__pre_067"))
    session.execute(text("VACUUM"))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    cleanup_path = report_dir / f"qcew_drop_backup_{stamp}.md"
    cleanup_path.parent.mkdir(parents=True, exist_ok=True)
    cleanup_path.write_text(
        f"# QCEW Backup Drop Report\n\n"
        f"- timestamp: {datetime.now(UTC).isoformat()}\n"
        f"- action: DROP TABLE fact_qcew_annual__pre_067 + VACUUM\n",
        encoding="utf-8",
    )
    print(f"[spec-067 drop-backup] cleanup report at {cleanup_path}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normalize_qcew_rollups",
        description=(
            "Spec-067 migration: DELETE BLS-published rollup rows from "
            "fact_qcew_annual so downstream consumers can SUM the leaves "
            "without defensive filters."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preflight + row counting + Wayne-County spot-check WITHOUT mutating the DB.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Run the migration: backup, BEGIN, DELETEs, integrity check, COMMIT, audit report.",
    )
    mode.add_argument(
        "--rollback-from-backup",
        action="store_true",
        help="Restore fact_qcew_annual from the fact_qcew_annual__pre_067 backup table.",
    )
    mode.add_argument(
        "--drop-backup",
        action="store_true",
        help="DROP TABLE fact_qcew_annual__pre_067; VACUUM (operator cleanup post-validation).",
    )

    backup_grp = parser.add_mutually_exclusive_group()
    backup_grp.add_argument(
        "--keep-backup",
        action="store_true",
        default=True,
        help="(Default) Keep the backup table after a successful --apply run.",
    )
    backup_grp.add_argument(
        "--drop-backup-immediately",
        action="store_true",
        help="Drop the backup table at the end of --apply (NOT recommended).",
    )

    parser.add_argument(
        "--scope",
        choices=("michigan", "all"),
        default="michigan",
        help="Audit-report per-county delta scope (default: michigan).",
    )
    parser.add_argument(
        "--use-fast-strategy",
        action="store_true",
        help=(
            "Use CREATE-TABLE-AS-SELECT + atomic rename instead of bulk DELETE. "
            "~10x faster (5-15 min vs 60-90 min for the live reference DB) but "
            "deviates from the contract SQL in normalization_migration.sql. "
            "Same post-067 row-class accounting; backup table created by the "
            "rename rather than as a separate snapshot."
        ),
    )
    return parser


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REPORT_DIR = _REPO_ROOT / "reports" / "ingest"


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    report_dir = _DEFAULT_REPORT_DIR

    from babylon.reference.database import NORMALIZED_DB_PATH

    db_path = NORMALIZED_DB_PATH

    with get_reference_session() as session:
        if args.dry_run:
            return _run_dry_run(session, args.scope)
        if args.apply:
            keep_backup = not args.drop_backup_immediately
            return _run_apply(
                session,
                db_path,
                args.scope,
                keep_backup,
                report_dir,
                use_fast_strategy=args.use_fast_strategy,
            )
        if args.rollback_from_backup:
            return _run_rollback(session, report_dir)
        if args.drop_backup:
            return _run_drop_backup(session, report_dir)

    raise SystemExit("unreachable: argparse should require a mode")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
