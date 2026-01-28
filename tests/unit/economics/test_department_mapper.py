"""Unit tests for DepartmentMapper and related classes.

Tests for NAICS-to-Marxian-department mapping including:
- DepartmentAllocation weight validation
- Hierarchical NAICS lookup (6-digit to 2-digit fallback)
- Excluded sectors (government NAICS 92)
- Default BEA ratios (cv_ratio, sv_ratio) for each department

TDD RED PHASE: These tests will fail until department_mapper.py is implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# These imports will fail until we implement the module (RED phase)
from babylon.economics.department_mapper import (
    Department,
    DepartmentAllocation,
    DepartmentMapper,
)

if TYPE_CHECKING:
    pass


class TestDepartment:
    """Tests for Department enum."""

    def test_department_enum_values(self) -> None:
        """Department enum has four values matching Marxian reproduction schema."""
        assert Department.I.value == "dept_I"
        assert Department.IIa.value == "dept_IIa"
        assert Department.IIb.value == "dept_IIb"
        assert Department.III.value == "dept_III"

    def test_department_str_representation(self) -> None:
        """Department __str__ returns name without 'dept_' prefix."""
        assert str(Department.I) == "I"
        assert str(Department.IIa) == "IIa"
        assert str(Department.IIb) == "IIb"
        assert str(Department.III) == "III"


class TestDepartmentAllocation:
    """Tests for DepartmentAllocation dataclass."""

    def test_create_valid_allocation_single_department(self) -> None:
        """Allocation with 100% to one department is valid."""
        alloc = DepartmentAllocation(dept_I=1.0)
        assert alloc.dept_I == 1.0
        assert alloc.dept_IIa == 0.0
        assert alloc.dept_IIb == 0.0
        assert alloc.dept_III == 0.0

    def test_create_valid_allocation_split(self) -> None:
        """Allocation split across departments summing to 1.0 is valid."""
        alloc = DepartmentAllocation(dept_I=0.3, dept_IIa=0.4, dept_IIb=0.2, dept_III=0.1)
        assert alloc.dept_I == 0.3
        assert alloc.dept_IIa == 0.4

    def test_weights_must_sum_to_one(self) -> None:
        """Allocation weights must sum to 1.0 within tolerance."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            DepartmentAllocation(dept_I=0.5, dept_IIa=0.3)  # Sum = 0.8

    def test_weights_tolerance_allows_small_deviation(self) -> None:
        """Weights summing to 0.999 or 1.001 are accepted (0.001 tolerance)."""
        # Should not raise
        DepartmentAllocation(dept_I=0.5, dept_IIa=0.4999)  # Sum = 0.9999

    def test_allocation_is_frozen(self) -> None:
        """DepartmentAllocation is immutable."""
        alloc = DepartmentAllocation(dept_I=1.0)
        with pytest.raises(AttributeError):
            alloc.dept_I = 0.5  # type: ignore[misc]

    def test_allocate_distributes_value(self) -> None:
        """allocate() distributes a value according to weights."""
        alloc = DepartmentAllocation(dept_I=0.3, dept_IIa=0.4, dept_IIb=0.2, dept_III=0.1)
        result = alloc.allocate(1_000_000.0)

        assert result[Department.I] == pytest.approx(300_000.0)
        assert result[Department.IIa] == pytest.approx(400_000.0)
        assert result[Department.IIb] == pytest.approx(200_000.0)
        assert result[Department.III] == pytest.approx(100_000.0)

    def test_allocate_zero_value(self) -> None:
        """allocate(0) returns zeros for all departments."""
        alloc = DepartmentAllocation(dept_I=0.5, dept_IIa=0.5)
        result = alloc.allocate(0.0)

        assert all(v == 0.0 for v in result.values())

    def test_from_dict_creates_allocation(self) -> None:
        """from_dict() creates allocation from dictionary."""
        d = {"dept_I": 0.6, "dept_IIa": 0.4}
        alloc = DepartmentAllocation.from_dict(d)

        assert alloc.dept_I == 0.6
        assert alloc.dept_IIa == 0.4
        assert alloc.dept_IIb == 0.0
        assert alloc.dept_III == 0.0

    def test_to_dict_returns_weights(self) -> None:
        """to_dict() returns weights as dictionary."""
        alloc = DepartmentAllocation(dept_I=0.3, dept_IIa=0.4, dept_IIb=0.2, dept_III=0.1)
        d = alloc.to_dict()

        assert d == {"dept_I": 0.3, "dept_IIa": 0.4, "dept_IIb": 0.2, "dept_III": 0.1}


class TestDepartmentMapperLookup:
    """Tests for DepartmentMapper NAICS lookup behavior."""

    @pytest.fixture
    def simple_mapper(self) -> DepartmentMapper:
        """Mapper with a simple 2-digit default and one override."""
        defaults = {
            "31": DepartmentAllocation(dept_IIa=1.0),  # Manufacturing -> IIa
            "11": DepartmentAllocation(dept_I=0.5, dept_IIa=0.5),  # Agriculture
        }
        overrides = {
            "336111": DepartmentAllocation(dept_IIa=0.65, dept_IIb=0.35),  # Automobile Mfg
            "3361": DepartmentAllocation(dept_IIa=0.7, dept_IIb=0.3),  # Motor Vehicles
        }
        excluded = {"92"}  # Government
        return DepartmentMapper(
            defaults=defaults,
            overrides=overrides,
            excluded=excluded,
        )

    def test_exact_6digit_match(self, simple_mapper: DepartmentMapper) -> None:
        """6-digit NAICS code matches exact override."""
        alloc = simple_mapper.get_allocation("336111")
        assert alloc is not None
        assert alloc.dept_IIa == 0.65
        assert alloc.dept_IIb == 0.35

    def test_4digit_match(self, simple_mapper: DepartmentMapper) -> None:
        """4-digit NAICS code matches 4-digit override."""
        alloc = simple_mapper.get_allocation("3361")
        assert alloc is not None
        assert alloc.dept_IIa == 0.7
        assert alloc.dept_IIb == 0.3

    def test_hierarchical_fallback_to_4digit(self, simple_mapper: DepartmentMapper) -> None:
        """6-digit code without exact match falls back to 4-digit."""
        alloc = simple_mapper.get_allocation("336199")  # Other motor vehicle
        assert alloc is not None
        assert alloc.dept_IIa == 0.7  # 4-digit override
        assert alloc.dept_IIb == 0.3

    def test_hierarchical_fallback_to_2digit(self, simple_mapper: DepartmentMapper) -> None:
        """NAICS code without override falls back to 2-digit default."""
        alloc = simple_mapper.get_allocation("315220")  # Apparel Mfg
        assert alloc is not None
        assert alloc.dept_IIa == 1.0  # 2-digit default for 31

    def test_excluded_sector_returns_none(self, simple_mapper: DepartmentMapper) -> None:
        """Excluded sectors (e.g., government) return None."""
        alloc = simple_mapper.get_allocation("921110")  # Federal government
        assert alloc is None

    def test_excluded_2digit_prefix(self, simple_mapper: DepartmentMapper) -> None:
        """Exclusion by 2-digit prefix works."""
        alloc = simple_mapper.get_allocation("92")
        assert alloc is None

    def test_is_excluded_true(self, simple_mapper: DepartmentMapper) -> None:
        """is_excluded() returns True for excluded codes."""
        assert simple_mapper.is_excluded("92") is True
        assert simple_mapper.is_excluded("921110") is True

    def test_is_excluded_false(self, simple_mapper: DepartmentMapper) -> None:
        """is_excluded() returns False for non-excluded codes."""
        assert simple_mapper.is_excluded("336111") is False
        assert simple_mapper.is_excluded("11") is False

    def test_unknown_sector_returns_none(self, simple_mapper: DepartmentMapper) -> None:
        """Unknown sector (no default or override) returns None."""
        alloc = simple_mapper.get_allocation("99")  # Nonexistent sector
        assert alloc is None


class TestDepartmentMapperAllocateMethods:
    """Tests for DepartmentMapper allocate methods."""

    @pytest.fixture
    def mapper(self) -> DepartmentMapper:
        """Mapper for allocation tests."""
        defaults = {
            "31": DepartmentAllocation(dept_IIa=1.0),
        }
        overrides = {
            "336111": DepartmentAllocation(dept_IIa=0.65, dept_IIb=0.35),
        }
        excluded = {"92"}
        return DepartmentMapper(defaults=defaults, overrides=overrides, excluded=excluded)

    def test_allocate_value_success(self, mapper: DepartmentMapper) -> None:
        """allocate_value() distributes value for valid NAICS code."""
        result = mapper.allocate_value("336111", 1_000_000.0)
        assert result is not None
        assert result[Department.IIa] == pytest.approx(650_000.0)
        assert result[Department.IIb] == pytest.approx(350_000.0)

    def test_allocate_value_excluded_returns_none(self, mapper: DepartmentMapper) -> None:
        """allocate_value() returns None for excluded sector."""
        result = mapper.allocate_value("921110", 1_000_000.0)
        assert result is None

    def test_allocate_batch_sums_departments(self, mapper: DepartmentMapper) -> None:
        """allocate_batch() sums allocations across records."""
        records = [
            ("336111", 1_000_000.0),  # 650k IIa, 350k IIb
            ("315220", 500_000.0),  # 500k IIa (2-digit default)
        ]
        result = mapper.allocate_batch(records)

        assert result[Department.IIa] == pytest.approx(1_150_000.0)
        assert result[Department.IIb] == pytest.approx(350_000.0)
        assert result[Department.I] == pytest.approx(0.0)
        assert result[Department.III] == pytest.approx(0.0)

    def test_allocate_batch_skips_excluded(self, mapper: DepartmentMapper) -> None:
        """allocate_batch() skips excluded sectors."""
        records = [
            ("336111", 1_000_000.0),
            ("921110", 500_000.0),  # Excluded - should be skipped
        ]
        result = mapper.allocate_batch(records)

        # Only 336111 should be allocated
        assert result[Department.IIa] == pytest.approx(650_000.0)
        assert result[Department.IIb] == pytest.approx(350_000.0)


class TestDepartmentMapperDefaultRatios:
    """Tests for default c/v and s/v ratios per department.

    These ratios are used when BEA data is unavailable.
    """

    @pytest.fixture
    def mapper_with_ratios(self, tmp_path: Path) -> DepartmentMapper:
        """Create mapper with default_ratios configuration."""
        yaml_content = """
defaults:
  31:
    dept_IIa: 1.0

overrides:
  336111:
    dept_IIa: 0.65
    dept_IIb: 0.35

excluded:
  - "92"

default_ratios:
  dept_I:
    cv_ratio: 3.0
    sv_ratio: 2.0
  dept_IIa:
    cv_ratio: 1.5
    sv_ratio: 1.0
  dept_IIb:
    cv_ratio: 2.5
    sv_ratio: 3.0
  dept_III:
    cv_ratio: 0.5
    sv_ratio: 0.7
"""
        config_file = tmp_path / "naics_to_dept.yaml"
        config_file.write_text(yaml_content)
        return DepartmentMapper.from_yaml(config_file)

    def test_get_default_cv_ratio_dept_I(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_cv_ratio returns c/v ratio for Department I."""
        ratio = mapper_with_ratios.get_default_cv_ratio(Department.I)
        assert ratio == pytest.approx(3.0)

    def test_get_default_cv_ratio_dept_IIa(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_cv_ratio returns c/v ratio for Department IIa."""
        ratio = mapper_with_ratios.get_default_cv_ratio(Department.IIa)
        assert ratio == pytest.approx(1.5)

    def test_get_default_cv_ratio_dept_IIb(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_cv_ratio returns c/v ratio for Department IIb."""
        ratio = mapper_with_ratios.get_default_cv_ratio(Department.IIb)
        assert ratio == pytest.approx(2.5)

    def test_get_default_cv_ratio_dept_III(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_cv_ratio returns c/v ratio for Department III."""
        ratio = mapper_with_ratios.get_default_cv_ratio(Department.III)
        assert ratio == pytest.approx(0.5)

    def test_get_default_sv_ratio_dept_I(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_sv_ratio returns s/v ratio for Department I."""
        ratio = mapper_with_ratios.get_default_sv_ratio(Department.I)
        assert ratio == pytest.approx(2.0)

    def test_get_default_sv_ratio_dept_IIa(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_sv_ratio returns s/v ratio for Department IIa."""
        ratio = mapper_with_ratios.get_default_sv_ratio(Department.IIa)
        assert ratio == pytest.approx(1.0)

    def test_get_default_sv_ratio_dept_IIb(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_sv_ratio returns s/v ratio for Department IIb."""
        ratio = mapper_with_ratios.get_default_sv_ratio(Department.IIb)
        assert ratio == pytest.approx(3.0)

    def test_get_default_sv_ratio_dept_III(self, mapper_with_ratios: DepartmentMapper) -> None:
        """get_default_sv_ratio returns s/v ratio for Department III."""
        ratio = mapper_with_ratios.get_default_sv_ratio(Department.III)
        assert ratio == pytest.approx(0.7)


class TestDepartmentMapperYAML:
    """Tests for DepartmentMapper YAML loading."""

    def test_from_yaml_loads_config(self, tmp_path: Path) -> None:
        """from_yaml() loads configuration from YAML file."""
        yaml_content = """
defaults:
  31:
    dept_IIa: 1.0
  11:
    dept_I: 0.5
    dept_IIa: 0.5

overrides:
  336111:
    dept_IIa: 0.65
    dept_IIb: 0.35

excluded:
  - "92"
  - "99"

default_ratios:
  dept_I:
    cv_ratio: 3.0
    sv_ratio: 2.0
  dept_IIa:
    cv_ratio: 1.5
    sv_ratio: 1.0
  dept_IIb:
    cv_ratio: 2.5
    sv_ratio: 3.0
  dept_III:
    cv_ratio: 0.5
    sv_ratio: 0.7
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        mapper = DepartmentMapper.from_yaml(config_file)

        # Verify defaults loaded
        alloc = mapper.get_allocation("31")
        assert alloc is not None
        assert alloc.dept_IIa == 1.0

        # Verify overrides loaded
        alloc = mapper.get_allocation("336111")
        assert alloc is not None
        assert alloc.dept_IIa == 0.65

        # Verify excluded loaded
        assert mapper.is_excluded("92") is True
        assert mapper.is_excluded("99") is True

        # Verify ratios loaded
        assert mapper.get_default_cv_ratio(Department.I) == 3.0
        assert mapper.get_default_sv_ratio(Department.IIb) == 3.0
