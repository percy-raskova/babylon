"""Type definitions for the TRPF counter-tendencies module.

Feature: 024-capital-volume-iii (US5)
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# ============================================================================

COUNTER_TENDENCY_WEIGHTS: Final[list[float]] = [0.20, 0.15, 0.15, 0.15, 0.20, 0.15]
"""Weights for the six TRPF counter-tendencies in net strength computation.

Order: [exploitation_rate, wage_suppression, capital_cheapening,
        reserve_army, imperial_rent, fictitious_profits]

Traceability: MLM-TW theory weights imperial rent (0.20) and exploitation
rate increase (0.20) higher than other counter-tendencies because these
are the primary mechanisms sustaining core profit rates. The remaining
four tendencies receive equal weight (0.15 each). Sum = 1.0.
"""

IMPERIAL_RENT_REFERENCE_SCALE: Final[float] = 500_000_000_000.0
"""Reference scale for imperial rent normalization (dollars).

Imperial rent flows are normalized to [0, 1] via::

    normalized = min(imperial_rent_flow / IMPERIAL_RENT_REFERENCE_SCALE, 1.0)

This makes the counter-tendency weight proportional to the actual
magnitude of unequal exchange (Marx V3 Ch14 §V), capping at 1.0
when the flow reaches the reference scale.

Traceability: The default $500B corresponds approximately to the annual
net value transfer from Global South to Global North estimated by
Cope (2012), *Divided World Divided Class*.  This constant is intended
to be tunable: a future imperial rent specification may replace it
with a GameDefines-sourced parameter calibrated against FRED trade data.
"""

_IMPERIAL_RENT_EPSILON: Final[float] = 1e-10
"""Epsilon for imperial rent normalization (prevents division by zero)."""


class CounterTendencyStrength(BaseModel):
    """Aggregate measure of six TRPF counter-tendencies.

    Feature: 024-capital-volume-iii (FR-010, FR-011)

    Tracks the six counter-tendencies to the tendency of the rate of
    profit to fall (Capital Vol. III, Ch. 14):

    1. Increasing exploitation rate (rising s/v)
    2. Wage suppression (productivity-wage gap)
    3. Cheapening of constant capital elements
    4. Relative surplus population (reserve army)
    5. Imperial rent / unequal exchange
    6. Fictitious profits (financial sector)

    The computed ``net_counter_tendency`` is a weighted sum using
    :data:`COUNTER_TENDENCY_WEIGHTS`. Positive values indicate
    counter-tendencies dominating; negative indicates TRPF dominating.

    Args:
        year: Calendar year.
        exploitation_rate_change: Year-over-year change in s/v ratio.
        wage_suppression: Productivity growth minus wage growth gap (>= 0).
        constant_capital_cheapening: Rate of change in capital goods prices.
        reserve_army_size: U-6 unemployment rate [0, 1].
        imperial_rent_flow: Net unequal exchange Phi (dollars, >= 0).
        fictitious_profit_share: Financial sector share of total profits [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040)
    exploitation_rate_change: float = Field(default=0.0, description="Delta(s/v) YoY")
    wage_suppression: float = Field(
        default=0.0, ge=0.0, description="Productivity growth - wage growth gap"
    )
    constant_capital_cheapening: float = Field(
        default=0.0, description="Rate of decline in capital goods prices"
    )
    reserve_army_size: float = Field(default=0.0, ge=0.0, le=1.0, description="U-6 unemployment")
    imperial_rent_flow: float = Field(default=0.0, ge=0.0, description="Net unequal exchange Phi")
    fictitious_profit_share: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Financial sector profit share"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def net_counter_tendency(self) -> float:
        """Weighted sum of counter-tendency indicators.

        Positive = counter-tendencies dominating (profit rate sustained).
        Negative = TRPF dominating (profit rate falling).

        Indicator mapping:

        - [0] exploitation_rate_change: direct (rising s/v = positive CT)
        - [1] wage_suppression: direct (gap = positive CT)
        - [2] -constant_capital_cheapening: inverted (negative price change
          = cheapening = positive CT)
        - [3] reserve_army_size: direct (high unemployment = positive CT)
        - [4] imperial_rent_flow: linear normalization against
          ``IMPERIAL_RENT_REFERENCE_SCALE``, capped at 1.0.
          The *magnitude* of unequal exchange matters (Marx V3 Ch14 §V).
        - [5] fictitious_profit_share: direct
        """
        # Magnitude-sensitive normalization: larger flows → stronger CT.
        # Capped at 1.0 at the reference scale. Extensible: adjust
        # IMPERIAL_RENT_REFERENCE_SCALE to recalibrate.
        imperial_normalized = min(
            self.imperial_rent_flow / max(IMPERIAL_RENT_REFERENCE_SCALE, _IMPERIAL_RENT_EPSILON),
            1.0,
        )

        indicators: list[float] = [
            self.exploitation_rate_change,
            self.wage_suppression,
            -self.constant_capital_cheapening,
            self.reserve_army_size,
            imperial_normalized,
            self.fictitious_profit_share,
        ]
        return sum(w * v for w, v in zip(indicators, COUNTER_TENDENCY_WEIGHTS, strict=True))
