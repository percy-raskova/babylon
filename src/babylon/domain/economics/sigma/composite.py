"""Compose the three σ ingredients into a single standardized coordinate.

Program 10 §3 specifies *what* the three ingredients are (OCC, capital
intensity, ℓ) but not *how* to combine them into one scalar — the ratified
text says only "Composite σ per BEA-industry×year" with no stated weighting
or normalization scheme. This module makes an explicit, documented design
choice for that gap (z-score standardization of each raw component against
its own cross-sectional distribution, then an explicitly-weighted linear
combination) and flags the choice as a Director-ruling item rather than
treating it as settled theory — see ``specs/107-sigma-gradient/spec.md``
Decision D1.
"""

from __future__ import annotations

from babylon.domain.economics.sigma.statistics import z_score
from babylon.domain.economics.sigma.types import (
    ComponentDistributionStats,
    ComponentWeights,
    SigmaComponents,
    SigmaScore,
    StandardizedComponents,
)

__all__ = ["compose_sigma", "standardize_components"]


def standardize_components(
    components: SigmaComponents,
    stats: ComponentDistributionStats,
) -> StandardizedComponents:
    """Z-score-standardize each raw ingredient against its own distribution.

    Args:
        components: The node's raw OCC/K-L/ℓ observation.
        stats: The reference cross-section's per-component distribution
            (typically computed once per year across all BEA industries via
            :func:`babylon.domain.economics.sigma.statistics.compute_distribution_stats`).

    Returns:
        The standardized components, with ``node_id``/``year`` carried
        through unchanged.

    Examples:
        >>> from babylon.domain.economics.sigma.types import DistributionStats
        >>> stats = ComponentDistributionStats(
        ...     organic_composition=DistributionStats(mean=3.0, std_dev=1.0, n_observations=10),
        ...     capital_intensity=DistributionStats(
        ...         mean=100_000.0, std_dev=50_000.0, n_observations=10
        ...     ),
        ...     labor_content=DistributionStats(mean=0.02, std_dev=0.01, n_observations=10),
        ... )
        >>> components = SigmaComponents(
        ...     node_id="BEA-334", year=2020,
        ...     organic_composition=4.0, capital_intensity=150_000.0, labor_content=0.03,
        ... )
        >>> standardize_components(components, stats).organic_composition_z
        1.0
    """
    return StandardizedComponents(
        node_id=components.node_id,
        year=components.year,
        organic_composition_z=z_score(components.organic_composition, stats.organic_composition),
        capital_intensity_z=z_score(components.capital_intensity, stats.capital_intensity),
        labor_content_z=z_score(components.labor_content, stats.labor_content),
    )


def compose_sigma(
    standardized: StandardizedComponents,
    weights: ComponentWeights,
) -> SigmaScore:
    """Weighted sum of the three standardized components — the raw composite σ.

    Args:
        standardized: The node's z-score-standardized OCC/K-L/ℓ.
        weights: Explicit, caller-supplied weights (no hardcoded default —
            the canonical values are a pending ``GameDefines`` addition
            gated on a Director ruling; see spec.md).

    Returns:
        The raw composite σ, before world-scale anchoring (see
        :func:`babylon.domain.economics.sigma.anchor.anchor_to_world_scale`).

    Examples:
        >>> standardized = StandardizedComponents(
        ...     node_id="BEA-334", year=2020,
        ...     organic_composition_z=1.0, capital_intensity_z=1.0, labor_content_z=1.0,
        ... )
        >>> weights = ComponentWeights(
        ...     weight_occ=1/3, weight_capital_intensity=1/3, weight_labor_content=1/3,
        ... )
        >>> round(compose_sigma(standardized, weights), 6)
        1.0
    """
    return (
        standardized.organic_composition_z * weights.weight_occ
        + standardized.capital_intensity_z * weights.weight_capital_intensity
        + standardized.labor_content_z * weights.weight_labor_content
    )
