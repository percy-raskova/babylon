"""Calibration module for empirical threshold computation.

Feature: 003-hydrator-temporal-validation

This module provides calibration artifacts for temporal validation:
- National 95th percentile YoY threshold computation
- Threshold persistence and loading
- Calibration artifact management

The calibrated threshold is used as a fallback when counties have
insufficient history (<5 years) for Z-score computation.

See Also:
    :mod:`babylon.economics.calibration.thresholds`: Threshold computation
"""

from __future__ import annotations

# Threshold calibration will be exported here after implementation in Phase 6
# from babylon.economics.calibration.thresholds import (
#     ThresholdCalibratorImpl,
# )

__all__: list[str] = [
    # Calibration (Phase 6)
    # "ThresholdCalibratorImpl",
]
