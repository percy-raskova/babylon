# Feature Specification: Class Dynamics Engine

**Feature Branch**: `016-class-dynamics-engine`
**Created**: 2026-02-05
**Status**: Draft
**Input**: User description: "Create a specification for the Class Dynamics Engine - integrates wealth-based class position, imperial rent, throughput, and visibility into a unified dynamics engine that models how class positions change over time through accumulation, dispossession, precaritization, and stabilization"

## Clarifications

### Session 2026-02-05

- Q: How should the MVP handle dispossession data sources (foreclosure, bankruptcy, eviction)? → A: Hardcoded national averages by year (e.g., 2008 foreclosure = 2.3%, 2015 = 0.5%) with county adapter protocol for future extension to real per-county data loaders
- Q: What form should the savings rate function take? → A: Class-based step function with one savings rate per ClassPosition (e.g., LA=12%, proletariat=3%, lumpen=0%), adjusted by imperial rent subsidy

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Wealth Accumulation Rate (Priority: P1)

As a simulation researcher, I need to compute the annual wealth accumulation rate for a given county-year to determine how fast workers accumulate or lose wealth, enabling prediction of class position transitions over time.

**Why this priority**: Wealth accumulation is the fundamental mechanism that drives all class transitions. Without computing how wealth changes over time, no transitions can be modeled. This is the minimum viable calculation: given wage income, consumption costs, and imperial rent subsidy, output the net wealth change rate.

**Independent Test**: Can be fully tested by computing accumulation rate for known wage/consumption/imperial-rent combinations and validating directional behavior: positive accumulation when wages exceed consumption, zero when living paycheck-to-paycheck, negative during dispossession events.

**Acceptance Scenarios**:

1. **Given** a worker with annual wage income of $60,000, consumption of $50,000, and savings rate of 15%, **When** I compute wealth accumulation, **Then** the annual wealth gain is approximately $1,500 (surplus times savings rate)
2. **Given** a worker with wage income of $40,000 and consumption of $39,500 (near-subsistence), **When** I compute wealth accumulation, **Then** the annual wealth gain is near zero regardless of imperial rent benefit
3. **Given** a worker with imperial rent subsidy (consumption subsidized by cheap imports), **When** I compare accumulation to an identical worker without subsidy, **Then** the subsidized worker accumulates faster because effective consumption cost is lower
4. **Given** a worker experiencing negative wealth shock (medical debt, foreclosure), **When** I compute accumulation, **Then** the result is negative, reflecting wealth destruction

______________________________________________________________________

### User Story 2 - Assess Dispossession Risk (Priority: P1)

As a simulation researcher, I need to assess the probability of dispossession events (foreclosure, bankruptcy, eviction) for a county-year to model sudden downward class transitions, particularly from labor aristocracy to proletariat.

**Why this priority**: Dispossession is the primary mechanism for downward class mobility in the MLM-TW framework. Labor aristocracy members lose their class position primarily through wealth destruction (losing home equity via foreclosure, savings via medical bankruptcy), not through gradual income decline. This is co-priority with accumulation because transitions require both mechanisms.

**Independent Test**: Can be tested by computing dispossession risk from foreclosure, bankruptcy, and eviction rates for known counties and validating that crisis years (2008-2012) show elevated risk compared to stable years (2015-2018).

**Acceptance Scenarios**:

1. **Given** county-level foreclosure rate, bankruptcy rate, and eviction rate for a stable year (e.g., 2015), **When** I compute composite dispossession risk, **Then** the result is a low probability reflecting normal economic churn
2. **Given** the same county during the 2008 financial crisis, **When** I compute dispossession risk, **Then** the result is significantly elevated (at least 2x the stable-year baseline)
3. **Given** a county with high eviction rate but low foreclosure rate, **When** I compute dispossession risk, **Then** eviction primarily affects proletariat-to-lumpen transitions while foreclosure primarily affects LA-to-proletariat transitions
4. **Given** dispossession risk data is unavailable for a county, **When** I request dispossession risk, **Then** the system returns a descriptive unavailability indicator with the specific missing data source identified

______________________________________________________________________

### User Story 3 - Simulate Class Distribution Transitions (Priority: P1)

As a simulation researcher, I need to simulate one period of class distribution transitions for a county to see how the five-class shares evolve based on economic conditions, enabling multi-period simulation of class dynamics.

**Why this priority**: This is the integration point that combines accumulation and dispossession into actual class share changes. Without this, the individual calculations have no practical effect on the simulation state. This completes the minimum viable dynamics engine.

**Independent Test**: Can be tested by starting with a known class distribution, applying known economic conditions for one period, and validating that the resulting distribution sums to 1.0 and transitions match expected directions.

**Acceptance Scenarios**:

1. **Given** an initial class distribution (1% bourgeoisie, 9% petit-bourgeoisie, 40% LA, 35% proletariat, 15% lumpen) and stable economic conditions, **When** I simulate one period, **Then** the resulting distribution is close to the initial (small perturbations only, shares still sum to 1.0)
2. **Given** crisis economic conditions (high unemployment, high foreclosure rate), **When** I simulate one period, **Then** LA share decreases, proletariat share may decrease or increase depending on dispossession vs precaritization balance, and lumpen share increases
3. **Given** recovery economic conditions (low unemployment, rising wages), **When** I simulate one period, **Then** lumpen share decreases (stabilization) and proletariat or LA share increases (upward mobility)
4. **Given** any transition simulation, **When** I check the output distribution, **Then** all shares are non-negative and sum to exactly 1.0 (within floating-point tolerance of 0.001)

______________________________________________________________________

### User Story 4 - Model Crisis Amplification (Priority: P2)

As a simulation researcher, I need the dynamics engine to amplify class transitions during crisis periods (triggered by TRPF or exogenous shocks) to model how economic crises accelerate class decomposition and potential revolutionary conditions.

**Why this priority**: Crisis dynamics are the core theoretical contribution of the MLM-TW framework. During crises, normal transition rates are insufficient; cascading effects (unemployment spikes causing foreclosures causing further unemployment) must be captured. Lower priority because it extends the base transition engine rather than being required for it.

**Independent Test**: Can be tested by comparing transition magnitudes under normal vs crisis conditions and validating that crisis produces non-linear acceleration of downward transitions.

**Acceptance Scenarios**:

1. **Given** a TRPF-triggered crisis flag, **When** I simulate class transitions, **Then** downward transition rates (LA-to-proletariat, proletariat-to-lumpen) are amplified beyond what individual indicator changes would predict
2. **Given** unemployment spikes from 4% to 10%, **When** I simulate transitions, **Then** the proletariat-to-lumpen flow increases and the lumpen-to-proletariat flow decreases (mobility freeze)
3. **Given** a crisis period lasting multiple simulation ticks, **When** I simulate sequentially, **Then** cumulative downward mobility shows accelerating pattern (not linear) as wealth destruction compounds

______________________________________________________________________

### User Story 5 - Validate Against Historical Class Composition (Priority: P3)

As a simulation researcher, I need to validate computed class distributions against historical estimates of US class composition to ensure theoretical plausibility of the dynamics engine output.

**Why this priority**: Validation ensures the model produces realistic results, but it depends on all other stories being complete first. Historical class composition data is inherently approximate, so validation is directional rather than precise.

**Independent Test**: Can be tested by running the dynamics engine from a known starting distribution through historical economic conditions and comparing output to rough class composition estimates from Fed SCF wealth surveys.

**Acceptance Scenarios**:

1. **Given** historical economic conditions from 2010-2019, **When** I run multi-year simulation, **Then** final class distribution is within plausible ranges: bourgeoisie 0.5-2%, petit-bourgeoisie 5-15%, LA 30-50%, proletariat 25-45%, lumpen 10-25%
2. **Given** 2008 crisis conditions applied to 2007 class distribution, **When** I simulate 2008-2012, **Then** LA share declines and lumpen share increases, matching the directional pattern of the Great Recession
3. **Given** 2020 pandemic conditions, **When** I simulate, **Then** the engine produces rapid precaritization followed by partial recovery, matching observed labor market dynamics

______________________________________________________________________

### Edge Cases

- **What happens when all class shares are zero except one?** System handles degenerate distributions gracefully; transitions from empty classes produce no flow
- **What happens when economic data is unavailable for a county-year?** System returns descriptive unavailability indicator identifying which data source is missing
- **What happens when dispossession risk exceeds 1.0?** System clamps probabilities to [0.0, 1.0] range before applying transitions
- **How does system handle counties with extremely small populations?** Transition rates may produce sub-person flows; system treats shares as continuous proportions (not discrete headcounts)
- **What happens when wage equals exactly zero?** Accumulation is negative (consumption without income); the worker is either lumpen or in process of precaritization
- **What happens during deflation (negative price changes)?** Accumulation rate adjusts through MELT changes; system does not assume positive inflation

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute annual wealth accumulation rate as net income (wage minus consumption) multiplied by savings rate, where savings rate is a class-based step function: one base rate per ClassPosition (e.g., LA approximately 12%, proletariat approximately 3%, lumpen 0%), adjusted upward by imperial rent subsidy effect on consumption
- **FR-002**: System MUST model four class transition pathways: LA-to-proletariat (dispossession), proletariat-to-LA (accumulation), proletariat-to-lumpen (precaritization), and lumpen-to-proletariat (stabilization)
- **FR-003**: System MUST compute composite dispossession risk from foreclosure rate, bankruptcy rate, and eviction rate, with each component weighted by its class-transition relevance. MVP uses hardcoded national averages by year with a data source protocol enabling future per-county data loaders
- **FR-004**: System MUST preserve class distribution invariant: all shares non-negative and sum to 1.0 after every transition simulation
- **FR-005**: System MUST accept class distribution and economic conditions as inputs and produce updated class distribution as output for one simulation period
- **FR-006**: System MUST distinguish between dispossession mechanisms: foreclosure affects primarily LA-to-proletariat, eviction affects primarily proletariat-to-lumpen, bankruptcy affects both pathways
- **FR-007**: System MUST integrate with existing wealth-based ClassPosition classification from Feature 013
- **FR-008**: System MUST integrate imperial rent (from Feature 013) as a consumption subsidy that accelerates accumulation for workers with positive imperial rent flow
- **FR-009**: System MUST support crisis amplification where transition rates increase non-linearly during crisis conditions
- **FR-010**: System MUST return descriptive unavailability indicators (following NoDataSentinel pattern) when required data sources are missing, with distinct messages per data source
- **FR-011**: System MUST validate computed transition rates against expected ranges and log warnings for anomalous values
- **FR-012**: System MUST treat bourgeoisie and petit-bourgeoisie shares as externally determined (from Fed SCF wealth data); dynamics engine focuses on LA/proletariat/lumpen transitions
- **FR-013**: System MUST compute transition rates as continuous flows (not discrete jumps) to maintain smooth class distribution evolution
- **FR-014**: System MUST support per-county computation using FIPS codes consistent with existing economics modules

### Key Entities

- **ClassDistribution**: Five-class share distribution for a county-year (bourgeoisie, petit-bourgeoisie, labor aristocracy, proletariat, lumpenproletariat), constrained to sum to 1.0
- **EconomicConditions**: Aggregate economic state for a county-year including unemployment rate, wage level, MELT, imperial rent, foreclosure rate, bankruptcy rate, eviction rate, and crisis flag
- **TransitionRates**: Sparse transition structure for the three dynamic classes (LA, proletariat, lumpenproletariat) covering four named pathways (accumulation, dispossession, precaritization, stabilization) per simulation period; bourgeoisie and petit-bourgeoisie rows/columns are zero (externally determined)
- **AccumulationResult**: Computed wealth change rate for a given income/consumption/savings configuration, including imperial rent subsidy effect
- **SavingsRateSchedule**: Class-based step function mapping each ClassPosition to a base savings rate, with imperial rent adjustment factor
- **DispossessionRisk**: Composite risk assessment from multiple data sources (foreclosure, bankruptcy, eviction) with per-source availability tracking

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Class distribution remains stable (total share change less than 2% per period) under non-crisis economic conditions
- **SC-002**: Crisis years (2008-2012 economic conditions) produce at least 2x the transition magnitude of stable years (2015-2018 conditions)
- **SC-003**: Foreclosure rate shows positive correlation with LA-to-proletariat transition rate across counties
- **SC-004**: Recovery periods show gradual upward mobility: lumpen share decreasing and proletariat/LA shares increasing over consecutive periods
- **SC-005**: Output class distributions always sum to 1.0 (within tolerance of 0.001) and contain no negative shares
- **SC-006**: Imperial rent subsidy produces measurable difference in accumulation rate: workers with positive imperial rent accumulate faster than equivalent workers without, validated via synthetic test scenarios
- **SC-007**: All edge cases (missing data, zero shares, extreme values) handled without system errors
- **SC-008**: Multi-period simulation from plausible 2010 starting distribution produces 2019 distribution within expected ranges (bourgeoisie 0.5-2%, petit-bourgeoisie 5-15%, LA 30-50%, proletariat 25-45%, lumpen 10-25%)

## Assumptions

- Wealth-based class position classification exists from Feature 013 and provides the five-class model with wealth percentile thresholds
- Imperial rent calculator exists from Feature 013 and provides per-hour imperial rent extraction values
- MELT calculator exists from Feature 013 for labor-time to price-space conversion
- Gamma visibility tensor exists from Feature 015 for consumption basket subsidy quantification
- Throughput position exists from Feature 014 for domestic geographic wage variation
- MVP dispossession data uses hardcoded national averages by year (covering at minimum 2007-2020 to capture crisis and recovery dynamics), exposed behind a data source protocol that enables future replacement with real per-county data loaders (Eviction Lab, US Courts, ATTOM/CoreLogic)
- Savings rate uses a class-based step function with one rate per ClassPosition, calibrated against Fed Survey of Consumer Finances (SCF) aggregate data
- Bourgeoisie and petit-bourgeoisie shares are relatively stable and determined externally; the dynamics engine primarily models LA/proletariat/lumpen transitions
- Transition rates are computed annually (one simulation period = one year)

## Constraints

- Class dynamics apply ONLY to the three working classes (LA, proletariat, lumpenproletariat); bourgeoisie and petit-bourgeoisie transitions are out of scope for this feature
- All transitions must be continuous flows (no discrete class jumps within a single period)
- The dynamics engine does not generate new economic conditions; it consumes conditions produced by other systems
- County-level computation requires FIPS-coded data consistent with existing economics modules
- Transition rates must be non-negative (no "anti-transitions")
- The sum-to-one invariant on class distribution is a hard constraint that must never be violated

## Dependencies

- **Requires**: Feature 013 (MELT Basket Visibility) for ClassPosition, imperial rent, MELT calculation
- **Requires**: Feature 014 (Throughput Position) for domestic wage geography
- **Requires**: Feature 015 (Gamma Visibility Tensor) for consumption basket visibility and subsidy quantification
- **Data**: Eviction Lab (eviction rates by county), US Courts (bankruptcy rates by district mapped to county), ATTOM/CoreLogic (foreclosure rates), Fed SCF (savings rates by income bracket)

## Future Enhancements

- **FE-001**: Petit-bourgeoisie dynamics (small business failure rates, downward mobility into proletariat during crisis)
- **FE-002**: Bourgeoisie concentration dynamics (wealth concentration trends, merger/acquisition effects)
- **FE-003**: Inter-county migration as a class transition mechanism (workers moving to lower-cost counties to maintain class position)
- **FE-004**: Racial stratification of transition rates (differential foreclosure/eviction rates by race within counties)
- **FE-005**: Integration with TRPF (Tendency of the Rate of Profit to Fall) system for endogenous crisis generation
- **FE-006**: Household-level microsimulation (individual wealth trajectories rather than aggregate share flows)
- **FE-007**: Real per-county dispossession data loaders (Eviction Lab API, US Courts bankruptcy, ATTOM/CoreLogic foreclosure) replacing hardcoded national averages
