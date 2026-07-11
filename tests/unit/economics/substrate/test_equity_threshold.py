"""Unit tests for equity threshold test (Spec 038 FR-005).

Feature: 038-unified-class-system (amended for Feature 043)
Date: 2026-04-09

Tests that the equity threshold test correctly classifies LA membership
through endogenous property relation logic rather than the deprecated
static ACS proxy.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import ClassSystemDefines
from babylon.domain.economics.substrate.transitions import (
    check_equity_threshold,
    evaluate_class_shares,
)
from babylon.domain.economics.substrate.types import HexEconomicState, HexTenureComposition
from babylon.models.enums import SocialRole


def _make_tenure(**kwargs: float) -> HexTenureComposition:
    """Build HexTenureComposition with defaults summing to 1.0."""
    defaults = {
        "residential_owner_occupied": 0.4,
        "residential_rental": 0.2,
        "commercial": 0.1,
        "industrial": 0.1,
        "public": 0.1,
        "trust_land": 0.0,
        "vacant_abandoned": 0.1,
    }
    defaults.update(kwargs)
    return HexTenureComposition(**defaults)


def _make_hex_state(
    c: float = 100.0,
    v: float = 50.0,
    s: float = 30.0,
    tenure: HexTenureComposition | None = None,
) -> HexEconomicState:
    """Build a HexEconomicState with computed rates."""
    cv = c + v
    return HexEconomicState(
        h3_index="872830828ffffff",
        county_fips="26163",
        constant_capital=c,
        variable_capital=v,
        surplus_value=s,
        employment=100.0,
        dept_shares=(0.25, 0.25, 0.25, 0.25),
        profit_rate=s / cv if cv > 0 else 0.0,
        tenure_composition=tenure,
    )


@pytest.mark.unit
class TestCheckEquityThreshold:
    """Tests for check_equity_threshold (FR-005).

    The equity_factor is an absolute threshold test on equity ratio,
    NOT a population-level numeric scaler.
    """

    def test_above_threshold_returns_true(self) -> None:
        """Equity ratio above threshold -> homeowners qualify as LA."""
        # equity_ratio = s / (c + v + s) = 30 / 180 = 0.167
        # With high surplus -> equity ratio exceeds threshold
        state = _make_hex_state(c=100, v=50, s=100, tenure=_make_tenure())
        defines = ClassSystemDefines(equity_factor=0.1)

        result = check_equity_threshold(state, defines)
        assert result is True

    def test_below_threshold_returns_false(self) -> None:
        """Equity ratio below threshold -> homeowners are NOT LA."""
        # Very low surplus -> equity ratio below threshold
        state = _make_hex_state(c=100, v=100, s=5, tenure=_make_tenure())
        defines = ClassSystemDefines(equity_factor=0.5)

        result = check_equity_threshold(state, defines)
        assert result is False

    def test_no_tenure_returns_false(self) -> None:
        """Without tenure_composition, no one is classified as LA by property."""
        state = _make_hex_state(c=100, v=50, s=100, tenure=None)
        defines = ClassSystemDefines(equity_factor=0.1)

        result = check_equity_threshold(state, defines)
        assert result is False

    def test_zero_surplus_fails_threshold(self) -> None:
        """Zero surplus value means zero equity ratio -> threshold not met."""
        state = _make_hex_state(c=100, v=50, s=0, tenure=_make_tenure())
        defines = ClassSystemDefines(equity_factor=0.1)

        result = check_equity_threshold(state, defines)
        assert result is False

    def test_default_defines_value(self) -> None:
        """Uses default equity_factor (0.6) from ClassSystemDefines."""
        # equity_ratio = 100 / (100 + 50 + 100) = 0.4 < 0.6 default
        state = _make_hex_state(c=100, v=50, s=100, tenure=_make_tenure())
        defines = ClassSystemDefines()  # equity_factor=0.6 default

        result = check_equity_threshold(state, defines)
        assert result is False  # 0.4 < 0.6

    def test_high_equity_passes_default(self) -> None:
        """High surplus value passes even the default 0.6 threshold."""
        # equity_ratio = 300 / (100 + 50 + 300) = 0.667 > 0.6
        state = _make_hex_state(c=100, v=50, s=300, tenure=_make_tenure())
        defines = ClassSystemDefines()  # equity_factor=0.6 default

        result = check_equity_threshold(state, defines)
        assert result is True


@pytest.mark.unit
class TestEvaluateClassSharesWithThreshold:
    """Integration: evaluate_class_shares + check_equity_threshold."""

    def test_foreclosure_demotes_la_to_proletariat(self) -> None:
        """After foreclosure empties owner-occupied, LA share drops to zero.

        Spec 038 FR-005 + Spec 043: foreclosure severs equity ->
        class mutation LA -> Proletariat.
        """
        # Start with 40% owner-occupied
        tenure = _make_tenure(residential_owner_occupied=0.4)
        shares_before = evaluate_class_shares(tenure, equity_threshold_met=True)
        assert shares_before[SocialRole.LABOR_ARISTOCRACY] == pytest.approx(0.4)

        # After total foreclosure: owner-occupied = 0
        post_tenure = _make_tenure(
            residential_owner_occupied=0.0,
            residential_rental=0.2,
            commercial=0.1,
            industrial=0.1,
            public=0.1,
            trust_land=0.0,
            vacant_abandoned=0.5,  # foreclosed -> vacant
        )
        shares_after = evaluate_class_shares(post_tenure, equity_threshold_met=True)
        assert shares_after[SocialRole.LABOR_ARISTOCRACY] == pytest.approx(0.0)
        assert shares_after[SocialRole.LUMPENPROLETARIAT] == pytest.approx(0.5)

    def test_equity_failure_demotes_all_owners_to_proletariat(self) -> None:
        """When equity threshold is not met, ALL owner-occupants become Proletariat.

        This models underwater mortgages: nominal ownership without
        meaningful equity does not constitute LA.
        """
        tenure = _make_tenure(residential_owner_occupied=0.4, residential_rental=0.2)
        shares = evaluate_class_shares(tenure, equity_threshold_met=False)

        # Owner-occupied (0.4) + Rental (0.2) = 0.6 Proletariat
        assert shares[SocialRole.LABOR_ARISTOCRACY] == pytest.approx(0.0)
        assert shares[SocialRole.INTERNAL_PROLETARIAT] == pytest.approx(0.6)
