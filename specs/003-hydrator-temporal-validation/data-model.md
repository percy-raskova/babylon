# Data Model: Hydrator Temporal Validation

**Feature**: 003-hydrator-temporal-validation
**Date**: 2026-01-30

## Overview

This document defines the Pydantic models for temporal validation of MarxianHydrator outputs. All models follow the Constitution's principle of immutability (frozen models) and use constrained types from `babylon.models`.

## Entity Definitions

### DetectionMethod (Enum)

```python
class DetectionMethod(str, Enum):
    """Method used to detect anomaly threshold violation."""

    Z_SCORE = "z_score"
    """Primary: County has ≥5 years history, Z-score computed from rolling stats."""

    EMPIRICAL_THRESHOLD = "empirical_threshold"
    """Fallback: County has <5 years history, uses national 95th percentile."""

    BOOTSTRAP = "bootstrap"
    """Initial: National percentile not yet computed, uses 15% conservative threshold."""
```

### AnomalyFlag (Model)

```python
class AnomalyFlag(BaseModel, frozen=True):
    """A single anomaly flag raised during temporal validation."""

    component: str
    """Which tensor component triggered the flag (e.g., 'total_v', 'dept_i_share')."""

    value: float
    """The actual YoY change percentage that triggered the flag."""

    threshold: float
    """The threshold that was exceeded."""

    z_score: float | None = None
    """Z-score if computed (None for fallback/bootstrap methods)."""

    year_context: str | None = None
    """Optional context annotation (e.g., 'COVID-2020', 'documented shock')."""
```

### TemporalTransition

```python
class TemporalTransition(BaseModel, frozen=True):
    """Year-over-year change between two consecutive ValueTensor4x3 instances.

    Represents the delta between tensors for a single county across
    consecutive years. Used for anomaly detection and trend analysis.
    """

    fips_code: str
    """5-digit county FIPS code."""

    year_from: int
    """Starting year of the transition."""

    year_to: int
    """Ending year of the transition (year_from + 1)."""

    # Delta percentages (positive = increase, negative = decrease)
    delta_total_v: float
    """Percentage change in total variable capital."""

    delta_dept_shares: dict[str, float]
    """Percentage change in each department's V share.
    Keys: 'dept_i', 'dept_ii', 'dept_iii', 'dept_iv'
    """

    delta_profit_rate: float
    """Percentage change in profit rate (r)."""

    # Detection results
    z_scores: dict[str, float]
    """Z-scores for each component (empty if insufficient history)."""

    flags_raised: list[AnomalyFlag]
    """Anomalies detected in this transition."""

    detection_method: DetectionMethod
    """Which threshold method was used for this transition."""

    @property
    def is_anomalous(self) -> bool:
        """True if any flags were raised."""
        return len(self.flags_raised) > 0
```

### AnomalyThresholdConfig

```python
class AnomalyThresholdConfig(BaseModel, frozen=True):
    """Configuration for tiered anomaly detection.

    Implements FR-002's three-tier threshold system:
    1. Z-score with rolling window (primary)
    2. Empirical 95th percentile (fallback for <5 years)
    3. Bootstrap 15% threshold (initial calibration)
    """

    z_score_k: float = 2.5
    """Standard deviations for Z-score threshold (k=2.5 ≈ 99% coverage)."""

    rolling_window_years: int = 5
    """Years of history required for Z-score computation."""

    empirical_percentile: int = 95
    """Percentile for national fallback threshold."""

    bootstrap_threshold: float = 0.15
    """Conservative initial threshold (15%) before empirical calibration."""

    national_p95_threshold: float | None = None
    """Computed 95th percentile of national YoY changes.
    None if not yet calibrated from data.
    """

    @property
    def fallback_threshold(self) -> float:
        """Returns the appropriate fallback threshold.

        Uses national_p95_threshold if available, otherwise bootstrap_threshold.
        """
        return self.national_p95_threshold or self.bootstrap_threshold
```

### SmoothedCoefficientSeries

```python
class SmoothedCoefficientSeries(BaseModel, frozen=True):
    """Time series of α-smoothed coefficient values.

    Implements FR-004's exponentially weighted moving average (EWMA)
    for coefficient stabilization per Constitution II.4.

    Formula: S_t = α * X_t + (1 - α) * S_{t-1}
    where α ∈ [0, 1], X_t is raw value, S_t is smoothed value.
    """

    fips_code: str
    """5-digit county FIPS code."""

    coefficient_name: str
    """Name of the coefficient being smoothed (e.g., 'profit_rate', 'dept_i_share')."""

    alpha: float
    """Smoothing parameter α ∈ [0, 1].
    α=0: Full smoothing (output = first value)
    α=1: No smoothing (output = raw values)
    """

    years: list[int]
    """Years in the series, ascending order."""

    raw_values: list[float]
    """Original unsmoothed coefficient values."""

    smoothed_values: list[float]
    """EWMA-smoothed values."""

    gaps: list[int] = []
    """Years that were missing and skipped in smoothing computation."""

    @property
    def variance_reduction(self) -> float:
        """Ratio of smoothed variance to raw variance.

        Lower values indicate more variance reduction.
        SC-003 requires ≥40% reduction (ratio ≤ 0.6) for α=0.3.
        """
        if len(self.raw_values) < 2:
            return 1.0
        raw_var = _variance(self.raw_values)
        smooth_var = _variance(self.smoothed_values)
        return smooth_var / raw_var if raw_var > 0 else 1.0
```

### DeindustrializationSignal

```python
class DeindustrializationSignal(BaseModel, frozen=True):
    """Comparison of Dept I (means of production) trajectories between counties.

    Implements FR-003 and FR-005: Detecting deindustrialization by comparing
    manufacturing sector (Dept I) share trajectories between a deindustrialized
    core county and an affluent suburb.

    Detroit test case: Wayne (26163) vs Oakland (26125)
    """

    core_county: str
    """FIPS code of the deindustrialized core county (e.g., '26163' Wayne)."""

    suburb_county: str
    """FIPS code of the affluent suburb county (e.g., '26125' Oakland)."""

    year_range: tuple[int, int]
    """Start and end years of the comparison (inclusive)."""

    core_dept_i_trend: float
    """Linear regression slope of core county's Dept I share over time.
    Negative indicates declining manufacturing share.
    """

    suburb_dept_i_trend: float
    """Linear regression slope of suburb county's Dept I share over time."""

    signal_detected: bool
    """True if deindustrialization pattern is detected.

    Detection criteria:
    - Core shows decline OR stagnation (trend ≤ 0)
    - Core trend is worse than suburb trend
    """

    signal_strength: float
    """Magnitude of the deindustrialization signal.

    Computed as: suburb_trend - core_trend
    Higher values indicate stronger deindustrialization divergence.
    """

    @property
    def core_declining(self) -> bool:
        """True if core county's Dept I share is declining."""
        return self.core_dept_i_trend < 0

    @property
    def core_stagnating(self) -> bool:
        """True if core county's Dept I share is stagnating (near-zero trend)."""
        return abs(self.core_dept_i_trend) < 0.001
```

### TransitionAnnotation

```python
class TransitionAnnotation(BaseModel, frozen=True):
    """Analyst annotation for a flagged transition.

    Implements FR-006: Allow analysts to annotate flagged transitions.
    """

    transition_key: str
    """Unique key: '{fips}_{year_from}_{year_to}'."""

    annotation_type: Literal["documented_shock", "data_quality_issue", "structural_shift", "other"]
    """Classification of the flagged transition."""

    description: str
    """Analyst's explanation of the flag."""

    annotated_by: str
    """Identifier of the analyst who created the annotation."""

    annotated_at: datetime
    """Timestamp of annotation creation."""
```

### TemporalValidationReport

```python
class TemporalValidationReport(BaseModel, frozen=True):
    """Comprehensive temporal validation report for a county or region.

    Implements FR-007: Aggregate report containing all temporal validation
    outputs for a given analysis.
    """

    fips_codes: list[str]
    """Counties included in this report."""

    year_range: tuple[int, int]
    """Start and end years of the analysis."""

    generated_at: datetime
    """Timestamp of report generation."""

    # Core outputs
    transitions: list[TemporalTransition]
    """All computed transitions, including non-anomalous."""

    smoothed_series: dict[str, SmoothedCoefficientSeries]
    """Smoothed coefficient series by coefficient name."""

    signals: list[DeindustrializationSignal]
    """Deindustrialization signals detected (if multi-county comparison)."""

    # Configuration
    threshold_config: AnomalyThresholdConfig
    """Configuration used for anomaly detection."""

    # Annotations
    annotations: list[TransitionAnnotation] = []
    """Analyst annotations for flagged transitions."""

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
        """
        # Count flags per year across all transitions
        year_flag_counts: dict[int, int] = {}
        for t in self.anomalous_transitions:
            year_flag_counts[t.year_to] = year_flag_counts.get(t.year_to, 0) + 1

        # Return years with 2+ flagged transitions (multi-county)
        return [y for y, count in year_flag_counts.items() if count >= 2]
```

## Relationships

```
AnomalyThresholdConfig
        │
        │ (configures)
        ▼
TemporalTransition ────────────► AnomalyFlag (0..*)
        │                              │
        │                              │ (annotated by)
        │                              ▼
        │                    TransitionAnnotation
        │
        │ (aggregated into)
        ▼
TemporalValidationReport ◄──── SmoothedCoefficientSeries
        │
        │ (contains)
        ▼
DeindustrializationSignal
```

## Validation Rules

1. **TemporalTransition.year_to** must equal `year_from + 1`
1. **SmoothedCoefficientSeries.alpha** must be in range [0, 1]
1. **SmoothedCoefficientSeries** lists (years, raw_values, smoothed_values) must have equal length
1. **DeindustrializationSignal.year_range** must have start < end
1. **AnomalyThresholdConfig.rolling_window_years** must be ≥ 2
1. **AnomalyThresholdConfig.empirical_percentile** must be in range [1, 99]
