"""DB-probe tier of the data-catalog sentinel (Program 21, refdata lane).

Reconciles ``data-catalog.yaml`` against the actual reference database:
no undeclared objects, no phantom rows, no dark KEEP objects. The synthetic-row
efficacy test pins the ``view_surplus_value`` pathology (a consumed view over
an EMPTY base table, Constitution III.11) as a regression contract — the exact
defect the 2026-07-16 census found shipping.

Requires the reference DB (full local copy or the ci-data subset); the module
is skipped wherever the DB is absent.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.coverage.catalog import CatalogTable
from babylon.sentinels.coverage.db_probe import (
    _database_path,
    check_catalog_db_reconciliation,
    check_subset_view_absence,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.requires_reference_db,
    pytest.mark.skipif(
        not _database_path().is_file(),
        reason="reference DB absent (fetch-reference-db not run / drive unmounted)",
    ),
]

_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestRealCatalogAgainstRealDb:
    """The shipped catalog reconciles cleanly with the shipped DB."""

    def test_reconciliation_clean(self) -> None:
        assert check_catalog_db_reconciliation() == []

    def test_subset_view_absence_is_advisory_shape(self) -> None:
        findings = check_subset_view_absence()
        # Full DB → no findings; subset DB → exactly one advisory naming the
        # unchecked view-row count. Either way, never a hard failure.
        assert len(findings) <= 1

    def test_cli_catalog_check_exits_clean(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sentinel_check.py"), "catalog", "--check"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"catalog sentinel red:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


class TestEfficacy:
    """Injected defects red; broken infrastructure raises (exit-2 class)."""

    def test_empty_keep_view_reds_the_surplus_value_pathology(self, tmp_path: Path) -> None:
        # Regression contract: a KEEP view over an EMPTY base table must red —
        # the exact pathology the 2026-07-16 census found shipping. The real
        # fact_productivity_annual has been FILLED since (2026-07-17, ruling 1),
        # so the scenario is reconstructed in a synthetic mini-DB: the guard
        # must keep catching what the census caught, forever.
        mini_db = tmp_path / "pathology.sqlite"
        conn = sqlite3.connect(mini_db)
        conn.execute("CREATE TABLE fact_productivity_annual (industry_id INTEGER)")
        conn.execute(
            "CREATE VIEW view_surplus_value AS SELECT industry_id FROM fact_productivity_annual"
        )
        conn.commit()
        conn.close()
        synthetic_base = CatalogTable(
            name="fact_productivity_annual",
            kind="table",
            source="BLS_Productivity",
            disposition="fill",  # declared debt — must NOT trip the keep-emptiness law itself
            subset_policy="skip",
            material_relation="empty base reconstructing the census pathology",
        )
        synthetic_view = CatalogTable(
            name="view_surplus_value",
            kind="view",
            source="derived",
            reads=("fact_productivity_annual",),
            disposition="keep",
            subset_policy="skip",
            material_relation="s/v rate of exploitation by industry",
        )
        violations = check_catalog_db_reconciliation(
            catalog=(synthetic_base, synthetic_view), db_path=mini_db
        )
        assert any("view_surplus_value" in v and "EMPTY" in v for v in violations), (
            f"expected the empty-base-table violation, got: {violations[:5]}"
        )

    def test_skip_policy_table_absent_from_subset_env_is_exempt(self, tmp_path: Path) -> None:
        # A skip-policy table is BY DESIGN absent from the ci-data subset
        # (view-less DB). In a full environment (views present) the same
        # absence IS a phantom. Both directions pinned.
        skip_row = CatalogTable(
            name="fact_hpms_road_segment",
            kind="table",
            source="HPMS",
            disposition="investigate",
            subset_policy="skip",
            material_relation="efficacy probe: skip-policy subset absence",
        )
        subset_db = tmp_path / "subset.sqlite"
        conn = sqlite3.connect(subset_db)
        conn.execute("CREATE TABLE fact_present (id INTEGER)")  # no views => subset env
        conn.commit()
        conn.close()
        present_row = CatalogTable(
            name="fact_present",
            kind="table",
            source="internal",
            disposition="investigate",
            subset_policy="full",
            material_relation="efficacy probe companion",
        )
        assert (
            check_catalog_db_reconciliation(catalog=(skip_row, present_row), db_path=subset_db)
            == []
        )
        full_db = tmp_path / "full.sqlite"
        conn = sqlite3.connect(full_db)
        conn.execute("CREATE TABLE fact_present (id INTEGER)")
        conn.execute("CREATE VIEW view_marker AS SELECT id FROM fact_present")
        conn.commit()
        conn.close()
        view_row = CatalogTable(
            name="view_marker",
            kind="view",
            source="derived",
            reads=("fact_present",),
            disposition="investigate",
            subset_policy="skip",
            material_relation="efficacy probe view marker",
        )
        violations = check_catalog_db_reconciliation(
            catalog=(skip_row, present_row, view_row), db_path=full_db
        )
        assert any("fact_hpms_road_segment" in v and "phantom" in v for v in violations)

    def test_phantom_row_reds(self) -> None:
        # full-policy: a skip-policy absence is legitimately exempt in subset
        # environments (see the dedicated test above), so the phantom probe
        # must use a policy that promises presence everywhere.
        phantom = CatalogTable(
            name="fact_absolutely_not_a_table",
            kind="table",
            source="internal",
            disposition="investigate",
            subset_policy="full",
            material_relation="efficacy probe",
        )
        violations = check_catalog_db_reconciliation(catalog=(phantom,))
        assert any("phantom" in v for v in violations)

    def test_missing_db_is_loud(self, tmp_path: Path) -> None:
        with pytest.raises(SentinelCheckError):
            check_catalog_db_reconciliation(db_path=tmp_path / "nope.sqlite")
