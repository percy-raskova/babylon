"""Anomaly detection for temporal transitions.

Feature: 003-hydrator-temporal-validation
User Story 2: Flag Anomalous Year-over-Year Jumps

This module implements FR-002: Tiered anomaly detection using:
1. Z-score with rolling window (primary, for ≥5 years history)
2. Empirical 95th percentile (fallback for <5 years)
3. Bootstrap 15% threshold (initial calibration phase)

See Also:
    :mod:`babylon.economics.temporal.protocols`: AnomalyDetector protocol
    :mod:`babylon.economics.temporal.models`: AnomalyFlag, AnomalyThresholdConfig
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from babylon.economics.temporal.models import (
    AnomalyFlag,
    AnomalyThresholdConfig,
    DetectionMethod,
    TemporalTransition,
)
from babylon.economics.temporal.transitions import (
    TransitionComputerImpl,
)

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator


def rolling_zscore(values: Sequence[float], window_size: int) -> float | None:
    """Compute Z-score for the last value using rolling statistics.

    Z-score formula: z = (x - μ) / σ
    where μ and σ are computed from the window of values.

    Args:
        values: Sequence of values (must have at least window_size elements).
        window_size: Number of values to use for computing statistics.

    Returns:
        Z-score for the last value, or None if insufficient history.
        Returns 0.0 if standard deviation is zero.

    Example:
        >>> rolling_zscore([0.10, 0.12, 0.11, 0.13, 0.25], window_size=5)
        2.83  # Approximate, 0.25 is an outlier
    """
    if len(values) < window_size:
        return None

    # Use the last window_size values
    window = list(values[-window_size:])
    n = len(window)

    # Compute mean
    mean = sum(window) / n

    # Compute standard deviation
    variance = sum((x - mean) ** 2 for x in window) / n
    std = math.sqrt(variance)

    if std == 0:
        return 0.0

    # Z-score for the last value
    last_value = window[-1]
    return (last_value - mean) / std


def select_detection_method(
    years_of_history: int,
    config: AnomalyThresholdConfig,
) -> DetectionMethod:
    """Select appropriate detection method based on data availability.

    Tiered selection per FR-002:
    1. Z_SCORE: If we have ≥ rolling_window_years of history
    2. EMPIRICAL_THRESHOLD: If we have national p95 threshold calibrated
    3. BOOTSTRAP: Otherwise use conservative 15% threshold

    Args:
        years_of_history: Number of years of available data.
        config: Threshold configuration.

    Returns:
        Appropriate DetectionMethod enum value.
    """
    if years_of_history >= config.rolling_window_years:
        return DetectionMethod.Z_SCORE

    if config.national_p95_threshold is not None:
        return DetectionMethod.EMPIRICAL_THRESHOLD

    return DetectionMethod.BOOTSTRAP


def check_threshold_violation(
    component: str,
    delta_value: float,
    z_score: float | None,
    config: AnomalyThresholdConfig,
    detection_method: DetectionMethod,
) -> AnomalyFlag | None:
    """Check if a delta value violates the threshold for the detection method.

    Args:
        component: Name of the tensor component being checked.
        delta_value: Percentage change (absolute value will be checked).
        z_score: Z-score if available (for Z_SCORE method).
        config: Threshold configuration.
        detection_method: Which detection method is being used.

    Returns:
        AnomalyFlag if threshold violated, None otherwise.
    """
    abs_delta = abs(delta_value)

    if detection_method == DetectionMethod.Z_SCORE:
        if z_score is None:
            return None
        if abs(z_score) > config.z_score_k:
            return AnomalyFlag(
                component=component,
                value=delta_value,
                threshold=config.z_score_k,
                z_score=z_score,
            )
        return None

    if detection_method == DetectionMethod.EMPIRICAL_THRESHOLD:
        threshold = config.national_p95_threshold or config.bootstrap_threshold
        if abs_delta > threshold:
            return AnomalyFlag(
                component=component,
                value=delta_value,
                threshold=threshold,
                z_score=None,
            )
        return None

    # BOOTSTRAP method
    if abs_delta > config.bootstrap_threshold:
        return AnomalyFlag(
            component=component,
            value=delta_value,
            threshold=config.bootstrap_threshold,
            z_score=None,
        )
    return None


class AnomalyDetectorImpl:
    """Implementation of tiered anomaly detection.

    Detects statistically anomalous year-over-year changes in tensor
    components using a tiered threshold system.

    Attributes:
        hydrator: MarxianHydrator instance for tensor retrieval.
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize detector with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator
        self._transition_computer = TransitionComputerImpl(hydrator)

    def detect_anomalies(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig,
    ) -> list[TemporalTransition]:
        """Detect anomalous transitions across year range.

        Args:
            fips: 5-digit county FIPS code.
            years: Years to analyze (transitions computed between consecutive).
            config: Threshold configuration for detection.

        Returns:
            List of all TemporalTransitions with flags and detection methods set.

        Raises:
            ValueError: If years sequence has fewer than 2 elements.
        """
        years_list = sorted(years)

        if len(years_list) < 2:
            msg = "Anomaly detection requires at least 2 years"
            raise ValueError(msg)

        # Collect historical deltas for Z-score computation
        delta_history: dict[str, list[float]] = {
            "total_v": [],
            "profit_rate": [],
            "dept_I": [],
            "dept_IIa": [],
            "dept_IIb": [],
            "dept_III": [],
        }

        transitions: list[TemporalTransition] = []

        for i in range(len(years_list) - 1):
            year_from = years_list[i]
            year_to = years_list[i + 1]

            # Skip non-consecutive years
            if year_to != year_from + 1:
                continue

            # Compute base transition
            transition = self._transition_computer.compute_transition(fips, year_from, year_to)

            # Update delta history
            delta_history["total_v"].append(transition.delta_total_v)
            delta_history["profit_rate"].append(transition.delta_profit_rate)
            for dept, delta in transition.delta_dept_shares.items():
                if dept in delta_history:
                    delta_history[dept].append(delta)

            # Determine detection method
            years_of_history = i + 2  # Number of years we've seen
            detection_method = select_detection_method(years_of_history, config)

            # Compute Z-scores if appropriate
            z_scores: dict[str, float] = {}
            if detection_method == DetectionMethod.Z_SCORE:
                for component, history in delta_history.items():
                    z = rolling_zscore(history, config.rolling_window_years)
                    if z is not None:
                        z_scores[component] = z

            # Check for threshold violations
            flags: list[AnomalyFlag] = []

            # Check total_v
            flag = check_threshold_violation(
                "total_v",
                transition.delta_total_v,
                z_scores.get("total_v"),
                config,
                detection_method,
            )
            if flag:
                flags.append(flag)

            # Check profit_rate
            flag = check_threshold_violation(
                "profit_rate",
                transition.delta_profit_rate,
                z_scores.get("profit_rate"),
                config,
                detection_method,
            )
            if flag:
                flags.append(flag)

            # Check department shares
            for dept, delta in transition.delta_dept_shares.items():
                flag = check_threshold_violation(
                    dept,
                    delta,
                    z_scores.get(dept),
                    config,
                    detection_method,
                )
                if flag:
                    flags.append(flag)

            # Create updated transition with detection results
            updated_transition = TemporalTransition(
                fips_code=transition.fips_code,
                year_from=transition.year_from,
                year_to=transition.year_to,
                delta_total_v=transition.delta_total_v,
                delta_dept_shares=transition.delta_dept_shares,
                delta_profit_rate=transition.delta_profit_rate,
                z_scores=z_scores,
                flags_raised=flags,
                detection_method=detection_method,
            )

            transitions.append(updated_transition)

        return transitions

    def compute_z_scores(
        self,
        fips: str,
        years: Sequence[int],
        component: str,
    ) -> dict[int, float]:
        """Compute Z-scores for a component across years.

        Args:
            fips: 5-digit county FIPS code.
            years: Years to analyze (need ≥5 for meaningful Z-scores).
            component: Tensor component name (e.g., 'total_v', 'profit_rate').

        Returns:
            Dict mapping year_to → Z-score for each transition.
            Empty dict if insufficient history.
        """
        years_list = sorted(years)

        if len(years_list) < 2:
            return {}

        # Collect deltas for the component
        deltas: list[float] = []
        year_to_list: list[int] = []

        for i in range(len(years_list) - 1):
            year_from = years_list[i]
            year_to = years_list[i + 1]

            if year_to != year_from + 1:
                continue

            # Get delta for this component
            transition = self._transition_computer.compute_transition(fips, year_from, year_to)

            if component == "total_v":
                delta = transition.delta_total_v
            elif component == "profit_rate":
                delta = transition.delta_profit_rate
            elif component in transition.delta_dept_shares:
                delta = transition.delta_dept_shares[component]
            else:
                continue

            deltas.append(delta)
            year_to_list.append(year_to)

        # Compute Z-scores
        result: dict[int, float] = {}
        window_size = 5  # Default rolling window

        for i, year_to in enumerate(year_to_list):
            if i + 1 >= window_size:
                history = deltas[: i + 1]
                z = rolling_zscore(history, window_size)
                if z is not None:
                    result[year_to] = z

        return result
