"""Protocol definitions for Temporal Validation.

Feature: 003-hydrator-temporal-validation
Date: 2026-01-31

This module defines the interface contracts that temporal validation
implementations must satisfy. These protocols enable dependency injection
and testing with mock implementations.

See Also:
    :mod:`babylon.domain.economics.temporal.models`: Data model definitions
    :mod:`babylon.domain.economics.temporal.validator`: Combined implementation
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.domain.economics.temporal.models import (
        AnomalyThresholdConfig,
        DeindustrializationSignal,
        SmoothedCoefficientSeries,
        TemporalTransition,
        TemporalValidationReport,
        TransitionAnnotation,
    )


class TransitionComputer(Protocol):
    """Protocol for computing year-over-year transitions.

    Implements FR-001: Compute YoY change percentages for tensor components.
    """

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
        ...


class AnomalyDetector(Protocol):
    """Protocol for detecting anomalous transitions.

    Implements FR-002: Tiered anomaly detection using Z-score, empirical
    threshold, or bootstrap threshold based on data availability.
    """

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
        ...

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
        ...


class CoefficientSmoother(Protocol):
    """Protocol for α-smoothed coefficient computation.

    Implements FR-004: Exponentially weighted moving average for coefficients.
    Satisfies Constitution II.4: "Coefficients transform slowly via α-smoothing."
    """

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
        ...


class DeindustrializationDetector(Protocol):
    """Protocol for deindustrialization signal detection.

    Implements FR-003, FR-005: Compare Dept I trajectories between
    deindustrialized core and affluent suburb counties.
    """

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
        ...


class ReportGenerator(Protocol):
    """Protocol for comprehensive report generation.

    Implements FR-007: Aggregate temporal validation outputs into
    a single report for analyst review.
    """

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
        ...


class TemporalValidator(
    TransitionComputer,
    AnomalyDetector,
    CoefficientSmoother,
    DeindustrializationDetector,
    ReportGenerator,
    Protocol,
):
    """Combined protocol for all temporal validation operations.

    This is the main interface that implementations should satisfy.
    It combines all sub-protocols into a single interface.
    """

    pass


class ThresholdCalibrator(Protocol):
    """Protocol for empirical threshold calibration.

    Implements FR-008: Compute and persist national 95th percentile
    YoY threshold from available QCEW data.
    """

    def calibrate_national_threshold(
        self,
        years: Sequence[int],
        min_counties: int = 100,
    ) -> float:
        """Compute national 95th percentile of YoY changes.

        Args:
            years: Years of data to use for calibration.
            min_counties: Minimum counties required for valid calibration.

        Returns:
            95th percentile threshold value.

        Raises:
            InsufficientDataError: If fewer than min_counties have data.
        """
        ...

    def persist_threshold(self, threshold: float, year: int) -> None:
        """Persist computed threshold as calibration artifact.

        Args:
            threshold: The computed 95th percentile value.
            year: Year of latest data used in computation.
        """
        ...

    def load_threshold(self) -> float | None:
        """Load previously computed threshold.

        Returns:
            The persisted threshold, or None if not yet calibrated.
        """
        ...


class AnnotationManager(Protocol):
    """Protocol for managing analyst annotations on flagged transitions.

    Implements FR-006: Allow analysts to annotate flagged transitions as
    "documented shock" or "data quality issue" via metadata.
    """

    def annotate_transition(
        self,
        fips: str,
        year_from: int,
        year_to: int,
        annotation_type: str,
        description: str,
        annotated_by: str,
    ) -> TransitionAnnotation:
        """Create annotation for a flagged transition.

        Args:
            fips: 5-digit county FIPS code.
            year_from: Starting year of the transition.
            year_to: Ending year of the transition.
            annotation_type: One of "documented_shock", "data_quality_issue",
                           "structural_shift", or "other".
            description: Analyst's explanation of the flag.
            annotated_by: Identifier of the analyst.

        Returns:
            TransitionAnnotation with generated transition_key and timestamp.

        Raises:
            ValueError: If annotation_type is not valid.
        """
        ...

    def get_annotations(
        self,
        fips: str | None = None,
        year: int | None = None,
    ) -> list[TransitionAnnotation]:
        """Retrieve annotations, optionally filtered by county or year.

        Args:
            fips: Optional filter by county FIPS code.
            year: Optional filter by year_to of transition.

        Returns:
            List of matching TransitionAnnotation objects.
        """
        ...

    def delete_annotation(self, transition_key: str) -> bool:
        """Remove an annotation by its transition key.

        Args:
            transition_key: Unique key '{fips}_{year_from}_{year_to}'.

        Returns:
            True if annotation was deleted, False if not found.
        """
        ...
