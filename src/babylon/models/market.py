"""National market-scissors state — the price⟷value axis (Program 23 Phase 1).

The phenomenal form's dynamical state: log price-to-value ratio and log
fictitious-to-real ratio with their oscillator velocities, plus the EMA
anchors of the realized value/surplus flow. ``WorldState`` holds it as an
optional field and round-trips it via ``G.graph["market"]`` (the
``wealth_distribution`` metadata pattern), written only when set so
axis-less graphs stay byte-identical.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MarketState(BaseModel):
    """Price and fictitious-capital oscillator state (national, per-tick units).

    :ivar price_log: ``ln(price index / value anchor)`` — the scissors.
    :ivar price_velocity: d(price_log)/dt.
    :ivar fictitious_log: ``ln(fictitious capitalization / real capitalization)``.
    :ivar fictitious_velocity: d(fictitious_log)/dt.
    :ivar surplus_ema: EMA of realized surplus ``max(Σv_produced − Σw_paid, 0)``.
    :ivar value_ema: EMA of realized value output ``Σv_produced``.
    :ivar tick: The tick this state was computed at.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    price_log: float
    price_velocity: float
    fictitious_log: float
    fictitious_velocity: float
    surplus_ema: float = Field(ge=0.0)
    value_ema: float = Field(ge=0.0)
    tick: int = Field(ge=0)
