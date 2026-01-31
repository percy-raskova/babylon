# Feature Specification: Hydrator Temporal Validation & Deindustrialization Signals

**Feature Branch**: `003-hydrator-temporal-validation`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Add α-smoothed temporal validation and deindustrialization signal detection to MarxianHydrator"

## Clarifications

### Session 2026-01-30

- Q: Should anomaly detection use a static threshold (50%) or a dynamic method? → A: Z-score method (k=2.5 std devs) with 5-year rolling baseline. For counties with insufficient history (\<5 years), fall back to an empirical 95th percentile threshold (95th percentile of YoY changes across all counties with sufficient data).
- Q: How to handle current data gap (only 2021-2022 loaded, but spec references 2010-2022)? → A: Document QCEW data ingestion (2010-2022) as a prerequisite task that must complete before full feature validation.
- Q: Financial crisis scenario references 2008, but data starts at 2010? → A: Adjust to "2010 vs 2015" - no QCEW data available before 2010.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect Deindustrialization Signal (Priority: P1)

As a simulation analyst, I need to compare ValueTensor4x3 outputs between Wayne County (Detroit core) and Oakland County (affluent suburb) to verify that the tensor correctly captures the deindustrialization pattern: Wayne should show declining V_produced (total variable capital) relative to Oakland's professional services economy over multi-year time series.

**Why this priority**: The Detroit test case is the foundational validation for the MLM-TW framework. If the hydrator cannot distinguish between a deindustrialized core and an affluent suburb, the simulation loses its empirical grounding.

**Independent Test**: Can be fully tested by hydrating tensors for Wayne (26163) and Oakland (26125) counties across 2010-2022 and measuring the Dept I proportion trajectory.

**Acceptance Scenarios**:

1. **Given** hydrated tensors for Wayne County from 2010-2022, **When** I compute the year-over-year Dept I share (V_I / total_V), **Then** the trend should show decline OR stagnation (not growth) relative to Oakland County's Dept I share over the same period.

1. **Given** hydrated tensors for both counties in any single year, **When** I compare the Dept I absolute values, **Then** Wayne's manufacturing-to-professional-services ratio should be higher than Oakland's (Wayne retains manufacturing character despite decline).

1. **Given** hydrated tensors for Wayne County 2010 vs 2015 (post-financial crisis recovery period), **When** I measure the Dept I share change, **Then** Wayne should show a more severe decline or slower recovery than Oakland (manufacturing sector recovery lagged professional services).

______________________________________________________________________

### User Story 2 - Flag Anomalous Year-over-Year Jumps (Priority: P1)

As a data quality analyst, I need the system to flag any county-year tensor where year-over-year changes are statistically anomalous relative to that county's historical volatility, so that I can investigate data quality issues or document genuine structural shifts.

**Why this priority**: Tied with US1 - anomaly detection prevents data quality issues from propagating silently into simulation results. Using Z-scores adapts to each county's natural volatility rather than applying an arbitrary static threshold.

**Independent Test**: Can be fully tested by hydrating multi-year tensors, computing rolling statistics, and verifying Z-score flags.

**Acceptance Scenarios**:

1. **Given** a county with 5+ years of historical data, **When** any component (total_v, dept shares, profit_rate) changes by more than k=2.5 standard deviations from the 5-year rolling mean, **Then** the system flags this transition for review.

1. **Given** a county with fewer than 5 years of historical data, **When** any component changes by more than the empirical 95th percentile threshold (95th percentile of national YoY changes), **Then** the system flags this transition for review.

1. **Given** a known economic shock year (e.g., 2020 COVID), **When** the flag is raised, **Then** the flag metadata should include the year context allowing analyst to annotate as "documented shock."

1. **Given** flagged transitions across multiple counties in the same year, **When** the analyst reviews, **Then** systemic shocks (affecting many counties) should be distinguishable from county-specific data issues.

______________________________________________________________________

### User Story 3 - Apply α-Smoothed Coefficients (Priority: P2)

As a simulation engine consumer, I need tensor-derived coefficients (profit_rate, dept shares, OCC ratios) to be available in both raw and α-smoothed forms, so that the simulation can use stable coefficients that don't oscillate wildly from year to year while still having access to raw values for analysis.

**Why this priority**: Constitution Section II.4 specifies that coefficients "transform slowly via α-smoothing." However, this is a layer above the hydrator's core transformation, hence P2.

**Independent Test**: Can be fully tested by requesting smoothed coefficients over a 5-year window and verifying the smoothing formula is applied correctly.

**Acceptance Scenarios**:

1. **Given** a series of 5 consecutive tensors for a county, **When** I request α-smoothed profit_rate with α=0.3, **Then** the result should be an exponentially weighted moving average where recent years have higher weight.

1. **Given** raw profit_rate values that jump from 4% to 6% to 5%, **When** I apply α-smoothing, **Then** the smoothed series should show dampened oscillation (e.g., 4% → 4.6% → 4.72%).

1. **Given** α=1.0, **When** I request smoothed values, **Then** the output equals raw values (no smoothing applied).

1. **Given** α=0.0, **When** I request smoothed values, **Then** the output equals the first value in the series (full smoothing, no responsiveness).

______________________________________________________________________

### Edge Cases

- What happens when requesting smoothed values for a county with only 1 year of data?

  - Return raw value with a warning that smoothing requires multi-year data.

- What happens when a year is missing in the middle of the series (e.g., 2018, 2020, 2021 but no 2019)?

  - Skip the missing year in smoothing calculation; flag gap in metadata.

- What happens when Z-score cannot be computed (fewer than 5 years of history)?

  - Fall back to the empirical 95th percentile threshold (95th percentile of national YoY changes).

- What happens when the fallback threshold hasn't been computed yet (bootstrap phase)?

  - Use a conservative initial threshold of 15% until sufficient national data is available to compute the 95th percentile.

- What happens when deindustrialization signal test fails due to NAICS reclassification?

  - The test should use consistent NAICS code mapping; if major reclassification occurred mid-series, document in test assertions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute year-over-year change percentages for total_v, each dept's v share, and profit_rate when given consecutive yearly tensors.

- **FR-002**: System MUST flag YoY changes as anomalous using a tiered approach:

  - **Primary (Z-score)**: For counties with ≥5 years of history, flag if change exceeds k=2.5 standard deviations from the 5-year rolling mean.
  - **Fallback (empirical threshold)**: For counties with \<5 years of history, flag if change exceeds the 95th percentile of YoY changes computed across all counties with sufficient data.
  - **Bootstrap (initial threshold)**: If national 95th percentile is not yet computed, use 15% as a conservative initial threshold.

- **FR-003**: System MUST provide a method to compare Dept I share trajectories between two counties over a specified year range.

- **FR-004**: System MUST compute α-smoothed versions of scalar coefficients (profit_rate, dept shares, exploitation_rate) given a smoothing parameter α ∈ [0, 1].

- **FR-005**: System MUST validate that the deindustrialization signal (Wayne Dept I trajectory vs Oakland) meets the specified direction constraint in integration tests.

- **FR-006**: System MUST allow analysts to annotate flagged transitions as "documented shock" or "data quality issue" via metadata.

- **FR-007**: System MUST produce a TemporalValidationReport containing: all flags raised, trend directions by dept, and smoothed coefficient series.

- **FR-008**: System MUST compute and persist the national 95th percentile YoY threshold as a calibration artifact, updated when new QCEW data is ingested.

### Key Entities

- **TemporalTransition**: Represents the change between two consecutive yearly tensors for a county. Contains: fips_code, year_from, year_to, delta_total_v (%), delta_dept_shares (dict), delta_profit_rate (%), z_scores (dict), flags_raised (list), detection_method (enum: Z_SCORE | EMPIRICAL_THRESHOLD | BOOTSTRAP).

- **AnomalyThresholdConfig**: Configuration for anomaly detection. Contains: z_score_k (default 2.5), rolling_window_years (default 5), empirical_percentile (default 95), bootstrap_threshold (default 0.15), national_p95_threshold (computed from data).

- **SmoothedCoefficientSeries**: Time series of α-smoothed values for a single coefficient. Contains: fips_code, coefficient_name, alpha, raw_values (list), smoothed_values (list), years (list).

- **DeindustrializationSignal**: Comparison result between two counties' Dept I trajectories. Contains: core_county (FIPS), suburb_county (FIPS), year_range, core_dept_i_trend (slope), suburb_dept_i_trend (slope), signal_detected (bool), signal_strength (float).

- **TemporalValidationReport**: Aggregate report for a county or region. Contains: transitions (list[TemporalTransition]), smoothed_series (dict[str, SmoothedCoefficientSeries]), signals (list[DeindustrializationSignal]), threshold_config (AnomalyThresholdConfig).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For Wayne County 2010-2022, the deindustrialization signal detection correctly identifies declining or stagnating Dept I share relative to Oakland in at least 80% of year-pairs.

- **SC-002**: Z-score anomaly detection achieves ≤5% false positive rate when validated against historical QCEW data with known shock years (2020 COVID) excluded. **Measurement methodology**: After implementation, analyst reviews a random sample of 100+ flagged transitions from non-shock years. A flag is a "false positive" if the analyst annotates it as "normal variation" rather than "documented shock", "data quality issue", or "structural shift". False positive rate = (flags dismissed as normal) / (total flags reviewed).

- **SC-003**: α-smoothed coefficient series reduces variance by at least 40% compared to raw series when α=0.3 (measured across Detroit metro counties 2015-2022).

- **SC-004**: The flagging system produces actionable output: analysts can resolve 90% of flags within 5 minutes by examining the metadata and tensor details.

- **SC-005**: Tests for deindustrialization signal pass across all available QCEW years (2010-2022) for the Wayne/Oakland comparison.

- **SC-006**: α-smoothing computation adds less than 10% overhead to tensor retrieval time for a 10-year series.

- **SC-007**: The empirical 95th percentile threshold (national 95th percentile) is computed and documented, with the actual percentage recorded in the calibration artifact.

## Prerequisites

Before full feature validation can occur, the following must be completed:

- **PRE-001**: QCEW data ingestion for years 2010-2024 must be loaded into `fact_qcew_annual`. Current state: only 2021-2022 loaded (3,220 counties each year). Required: 2010-2024 for Detroit metro counties at minimum; ideally nationwide for empirical threshold calibration.
  - **Specification**: [004-qcew-data-ingestion](../004-qcew-data-ingestion/spec.md)
  - **Data Source**: BLS bulk downloads at `https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip`

**Impact of missing prerequisite:**

- Z-score computation requires 5 years of history → only works for 2017+ with 2010 data loaded
- Deindustrialization signal (US1) requires 2010-2022 trend analysis → blocked until data loaded
- α-smoothing (US3) and basic anomaly detection (US2 with bootstrap threshold) can proceed with available data

## Assumptions

- QCEW data for Wayne and Oakland counties will be available and complete for 2010-2022 after PRE-001 is satisfied.
- NAICS code mappings are consistent across the time series (or documented where they change).
- k=2.5 standard deviations captures approximately 99% of normal variation (appropriate for economic data which is not perfectly normal but approximately so).
- The 5-year rolling window balances responsiveness to structural change with sufficient sample size for stable variance estimation.
- α=0.3 is a reasonable default smoothing parameter based on typical coefficient autocorrelation in economic time series.
- COVID year (2020) is a known shock that should be annotated, not treated as a data quality issue.
- The 15% bootstrap threshold is conservative enough to avoid false negatives while the system accumulates data for empirical calibration.
