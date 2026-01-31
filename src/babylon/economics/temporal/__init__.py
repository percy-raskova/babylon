"""Temporal validation module for MarxianHydrator outputs.

Feature: 003-hydrator-temporal-validation

This module provides temporal validation capabilities including:
- Year-over-year transition computation
- Z-score anomaly detection with tiered thresholds
- Alpha-smoothed coefficient series (EWMA)
- Deindustrialization signal detection
- Comprehensive validation reports

See Also:
    :mod:`babylon.economics.temporal.models`: Pydantic entity definitions
    :mod:`babylon.economics.temporal.transitions`: Transition computation
    :mod:`babylon.economics.temporal.anomaly`: Anomaly detection
    :mod:`babylon.economics.temporal.smoothing`: Coefficient smoothing
    :mod:`babylon.economics.temporal.signals`: Deindustrialization detection
    :mod:`babylon.economics.temporal.reports`: Report generation
    :mod:`babylon.economics.temporal.annotations`: Analyst annotations
    :mod:`babylon.economics.temporal.validator`: Unified facade
"""

from __future__ import annotations

from babylon.economics.temporal.models import (
    AnomalyFlag,
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    DetectionMethod,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
    TransitionAnnotation,
)

__all__: list[str] = [
    # Models
    "DetectionMethod",
    "AnomalyFlag",
    "TemporalTransition",
    "AnomalyThresholdConfig",
    "SmoothedCoefficientSeries",
    "DeindustrializationSignal",
    "TransitionAnnotation",
    "TemporalValidationReport",
]
