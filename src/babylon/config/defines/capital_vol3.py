"""Volume III financial-claims coefficients (spec 024-capital-volume-iii).

Thresholds and reference scales for the surplus-value distribution, TRPF
counter-tendency, and financial-crisis-assessment layers — extracted from
module-level ``Final`` constants during the 2026-07-18
vol3-money-scissors-design honesty sweep (U2) so ``defines.yaml`` edits
actually take effect (Constitution III.1).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
        ge=0.0,
        le=1.0,
        description=(
            "NOT YET READ BY ANY CODE — editing this value changes nothing "
            "in the shipped game. Intended meaning: the accumulated debt / "
            "annual surplus ratio at which a county's debt spiral becomes "
            "self-reinforcing (NBER 2001/2008 corporate debt-to-earnings "
            "recession analysis). DebtAccumulation tracks accumulated_debt "
            "and consecutive_deficit_ticks but never compares either "
            "against this ratio, and no debt-spiral flag exists on any "
            "model. The consumer is owed by U5 (debt_spiral opposition); "
            "until it lands, this row is pinned dead by "
            "tests/integration/economics/test_vol3_defines_reachability_live.py."
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
