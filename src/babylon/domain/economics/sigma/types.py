"""Frozen Pydantic types for the σ-gradient (Spectrum of Unequal Exchange, spec-107).

Program 10 (``project/programs/10-spectrum-of-unequal-exchange.md``, ratified
2026-07-08) specifies a per-node spectrum coordinate σ composed from three
production-structure ingredients — organic composition of capital (OCC),
capital intensity (K/L), and vertically-integrated labor content (ℓ) — then
anchored onto a single world-scale axis via the Hickel ERDI / Ricci
unequal-exchange series so US counties and the eight external bloc nodes share
one coordinate system (Owner Ruling 1, program §2).

These types are pure data containers: no I/O, no engine coupling. They are
consumed by :mod:`babylon.domain.economics.sigma.components`,
:mod:`babylon.domain.economics.sigma.statistics`,
:mod:`babylon.domain.economics.sigma.composite`,
:mod:`babylon.domain.economics.sigma.anchor`, and
:mod:`babylon.domain.economics.sigma.wage_alignment`.

See Also:
    ``specs/107-sigma-gradient/spec.md``: the full functional-requirements
    contract, including which composition/normalization choices are
    Director-ruling items rather than settled math.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.types import Coefficient, Ratio, SnapToGrid

__all__ = [
    "ComponentDistributionStats",
    "ComponentWeights",
    "DistributionStats",
    "LaborContent",
    "SigmaComponents",
    "SigmaScore",
    "SignedCurrency",
    "StandardizedComponents",
    "WageTargetModel",
]

# =============================================================================
# LABOR CONTENT TYPE [0.0, infinity)
# =============================================================================

LaborContent = Annotated[
    float,
    Field(
        ge=0.0,
        description="Vertically-integrated labor-hours embodied per dollar of final output",
    ),
    SnapToGrid,
]
"""LaborContent: [0.0, inf)

The Pasinetti vertically-integrated labor coefficient ℓ (Program 10 §3): total
direct+indirect labor embodied per unit of final output, derived from the
Leontief inverse (BEA TOTAL_REQ) dotted against per-industry QCEW labor
coefficients. Distinct from :data:`babylon.models.types.LaborHours` (an
absolute labor-time quantity) — this is a *rate*, hours per dollar.
"""

# =============================================================================
# SIGMA SCORE TYPE (-infinity, +infinity)
# =============================================================================

SigmaScore = Annotated[
    float,
    Field(
        description=(
            "A z-score-standardized coordinate on the spectrum axis: 0.0 is "
            "the reference distribution's mean, positive is toward the apex "
            "(high-OCC, capital-intensive, high labor content), negative is "
            "toward the base."
        )
    ),
    SnapToGrid,
]
"""SigmaScore: (-inf, +inf)

Used both for standardized *components* (each raw ingredient expressed
relative to its own cross-sectional distribution) and for the world-anchored
composite σ (Program 10 §3's "one global axis" — Owner Ruling 1). Unbounded
because z-scores are unbounded by construction; the ratified text gives no
compression/clamping rule, so none is applied here (a Director ruling item —
see spec.md).
"""

# =============================================================================
# SIGNED CURRENCY TYPE (-infinity, +infinity)
# =============================================================================

SignedCurrency = Annotated[
    float,
    Field(description="Signed USD quantity — a gap or deviation, not a stock"),
    SnapToGrid,
]
"""SignedCurrency: (-inf, +inf)

Used for the wage-gravitation deviation δ = w − ŵ(σ) (Program 10 §3): positive
δ at the apex *is* the super-wage / imperial-rent share, the graded
generalization of ``unearned_increment``. Distinct from
:data:`babylon.models.types.Currency` (non-negative stocks like wages or
wealth) because a deviation is signed by construction.
"""


class DistributionStats(BaseModel):
    """Mean and (sample) standard deviation of a finite set of observations.

    The single reusable statistic behind both component standardization
    (:mod:`babylon.domain.economics.sigma.composite`) and world-scale
    anchoring (:mod:`babylon.domain.economics.sigma.anchor`) — Program 10's
    "normalize on the world scale" (§3) and the industry-level standardization
    it presupposes are the *same* z-score operation applied at two different
    reference distributions.

    Args:
        mean: Sample mean of the observations.
        std_dev: Sample standard deviation (ddof=1). Must be strictly
            positive — a zero-spread distribution cannot ground a z-score.
        n_observations: Count of observations the statistics were computed
            from. Must be at least 2 (a single point has no spread).

    Examples:
        >>> DistributionStats(mean=1.0, std_dev=0.5, n_observations=3)
        DistributionStats(mean=1.0, std_dev=0.5, n_observations=3)
    """

    model_config = ConfigDict(frozen=True)

    mean: float
    std_dev: float = Field(gt=0.0)
    n_observations: int = Field(ge=2)


class SigmaComponents(BaseModel):
    """Raw, unstandardized σ ingredients for one node at one point in time.

    "Node" is deliberately generic (Program 10 §3's pipeline runs the same
    three ingredients at BEA-industry×year, then county, then hex, then
    external-bloc granularity) — this type does not encode which stage
    produced it; that provenance lives in ``node_id``.

    Args:
        node_id: Opaque identifier for the producing node (a BEA industry
            code, county FIPS, hex ID, or external bloc key).
        year: Calendar year the observation applies to.
        organic_composition: OCC = K/v (capital stock over the wage bill).
        capital_intensity: K/L (capital stock per worker).
        labor_content: ℓ, the vertically-integrated labor coefficient.

    Examples:
        >>> SigmaComponents(
        ...     node_id="BEA-334", year=2020,
        ...     organic_composition=3.2, capital_intensity=185000.0,
        ...     labor_content=0.014,
        ... ).node_id
        'BEA-334'
    """

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    organic_composition: Ratio
    capital_intensity: Ratio
    labor_content: LaborContent


class ComponentWeights(BaseModel):
    """Explicit weights for combining standardized σ components.

    No defaults are supplied anywhere in this package (Constitution
    III.1 no-magic-numbers): every caller must state its weights, and the
    canonical values belong in ``GameDefines`` once a Director ruling settles
    them (spec.md's pending-defines list) — this model exists so that
    settlement, and only that settlement, is required to change to alter the
    composite.

    Args:
        weight_occ: Weight on the standardized organic-composition component.
        weight_capital_intensity: Weight on the standardized capital-intensity
            component.
        weight_labor_content: Weight on the standardized labor-content
            component.

    Raises:
        ValueError: If the three weights do not sum to 1.0 within 1e-4 (loose
            enough to absorb each ``Coefficient``'s own 1e-5 ``SnapToGrid``
            quantization, e.g. three repeating-decimal 1/3 weights) — a
            silent renormalization would hide a caller's bug (the same
            no-silent-renormalization discipline as
            :func:`babylon.domain.economics.county_exposure.load_county_exposure_map`).

    Examples:
        >>> ComponentWeights(
        ...     weight_occ=0.4, weight_capital_intensity=0.3,
        ...     weight_labor_content=0.3,
        ... ).weight_occ
        0.4
    """

    model_config = ConfigDict(frozen=True)

    weight_occ: Coefficient
    weight_capital_intensity: Coefficient
    weight_labor_content: Coefficient

    @model_validator(mode="after")
    def _check_weights_sum_to_one(self) -> ComponentWeights:
        total = self.weight_occ + self.weight_capital_intensity + self.weight_labor_content
        if abs(total - 1.0) > 1e-4:
            raise ValueError(
                f"ComponentWeights must sum to 1.0, got {total!r} "
                f"(weight_occ={self.weight_occ}, "
                f"weight_capital_intensity={self.weight_capital_intensity}, "
                f"weight_labor_content={self.weight_labor_content}). "
                "No silent renormalization — fix the caller's weights."
            )
        return self


class ComponentDistributionStats(BaseModel):
    """Cross-sectional distribution stats for each of the three raw components.

    Computed once per (year, cross-section) — e.g. across the ~107 BEA
    industries — and reused to standardize every node's
    :class:`SigmaComponents` for that year via
    :func:`babylon.domain.economics.sigma.composite.standardize_components`.

    Args:
        organic_composition: Distribution stats for OCC across the reference
            cross-section.
        capital_intensity: Distribution stats for K/L across the reference
            cross-section.
        labor_content: Distribution stats for ℓ across the reference
            cross-section.
    """

    model_config = ConfigDict(frozen=True)

    organic_composition: DistributionStats
    capital_intensity: DistributionStats
    labor_content: DistributionStats


class StandardizedComponents(BaseModel):
    """Z-score-standardized σ ingredients for one node at one point in time.

    Args:
        node_id: Opaque identifier, carried through from the source
            :class:`SigmaComponents`.
        year: Calendar year, carried through from the source
            :class:`SigmaComponents`.
        organic_composition_z: Standardized OCC.
        capital_intensity_z: Standardized K/L.
        labor_content_z: Standardized ℓ.
    """

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    organic_composition_z: SigmaScore
    capital_intensity_z: SigmaScore
    labor_content_z: SigmaScore


class WageTargetModel(BaseModel):
    """A fitted linear wage-gravitation target ŵ(σ) = slope·σ + intercept.

    Program 10 §3: "target wage ŵ(σ) monotone in σ, calibrated once per
    sim-year from the QCEW cross-section (wage regression on σ over
    counties)." This model is the OLS fit's output;
    :func:`babylon.domain.economics.sigma.wage_alignment.fit_linear_wage_target`
    produces it, :func:`babylon.domain.economics.sigma.wage_alignment.compute_wage_target`
    evaluates it.

    Args:
        slope: OLS slope (USD per unit of σ).
        intercept: OLS intercept (USD at σ=0, i.e. the world mean).
        n_observations: Count of (σ, wage) pairs the fit used. Must be at
            least 2.

    Note:
        Monotonicity (slope > 0) is an *empirical claim* Program 10 makes
        about real QCEW data (the acceptance criterion in program §7), not a
        constraint this type enforces — a fit that comes back with a
        non-positive slope is informative (the alignment premise may be
        failing), not invalid input.
    """

    model_config = ConfigDict(frozen=True)

    slope: float
    intercept: float
    n_observations: int = Field(ge=2)
