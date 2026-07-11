"""Threshold calibration for anomaly detection.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

This module implements FR-008: Compute and persist national 95th percentile
YoY threshold from available QCEW data.

See Also:
    :mod:`babylon.domain.economics.temporal.protocols`: ThresholdCalibrator protocol
    :mod:`babylon.domain.economics.temporal.models`: AnomalyThresholdConfig
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.domain.economics.hydrator import MarxianHydrator

logger = logging.getLogger(__name__)

# Reasonable threshold bounds
MIN_THRESHOLD = 0.0
MAX_THRESHOLD = 2.0  # 200% change is the upper bound


class ThresholdCalibratorImpl:
    """Implementation of empirical threshold calibration.

    Computes and persists national 95th percentile YoY threshold
    from available QCEW data across all counties.

    Attributes:
        calibration_dir: Directory for storing calibration artifacts.
        hydrator: MarxianHydrator instance for data access.
    """

    def __init__(
        self,
        calibration_dir: Path,
        hydrator: MarxianHydrator,
    ) -> None:
        """Initialize calibrator with storage location and data source.

        Args:
            calibration_dir: Directory for storing calibration artifacts.
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._calibration_dir = calibration_dir
        self._hydrator = hydrator
        self._artifact_path = calibration_dir / "threshold_calibration.json"

    def calibrate_national_threshold(
        self,
        years: Sequence[int],
        min_counties: int = 100,
    ) -> float:
        """Compute national 95th percentile of YoY changes.

        Collects YoY changes in total_v across all available counties
        and computes the 95th percentile as the fallback threshold.

        Args:
            years: Years of data to use for calibration.
            min_counties: Minimum counties required for valid calibration.

        Returns:
            95th percentile threshold value.

        Raises:
            ValueError: If min_counties is invalid.
            RuntimeError: If fewer than min_counties have data.
        """
        if min_counties < 1:
            msg = "min_counties must be at least 1"
            raise ValueError(msg)

        # Get all available counties from hydrator
        if self._hydrator is None:
            msg = "Hydrator is required for calibration"
            raise TypeError(msg)

        # TODO(Phase 7): Implement when hydrator exposes county iteration
        # This would require hydrator to expose list of FIPS codes.
        # The algorithm would:
        # 1. For each county, compute YoY deltas across `years`
        # 2. Collect absolute delta values
        # 3. Sort and compute 95th percentile
        #
        # Example pseudo-implementation:
        # all_deltas = []
        # for fips in self._hydrator.list_counties():
        #     transitions = self._transition_computer.compute_transitions(fips, years)
        #     all_deltas.extend([abs(t.delta_total_v) for t in transitions])
        # sorted_deltas = sorted(all_deltas)
        # p95_index = int(0.95 * len(sorted_deltas))
        # return sorted_deltas[p95_index]
        #
        # Placeholder: return bootstrap threshold
        _ = years  # Mark as used (placeholder until full implementation)
        return 0.15

    def persist_threshold(self, threshold: float, year: int) -> None:
        """Persist computed threshold as calibration artifact.

        Args:
            threshold: The computed 95th percentile value.
            year: Year of latest data used in computation.

        Raises:
            ValueError: If threshold is not positive or exceeds bounds.
        """
        if threshold <= MIN_THRESHOLD:
            msg = f"threshold must be positive, got {threshold}"
            raise ValueError(msg)
        if threshold > MAX_THRESHOLD:
            msg = f"threshold must be <= {MAX_THRESHOLD} (200%), got {threshold}"
            raise ValueError(msg)

        artifact: dict[str, Any] = {
            "threshold": threshold,
            "year": year,
            "percentile": 95,
            "calibrated_at": datetime.now().isoformat(),
        }

        # Ensure directory exists
        self._calibration_dir.mkdir(parents=True, exist_ok=True)

        with open(self._artifact_path, "w") as f:
            json.dump(artifact, f, indent=2)

        logger.info(
            "Persisted threshold calibration: %.3f (year=%d) to %s",
            threshold,
            year,
            self._artifact_path,
        )

    def load_threshold(self) -> float | None:
        """Load previously computed threshold.

        Returns:
            The persisted threshold, or None if not yet calibrated.
        """
        if not self._artifact_path.exists():
            return None

        try:
            with open(self._artifact_path) as f:
                artifact = json.load(f)
            return float(artifact["threshold"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load threshold artifact: %s", e)
            return None
