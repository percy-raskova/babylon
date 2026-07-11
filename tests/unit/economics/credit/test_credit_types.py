"""Tests for credit dynamics type definitions (InterestRateState, CreditState).

Feature: 024-capital-volume-iii (US2, FR-002, FR-003, FR-006)
TDD Red Phase: Tests define expected behavior for interest rate and credit state models.

InterestRateState: national interest rate environment snapshot.
CreditState: national credit system health snapshot with credit cycle phase.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.credit.types import (
    CreditCyclePhase,
    CreditState,
    InterestRateState,
)

# =============================================================================
# InterestRateState
# =============================================================================


@pytest.mark.unit
class TestInterestRateStateFrozen:
    """InterestRateState must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        state = InterestRateState(
            year=2020,
            base_rate=0.0036,
            treasury_10y=0.0089,
            baa_spread=0.0234,
        )
        with pytest.raises(ValidationError):
            state.base_rate = 0.05  # type: ignore[misc]


@pytest.mark.unit
class TestInterestRateStateFields:
    """InterestRateState field validation and computed properties."""

    def test_valid_construction(self) -> None:
        """Normal construction with all required fields succeeds."""
        state = InterestRateState(
            year=2020,
            base_rate=0.0036,
            treasury_10y=0.0089,
            baa_spread=0.0234,
        )
        assert state.year == 2020
        assert state.base_rate == pytest.approx(0.0036)
        assert state.treasury_10y == pytest.approx(0.0089)
        assert state.baa_spread == pytest.approx(0.0234)

    def test_negative_base_rate_rejected(self) -> None:
        """Negative base_rate is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="base_rate"):
            InterestRateState(
                year=2020,
                base_rate=-0.01,
                treasury_10y=0.0089,
                baa_spread=0.0234,
            )

    def test_negative_treasury_10y_rejected(self) -> None:
        """Negative treasury_10y is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="treasury_10y"):
            InterestRateState(
                year=2020,
                base_rate=0.0036,
                treasury_10y=-0.001,
                baa_spread=0.0234,
            )

    def test_negative_baa_spread_rejected(self) -> None:
        """Negative baa_spread is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="baa_spread"):
            InterestRateState(
                year=2020,
                base_rate=0.0036,
                treasury_10y=0.0089,
                baa_spread=-0.005,
            )

    def test_zero_rates_accepted(self) -> None:
        """Zero values for all rate fields are valid (ZIRP environment)."""
        state = InterestRateState(
            year=2020,
            base_rate=0.0,
            treasury_10y=0.0,
            baa_spread=0.0,
        )
        assert state.base_rate == 0.0
        assert state.treasury_10y == 0.0
        assert state.baa_spread == 0.0


@pytest.mark.unit
class TestInterestRateStateEffectiveRate:
    """InterestRateState.effective_rate computed field."""

    def test_effective_rate_is_sum(self) -> None:
        """effective_rate = base_rate + baa_spread."""
        state = InterestRateState(
            year=2020,
            base_rate=0.0036,
            treasury_10y=0.0089,
            baa_spread=0.0234,
        )
        assert state.effective_rate == pytest.approx(0.0036 + 0.0234)

    def test_effective_rate_zero_when_both_zero(self) -> None:
        """effective_rate = 0 when base_rate and baa_spread are both 0."""
        state = InterestRateState(
            year=2020,
            base_rate=0.0,
            treasury_10y=0.02,
            baa_spread=0.0,
        )
        assert state.effective_rate == pytest.approx(0.0)

    def test_effective_rate_crisis_year(self) -> None:
        """2008 crisis: low base_rate but wide baa_spread."""
        state = InterestRateState(
            year=2008,
            base_rate=0.0193,
            treasury_10y=0.0366,
            baa_spread=0.0349,
        )
        assert state.effective_rate == pytest.approx(0.0193 + 0.0349)


# =============================================================================
# CreditState
# =============================================================================


@pytest.mark.unit
class TestCreditStateFrozen:
    """CreditState must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
        )
        with pytest.raises(ValidationError):
            state.total_credit = 0.0  # type: ignore[misc]


@pytest.mark.unit
class TestCreditStateFields:
    """CreditState field validation."""

    def test_minimal_construction(self) -> None:
        """Construction with only required fields uses defaults."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
        )
        assert state.year == 2020
        assert state.total_credit == pytest.approx(83_000_000_000_000.0)
        assert state.credit_expansion_rate == pytest.approx(0.0)
        assert state.default_rate == pytest.approx(0.0)
        assert state.spread_to_treasuries == pytest.approx(0.0)
        assert state.phase == CreditCyclePhase.EXPANSION
        assert state.prev_phase is None

    def test_full_construction(self) -> None:
        """Construction with all fields explicit."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
            credit_expansion_rate=0.05,
            default_rate=0.015,
            spread_to_treasuries=0.02,
            phase=CreditCyclePhase.OVEREXTENSION,
            prev_phase=CreditCyclePhase.EXPANSION,
        )
        assert state.phase == CreditCyclePhase.OVEREXTENSION
        assert state.prev_phase == CreditCyclePhase.EXPANSION
        assert state.default_rate == pytest.approx(0.015)

    def test_negative_total_credit_rejected(self) -> None:
        """Negative total_credit is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="total_credit"):
            CreditState(
                year=2020,
                total_credit=-1.0,
            )

    def test_default_rate_above_one_rejected(self) -> None:
        """default_rate > 1.0 is rejected by le=1 constraint."""
        with pytest.raises(ValidationError, match="default_rate"):
            CreditState(
                year=2020,
                total_credit=83_000_000_000_000.0,
                default_rate=1.01,
            )

    def test_negative_default_rate_rejected(self) -> None:
        """Negative default_rate is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="default_rate"):
            CreditState(
                year=2020,
                total_credit=83_000_000_000_000.0,
                default_rate=-0.01,
            )

    def test_negative_spread_rejected(self) -> None:
        """Negative spread_to_treasuries is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="spread_to_treasuries"):
            CreditState(
                year=2020,
                total_credit=83_000_000_000_000.0,
                spread_to_treasuries=-0.01,
            )

    def test_default_phase_is_expansion(self) -> None:
        """Default phase is EXPANSION per spec."""
        state = CreditState(year=2020, total_credit=1.0)
        assert state.phase == CreditCyclePhase.EXPANSION


@pytest.mark.unit
class TestCreditStateCreditFragility:
    """CreditState.credit_fragility computed field."""

    def test_credit_fragility_product(self) -> None:
        """credit_fragility = default_rate * spread_to_treasuries."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
            default_rate=0.04,
            spread_to_treasuries=0.06,
        )
        assert state.credit_fragility == pytest.approx(0.04 * 0.06)

    def test_credit_fragility_zero_when_no_defaults(self) -> None:
        """credit_fragility = 0 when default_rate is 0."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
            default_rate=0.0,
            spread_to_treasuries=0.05,
        )
        assert state.credit_fragility == pytest.approx(0.0)

    def test_credit_fragility_zero_when_no_spread(self) -> None:
        """credit_fragility = 0 when spread_to_treasuries is 0."""
        state = CreditState(
            year=2020,
            total_credit=83_000_000_000_000.0,
            default_rate=0.03,
            spread_to_treasuries=0.0,
        )
        assert state.credit_fragility == pytest.approx(0.0)
