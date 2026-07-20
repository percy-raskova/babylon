"""Volume III financial-claims coefficients (spec 024-capital-volume-iii).

Thresholds and reference scales for the surplus-value distribution, TRPF
counter-tendency, and financial-crisis-assessment layers — extracted from
module-level ``Final`` constants during the 2026-07-18
vol3-money-scissors-design honesty sweep (U2) so ``defines.yaml`` edits
actually take effect (Constitution III.1).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

COUNTER_TENDENCY_COUNT: int = 6
"""Number of TRPF counter-tendencies (Marx, *Capital* Vol. III Ch. 14).

The weight list is indexed positionally against a six-element indicator list
zipped with ``strict=True`` in ``CounterTendencyStrength.net_counter_tendency``
(``babylon.domain.economics.counter_tendencies.types``), so the length is a
hard structural requirement, not a convention.
"""

_WEIGHT_SUM_TOLERANCE: float = 1e-9
"""Absolute tolerance for the weights-sum-to-1.0 invariant (IEEE-754 slack)."""


class CapitalVolumeIIIDefines(BaseModel):
    """Volume III (surplus distribution / credit / counter-tendency) coefficients."""

    model_config = ConfigDict(frozen=True)

    debt_spiral_threshold: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "Live since U5.10: the engine divides a county's accumulated "
            "debt / annual surplus ratio by this before handing it to the "
            "defines-free catalog (ContradictionSystem._county_money_ratios, "
            "src/babylon/engine/systems/contradiction.py), so the "
            "solvent<->indebted debt_spiral opposition's balance crosses "
            "zero exactly AT this threshold — matching the "
            "credit_fragility_scale division of labour. Derived from NBER "
            "2001/2008 corporate debt-to-earnings recession analysis. Must "
            "be strictly positive: it is a live divisor, and gt=0.0 (not "
            "ge=0.0) enforces that at the schema boundary."
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
        min_length=COUNTER_TENDENCY_COUNT,
        max_length=COUNTER_TENDENCY_COUNT,
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
    credit_fragility_threshold: float = Field(
        default=1.0e-3,
        gt=0.0,
        le=1.0,
        description=(
            "Expected-loss product (default_rate * credit_spread) above "
            "which the credit_fragility signal fires. Calibrated for "
            "DECIMAL inputs: FRED BAA10Y is divided by 100 at load "
            "(factory.py), peaking at 0.0556 in Dec 2008, so with the 2% "
            "default-rate estimate the crisis-peak product is 1.11e-3 and "
            "a calm-year product (0.018 spread) is 3.6e-4. The prior "
            "hardcoded 0.02 was calibrated for PERCENT-scaled inputs and "
            "required a 100% borrowing rate to fire, so the signal was "
            "hardwired False in every modeled year (U2.3 review finding 5)."
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
    credit_fragility_scale: float = Field(
        default=1.0e-3,
        gt=0.0,
        description=(
            "Empirical: crisis reference for the credit opposition. The "
            "engine divides the credit fragility index "
            "(default_rate * spread_to_treasuries) by this before handing it "
            "to the defines-free catalog, so the accommodation⇄fragility "
            "balance crosses zero exactly AT the threshold — which requires "
            "this to equal credit_fragility_threshold (the same raw product "
            "IS the threshold). 1.0e-3 is the Dec-2008 reading — corporate "
            "bond spread 0.0556 times default rate 0.02 — matching "
            "capital_vol3.credit_fragility_threshold's own derivation."
        ),
    )
    interest_profit_share_base: float = Field(
        default=0.30,
        gt=0.0,
        lt=1.0,
        description=(
            "Calm interest share of the average rate of profit (Capital "
            "Vol. III ch. 22 — the 'purely empirical' division of profit "
            "into interest and profit of enterprise; a convention, not a "
            "law, hence player-editable). Calibration: FRED net corporate "
            "interest paid (W273RC1) / corporate profits before tax "
            "(A053RC1Q027SBEA) ~ 0.25-0.35 across non-crisis years "
            "1990-2019."
        ),
    )
    interest_profit_share_ceiling: float = Field(
        default=0.95,
        gt=0.0,
        lt=1.0,
        description=(
            "Crisis-maximum interest share of profit. Capital Vol. III "
            "ch. 22: the absolute maximum is i=r (profit of enterprise=0); "
            "the sim reserves 5% of profit for the functioning capitalist so "
            "the surplus identity's profit-of-enterprise residual stays "
            "positive, hence a strict ceiling < 1. Must exceed "
            "interest_profit_share_base."
        ),
    )
    interest_reserve_demand_gain: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Demand-side sensitivity of loan-market tightness to the "
            "reserve-army downturn signal (Capital Vol. III ch. 22 — the "
            "demand for loanable capital decides the market rate). Unit "
            "default; a mod dials crisis sensitivity of the credit system."
        ),
    )
    interest_reserve_reference: float = Field(
        default=0.08,
        ge=0.0,
        lt=1.0,
        description=(
            "Reserve-army ratio at which the demand-side liquidity scramble "
            "begins (below it, s_r=0). Calibration: BLS civilian "
            "unemployment (UNRATE) averaged ~5.8% 1948-2019; ~8% marks "
            "recession-territory onset of the scramble for means of payment "
            "(Capital Vol. III ch. 25)."
        ),
    )

    @field_validator("counter_tendency_weights")
    @classmethod
    def verify_weights_sum_to_one(cls, weights: list[float]) -> list[float]:
        """Reject a weight vector that does not sum to 1.0.

        ``net_counter_tendency`` is a plain weighted sum with no
        normalization, so a vector summing to anything other than 1.0
        rescales the entire TRPF counter-tendency signal silently — no
        exception, no diagnostic, just a wrong number propagating through
        the crisis layer. Since the 2026-07-18 honesty sweep moved this
        coefficient out of a module-level ``Final`` and into player-editable
        ``defines.yaml``, that state is reachable by a plausible edit, so it
        fails loudly at config-load time instead (Constitution III.11).

        The length is enforced separately by the field's ``min_length`` /
        ``max_length``, which run before this validator.

        Args:
            weights: Candidate counter-tendency weight vector.

        Returns:
            The weights unchanged, when they sum to 1.0.

        Raises:
            ValueError: If the weights do not sum to 1.0 within
                ``_WEIGHT_SUM_TOLERANCE``.
        """
        total = math.fsum(weights)
        if not math.isclose(total, 1.0, abs_tol=_WEIGHT_SUM_TOLERANCE):
            raise ValueError(
                f"capital_vol3.counter_tendency_weights must sum to 1.0, "
                f"got {total!r} from {weights!r} — check the "
                f"capital_vol3.counter_tendency_weights list in defines.yaml"
            )
        return weights

    @model_validator(mode="after")
    def verify_interest_share_ordering(self) -> CapitalVolumeIIIDefines:
        """Reject base >= ceiling (ch. 22: interest is bounded by profit).

        share(tau) = base + (ceiling-base)*tau must land in (0, 1) with the
        crisis ceiling above the calm base, else the endogenous rate is not
        monotone in loan-market tightness. Fails loudly at config-load
        (Constitution III.11).
        """
        if self.interest_profit_share_base >= self.interest_profit_share_ceiling:
            raise ValueError(
                f"capital_vol3.interest_profit_share_base "
                f"({self.interest_profit_share_base!r}) must be strictly below "
                f"interest_profit_share_ceiling "
                f"({self.interest_profit_share_ceiling!r}) — check defines.yaml"
            )
        return self
