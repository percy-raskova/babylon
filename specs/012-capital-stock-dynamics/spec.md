# Feature Specification: Capital Stock Dynamics

**Feature Branch**: `012-capital-stock-dynamics`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "Create a specification for Capital Stock Dynamics - derive capital STOCK (K) from capital FLOWS (c) for profit rate calculation using TSSI historical cost valuation and perpetual inventory method. Required for testing the Tendency of the Rate of Profit to Fall (TRPF)."
**TVT Reference**: Implements Axiom A3 (Stock-Flow Consistency) and Section 5.2 (Capital Stock Evolution) from `ai-docs/brainstorms/tensor/tvt_mathematical_formalization.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute County-Level Capital Stock (Priority: P1)

Researchers analyzing TRPF dynamics need to access capital stock values for individual counties across multiple years, derived from the primitive tensor's constant capital flows (c).

**Why this priority**: Capital stock is the foundational derived value. Without K[fips, year], none of the derived rates (profit rate, OCC, exploitation rate) can be computed. This is the enabling primitive for all TRPF analysis.

**Independent Test**: Can be fully tested by hydrating a single county's tensor data for 2010-2024, computing K for each year, and validating the perpetual inventory accumulation formula.

**Acceptance Scenarios**:

1. **Given** primitive tensor data for Wayne County (26163) from 2010-2024, **When** requesting K[26163, 2015], **Then** the system returns capital stock computed as K[2015] = K[2014] × (1 - δ) + total_c[2014], where δ = 0.07, total_c = Σ_μ c^μ (sum of c across all 4 departments), and K[2010] = total_c[2010] / δ.

2. **Given** tensor data for a county starting in 2010, **When** requesting K for each year 2010-2024, **Then** K values form a monotonically consistent time series following the perpetual inventory formula.

3. **Given** a county with missing year data (e.g., 2018 missing), **When** requesting K for years after the gap, **Then** the system skips the missing year and continues accumulation from the last available year, logging a warning.

______________________________________________________________________

### User Story 2 - Calculate Profit Rate Time Series (Priority: P1)

Economists validating TRPF theory need to compute profit rate (r) for counties and observe secular decline trends over the 2010-2024 period.

**Why this priority**: Profit rate is the primary validation metric for TRPF theory. Without r[fips, year], the simulation cannot test Marx's hypothesis about falling profits.

**Independent Test**: Can be fully tested by computing r for a county time series and verifying the formula r = s / (K + v), with expected secular decline visible in the data.

**Acceptance Scenarios**:

1. **Given** primitive tensor with total_s and total_v, and derived K, **When** requesting profit rate r[26163, 2022], **Then** the system returns r = total_s / (K + total_v).

2. **Given** K = 0 and total_v = 0 for a pathological case, **When** computing profit rate, **Then** the system returns float('inf') to indicate undefined rate (consistent with existing tensor patterns).

3. **Given** a county's profit rate time series 2010-2024, **When** analyzing the trend, **Then** the profit rate shows secular decline (negative slope), validating TRPF prediction.

______________________________________________________________________

### User Story 3 - Access Derived Ratios (OCC and Exploitation Rate) (Priority: P2)

Analysts studying the composition of capital need to access Organic Composition of Capital (OCC) and exploitation rate (e) as derived fields that aggregate flows across departments.

**Why this priority**: These ratios provide complementary perspectives on capital dynamics. OCC measures mechanization; exploitation rate measures labor extraction. Both are required for complete TRPF analysis.

**Independent Test**: Can be fully tested by computing OCC and e from the primitive tensor's c, v, s values and verifying the formulas OCC = total_c / total_v and e = total_s / total_v.

**Acceptance Scenarios**:

1. **Given** a county tensor with total_c, total_v, total_s, **When** requesting OCC[26163, 2022], **Then** the system returns OCC = total_c / total_v.

2. **Given** a county tensor, **When** requesting exploitation rate e[26163, 2022], **Then** the system returns e = total_s / total_v.

3. **Given** a county with total_v = 0, **When** computing OCC or e, **Then** the system returns float('inf') (consistent with existing ValueTensor4x3 patterns).

______________________________________________________________________

### User Story 4 - Perform Depreciation Sensitivity Analysis (Priority: P2)

Researchers want to test the robustness of TRPF conclusions by varying the depreciation rate δ and observing how results change.

**Why this priority**: The depreciation rate is an assumption that affects capital stock magnitude. Sensitivity analysis validates that TRPF conclusions are robust to reasonable parameter variations.

**Independent Test**: Can be fully tested by computing K with δ = 0.05, 0.07, and 0.10, then verifying that TRPF trend (declining r) persists across all scenarios.

**Acceptance Scenarios**:

1. **Given** δ = 0.05 (slow depreciation), **When** computing capital stock time series, **Then** K values are larger than with δ = 0.07.

2. **Given** δ = 0.10 (fast depreciation), **When** computing capital stock time series, **Then** K values are smaller than with δ = 0.07.

3. **Given** profit rates computed under δ ∈ {0.05, 0.07, 0.10}, **When** comparing trends, **Then** all three show secular decline, indicating TRPF robustness to depreciation assumptions.

______________________________________________________________________

### User Story 5 - Access Aggregated Capital Stock (Priority: P3)

Policy analysts need state-level and national capital stock totals for macro-level TRPF analysis.

**Why this priority**: Aggregation extends county-level analysis to macro scales. Lower priority because county-level analysis provides the foundational validation.

**Independent Test**: Can be fully tested by computing K for all Michigan counties, summing to state total, and verifying against direct state-level aggregation.

**Acceptance Scenarios**:

1. **Given** capital stock for all counties in Michigan, **When** requesting K[STATE, "26", 2022], **Then** the system returns the sum of K for all Michigan counties.

2. **Given** K computed for all US counties, **When** requesting K[NATION, "US", 2022], **Then** the system returns the national capital stock total.

3. **Given** only 40% of Michigan counties have valid K data (below 50% threshold), **When** requesting K[STATE, "26", 2022], **Then** the system returns NoDataSentinel with reason "Insufficient county coverage (40%)".

4. **Given** 60% of Michigan counties have valid K data (above 50% threshold), **When** requesting K[STATE, "26", 2022], **Then** the system returns the sum of available county K values with a warning noting partial coverage.

______________________________________________________________________

### Edge Cases

- What happens when the primitive tensor is missing for a county-year? Return NoDataSentinel with descriptive reason.
- What happens when K would be negative due to extreme depreciation? K is clamped to 0 (capital stock cannot be negative).
- What happens for years before 2010? Return NoDataSentinel (outside data range).
- What happens for years after 2024 with no primitive data? Extrapolation is not supported; return NoDataSentinel.
- What happens when total_c or total_v are zero? Return computed ratio (may be 0 or inf) with consistent behavior matching existing ValueTensor4x3.

### Validation Case: Detroit Metro (Wayne vs Oakland)

Per TVT political-theoretical exposition Section 4.2, the Detroit metro area provides a concrete validation case:

- **Wayne County (26163)**: Domestic periphery - labor exporter, lower τ, lower OCC expected
- **Oakland County (26125)**: Domestic core - labor importer, higher τ, higher OCC expected

Test: OCC[Oakland] > OCC[Wayne] consistently across 2010-2024, demonstrating OCC-CoreIndex correlation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute capital stock K[fips, t] using perpetual inventory method per TVT Axiom A3:
  ```
  K[fips, t+1] = K[fips, t] × (1 - δ) + Σ_μ c^μ[fips, t]
  ```
  Where Σ_μ c^μ = total_c from ValueTensor4x3 (sum of constant capital across all 4 departments: I, IIa, IIb, III)
- **FR-002**: System MUST initialize K[fips, 2010] using steady-state assumption: K_0 = (Σ_μ c^μ_0) / δ
- **FR-003**: System MUST use BEA average depreciation rate δ = 0.07 as the default, configurable via parameter
- **FR-004**: System MUST compute profit rate per TVT Section 3.6:
  ```
  r[fips, t] = Σ_μ s^μ[fips, t] / (K[fips, t] + Σ_μ v^μ[fips, t])
  ```
- **FR-005**: System MUST compute Organic Composition of Capital per TVT Section 3.7:
  ```
  OCC[fips, t] = Σ_μ c^μ[fips, t] / Σ_μ v^μ[fips, t]
  ```
- **FR-006**: System MUST compute exploitation rate per TVT Section 3.8:
  ```
  e[fips, t] = Σ_μ s^μ[fips, t] / Σ_μ v^μ[fips, t]
  ```
- **FR-007**: System MUST derive all values from the cached TensorRegistry, never querying the database directly
- **FR-008**: System MUST handle missing year data by skipping the gap year and continuing K accumulation from the last available year's values, logging a warning with the skipped year(s)
- **FR-009**: System MUST return NoDataSentinel with descriptive `.reason` attribute (e.g., "Year outside data range", "No tensor data for county") when requested data cannot be computed
- **FR-010**: System MUST support aggregation of capital stock to state and national levels, requiring at least 50% of constituent counties to have valid K data; return NoDataSentinel with reason "Insufficient county coverage (X%)" if threshold not met
- **FR-011**: System MUST support configurable depreciation rates for sensitivity analysis (range: 0.01 to 0.20)
- **FR-012**: System MUST clamp capital stock K to non-negative values (K >= 0)

### Key Entities

- **CapitalStockCalculator**: Service that computes K[fips, year] from primitive tensor data using perpetual inventory method. Caches computed values. Accepts depreciation rate δ as configuration.

- **DerivedTensorMetrics**: Container for derived ratios (r, OCC, e) computed for a specific county-year. Immutable. References the source capital stock and primitive tensor.

- **DepreciationConfig**: Configuration object holding depreciation rate δ and initialization assumptions. Supports sensitivity analysis by allowing multiple configurations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Capital stock K can be computed for all counties with primitive tensor data in under 100ms per county time series (2010-2024). Measured via pytest-benchmark with 100 iterations on a standard development machine; cold cache (first call) and warm cache (subsequent calls) measured separately.
- **SC-002**: Profit rate validates TVT Prediction 9 (TRPF):
  - H₀: dr/dt ≥ 0 (no TRPF)
  - H₁: dr/dt < 0 (TRPF operative)
  - Test: Profit rate time series for 50 counties shows statistically significant negative slope (p < 0.05)
- **SC-003**: OCC validates TVT Prediction 10 (OCC-Core Correlation):
  - H₀: corr(OCC, CoreIndex) ≤ 0
  - H₁: corr(OCC, CoreIndex) > 0
  - Test: OCC shows positive correlation (r > 0.3) with τ (MELT, a component of CoreIndex), validating theory that core economies have higher capital intensity
- **SC-004**: Sensitivity test with δ ∈ {0.05, 0.07, 0.10} produces consistent TRPF trend direction (declining r) in at least 80% of counties
- **SC-005**: Aggregated state-level K equals sum of constituent county K values within floating-point precision (< 0.01% error)
- **SC-006**: All derived metrics (K, r, OCC, e) integrate with existing TensorRegistry without breaking existing consumers

## Assumptions

- **A-001**: Depreciation rate of 0.07 (7% per year) is appropriate as a starting estimate based on BEA fixed asset tables. This is a single national rate; industry-specific rates are a future enhancement.
- **A-002**: Steady-state initialization K_0 = c_0 / δ produces reasonable estimates for 2010 baseline. The error from this assumption decays exponentially with time constant 1/δ ≈ 14 years.
- **A-003**: TSSI (Temporal Single-System Interpretation) historical cost valuation is the correct accounting method per TVT Axiom B2. Capital stock represents what was actually paid for means of production, not current replacement cost.
- **A-004**: The primitive tensor's total_c (Σ_μ c^μ, constant capital flow summed across all departments) is an appropriate proxy for annual gross investment I. This aligns with TVT Section 5.2.
- **A-005**: Missing years in the time series can be skipped without interpolation. The accumulation formula continues from the last available year. Users requiring continuity must ensure complete data.
- **A-006**: Normal depreciation rate δ applies uniformly. Crisis-accelerated depreciation (δ_effective > δ_normal, per TVT Section 9.4) is out of scope for initial implementation.

## Future Enhancements

Per TVT mathematical formalization (Sections 9.2, 9.4), the following are identified as future extensions:

- **Vintage Capital**: Track each year's investment separately for rigorous TRPF analysis:
  ```
  K[fips, t] = Σ_{τ ≤ t} I[fips, τ] × (1 - δ)^(t-τ)
  ```
  This increases state space but provides more accurate capital valuation.

- **Crisis Dynamics**: Derive crisis endogenously and apply accelerated depreciation:
  ```
  Crisis triggers when: r[t] < r_threshold for sustained period
  Crisis resolves via: K[t+1] = K[t] × (1 - δ_crisis), δ_crisis >> δ_normal
  ```

- **Industry-Specific Depreciation**: Use BEA fixed asset tables to apply different δ rates by NAICS sector rather than a single national rate.

- **Department-Level Capital Stock**: Track K separately for each department (K_I, K_IIa, K_IIb, K_III) rather than aggregate K only.
