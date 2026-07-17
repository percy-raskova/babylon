"""Phase-2 MarketDefines contract — the correction coefficients (ADR078).

Pins the promotion-ceremony gate default (``feedback_enabled``) and the
bounds of the correction machinery's nine coefficients. The gate default is
flipped to ``True`` in the promotion commit (the EH/Doctrine staging
pattern); this file's assertion is updated in the SAME commit, deliberately.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import MarketDefines
from babylon.models.market import MarketState

pytestmark = pytest.mark.unit


class TestPhase2Defaults:
    def test_correction_coefficients_defaults(self) -> None:
        """The nine Phase-2 coefficients carry their ADR078 defaults."""
        d = MarketDefines()
        assert d.correction_threshold_base == 0.55
        assert d.correction_profit_slope == 4.0
        assert d.correction_severity == 0.6
        assert d.correction_price_severity == 0.3
        assert d.correction_cooldown_ticks == 8
        assert d.evaporation_gain == 0.15
        assert d.unemployment_gain == 0.08
        assert d.wealth_axis_kick_gain == 0.02

    def test_feedback_gate_default(self) -> None:
        """Promotion ceremony (ADR078) flipped the gate: the correction is LIVE."""
        assert MarketDefines().feedback_enabled is True


class TestPhase2Bounds:
    def test_severity_bounded_to_unit_interval(self) -> None:
        with pytest.raises(ValidationError):
            MarketDefines(correction_severity=1.5)

    def test_cooldown_at_least_one_tick(self) -> None:
        with pytest.raises(ValidationError):
            MarketDefines(correction_cooldown_ticks=0)

    def test_evaporation_gain_capped(self) -> None:
        with pytest.raises(ValidationError):
            MarketDefines(evaporation_gain=0.6)


class TestCorrectionLedger:
    def test_market_state_ledger_defaults(self) -> None:
        """MarketState carries the cumulative correction ledger (real fields,
        never shadow attrs — event-sourced accumulated state)."""
        state = MarketState(
            price_log=0.0,
            price_velocity=0.0,
            fictitious_log=0.0,
            fictitious_velocity=0.0,
            surplus_ema=1.0,
            value_ema=1.0,
            tick=0,
        )
        assert state.corrections == 0
        assert state.last_correction_tick is None

    def test_ledger_round_trips(self) -> None:
        state = MarketState(
            price_log=0.1,
            price_velocity=0.0,
            fictitious_log=0.4,
            fictitious_velocity=0.0,
            surplus_ema=1.0,
            value_ema=1.0,
            tick=9,
            corrections=2,
            last_correction_tick=7,
        )
        rebuilt = MarketState(**state.model_dump())
        assert rebuilt.corrections == 2
        assert rebuilt.last_correction_tick == 7

    def test_negative_corrections_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketState(
                price_log=0.0,
                price_velocity=0.0,
                fictitious_log=0.0,
                fictitious_velocity=0.0,
                surplus_ema=1.0,
                value_ema=1.0,
                tick=0,
                corrections=-1,
            )
