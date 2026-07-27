"""World-scale anchoring for the composite σ (Program 10 §3, Owner Ruling 1).

"Axis scope: ONE global axis. US hexes occupy the upper band; internal
core-periphery emerges as domestic band structure on the same scale as the
world periphery; external boundary nodes sit low on it." — Owner Ruling 1,
``project/programs/10-spectrum-of-unequal-exchange.md`` §2.

This module names the *second* z-score stage explicitly (the composite σ,
already standardized across BEA industries by
:mod:`babylon.domain.economics.sigma.composite`, is standardized again
against a world-scale distribution) so consumers have one clearly-cited
entry point for "anchor this composite onto the shared world axis," even
though the arithmetic is the same
:func:`babylon.domain.economics.sigma.statistics.z_score` operation. See
``specs/107-sigma-gradient/spec.md`` for the disclosed gap in what data
currently grounds ``world_stats`` (the Hickel ERDI series is a single
national aggregate, not per-bloc; the Ricci/Andrea-Ricci unequal-exchange
series exists only as an in-repo CSV, not a live reference-DB table — a
Director ruling item, not resolved by this module).
"""

from __future__ import annotations

from babylon.domain.economics.sigma.statistics import z_score
from babylon.domain.economics.sigma.types import DistributionStats, SigmaScore

__all__ = ["anchor_to_world_scale"]


def anchor_to_world_scale(raw_composite: SigmaScore, world_stats: DistributionStats) -> SigmaScore:
    """Standardize a node's raw composite σ against the world-scale distribution.

    Args:
        raw_composite: The node's raw composite σ (output of
            :func:`babylon.domain.economics.sigma.composite.compose_sigma`).
        world_stats: Mean/std_dev of raw composite σ across the world-scale
            reference sample (e.g. the 8 external bloc nodes + rest-of-USA;
            computed via
            :func:`babylon.domain.economics.sigma.statistics.compute_distribution_stats`).

    Returns:
        The world-anchored σ: 0.0 at the world mean, positive toward the
        apex (Owner Ruling 1's "upper band"), negative toward the base.

    Examples:
        >>> from babylon.domain.economics.sigma.types import DistributionStats
        >>> anchor_to_world_scale(2.5, DistributionStats(mean=0.0, std_dev=1.0, n_observations=9))
        2.5
    """
    return z_score(raw_composite, world_stats)
