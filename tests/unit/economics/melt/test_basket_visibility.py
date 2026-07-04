"""Unit tests for BasketVisibilityCalculator (User Story 3).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

TDD Red Phase: These tests define the expected behavior for basket visibility
computation per TVT Axiom D3.
"""

from __future__ import annotations

import math

from babylon.economics.melt import DefaultBasketVisibilityCalculator
from babylon.economics.melt.gamma_hydration import GammaHydrationSource


class TestBasketVisibilityFormula:
    """Tests for γ_basket = 1 / (α/γ_import + (1-α)) formula."""

    def test_formula_with_mvp_values(self) -> None:
        """Test γ_basket formula: 1 / (0.25/0.35 + 0.75) ≈ 0.683.

        Expected computation:
        γ_basket = 1 / (α/γ_import + (1-α))
                 = 1 / (0.25/0.35 + 0.75)
                 = 1 / (0.714 + 0.75)
                 = 1 / 1.464
                 ≈ 0.683
        """
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.35)

        # Should compute from provided values, not use MVP
        assert estimated is False
        # Result should be approximately 0.683
        expected = 1.0 / (0.25 / 0.35 + 0.75)
        assert abs(gamma - expected) < 0.001

    def test_formula_with_different_values(self) -> None:
        """Test γ_basket formula with non-MVP values."""
        calculator = DefaultBasketVisibilityCalculator()

        # α = 0.30, γ_import = 0.40
        # γ_basket = 1 / (0.30/0.40 + 0.70) = 1 / (0.75 + 0.70) = 1/1.45 ≈ 0.69
        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.30, gamma_import=0.40)

        assert estimated is False
        expected = 1.0 / (0.30 / 0.40 + 0.70)
        assert abs(gamma - expected) < 0.001


class TestMVPMode:
    """Tests for MVP mode behavior when data is unavailable."""

    def test_mvp_mode_when_alpha_missing(self) -> None:
        """Test that missing α triggers MVP mode."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=None, gamma_import=0.35)

        assert gamma == 0.68
        assert estimated is True

    def test_mvp_mode_when_gamma_import_missing(self) -> None:
        """Test that missing γ_import triggers MVP mode."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=None)

        assert gamma == 0.68
        assert estimated is True

    def test_mvp_mode_when_both_missing(self) -> None:
        """Test that missing both parameters triggers MVP mode."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022)

        assert gamma == 0.68
        assert estimated is True

    def test_mvp_mode_returns_tuple_format(self) -> None:
        """Test MVP mode returns (0.68, True) tuple."""
        calculator = DefaultBasketVisibilityCalculator()

        result = calculator.get_gamma_basket(2022)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result == (0.68, True)


class TestEdgeCases:
    """Tests for edge cases in γ_basket computation."""

    def test_alpha_zero_returns_one(self) -> None:
        """Test edge case α=0: returns γ_basket=1.0 (no imports, no subsidy).

        When α = 0 (no imports), the basket visibility is 1.0 because
        there is no imperial subsidy from peripheral labor.
        """
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.0, gamma_import=0.35)

        assert gamma == 1.0
        assert estimated is False

    def test_alpha_one_returns_gamma_import(self) -> None:
        """Test edge case α=1: returns γ_basket=γ_import (100% imports).

        When α = 1 (100% imports), the basket visibility equals γ_import
        because all consumption is subsidized by peripheral labor.
        """
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=1.0, gamma_import=0.35)

        assert gamma == 0.35
        assert estimated is False

    def test_alpha_one_with_different_gamma_import(self) -> None:
        """Test α=1 edge case with different γ_import values."""
        calculator = DefaultBasketVisibilityCalculator()

        for gamma_import in [0.20, 0.50, 0.80]:
            gamma, estimated = calculator.get_gamma_basket(
                2022, alpha=1.0, gamma_import=gamma_import
            )
            assert gamma == gamma_import
            assert estimated is False


class TestSanityValidation:
    """Tests for sanity validation ranges per FR-010."""

    def test_expected_range_valid_no_message(self) -> None:
        """Test γ_basket in expected range (0.60-0.80) returns valid=True, message=None."""
        calculator = DefaultBasketVisibilityCalculator()

        for gamma in [0.60, 0.68, 0.70, 0.80]:
            valid, message = calculator.validate_gamma_basket(gamma)
            assert valid is True
            assert message is None

    def test_warning_range_below_expected(self) -> None:
        """Test γ_basket in warning range (0.40-0.60) returns valid=True with warning."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.50)

        assert valid is True
        assert message is not None
        assert "WARNING" in message
        assert "0.50" in message

    def test_warning_range_above_expected(self) -> None:
        """Test γ_basket in warning range (0.80-0.95) returns valid=True with warning."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.90)

        assert valid is True
        assert message is not None
        assert "WARNING" in message
        assert "0.90" in message

    def test_fail_range_below_valid(self) -> None:
        """Test γ_basket below valid range (<0.1) returns valid=False."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.05)

        assert valid is False
        assert message is not None
        assert "0.05" in message

    def test_fail_range_above_valid(self) -> None:
        """Test γ_basket above valid range (>1.0) returns valid=False."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(1.5)

        assert valid is False
        assert message is not None
        assert "1.50" in message

    def test_boundary_at_expected_min(self) -> None:
        """Test γ_basket at expected minimum (0.60) is valid without warning."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.60)

        assert valid is True
        assert message is None

    def test_boundary_at_expected_max(self) -> None:
        """Test γ_basket at expected maximum (0.80) is valid without warning."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.80)

        assert valid is True
        assert message is None

    def test_boundary_at_fail_min(self) -> None:
        """Test γ_basket at fail minimum (0.10) is valid (just inside warning range)."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(0.10)

        # 0.10 is at the boundary of fail range - should be valid but with warning
        assert valid is True
        assert message is not None  # In warning range, not expected range

    def test_boundary_at_fail_max(self) -> None:
        """Test γ_basket at fail maximum (1.0) is valid (just inside warning range)."""
        calculator = DefaultBasketVisibilityCalculator()

        valid, message = calculator.validate_gamma_basket(1.0)

        # 1.0 is at the boundary of fail range - should be valid but with warning
        assert valid is True
        assert message is not None  # In warning range, not expected range


class TestMVPProperties:
    """Tests for MVP constant properties."""

    def test_mvp_alpha_returns_025(self) -> None:
        """Test mvp_alpha property returns 0.25."""
        calculator = DefaultBasketVisibilityCalculator()

        assert calculator.mvp_alpha == 0.25

    def test_mvp_gamma_import_returns_035(self) -> None:
        """Test mvp_gamma_import property returns 0.35."""
        calculator = DefaultBasketVisibilityCalculator()

        assert calculator.mvp_gamma_import == 0.35

    def test_mvp_gamma_basket_returns_068(self) -> None:
        """Test mvp_gamma_basket property returns 0.68."""
        calculator = DefaultBasketVisibilityCalculator()

        assert calculator.mvp_gamma_basket == 0.68

    def test_mvp_values_are_consistent(self) -> None:
        """Test that MVP values are internally consistent.

        The MVP γ_basket should approximately equal the formula result
        computed from MVP α and γ_import values.
        """
        calculator = DefaultBasketVisibilityCalculator()

        alpha = calculator.mvp_alpha
        gamma_import = calculator.mvp_gamma_import
        gamma_basket = calculator.mvp_gamma_basket

        # Compute expected value from formula
        expected = 1.0 / (alpha / gamma_import + (1 - alpha))

        # MVP value should be close to computed value
        # (they differ slightly due to rounding in the MVP constant)
        assert abs(gamma_basket - expected) < 0.01


class TestYearParameter:
    """Tests for year parameter handling."""

    def test_year_is_accepted_but_unused_in_mvp_mode(self) -> None:
        """Test that year parameter is accepted but doesn't affect MVP output."""
        calculator = DefaultBasketVisibilityCalculator()

        # Different years should give same MVP result
        for year in [2010, 2015, 2020, 2022, 2024]:
            gamma, estimated = calculator.get_gamma_basket(year)
            assert gamma == 0.68
            assert estimated is True

    def test_year_is_accepted_with_explicit_params(self) -> None:
        """Test that year parameter is accepted when explicit params provided."""
        calculator = DefaultBasketVisibilityCalculator()

        # Different years with same explicit params should give same result
        gamma_2010, _ = calculator.get_gamma_basket(2010, alpha=0.25, gamma_import=0.35)
        gamma_2022, _ = calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.35)

        assert gamma_2010 == gamma_2022


class TestNumericalStability:
    """Tests for numerical edge cases."""

    def test_small_gamma_import_does_not_cause_overflow(self) -> None:
        """Test that small γ_import values don't cause numerical issues."""
        calculator = DefaultBasketVisibilityCalculator()

        # Very small γ_import with α > 0 should still compute
        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.01)

        assert estimated is False
        assert not math.isnan(gamma)
        assert not math.isinf(gamma)
        # With α=0.25 and γ_import=0.01:
        # γ_basket = 1 / (0.25/0.01 + 0.75) = 1 / (25 + 0.75) = 1/25.75 ≈ 0.039
        assert gamma < 0.10  # Should be quite small

    def test_gamma_import_near_one(self) -> None:
        """Test computation with γ_import near 1.0 (minimal peripheral compression)."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.99)

        assert estimated is False
        # With high γ_import, γ_basket should be close to 1.0
        assert gamma > 0.95

    def test_alpha_near_zero(self) -> None:
        """Test computation with α very close to zero."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.001, gamma_import=0.35)

        assert estimated is False
        # With α ≈ 0, γ_basket should be close to 1.0
        assert gamma > 0.99

    def test_alpha_near_one(self) -> None:
        """Test computation with α very close to one."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2022, alpha=0.999, gamma_import=0.35)

        assert estimated is False
        # With α ≈ 1, γ_basket should be close to γ_import
        assert abs(gamma - 0.35) < 0.01


class _FakeHydrationSource:
    """Fake GammaHydrationSource returning scripted per-year values."""

    def __init__(
        self,
        alpha_by_year: dict[int, float | None],
        gamma_import_by_year: dict[int, float | None],
    ) -> None:
        self._alpha_by_year = alpha_by_year
        self._gamma_import_by_year = gamma_import_by_year

    def get_alpha(self, year: int) -> float | None:
        return self._alpha_by_year.get(year)

    def get_gamma_import(self, year: int, scale_type: str = "Intensive") -> float | None:  # noqa: ARG002
        return self._gamma_import_by_year.get(year)


class TestHydrationSourceWiring:
    """Spec-102: DefaultBasketVisibilityCalculator hydrates via an injected source."""

    def test_default_implements_protocol(self) -> None:
        """SQLiteGammaHydrationSource-shaped fakes satisfy GammaHydrationSource."""
        source = _FakeHydrationSource({2012: 0.25}, {2012: 1.0 / 7.86})
        assert isinstance(source, GammaHydrationSource)

    def test_hydrated_year_returns_estimated_false_with_real_value(self) -> None:
        source = _FakeHydrationSource({2012: 0.25}, {2012: 1.0 / 7.86})
        calculator = DefaultBasketVisibilityCalculator(hydration_source=source)

        gamma, estimated = calculator.get_gamma_basket(2012)

        assert estimated is False
        assert gamma != 0.68
        expected = 1.0 / (0.25 / (1.0 / 7.86) + 0.75)
        assert abs(gamma - expected) < 1e-9

    def test_unhydratable_year_falls_back_to_mvp(self) -> None:
        """2020 has no Hickel row (spec.md FR-102-2) -> MVP fallback, not a crash."""
        source = _FakeHydrationSource({2012: 0.25}, {2012: 1.0 / 7.86})
        calculator = DefaultBasketVisibilityCalculator(hydration_source=source)

        gamma, estimated = calculator.get_gamma_basket(2020)

        assert gamma == 0.68
        assert estimated is True

    def test_partial_hydration_falls_back_to_mvp(self) -> None:
        """alpha hydrates but gamma_import doesn't -> MVP fallback (no half-formula)."""
        source = _FakeHydrationSource({2012: 0.25}, {})
        calculator = DefaultBasketVisibilityCalculator(hydration_source=source)

        gamma, estimated = calculator.get_gamma_basket(2012)

        assert gamma == 0.68
        assert estimated is True

    def test_explicit_alpha_overrides_hydration(self) -> None:
        """Caller-supplied alpha is used as-is; hydration only fills gaps."""
        source = _FakeHydrationSource({2012: 0.99}, {2012: 1.0 / 7.86})
        calculator = DefaultBasketVisibilityCalculator(hydration_source=source)

        gamma, estimated = calculator.get_gamma_basket(2012, alpha=0.25)

        assert estimated is False
        expected = 1.0 / (0.25 / (1.0 / 7.86) + 0.75)
        assert abs(gamma - expected) < 1e-9

    def test_no_hydration_source_is_byte_identical_to_pre_spec_102(self) -> None:
        """Constructing with zero args (the pre-existing call pattern) is unchanged."""
        calculator = DefaultBasketVisibilityCalculator()

        gamma, estimated = calculator.get_gamma_basket(2012)

        assert gamma == 0.68
        assert estimated is True
