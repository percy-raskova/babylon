"""Year-over-year transition computation.

Feature: 003-hydrator-temporal-validation
User Story 2: Flag Anomalous Year-over-Year Jumps

This module implements FR-001: Compute YoY change percentages for
total_v, each dept's v share, and profit_rate.

See Also:
    :mod:`babylon.economics.temporal.protocols`: TransitionComputer protocol
    :mod:`babylon.economics.temporal.models`: TemporalTransition model
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.temporal.models import DetectionMethod, TemporalTransition

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator


def compute_delta_percentage(old_value: float, new_value: float) -> float:
    """Compute percentage change between two values.

    Formula: (new - old) / old

    Args:
        old_value: Previous value (denominator).
        new_value: Current value.

    Returns:
        Percentage change as decimal (0.05 = 5% increase).
        Returns 0.0 if both values are zero.
        Returns infinity if old_value is zero but new_value is not.

    Example:
        >>> compute_delta_percentage(100.0, 120.0)
        0.2
        >>> compute_delta_percentage(100.0, 80.0)
        -0.2
    """
    if old_value == 0.0:
        if new_value == 0.0:
            return 0.0
        return float("inf")

    return (new_value - old_value) / old_value


class TransitionComputerImpl:
    """Implementation of year-over-year transition computation.

    Computes delta percentages for tensor components between consecutive years.

    Attributes:
        hydrator: MarxianHydrator instance for tensor retrieval.
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize computer with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator

    def compute_transition(
        self,
        fips: str,
        year_from: int,
        year_to: int,
    ) -> TemporalTransition:
        """Compute YoY transition between consecutive years.

        Args:
            fips: 5-digit county FIPS code.
            year_from: Starting year.
            year_to: Ending year (must be year_from + 1).

        Returns:
            TemporalTransition with delta percentages for all components.
            Note: z_scores and flags_raised are empty; populate via AnomalyDetector.

        Raises:
            ValueError: If year_to != year_from + 1.
            DataNotFoundError: If tensor data missing for either year.
        """
        if year_to != year_from + 1:
            msg = f"year_to must be consecutive: expected {year_from + 1}, got {year_to}"
            raise ValueError(msg)

        # Hydrate tensors for both years
        tensor_from = self._hydrator.hydrate(fips, year_from)
        tensor_to = self._hydrator.hydrate(fips, year_to)

        # Compute delta percentages
        delta_total_v = compute_delta_percentage(
            float(tensor_from.total_v),
            float(tensor_to.total_v),
        )

        # Compute department share deltas
        # Share = dept_v / total_v
        total_v_from = float(tensor_from.total_v)
        total_v_to = float(tensor_to.total_v)

        dept_shares_from = self._compute_dept_shares(tensor_from, total_v_from)
        dept_shares_to = self._compute_dept_shares(tensor_to, total_v_to)

        delta_dept_shares = {
            dept: compute_delta_percentage(dept_shares_from[dept], dept_shares_to[dept])
            for dept in dept_shares_from
        }

        # Compute profit rate delta
        delta_profit_rate = compute_delta_percentage(
            float(tensor_from.profit_rate),
            float(tensor_to.profit_rate),
        )

        return TemporalTransition(
            fips_code=fips,
            year_from=year_from,
            year_to=year_to,
            delta_total_v=delta_total_v,
            delta_dept_shares=delta_dept_shares,
            delta_profit_rate=delta_profit_rate,
            z_scores={},  # Populated by AnomalyDetector
            flags_raised=[],  # Populated by AnomalyDetector
            detection_method=DetectionMethod.BOOTSTRAP,  # Default, updated by detector
        )

    def _compute_dept_shares(
        self,
        tensor: object,  # ValueTensor4x3
        total_v: float,
    ) -> dict[str, float]:
        """Compute department V shares from tensor.

        Args:
            tensor: ValueTensor4x3 instance.
            total_v: Total variable capital.

        Returns:
            Dict mapping department name to share (v_dept / total_v).
        """
        if total_v == 0:
            return {
                "dept_I": 0.0,
                "dept_IIa": 0.0,
                "dept_IIb": 0.0,
                "dept_III": 0.0,
            }

        return {
            "dept_I": float(tensor.dept_I.v) / total_v,  # type: ignore[attr-defined]
            "dept_IIa": float(tensor.dept_IIa.v) / total_v,  # type: ignore[attr-defined]
            "dept_IIb": float(tensor.dept_IIb.v) / total_v,  # type: ignore[attr-defined]
            "dept_III": float(tensor.dept_III.v) / total_v,  # type: ignore[attr-defined]
        }
