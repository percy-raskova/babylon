"""Type definitions for the TRPF counter-tendencies module.

Feature: 024-capital-volume-iii (US5)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.config.defines import GameDefines

# ============================================================================
# THRESHOLD ACCESSORS (GameDefines-backed)
# ============================================================================


@lru_cache(maxsize=1)
def _default_defines() -> GameDefines:
    """Process-cached ``GameDefines.load_default()`` for the accessors below.

    Same rationale as ``distribution.types._default_defines``: both accessors
    are read from the ``net_counter_tendency`` computed field, evaluated on
    every model access and every ``model_dump()``. Cached on FIRST USE, not at
    import time; an explicit ``defines`` argument bypasses the cache.
    """
    return GameDefines.load_default()


def counter_tendency_weights(defines: GameDefines | None = None) -> list[float]:
    """Weights for the six TRPF counter-tendencies in net strength computation.

    Order: [exploitation_rate, wage_suppression, capital_cheapening,
            reserve_army, imperial_rent, fictitious_profits]

    Traceability: MLM-TW theory weights imperial rent (0.20) and exploitation
    rate increase (0.20) higher than other counter-tendencies because these
    are the primary mechanisms sustaining core profit rates. The remaining
    four tendencies receive equal weight (0.15 each). Sum = 1.0.
    GameDefines-backed (``capital_vol3.counter_tendency_weights``) since the
    2026-07-18 honesty sweep.

    Reads ``capital_vol3.counter_tendency_weights`` from the passed
    ``defines``, or from the process-cached default when omitted.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.capital_vol3.counter_tendency_weights


def imperial_rent_reference_scale(defines: GameDefines | None = None) -> float:
    """Reference scale for imperial rent normalization (dollars).

    Imperial rent flows are normalized to [0, 1] via::

        normalized = min(imperial_rent_flow / imperial_rent_reference_scale(), 1.0)

    Traceability: The default $500B corresponds approximately to the annual
    net value transfer from Global South to Global North estimated by
    Cope (2012), *Divided World Divided Class*. GameDefines-backed
    (``capital_vol3.imperial_rent_reference_scale``) since the 2026-07-18
    honesty sweep.

    Reads ``capital_vol3.imperial_rent_reference_scale`` from the passed
    ``defines``, or from the process-cached default when omitted.
    """
    resolved = defines if defines is not None else _default_defines()
    return resolved.capital_vol3.imperial_rent_reference_scale


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
    :func:`counter_tendency_weights`. Positive values indicate
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
          :func:`imperial_rent_reference_scale`, capped at 1.0.
          The *magnitude* of unequal exchange matters (Marx V3 Ch14 §V).
        - [5] fictitious_profit_share: direct
        """
        # Magnitude-sensitive normalization: larger flows → stronger CT.
        # Capped at 1.0 at the reference scale. Extensible: edit
        # capital_vol3.imperial_rent_reference_scale in defines.yaml to
        # recalibrate — no code change needed since the 2026-07-18 sweep.
        imperial_normalized = min(
            self.imperial_rent_flow / max(imperial_rent_reference_scale(), _IMPERIAL_RENT_EPSILON),
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
        return sum(w * v for w, v in zip(indicators, counter_tendency_weights(), strict=True))
