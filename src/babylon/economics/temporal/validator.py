"""Unified temporal validation facade.

Feature: 003-hydrator-temporal-validation
Phase 7: Integration & TemporalValidator Facade

This module provides the `TemporalValidatorFacade` class that combines
all temporal validation implementations into a single unified interface.

See Also:
    :mod:`babylon.economics.temporal.protocols`: TemporalValidator protocol
    :mod:`babylon.economics.temporal.transitions`: Transition computation
    :mod:`babylon.economics.temporal.anomaly`: Anomaly detection
    :mod:`babylon.economics.temporal.smoothing`: Coefficient smoothing
    :mod:`babylon.economics.temporal.signals`: Deindustrialization detection
    :mod:`babylon.economics.temporal.reports`: Report generation
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from babylon.economics.temporal.anomaly import AnomalyDetectorImpl
from babylon.economics.temporal.models import (
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
)
from babylon.economics.temporal.reports import ReportGeneratorImpl
from babylon.economics.temporal.signals import DeindustrializationDetectorImpl
from babylon.economics.temporal.smoothing import CoefficientSmootherImpl
from babylon.economics.temporal.transitions import TransitionComputerImpl

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator


class TemporalValidatorFacade:
    """Unified facade for all temporal validation operations.

    Composes all temporal validation implementations into a single
    interface that satisfies the `TemporalValidator` protocol.

    This facade provides a clean API for clients who need temporal
    validation without managing multiple implementation classes.

    Attributes:
        hydrator: MarxianHydrator instance for data access.

    Example:
        >>> validator = TemporalValidatorFacade(hydrator=my_hydrator)
        >>> signal = validator.detect_deindustrialization("26163", "26125", [2020, 2021, 2022])
        >>> report = validator.generate_report("26163", [2020, 2021, 2022], config)
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize facade with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator
        self._transition_computer = TransitionComputerImpl(hydrator)
        self._anomaly_detector = AnomalyDetectorImpl(hydrator)
        self._smoother = CoefficientSmootherImpl(hydrator)
        self._signal_detector = DeindustrializationDetectorImpl(hydrator)
        self._report_generator = ReportGeneratorImpl(hydrator)

    # =====================================================================
    # TransitionComputer Protocol
    # =====================================================================

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

        Raises:
            ValueError: If year_to != year_from + 1.
            DataNotFoundError: If tensor data missing for either year.
        """
        return self._transition_computer.compute_transition(fips, year_from, year_to)

    # =====================================================================
    # AnomalyDetector Protocol
    # =====================================================================

    def detect_anomalies(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig,
    ) -> list[TemporalTransition]:
        """Detect anomalous transitions across year range.

        Args:
            fips: 5-digit county FIPS code.
            years: Years to analyze (transitions computed between consecutive years).
            config: Threshold configuration for detection.

        Returns:
            List of all TemporalTransitions (anomalous and non-anomalous).
            Check transition.is_anomalous to filter.

        Raises:
            ValueError: If years sequence has fewer than 2 elements.
        """
        return self._anomaly_detector.detect_anomalies(fips, years, config)

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
        return self._anomaly_detector.compute_z_scores(fips, years, component)

    # =====================================================================
    # CoefficientSmoother Protocol
    # =====================================================================

    def smooth_coefficients(
        self,
        fips: str,
        years: Sequence[int],
        coefficient: str,
        alpha: float,
    ) -> SmoothedCoefficientSeries:
        """Compute α-smoothed coefficient series.

        Formula: S_t = α * X_t + (1 - α) * S_{t-1}

        Args:
            fips: 5-digit county FIPS code.
            years: Years to include in series.
            coefficient: Name of coefficient to smooth.
            alpha: Smoothing parameter ∈ [0, 1].
                   α=0: Full smoothing (output = first value)
                   α=1: No smoothing (output = raw values)

        Returns:
            SmoothedCoefficientSeries with raw and smoothed values.

        Raises:
            ValueError: If alpha not in [0, 1].
        """
        return self._smoother.smooth_coefficients(fips, years, coefficient, alpha)

    # =====================================================================
    # DeindustrializationDetector Protocol
    # =====================================================================

    def detect_deindustrialization(
        self,
        core_fips: str,
        suburb_fips: str,
        years: Sequence[int],
    ) -> DeindustrializationSignal:
        """Compare Dept I trajectories between core and suburb.

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
        return self._signal_detector.detect_deindustrialization(core_fips, suburb_fips, years)

    # =====================================================================
    # ReportGenerator Protocol
    # =====================================================================

    def generate_report(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig,
    ) -> TemporalValidationReport:
        """Generate comprehensive validation report.

        Args:
            fips: 5-digit county FIPS code.
            years: Year range for analysis.
            config: Threshold configuration for anomaly detection.

        Returns:
            TemporalValidationReport with all computed outputs.
        """
        return self._report_generator.generate_report(fips, years, config)
