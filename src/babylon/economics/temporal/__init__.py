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

from babylon.economics.temporal.annotations import AnnotationManagerImpl
from babylon.economics.temporal.anomaly import (
    AnomalyDetectorImpl,
    check_threshold_violation,
    rolling_zscore,
    select_detection_method,
)
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
from babylon.economics.temporal.protocols import (
    AnnotationManager,
    AnomalyDetector,
    CoefficientSmoother,
    DeindustrializationDetector,
    ReportGenerator,
    TemporalValidator,
    ThresholdCalibrator,
    TransitionComputer,
)
from babylon.economics.temporal.reports import ReportGeneratorImpl
from babylon.economics.temporal.signals import (
    DeindustrializationDetectorImpl,
    compute_trend,
)
from babylon.economics.temporal.smoothing import (
    CoefficientSmootherImpl,
    ewma,
)
from babylon.economics.temporal.transitions import (
    TransitionComputerImpl,
    compute_delta_percentage,
)
from babylon.economics.temporal.validator import TemporalValidatorFacade

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
    # Protocols
    "TransitionComputer",
    "AnomalyDetector",
    "CoefficientSmoother",
    "DeindustrializationDetector",
    "ReportGenerator",
    "TemporalValidator",
    "ThresholdCalibrator",
    "AnnotationManager",
    # Implementations (User Story 1)
    "DeindustrializationDetectorImpl",
    "compute_trend",
    # Implementations (User Story 2)
    "TransitionComputerImpl",
    "compute_delta_percentage",
    "AnomalyDetectorImpl",
    "rolling_zscore",
    "select_detection_method",
    "check_threshold_violation",
    # Implementations (User Story 3)
    "CoefficientSmootherImpl",
    "ewma",
    # Implementations (Phase 6 - Report & Calibration)
    "AnnotationManagerImpl",
    "ReportGeneratorImpl",
    # Implementations (Phase 7 - Unified Facade)
    "TemporalValidatorFacade",
]
