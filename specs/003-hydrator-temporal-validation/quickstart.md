# Quickstart: Hydrator Temporal Validation

**Feature**: 003-hydrator-temporal-validation
**Date**: 2026-01-30

## Overview

This guide demonstrates how to use the temporal validation capabilities added to MarxianHydrator. These tools help detect anomalous year-over-year changes, smooth volatile coefficients, and identify deindustrialization patterns.

## Prerequisites

- QCEW data loaded for target years (see PRE-001)
- MarxianHydrator configured with database session

## Basic Usage

### 1. Compute Year-over-Year Transition

```python
from babylon.economics.temporal import TemporalValidator
from babylon.economics.temporal.models import AnomalyThresholdConfig

# Initialize validator with database session
validator = TemporalValidator(session=db_session)

# Compute transition for Wayne County 2021→2022
transition = validator.compute_transition(
    fips="26163",
    year_from=2021,
    year_to=2022
)

# Access delta percentages
print(f"Total V change: {transition.delta_total_v:.1%}")
print(f"Profit rate change: {transition.delta_profit_rate:.1%}")
print(f"Dept I share change: {transition.delta_dept_shares['dept_i']:.1%}")

# Check if anomalous
if transition.is_anomalous:
    for flag in transition.flags_raised:
        print(f"ANOMALY: {flag.component} changed by {flag.value:.1%}")
        print(f"         Threshold: {flag.threshold:.1%}, Method: {transition.detection_method}")
```

### 2. Detect Anomalies Over Time Range

```python
# Configure threshold detection
config = AnomalyThresholdConfig(
    z_score_k=2.5,              # 2.5 std devs
    rolling_window_years=5,      # 5-year baseline
    bootstrap_threshold=0.15     # 15% fallback
)

# Get all anomalous transitions for 2010-2022
transitions = validator.detect_anomalies(
    fips="26163",
    years=range(2010, 2023),
    config=config
)

# Filter to only anomalous
anomalies = [t for t in transitions if t.is_anomalous]
print(f"Found {len(anomalies)} anomalous transitions")

for t in anomalies:
    print(f"\n{t.year_from}→{t.year_to} ({t.detection_method.value}):")
    for flag in t.flags_raised:
        print(f"  - {flag.component}: {flag.value:+.1%}")
```

### 3. Apply α-Smoothing to Coefficients

```python
# Get smoothed profit rate series
series = validator.smooth_coefficients(
    fips="26163",
    years=range(2010, 2023),
    coefficient="profit_rate",
    alpha=0.3  # 30% responsiveness to new data
)

# Compare raw vs smoothed
for year, raw, smooth in zip(series.years, series.raw_values, series.smoothed_values):
    print(f"{year}: raw={raw:.3f}, smoothed={smooth:.3f}")

# Check variance reduction (SC-003: must be ≥40%)
reduction = 1 - series.variance_reduction
print(f"\nVariance reduction: {reduction:.1%}")
```

### 4. Detect Deindustrialization Signal

```python
# Compare Wayne (Detroit core) vs Oakland (affluent suburb)
signal = validator.detect_deindustrialization(
    core_fips="26163",      # Wayne County
    suburb_fips="26125",    # Oakland County
    years=range(2010, 2023)
)

print(f"Core Dept I trend: {signal.core_dept_i_trend:.4f}")
print(f"Suburb Dept I trend: {signal.suburb_dept_i_trend:.4f}")
print(f"Signal detected: {signal.signal_detected}")
print(f"Signal strength: {signal.signal_strength:.4f}")

if signal.signal_detected:
    if signal.core_declining:
        print("Wayne County shows declining manufacturing share")
    elif signal.core_stagnating:
        print("Wayne County shows stagnating manufacturing share")
```

### 5. Generate Comprehensive Report

```python
from datetime import datetime

# Generate full validation report
report = validator.generate_report(
    fips="26163",
    years=range(2010, 2023),
    config=config
)

print(f"Report generated: {report.generated_at}")
print(f"Total transitions: {len(report.transitions)}")
print(f"Anomalous transitions: {len(report.anomalous_transitions)}")

# Check for systemic shocks (multiple counties affected same year)
for year in report.systemic_shock_years:
    print(f"Systemic shock detected in {year}")

# Access smoothed series
for name, series in report.smoothed_series.items():
    print(f"Smoothed {name}: {len(series.years)} years")
```

### 6. Annotate Flagged Transitions

```python
from babylon.economics.temporal.models import TransitionAnnotation

# Create annotation for COVID year
annotation = TransitionAnnotation(
    transition_key="26163_2019_2020",
    annotation_type="documented_shock",
    description="COVID-19 pandemic caused sharp employment decline",
    annotated_by="analyst@example.com",
    annotated_at=datetime.now()
)

# Add to report (creates new immutable report)
annotated_report = report.model_copy(
    update={"annotations": report.annotations + [annotation]}
)
```

## Edge Cases

### Single Year of Data

```python
# Returns raw value with warning
series = validator.smooth_coefficients(
    fips="26163",
    years=[2022],
    coefficient="profit_rate",
    alpha=0.3
)
# series.smoothed_values == series.raw_values
# Warning logged about insufficient data for smoothing
```

### Missing Years in Series

```python
# Gap years are skipped, flagged in metadata
series = validator.smooth_coefficients(
    fips="26163",
    years=[2018, 2020, 2021],  # 2019 missing
    coefficient="profit_rate",
    alpha=0.3
)
print(f"Gaps: {series.gaps}")  # [2019]
```

### Insufficient History for Z-Score

```python
# Falls back to empirical or bootstrap threshold
transitions = validator.detect_anomalies(
    fips="26163",
    years=[2021, 2022],  # Only 2 years
    config=config
)
# Uses EMPIRICAL_THRESHOLD or BOOTSTRAP method
```

## Performance Notes

- α-smoothing adds \<10% overhead to tensor retrieval for 10-year series (SC-006)
- Z-score computation requires NumPy for rolling statistics
- Report generation caches intermediate results for multi-coefficient analysis
