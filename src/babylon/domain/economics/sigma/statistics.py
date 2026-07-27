"""Reusable distribution statistics for σ standardization and world anchoring.

One operation — the z-score — grounds both stages of Program 10's pipeline:
standardizing each raw component against its own cross-sectional distribution
(:mod:`babylon.domain.economics.sigma.composite`) and anchoring the composite
σ against the world-scale distribution
(:mod:`babylon.domain.economics.sigma.anchor`). Kept here, once, rather than
duplicated per stage.
"""

from __future__ import annotations

import statistics as _stdlib_statistics
from collections.abc import Sequence

from babylon.domain.economics.sigma.types import DistributionStats, SigmaScore

__all__ = ["compute_distribution_stats", "z_score"]


def compute_distribution_stats(values: Sequence[float]) -> DistributionStats:
    """Compute sample mean and sample standard deviation (ddof=1) of ``values``.

    Args:
        values: The cross-sectional observations (e.g. OCC across ~107 BEA
            industries for one year, or raw composite σ across the world's
            external blocs).

    Returns:
        The computed :class:`DistributionStats`.

    Raises:
        ValueError: If fewer than 2 observations are given (no spread is
            computable), or if the observations have zero spread (a
            degenerate distribution cannot ground a z-score — dividing by a
            zero std_dev would be undefined, not merely uninformative).

    Examples:
        >>> compute_distribution_stats([1.0, 2.0, 3.0]).mean
        2.0
    """
    n = len(values)
    if n < 2:
        raise ValueError(f"compute_distribution_stats requires at least 2 observations, got {n}.")
    mean = _stdlib_statistics.fmean(values)
    std_dev = _stdlib_statistics.stdev(values)
    if std_dev == 0.0:
        raise ValueError(
            f"Cannot compute distribution stats: zero spread across {n} observations "
            f"(all values equal {values[0]!r}). A degenerate distribution cannot "
            "ground a z-score."
        )
    return DistributionStats(mean=mean, std_dev=std_dev, n_observations=n)


def z_score(value: float, stats: DistributionStats) -> SigmaScore:
    """Standardize ``value`` against ``stats`` — (value − mean) / std_dev.

    Args:
        value: The raw observation to standardize.
        stats: The reference distribution's mean and standard deviation.

    Returns:
        The z-score: 0.0 at the distribution's mean, positive above it,
        negative below it.

    Examples:
        >>> from babylon.domain.economics.sigma.types import DistributionStats
        >>> z_score(12.0, DistributionStats(mean=10.0, std_dev=2.0, n_observations=5))
        1.0
    """
    return (value - stats.mean) / stats.std_dev
