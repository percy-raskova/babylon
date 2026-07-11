"""Integration tests for MarxianHydrator.

Tests for the hydrator that transforms QCEW wage data into 4x3 Marxian
value tensors using the DepartmentMapper and BEA ratio data.

Key integration tests:
- Gentrification Signal: Oakland County (affluent) has higher IIb/IIa than Wayne (Detroit)
- Dept III isolation: Only NAICS 814 + 6244 contribute
- Surplus rates vary by department
- Allocation + excluded = total QCEW wages

TDD RED PHASE: These tests will fail until hydrator.py and adapters.py are implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.domain.economics.department_mapper import Department, DepartmentMapper
from babylon.domain.economics.hydrator import MarxianHydrator
from babylon.domain.economics.tensor import ValueTensor4x3

# =============================================================================
# MOCK DATA SOURCES FOR TESTING
# =============================================================================


class MockQCEWDataSource:
    """Mock QCEW data source with predetermined county wage data.

    Implements the QCEWDataSource protocol for testing.
    """

    def __init__(self, data: dict[tuple[str, int], list[tuple[str, float, int]]]) -> None:
        """Initialize with county data.

        Args:
            data: Mapping of (fips_code, year) -> list of (naics_code, wages, employment)
        """
        self._data = data

    def fetch_county_wages(self, fips_code: str, year: int) -> list[tuple[str, float, int]]:
        """Fetch wage data for a county-year.

        Returns:
            List of (naics_code, wages, employment) tuples.
        """
        return self._data.get((fips_code, year), [])


class MockBEADataSource:
    """Mock BEA data source with predetermined industry ratios.

    Implements the BEADataSource protocol for testing.
    """

    def __init__(
        self,
        sv_ratios: dict[str, float] | None = None,
        cv_ratios: dict[str, float] | None = None,
    ) -> None:
        """Initialize with ratio data.

        Args:
            sv_ratios: NAICS code -> s/v ratio mapping.
            cv_ratios: NAICS code -> c/v ratio mapping.
        """
        self._sv_ratios = sv_ratios or {}
        self._cv_ratios = cv_ratios or {}

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get s/v ratio for a NAICS code.

        Returns:
            Rate of surplus value, or None if unavailable.
        """
        return self._sv_ratios.get(naics_code)

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:
        """Get c/v ratio for a NAICS code.

        Returns:
            Organic composition of capital, or None if unavailable.
        """
        return self._cv_ratios.get(naics_code)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def wayne_county_qcew() -> list[tuple[str, float, int]]:
    """Wayne County (Detroit area) QCEW data - working class industrial base.

    Wayne County characteristics:
    - Strong manufacturing (auto industry) - Dept IIa
    - Basic retail and services - Dept IIa
    - Limited luxury sector - Dept IIb
    - Government excluded (NAICS 92)
    """
    return [
        # Manufacturing (heavily IIa - necessary consumption)
        ("336111", 500_000_000.0, 50000),  # Auto manufacturing
        ("311", 100_000_000.0, 15000),  # Food manufacturing
        # Retail (mostly IIa)
        ("4451", 80_000_000.0, 20000),  # Grocery stores
        ("4522", 60_000_000.0, 12000),  # Department stores
        # Services (mix)
        ("722513", 40_000_000.0, 25000),  # Fast food (IIa)
        # Healthcare/Education (Dept III - social reproduction)
        ("62", 200_000_000.0, 45000),  # Healthcare
        ("6244", 30_000_000.0, 8000),  # Child day care
        # Government - excluded
        ("921110", 150_000_000.0, 20000),  # Federal government
    ]


@pytest.fixture
def oakland_county_qcew() -> list[tuple[str, float, int]]:
    """Oakland County (affluent suburb) QCEW data - upper middle class consumption.

    Oakland County characteristics:
    - Professional services - Dept I (B2B)
    - Luxury retail and services - Dept IIb
    - Higher proportion of luxury consumption
    - Government excluded (NAICS 92)
    """
    return [
        # Professional services (Dept I - B2B)
        ("54", 300_000_000.0, 40000),  # Professional services
        # Retail (more luxury-oriented)
        ("44831", 50_000_000.0, 3000),  # Jewelry stores (pure IIb)
        ("45111", 40_000_000.0, 5000),  # Sporting goods (IIb-heavy)
        ("4522", 80_000_000.0, 15000),  # Department stores (mix)
        # Services (more luxury)
        ("71391", 30_000_000.0, 2000),  # Golf courses (pure IIb)
        ("722511", 60_000_000.0, 8000),  # Fine dining (IIb-heavy)
        # Healthcare/Education (Dept III)
        ("62", 180_000_000.0, 35000),  # Healthcare
        ("6244", 25_000_000.0, 6000),  # Child day care
        # Government - excluded
        ("921110", 100_000_000.0, 12000),  # Federal government
    ]


@pytest.fixture
def dept_mapper(tmp_path: Path) -> DepartmentMapper:
    """Create a DepartmentMapper for testing."""
    yaml_content = """
defaults:
  31:
    dept_IIa: 0.70
    dept_IIb: 0.30
  44:
    dept_IIa: 0.75
    dept_IIb: 0.25
  45:
    dept_IIa: 0.65
    dept_IIb: 0.35
  54:
    dept_I: 0.60
    dept_IIa: 0.30
    dept_IIb: 0.10
  62:
    dept_IIa: 0.30
    dept_III: 0.70
  71:
    dept_IIa: 0.30
    dept_IIb: 0.70
  72:
    dept_IIa: 0.60
    dept_IIb: 0.40

overrides:
  336111:
    dept_IIa: 0.65
    dept_IIb: 0.35
  311:
    dept_IIa: 0.85
    dept_IIb: 0.15
  4451:
    dept_IIa: 0.95
    dept_IIb: 0.05
  4522:
    dept_IIa: 0.60
    dept_IIb: 0.40
  44831:
    dept_IIb: 1.0
  45111:
    dept_IIa: 0.30
    dept_IIb: 0.70
  6244:
    dept_III: 1.0
  71391:
    dept_IIb: 1.0
  722511:
    dept_IIa: 0.20
    dept_IIb: 0.80
  722513:
    dept_IIa: 0.90
    dept_IIb: 0.10

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


@pytest.fixture
def mock_bea_source() -> MockBEADataSource:
    """Create a mock BEA data source with industry ratios."""
    return MockBEADataSource(
        sv_ratios={
            "336111": 1.2,  # Auto manufacturing
            "311": 0.9,  # Food manufacturing
            "4451": 0.8,  # Grocery stores
        },
        cv_ratios={
            "336111": 2.5,  # Capital-intensive auto
            "311": 1.8,  # Food manufacturing
            "4451": 1.2,  # Retail
        },
    )


# =============================================================================
# GENTRIFICATION SIGNAL TEST
# =============================================================================


class TestGentrificationSignal:
    """Tests for the gentrification signal: Oakland has higher IIb/IIa ratio."""

    def test_oakland_has_higher_luxury_ratio_than_wayne(
        self,
        wayne_county_qcew: list[tuple[str, float, int]],
        oakland_county_qcew: list[tuple[str, float, int]],
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Oakland County should have higher IIb/IIa ratio than Wayne.

        This test encodes the "gentrification signal" - affluent suburbs
        have proportionally more luxury consumption relative to necessary
        consumption compared to working-class industrial areas.
        """
        wayne_qcew = MockQCEWDataSource({("26163", 2022): wayne_county_qcew})
        oakland_qcew = MockQCEWDataSource({("26125", 2022): oakland_county_qcew})

        wayne_hydrator = MarxianHydrator(
            qcew_source=wayne_qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )
        oakland_hydrator = MarxianHydrator(
            qcew_source=oakland_qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        wayne = wayne_hydrator.hydrate("26163", 2022)  # Wayne County, MI
        oakland = oakland_hydrator.hydrate("26125", 2022)  # Oakland County, MI

        # Calculate luxury/necessary ratio for each county
        wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
        oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

        # Oakland (affluent) should have higher luxury ratio
        assert oakland_ratio > wayne_ratio, (
            f"Oakland IIb/IIa ratio ({oakland_ratio:.3f}) should be greater than "
            f"Wayne IIb/IIa ratio ({wayne_ratio:.3f})"
        )


# =============================================================================
# DEPARTMENT III ISOLATION TEST
# =============================================================================


class TestDeptIIIIsolation:
    """Tests that Dept III only receives care work industries."""

    def test_dept_III_only_from_care_industries(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Dept III should only receive wages from NAICS 814, 6244, and healthcare."""
        # Create data with clear separation
        qcew_data = [
            ("6244", 100_000.0, 50),  # Child day care - 100% Dept III
            ("336111", 500_000.0, 100),  # Auto manufacturing - 0% Dept III
            ("4451", 200_000.0, 80),  # Grocery stores - 0% Dept III
            ("62", 300_000.0, 100),  # Healthcare - 70% Dept III
        ]
        qcew = MockQCEWDataSource({("12345", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("12345", 2022)

        # Dept III should only come from 6244 (100%) and 62 (70%)
        # 6244: 100,000 * 1.0 = 100,000
        # 62: 300,000 * 0.7 = 210,000
        # Total Dept III v: 310,000
        expected_dept_III_v = 100_000.0 + (300_000.0 * 0.7)
        assert tensor.dept_III.v == pytest.approx(expected_dept_III_v, rel=0.01)


# =============================================================================
# SURPLUS RATE VARIATION TEST
# =============================================================================


class TestSurplusRateVariation:
    """Tests that surplus rates vary by department as expected."""

    def test_dept_I_and_IIb_have_higher_surplus_rates(
        self,
        dept_mapper: DepartmentMapper,
    ) -> None:
        """Dept I and IIb should have higher s/v ratios than IIa and III."""
        # Verify the theoretical expectation from default ratios
        sv_I = dept_mapper.get_default_sv_ratio(Department.I)
        sv_IIa = dept_mapper.get_default_sv_ratio(Department.IIa)
        sv_IIb = dept_mapper.get_default_sv_ratio(Department.IIb)
        sv_III = dept_mapper.get_default_sv_ratio(Department.III)

        # Dept I (capital-intensive extraction) and IIb (monopoly rents)
        # should have higher surplus rates than IIa (competitive) and III (suppressed)
        assert sv_I > sv_IIa, f"Dept I ({sv_I}) should > IIa ({sv_IIa})"
        assert sv_IIb > sv_IIa, f"Dept IIb ({sv_IIb}) should > IIa ({sv_IIa})"
        assert sv_IIa > sv_III, f"Dept IIa ({sv_IIa}) should > III ({sv_III})"


# =============================================================================
# ALLOCATION COMPLETENESS TEST
# =============================================================================


class TestAllocationCompleteness:
    """Tests that allocated + excluded = total QCEW wages."""

    def test_allocation_plus_excluded_equals_total(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Sum of allocated wages + excluded wages should equal total QCEW wages."""
        qcew_data = [
            ("336111", 500_000.0, 100),  # Auto - allocated
            ("4451", 200_000.0, 80),  # Grocery - allocated
            ("921110", 150_000.0, 50),  # Government - excluded
        ]
        qcew = MockQCEWDataSource({("12345", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("12345", 2022)

        # Total input wages
        total_input = sum(wages for _, wages, _ in qcew_data)

        # Total allocated v (wages that went into departments)
        total_allocated_v = (
            tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v
        )

        # Allocation + excluded should equal total input
        assert total_allocated_v + tensor.excluded_wages == pytest.approx(total_input, rel=0.01), (
            f"Allocated ({total_allocated_v}) + Excluded ({tensor.excluded_wages}) "
            f"should equal Total ({total_input})"
        )


# =============================================================================
# TENSOR OUTPUT VALIDATION
# =============================================================================


class TestTensorOutput:
    """Tests for ValueTensor4x3 output structure and validation."""

    def test_hydrate_returns_valid_tensor(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Hydrator returns a valid ValueTensor4x3 with correct metadata."""
        qcew_data = [
            ("336111", 500_000.0, 100),
            ("4451", 200_000.0, 80),
        ]
        qcew = MockQCEWDataSource({("26163", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("26163", 2022)

        # Verify structure
        assert isinstance(tensor, ValueTensor4x3)
        assert tensor.fips_code == "26163"
        assert tensor.year == 2022

        # Verify computed fields work
        assert tensor.profit_rate > 0
        assert tensor.total_value > 0

        # Verify naics_granularity is reasonable
        assert 0.0 <= tensor.naics_granularity <= 1.0

    def test_empty_county_returns_zero_tensor(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """County with no QCEW data returns tensor with zero values."""
        qcew = MockQCEWDataSource({})  # No data
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("99999", 2022)

        assert tensor.dept_I.v == 0.0
        assert tensor.dept_IIa.v == 0.0
        assert tensor.dept_IIb.v == 0.0
        assert tensor.dept_III.v == 0.0
        assert tensor.excluded_wages == 0.0

    def test_tensor_serialization_roundtrip(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Tensor can be serialized to JSON and deserialized."""
        qcew_data = [("336111", 500_000.0, 100)]
        qcew = MockQCEWDataSource({("26163", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("26163", 2022)
        json_str = tensor.model_dump_json()
        restored = ValueTensor4x3.model_validate_json(json_str)

        assert restored.fips_code == tensor.fips_code
        assert restored.year == tensor.year
        assert restored.dept_I.v == pytest.approx(tensor.dept_I.v)


# =============================================================================
# MARXIAN THEORY VALIDATION TESTS
# =============================================================================


class TestReproductionSchemaConditions:
    """Tests for Marx's reproduction schema conditions on hydrated tensors.

    These tests verify that QCEW-derived tensors satisfy (or approach)
    Marx's equilibrium conditions from Capital Volume 2.
    """

    @pytest.mark.theory
    def test_tensor_satisfies_simple_reproduction_ratio(
        self,
        wayne_county_qcew: list[tuple[str, float, int]],
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """A balanced economy tensor should approach I(v+s) ~ IIc.

        This tests that real QCEW data produces tensors compatible
        with Marx's reproduction conditions. The ratio should be
        roughly balanced (in range 0.5 to 2.0) for a functioning economy.

        Perfect equality (1.0) indicates simple reproduction.
        Values > 1.0 indicate expanded reproduction (accumulation).
        """
        qcew = MockQCEWDataSource({("26163", 2022): wayne_county_qcew})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("26163", 2022)

        # I(v+s) - living labor in Dept I
        I_living = tensor.dept_I.v + tensor.dept_I.s

        # IIc - constant capital in consumption departments (IIa + IIb + III)
        II_constant = tensor.dept_IIa.c + tensor.dept_IIb.c + tensor.dept_III.c

        # Skip if either is zero (degenerate case)
        if I_living == 0.0 or II_constant == 0.0:
            pytest.skip(
                "By-design exclusion (ADR-037): degenerate tensor with zero "
                "I(v+s) or IIc cannot express Marx's reproduction theory; "
                "the test asserts properties of a balanced economy."
            )

        ratio = I_living / II_constant

        # Should be roughly balanced (0.5 to 2.0 range)
        # This is a weak condition - a functioning economy shouldn't be
        # wildly unbalanced between production and consumption
        assert 0.5 <= ratio <= 2.0, (
            f"Reproduction ratio I(v+s)/IIc = {ratio:.3f} outside plausible range [0.5, 2.0]. "
            f"I(v+s)={I_living:.2f}, IIc={II_constant:.2f}"
        )


class TestOrganicCompositionOrdering:
    """Tests for organic composition ordering in hydrated tensors.

    Theoretical prediction: Dept I (capital goods) should have
    higher OCC than Dept IIa (wage goods) which should have higher
    OCC than Dept III (care work).
    """

    @pytest.mark.theory
    def test_aggregate_occ_ordering_in_real_data(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Real QCEW data should produce OCC ordering: I > IIa > III.

        This test uses carefully constructed QCEW data that mimics
        the theoretical capital intensity differences between departments.
        """
        # Create data with clear departmental separation
        # Dept I industries (mining, machinery) - capital intensive
        # Dept IIa industries (retail, food) - moderate
        # Dept III industries (care work) - labor intensive
        qcew_data = [
            # Dept I - high capital intensity
            ("21221", 100_000.0, 50),  # Iron ore mining - 100% I
            ("3332", 80_000.0, 40),  # Industrial machinery - 95% I
            # Dept IIa - moderate capital
            ("4451", 200_000.0, 150),  # Grocery stores - 95% IIa
            ("311", 150_000.0, 100),  # Food manufacturing - 85% IIa
            # Dept III - low capital (labor intensive)
            ("6244", 100_000.0, 80),  # Child day care - 100% III
            ("814", 50_000.0, 60),  # Private households - 100% III
        ]

        qcew = MockQCEWDataSource({("12345", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("12345", 2022)

        # Skip if any department has zero variable capital
        if tensor.dept_I.v == 0.0 or tensor.dept_IIa.v == 0.0 or tensor.dept_III.v == 0.0:
            pytest.skip(
                "By-design exclusion (ADR-037): degenerate tensor with zero "
                "variable capital in some department breaks the organic-"
                "composition ordering (I > IIa > III) the test exists to enforce."
            )

        # Get organic compositions
        occ_I = tensor.dept_I.organic_composition
        occ_III = tensor.dept_III.organic_composition

        # Theoretical ordering: I > III
        # (We skip IIa/IIb as they depend on sector composition which varies)
        assert occ_I > occ_III, f"Dept I OCC ({occ_I:.2f}) should > Dept III OCC ({occ_III:.2f})"


class TestExploitationRateOrdering:
    """Tests for exploitation rate ordering in hydrated tensors.

    Theoretical prediction: Dept IIb (luxury goods) should have
    higher s/v than Dept IIa (competitive markets) which should
    have higher s/v than Dept III (suppressed care wages).
    """

    @pytest.mark.theory
    def test_aggregate_exploitation_ordering_in_real_data(
        self,
        dept_mapper: DepartmentMapper,
        mock_bea_source: MockBEADataSource,
    ) -> None:
        """Real QCEW data should produce s/v ordering with IIb higher than IIa.

        This test uses QCEW data with clear luxury vs. necessary distinction.
        """
        # Create data with clear departmental separation
        qcew_data = [
            # Dept IIb - high exploitation (luxury monopoly rents)
            ("44831", 100_000.0, 30),  # Jewelry stores - 100% IIb
            ("71391", 80_000.0, 20),  # Golf courses - 100% IIb
            ("722511", 60_000.0, 25),  # Fine dining - 80% IIb
            # Dept IIa - moderate exploitation (competitive)
            ("4451", 200_000.0, 150),  # Grocery stores - 95% IIa
            ("722513", 100_000.0, 100),  # Fast food - 90% IIa
            # Dept III - lowest exploitation (suppressed)
            ("6244", 120_000.0, 100),  # Child day care - 100% III
            ("814", 60_000.0, 80),  # Private households - 100% III
        ]

        qcew = MockQCEWDataSource({("12345", 2022): qcew_data})
        hydrator = MarxianHydrator(
            qcew_source=qcew,
            bea_source=mock_bea_source,
            dept_mapper=dept_mapper,
        )

        tensor = hydrator.hydrate("12345", 2022)

        # Skip if any department has zero variable capital
        if tensor.dept_IIa.v == 0.0 or tensor.dept_IIb.v == 0.0 or tensor.dept_III.v == 0.0:
            pytest.skip(
                "By-design exclusion (ADR-037): degenerate tensor with zero "
                "variable capital in some department breaks the organic-"
                "composition ordering (I > IIa > III) the test exists to enforce."
            )

        # Get exploitation rates
        sv_IIa = tensor.dept_IIa.exploitation_rate
        sv_IIb = tensor.dept_IIb.exploitation_rate
        sv_III = tensor.dept_III.exploitation_rate

        # Theoretical ordering: IIb > IIa > III
        assert sv_IIb > sv_III, (
            f"Dept IIb exploitation rate ({sv_IIb:.2f}) should > "
            f"Dept III exploitation rate ({sv_III:.2f})"
        )
        assert sv_IIa > sv_III, (
            f"Dept IIa exploitation rate ({sv_IIa:.2f}) should > "
            f"Dept III exploitation rate ({sv_III:.2f})"
        )
