"""Behavioral contract for tariff-dampened effective trade (P26 U5f, ADR165).

Pure function, no I/O — the U5d attribution/trade dataflow composes raw
per-node trade volumes with LEGISLATE-adjusted tariff rates and calls this
at init/re-init time. Never runs in-tick.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.trade_policy import (
    TradePolicyInputError,
    effective_trade,
    tariff_dampening,
)

pytestmark = pytest.mark.unit


class TestTariffDampening:
    def test_zero_rate_is_zero_dampening(self) -> None:
        assert tariff_dampening(0.0, 1.0) == 0.0

    def test_linear_pass_through_at_full_coefficient(self) -> None:
        assert tariff_dampening(0.25, 1.0) == pytest.approx(0.25)

    def test_coefficient_scales_the_rate(self) -> None:
        assert tariff_dampening(0.4, 0.5) == pytest.approx(0.2)

    def test_rate_above_one_rejected(self) -> None:
        with pytest.raises(TradePolicyInputError, match="rate"):
            tariff_dampening(1.5, 1.0)

    def test_rate_below_zero_rejected(self) -> None:
        with pytest.raises(TradePolicyInputError, match="rate"):
            tariff_dampening(-0.1, 1.0)

    def test_coefficient_above_one_rejected(self) -> None:
        with pytest.raises(TradePolicyInputError, match="coefficient"):
            tariff_dampening(0.5, 1.5)

    def test_coefficient_below_zero_rejected(self) -> None:
        with pytest.raises(TradePolicyInputError, match="coefficient"):
            tariff_dampening(0.5, -0.1)


class TestEffectiveTrade:
    def test_zero_rates_are_byte_identical_to_raw_trade(self) -> None:
        """Default-inert law: absent/zero tariff rates change nothing."""
        trade = {"china": 100.0, "eu": 50.0, "canada": 25.0}
        result = effective_trade(trade, {}, dampening=1.0)
        assert result == trade

    def test_dampens_by_the_node_rate(self) -> None:
        trade = {"china": 100.0}
        result = effective_trade(trade, {"china": 0.2}, dampening=1.0)
        assert result["china"] == pytest.approx(80.0)

    def test_missing_node_rate_defaults_to_zero(self) -> None:
        trade = {"china": 100.0, "eu": 50.0}
        result = effective_trade(trade, {"china": 0.2}, dampening=1.0)
        assert result["eu"] == pytest.approx(50.0)
        assert result["china"] == pytest.approx(80.0)

    def test_result_is_sorted_by_node(self) -> None:
        trade = {"eu": 1.0, "canada": 2.0, "china": 3.0}
        result = effective_trade(trade, {}, dampening=1.0)
        assert list(result.keys()) == sorted(trade.keys())

    def test_negative_trade_value_is_a_hard_error(self) -> None:
        with pytest.raises(TradePolicyInputError, match="negative"):
            effective_trade({"china": -1.0}, {}, dampening=1.0)

    def test_out_of_range_rate_is_a_hard_error(self) -> None:
        with pytest.raises(TradePolicyInputError, match="rate"):
            effective_trade({"china": 100.0}, {"china": 2.0}, dampening=1.0)

    def test_deterministic_same_inputs_same_output(self) -> None:
        trade = {"china": 100.0, "eu": 50.0}
        rates = {"china": 0.3, "eu": 0.1}
        first = effective_trade(trade, rates, dampening=0.8)
        second = effective_trade(trade, rates, dampening=0.8)
        assert first == second


class TestDefaultInertPin:
    """The default-inert law, pinned end-to-end through GameDefines: a
    campaign with no tariff LEGISLATE motions ever drafted reads
    TradePolicyDefines' shipped defaults, and effective_trade must return
    the raw trade values unchanged."""

    def test_game_defines_trade_policy_defaults_are_byte_identical(self) -> None:
        trade_policy = GameDefines().trade_policy
        trade = {"canada": 40.0, "china": 300.0, "eu": 200.0, "india": 60.0}
        result = effective_trade(
            trade,
            trade_policy.tariff_rates,
            dampening=trade_policy.tariff_dampening_coefficient,
        )
        assert result == trade
