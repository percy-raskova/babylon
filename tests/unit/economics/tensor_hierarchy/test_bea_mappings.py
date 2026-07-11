"""Spec 058 / FR-009 — BEAMappings contract tests.

Per the 2026-05-08 commit-7 reformulation: the actual TOML schema is
``{departments: {I: [bea_codes], IIA: [...], IIB: [...], III: [...]}}`` —
4 departments, no per-row weights. The test contract has been adjusted
to match (the original 14-test contract in ``contracts/bea_mappings.md``
was based on a row-array shape that doesn't exist on disk).

Coverage:
  - Production TOML: loads, has all 4 departments, every code unique
  - Synthetic malformed inputs: empty, unknown department, duplicate
    bea_code across departments
  - Frozen invariants: model_copy on frozen model raises
  - Lookup API: get_department + as_flat_dict
  - Equivalence: as_flat_dict matches the legacy
    DefaultDepartmentAggregator.get_default_mapping output
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tensor_hierarchy.mappings import (
    BEA_TO_DEPARTMENT,
    VALID_DEPARTMENTS,
    BEAMappings,
)


@pytest.mark.unit
class TestProductionTOML:
    """Spec 058 SC-009: production fixture loads cleanly + has expected shape."""

    def test_loads_at_import_time(self) -> None:
        """The singleton constructs without error at module import."""
        assert isinstance(BEA_TO_DEPARTMENT, BEAMappings)

    def test_has_all_four_departments(self) -> None:
        """All 4 canonical Marxian departments are present in the TOML."""
        assert set(BEA_TO_DEPARTMENT.departments.keys()) == VALID_DEPARTMENTS

    def test_every_bea_code_unique_across_departments(self) -> None:
        """No BEA code appears in more than one department (validator check)."""
        flat = BEA_TO_DEPARTMENT.as_flat_dict()
        all_codes = [code for codes in BEA_TO_DEPARTMENT.departments.values() for code in codes]
        assert len(all_codes) == len(flat), (
            "as_flat_dict() loses entries — implies duplicate bea_code across departments"
        )

    def test_get_department_round_trips_known_code(self) -> None:
        """Pick the first BEA code from each department; verify lookup."""
        for dept, codes in BEA_TO_DEPARTMENT.departments.items():
            if codes:
                assert BEA_TO_DEPARTMENT.get_department(codes[0]) == dept

    def test_get_department_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="No department mapping for BEA code"):
            BEA_TO_DEPARTMENT.get_department("ZZZ_NEVER_EXISTS")


@pytest.mark.unit
class TestValidation:
    """Synthetic malformed inputs — every invariant fires."""

    def test_empty_departments_rejected(self) -> None:
        with pytest.raises(ValueError, match="must contain at least one department"):
            BEAMappings.model_validate({"departments": {}})

    def test_unknown_department_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown department keys"):
            BEAMappings.model_validate({"departments": {"IV": ["111"]}})

    def test_partial_department_set_accepted(self) -> None:
        """A subset of canonical departments is fine (only the unknown ones fail)."""
        m = BEAMappings.model_validate({"departments": {"I": ["111"], "IIA": ["112"]}})
        assert set(m.departments.keys()) == {"I", "IIA"}

    def test_duplicate_bea_code_across_departments_rejected(self) -> None:
        with pytest.raises(ValueError, match="appears in both"):
            BEAMappings.model_validate(
                {"departments": {"I": ["111"], "IIA": ["111"]}},
            )

    def test_frozen_model_rejects_mutation(self) -> None:
        from pydantic import ValidationError

        with pytest.raises((ValidationError, TypeError)):
            BEA_TO_DEPARTMENT.departments = {}  # type: ignore[misc]


@pytest.mark.unit
class TestLegacyEquivalence:
    """The new typed singleton's flat-dict output MUST match the legacy
    runtime-reparse output exactly (for the inter_industry.py consumer)."""

    def test_as_flat_dict_matches_legacy_aggregator(self) -> None:
        """Drop-in replacement check: BEA_TO_DEPARTMENT.as_flat_dict() ==
        DefaultDepartmentAggregator().get_default_mapping()."""
        from babylon.domain.economics.tensor_hierarchy.inter_industry import (
            DefaultDepartmentAggregator,
        )

        legacy = DefaultDepartmentAggregator().get_default_mapping()
        new = BEA_TO_DEPARTMENT.as_flat_dict()
        assert new == legacy, (
            "BEAMappings.as_flat_dict() drifted from "
            "DefaultDepartmentAggregator.get_default_mapping(); the typed "
            "loader is no longer a drop-in replacement."
        )

    def test_legacy_aggregator_can_consume_typed_dict(self) -> None:
        """Callers of the legacy aggregator's mapping can use BEA_TO_DEPARTMENT
        directly via as_flat_dict() with no other changes."""
        flat = BEA_TO_DEPARTMENT.as_flat_dict()
        # Spot-check: the flat dict shape is dict[str, str] with valid dept values
        assert all(isinstance(k, str) for k in flat)
        assert all(v in VALID_DEPARTMENTS for v in flat.values())
