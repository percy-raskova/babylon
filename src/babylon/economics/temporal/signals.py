"""Deindustrialization signal detection.

Feature: 003-hydrator-temporal-validation
User Story 1: Detect Deindustrialization Signal

This module implements FR-003 and FR-005: Compare Dept I trajectories
between deindustrialized core and affluent suburb counties.

See Also:
    :mod:`babylon.economics.temporal.protocols`: DeindustrializationDetector protocol
    :mod:`babylon.economics.temporal.models`: DeindustrializationSignal model
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from babylon.economics.temporal.models import DeindustrializationSignal

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator


def compute_trend(years: Sequence[int], values: Sequence[float]) -> float:
    """Compute linear regression slope for a time series.

    Uses ordinary least squares to fit y = mx + b and returns slope m.

    Formula:
        m = Σ((x - x̄)(y - ȳ)) / Σ((x - x̄)²)

    Args:
        years: Sequence of years (x values).
        values: Sequence of corresponding values (y values).

    Returns:
        Linear regression slope (change per year).

    Raises:
        ValueError: If fewer than 2 points provided.
        ValueError: If years and values have different lengths.

    Example:
        >>> compute_trend([2018, 2019, 2020], [0.10, 0.12, 0.14])
        0.02
    """
    if len(years) != len(values):
        msg = f"years and values must have same length: {len(years)} != {len(values)}"
        raise ValueError(msg)

    if len(years) < 2:
        msg = "Trend computation requires at least 2 data points"
        raise ValueError(msg)

    n = len(years)
    x_list = list(years)
    y_list = list(values)

    # Compute means
    x_mean = sum(x_list) / n
    y_mean = sum(y_list) / n

    # Compute slope using OLS formula
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_list, y_list, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in x_list)

    if denominator == 0:
        return 0.0

    return numerator / denominator


class DeindustrializationDetectorImpl:
    """Implementation of deindustrialization signal detection.

    Compares Dept I (means of production / manufacturing) share trajectories
    between a deindustrialized core county and an affluent suburb.

    Detroit test case: Wayne (26163) vs Oakland (26125)

    Attributes:
        hydrator: MarxianHydrator instance for tensor retrieval.
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize detector with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator

    def detect_deindustrialization(  # pragma: no mutate — temporal orchestrator
        self,
        core_fips: str,
        suburb_fips: str,
        years: Sequence[int],
    ) -> DeindustrializationSignal:
        """Compare Dept I trajectories between core and suburb.

        Detection criteria:
        1. Core shows decline OR stagnation (trend ≤ 0)
        2. Core trend is worse than suburb trend

        Args:
            core_fips: FIPS code of deindustrialized core (e.g., Wayne 26163).
            suburb_fips: FIPS code of affluent suburb (e.g., Oakland 26125).
            years: Year range for trend analysis.

        Returns:
            DeindustrializationSignal with trend slopes and detection result.

        Raises:
            ValueError: If years sequence has fewer than 2 elements.
            DataNotFoundError: If tensor data missing for either county.
        """
        years_list = list(years)  # pragma: no mutate

        if len(years_list) < 2:  # pragma: no mutate
            msg = "Deindustrialization detection requires at least 2 years"  # pragma: no mutate
            raise ValueError(msg)  # pragma: no mutate

        # Get Dept I shares for each county across years
        core_shares = self._get_dept_i_shares(core_fips, years_list)  # pragma: no mutate
        suburb_shares = self._get_dept_i_shares(suburb_fips, years_list)  # pragma: no mutate

        # Compute linear trend slopes
        core_trend = compute_trend(years_list, core_shares)  # pragma: no mutate
        suburb_trend = compute_trend(years_list, suburb_shares)  # pragma: no mutate

        # Signal detected if:
        # 1. Core is declining or stagnating (trend <= 0)
        # 2. Core trend is worse than suburb trend
        core_declining_or_stagnating = core_trend <= 0  # pragma: no mutate
        core_worse_than_suburb = core_trend < suburb_trend  # pragma: no mutate

        signal_detected = (
            core_declining_or_stagnating and core_worse_than_suburb
        )  # pragma: no mutate
        signal_strength = suburb_trend - core_trend  # pragma: no mutate

        return DeindustrializationSignal(  # pragma: no mutate
            core_county=core_fips,  # pragma: no mutate
            suburb_county=suburb_fips,  # pragma: no mutate
            year_range=(min(years_list), max(years_list)),  # pragma: no mutate
            core_dept_i_trend=core_trend,  # pragma: no mutate
            suburb_dept_i_trend=suburb_trend,  # pragma: no mutate
            signal_detected=signal_detected,  # pragma: no mutate
            signal_strength=signal_strength,  # pragma: no mutate
        )  # pragma: no mutate

    def _get_dept_i_shares(self, fips: str, years: list[int]) -> list[float]:
        """Get Dept I share for each year.

        Args:
            fips: County FIPS code.
            years: Years to retrieve.

        Returns:
            List of Dept I shares (V_I / total_V) for each year.
        """
        shares = []
        for year in years:
            tensor = self._hydrator.hydrate(fips, year)
            # Dept I share = V_I / total_V
            total_v = float(tensor.total_v)
            if total_v > 0:
                dept_i_v = float(tensor.dept_I.v)
                share = dept_i_v / total_v
            else:
                share = 0.0
            shares.append(share)
        return shares
