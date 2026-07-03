"""Unit tests for Marxian reproduction schema theory validation.

Tests validating that our 4x3 Marxian value tensor formulation adheres to
Marx's original theories from Capital Volume 2, Chapters 20-21.

Theoretical Foundation:
    - Simple Reproduction (Ch. 20): I(v+s) = IIc
    - Expanded Reproduction (Ch. 21): I(v+s) > IIc
    - Value Decomposition: c + v + s = total_value
    - Organic Composition: c/v ordering by capital intensity
    - Exploitation Rate: s/v ordering by market power

Sources:
    - https://www.marxists.org/archive/marx/works/1885-c2/ch20_02.htm
    - https://www.marxists.org/archive/marx/works/1885-c2/ch21_01.htm

See Also:
    :mod:`babylon.economics.tensor`: ValueTensor4x3 implementation.
    :mod:`tests.constants`: MarxReproductionExamples constants.
"""

from __future__ import annotations

import pytest

from babylon.economics.department_mapper import DefaultRatios, Department, DepartmentMapper
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
from tests.constants import TestConstants

TC = TestConstants
Marx = TC.MarxReproduction


# =============================================================================
# REPRODUCTION EQUILIBRIUM TESTS
# =============================================================================


class TestReproductionEquilibrium:
    """Tests for Marx's reproduction equilibrium conditions.

    From Capital Vol. 2, Chapter 20: The fundamental exchange between
    departments determines the conditions for reproduction.
    """

    @pytest.mark.theory
    def test_simple_reproduction_equilibrium_condition(self) -> None:
        """Verify I(v+s) = IIc for simple reproduction.

        From Capital Vol. 2, Ch. 20: 'the entire constant capital-value of II
        re-appearing in articles of consumption gets replaced through exchange
        with the variable capital-value I reproduced during the year and the
        newly produced surplus-value I.'

        In simple reproduction, the value created by living labor in Dept I
        equals the constant capital needed by Dept II.
        """
        # Construct a tensor matching Marx's simple reproduction example
        tensor = ValueTensor4x3(
            fips_code="00000",
            year=2022,
            dept_I=DepartmentRow(c=Marx.SIMPLE_I_C, v=Marx.SIMPLE_I_V, s=Marx.SIMPLE_I_S),
            dept_IIa=DepartmentRow(c=Marx.SIMPLE_IIA_C, v=Marx.SIMPLE_IIA_V, s=Marx.SIMPLE_IIA_S),
            dept_IIb=DepartmentRow(c=Marx.SIMPLE_IIB_C, v=Marx.SIMPLE_IIB_V, s=Marx.SIMPLE_IIB_S),
            dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),  # Not in Marx's original
            naics_granularity=1.0,
            excluded_wages=0.0,
        )

        # I(v+s) = living labor created in Dept I
        I_living_labor = tensor.dept_I.v + tensor.dept_I.s

        # IIc = constant capital needed by Dept II (IIa + IIb + III)
        II_constant_capital = tensor.dept_IIa.c + tensor.dept_IIb.c + tensor.dept_III.c

        # Simple reproduction equilibrium: I(v+s) = IIc
        assert I_living_labor == pytest.approx(II_constant_capital), (
            f"Simple reproduction requires I(v+s) = IIc: {I_living_labor} != {II_constant_capital}"
        )

    @pytest.mark.theory
    def test_expanded_reproduction_requires_surplus(self) -> None:
        """Verify I(v+s) > IIc for expanded reproduction.

        From Capital Vol. 2, Ch. 21: 'I(v + s) cannot be equal to IIc'
        under capitalist production with accumulation.

        In expanded reproduction, Dept I produces more means of production
        than Dept II needs to replace its constant capital, allowing
        accumulation of additional capital stock.
        """
        # Construct a tensor matching Marx's expanded reproduction example
        tensor = ValueTensor4x3(
            fips_code="00000",
            year=2022,
            dept_I=DepartmentRow(c=Marx.EXPAND_I_C, v=Marx.EXPAND_I_V, s=Marx.EXPAND_I_S),
            dept_IIa=DepartmentRow(
                c=Marx.EXPAND_II_C * 0.8,  # 80% of II is IIa (necessities)
                v=Marx.EXPAND_II_V * 0.8,
                s=Marx.EXPAND_II_S * 0.8,
            ),
            dept_IIb=DepartmentRow(
                c=Marx.EXPAND_II_C * 0.2,  # 20% of II is IIb (luxuries)
                v=Marx.EXPAND_II_V * 0.2,
                s=Marx.EXPAND_II_S * 0.2,
            ),
            dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),
            naics_granularity=1.0,
            excluded_wages=0.0,
        )

        I_living_labor = tensor.dept_I.v + tensor.dept_I.s
        II_constant_capital = tensor.dept_IIa.c + tensor.dept_IIb.c + tensor.dept_III.c

        # Expanded reproduction: I(v+s) > IIc
        assert I_living_labor > II_constant_capital, (
            f"Expanded reproduction requires I(v+s) > IIc: "
            f"{I_living_labor} should be > {II_constant_capital}"
        )

    @pytest.mark.theory
    @pytest.mark.parametrize(
        "dept_name,row",
        [
            ("I", DepartmentRow(c=Marx.SIMPLE_I_C, v=Marx.SIMPLE_I_V, s=Marx.SIMPLE_I_S)),
            ("IIa", DepartmentRow(c=Marx.SIMPLE_IIA_C, v=Marx.SIMPLE_IIA_V, s=Marx.SIMPLE_IIA_S)),
            ("IIb", DepartmentRow(c=Marx.SIMPLE_IIB_C, v=Marx.SIMPLE_IIB_V, s=Marx.SIMPLE_IIB_S)),
        ],
        ids=["dept_I", "dept_IIa", "dept_IIb"],
    )
    def test_value_decomposition_invariant(self, dept_name: str, row: DepartmentRow) -> None:
        """Verify c + v + s = total_value for every department.

        This is the fundamental value decomposition invariant from
        Marx's labor theory of value. Every commodity's value decomposes
        into dead labor (c), living labor (v), and unpaid labor (s).
        """
        expected_total = row.c + row.v + row.s
        assert row.total_value == pytest.approx(expected_total), (
            f"Dept {dept_name}: c + v + s = {expected_total} != total_value = {row.total_value}"
        )

    @pytest.mark.theory
    def test_profit_rate_formula(self) -> None:
        """Verify r = s/(c+v) matches Marx's formulation.

        The rate of profit is the ratio of surplus value to total
        capital advanced (constant + variable capital).
        """
        row = DepartmentRow(c=400.0, v=100.0, s=100.0)

        # Marx's formula: r = s / (c + v)
        expected_rate = row.s / (row.c + row.v)

        # Use tensor to compute aggregate profit rate
        tensor = ValueTensor4x3(
            fips_code="00000",
            year=2022,
            dept_I=row,
            dept_IIa=row,
            dept_IIb=row,
            dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),
            naics_granularity=1.0,
            excluded_wages=0.0,
        )

        # With identical departments, aggregate rate = individual rate
        assert tensor.profit_rate == pytest.approx(expected_rate)


# =============================================================================
# MARX'S NUMERICAL EXAMPLES TESTS
# =============================================================================


class TestMarxNumericalExamples:
    """Tests validating Marx's exact numerical examples from Capital Vol. 2."""

    @pytest.mark.theory
    def test_marx_simple_reproduction_example(self) -> None:
        """Validate Marx's exact numerical example from Capital Vol. 2, Ch. 20.

        I:  4000c + 1000v + 1000s = 6000
        II: 2000c +  500v +  500s = 3000
        Total: 9000
        """
        dept_I = DepartmentRow(c=Marx.SIMPLE_I_C, v=Marx.SIMPLE_I_V, s=Marx.SIMPLE_I_S)
        dept_II = DepartmentRow(c=Marx.SIMPLE_II_C, v=Marx.SIMPLE_II_V, s=Marx.SIMPLE_II_S)

        # Verify department totals
        assert dept_I.total_value == pytest.approx(Marx.SIMPLE_I_TOTAL)
        assert dept_II.total_value == pytest.approx(Marx.SIMPLE_II_TOTAL)

        # Verify economy total
        total = dept_I.total_value + dept_II.total_value
        assert total == pytest.approx(Marx.SIMPLE_TOTAL_VALUE)

    @pytest.mark.theory
    def test_marx_iia_iib_subdivision(self) -> None:
        """Validate Marx's IIa/IIb split from Chapter 20.

        IIa: 1600c + 400v + 400s = 2400 (necessities)
        IIb:  400c + 100v + 100s =  600 (luxuries)
        Ratio: IIb/IIa = 0.25 (25% luxury consumption)
        """
        dept_IIa = DepartmentRow(c=Marx.SIMPLE_IIA_C, v=Marx.SIMPLE_IIA_V, s=Marx.SIMPLE_IIA_S)
        dept_IIb = DepartmentRow(c=Marx.SIMPLE_IIB_C, v=Marx.SIMPLE_IIB_V, s=Marx.SIMPLE_IIB_S)

        # Verify subdivision totals
        assert dept_IIa.total_value == pytest.approx(Marx.SIMPLE_IIA_TOTAL)
        assert dept_IIb.total_value == pytest.approx(Marx.SIMPLE_IIB_TOTAL)

        # Verify IIa + IIb = II
        assert dept_IIa.total_value + dept_IIb.total_value == pytest.approx(Marx.SIMPLE_II_TOTAL)

        # Verify luxury ratio
        luxury_ratio = dept_IIb.total_value / Marx.SIMPLE_II_TOTAL
        assert luxury_ratio == pytest.approx(Marx.IIB_TO_II_RATIO)

    @pytest.mark.theory
    def test_marx_expanded_reproduction_example(self) -> None:
        """Validate Marx's accumulation example from Capital Vol. 2, Ch. 21.

        I:  5000c + 1000v + 1000s = 7000
        II: 1430c +  285v +  285s = 2000
        """
        dept_I = DepartmentRow(c=Marx.EXPAND_I_C, v=Marx.EXPAND_I_V, s=Marx.EXPAND_I_S)
        dept_II = DepartmentRow(c=Marx.EXPAND_II_C, v=Marx.EXPAND_II_V, s=Marx.EXPAND_II_S)

        # Verify department totals
        assert dept_I.total_value == pytest.approx(Marx.EXPAND_I_TOTAL)
        assert dept_II.total_value == pytest.approx(Marx.EXPAND_II_TOTAL)

    @pytest.mark.theory
    def test_marx_uniform_occ_assumption(self) -> None:
        """Validate Marx's uniform organic composition assumption.

        Marx used c/v = 4:1 throughout his examples for simplicity.
        Our implementation extends this with variable OCC by department.
        """
        # All Marx examples use 4:1 OCC
        dept_I = DepartmentRow(c=Marx.SIMPLE_I_C, v=Marx.SIMPLE_I_V, s=Marx.SIMPLE_I_S)
        dept_IIa = DepartmentRow(c=Marx.SIMPLE_IIA_C, v=Marx.SIMPLE_IIA_V, s=Marx.SIMPLE_IIA_S)
        dept_IIb = DepartmentRow(c=Marx.SIMPLE_IIB_C, v=Marx.SIMPLE_IIB_V, s=Marx.SIMPLE_IIB_S)

        assert dept_I.organic_composition == pytest.approx(Marx.MARX_OCC)
        assert dept_IIa.organic_composition == pytest.approx(Marx.MARX_OCC)
        assert dept_IIb.organic_composition == pytest.approx(Marx.MARX_OCC)

    @pytest.mark.theory
    def test_marx_uniform_exploitation_assumption(self) -> None:
        """Validate Marx's uniform exploitation rate assumption.

        Marx used s/v = 1:1 (100% exploitation) throughout his examples.
        This means workers spend half their time producing their wages
        and half producing surplus for capitalists.
        """
        dept_I = DepartmentRow(c=Marx.SIMPLE_I_C, v=Marx.SIMPLE_I_V, s=Marx.SIMPLE_I_S)
        dept_IIa = DepartmentRow(c=Marx.SIMPLE_IIA_C, v=Marx.SIMPLE_IIA_V, s=Marx.SIMPLE_IIA_S)

        assert dept_I.exploitation_rate == pytest.approx(Marx.MARX_EXPLOITATION_RATE)
        assert dept_IIa.exploitation_rate == pytest.approx(Marx.MARX_EXPLOITATION_RATE)


# =============================================================================
# ORGANIC COMPOSITION THEORY TESTS
# =============================================================================


class TestOrganicCompositionTheory:
    """Tests for organic composition of capital (c/v) ordering.

    Theoretical basis: Different industries have different capital intensities.
    Means of production (mining, machinery) require more constant capital
    per worker than care work (childcare, domestic labor).
    """

    @pytest.fixture
    def mapper_with_theory_ratios(self) -> DepartmentMapper:
        """Create mapper with theoretically-ordered default ratios."""
        default_ratios: dict[Department, DefaultRatios] = {
            Department.I: DefaultRatios(cv_ratio=3.0, sv_ratio=2.0),
            Department.IIa: DefaultRatios(cv_ratio=1.5, sv_ratio=1.0),
            Department.IIb: DefaultRatios(cv_ratio=2.5, sv_ratio=3.0),
            Department.III: DefaultRatios(cv_ratio=0.5, sv_ratio=0.7),
        }
        return DepartmentMapper(
            defaults={},
            overrides={},
            excluded=set(),
            default_ratios=default_ratios,
        )

    @pytest.mark.theory
    def test_dept_I_has_highest_occ(self, mapper_with_theory_ratios: DepartmentMapper) -> None:
        """Dept I (capital goods) should have highest c/v ratio.

        Theoretical basis: Mining, machinery, construction materials
        require intensive constant capital investment per worker.
        """
        cv_I = mapper_with_theory_ratios.get_default_cv_ratio(Department.I)
        cv_IIa = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIa)
        cv_IIb = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIb)
        cv_III = mapper_with_theory_ratios.get_default_cv_ratio(Department.III)

        assert cv_I > cv_IIa, f"Dept I ({cv_I}) should have higher OCC than IIa ({cv_IIa})"
        assert cv_I > cv_IIb, f"Dept I ({cv_I}) should have higher OCC than IIb ({cv_IIb})"
        assert cv_I > cv_III, f"Dept I ({cv_I}) should have higher OCC than III ({cv_III})"

    @pytest.mark.theory
    def test_dept_III_has_lowest_occ(self, mapper_with_theory_ratios: DepartmentMapper) -> None:
        """Dept III (care work) should have lowest c/v ratio.

        Theoretical basis: Care work is maximally labor-intensive,
        requiring minimal machinery/constant capital. Childcare, nursing,
        domestic labor are performed with minimal capital equipment.
        """
        cv_I = mapper_with_theory_ratios.get_default_cv_ratio(Department.I)
        cv_IIa = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIa)
        cv_IIb = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIb)
        cv_III = mapper_with_theory_ratios.get_default_cv_ratio(Department.III)

        assert cv_III < cv_I, f"Dept III ({cv_III}) should have lower OCC than I ({cv_I})"
        assert cv_III < cv_IIa, f"Dept III ({cv_III}) should have lower OCC than IIa ({cv_IIa})"
        assert cv_III < cv_IIb, f"Dept III ({cv_III}) should have lower OCC than IIb ({cv_IIb})"

    @pytest.mark.theory
    def test_occ_ordering_reflects_capital_intensity(
        self, mapper_with_theory_ratios: DepartmentMapper
    ) -> None:
        """Verify c/v ordering: I > IIb > IIa > III.

        Capital intensity decreases from means of production
        through luxury goods to necessary consumption to care work.

        Rationale:
        - I: Mining, machinery, heavy industry (highest capital per worker)
        - IIb: Luxury goods often have monopoly capital, brand assets
        - IIa: Retail, food services, competitive markets (moderate)
        - III: Care work, domestic labor (lowest capital per worker)
        """
        cv_I = mapper_with_theory_ratios.get_default_cv_ratio(Department.I)
        cv_IIa = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIa)
        cv_IIb = mapper_with_theory_ratios.get_default_cv_ratio(Department.IIb)
        cv_III = mapper_with_theory_ratios.get_default_cv_ratio(Department.III)

        # Verify ordering: I > IIb > IIa > III
        assert cv_I > cv_IIb > cv_IIa > cv_III, (
            f"Expected OCC ordering I > IIb > IIa > III, got: "
            f"I={cv_I}, IIb={cv_IIb}, IIa={cv_IIa}, III={cv_III}"
        )


# =============================================================================
# EXPLOITATION RATE THEORY TESTS
# =============================================================================


class TestExploitationRateTheory:
    """Tests for rate of exploitation (s/v) ordering.

    Theoretical basis: Different market structures allow different
    levels of surplus extraction. Monopoly luxury goods can extract
    higher rents than competitive wage goods or suppressed care work.
    """

    @pytest.fixture
    def mapper_with_theory_ratios(self) -> DepartmentMapper:
        """Create mapper with theoretically-ordered default ratios."""
        default_ratios: dict[Department, DefaultRatios] = {
            Department.I: DefaultRatios(cv_ratio=3.0, sv_ratio=2.0),
            Department.IIa: DefaultRatios(cv_ratio=1.5, sv_ratio=1.0),
            Department.IIb: DefaultRatios(cv_ratio=2.5, sv_ratio=3.0),
            Department.III: DefaultRatios(cv_ratio=0.5, sv_ratio=0.7),
        }
        return DepartmentMapper(
            defaults={},
            overrides={},
            excluded=set(),
            default_ratios=default_ratios,
        )

    @pytest.mark.theory
    def test_dept_IIb_has_highest_exploitation(
        self, mapper_with_theory_ratios: DepartmentMapper
    ) -> None:
        """Dept IIb (luxury goods) should have highest s/v ratio.

        Theoretical basis: Monopoly rents, brand premiums, and
        status goods command superprofits above competitive rates.
        Luxury goods benefit from inelastic demand from the wealthy.
        """
        sv_I = mapper_with_theory_ratios.get_default_sv_ratio(Department.I)
        sv_IIa = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIa)
        sv_IIb = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIb)
        sv_III = mapper_with_theory_ratios.get_default_sv_ratio(Department.III)

        assert sv_IIb > sv_I, f"Dept IIb ({sv_IIb}) should have higher s/v than I ({sv_I})"
        assert sv_IIb > sv_IIa, f"Dept IIb ({sv_IIb}) should have higher s/v than IIa ({sv_IIa})"
        assert sv_IIb > sv_III, f"Dept IIb ({sv_IIb}) should have higher s/v than III ({sv_III})"

    @pytest.mark.theory
    def test_dept_III_has_lowest_exploitation(
        self, mapper_with_theory_ratios: DepartmentMapper
    ) -> None:
        """Dept III (care work) should have lowest s/v ratio.

        Theoretical basis: Care work wages are systematically
        suppressed, often equivalent to or below unpaid domestic labor.
        This is not low exploitation but rather reflects the
        systematic devaluation of reproductive labor.
        """
        sv_I = mapper_with_theory_ratios.get_default_sv_ratio(Department.I)
        sv_IIa = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIa)
        sv_IIb = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIb)
        sv_III = mapper_with_theory_ratios.get_default_sv_ratio(Department.III)

        assert sv_III < sv_I, f"Dept III ({sv_III}) should have lower s/v than I ({sv_I})"
        assert sv_III < sv_IIa, f"Dept III ({sv_III}) should have lower s/v than IIa ({sv_IIa})"
        assert sv_III < sv_IIb, f"Dept III ({sv_III}) should have lower s/v than IIb ({sv_IIb})"

    @pytest.mark.theory
    def test_exploitation_ordering(self, mapper_with_theory_ratios: DepartmentMapper) -> None:
        """Verify s/v ordering: IIb > I > IIa > III.

        Market power/monopoly profits > extractive industries >
        competitive goods markets > systematically devalued care work.

        Rationale:
        - IIb: Monopoly rents, brand premiums, status goods
        - I: Extractive industries, high productivity gains
        - IIa: Competitive markets, squeezed margins
        - III: Care work, systematically undervalued
        """
        sv_I = mapper_with_theory_ratios.get_default_sv_ratio(Department.I)
        sv_IIa = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIa)
        sv_IIb = mapper_with_theory_ratios.get_default_sv_ratio(Department.IIb)
        sv_III = mapper_with_theory_ratios.get_default_sv_ratio(Department.III)

        # Verify ordering: IIb > I > IIa > III
        assert sv_IIb > sv_I > sv_IIa > sv_III, (
            f"Expected s/v ordering IIb > I > IIa > III, got: "
            f"IIb={sv_IIb}, I={sv_I}, IIa={sv_IIa}, III={sv_III}"
        )


# =============================================================================
# ADDITIONAL THEORY TESTS
# =============================================================================


class TestTRPFConnection:
    """Tests connecting reproduction schema to Tendency of Rate of Profit to Fall.

    Marx's TRPF (Capital Vol. 3) connects to reproduction schema:
    As OCC rises (more c relative to v), the rate of profit s/(c+v) falls.
    """

    @pytest.mark.theory
    @pytest.mark.parametrize(
        "occ,expected_profit_trend",
        [
            (0.5, "high"),  # Low OCC -> high profit rate
            (4.0, "medium"),  # Marx's example OCC
            (10.0, "low"),  # High OCC -> low profit rate
        ],
        ids=["low_occ", "marx_occ", "high_occ"],
    )
    def test_profit_rate_falls_with_rising_occ(
        self, occ: float, expected_profit_trend: str
    ) -> None:
        """Higher organic composition leads to lower profit rate.

        With constant s/v = 1 (100% exploitation), as c/v rises,
        r = s/(c+v) necessarily falls.
        """
        v = 100.0
        s = 100.0  # s/v = 1.0 (100% exploitation)
        c = v * occ  # c/v = occ

        # Rate of profit formula
        rate = s / (c + v)

        # Expected ranges for profit rate
        thresholds = {"high": 0.4, "medium": 0.15, "low": 0.1}

        if expected_profit_trend == "high":
            assert rate > thresholds["high"], f"Low OCC should give high profit rate, got {rate}"
        elif expected_profit_trend == "medium":
            assert 0.1 < rate < 0.4, f"Marx OCC should give medium profit rate, got {rate}"
        else:  # low
            assert rate < thresholds["low"], f"High OCC should give low profit rate, got {rate}"

    @pytest.mark.theory
    def test_aggregate_occ_affects_economy_profit_rate(self) -> None:
        """Economy-wide profit rate depends on aggregate OCC across departments.

        An economy weighted toward Dept I (high OCC) will have lower
        aggregate profit rate than one weighted toward Dept III (low OCC).
        """
        # High OCC economy (Dept I dominated)
        high_occ_tensor = ValueTensor4x3(
            fips_code="00000",
            year=2022,
            dept_I=DepartmentRow(c=3000.0, v=1000.0, s=1000.0),  # OCC=3
            dept_IIa=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIb=DepartmentRow(c=50.0, v=50.0, s=50.0),
            dept_III=DepartmentRow(c=50.0, v=100.0, s=70.0),
            naics_granularity=1.0,
            excluded_wages=0.0,
        )

        # Low OCC economy (Dept III dominated)
        low_occ_tensor = ValueTensor4x3(
            fips_code="00000",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIa=DepartmentRow(c=100.0, v=100.0, s=100.0),
            dept_IIb=DepartmentRow(c=50.0, v=50.0, s=50.0),
            dept_III=DepartmentRow(c=500.0, v=1000.0, s=700.0),  # OCC=0.5
            naics_granularity=1.0,
            excluded_wages=0.0,
        )

        # Low OCC economy should have higher profit rate
        assert low_occ_tensor.profit_rate > high_occ_tensor.profit_rate, (
            f"Low OCC economy ({low_occ_tensor.profit_rate:.3f}) should have "
            f"higher profit rate than high OCC ({high_occ_tensor.profit_rate:.3f})"
        )
