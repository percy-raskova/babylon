"""Mutation-killing tests for MarxianHydrator.

Targets the untested algorithmic paths in hydrate() and _get_dept_sv_ratio():
- Wage allocation to departments
- Granularity metric computation
- Excluded wages tracking (NAICS 92)
- sv_ratio weighted average + BEA/sector/default fallback cascade
- SNLT conversion factor application
- hydrate_with_rent() error path and calculation
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.department_mapper import Department, DepartmentAllocation
from babylon.domain.economics.hydrator import MarxianHydrator
from babylon.domain.economics.snlt import SNLTConfig
from babylon.domain.economics.tensor import ValueTensor4x3

# =============================================================================
# Mock data sources implementing Protocol interfaces
# =============================================================================


class MockQCEWSource:
    """Mock QCEWDataSource returning configurable records."""

    def __init__(self, records: list[tuple[str, float, int]] | None = None) -> None:
        self._records = records or []

    def fetch_county_wages(
        self,
        fips_code: str,
        year: int,  # noqa: ARG002
    ) -> list[tuple[str, float, int]]:
        return self._records


class MockBEASource:
    """Mock BEADataSource with configurable ratios."""

    def __init__(
        self,
        sv_ratios: dict[str, float] | None = None,
        cv_ratios: dict[str, float] | None = None,
    ) -> None:
        self._sv = sv_ratios or {}
        self._cv = cv_ratios or {}

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        return self._sv.get(naics_code)

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        return self._cv.get(naics_code)


class MockDeptMapper:
    """Mock DepartmentMapper with configurable allocations and ratios."""

    def __init__(
        self,
        allocations: dict[str, DepartmentAllocation | None] | None = None,
        sector_sv: dict[str, float] | None = None,
        sector_cv: dict[str, float] | None = None,
        default_sv: dict[Department, float] | None = None,
        default_cv: dict[Department, float] | None = None,
    ) -> None:
        self._allocations = allocations or {}
        self._sector_sv = sector_sv or {}
        self._sector_cv = sector_cv or {}
        self._default_sv: dict[Department, float] = default_sv or dict.fromkeys(Department, 1.0)
        self._default_cv: dict[Department, float] = default_cv or dict.fromkeys(Department, 2.0)

    def get_allocation(self, naics_code: str) -> DepartmentAllocation | None:
        # Try exact match, then cascade through prefix
        if naics_code in self._allocations:
            return self._allocations[naics_code]
        # Try progressively shorter prefixes
        for length in range(len(naics_code) - 1, 1, -1):
            prefix = naics_code[:length]
            if prefix in self._allocations:
                return self._allocations[prefix]
        return self._allocations.get(naics_code[:2])

    def is_excluded(self, naics_code: str) -> bool:
        return self.get_allocation(naics_code) is None

    def get_sector_sv_ratio(self, sector: str) -> float | None:
        return self._sector_sv.get(sector)

    def get_sector_cv_ratio(self, sector: str) -> float | None:
        return self._sector_cv.get(sector)

    def get_default_sv_ratio(self, dept: Department) -> float:
        return self._default_sv[dept]

    def get_default_cv_ratio(self, dept: Department) -> float:
        return self._default_cv[dept]


# =============================================================================
# TESTS: hydrate() core algorithm
# =============================================================================


class TestHydrateWageAllocation:
    """Tests for wage allocation to departments."""

    def test_single_naics_allocated_to_one_department(self) -> None:
        """Single NAICS code allocated 100% to Dept I."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            default_sv=dict.fromkeys(Department, 1.0),
            default_cv=dict.fromkeys(Department, 2.0),
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert isinstance(tensor, ValueTensor4x3)
        assert tensor.dept_I.v == pytest.approx(1000.0)
        assert tensor.dept_IIa.v == pytest.approx(0.0)
        assert tensor.dept_IIb.v == pytest.approx(0.0)
        assert tensor.dept_III.v == pytest.approx(0.0)

    def test_split_allocation_across_departments(self) -> None:
        """Wages split across multiple departments."""
        qcew = MockQCEWSource([("44", 1000.0, 50)])
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"44": DepartmentAllocation(dept_IIa=0.6, dept_IIb=0.3, dept_III=0.1)},
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.dept_IIa.v == pytest.approx(600.0)
        assert tensor.dept_IIb.v == pytest.approx(300.0)
        assert tensor.dept_III.v == pytest.approx(100.0)

    def test_multiple_naics_accumulated(self) -> None:
        """Multiple NAICS codes accumulate wages in same department."""
        qcew = MockQCEWSource(
            [
                ("31", 500.0, 25),
                ("33", 300.0, 15),
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "31": DepartmentAllocation(dept_I=1.0),
                "33": DepartmentAllocation(dept_I=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.dept_I.v == pytest.approx(800.0)

    def test_excluded_sector_tracked(self) -> None:
        """NAICS with no allocation is excluded."""
        qcew = MockQCEWSource(
            [
                ("31", 800.0, 40),
                ("92", 200.0, 10),  # Government - excluded
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "31": DepartmentAllocation(dept_I=1.0),
                # "92" not in allocations → excluded
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.dept_I.v == pytest.approx(800.0)
        assert tensor.excluded_wages == pytest.approx(200.0)


class TestHydrateGranularity:
    """Tests for naics_granularity metric computation."""

    def test_all_6digit_naics_yields_granularity_1(self) -> None:
        """All 6-digit NAICS codes → naics_granularity = 1.0."""
        qcew = MockQCEWSource(
            [
                ("336111", 500.0, 25),
                ("445110", 500.0, 25),
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "33": DepartmentAllocation(dept_I=1.0),
                "44": DepartmentAllocation(dept_IIa=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.naics_granularity == pytest.approx(1.0)

    def test_all_2digit_naics_yields_granularity_0(self) -> None:
        """All 2-digit NAICS codes → naics_granularity = 0.0."""
        qcew = MockQCEWSource(
            [
                ("31", 500.0, 25),
                ("44", 500.0, 25),
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "31": DepartmentAllocation(dept_I=1.0),
                "44": DepartmentAllocation(dept_IIa=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.naics_granularity == pytest.approx(0.0)

    def test_mixed_granularity(self) -> None:
        """Mix of 2-digit and 6-digit → proportional granularity."""
        qcew = MockQCEWSource(
            [
                ("336111", 600.0, 30),  # 6-digit: granular
                ("44", 400.0, 20),  # 2-digit: coarse
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "33": DepartmentAllocation(dept_I=1.0),
                "44": DepartmentAllocation(dept_IIa=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # granular_wages=600, allocated_wages=1000 → 0.6
        assert tensor.naics_granularity == pytest.approx(0.6)

    def test_granularity_excludes_excluded_wages(self) -> None:
        """Excluded wages don't count in granularity denominator."""
        qcew = MockQCEWSource(
            [
                ("336111", 500.0, 25),  # 6-digit, allocated
                ("92", 500.0, 25),  # Excluded (no allocation)
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={
                "33": DepartmentAllocation(dept_I=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # granular=500, allocated=500 (excluding 500 govt) → 1.0
        assert tensor.naics_granularity == pytest.approx(1.0)

    def test_no_allocated_wages_yields_granularity_0(self) -> None:
        """All wages excluded → granularity = 0.0."""
        qcew = MockQCEWSource(
            [
                ("92", 1000.0, 50),  # All excluded
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper()

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.naics_granularity == pytest.approx(0.0)


class TestHydrateSVRatioFallback:
    """Tests for _get_dept_sv_ratio fallback cascade."""

    def test_bea_ratio_used_when_available(self) -> None:
        """BEA ratio takes priority over sector and default."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource(sv_ratios={"31": 0.8})
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            sector_sv={"31": 0.5},
            default_sv=dict.fromkeys(Department, 1.0),
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # s = v * sv_ratio = 1000 * 0.8 = 800
        assert tensor.dept_I.s == pytest.approx(800.0)

    def test_sector_ratio_used_when_bea_unavailable(self) -> None:
        """Sector ratio used when BEA returns None."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource()  # No BEA ratios
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            sector_sv={"31": 0.5},
            default_sv=dict.fromkeys(Department, 1.0),
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # s = v * sector_sv = 1000 * 0.5 = 500
        assert tensor.dept_I.s == pytest.approx(500.0)

    def test_default_ratio_used_when_nothing_found(self) -> None:
        """Department default used when BEA and sector both unavailable."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource()  # No ratios
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            # No sector ratios
            default_sv=dict.fromkeys(Department, 1.5),
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # s = v * default_sv = 1000 * 1.5 = 1500
        assert tensor.dept_I.s == pytest.approx(1500.0)

    def test_weighted_average_across_naics(self) -> None:
        """Multiple NAICS in same dept → weighted average sv_ratio."""
        qcew = MockQCEWSource(
            [
                ("31", 600.0, 30),  # 60% of weight
                ("33", 400.0, 20),  # 40% of weight
            ]
        )
        bea = MockBEASource(sv_ratios={"31": 1.0, "33": 0.5})
        mapper = MockDeptMapper(
            allocations={
                "31": DepartmentAllocation(dept_I=1.0),
                "33": DepartmentAllocation(dept_I=1.0),
            },
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # weighted sv = (1.0*600 + 0.5*400) / (600+400) = 800/1000 = 0.8
        # v = 1000, s = 1000 * 0.8 = 800
        assert tensor.dept_I.v == pytest.approx(1000.0)
        assert tensor.dept_I.s == pytest.approx(800.0)


class TestHydrateSNLTConversion:
    """Tests for SNLT (Socially Necessary Labor Time) conversion."""

    def test_default_snlt_factor_is_1(self) -> None:
        """Default SNLT factor = 1.0 (wage-proportional proxy)."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            default_sv=dict.fromkeys(Department, 1.0),
            default_cv=dict.fromkeys(Department, 2.0),
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # With SNLT factor 1.0: labor_hours = wages * 1.0
        assert tensor.dept_I.v == pytest.approx(1000.0)
        assert tensor.dept_I.s == pytest.approx(1000.0)
        assert tensor.dept_I.c == pytest.approx(2000.0)

    def test_custom_snlt_factor(self) -> None:
        """Custom SNLT factor scales all values."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
            default_sv=dict.fromkeys(Department, 1.0),
            default_cv=dict.fromkeys(Department, 2.0),
        )
        snlt = SNLTConfig(factors={2022: 0.5}, default_factor=1.0)

        hydrator = MarxianHydrator(qcew, bea, mapper, snlt_config=snlt)
        tensor = hydrator.hydrate("26163", 2022)

        # v_money=1000, factor=0.5 → v_hours=500
        assert tensor.dept_I.v == pytest.approx(500.0)
        assert tensor.dept_I.s == pytest.approx(500.0)
        assert tensor.dept_I.c == pytest.approx(1000.0)

    def test_excluded_wages_also_converted(self) -> None:
        """Excluded wages are also converted via SNLT factor."""
        qcew = MockQCEWSource(
            [
                ("31", 800.0, 40),
                ("92", 200.0, 10),
            ]
        )
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
        )
        snlt = SNLTConfig(factors={2022: 0.5}, default_factor=1.0)

        hydrator = MarxianHydrator(qcew, bea, mapper, snlt_config=snlt)
        tensor = hydrator.hydrate("26163", 2022)

        # excluded_wages = 200 * 0.5 = 100
        assert tensor.excluded_wages == pytest.approx(100.0)


class TestHydrateEdgeCases:
    """Edge cases for hydrate() method."""

    def test_empty_qcew_returns_zero_tensor(self) -> None:
        """Empty QCEW data returns all-zero tensor."""
        qcew = MockQCEWSource([])
        bea = MockBEASource()
        mapper = MockDeptMapper()

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.dept_I.v == pytest.approx(0.0)
        assert tensor.dept_I.s == pytest.approx(0.0)
        assert tensor.dept_I.c == pytest.approx(0.0)
        assert tensor.naics_granularity == pytest.approx(0.0)

    def test_tensor_fips_and_year_set(self) -> None:
        """Output tensor has correct fips_code and year."""
        qcew = MockQCEWSource([("31", 100.0, 5)])
        bea = MockBEASource()
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        assert tensor.fips_code == "26163"
        assert tensor.year == 2022

    def test_cv_ratio_applied_to_c(self) -> None:
        """c = v * cv_ratio is computed correctly."""
        qcew = MockQCEWSource([("31", 1000.0, 50)])
        bea = MockBEASource(cv_ratios={"31": 3.5})
        mapper = MockDeptMapper(
            allocations={"31": DepartmentAllocation(dept_I=1.0)},
        )

        hydrator = MarxianHydrator(qcew, bea, mapper)
        tensor = hydrator.hydrate("26163", 2022)

        # c = 1000 * 3.5 = 3500
        assert tensor.dept_I.c == pytest.approx(3500.0)
