"""Spec-086 T029: audit-report models + builder math (US3).

RED phase until T031 implements ``babylon_data.qcew.audit``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.qcew import (
    constraint_70_row,
    constraint_71_row,
    leaf_row,
    us_total_row,
    write_mini_singlefile,
)

audit = pytest.importorskip(
    "babylon_data.qcew.audit", reason="babylon-data symlink not resolved (CI)"
)
hierarchy = pytest.importorskip(
    "babylon_data.qcew.hierarchy", reason="babylon-data symlink not resolved (CI)"
)
imputation = pytest.importorskip(
    "babylon_data.qcew.imputation", reason="babylon-data symlink not resolved (CI)"
)
singlefile = pytest.importorskip(
    "babylon_data.qcew.singlefile", reason="babylon-data symlink not resolved (CI)"
)
validation = pytest.importorskip(
    "babylon_data.qcew.validation", reason="babylon-data symlink not resolved (CI)"
)

pytestmark = [pytest.mark.unit, pytest.mark.ledger]

KNOWN_FIPS = {"26163", "26099", "46102", "46113", "09110"}


def _year_entry(tmp_path: Path):  # type: ignore[no-untyped-def]
    rows = [
        constraint_70_row("26163", estabs=12, employment=1000, wages=50_000_000),
        constraint_71_row("26163", "5", estabs=12, employment=1000, wages=50_000_000),
        leaf_row("26163", "5", "336111", estabs=8, employment=700, wages=35_000_000),
        leaf_row("26163", "5", "336112", estabs=4, suppressed=True),
        # Suppressed-70 county → low-confidence:
        constraint_70_row("26099", estabs=2, employment=0, wages=0, suppressed=True),
        constraint_71_row("26099", "5", estabs=2, employment=200, wages=8_000_000),
        leaf_row("26099", "5", "541511", estabs=2, employment=200, wages=8_000_000),
        # Excluded pseudo-area with published mass (national check term):
        leaf_row("26999", "5", "336111", estabs=1, employment=50, wages=1_000_000),
        us_total_row(estabs=15, employment=1250, wages=59_000_000),
    ]
    path = write_mini_singlefile(tmp_path, 2010, rows)
    year_data = singlefile.read_singlefile(path, year=2010, known_county_fips=KNOWN_FIPS)
    trees = hierarchy.trees_from_year_data(year_data)
    results = {fips: imputation.impute_county(tree) for fips, tree in trees.items()}
    reconciliation = validation.reconcile_results(results)
    return audit.build_year_entry(year_data, results, reconciliation), year_data


class TestYearEntry:
    def test_suppression_accounting(self, tmp_path: Path) -> None:
        entry, _ = _year_entry(tmp_path)
        assert entry.suppression.leaf_cells == 3
        assert entry.suppression.suppressed_cells == 1
        assert entry.suppression.exact_recovery == 1
        assert (
            entry.suppression.exact_recovery
            + entry.suppression.estabs_apportioned
            + entry.suppression.equal_split
            + entry.suppression.zero_negative_remainder
            == entry.suppression.suppressed_cells
        )
        assert entry.suppression.suppression_rate == pytest.approx(1 / 3)

    def test_exclusion_counters(self, tmp_path: Path) -> None:
        entry, _ = _year_entry(tmp_path)
        assert entry.excluded.ss999_unknown_county == 1
        assert entry.excluded.us_national == 0

    def test_low_confidence_mapping(self, tmp_path: Path) -> None:
        entry, _ = _year_entry(tmp_path)
        flagged = {
            item.county_fips: item.reason
            for item in entry.reconciliation.low_confidence_county_years
        }
        assert flagged == {"26099": "county_total_suppressed"}

    def test_national_check_math(self, tmp_path: Path) -> None:
        entry, _ = _year_entry(tmp_path)
        national = entry.national_check
        # counties: 26163 → 1000, 26099 → 200; excluded published SS999 mass 50.
        assert national.sum_counties_employment == 1200
        assert national.excluded_pseudo_mass_employment == 50
        assert national.bls_us000_employment == 1250
        assert national.delta_pct == pytest.approx(0.0)
        assert national.pass_ is True

    def test_reconciliation_distribution(self, tmp_path: Path) -> None:
        entry, _ = _year_entry(tmp_path)
        reconciliation = entry.reconciliation
        assert reconciliation.counties == 2
        assert reconciliation.within_2pct_employment == 2
        assert reconciliation.residual_abs_pct.max == pytest.approx(0.0)


class TestReportRoundTrip:
    def test_to_json_from_json(self, tmp_path: Path) -> None:
        entry, year_data = _year_entry(tmp_path)
        report = audit.QcewImputeAuditReport(
            schema_version="1.0.0",
            run_metadata=audit.RunMetadata(
                timestamp_utc="2026-07-02T18:00:00Z",
                mode="dry-run",
                years=[2010],
                database_path="/tmp/x.sqlite",
                database_sha256_pre="0" * 64,
                database_sha256_post="0" * 64,
                duration_seconds=1.5,
                babylon_git=audit.GitRef(branch="b", sha="a" * 7),
                babylon_data_git=audit.GitRef(branch="main", sha="b" * 7),
                table_hashes=audit.TableHashes(
                    fact_qcew_annual="c" * 64, fact_qcew_county_rollup="d" * 64
                ),
            ),
            per_year=[entry],
            identity_resolutions=audit.IdentityResolutions(
                shannon_to_oglala_rows=0,
                shannon_2015_duplicates_dropped=0,
                ct_2024_planning_regions=False,
            ),
            sc_gates=audit.ScGates(),
        )
        payload = report.to_json()
        restored = audit.QcewImputeAuditReport.from_json(payload)
        assert restored.per_year[0].year == 2010
        assert restored.run_metadata.mode == "dry-run"
