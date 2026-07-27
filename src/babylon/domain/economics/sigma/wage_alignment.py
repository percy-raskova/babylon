"""Wage-gravitation math for σ coupling 2 (Program 10 §3).

"Wages align, don't define. σ is production structure only (OCC, capital
intensity, integrated labor content). Wages gravitate toward position; the
wage–position deviation is the measured tension." — Owner Ruling 2. "target
wage ŵ(σ) monotone in σ, calibrated once per sim-year from the QCEW
cross-section (wage regression on σ over counties). Actual wage w gravitates
toward ŵ(σ) each tick with a defines-tuned rate... Deviation δ = w − ŵ(σ) is
the observable tension." — program §3.

This module implements the regression-fit and evaluation math only. The
per-tick gravitation *rate* (how fast w moves toward ŵ(σ)) is an engine
coupling — a consumption seam declared, not inserted, for U5 (see spec.md).
"""

from __future__ import annotations

from collections.abc import Sequence

from babylon.domain.economics.sigma.types import SignedCurrency, WageTargetModel
from babylon.models.types import Currency

__all__ = ["compute_wage_deviation", "compute_wage_target", "fit_linear_wage_target"]


def fit_linear_wage_target(
    sigma_values: Sequence[float],
    wage_values: Sequence[float],
) -> WageTargetModel:
    """Ordinary-least-squares fit of ŵ(σ) = slope·σ + intercept.

    Args:
        sigma_values: World-anchored σ observations (one per county in the
            calibration cross-section).
        wage_values: The corresponding QCEW wage observations, same order.

    Returns:
        The fitted :class:`~babylon.domain.economics.sigma.types.WageTargetModel`.

    Raises:
        ValueError: If fewer than 2 points are given, if the two sequences
            have different lengths, or if the σ values are degenerate (all
            equal — a vertical/undefined slope).

    Examples:
        >>> fit_linear_wage_target([-1.0, 0.0, 1.0, 2.0], [15.0, 20.0, 25.0, 30.0]).slope
        5.0
    """
    n = len(sigma_values)
    if n < 2:
        raise ValueError(f"fit_linear_wage_target requires at least 2 points, got {n}.")
    if len(wage_values) != n:
        raise ValueError(
            f"sigma_values and wage_values must have the same length, "
            f"got {n} and {len(wage_values)}."
        )

    sigma_mean = sum(sigma_values) / n
    wage_mean = sum(wage_values) / n
    numerator = sum(
        (sigma - sigma_mean) * (wage - wage_mean)
        for sigma, wage in zip(sigma_values, wage_values, strict=True)
    )
    denominator = sum((sigma - sigma_mean) ** 2 for sigma in sigma_values)
    if denominator == 0.0:
        raise ValueError(
            "fit_linear_wage_target: degenerate sigma_values (all equal to "
            f"{sigma_values[0]!r}) — the slope is undefined."
        )

    slope = numerator / denominator
    intercept = wage_mean - slope * sigma_mean
    return WageTargetModel(slope=slope, intercept=intercept, n_observations=n)


def compute_wage_target(*, sigma: float, model: WageTargetModel) -> Currency:
    """Evaluate ŵ(σ) = slope·σ + intercept for a single node.

    Args:
        sigma: The node's world-anchored σ.
        model: The fitted wage-target model (see :func:`fit_linear_wage_target`).

    Returns:
        The target wage ŵ(σ), USD.

    Raises:
        ValueError: If the linear model evaluates to a negative wage at this
            σ (Constitution III.11 Loud Failure — a negative implied wage
            means the fit's domain does not cover this σ, and that must
            surface as an error, not a silent clamp to zero).

    Examples:
        >>> from babylon.domain.economics.sigma.types import WageTargetModel
        >>> compute_wage_target(sigma=1.0, model=WageTargetModel(
        ...     slope=5.0, intercept=20.0, n_observations=4,
        ... ))
        25.0
    """
    target = model.slope * sigma + model.intercept
    if target < 0:
        raise ValueError(
            f"compute_wage_target: model evaluates to a negative wage ({target!r}) "
            f"at sigma={sigma!r} (slope={model.slope!r}, intercept={model.intercept!r}). "
            "The fit's domain does not cover this sigma — surfacing loudly rather "
            "than clamping to zero (Constitution III.11)."
        )
    return target


def compute_wage_deviation(*, actual_wage: float, target_wage: float) -> SignedCurrency:
    """δ = w − ŵ(σ) — the wage-gravitation tension (Program 10 §3).

    Args:
        actual_wage: w, the node's actual (measured) wage, USD.
        target_wage: ŵ(σ), the node's target wage from
            :func:`compute_wage_target`, USD.

    Returns:
        The signed deviation δ. Positive δ at the apex of the spectrum *is*
        the super-wage / imperial-rent share (the graded generalization of
        ``unearned_increment``).

    Examples:
        >>> compute_wage_deviation(actual_wage=30.0, target_wage=25.0)
        5.0
    """
    return actual_wage - target_wage
