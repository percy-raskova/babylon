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

    def test_empty_keep_view_reds_the_surplus_value_pathology(self) -> None:
        # Regression contract: a KEEP view over the (still-empty)
        # fact_productivity_annual must red. The shipped catalog carries the
        # honest disposition instead; this synthetic row proves the guard
        # would have caught the pathology the census found.
        synthetic = CatalogTable(
            name="view_surplus_value",
            kind="view",
            source="derived",
            reads=("fact_productivity_annual",),
            disposition="keep",
            subset_policy="skip",
            material_relation="s/v rate of exploitation by industry",
        )
        violations = check_catalog_db_reconciliation(catalog=(synthetic,))
        assert any("view_surplus_value" in v and "EMPTY" in v for v in violations), (
            f"expected the empty-base-table violation, got: {violations[:5]}"
        )

    def test_phantom_row_reds(self) -> None:
        phantom = CatalogTable(
            name="fact_absolutely_not_a_table",
            kind="table",
            source="internal",
            disposition="investigate",
            subset_policy="skip",
            material_relation="efficacy probe",
        )
        violations = check_catalog_db_reconciliation(catalog=(phantom,))
        assert any("phantom" in v for v in violations)

    def test_missing_db_is_loud(self, tmp_path: Path) -> None:
        with pytest.raises(SentinelCheckError):
            check_catalog_db_reconciliation(db_path=tmp_path / "nope.sqlite")
