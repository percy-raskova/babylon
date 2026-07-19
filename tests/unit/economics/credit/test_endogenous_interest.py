"""U9.3: the endogenous interest rate as a bounded share of the average
rate of profit (Capital Vol. III Part V)."""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.credit.endogenous_interest import (
    endogenous_interest_rate,
)


@pytest.mark.unit
class TestEndogenousInterestRate:
    def _defines(self) -> GameDefines:
        return GameDefines.load_default()

    def test_calm_market_pays_the_base_share_of_profit(self) -> None:
        state = endogenous_interest_rate(0.15, 0.0, self._defines())
        assert state.rate == pytest.approx(0.15 * 0.30)
        assert state.fragility_premium == pytest.approx(0.0)
        assert state.profit_rate_ceiling == pytest.approx(0.15)

    def test_full_tightness_approaches_the_crisis_ceiling(self) -> None:
        state = endogenous_interest_rate(0.15, 1.0, self._defines())
        assert state.rate == pytest.approx(0.15 * 0.95)
        assert state.rate < state.profit_rate_ceiling  # ch.22: i < r
        assert state.fragility_premium == pytest.approx(0.15 * (0.95 - 0.30))

    def test_absent_profit_rate_yields_zero_interest(self) -> None:
        # tick 0 / no territory carries a profit rate: nothing to divide.
        state = endogenous_interest_rate(None, 0.7, self._defines())
        assert state.rate == 0.0
        assert state.fragility_premium == 0.0
        assert state.profit_rate_ceiling == 0.0

    def test_nonpositive_profit_rate_yields_zero_interest(self) -> None:
        state = endogenous_interest_rate(-0.02, 1.0, self._defines())
        assert state.rate == 0.0
        assert state.fragility_premium == 0.0

    def test_tightness_is_clamped_into_unit_interval(self) -> None:
        hot = endogenous_interest_rate(0.15, 5.0, self._defines())
        assert hot.tightness == 1.0
        assert hot.rate == pytest.approx(0.15 * 0.95)
        cold = endogenous_interest_rate(0.15, -3.0, self._defines())
        assert cold.tightness == 0.0
        assert cold.rate == pytest.approx(0.15 * 0.30)
