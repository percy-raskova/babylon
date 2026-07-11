"""Tests for ClassMobilityCalculator (Feature 030, US6).

Covers Chetty KFR baseline rates, racial gap, carceral/mortality modifiers,
covariate adjustment, and event-driven parameter shifts.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.lifecycle.mobility import DefaultClassMobilityCalculator
from babylon.domain.economics.lifecycle.types import ClassMobilityParams


class TestClassMobilityCalculator:
    """T022: ClassMobilityCalculator tests."""

    @pytest.fixture
    def calc(self) -> DefaultClassMobilityCalculator:
        return DefaultClassMobilityCalculator()

    @pytest.fixture
    def default_params(self) -> ClassMobilityParams:
        return ClassMobilityParams()

    @pytest.mark.unit
    @pytest.mark.math
    def test_baseline_kfr_p25(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """SC-010: P25 parent → child at ~P44.5 (within 5%)."""
        outcome = calc.compute_mobility_outcome(
            parental_percentile=25.0,
            race="white",
            params=default_params,
        )
        assert abs(outcome - 0.445) < 0.445 * 0.05

    @pytest.mark.unit
    @pytest.mark.math
    def test_baseline_kfr_p75(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """SC-010: P75 parent → child at ~P58.0 (within 5%)."""
        outcome = calc.compute_mobility_outcome(
            parental_percentile=75.0,
            race="white",
            params=default_params,
        )
        assert abs(outcome - 0.580) < 0.580 * 0.05

    @pytest.mark.unit
    @pytest.mark.math
    def test_linear_interpolation_p50(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """P50 parent → midpoint between P25 and P75 KFR."""
        outcome = calc.compute_mobility_outcome(
            parental_percentile=50.0,
            race="white",
            params=default_params,
        )
        expected = 0.445 + 0.5 * (0.580 - 0.445)
        assert abs(outcome - expected) < 0.01

    @pytest.mark.unit
    @pytest.mark.math
    def test_below_p25_clamps_to_base(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Below P25 → same outcome as P25."""
        outcome = calc.compute_mobility_outcome(
            parental_percentile=10.0,
            race="white",
            params=default_params,
        )
        assert abs(outcome - 0.445) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_above_p75_clamps_to_p75(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Above P75 → same outcome as P75."""
        outcome = calc.compute_mobility_outcome(
            parental_percentile=90.0,
            race="white",
            params=default_params,
        )
        assert abs(outcome - 0.580) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_racial_gap_black(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Black P25 child outcome reduced by racial gap (0.134)."""
        white_outcome = calc.compute_mobility_outcome(
            parental_percentile=25.0,
            race="white",
            params=default_params,
        )
        black_outcome = calc.compute_mobility_outcome(
            parental_percentile=25.0,
            race="black",
            params=default_params,
        )
        gap = white_outcome - black_outcome
        assert abs(gap - 0.134) < 0.01

    @pytest.mark.unit
    @pytest.mark.math
    def test_racial_gap_floors_at_zero(
        self,
        calc: DefaultClassMobilityCalculator,
    ) -> None:
        """Racial gap cannot push outcome below zero."""
        params = ClassMobilityParams(
            mobility_base_rate=0.10,
            mobility_base_rate_p75=0.20,
            mobility_racial_gap=0.10,
        )
        outcome = calc.compute_mobility_outcome(
            parental_percentile=10.0,
            race="black",
            params=params,
        )
        assert outcome >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_carceral_modifier_premature_exit(
        self,
        calc: DefaultClassMobilityCalculator,
    ) -> None:
        """Carceral modifier 2.8x increases P→D' rate."""
        rate = calc.compute_premature_exit_rate(
            base_rate=0.0213,
            mortality_modifier=1.0,
            carceral_modifier=2.8,
        )
        expected = 0.0213 * 2.8
        assert abs(rate - expected) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_early_mortality_modifier(
        self,
        calc: DefaultClassMobilityCalculator,
    ) -> None:
        """Early mortality modifier 1.24x increases P→D' rate."""
        rate = calc.compute_premature_exit_rate(
            base_rate=0.0213,
            mortality_modifier=1.24,
            carceral_modifier=1.0,
        )
        expected = 0.0213 * 1.24
        assert abs(rate - expected) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_combined_modifiers(
        self,
        calc: DefaultClassMobilityCalculator,
    ) -> None:
        """Carceral and mortality modifiers compound."""
        rate = calc.compute_premature_exit_rate(
            base_rate=0.0213,
            mortality_modifier=1.24,
            carceral_modifier=2.8,
        )
        expected = 0.0213 * 1.24 * 2.8
        assert abs(rate - expected) < 0.001
        # Must be capped at 1.0
        assert rate <= 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_covariate_positive_college(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Higher college rate → improved mobility outcome."""
        base_outcome = 0.445
        high_college = ClassMobilityParams(college_rate=0.60)
        low_college = ClassMobilityParams(college_rate=0.10)
        adj_high = calc.apply_covariate_adjustment(base_outcome, high_college)
        adj_low = calc.apply_covariate_adjustment(base_outcome, low_college)
        assert adj_high > adj_low

    @pytest.mark.unit
    @pytest.mark.math
    def test_covariate_negative_poverty(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Higher poverty share → reduced mobility outcome."""
        base_outcome = 0.445
        high_poverty = ClassMobilityParams(poverty_share=0.30)
        low_poverty = ClassMobilityParams(poverty_share=0.05)
        adj_high = calc.apply_covariate_adjustment(base_outcome, high_poverty)
        adj_low = calc.apply_covariate_adjustment(base_outcome, low_poverty)
        assert adj_high < adj_low

    @pytest.mark.unit
    @pytest.mark.math
    def test_event_modifier_widens_racial_gap(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """In-game event widens racial gap by magnitude."""
        modified = calc.apply_event_modifier(
            params=default_params,
            event_type="racial_discrimination",
            magnitude=0.2,
        )
        expected_gap = 0.134 * (1.0 + 0.2)
        assert abs(modified.mobility_racial_gap - expected_gap) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_event_modifier_carceral_expansion(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Carceral expansion event increases carceral modifier."""
        modified = calc.apply_event_modifier(
            params=default_params,
            event_type="carceral_expansion",
            magnitude=0.5,
        )
        expected = 2.8 * (1.0 + 0.5)
        assert abs(modified.carceral_modifier - expected) < 0.01

    @pytest.mark.unit
    @pytest.mark.math
    def test_unknown_event_returns_unchanged(
        self,
        calc: DefaultClassMobilityCalculator,
        default_params: ClassMobilityParams,
    ) -> None:
        """Unknown event type returns params unchanged."""
        modified = calc.apply_event_modifier(
            params=default_params,
            event_type="unknown_event",
            magnitude=0.5,
        )
        assert modified.mobility_racial_gap == default_params.mobility_racial_gap
        assert modified.carceral_modifier == default_params.carceral_modifier
