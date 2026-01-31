# Research: Hydrator Temporal Validation

**Feature**: 003-hydrator-temporal-validation
**Date**: 2026-01-30
**Phase**: 0 (Pre-Design Research)

## Executive Summary

This document captures research findings for implementing temporal validation on MarxianHydrator outputs. The existing hydrator is fully functional (145 tests passing) but lacks multi-year comparison capabilities. This feature adds Z-score anomaly detection, α-smoothing, and deindustrialization signal detection.

## Existing Code Analysis

### MarxianHydrator (`src/babylon/economics/hydrator.py`)

**Current State**: 322 lines, production-ready

**Key Methods**:

```python
def hydrate(self, fips: str, year: int) -> ValueTensor4x3:
    """Hydrate a single county-year into a Marxian value tensor."""

def hydrate_with_rent(
    self,
    core_fips: str,
    periphery_fips: str,
    year: int
) -> Tuple[ValueTensor4x3, ValueTensor4x3, ImperialRent]:
    """Hydrate two counties and compute imperial rent transfer."""
```

**Dependencies**:

- SQLAlchemy session for database access
- `DepartmentMapper` for NAICS → Department classification
- `ShadowLaborEstimator` for Department III
- `ValueTensor4x3` for output structure

**Extension Point**: The hydrator is a service class. Temporal validation can be added as a separate service that composes with the hydrator rather than modifying it.

### ValueTensor4x3 (`src/babylon/economics/tensor.py`)

**Structure**:

```python
class ValueTensor4x3(BaseModel, frozen=True):
    """4 departments × 3 value components (c, v, s)."""

    dept_i: DepartmentValues      # Means of production
    dept_ii: DepartmentValues     # Means of consumption
    dept_iii: DepartmentValues    # Reproductive labor
    dept_iv: DepartmentValues     # Luxury goods

    @property
    def total_v(self) -> Currency:
        """Sum of variable capital across all departments."""

    @property
    def profit_rate(self) -> Coefficient:
        """r = s / (c + v) across all departments."""

    @property
    def dept_i_share(self) -> Coefficient:
        """Dept I's proportion of total variable capital."""
```

**Relevant Properties for Temporal Validation**:

- `total_v`: Total variable capital
- `profit_rate`: Rate of profit
- `dept_i_share`, `dept_ii_share`, etc.: Department proportions
- `exploitation_rate`: s/v ratio
- `organic_composition`: c/v ratio

### Database Schema

**`fact_qcew_annual`**:

| Column             | Type    | Description             |
| ------------------ | ------- | ----------------------- |
| fips_code          | TEXT    | 5-digit county FIPS     |
| year               | INTEGER | Data year               |
| naics_code         | TEXT    | Industry classification |
| annual_avg_emplvl  | INTEGER | Employment level        |
| total_annual_wages | INTEGER | Total wages ($)         |
| avg_annual_pay     | INTEGER | Average pay ($)         |

**Current Coverage**:

- Years: 2021, 2022 only
- Counties: ~3,220 per year
- PRE-001 required for 2010-2022 coverage

### Test Infrastructure

**Existing Tests** (`tests/integration/economics/test_hydrator.py`):

- 145 tests covering single-year hydration
- Uses `@pytest.mark.integration` marker
- Requires database fixture for QCEW data

**Test Constants** (`tests/constants.py`):

```python
class DetroitMetro:
    WAYNE_FIPS = "26163"
    OAKLAND_FIPS = "26125"
    MACOMB_FIPS = "26099"
```

## Statistical Methodology

### Z-Score Computation

**Formula**:

```
z = (x - μ) / σ
```

Where:

- `x` = current YoY change
- `μ` = rolling mean of YoY changes (5-year window)
- `σ` = rolling standard deviation (5-year window)

**Threshold**: k = 2.5 standard deviations

**Statistical Basis**: For normal distributions, 2.5σ captures ~99% of observations. Economic data is approximately normal with heavier tails, making 2.5σ appropriately conservative.

**Implementation Note**: Use NumPy for rolling statistics:

```python
import numpy as np

def rolling_zscore(values: list[float], window: int) -> list[float | None]:
    """Compute rolling Z-scores with specified window."""
    result = []
    for i in range(len(values)):
        if i < window:
            result.append(None)  # Insufficient history
        else:
            window_data = values[i - window:i]
            mu = np.mean(window_data)
            sigma = np.std(window_data, ddof=1)  # Sample std dev
            if sigma == 0:
                result.append(0.0)  # No variance
            else:
                result.append((values[i] - mu) / sigma)
    return result
```

### α-Smoothing (EWMA)

**Formula**:

```
S_t = α * X_t + (1 - α) * S_{t-1}
```

Where:

- `S_t` = smoothed value at time t
- `X_t` = raw value at time t
- `α` = smoothing parameter ∈ [0, 1]
- `S_0` = X_0 (first value)

**Interpretation**:

- α = 0: Maximum smoothing (output = first value forever)
- α = 1: No smoothing (output = raw values)
- α = 0.3: Recommended default, balances responsiveness and stability

**Variance Reduction**:
For stationary series, EWMA reduces variance by factor ≈ α / (2 - α).
At α = 0.3: variance ratio ≈ 0.18 (82% reduction, exceeds SC-003's 40% requirement).

### Linear Trend Estimation

**For Deindustrialization Signal**:

```python
from scipy import stats

def compute_trend(years: list[int], values: list[float]) -> float:
    """Compute linear regression slope."""
    slope, _, _, _, _ = stats.linregress(years, values)
    return slope
```

**Signal Detection Criteria**:

1. Core county Dept I trend ≤ 0 (declining or stagnating)
1. Core trend < Suburb trend (divergence)

## Data Availability Analysis

### Current State (2021-2022)

```sql
SELECT year, COUNT(DISTINCT fips_code) as county_count
FROM fact_qcew_annual
GROUP BY year;
```

| Year | Counties |
| ---- | -------- |
| 2021 | 3,220    |
| 2022 | 3,220    |

### Required State (2010-2022)

PRE-001 must deliver:

- Years: 2010-2022 (13 years)
- Coverage: Detroit metro at minimum, nationwide for calibration
- Source: BLS QCEW annual data files

### Impact on Feature Components

| Component              | 2021-2022 Only          | With PRE-001         |
| ---------------------- | ----------------------- | -------------------- |
| Transition computation | ✅ Works (1 transition) | ✅ Full series       |
| Z-score detection      | ❌ Needs 5+ years       | ✅ Works 2015+       |
| Bootstrap threshold    | ✅ Works                | N/A                  |
| Empirical threshold    | ⚠️ Limited (1 YoY)      | ✅ Full calibration  |
| α-smoothing            | ⚠️ Limited value        | ✅ Meaningful series |
| Deindustrialization    | ❌ Needs trend          | ✅ 13-year trend     |

## Risks and Mitigations

### Risk 1: Insufficient Historical Data

**Probability**: High (PRE-001 pending)
**Impact**: Z-score detection and deindustrialization signal blocked
**Mitigation**: Tiered threshold fallback (BOOTSTRAP → EMPIRICAL → Z_SCORE)

### Risk 2: NAICS Reclassification

**Background**: NAICS codes were revised in 2017, potentially affecting time series consistency.
**Probability**: Medium
**Impact**: Department classification may shift mid-series
**Mitigation**:

1. Document NAICS version in tensor metadata
1. Flag transitions spanning 2016-2017 boundary
1. Use crosswalk tables if available

### Risk 3: COVID-2020 Anomaly Flooding

**Background**: 2020 will trigger massive YoY changes across all counties.
**Probability**: Certain
**Impact**: Most 2019→2020 transitions will be flagged
**Mitigation**:

1. Allow analyst annotations for "documented shock"
1. Identify systemic shocks (many counties same year) in report
1. Provide pre-annotated COVID context

### Risk 4: Performance at Scale

**Concern**: Smoothing and Z-score computation for many counties/years
**Probability**: Low
**Impact**: SC-006 violation (\<10% overhead)
**Mitigation**:

1. Use NumPy vectorized operations
1. Cache hydrated tensors during report generation
1. Lazy computation (only compute what's needed)

## Dependencies

### Existing (Already in Project)

- **Pydantic 2.x**: Model definitions, validation
- **SQLAlchemy 2.x**: Database access
- **NumPy**: Already used for matrix operations

### New Dependencies

None required. NumPy already available for statistical computation.

## Architecture Recommendation

**Pattern**: Composition over modification

```
┌─────────────────────────────────────────┐
│           TemporalValidator             │
│  (orchestrates temporal operations)     │
├─────────────────────────────────────────┤
│ - compute_transition()                  │
│ - detect_anomalies()                    │
│ - smooth_coefficients()                 │
│ - detect_deindustrialization()          │
│ - generate_report()                     │
└───────────────┬─────────────────────────┘
                │ uses
                ▼
┌─────────────────────────────────────────┐
│          MarxianHydrator                │
│     (existing, unchanged)               │
├─────────────────────────────────────────┤
│ - hydrate(fips, year)                   │
│ - hydrate_with_rent(...)                │
└─────────────────────────────────────────┘
```

**Rationale**:

1. Hydrator already works and is tested
1. Temporal validation is a separate concern
1. Follows Single Responsibility Principle
1. Enables independent testing of temporal logic

## References

- Constitution II.4: Coefficient α-smoothing requirement
- Constitution III.1: No magic constants (thresholds must trace to data)
- Constitution IV: Metro Detroit test case (Wayne vs Oakland)
- BLS QCEW Program: https://www.bls.gov/cew/
