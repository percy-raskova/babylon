"""The Spectrum of Unequal Exchange — σ-gradient domain math (spec-107).

Program 10 (``project/programs/10-spectrum-of-unequal-exchange.md``) ratified
a per-node spectrum coordinate σ combining organic composition of capital,
capital intensity, and vertically-integrated labor content, anchored onto a
shared world-scale axis (Hickel ERDI / Ricci) so US counties and the eight
external bloc nodes are directly comparable. This package is the pure-math
layer of that spec: no engine coupling, no reference-DB I/O — every function
takes explicit, already-hydrated inputs.

Modules:
    :mod:`~babylon.domain.economics.sigma.types`: Frozen Pydantic types.
    :mod:`~babylon.domain.economics.sigma.components`: OCC, capital
        intensity, ℓ — the three raw ingredients.
    :mod:`~babylon.domain.economics.sigma.statistics`: The shared z-score
        primitive.
    :mod:`~babylon.domain.economics.sigma.composite`: Standardize + combine
        the three ingredients into a raw composite σ.
    :mod:`~babylon.domain.economics.sigma.anchor`: Anchor the composite onto
        the world-scale axis (Owner Ruling 1's "one global axis").
    :mod:`~babylon.domain.economics.sigma.wage_alignment`: The ŵ(σ)
        wage-gravitation regression (coupling 2).

See Also:
    ``specs/107-sigma-gradient/spec.md``: the full functional-requirements
    contract, disclosed data gaps, and Director-ruling items.
"""

from __future__ import annotations

from babylon.domain.economics.sigma.anchor import anchor_to_world_scale
from babylon.domain.economics.sigma.components import (
    compute_capital_intensity,
    compute_organic_composition,
    compute_vertically_integrated_labor_content,
)
from babylon.domain.economics.sigma.composite import compose_sigma, standardize_components
from babylon.domain.economics.sigma.statistics import compute_distribution_stats, z_score
from babylon.domain.economics.sigma.types import (
    ComponentDistributionStats,
    ComponentWeights,
    DistributionStats,
    LaborContent,
    SigmaComponents,
    SigmaScore,
    SignedCurrency,
    StandardizedComponents,
    WageTargetModel,
)
from babylon.domain.economics.sigma.wage_alignment import (
    compute_wage_deviation,
    compute_wage_target,
    fit_linear_wage_target,
)

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
    "anchor_to_world_scale",
    "compose_sigma",
    "compute_capital_intensity",
    "compute_distribution_stats",
    "compute_organic_composition",
    "compute_vertically_integrated_labor_content",
    "compute_wage_deviation",
    "compute_wage_target",
    "fit_linear_wage_target",
    "standardize_components",
    "z_score",
]
