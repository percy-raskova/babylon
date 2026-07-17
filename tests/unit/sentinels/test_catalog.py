"""Tests for the data-catalog registry sentinel (Program 21, Data Constitution).

Two tiers, per the sentinel contract:

- **Invariant** — the real ``data-catalog.yaml`` ``tables:`` block loads into
  frozen :class:`CatalogTable` rows, every declared consumer/test path exists,
  and every base table's ``subset_policy`` matches the
  ``tools/make_reference_subset.py`` ``TABLE`` policy dict (two SoTs, one truth).
- **Efficacy** — the sensor REDS on injected defects (phantom consumer path,
  subset-policy mismatch) and raises :class:`SentinelCheckError` loudly on a
  missing/unparseable catalog (infrastructure failure, never a false pass).

This module is **purely static** (fast-gate tier): it never opens the reference
DB. The DB-probe tier (undeclared tables, empty-under-consumed-view) lives in
``tests/integration/reference/test_catalog_db.py`` behind
``requires_reference_db``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.coverage.catalog import (
    CatalogTable,
    load_catalog_tables,
    subset_policy_map,
)
from babylon.sentinels.coverage.checks import (
    check_catalog_paths_exist,
    check_subset_policy_parity,
)

pytestmark = pytest.mark.unit


def _row(**overrides: object) -> CatalogTable:
    """Build a valid baseline row, then apply per-test overrides."""
    base: dict[str, object] = {
        "name": "fact_example",
        "kind": "table",
        "source": "QCEW",
        "disposition": "keep",
        "subset_policy": "full",
        "material_relation": "example relation",
    }
    base.update(overrides)
    return CatalogTable(**base)  # type: ignore[arg-type]


class TestCatalogTableModel:
    """Loud-at-construction shape validation (Constitution III.11)."""

    def test_valid_row_constructs_frozen(self) -> None:
        row = _row()
        assert row.name == "fact_example"
        with pytest.raises(ValidationError):
            row.name = "mutated"  # type: ignore[misc]

    def test_blank_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="name"):
            _row(name="   ")

    def test_blank_material_relation_rejected(self) -> None:
        with pytest.raises(ValidationError, match="material_relation"):
            _row(material_relation="")

    def test_view_requires_reads(self) -> None:
        with pytest.raises(ValidationError, match="reads"):
            _row(name="view_example", kind="view", reads=())

    def test_table_must_not_declare_reads(self) -> None:
        with pytest.raises(ValidationError, match="reads"):
            _row(reads=("fact_other",))

    def test_view_subset_policy_must_be_skip(self) -> None:
        # Views are never copied into ci-data subsets (the generator copies
        # type='table' only) — any other policy claim is a lie.
        with pytest.raises(ValidationError, match="skip"):
            _row(
                name="view_example",
                kind="view",
                reads=("fact_example",),
                subset_policy="full",
            )

    def test_non_py_consumer_rejected(self) -> None:
        with pytest.raises(ValidationError, match="consumers"):
            _row(consumers=("src/babylon/notes.txt",))

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CatalogTable(  # type: ignore[call-arg]
                name="fact_example",
                kind="table",
                source="QCEW",
                disposition="keep",
                subset_policy="full",
                material_relation="x",
                bogus_field=1,
            )


class TestRealCatalogInvariants:
    """The shipped data-catalog.yaml satisfies its own contract."""

    def test_catalog_loads_and_is_populated(self) -> None:
        rows = load_catalog_tables()
        assert len(rows) >= 99, "expected the full census backfill (99 tables + views)"
        names = {r.name for r in rows}
        assert "fact_qcew_annual" in names
        assert "view_surplus_value" in names

    def test_real_catalog_paths_coherent(self) -> None:
        assert check_catalog_paths_exist() == []

    def test_real_subset_policy_parity(self) -> None:
        assert check_subset_policy_parity() == []

    def test_no_duplicate_names(self) -> None:
        rows = load_catalog_tables()
        names = [r.name for r in rows]
        assert len(names) == len(set(names))


class TestEfficacy:
    """Injected defects red; broken infrastructure raises (exit-2 class)."""

    def test_phantom_consumer_path_reds(self) -> None:
        bad = _row(consumers=("src/babylon/does_not_exist_anywhere.py",))
        violations = check_catalog_paths_exist(catalog=(bad,))
        assert len(violations) == 1
        assert "does_not_exist_anywhere" in violations[0]

    def test_phantom_test_path_reds(self) -> None:
        bad = _row(tests=("tests/unit/reference/no_such_test_file.py",))
        violations = check_catalog_paths_exist(catalog=(bad,))
        assert len(violations) == 1

    def test_subset_policy_mismatch_reds(self) -> None:
        # fact_qcew_annual is 'michigan' in the generator's TABLE dict; a
        # catalog row claiming 'skip' is drift between the two SoTs.
        bad = _row(name="fact_qcew_annual", subset_policy="skip")
        violations = check_subset_policy_parity(catalog=(bad,))
        assert len(violations) == 1
        assert "fact_qcew_annual" in violations[0]

    def test_unknown_table_in_catalog_reds_parity(self) -> None:
        bad = _row(name="fact_never_heard_of_it")
        violations = check_subset_policy_parity(catalog=(bad,))
        assert len(violations) == 1

    def test_missing_catalog_file_is_loud(self, tmp_path: Path) -> None:
        with pytest.raises(SentinelCheckError):
            load_catalog_tables(path=tmp_path / "no-such-catalog.yaml")

    def test_unparseable_catalog_is_loud(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.yaml"
        bad.write_text("tables: [unclosed", encoding="utf-8")
        with pytest.raises(SentinelCheckError):
            load_catalog_tables(path=bad)

    def test_catalog_without_tables_block_is_loud(self, tmp_path: Path) -> None:
        legacy = tmp_path / "legacy.yaml"
        legacy.write_text("version: '2.6.3'\ncategories: []\n", encoding="utf-8")
        with pytest.raises(SentinelCheckError, match="tables"):
            load_catalog_tables(path=legacy)


class TestSubsetPolicyMap:
    """The AST parse of the generator's TABLE dict yields the real policies."""

    def test_known_scopes(self) -> None:
        policies = subset_policy_map()
        assert policies["dim_asset_category"] == "full"
        assert policies["fact_qcew_annual"] == "michigan"
        assert len(policies) >= 90
