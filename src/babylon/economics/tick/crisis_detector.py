"""Threshold-based crisis detection for the tick dynamics pipeline.

Feature: 017-simulation-tick-dynamics

Detects county-level economic crisis based on unemployment and profit rate
decline thresholds. Crisis flags trigger amplified class transitions in
the pipeline.

See Also:
    :mod:`babylon.economics.tick.system`: Pipeline orchestration
    :mod:`babylon.economics.tick.types`: CountyEconomicState.crisis
"""

from __future__ import annotations


class ThresholdCrisisDetector:
    """Detect economic crisis via threshold comparison.

    Args:
        unemployment_threshold: Unemployment rate above which crisis is
            triggered. Default 0.08 (8%).
        profit_decline_threshold: Fractional decline in profit rate above
            which crisis is triggered. Default 0.15 (15%).

    Example:
        >>> detector = ThresholdCrisisDetector()
        >>> detector.is_crisis(0.09, 0.10, 0.15)
        True
    """

    def __init__(
        self,
        unemployment_threshold: float = 0.08,
        profit_decline_threshold: float = 0.15,
    ) -> None:
        self.unemployment_threshold = unemployment_threshold
        self.profit_decline_threshold = profit_decline_threshold

    def is_crisis(
        self,
        unemployment_rate: float,
        current_profit_rate: float | None,
        previous_profit_rate: float | None,
    ) -> bool:
        """Determine if economic conditions indicate crisis.

        Args:
            unemployment_rate: Current county unemployment rate.
            current_profit_rate: Current profit rate (None if unavailable).
            previous_profit_rate: Previous profit rate (None if unavailable).

        Returns:
            True if any crisis threshold is exceeded.
        """
        # Check unemployment threshold
        if unemployment_rate > self.unemployment_threshold:
            return True

        # Check profit rate decline (only if both rates are available and positive)
        if (
            current_profit_rate is not None
            and previous_profit_rate is not None
            and previous_profit_rate > 0
        ):
            decline = (previous_profit_rate - current_profit_rate) / previous_profit_rate
            if decline > self.profit_decline_threshold:
                return True

        return False


__all__ = ["ThresholdCrisisDetector"]
