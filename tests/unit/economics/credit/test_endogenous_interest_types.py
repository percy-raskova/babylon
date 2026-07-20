"""U9.1: the EndogenousInterestRate model encodes Marx's ch. 22 bound
(0 <= i < r) as a construction invariant — a behavioral contract that
outlives the producer (Constitution III.12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.credit.types import EndogenousInterestRate


@pytest.mark.unit
class TestEndogenousInterestRate:
    def test_present_rate_is_strictly_below_the_profit_ceiling(self) -> None:
        state = EndogenousInterestRate(
            year=2015,
            profit_rate_ceiling=0.15,
            rate=0.045,
            fragility_premium=0.0,
            tightness=0.0,
            reserve_army_signal=0.0,
        )
        assert state.rate < state.profit_rate_ceiling
        assert state.base_component == pytest.approx(0.045)

    def test_base_component_strips_the_fragility_premium(self) -> None:
        state = EndogenousInterestRate(
            year=2015,
            profit_rate_ceiling=0.15,
            rate=0.12,
            fragility_premium=0.075,
            tightness=0.8,
            reserve_army_signal=0.8,
        )
        assert state.base_component == pytest.approx(0.045)

    def test_zero_ceiling_forces_zero_rate(self) -> None:
        # r <= 0: no profit to divide -> i must be 0 (ch. 22 / ch. 23).
        EndogenousInterestRate(
            year=2015,
            profit_rate_ceiling=0.0,
            rate=0.0,
            fragility_premium=0.0,
            tightness=0.0,
            reserve_army_signal=0.0,
        )

    def test_rate_at_or_above_ceiling_is_rejected(self) -> None:
        # ch. 22: the maximum limit of interest is the profit itself; the sim
        # keeps profit-of-enterprise strictly positive, so i must be < r.
        with pytest.raises(ValidationError, match="rate .* profit_rate_ceiling"):
            EndogenousInterestRate(
                year=2015,
                profit_rate_ceiling=0.10,
                rate=0.10,
                fragility_premium=0.0,
                tightness=0.0,
                reserve_army_signal=0.0,
            )

    def test_nonzero_rate_with_zero_ceiling_is_rejected(self) -> None:
        # r <= 0: no profit to divide -> i must be 0 (ch. 22 / ch. 23). A
        # nonzero rate against a zero (or negative-clamped-to-zero) ceiling
        # violates that half of the bound and must be rejected loudly.
        with pytest.raises(ValidationError, match="rate must be 0.0"):
            EndogenousInterestRate(
                year=2015,
                profit_rate_ceiling=0.0,
                rate=0.05,
                fragility_premium=0.0,
                tightness=0.0,
                reserve_army_signal=0.0,
            )
