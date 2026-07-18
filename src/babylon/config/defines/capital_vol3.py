"""Volume III financial-claims coefficients (spec 024-capital-volume-iii).

Thresholds and reference scales for the surplus-value distribution, TRPF
counter-tendency, and financial-crisis-assessment layers — extracted from
module-level ``Final`` constants during the 2026-07-18
vol3-money-scissors-design honesty sweep (U2) so ``defines.yaml`` edits
actually take effect (Constitution III.1).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CapitalVolumeIIIDefines(BaseModel):
    """Volume III (surplus distribution / credit / counter-tendency) coefficients."""

    model_config = ConfigDict(frozen=True)

    debt_spiral_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Accumulated debt / annual surplus ratio triggering the "
            "debt-spiral crisis flag (NBER 2001/2008 corporate "
            "debt-to-earnings recession analysis)."
        ),
    )
    distribution_epsilon: float = Field(
        default=1e-9,
        gt=0.0,
        le=1e-3,
        description=(
            "Floating-point tolerance for the surplus distribution "
            "accounting identity s = p + i + r + t (IEEE 754 double "
            "tolerance)."
        ),
    )
    counter_tendency_weights: list[float] = Field(
        default=[0.20, 0.15, 0.15, 0.15, 0.20, 0.15],
        description=(
            "Weights for the six TRPF counter-tendencies "
            "(exploitation_rate, wage_suppression, capital_cheapening, "
            "reserve_army, imperial_rent, fictitious_profits); must sum "
            "to 1.0."
        ),
    )
    imperial_rent_reference_scale: float = Field(
        default=500_000_000_000.0,
        gt=0.0,
        description=(
            "Reference scale (dollars) normalizing imperial rent flow "
            "into the counter-tendency weight; Cope (2012) annual "
            "Global South-to-North transfer estimate."
        ),
    )
    profit_rate_fallback: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "County profit rate used for the surplus-distribution "
            "interest calculation when the tensor registry has no "
            "profit_rate for this county-year."
        ),
    )
    national_county_count: int = Field(
        default=3300,
        ge=1,
        le=5000,
        description=(
            "Approximate US county count used to scale a single "
            "county's surplus up to a national proxy for the "
            "financialization ratio (FictitiousCapitalStock."
            "ratio_to_real denominator)."
        ),
    )
    default_rate_estimate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Loan default-rate estimate feeding credit_fragility. No "
            "FRED charge-off-rate series is wired for this (D4's "
            "fixture list has none) — a documented estimate, not live "
            "data; see spec 2026-07-18 vol3-money-scissors-design "
            "Table 3.6."
        ),
    )
    housing_capitalization_rate_default: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Fallback interest rate for housing ground-rent "
            "capitalization (construction-time snapshot; "
            "DefaultHousingDecompositionCalculator does not re-read a "
            "live per-tick rate)."
        ),
    )
