"""Tests for Capital Volume II: Fixed/Circulating Capital (US3).

Feature: 023-capital-volume-ii
Tasks: T040-T047 (FR-008, FR-009, FR-010, FR-011)

Tests for decompose_constant_capital, update_depreciation_fund,
and compute_moral_depreciation functions.
"""

from __future__ import annotations

import pytest

from babylon.economics.circulation.fixed_circulating import (
    compute_moral_depreciation,
    decompose_constant_capital,
    update_depreciation_fund,
)
from babylon.economics.circulation.types import (
    DepreciationFundState,
    ReplacementCyclePosition,
)
from babylon.models.types import Currency

# =============================================================================
# T040-T042: decompose_constant_capital
# =============================================================================


class TestDecomposeConstantCapital:
    """Tests for decompose_constant_capital (FR-008)."""

    def test_ratio_zero_all_circulating(self) -> None:
        """ratio=0 means all capital is circulating, none is fixed."""
        fixed, circulating = decompose_constant_capital(
            total_c=Currency(100.0),
            fixed_capital_ratio=0.0,
        )
        assert fixed == pytest.approx(0.0)
        assert circulating == pytest.approx(100.0)

    def test_ratio_one_all_fixed(self) -> None:
        """ratio=1 means all capital is fixed, none is circulating."""
        fixed, circulating = decompose_constant_capital(
            total_c=Currency(100.0),
            fixed_capital_ratio=1.0,
        )
        assert fixed == pytest.approx(100.0)
        assert circulating == pytest.approx(0.0)

    def test_ratio_mid_value(self) -> None:
        """ratio=0.6 splits 100 into 60 fixed and 40 circulating."""
        fixed, circulating = decompose_constant_capital(
            total_c=Currency(100.0),
            fixed_capital_ratio=0.6,
        )
        assert fixed == pytest.approx(60.0)
        assert circulating == pytest.approx(40.0)

    def test_sum_equals_total(self) -> None:
        """Fixed + circulating must always sum to total_c."""
        total = Currency(250.0)
        fixed, circulating = decompose_constant_capital(
            total_c=total,
            fixed_capital_ratio=0.35,
        )
        assert fixed + circulating == pytest.approx(250.0)

    def test_large_capital_value(self) -> None:
        """Works correctly with large capital values."""
        fixed, circulating = decompose_constant_capital(
            total_c=Currency(1_000_000.0),
            fixed_capital_ratio=0.75,
        )
        assert fixed == pytest.approx(750_000.0)
        assert circulating == pytest.approx(250_000.0)

    def test_ratio_below_zero_raises(self) -> None:
        """Ratio below 0 must raise ValueError."""
        with pytest.raises(ValueError, match="ratio"):
            decompose_constant_capital(
                total_c=Currency(100.0),
                fixed_capital_ratio=-0.1,
            )

    def test_ratio_above_one_raises(self) -> None:
        """Ratio above 1 must raise ValueError."""
        with pytest.raises(ValueError, match="ratio"):
            decompose_constant_capital(
                total_c=Currency(100.0),
                fixed_capital_ratio=1.1,
            )

    def test_zero_total_c(self) -> None:
        """Zero total capital returns (0, 0) regardless of ratio."""
        fixed, circulating = decompose_constant_capital(
            total_c=Currency(0.0),
            fixed_capital_ratio=0.5,
        )
        assert fixed == pytest.approx(0.0)
        assert circulating == pytest.approx(0.0)


# =============================================================================
# T043-T046: update_depreciation_fund
# =============================================================================


class TestUpdateDepreciationFund:
    """Tests for update_depreciation_fund (FR-009, FR-010)."""

    @pytest.fixture
    def base_fund(self) -> DepreciationFundState:
        """Baseline depreciation fund for testing."""
        return DepreciationFundState(
            fips_code="26163",
            year=2020,
            total_fixed_capital=Currency(1_000_000.0),
            accumulated_depreciation=Currency(100_000.0),
            annual_depreciation_flow=Currency(100_000.0),
            replacement_expenditure=Currency(80_000.0),
        )

    def test_accumulation_adds_annual_depreciation(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """Accumulated depreciation increases by annual_depreciation."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(80_000.0),
        )
        # previous.accumulated (100k) + annual (100k) = 200k
        assert result.accumulated_depreciation == pytest.approx(200_000.0)

    def test_replacement_expenditure_preserved(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """Replacement expenditure in result reflects the input value."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(120_000.0),
        )
        assert result.replacement_expenditure == pytest.approx(120_000.0)

    def test_year_increments(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """Year in result is previous year + 1."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(80_000.0),
        )
        assert result.year == 2021

    def test_fips_code_preserved(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """FIPS code carries through from previous state."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(80_000.0),
        )
        assert result.fips_code == "26163"

    def test_investment_boom_cycle_position(self) -> None:
        """High replacement triggers INVESTMENT_BOOM cycle position."""
        fund = DepreciationFundState(
            fips_code="26163",
            year=2020,
            total_fixed_capital=Currency(1_000_000.0),
            accumulated_depreciation=Currency(200_000.0),
            annual_depreciation_flow=Currency(100_000.0),
            replacement_expenditure=Currency(160_000.0),
        )
        result = update_depreciation_fund(
            previous=fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(160_000.0),
        )
        assert result.replacement_cycle_position == ReplacementCyclePosition.INVESTMENT_BOOM

    def test_disinvestment_cycle_position(self) -> None:
        """Low replacement triggers DISINVESTMENT cycle position."""
        fund = DepreciationFundState(
            fips_code="26163",
            year=2020,
            total_fixed_capital=Currency(1_000_000.0),
            accumulated_depreciation=Currency(50_000.0),
            annual_depreciation_flow=Currency(100_000.0),
            replacement_expenditure=Currency(30_000.0),
        )
        result = update_depreciation_fund(
            previous=fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(30_000.0),
        )
        assert result.replacement_cycle_position == ReplacementCyclePosition.DISINVESTMENT

    def test_total_fixed_capital_preserved(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """Total fixed capital carries through from previous state."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(100_000.0),
            replacement_expenditure=Currency(80_000.0),
        )
        assert result.total_fixed_capital == pytest.approx(1_000_000.0)

    def test_annual_depreciation_flow_updated(
        self,
        base_fund: DepreciationFundState,
    ) -> None:
        """Annual depreciation flow in result reflects the new annual_depreciation."""
        result = update_depreciation_fund(
            previous=base_fund,
            annual_depreciation=Currency(120_000.0),
            replacement_expenditure=Currency(80_000.0),
        )
        assert result.annual_depreciation_flow == pytest.approx(120_000.0)


# =============================================================================
# T047: compute_moral_depreciation
# =============================================================================


class TestComputeMoralDepreciation:
    """Tests for compute_moral_depreciation (FR-011)."""

    def test_rapid_obsolescence(self) -> None:
        """Physical > economic life means rapid obsolescence (factor < 1)."""
        result = compute_moral_depreciation(
            naics_code="334",
            physical_remaining_life=10.0,
            economic_remaining_life=3.0,
        )
        assert result.naics_code == "334"
        assert result.physical_remaining_life == pytest.approx(10.0)
        assert result.economic_remaining_life == pytest.approx(3.0)
        assert result.obsolescence_factor == pytest.approx(0.3)

    def test_equal_lives(self) -> None:
        """Equal physical and economic life means no moral depreciation."""
        result = compute_moral_depreciation(
            naics_code="211",
            physical_remaining_life=15.0,
            economic_remaining_life=15.0,
        )
        assert result.obsolescence_factor == pytest.approx(1.0)

    def test_zero_physical_life(self) -> None:
        """Zero physical life returns obsolescence_factor of 1.0."""
        result = compute_moral_depreciation(
            naics_code="336",
            physical_remaining_life=0.0,
            economic_remaining_life=0.0,
        )
        assert result.obsolescence_factor == pytest.approx(1.0)

    def test_naics_code_preserved(self) -> None:
        """NAICS code is stored correctly on result."""
        result = compute_moral_depreciation(
            naics_code="541",
            physical_remaining_life=8.0,
            economic_remaining_life=4.0,
        )
        assert result.naics_code == "541"

    def test_very_short_economic_life(self) -> None:
        """Very short economic life relative to physical."""
        result = compute_moral_depreciation(
            naics_code="511",
            physical_remaining_life=20.0,
            economic_remaining_life=1.0,
        )
        assert result.obsolescence_factor == pytest.approx(0.05)
