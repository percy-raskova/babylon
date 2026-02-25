"""Tests for CounterTendencyStrength frozen model.

Feature: 024-capital-volume-iii (US5, FR-010, FR-011)
TDD Red Phase: Tests define expected behavior for counter-tendency strength.

CounterTendencyStrength: Aggregate measure of six TRPF counter-tendencies
with computed net_counter_tendency (weighted sum).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.counter_tendencies.types import (
    COUNTER_TENDENCY_WEIGHTS,
    CounterTendencyStrength,
)

# =============================================================================
# Frozen Model Invariants
# =============================================================================


@pytest.mark.unit
class TestCounterTendencyStrengthFrozen:
    """CounterTendencyStrength model is frozen (immutable)."""

    def test_frozen(self) -> None:
        """Cannot mutate fields after construction."""
        ct = CounterTendencyStrength(
            year=2020,
            exploitation_rate_change=0.1,
            wage_suppression=0.01,
            constant_capital_cheapening=-0.03,
            reserve_army_size=0.08,
            imperial_rent_flow=500_000_000_000.0,
            fictitious_profit_share=0.25,
        )
        with pytest.raises(ValidationError):
            ct.year = 2021  # type: ignore[misc]


# =============================================================================
# Field Validation
# =============================================================================


@pytest.mark.unit
class TestCounterTendencyStrengthValidation:
    """CounterTendencyStrength field constraints."""

    def test_defaults_to_zero(self) -> None:
        """All indicator fields default to 0.0."""
        ct = CounterTendencyStrength(year=2020)
        assert ct.exploitation_rate_change == pytest.approx(0.0)
        assert ct.wage_suppression == pytest.approx(0.0)
        assert ct.constant_capital_cheapening == pytest.approx(0.0)
        assert ct.reserve_army_size == pytest.approx(0.0)
        assert ct.imperial_rent_flow == pytest.approx(0.0)
        assert ct.fictitious_profit_share == pytest.approx(0.0)

    def test_negative_wage_suppression_rejected(self) -> None:
        """wage_suppression must be >= 0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, wage_suppression=-0.01)

    def test_negative_reserve_army_size_rejected(self) -> None:
        """reserve_army_size must be >= 0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, reserve_army_size=-0.01)

    def test_reserve_army_size_above_one_rejected(self) -> None:
        """reserve_army_size must be <= 1.0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, reserve_army_size=1.01)

    def test_negative_imperial_rent_flow_rejected(self) -> None:
        """imperial_rent_flow must be >= 0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, imperial_rent_flow=-1.0)

    def test_negative_fictitious_profit_share_rejected(self) -> None:
        """fictitious_profit_share must be >= 0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, fictitious_profit_share=-0.01)

    def test_fictitious_profit_share_above_one_rejected(self) -> None:
        """fictitious_profit_share must be <= 1.0."""
        with pytest.raises(ValidationError):
            CounterTendencyStrength(year=2020, fictitious_profit_share=1.01)

    def test_exploitation_rate_change_can_be_negative(self) -> None:
        """exploitation_rate_change allows negative values (declining s/v)."""
        ct = CounterTendencyStrength(year=2020, exploitation_rate_change=-0.5)
        assert ct.exploitation_rate_change == pytest.approx(-0.5)

    def test_constant_capital_cheapening_can_be_positive(self) -> None:
        """constant_capital_cheapening can be positive (capital getting more expensive)."""
        ct = CounterTendencyStrength(year=2020, constant_capital_cheapening=0.05)
        assert ct.constant_capital_cheapening == pytest.approx(0.05)


# =============================================================================
# Computed Fields
# =============================================================================


@pytest.mark.unit
class TestCounterTendencyStrengthComputed:
    """CounterTendencyStrength computed net_counter_tendency."""

    def test_weights_sum_to_one(self) -> None:
        """COUNTER_TENDENCY_WEIGHTS should sum to 1.0."""
        assert sum(COUNTER_TENDENCY_WEIGHTS) == pytest.approx(1.0)

    def test_weights_length_six(self) -> None:
        """COUNTER_TENDENCY_WEIGHTS has exactly 6 elements."""
        assert len(COUNTER_TENDENCY_WEIGHTS) == 6

    def test_net_counter_tendency_all_zero(self) -> None:
        """Net counter-tendency is 0.0 when all indicators are zero."""
        ct = CounterTendencyStrength(year=2020)
        assert ct.net_counter_tendency == pytest.approx(0.0)

    def test_positive_net_when_counter_tendencies_dominate(self) -> None:
        """Positive net when exploitation rising, wages suppressed, etc."""
        ct = CounterTendencyStrength(
            year=2020,
            exploitation_rate_change=0.1,  # Rising exploitation
            wage_suppression=0.02,  # Wages lagging productivity
            constant_capital_cheapening=-0.03,  # Capital goods cheapening
            reserve_army_size=0.10,  # High unemployment
            imperial_rent_flow=500_000_000_000.0,  # Strong imperial rent
            fictitious_profit_share=0.25,  # Financial profits absorb surplus
        )
        assert ct.net_counter_tendency > 0.0

    def test_negative_net_possible_when_trpf_dominates(self) -> None:
        """Negative net when counter-tendencies weakening."""
        ct = CounterTendencyStrength(
            year=2020,
            exploitation_rate_change=-0.1,  # Exploitation declining
            wage_suppression=0.0,  # No wage suppression
            constant_capital_cheapening=0.05,  # Capital goods getting expensive
            reserve_army_size=0.03,  # Low unemployment
            imperial_rent_flow=0.0,  # No imperial rent
            fictitious_profit_share=0.05,  # Small financial sector
        )
        assert ct.net_counter_tendency < 0.0

    def test_net_counter_tendency_weighted_sum(self) -> None:
        """net_counter_tendency uses COUNTER_TENDENCY_WEIGHTS in correct order."""
        ct = CounterTendencyStrength(
            year=2020,
            exploitation_rate_change=0.1,
            wage_suppression=0.01,
            constant_capital_cheapening=-0.03,
            reserve_army_size=0.08,
            imperial_rent_flow=500_000_000_000.0,
            fictitious_profit_share=0.25,
        )
        # Manual calculation of indicators:
        # [0] exploitation_rate_change = 0.1
        # [1] wage_suppression = 0.01
        # [2] -constant_capital_cheapening = -(-0.03) = 0.03
        # [3] reserve_army_size = 0.08
        # [4] normalized imperial rent = 1.0 (since flow > 0)
        # [5] fictitious_profit_share = 0.25
        indicators = [0.1, 0.01, 0.03, 0.08, 1.0, 0.25]
        expected = sum(w * v for w, v in zip(indicators, COUNTER_TENDENCY_WEIGHTS, strict=True))
        assert ct.net_counter_tendency == pytest.approx(expected)

    def test_imperial_rent_normalized_to_binary(self) -> None:
        """Imperial rent flow > 0 normalizes to 1.0 in the weighted sum."""
        ct_with_rent = CounterTendencyStrength(
            year=2020,
            imperial_rent_flow=1.0,  # Tiny but positive
        )
        ct_without_rent = CounterTendencyStrength(
            year=2020,
            imperial_rent_flow=0.0,
        )
        # Difference should be exactly the imperial rent weight * 1.0
        imperial_rent_weight = COUNTER_TENDENCY_WEIGHTS[4]
        diff = ct_with_rent.net_counter_tendency - ct_without_rent.net_counter_tendency
        assert diff == pytest.approx(imperial_rent_weight)
