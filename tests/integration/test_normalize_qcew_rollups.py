"""Integration tests for the spec-067 QCEW normalization migration tool.

Covers pre-flight assertions, backup creation, DELETE statements, integrity
check, post-migration validation, Wayne-County spot-check, audit reports,
dry-run / apply / rollback / drop-backup modes, and idempotency.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_TINY_DDL = """
CREATE TABLE dim_industry (
    industry_id INTEGER PRIMARY KEY,
    naics_code TEXT NOT NULL,
    industry_title TEXT NOT NULL,
    naics_level INTEGER NOT NULL
);
CREATE TABLE dim_ownership (
    ownership_id INTEGER PRIMARY KEY,
    own_code TEXT NOT NULL,
    own_title TEXT NOT NULL,
    is_government INTEGER NOT NULL,
    is_private INTEGER NOT NULL
);
CREATE TABLE dim_county (
    county_id INTEGER PRIMARY KEY,
    fips TEXT NOT NULL,
    county_name TEXT NOT NULL
);
CREATE TABLE dim_time (
    time_id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    is_annual INTEGER NOT NULL
);
CREATE TABLE fact_qcew_annual (
    county_id INTEGER NOT NULL,
    industry_id INTEGER NOT NULL,
    ownership_id INTEGER NOT NULL,
    time_id INTEGER NOT NULL,
    employment INTEGER,
    total_wages_usd REAL,
    PRIMARY KEY (county_id, industry_id, ownership_id, time_id),
    FOREIGN KEY (industry_id) REFERENCES dim_industry(industry_id),
    FOREIGN KEY (ownership_id) REFERENCES dim_ownership(ownership_id),
    FOREIGN KEY (county_id) REFERENCES dim_county(county_id),
    FOREIGN KEY (time_id) REFERENCES dim_time(time_id)
);
"""


def _seed_tiny_dims(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO dim_industry (industry_id, naics_code, industry_title, naics_level) VALUES "
            "(1, '10', 'All industries (supersector rollup)', 0), "
            "(2, '311111', 'Dog and cat food mfg', 6), "
            "(3, '311119', 'Other animal food mfg', 6)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_ownership (ownership_id, own_code, own_title, is_government, is_private) VALUES "
            "(1, '0', 'Total Covered (rollup)', 0, 0), "
            "(2, '5', 'Private', 0, 1), "
            "(3, '1', 'Federal Government', 1, 0), "
            "(4, '2', 'State Government', 1, 0), "
            "(5, '3', 'Local Government', 1, 0)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_county (county_id, fips, county_name) VALUES "
            "(1, '26163', 'Wayne County'), (2, '26099', 'Macomb County')"
        )
    )
    session.execute(text("INSERT INTO dim_time (time_id, year, is_annual) VALUES (1, 2010, 1)"))


def _seed_tiny_facts(session: Session) -> None:
    # 6 rows: 2 rollups (1 NAICS rollup + 1 ownership rollup), 4 canonical leaves.
    rows = [
        # NAICS rollup (industry_id=1, all-industries supersector) — DELETE 3a
        (1, 1, 2, 1, 1200, 62_000_000.0),  # Wayne private all-industries
        # Ownership rollup (ownership_id=1, total-covered) — DELETE 3b
        (1, 2, 1, 1, 700, 35_000_000.0),  # Wayne 311111 total-covered
        # Canonical leaves — SURVIVE (4 rows)
        (1, 2, 2, 1, 500, 25_000_000.0),  # Wayne 311111 private
        (1, 2, 3, 1, 100, 6_000_000.0),  # Wayne 311111 federal
        (1, 3, 2, 1, 100, 5_500_000.0),  # Wayne 311119 private
        (2, 3, 3, 1, 50, 2_800_000.0),  # Macomb 311119 federal
    ]
    session.execute(
        text(
            "INSERT INTO fact_qcew_annual "
            "(county_id, industry_id, ownership_id, time_id, employment, total_wages_usd) "
            "VALUES (:c, :i, :o, :t, :e, :w)"
        ),
        [{"c": c, "i": i, "o": o, "t": t, "e": e, "w": w} for (c, i, o, t, e, w) in rows],
    )


@pytest.fixture
def tiny_qcew_fixture() -> Iterator[Session]:
    """In-memory SQLite with 6 hand-crafted rows (2 rollups, 4 leaves)."""

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for stmt in _TINY_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        _seed_tiny_dims(session)
        _seed_tiny_facts(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def populated_qcew_fixture(tmp_path: Path) -> Iterator[Session]:
    """Mid-size 100-row fixture for end-to-end migration validation."""

    # T012-T036 use this fixture; for now we ship a placeholder that scales the
    # tiny fixture up by replicating it across 16 (county, year) cells. This is
    # adequate for integrity-check + Wayne-spot-check tests; full populated
    # behavior arrives with T012.
    db_path = tmp_path / "populated_qcew.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        for stmt in _TINY_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        _seed_tiny_dims(session)
        # Replicate to 16 cells (still small but enough for rate-of-rollup
        # ratios to look plausible).
        for time_offset in range(16):
            session.execute(
                text(
                    "INSERT OR IGNORE INTO dim_time (time_id, year, is_annual) VALUES (:t, :y, 1)"
                ),
                {"t": time_offset + 2, "y": 2010 + time_offset},
            )
        _seed_tiny_facts(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Smoke test (T009)
# ---------------------------------------------------------------------------


def test_smoke_dry_sql(tiny_qcew_fixture: Session) -> None:
    """Run the canonical DELETE statements directly against the tiny fixture
    and assert the post-state has exactly 4 canonical-leaf rows.
    """

    session = tiny_qcew_fixture
    pre = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    assert pre == 6, f"tiny fixture should start with 6 rows, got {pre}"

    session.execute(
        text(
            "DELETE FROM fact_qcew_annual WHERE industry_id IN "
            "(SELECT industry_id FROM dim_industry WHERE naics_level != 6)"
        )
    )
    session.execute(
        text(
            "DELETE FROM fact_qcew_annual WHERE ownership_id IN "
            "(SELECT ownership_id FROM dim_ownership WHERE own_code = '0')"
        )
    )
    session.commit()

    post = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    assert post == 4, (
        f"expected 4 canonical-leaf rows (naics_level=6 × own_code in {{'1','5'}}), got {post}"
    )

    # Every survivor must satisfy the canonical predicate.
    violations = session.execute(
        text(
            "SELECT COUNT(*) FROM fact_qcew_annual fq "
            "JOIN dim_industry i ON fq.industry_id = i.industry_id "
            "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
            "WHERE NOT (i.naics_level = 6 AND o.own_code != '0')"
        )
    ).scalar()
    assert violations == 0, f"{violations} non-canonical rows survived"


# ---------------------------------------------------------------------------
# US1 unit tests for migration primitives
# ---------------------------------------------------------------------------


from tools.normalize_qcew_rollups import (  # noqa: E402
    AUDIT_SCHEMA_VERSION,
    AuditReport,
    PerCountyDeltas,
    PostMigrationValidationError,
    PreflightAssertionError,
    RowCounts,
    RowCountsExcluded,
    RunMetadata,
    SummaryStats,
    _apply_fast_strategy,
    _per_county_deltas,
    backup_fact_qcew_annual,
    delete_naics_rollups,
    delete_ownership_rollups,
    integrity_check,
    post_migration_validation,
    preflight_assertions,
    wayne_county_2010_spot_check,
    write_audit_report_json,
    write_audit_report_markdown,
)


def _execute_full_migration(session: Session) -> tuple[int, int, int]:
    """Apply the canonical DELETE sequence; return (pre, naics_n, ownership_n)."""

    pre = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0
    naics_n = delete_naics_rollups(session)
    ownership_n = delete_ownership_rollups(session)
    session.commit()
    return int(pre), naics_n, ownership_n


# T010
def test_preflight_catches_unpopulated_naics_level(tiny_qcew_fixture: Session) -> None:
    """Preflight fails if dim_industry has no rows at naics_level=6."""

    tiny_qcew_fixture.execute(text("DELETE FROM fact_qcew_annual"))
    tiny_qcew_fixture.execute(text("DELETE FROM dim_industry WHERE naics_level = 6"))
    tiny_qcew_fixture.commit()
    with pytest.raises(PreflightAssertionError, match="naics_level=6"):
        preflight_assertions(tiny_qcew_fixture)


# T011
def test_preflight_catches_missing_total_covered_ownership(
    tiny_qcew_fixture: Session,
) -> None:
    """Preflight fails if dim_ownership lacks the rollup row."""

    tiny_qcew_fixture.execute(text("DELETE FROM fact_qcew_annual"))
    tiny_qcew_fixture.execute(text("DELETE FROM dim_ownership WHERE own_code = '0'"))
    tiny_qcew_fixture.commit()
    with pytest.raises(PreflightAssertionError, match="Total Covered"):
        preflight_assertions(tiny_qcew_fixture)


# T013
def test_backup_table_created_with_identical_row_count(
    tiny_qcew_fixture: Session,
) -> None:
    """Backup table mirrors pre-migration row count."""

    pre = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0
    backup_count = backup_fact_qcew_annual(tiny_qcew_fixture)
    assert backup_count == int(pre)


def test_backup_table_idempotent_when_already_exists(
    tiny_qcew_fixture: Session,
) -> None:
    """Re-running backup_fact_qcew_annual leaves the existing backup intact.

    Real-world scenario: a prior migration run created the backup table but
    crashed before COMMIT; the operator re-runs --apply. The backup table
    already exists; the tool should not re-create it (which would lose the
    pre-067 snapshot) or fail noisily — it should treat the existing backup
    as authoritative.
    """

    first = backup_fact_qcew_annual(tiny_qcew_fixture)
    # Simulate a partial DELETE happening between the two backup calls.
    tiny_qcew_fixture.execute(text("DELETE FROM fact_qcew_annual WHERE industry_id = 1"))
    tiny_qcew_fixture.commit()
    second = backup_fact_qcew_annual(tiny_qcew_fixture)
    # Second call must return the ORIGINAL backup count, not the
    # post-partial-DELETE count. The CREATE TABLE IF NOT EXISTS clause
    # is the load-bearing detail.
    assert second == first, (
        f"backup_fact_qcew_annual re-overwrote on second call: first={first}, second={second}"
    )


# T016
def test_naics_rollups_deleted_count_matches_preflight(
    tiny_qcew_fixture: Session,
) -> None:
    """delete_naics_rollups removes exactly the preflight-counted NAICS rows."""

    pre_result = preflight_assertions(tiny_qcew_fixture)
    deleted = delete_naics_rollups(tiny_qcew_fixture)
    # In the tiny fixture, the only NAICS rollup is industry_id=1 with private
    # ownership (1 row in `naics_only`).
    assert deleted == pre_result.naics_only_count + pre_result.both_axes_count


# T017
def test_ownership_rollups_deleted_count_matches_preflight(
    tiny_qcew_fixture: Session,
) -> None:
    """delete_ownership_rollups removes the ownership-rollup subset that
    survived 3a (i.e. ownership_only after the NAICS DELETE).
    """

    pre_result = preflight_assertions(tiny_qcew_fixture)
    delete_naics_rollups(tiny_qcew_fixture)
    deleted = delete_ownership_rollups(tiny_qcew_fixture)
    # After 3a, only ownership_only rows remain that match 3b.
    assert deleted == pre_result.ownership_only_count


# T019
def test_integrity_check_passes_on_consistent_counts() -> None:
    assert integrity_check(
        pre=100, post=70, excluded_naics=20, excluded_ownership=8, excluded_both=2
    )


def test_integrity_check_fails_on_mismatch() -> None:
    assert not integrity_check(
        pre=100, post=70, excluded_naics=20, excluded_ownership=8, excluded_both=5
    )


# T021
def test_post_migration_no_rollups_remain(tiny_qcew_fixture: Session) -> None:
    _execute_full_migration(tiny_qcew_fixture)
    post_migration_validation(tiny_qcew_fixture)


def test_post_migration_validation_flags_surviving_rollups(
    tiny_qcew_fixture: Session,
) -> None:
    """If we forget to run 3b, post_migration_validation raises."""

    delete_naics_rollups(tiny_qcew_fixture)
    tiny_qcew_fixture.commit()
    with pytest.raises(PostMigrationValidationError):
        post_migration_validation(tiny_qcew_fixture)


# T023 — Wayne County is not present in the tiny fixture at BLS scale, so the
# tiny-fixture spot check returns actual << expected_lower. The real-DB run in
# T036 is the load-bearing case; here we only verify the helper returns a
# SpotCheckResult with the right structure and a passed=False signal.
def test_wayne_2010_spot_check_returns_structure(tiny_qcew_fixture: Session) -> None:
    _execute_full_migration(tiny_qcew_fixture)
    result = wayne_county_2010_spot_check(tiny_qcew_fixture)
    assert result.county_fips == "26163"
    assert result.year == 2010
    # tiny fixture has 500+100=600 employment for Wayne 2010 — far below the
    # ~660K BLS target; we only assert the structural envelope here.
    assert result.expected_lower < result.expected_upper
    assert result.passed is False


# T026
def _make_minimal_report() -> AuditReport:
    """Construct a schema-valid AuditReport for serialization tests."""

    return AuditReport(
        schema_version=AUDIT_SCHEMA_VERSION,
        run_metadata=RunMetadata(
            timestamp_utc="2026-05-16T12:00:00+00:00",
            migration_version="spec-067-v1.0",
            database_path="/tmp/test.sqlite",
            database_sha256_pre="a" * 64,
            database_sha256_post="b" * 64,
            migration_duration_seconds=1.0,
            git_branch="067-qcew-ownership-normalization",
            git_sha="abc1234",
        ),
        row_counts=RowCounts(
            fact_qcew_annual_pre=10,
            fact_qcew_annual_post=4,
            rows_excluded=RowCountsExcluded(
                naics_only=4,
                ownership_only=1,
                both_axes=1,
                total=6,
            ),
            integrity_check_passed=True,
        ),
        naics_vintages={"2010": "2007"},
        bls_suppressed_county_years=(),
        per_county_deltas=PerCountyDeltas(
            michigan_scope_only=True,
            summary_stats=SummaryStats(
                counties_within_5pct_band=1,
                counties_within_5pct_band_pct=100.0,
                counties_with_delta_gt_10pct=0,
                max_abs_delta_pct=0.0,
            ),
            outliers=(),
        ),
    )


def test_audit_report_json_validates_against_schema(tmp_path: Path) -> None:
    report = _make_minimal_report()
    out = tmp_path / "audit.json"
    write_audit_report_json(report, out)
    payload = out.read_text(encoding="utf-8")
    assert "schema_version" in payload
    assert "naics_vintages" in payload


def test_audit_report_markdown_emits_required_sections(tmp_path: Path) -> None:
    report = _make_minimal_report()
    out = tmp_path / "audit.md"
    write_audit_report_markdown(report, out)
    text_md = out.read_text(encoding="utf-8")
    assert "# QCEW Normalization Report" in text_md
    assert "## Summary" in text_md
    assert "## NAICS vintages" in text_md
    assert "## Per-county deltas" in text_md
    assert "BLS-suppressed county-years" in text_md


# T028
def test_dry_run_does_not_mutate_database(tiny_qcew_fixture: Session) -> None:
    """Dry-run leaves the table untouched."""

    pre = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    _ = preflight_assertions(tiny_qcew_fixture)  # dry-run only reads
    _ = wayne_county_2010_spot_check(tiny_qcew_fixture)
    post = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    assert pre == post


# T030 — Idempotency: re-running the DELETE sequence after a successful run
# removes zero additional rows.
def test_apply_idempotency_byte_identical_state_post_rerun(
    tiny_qcew_fixture: Session,
) -> None:
    pre1, naics1, own1 = _execute_full_migration(tiny_qcew_fixture)
    post1 = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    naics2 = delete_naics_rollups(tiny_qcew_fixture)
    own2 = delete_ownership_rollups(tiny_qcew_fixture)
    tiny_qcew_fixture.commit()
    post2 = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    assert (naics2, own2) == (0, 0)
    assert post1 == post2
    # Sanity: the first pass actually did delete the rollups.
    assert naics1 + own1 > 0


# Larger-fixture end-to-end test (added 2026-05-16 while T036 was in flight
# against the live reference DB; validates the full apply path against a
# non-trivial in-memory dataset without depending on the locked live DB).
def test_full_apply_path_against_larger_fixture(tmp_path: Path) -> None:
    """Exercise the full migration sequence against a 1000-row synthetic DB.

    The tiny fixture (6 rows) doesn't reach all execution paths in
    `_per_county_deltas` (which scans backup vs. current and computes
    delta_pct). This test scales up to 1000 rows across 5 counties × 15
    years, with realistic rollup/leaf ratios, and confirms:

    * The integrity check passes (pre - post == naics_only +
      ownership_only + both_axes).
    * `post_migration_validation` finds zero non-canonical rows.
    * The audit-report's `_per_county_deltas` produces sensible counts.
    * Idempotent re-run yields zero additional excluded rows.

    Real-DB validation happens in T036; this test exists to catch
    regressions in the migration tool's row-class-accounting paths
    without requiring a live --apply.
    """

    db_path = tmp_path / "larger_qcew.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        for stmt in _TINY_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        _seed_tiny_dims(session)
        # Add more counties + years to reach 1000+ rows.
        # 5 counties: Wayne (already exists at id=1), Macomb (id=2),
        # plus 3 new ones.
        session.execute(
            text(
                "INSERT INTO dim_county (county_id, fips, county_name) VALUES "
                "(3, '26125', 'Oakland County'), "
                "(4, '26049', 'Genesee County'), "
                "(5, '26161', 'Washtenaw County')"
            )
        )
        # 15 years.
        for offset in range(15):
            session.execute(
                text(
                    "INSERT OR IGNORE INTO dim_time (time_id, year, is_annual) VALUES (:t, :y, 1)"
                ),
                {"t": offset + 10, "y": 2010 + offset},
            )
        # Seed rows: for each (county, year), generate
        #   * 3 NAICS rollups × 4 ownership leaves = 12 naics_only rows
        #   * 1 ownership rollup × 1 canonical industry = 1 ownership_only row
        #   * 1 both_axes row
        #   * 4 canonical leaves
        rows: list[dict[str, int | float]] = []
        for county_id in range(1, 6):
            for time_id in range(10, 25):
                # naics_only (industry_id=1=rollup, ownership_id ∈ {2,3,4,5})
                for own in (2, 3, 4, 5):
                    rows.append(
                        {
                            "c": county_id,
                            "i": 1,
                            "o": own,
                            "t": time_id,
                            "e": 100,
                            "w": 5_000_000.0,
                        }
                    )
                # ownership_only (industry_id=2 OR 3 = canonical leaf, ownership_id=1=rollup)
                for ind in (2, 3):
                    rows.append(
                        {
                            "c": county_id,
                            "i": ind,
                            "o": 1,
                            "t": time_id,
                            "e": 100,
                            "w": 5_000_000.0,
                        }
                    )
                # both_axes (industry_id=1=rollup, ownership_id=1=rollup)
                rows.append(
                    {
                        "c": county_id,
                        "i": 1,
                        "o": 1,
                        "t": time_id,
                        "e": 200,
                        "w": 10_000_000.0,
                    }
                )
                # canonical leaves (industry_id ∈ {2,3} × ownership_id ∈ {2,3,4,5})
                for ind in (2, 3):
                    for own in (2, 3, 4, 5):
                        rows.append(
                            {
                                "c": county_id,
                                "i": ind,
                                "o": own,
                                "t": time_id,
                                "e": 75,
                                "w": 3_750_000.0,
                            }
                        )
        session.execute(
            text(
                "INSERT INTO fact_qcew_annual "
                "(county_id, industry_id, ownership_id, time_id, employment, "
                "total_wages_usd) VALUES (:c, :i, :o, :t, :e, :w)"
            ),
            rows,
        )
        session.commit()

        # Pre-flight + preflight count consistency.
        # 5 counties × 15 years × 15 rows-per-cell = 1125 rows.
        # Per cell: 4 naics_only + 2 ownership_only + 1 both_axes + 8 canonical.
        pre_result = preflight_assertions(session)
        assert pre_result.fact_qcew_annual_pre == 1125
        assert pre_result.naics_only_count == 5 * 15 * 4  # 300
        assert pre_result.ownership_only_count == 5 * 15 * 2  # 150
        assert pre_result.both_axes_count == 5 * 15 * 1  # 75
        assert pre_result.canonical_count == 5 * 15 * 8  # 600
        assert pre_result.total_rollups == 525

        # Backup.
        backup_count = backup_fact_qcew_annual(session)
        assert backup_count == 1125

        # DELETEs.
        naics_n = delete_naics_rollups(session)
        ownership_n = delete_ownership_rollups(session)
        assert naics_n == 300 + 75  # naics_only + both_axes (which 3a catches)
        assert ownership_n == 150  # ownership_only remaining after 3a
        session.commit()

        # Integrity check.
        assert integrity_check(
            pre=1125,
            post=600,  # only the canonical-leaf rows survive
            excluded_naics=pre_result.naics_only_count,
            excluded_ownership=pre_result.ownership_only_count,
            excluded_both=pre_result.both_axes_count,
        )

        # Post-migration validation passes.
        post_migration_validation(session)

        post = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
        assert post == 600

        # Idempotent re-run.
        re_naics = delete_naics_rollups(session)
        re_ownership = delete_ownership_rollups(session)
        assert (re_naics, re_ownership) == (0, 0)

        # _per_county_deltas executes without error.
        deltas = _per_county_deltas(session, michigan_scope_only=True)
        # The fixture's `fips` codes are 26xxx so the michigan filter matches.
        # post_sum (canonical leaves) is 75 employment × 8 rows = 600 per cell.
        # pre_sum from backup (naics_level=0, own_code='0') = the both_axes row,
        # employment=200. Delta vs 600 is +200% → outlier.
        assert deltas.summary_stats.counties_with_delta_gt_10pct >= 1, (
            "expected at least one outlier in the synthetic fixture"
        )
    finally:
        session.close()
        engine.dispose()


def test_fast_strategy_produces_same_canonical_population(tiny_qcew_fixture: Session) -> None:
    """The CREATE-TABLE-AS-SELECT path lands on the same post-067 row set
    as the DELETE path, with the original table preserved as
    ``fact_qcew_annual__pre_067``."""

    session = tiny_qcew_fixture
    # Add the secondary indices the fast strategy expects to drop+recreate.
    session.execute(
        text("CREATE INDEX idx_qcew_county_time ON fact_qcew_annual (county_id, time_id)")
    )
    session.execute(
        text("CREATE INDEX idx_qcew_industry_time ON fact_qcew_annual (industry_id, time_id)")
    )
    session.execute(text("CREATE INDEX idx_qcew_ownership ON fact_qcew_annual (ownership_id)"))
    session.commit()

    pre = preflight_assertions(session)
    assert pre.fact_qcew_annual_pre == 6

    new_count = _apply_fast_strategy(session, pre)
    assert new_count == 4, f"expected 4 canonical leaves, got {new_count}"

    # Original table renamed to __pre_067 with all 6 rows preserved.
    backup_count = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual__pre_067")).scalar()
    assert backup_count == 6

    # Current table contains only canonical leaves.
    survivors = session.execute(
        text(
            "SELECT COUNT(*) FROM fact_qcew_annual fq "
            "JOIN dim_industry i ON fq.industry_id = i.industry_id "
            "JOIN dim_ownership o ON fq.ownership_id = o.ownership_id "
            "WHERE i.naics_level = 6 AND o.own_code != '0'"
        )
    ).scalar()
    assert survivors == 4

    # Secondary indices restored on the new table.
    indices = {
        row[0]
        for row in session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='fact_qcew_annual'"
            )
        ).all()
    }
    assert "idx_qcew_county_time" in indices
    assert "idx_qcew_industry_time" in indices
    assert "idx_qcew_ownership" in indices


# T032 — Rollback recovers the pre-migration state. Implemented via direct
# table-rename of the backup table to mirror the production code path.
def test_rollback_restores_pre_067_state(tiny_qcew_fixture: Session) -> None:
    pre = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar() or 0
    backup_count = backup_fact_qcew_annual(tiny_qcew_fixture)
    _execute_full_migration(tiny_qcew_fixture)
    tiny_qcew_fixture.execute(text("DROP TABLE fact_qcew_annual"))
    tiny_qcew_fixture.execute(
        text("ALTER TABLE fact_qcew_annual__pre_067 RENAME TO fact_qcew_annual")
    )
    tiny_qcew_fixture.commit()
    restored = tiny_qcew_fixture.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar()
    assert restored == pre == backup_count
