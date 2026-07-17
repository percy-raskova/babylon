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
    feedback_enabled: bool = Field(
        default=True,
        description=(
            "Master gate on the Phase-2 correction feedback (ADR078). True "
            "= the snap fires into the material base (the shipped default "
            "since the promotion ceremony); False restores Phase-1 "
            "observe-only shadow behavior for byte-comparison runs."
        ),
    )
    correction_threshold_base: float = Field(
        default=0.55,
        ge=0.0,
        le=2.0,
        description=(
            "Game design: log fictitious/real divergence serviceable at ZERO "
            "profit — the credit system's intrinsic tolerance. 0.55 ~ 73% "
            "excess claims before an unprofitable economy snaps."
        ),
    )
    correction_profit_slope: float = Field(
        default=4.0,
        ge=0.0,
        le=20.0,
        description=(
            "Game design: additional serviceable log-divergence per unit "
            "profit rate — a healthy rate of profit services a larger claims "
            "structure; its FALL is what makes a given bubble unpayable "
            "(Capital Vol. III part 3 meeting part 5)."
        ),
    )
    correction_severity: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: fraction of the fictitious log-ratio closed by one "
            "snap — the violent re-identification of claims with real "
            "surplus. 1.0 = total wipeout to par in a single tick."
        ),
    )
    correction_price_severity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: fraction of the PRICE log-ratio closed by the same "
            "snap — credit tightening deflates prices toward values, less "
            "violently than it deflates claims."
        ),
    )
    correction_cooldown_ticks: int = Field(
        default=8,
        ge=1,
        le=520,
        description=(
            "Engineering: minimum ticks between snaps — one correction per "
            "crisis, not one per tick while the overhang drains."
        ),
    )
    evaporation_gain: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description=(
            "Game design: claim-holder wealth fraction destroyed per unit "
            "overhang — the fictitious wealth was counted as wealth; the "
            "snap un-counts it. Applies to bracket-0/1 roles (the ADR075 "
            "fold: bourgeoisies + petty bourgeoisie)."
        ),
    )
    unemployment_gain: float = Field(
        default=0.08,
        ge=0.0,
        le=0.5,
        description=(
            "Game design: reserve-army ratio influx per unit overhang on "
            "territories carrying a wage relation (median_wage) — the "
            "crisis disciplines labor through the reserve army."
        ),
    )
    wealth_axis_kick_gain: float = Field(
        default=0.02,
        ge=0.0,
        le=0.1,
        description=(
            "Game design: w1 velocity impulse per unit overhang on the "
            "Program-21 wealth-share axis (conservation-preserving, the "
            "spec-114 FR-114-4 impulse form) — top-bracket paper wealth "
            "deflates relative to the whole."
        ),
    )
