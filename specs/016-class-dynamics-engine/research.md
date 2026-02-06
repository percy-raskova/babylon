# Research: Class Dynamics Engine

**Feature**: 016-class-dynamics-engine
**Date**: 2026-02-05

## 1. Implementation Pattern

**Decision**: Follow Protocol + DefaultImpl pattern from Features 013-015.

**Rationale**: This is the established pattern for all economics calculators in the project. Each service (accumulation, dispossession, transition engine, crisis amplifier) gets a Protocol defining the interface and a DefaultXxx implementation with dependency injection via constructor.

**Alternatives considered**:
- Single monolithic class: Rejected because it violates separation of concerns and makes testing harder.
- Functional approach (standalone functions): Rejected because it doesn't support dependency injection of data sources.

## 2. Transition Model Architecture

**Decision**: Sparse 3-class transition model with 4 named pathways.

**Rationale**: The spec constrains dynamics to LA/proletariat/lumpenproletariat only (FR-012 excludes bourgeoisie and petit-bourgeoisie). Four named pathways map cleanly to economic mechanisms:

| Pathway | From | To | Mechanism |
|---------|------|----|-----------|
| Dispossession | LA | Proletariat | Foreclosure, bankruptcy |
| Accumulation | Proletariat | LA | Sustained savings > threshold |
| Precaritization | Proletariat | Lumpen | Job loss, eviction |
| Stabilization | Lumpen | Proletariat | Gain stable employment |

This is NOT a general Markov chain; it's a constrained flow network with specific economic meanings per transition.

**Alternatives considered**:
- Full 5x5 transition matrix: Rejected because bourgeoisie/PB transitions are explicitly out of scope.
- General Markov chain: Rejected because it obscures the economic meaning of each transition type.

## 3. MVP Data Strategy: Hardcoded National Averages

**Decision**: Hardcode national dispossession rates by year (2007-2020) behind a data source protocol.

**Rationale**: Per clarification session, this allows proving the transition mechanics work without blocking on data loader infrastructure. The protocol enables future per-county data loaders (FE-007).

### Hardcoded Dispossession Rates (Annual)

**Foreclosure rates** (% of all households, from ATTOM/CoreLogic):

| Year | Rate | Context |
|------|------|---------|
| 2007 | 1.8% | Crisis onset |
| 2008 | 2.3% | Housing crisis deepens |
| 2009 | 2.8% | Peak filings |
| 2010 | 4.6% | Peak completions |
| 2011 | 3.5% | Slow decline |
| 2012 | 2.5% | Recovery begins |
| 2013 | 1.5% | Post-crisis |
| 2014 | 1.0% | Normalizing |
| 2015 | 0.6% | Stable |
| 2016 | 0.5% | Stable |
| 2017 | 0.5% | Stable |
| 2018 | 0.5% | Stable |
| 2019 | 0.4% | Stable |
| 2020 | 0.15% | Moratorium |

**Bankruptcy rates** (personal filings per household, from US Courts):

| Year | Rate | Context |
|------|------|---------|
| 2007 | 0.7% | Pre-crisis baseline |
| 2008 | 0.8% | Rising |
| 2009 | 1.0% | Crisis |
| 2010 | 1.3% | Peak |
| 2011 | 1.1% | Declining |
| 2012 | 0.9% | Declining |
| 2013 | 0.8% | Normalizing |
| 2014 | 0.7% | Stable |
| 2015 | 0.6% | Stable |
| 2016 | 0.6% | Stable |
| 2017 | 0.6% | Stable |
| 2018 | 0.6% | Stable |
| 2019 | 0.6% | Stable |
| 2020 | 0.4% | Moratorium/stimulus |

**Eviction rates** (% of renter households, from Eviction Lab):

| Year | Rate | Context |
|------|------|---------|
| 2007 | 6.4% | Slightly below average |
| 2008 | 6.5% | Crisis year |
| 2009 | 6.4% | Crisis year |
| 2010 | 7.0% | Elevated |
| 2011 | 7.2% | Elevated |
| 2012 | 7.0% | Slightly declining |
| 2013 | 6.7% | Normalizing |
| 2014 | 6.6% | Normalizing |
| 2015 | 6.3% | Stable |
| 2016 | 6.1% | Stable |
| 2017 | 6.2% | Stable |
| 2018 | 6.2% | Stable |
| 2019 | 6.0% | Stable |
| 2020 | 2.0% | Moratorium |

### §3a. Composite Dispossession Weighting

The composite dispossession risk combines three data sources into pathway-specific rates. Each source maps to specific class transitions per FR-006:

| Source | Primary Pathway | Weight in LA→P rate | Weight in P→L rate |
|--------|----------------|--------------------|--------------------|
| Foreclosure | LA → Proletariat | 0.6 | 0.1 |
| Bankruptcy | Both pathways | 0.3 | 0.3 |
| Eviction | Proletariat → Lumpen | 0.1 | 0.6 |

**LA→Proletariat (dispossession) rate**: `0.6 * foreclosure_rate + 0.3 * bankruptcy_rate + 0.1 * eviction_rate`

**P→Lumpen component from dispossession**: `0.1 * foreclosure_rate + 0.3 * bankruptcy_rate + 0.6 * eviction_rate`

Note: The P→Lumpen dispossession component feeds into precaritization alongside unemployment (see FR-015). The DispossessionCalculator outputs both pathway-specific rates.

**Rationale**: Foreclosure primarily destroys accumulated home equity (the wealth that distinguishes LA from proletariat). Eviction primarily affects renters who are already proletariat, pushing them into labor market exclusion. Bankruptcy affects both pathways depending on the debtor's initial position. Weights are calibrated heuristics subject to refinement with per-county data (FE-007).

## 4. Savings Rate Schedule

**Decision**: Class-based step function with one base rate per ClassPosition.

**Rationale**: Per clarification session, this maps directly to the five ClassPosition categories. Values calibrated against Fed SCF data (Saez & Zucman 2020).

| ClassPosition | Base Savings Rate | Source |
|---------------|-------------------|--------|
| BOURGEOISIE | 38% | Saez & Zucman: top 1% |
| PETIT_BOURGEOISIE | 20% | SCF: 90th-99th percentile |
| LABOR_ARISTOCRACY | 12% | SCF: 50th-90th percentile |
| PROLETARIAT | 3% | SCF: bottom 50% (positive savers) |
| LUMPENPROLETARIAT | 0% | No savings capacity |

**Imperial rent adjustment**: Workers with positive imperial rent (Phi_hour > 0) have their effective consumption reduced, which increases the savings surplus. The adjustment is: `effective_savings = base_rate + phi_adjustment`, where `phi_adjustment = min(phi_hour * hours_per_year / wage, 0.05)` capped at 5 percentage points to prevent unrealistic savings.

**Alternatives considered**:
- Continuous logistic function: Rejected for overcomplicating without improving accuracy.
- SCF lookup table: Rejected because it requires microdata ingestion beyond MVP scope.

## 5. Crisis Amplification Model

**Decision**: Multiplicative amplifier on base transition rates during crisis periods.

**Rationale**: During crisis, downward transition rates increase non-linearly. A simple multiplier on base rates (e.g., 2x-5x for downward, 0.5x for upward) captures the accelerating pattern described in the spec without requiring complex feedback modeling.

**Crisis detection**: Via `crisis` flag on EconomicConditions (set externally by TRPF system or manual override). When `crisis=True`:
- Downward rates (dispossession, precaritization) multiplied by crisis_amplifier (default 2.5)
- Upward rates (accumulation, stabilization) multiplied by recovery_dampener (default 0.3)
- Net effect: dramatic acceleration of downward mobility + freeze on upward mobility

**Calibration rationale**: The 2.5x crisis amplifier is derived from comparing peak-crisis to stable-year dispossession rates in the hardcoded data. Foreclosure rates: 2010 peak (4.6%) / 2015 stable (0.6%) = 7.7x. Bankruptcy: 2010 (1.3%) / 2015 (0.6%) = 2.2x. Eviction: 2011 (7.2%) / 2015 (6.3%) = 1.1x. The weighted average across mechanisms (~2-3x) suggests 2.5x as a reasonable composite amplifier. The 0.3x recovery dampener reflects that upward mobility (hiring, wage growth) responds more slowly than downward shocks during crisis — consistent with labor market hysteresis literature. Both values should be validated against SC-002 (2x transition magnitude requirement) and tuned within validation Warning bounds during US5 implementation.

**Alternatives considered**:
- Feedback loops (unemployment -> foreclosure -> more unemployment): Deferred to FE-005 (TRPF integration). Current model treats crisis as an exogenous condition.
- Non-linear amplification function: Considered but multiplicative is simpler and sufficient for MVP.

## 6. Sum-to-One Invariant Enforcement

**Decision**: Normalize after transition to enforce sum-to-one invariant.

**Rationale**: Transition flows may produce shares that don't sum to exactly 1.0 due to floating-point arithmetic. Post-transition normalization ensures the invariant is always preserved.

**Algorithm**:
1. Compute raw transition flows for each pathway
2. Apply flows to get raw new shares
3. Clamp each share to [0.0, 1.0]
4. Normalize: divide each share by sum of all shares
5. Assert abs(sum - 1.0) < 0.001

This is the standard approach for probabilistic distributions.

## 7. Validation Ranges

**Decision**: Three-tier validation for transition rates and class shares, following gamma/validation.py pattern.

### Transition Rate Validation

| Metric | Expected | Warning | Fail |
|--------|----------|---------|------|
| Dispossession rate (LA->P) | [0.001, 0.05] | [0.0001, 0.10] | <0 or >0.20 |
| Accumulation rate (P->LA) | [0.001, 0.03] | [0.0001, 0.08] | <0 or >0.15 |
| Precaritization rate (P->L) | [0.005, 0.08] | [0.001, 0.15] | <0 or >0.25 |
| Stabilization rate (L->P) | [0.01, 0.10] | [0.005, 0.20] | <0 or >0.30 |

### Class Share Validation

| Metric | Expected | Warning | Fail |
|--------|----------|---------|------|
| LA share | [0.30, 0.50] | [0.20, 0.60] | <0 or >1.0 |
| Proletariat share | [0.25, 0.45] | [0.15, 0.55] | <0 or >1.0 |
| Lumpen share | [0.10, 0.25] | [0.05, 0.35] | <0 or >1.0 |

## 8. Existing Codebase Integration Points

**ClassPosition** (from `babylon.economics.melt.types`): Reuse directly. The five-class enum is the canonical class taxonomy.

**NoDataSentinel** (from `babylon.economics.tensor`): Reuse for data unavailability signaling. Follow CHK030 pattern with distinct messages per data source.

**NationalParameters** (from `babylon.economics.melt.parameters`): Provides MELT (tau), imperial rent values. Read-only dependency.

**ImperialRentCalculator** (from `babylon.economics.melt.imperial_rent`): Provides Phi_hour for accumulation adjustment. Read-only dependency.

**Test infrastructure**: Follow conftest.py mock pattern from `tests/unit/economics/gamma/conftest.py`. Mock data sources with DEFAULT dicts and configurable overrides. Include runtime protocol compliance check.
