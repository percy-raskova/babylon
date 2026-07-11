"""Pydantic models for Temporal Validation.

Feature: 003-hydrator-temporal-validation
Date: 2026-01-31

This module defines the data models for temporal validation of
MarxianHydrator outputs. All models are frozen (immutable) per
Constitution requirements.

See Also:
    :mod:`babylon.domain.economics.temporal`: Module overview
    :doc:`specs/003-hydrator-temporal-validation/data-model`: Full entity definitions
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from typing import Self


def _variance(values: list[float]) -> float:
    """Compute population variance of a list of values.

    Args:
        values: List of numeric values.

    Returns:
        Population variance. Returns 0.0 for empty or single-element lists.
    """
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


class DetectionMethod(StrEnum):
    """Method used to detect anomaly threshold violation.

    The temporal validation system uses a tiered approach:
    1. Z_SCORE (primary): County has ≥5 years history
    2. EMPIRICAL_THRESHOLD (fallback): County has <5 years, uses national 95th percentile
    3. BOOTSTRAP (initial): National percentile not yet computed, uses 15% threshold
    """

    Z_SCORE = "z_score"
    """Primary: County has ≥5 years history, Z-score computed from rolling stats."""

    EMPIRICAL_THRESHOLD = "empirical_threshold"
    """Fallback: County has <5 years history, uses national 95th percentile."""

    BOOTSTRAP = "bootstrap"
    """Initial: National percentile not yet computed, uses 15% conservative threshold."""


class AnomalyFlag(BaseModel, frozen=True):
    """A single anomaly flag raised during temporal validation.

    Represents a threshold violation for a specific tensor component
    during year-over-year transition analysis.

    Attributes:
        component: Which tensor component triggered the flag.
        value: The actual YoY change percentage that triggered the flag.
        threshold: The threshold that was exceeded.
        z_score: Z-score if computed (None for fallback/bootstrap methods).
        year_context: Optional context annotation (e.g., 'COVID-2020').
    """

    component: str = Field(
        ...,
        description="Which tensor component triggered the flag (e.g., 'total_v', 'dept_i_share').",
    )

    value: float = Field(
        ...,
        description="The actual YoY change percentage that triggered the flag.",
    )

    threshold: float = Field(
        ...,
        description="The threshold that was exceeded.",
    )

    z_score: float | None = Field(
        default=None,
        description="Z-score if computed (None for fallback/bootstrap methods).",
    )

    year_context: str | None = Field(
        default=None,
        description="Optional context annotation (e.g., 'COVID-2020', 'documented shock').",
    )


class TemporalTransition(BaseModel, frozen=True):
    """Year-over-year change between two consecutive ValueTensor4x3 instances.

    Represents the delta between tensors for a single county across
    consecutive years. Used for anomaly detection and trend analysis.

    Attributes:
        fips_code: 5-digit county FIPS code.
        year_from: Starting year of the transition.
        year_to: Ending year of the transition (must be year_from + 1).
        delta_total_v: Percentage change in total variable capital.
        delta_dept_shares: Percentage change in each department's V share.
        delta_profit_rate: Percentage change in profit rate (r).
        z_scores: Z-scores for each component (empty if insufficient history).
        flags_raised: Anomalies detected in this transition.
        detection_method: Which threshold method was used.
    """

    fips_code: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5-digit county FIPS code.",
    )

    year_from: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Starting year of the transition.",
    )

    year_to: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Ending year of the transition (year_from + 1).",
    )

    delta_total_v: float = Field(
        ...,
        description="Percentage change in total variable capital.",
    )

    delta_dept_shares: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage change in each department's V share. Keys: 'dept_i', 'dept_ii', 'dept_iii', 'dept_iv'.",
    )

    delta_profit_rate: float = Field(
        ...,
        description="Percentage change in profit rate (r).",
    )

    z_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Z-scores for each component (empty if insufficient history).",
    )

    flags_raised: list[AnomalyFlag] = Field(
        default_factory=list,
        description="Anomalies detected in this transition.",
    )

    detection_method: DetectionMethod = Field(
        ...,
        description="Which threshold method was used for this transition.",
    )

    @model_validator(mode="after")
    def validate_year_sequence(self) -> Self:
        """Validate that year_to equals year_from + 1."""
        if self.year_to != self.year_from + 1:
            msg = f"year_to ({self.year_to}) must equal year_from + 1 ({self.year_from + 1})"
            raise ValueError(msg)
        return self

    @property
    def is_anomalous(self) -> bool:
        """True if any flags were raised."""
        return len(self.flags_raised) > 0


class AnomalyThresholdConfig(BaseModel, frozen=True):
    """Configuration for tiered anomaly detection.

    Implements FR-002's three-tier threshold system:
    1. Z-score with rolling window (primary)
    2. Empirical 95th percentile (fallback for <5 years)
    3. Bootstrap 15% threshold (initial calibration)

    Attributes:
        z_score_k: Standard deviations for Z-score threshold.
        rolling_window_years: Years of history required for Z-score.
        empirical_percentile: Percentile for national fallback threshold.
        bootstrap_threshold: Conservative initial threshold before calibration.
        national_p95_threshold: Computed 95th percentile (None if not calibrated).
    """

    z_score_k: float = Field(
        default=2.5,
        gt=0,
        description="Standard deviations for Z-score threshold (k=2.5 ≈ 99% coverage).",
    )

    rolling_window_years: int = Field(
        default=5,
        ge=2,
        description="Years of history required for Z-score computation.",
    )

    empirical_percentile: int = Field(
        default=95,
        ge=1,
        le=99,
        description="Percentile for national fallback threshold.",
    )

    bootstrap_threshold: float = Field(
        default=0.15,
        gt=0,
        le=1,
        description="Conservative initial threshold (15%) before empirical calibration.",
    )

    national_p95_threshold: float | None = Field(
        default=None,
        description="Computed 95th percentile of national YoY changes. None if not yet calibrated.",
    )

    @property
    def fallback_threshold(self) -> float:
        """Returns the appropriate fallback threshold.

        Uses national_p95_threshold if available, otherwise bootstrap_threshold.
        """
        return self.national_p95_threshold or self.bootstrap_threshold


class SmoothedCoefficientSeries(BaseModel, frozen=True):
    """Time series of α-smoothed coefficient values.

    Implements FR-004's exponentially weighted moving average (EWMA)
    for coefficient stabilization per Constitution II.4.

    Formula: S_t = α * X_t + (1 - α) * S_{t-1}
    where α ∈ [0, 1], X_t is raw value, S_t is smoothed value.

    Attributes:
        fips_code: 5-digit county FIPS code.
        coefficient_name: Name of the coefficient being smoothed.
        alpha: Smoothing parameter α ∈ [0, 1].
        years: Years in the series, ascending order.
        raw_values: Original unsmoothed coefficient values.
        smoothed_values: EWMA-smoothed values.
        gaps: Years that were missing and skipped in smoothing.
    """

    fips_code: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5-digit county FIPS code.",
    )

    coefficient_name: str = Field(
        ...,
        description="Name of the coefficient being smoothed (e.g., 'profit_rate', 'dept_i_share').",
    )

    alpha: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Smoothing parameter α ∈ [0, 1]. α=0: full smoothing, α=1: no smoothing.",
    )

    years: list[int] = Field(
        ...,
        description="Years in the series, ascending order.",
    )

    raw_values: list[float] = Field(
        ...,
        description="Original unsmoothed coefficient values.",
    )

    smoothed_values: list[float] = Field(
        ...,
        description="EWMA-smoothed values.",
    )

    gaps: list[int] = Field(
        default_factory=list,
        description="Years that were missing and skipped in smoothing computation.",
    )

    @model_validator(mode="after")
    def validate_list_lengths(self) -> Self:
        """Validate that years, raw_values, and smoothed_values have equal length."""
        if not (len(self.years) == len(self.raw_values) == len(self.smoothed_values)):
            msg = (
                f"List lengths must match: years={len(self.years)}, "
                f"raw_values={len(self.raw_values)}, smoothed_values={len(self.smoothed_values)}"
            )
            raise ValueError(msg)
        return self

    @property
    def variance_reduction(self) -> float:
        """Ratio of smoothed variance to raw variance.

        Lower values indicate more variance reduction.
        SC-003 requires ≥40% reduction (ratio ≤ 0.6) for α=0.3.

        Returns:
            Variance ratio. Returns 1.0 for insufficient data.
        """
        if len(self.raw_values) < 2:
            return 1.0
        raw_var = _variance(self.raw_values)
        smooth_var = _variance(self.smoothed_values)
        return smooth_var / raw_var if raw_var > 0 else 1.0


class DeindustrializationSignal(BaseModel, frozen=True):
    """Comparison of Dept I (means of production) trajectories between counties.

    Implements FR-003 and FR-005: Detecting deindustrialization by comparing
    manufacturing sector (Dept I) share trajectories between a deindustrialized
    core county and an affluent suburb.

    Detroit test case: Wayne (26163) vs Oakland (26125)

    Attributes:
        core_county: FIPS code of the deindustrialized core county.
        suburb_county: FIPS code of the affluent suburb county.
        year_range: Start and end years of the comparison (inclusive).
        core_dept_i_trend: Linear regression slope of core's Dept I share.
        suburb_dept_i_trend: Linear regression slope of suburb's Dept I share.
        signal_detected: True if deindustrialization pattern is detected.
        signal_strength: Magnitude of the deindustrialization signal.
    """

    core_county: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="FIPS code of the deindustrialized core county (e.g., '26163' Wayne).",
    )

    suburb_county: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="FIPS code of the affluent suburb county (e.g., '26125' Oakland).",
    )

    year_range: tuple[int, int] = Field(
        ...,
        description="Start and end years of the comparison (inclusive).",
    )

    core_dept_i_trend: float = Field(
        ...,
        description="Linear regression slope of core county's Dept I share. Negative = declining.",
    )

    suburb_dept_i_trend: float = Field(
        ...,
        description="Linear regression slope of suburb county's Dept I share.",
    )

    signal_detected: bool = Field(
        ...,
        description="True if deindustrialization pattern is detected.",
    )

    signal_strength: float = Field(
        ...,
        description="Magnitude: suburb_trend - core_trend. Higher = stronger divergence.",
    )

    @field_validator("year_range")
    @classmethod
    def validate_year_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Validate that start year is before end year."""
        if v[0] >= v[1]:
            msg = f"year_range start ({v[0]}) must be less than end ({v[1]})"
            raise ValueError(msg)
        return v

    @property
    def core_declining(self) -> bool:
        """True if core county's Dept I share is declining."""
        return self.core_dept_i_trend < 0

    @property
    def core_stagnating(self) -> bool:
        """True if core county's Dept I share is stagnating (near-zero trend)."""
        return abs(self.core_dept_i_trend) < 0.001


class TransitionAnnotation(BaseModel, frozen=True):
    """Analyst annotation for a flagged transition.

    Implements FR-006: Allow analysts to annotate flagged transitions
    as "documented shock", "data quality issue", or other categories.

    Attributes:
        transition_key: Unique key '{fips}_{year_from}_{year_to}'.
        annotation_type: Classification of the flagged transition.
        description: Analyst's explanation of the flag.
        annotated_by: Identifier of the analyst who created the annotation.
        annotated_at: Timestamp of annotation creation.
    """

    transition_key: str = Field(
        ...,
        description="Unique key: '{fips}_{year_from}_{year_to}'.",
    )

    annotation_type: Literal[
        "documented_shock", "data_quality_issue", "structural_shift", "other"
    ] = Field(
        ...,
        description="Classification of the flagged transition.",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Analyst's explanation of the flag.",
    )

    annotated_by: str = Field(
        ...,
        min_length=1,
        description="Identifier of the analyst who created the annotation.",
    )

    annotated_at: datetime = Field(
        ...,
        description="Timestamp of annotation creation.",
    )


class TemporalValidationReport(BaseModel, frozen=True):
    """Comprehensive temporal validation report for a county or region.

    Implements FR-007: Aggregate report containing all temporal validation
    outputs for a given analysis.

    Attributes:
        fips_codes: Counties included in this report.
        year_range: Start and end years of the analysis.
        generated_at: Timestamp of report generation.
        transitions: All computed transitions, including non-anomalous.
        smoothed_series: Smoothed coefficient series by coefficient name.
        signals: Deindustrialization signals detected.
        threshold_config: Configuration used for anomaly detection.
        annotations: Analyst annotations for flagged transitions.
    """

    fips_codes: list[str] = Field(
        ...,
        min_length=1,
        description="Counties included in this report.",
    )

    year_range: tuple[int, int] = Field(
        ...,
        description="Start and end years of the analysis.",
    )

    generated_at: datetime = Field(
        ...,
        description="Timestamp of report generation.",
    )

    transitions: list[TemporalTransition] = Field(
        ...,
        description="All computed transitions, including non-anomalous.",
    )

    smoothed_series: dict[str, SmoothedCoefficientSeries] = Field(
        default_factory=dict,
        description="Smoothed coefficient series by coefficient name.",
    )

    signals: list[DeindustrializationSignal] = Field(
        default_factory=list,
        description="Deindustrialization signals detected (if multi-county comparison).",
    )

    threshold_config: AnomalyThresholdConfig = Field(
        ...,
        description="Configuration used for anomaly detection.",
    )

    annotations: list[TransitionAnnotation] = Field(
        default_factory=list,
        description="Analyst annotations for flagged transitions.",
    )

    @field_validator("year_range")
    @classmethod
    def validate_year_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Validate that start year is before end year."""
        if v[0] >= v[1]:
            msg = f"year_range start ({v[0]}) must be less than end ({v[1]})"
            raise ValueError(msg)
        return v

    @property
    def anomalous_transitions(self) -> list[TemporalTransition]:
        """Filter to only transitions with flags raised."""
        return [t for t in self.transitions if t.is_anomalous]

    @property
    def flags_by_year(self) -> dict[int, list[AnomalyFlag]]:
        """Group all flags by the year they occurred in."""
        result: dict[int, list[AnomalyFlag]] = {}
        for t in self.transitions:
            if t.flags_raised:
                year = t.year_to
                result.setdefault(year, []).extend(t.flags_raised)
        return result

    @property
    def systemic_shock_years(self) -> list[int]:
        """Years where multiple counties flagged (suggesting systemic shock).

        Helps distinguish county-specific data issues from widespread events
        like COVID-2020.

        Returns:
            List of years with 2+ flagged transitions across counties.
        """
        year_flag_counts: dict[int, int] = {}
        for t in self.anomalous_transitions:
            year_flag_counts[t.year_to] = year_flag_counts.get(t.year_to, 0) + 1

        return [y for y, count in year_flag_counts.items() if count >= 2]
