"""Market-scissors coefficients (Program 23, ADR077).

Price and fictitious-capital dynamics: two damped-driven oscillators in
log-ratio space around the value anchor. The restoring force IS the law of
value; the drive terms are realized value/surplus growth (demand pull and
return-chasing speculation). All shadow-phase: nothing downstream consumes
the outputs yet (Phase 2 feedback is owner-gated).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MarketDefines(BaseModel):
    """Price⟷value scissors dynamics coefficients (per-tick units)."""

    model_config = ConfigDict(frozen=True)

    price_reversion: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: law-of-value restoring stiffness on the log "
            "price-to-value ratio. Underdamped with price_damping=0.15 so "
            "prices oscillate around values (Capital Vol. III ch. 10)."
        ),
    )
    price_damping: float = Field(
        default=0.15,
        ge=0.0,
        le=2.0,
        description=(
            "Behavior-tuned: velocity damping on the price oscillator; keeps "
            "the discrete Euler step stable at dt = 1 tick."
        ),
    )
    price_drive_sensitivity: float = Field(
        default=0.6,
        ge=0.0,
        le=5.0,
        description=(
            "Game design: how strongly relative value-output growth (demand "
            "pull) accelerates the price level."
        ),
    )
    fictitious_reversion: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: gravity pulling fictitious capitalization back to "
            "real capitalization (surplus_ema / capitalization_rate); weaker "
            "than price_reversion — bubbles outlive price swings (Capital "
            "Vol. III part 5)."
        ),
    )
    fictitious_damping: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Behavior-tuned: velocity damping on the fictitious-capital oscillator.",
    )
    fictitious_drive_sensitivity: float = Field(
        default=0.9,
        ge=0.0,
        le=5.0,
        description=(
            "Game design: how strongly realized-surplus growth (return-"
            "chasing) accelerates fictitious capitalization."
        ),
    )
    momentum_coupling: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description=(
            "Game design: speculation chases price momentum — the price "
            "oscillator's velocity feeds the fictitious drive "
            "(tension-on-tension)."
        ),
    )
    surplus_ema_alpha: float = Field(
        default=0.15,
        gt=0.0,
        le=1.0,
        description=(
            "Engineering: EMA smoothing for the surplus/value anchors; "
            "~13-tick (one quarter) memory at 0.15."
        ),
    )
    scissors_balance_scale: float = Field(
        default=0.5,
        gt=0.0,
        le=5.0,
        description=(
            "Engineering: tanh scale mapping the log price-to-value ratio "
            "onto the opposition Balance in [-1, 1]; 0.5 saturates near a "
            "65% price-over-value divergence."
        ),
    )
    max_abs_log: float = Field(
        default=2.0,
        gt=0.0,
        le=5.0,
        description=(
            "Engineering: hard clamp on both log ratios (e^2 ~ 7.4x "
            "divergence); momentum zeroes at the rail so the clamp cannot "
            "pump energy."
        ),
    )
    capitalization_rate: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description=(
            "Game design: expected profit rate capitalizing surplus into "
            "real capitalization K = s_ema / r (Capital Vol. III ch. 29, "
            "interest-bearing capital)."
        ),
    )
