"""Report generation for temporal validation.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

This module implements FR-007: Aggregate temporal validation outputs
into a comprehensive report for analyst review.

See Also:
    :mod:`babylon.domain.economics.temporal.protocols`: ReportGenerator protocol
    :mod:`babylon.domain.economics.temporal.models`: TemporalValidationReport
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from babylon.domain.economics.temporal.anomaly import AnomalyDetectorImpl
from babylon.domain.economics.temporal.models import (
    AnomalyThresholdConfig,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
    TransitionAnnotation,
)
from babylon.domain.economics.temporal.smoothing import CoefficientSmootherImpl

if TYPE_CHECKING:
    from babylon.domain.economics.hydrator import MarxianHydrator

logger = logging.getLogger(__name__)

# Default coefficients to smooth in reports
DEFAULT_COEFFICIENTS = [
    "profit_rate",
    "dept_I_share",
    "dept_IIa_share",
    "dept_IIb_share",
    "dept_III_share",
]


class ReportGeneratorImpl:
    """Implementation of comprehensive report generation.

    Orchestrates all temporal validation components and aggregates
    outputs into a single TemporalValidationReport.

    Attributes:
        hydrator: MarxianHydrator instance for data access.
    """

    def __init__(self, hydrator: MarxianHydrator) -> None:
        """Initialize report generator with hydrator dependency.

        Args:
            hydrator: MarxianHydrator for retrieving county tensors.
        """
        self._hydrator = hydrator
        self._anomaly_detector = AnomalyDetectorImpl(hydrator)
        self._smoother = CoefficientSmootherImpl(hydrator)

    def generate_report(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig,
        coefficients: Sequence[str] | None = None,
        alpha: float = 0.3,
        annotations: list[TransitionAnnotation] | None = None,
    ) -> TemporalValidationReport:
        """Generate comprehensive validation report.

        Orchestrates:
        1. Transition computation between consecutive years
        2. Anomaly detection using tiered thresholds
        3. Coefficient smoothing using EWMA

        Args:
            fips: 5-digit county FIPS code.
            years: Year range for analysis.
            config: Threshold configuration for anomaly detection.
            coefficients: Coefficients to smooth (default: profit_rate, dept shares).
            alpha: Smoothing parameter for EWMA (default: 0.3).
            annotations: Optional existing annotations to include.

        Returns:
            TemporalValidationReport with all computed outputs.

        Raises:
            ValueError: If years sequence has fewer than 2 elements.
        """
        years_list = sorted(years)

        if len(years_list) < 2:
            msg = "Report generation requires at least 2 years"
            raise ValueError(msg)

        # 1. Detect anomalies (includes transition computation)
        transitions = self._anomaly_detector.detect_anomalies(
            fips=fips,
            years=years_list,
            config=config,
        )

        # 2. Compute smoothed series for each coefficient
        coeffs = coefficients or DEFAULT_COEFFICIENTS
        smoothed_series: dict[str, SmoothedCoefficientSeries] = {}

        for coeff in coeffs:
            try:
                series = self._smoother.smooth_coefficients(
                    fips=fips,
                    years=years_list,
                    coefficient=coeff,
                    alpha=alpha,
                )
                smoothed_series[coeff] = series
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to smooth coefficient %s for %s: %s",
                    coeff,
                    fips,
                    e,
                )

        # 3. Build report
        return TemporalValidationReport(
            fips_codes=[fips],
            year_range=(years_list[0], years_list[-1]),
            generated_at=datetime.now(),
            transitions=transitions,
            smoothed_series=smoothed_series,
            signals=[],  # Signals are added via multi-county analysis
            threshold_config=config,
            annotations=annotations or [],
        )

    def generate_multi_county_report(
        self,
        fips_codes: list[str],
        years: Sequence[int],
        config: AnomalyThresholdConfig,
        coefficients: Sequence[str] | None = None,
        alpha: float = 0.3,
    ) -> TemporalValidationReport:
        """Generate report for multiple counties.

        Useful for detecting systemic shocks vs county-specific issues.

        Args:
            fips_codes: List of county FIPS codes.
            years: Year range for analysis.
            config: Threshold configuration.
            coefficients: Coefficients to smooth.
            alpha: Smoothing parameter.

        Returns:
            TemporalValidationReport aggregating all counties.

        Raises:
            ValueError: If years has fewer than 2 elements.
        """
        years_list = sorted(years)

        if len(years_list) < 2:
            msg = "Report generation requires at least 2 years"
            raise ValueError(msg)

        all_transitions: list[TemporalTransition] = []
        all_smoothed: dict[str, SmoothedCoefficientSeries] = {}

        for fips in fips_codes:
            # Get transitions for this county
            transitions = self._anomaly_detector.detect_anomalies(
                fips=fips,
                years=years_list,
                config=config,
            )
            all_transitions.extend(transitions)

            # Get smoothed series (key by fips_coeff)
            coeffs = coefficients or DEFAULT_COEFFICIENTS
            for coeff in coeffs:
                try:
                    series = self._smoother.smooth_coefficients(
                        fips=fips,
                        years=years_list,
                        coefficient=coeff,
                        alpha=alpha,
                    )
                    key = f"{fips}_{coeff}"
                    all_smoothed[key] = series
                except (ValueError, KeyError) as e:
                    logger.warning(
                        "Failed to smooth %s for %s: %s",
                        coeff,
                        fips,
                        e,
                    )

        return TemporalValidationReport(
            fips_codes=fips_codes,
            year_range=(years_list[0], years_list[-1]),
            generated_at=datetime.now(),
            transitions=all_transitions,
            smoothed_series=all_smoothed,
            signals=[],
            threshold_config=config,
            annotations=[],
        )
