# Research: Capital Stock Dynamics

**Feature**: 012-capital-stock-dynamics
**Date**: 2026-02-01
**Phase**: 0 - Research

## 1. Theoretical Foundation

### 1.1 TVT Mathematical Formalization Review

From `ai-docs/brainstorms/tensor/tvt_mathematical_formalization.md`:

**Axiom A3 (Stock-Flow Consistency)**:
```
K[fips, t+1] = K[fips, t] × (1 - δ) + I[fips, t]
```

Where:
- K = Capital stock (accumulated constant capital)
- δ = Depreciation rate (fraction of capital consumed per period)
- I = Gross investment (capital flow in period t)

**Section 5.2 (Capital Stock Evolution)**:
```
K[fips, t+1] = K[fips, t] × (1 - δ) + Σ_μ c^μ[fips, t+1]
```

The investment term I[fips, t] equals Σ_μ c^μ (total constant capital flow summed across all 4 departments). This is already computed as `ValueTensor4x3.total_c`.

**TVT Section 3.6 (Profit Rate)**:
```
r[fips, t] = Σ_μ s^μ[fips, t] / (K[fips, t] + Σ_μ v^μ[fips, t])
```

This is the **stock-based** profit rate, distinct from the flow-based rate `s/(c+v)` currently in ValueTensor4x3.

### 1.2 TSSI (Temporal Single-System Interpretation)

Per TVT Axiom B2, we use historical cost valuation:
- Capital stock represents what was actually paid for means of production
- NOT current replacement cost (which would be the simultaneist interpretation)
- This is critical for TRPF analysis: capital measured at historical cost shows the tendency more clearly

### 1.3 Steady-State Initialization

For the initial period (2010), we assume steady state:
```
K_0 = I_0 / δ = c_0 / δ
```

**Derivation**: At steady state, depreciation equals investment:
```
δK = I
K = I/δ
```

With δ = 0.07 and c_0 = $10B (hypothetical), K_0 ≈ $143B.

**Error Decay**: The error from this assumption follows:
```
Error(t) = Error(0) × (1 - δ)^t
```

After 14 years (t = 14), error is reduced to ~35% of initial. After 20 years, ~24%.

## 2. Existing Codebase Patterns

### 2.1 TensorRegistry Pattern

From `src/babylon/economics/tensor_registry.py`:

```python
class TensorRegistry:
    """Cached container for tensor primitives."""

    def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel
    def get_aggregate(self, level: GeoLevel, code: str, year: int) -> ...
    def put(self, fips: str, year: int, tensor: ValueTensor4x3) -> None
    def hydrate_counties(self, hydrator: CountyHydrator, fips_codes: Sequence[str], years: Sequence[int]) -> None
```

**Key patterns to follow**:
1. Thread-safe access via `threading.RLock()`
2. LRU caching for aggregates via `functools.lru_cache`
3. NoDataSentinel for missing data (falsy pattern)
4. Cache invalidation when source data changes
5. `cache_info()` method for diagnostics

### 2.2 ValueTensor4x3 Computed Fields

From `src/babylon/economics/tensor.py`:

```python
@computed_field
@property
def total_c(self) -> LaborHours:
    """Total constant capital across all departments."""
    return LaborHours(self.dept_I.c + self.dept_IIa.c + self.dept_IIb.c + self.dept_III.c)

@computed_field
@property
def profit_rate(self) -> float:
    """Average rate of profit (flow-based: s/(c+v))."""
    denominator = self.total_c + self.total_v
    if denominator == 0.0:
        return float("inf")
    return self.total_s / denominator
```

**Note**: The existing `profit_rate` uses flow-based formula. We will add a separate stock-based calculation.

### 2.3 MarxianHydrator Pattern

From `src/babylon/economics/hydrator.py`:

```python
class MarxianHydrator:
    """Transforms QCEW wage data into Marxian value tensors."""

    def hydrate(self, fips_code: str, year: int) -> ValueTensor4x3
```

**Pattern for CapitalStockCalculator**: Similar service class that takes TensorRegistry as dependency and computes derived values.

## 3. Implementation Strategy

### 3.1 CapitalStockCalculator Design

```python
@dataclass(frozen=True)
class DepreciationConfig:
    """Configuration for capital depreciation."""
    rate: float = 0.07  # BEA average

    def __post_init__(self) -> None:
        if not 0.01 <= self.rate <= 0.20:
            raise ValueError(f"Depreciation rate must be in [0.01, 0.20], got {self.rate}")

class CapitalStockCalculator:
    """Computes capital stock from tensor flow data."""

    def __init__(
        self,
        registry: TensorRegistry,
        depreciation: DepreciationConfig | None = None,
    ) -> None: ...

    def compute_K(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute capital stock for a specific county-year."""
        ...

    def compute_time_series(self, fips: str, start_year: int, end_year: int) -> dict[int, float]:
        """Compute K for all available years in range."""
        ...
```

### 3.2 DerivedTensorMetrics Design

```python
@dataclass(frozen=True)
class DerivedTensorMetrics:
    """Container for derived ratios computed from tensor + capital stock."""

    fips_code: str
    year: int
    capital_stock: float  # K
    profit_rate_stock: float  # r = s / (K + v)
    occ: float  # c / v (already on tensor, but convenient)
    exploitation_rate: float  # s / v (already on tensor)

    # Source references
    tensor: ValueTensor4x3
    depreciation_rate: float
```

### 3.3 Time-Series Computation Algorithm

```python
def compute_time_series(self, fips: str, years: Sequence[int]) -> dict[int, float]:
    """Compute K for all years using perpetual inventory method."""

    sorted_years = sorted(years)
    results: dict[int, float] = {}
    K_prev: float | None = None

    for year in sorted_years:
        tensor = self._registry.get(fips, year)

        if not tensor:  # NoDataSentinel
            # Skip missing year, log warning
            logger.warning("Missing data for %s/%d, skipping", fips, year)
            continue

        if K_prev is None:
            # Initial year: steady-state assumption
            K_0 = tensor.total_c / self._depreciation.rate
            results[year] = K_0
            K_prev = K_0
        else:
            # Perpetual inventory method
            K_new = K_prev * (1 - self._depreciation.rate) + tensor.total_c
            results[year] = max(0.0, K_new)  # Clamp to non-negative
            K_prev = results[year]

    return results
```

## 4. Test Data Requirements

### 4.1 Unit Test Data

For unit tests, create synthetic tensors with known values:

```python
# Test case: Simple steady state
# If c = 70 and δ = 0.07, K_0 = 70/0.07 = 1000
# Next year: K_1 = 1000 × 0.93 + 70 = 1000 (steady state maintained)

# Test case: Growing capital
# c_0 = 70, c_1 = 84 (20% growth)
# K_0 = 1000, K_1 = 1000 × 0.93 + 84 = 1014

# Test case: Declining capital
# c_0 = 70, c_1 = 50 (decline)
# K_0 = 1000, K_1 = 1000 × 0.93 + 50 = 980
```

### 4.2 Integration Test Data

For TRPF validation (SC-002), need:
- 50+ counties with complete time series (2010-2024)
- Counties should span core/periphery spectrum
- Wayne County (26163) and Oakland County (26125) for Detroit validation

### 4.3 Sensitivity Analysis Data

For SC-004, test with δ ∈ {0.05, 0.07, 0.10}:
- All three should show declining profit rate trend
- Higher δ → lower K → higher profit rate (but still declining)

## 5. Risk Assessment

### 5.1 Data Availability

**Risk**: Some counties may have missing years in QCEW data.
**Mitigation**: Skip missing years, continue accumulation from last available. Log warnings.

### 5.2 Initial Value Sensitivity

**Risk**: Steady-state assumption may be inappropriate for some counties.
**Mitigation**:
1. Error decays exponentially; by 2024, initial error is dampened
2. Sensitivity analysis will test robustness
3. For critical analysis, can provide alternative initialization methods later

### 5.3 Aggregation Complexity

**Risk**: State/national capital stock ≠ simple sum of county K values if counties have different depreciation rates.
**Mitigation**: Use uniform national δ for initial implementation. Industry-specific rates are documented as future enhancement.

## 6. Dependencies

### 6.1 Required from Spec 011

- `TensorRegistry` with `get(fips, year)` method
- `ValueTensor4x3` with `total_c`, `total_v`, `total_s` computed fields
- `NoDataSentinel` for missing data handling
- `GeoLevel` enum for aggregation

### 6.2 External Data

- BEA Fixed Asset Tables for depreciation rate validation
- QCEW data (via existing hydration pipeline)

## 7. Success Metrics Verification Plan

| Success Criterion | Verification Method |
|-------------------|---------------------|
| SC-001: <100ms per county | pytest benchmark with timer |
| SC-002: TRPF (dr/dt < 0, p < 0.05) | scipy.stats.linregress on r time series |
| SC-003: OCC-Core correlation > 0.3 | scipy.stats.pearsonr on OCC vs τ |
| SC-004: TRPF robust to δ variation | Repeat SC-002 with δ ∈ {0.05, 0.07, 0.10} |
| SC-005: Aggregation accuracy < 0.01% | Compare sum(county_K) vs state_K |
| SC-006: No breaking changes | Existing test suite passes |
