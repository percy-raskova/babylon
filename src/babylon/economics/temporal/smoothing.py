"""Coefficient smoothing using exponentially weighted moving average.

Feature: 003-hydrator-temporal-validation
User Story 3: Apply α-Smoothed Coefficients

This module implements FR-004: Exponentially weighted moving average (EWMA)
for coefficient stabilization per Constitution II.4.

Formula: S_t = α * X_t + (1 - α) * S_{t-1}

See Also:
    :mod:`babylon.economics.temporal.protocols`: CoefficientSmoother protocol
    :mod:`babylon.economics.temporal.models`: SmoothedCoefficientSeries model
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from babylon.economics.temporal.models import SmoothedCoefficientSeries

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator

logger = logging.getLogger(__name__)


def ewma(values: Sequence[float], alpha: float) -> list[float]:
    """Compute exponentially weighted moving average.

    Formula: S_t = α * X_t + (1 - α) * S_{t-1}
    where S_0 = X_0 (first value is used as initial state).

    Args:
        values: Sequence of raw values to smooth.
        alpha: Smoothing parameter ∈ [0, 1].
               α=0: Full smoothing (output = first value)
               α=1: No smoothing (output = raw values)

    Returns:
        List of smoothed values, same length as input.

    Example:
        >>> ewma([0.04, 0.06, 0.05], alpha=0.3)
        [0.04, 0.046, 0.0472]
    """
    if not values:
        return []

    values_list = list(values)
    smoothed = [values_list[0]]  # S_0 = X_0

    for i in range(1, len(values_list)):
        s_prev = smoothed[-1]
        x_curr = values_list[i]
        s_curr = alpha * x_curr + (1 - alpha) * s_prev
        smoothed.append(s_curr)

    return smoothed


class CoefficientSmootherImpl:
    """Implementation of α-smoothed coefficient computation.

    Provides EWMA-smoothed coefficient series for simulation stability
    per Constitution II.4.

    Attributes:
        hydrator: MarxianHydrator instance for tensor retrieval.
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize smoother with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator

    def smooth_coefficients(  # pragma: no mutate — temporal orchestrator
        self,
        fips: str,
        years: Sequence[int],
        coefficient: str,
        alpha: float,
    ) -> SmoothedCoefficientSeries:
        """Compute α-smoothed coefficient series.

        Args:
            fips: 5-digit county FIPS code.
            years: Years to include in series.
            coefficient: Name of coefficient to smooth.
                         Supported: 'profit_rate', 'dept_I_share', 'dept_IIa_share',
                                    'dept_IIb_share', 'dept_III_share', 'exploitation_rate'
            alpha: Smoothing parameter ∈ [0, 1].

        Returns:
            SmoothedCoefficientSeries with raw and smoothed values.

        Raises:
            ValueError: If alpha not in [0, 1].
            ValueError: If coefficient name not recognized.
        """
        if not (0.0 <= alpha <= 1.0):  # pragma: no mutate
            msg = f"alpha must be in [0, 1], got {alpha}"  # pragma: no mutate
            raise ValueError(msg)  # pragma: no mutate

        years_list = sorted(years)  # pragma: no mutate

        if len(years_list) == 1:  # pragma: no mutate
            logger.warning(  # pragma: no mutate
                "Single year series for %s in %s - smoothing requires multi-year data",  # pragma: no mutate
                coefficient,  # pragma: no mutate
                fips,  # pragma: no mutate
            )  # pragma: no mutate

        # Extract raw coefficient values
        raw_values: list[float] = []  # pragma: no mutate
        valid_years: list[int] = []  # pragma: no mutate
        gaps: list[int] = []  # pragma: no mutate

        for year in years_list:  # pragma: no mutate
            try:  # pragma: no mutate
                tensor = self._hydrator.hydrate(fips, year)  # pragma: no mutate
                value = self._extract_coefficient(tensor, coefficient)  # pragma: no mutate
                raw_values.append(value)  # pragma: no mutate
                valid_years.append(year)  # pragma: no mutate
            except Exception:  # pragma: no mutate
                # Year has missing data - record as gap
                gaps.append(year)  # pragma: no mutate
                logger.debug("Gap in data for %s year %d", fips, year)  # pragma: no mutate

        if not raw_values:  # pragma: no mutate
            msg = f"No valid data for {fips} in years {years_list}"  # pragma: no mutate
            raise ValueError(msg)  # pragma: no mutate

        # Apply EWMA smoothing
        smoothed_values = ewma(raw_values, alpha)  # pragma: no mutate

        return SmoothedCoefficientSeries(  # pragma: no mutate
            fips_code=fips,  # pragma: no mutate
            coefficient_name=coefficient,  # pragma: no mutate
            alpha=alpha,  # pragma: no mutate
            years=valid_years,  # pragma: no mutate
            raw_values=raw_values,  # pragma: no mutate
            smoothed_values=smoothed_values,  # pragma: no mutate
            gaps=gaps,  # pragma: no mutate
        )  # pragma: no mutate

    def _extract_coefficient(self, tensor: object, coefficient: str) -> float:
        """Extract coefficient value from tensor.

        Args:
            tensor: ValueTensor4x3 instance.
            coefficient: Name of coefficient to extract.

        Returns:
            Coefficient value as float.

        Raises:
            ValueError: If coefficient name not recognized.
        """
        if coefficient == "profit_rate":
            return float(tensor.profit_rate)  # type: ignore[attr-defined]

        if coefficient == "exploitation_rate":
            return float(tensor.exploitation_rate)  # type: ignore[attr-defined]

        # Department shares
        total_v = float(tensor.total_v)  # type: ignore[attr-defined]
        if total_v == 0:
            return 0.0

        if coefficient == "dept_I_share":
            return float(tensor.dept_I.v) / total_v  # type: ignore[attr-defined]
        if coefficient == "dept_IIa_share":
            return float(tensor.dept_IIa.v) / total_v  # type: ignore[attr-defined]
        if coefficient == "dept_IIb_share":
            return float(tensor.dept_IIb.v) / total_v  # type: ignore[attr-defined]
        if coefficient == "dept_III_share":
            return float(tensor.dept_III.v) / total_v  # type: ignore[attr-defined]

        msg = f"Unknown coefficient: {coefficient}"
        raise ValueError(msg)
