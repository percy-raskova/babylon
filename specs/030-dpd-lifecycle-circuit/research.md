# Research: D-P-D' Lifecycle Circuit

**Feature**: 030-dpd-lifecycle-circuit | **Date**: 2026-02-27

## Phase 0: Resolved Unknowns

### R-001: Demographic Parameter Defaults

**Decision**: Use empirically calibrated defaults from CDC, Census Bureau, BLS, and SSA data (2023-2024). All values exposed as tunable `GameDefines` coefficients.

**Rationale**: Runtime data ingestion (CDC WONDER, ACS microdata) was explicitly scoped out per user decision. Instead, parameters are scientifically derived with provenance citations and encoded as tunable coefficients, allowing in-game modification for scenario modeling.

**Alternatives Considered**:
- Full CDC WONDER ingestion at runtime → rejected (scope creep, runtime I/O violates II.6)
- Hardcoded constants without provenance → rejected (violates III.1 No Magic Constants)

**Calibrated Parameters**:

| Parameter | Default | Source | Citation |
|-----------|---------|--------|----------|
| `birth_rate` | 0.0107 | CDC National Vital Statistics | 3.596M births / 336.5M pop (2023) |
| `rate_D_to_P` | 0.0556 | Structural (1/18 years) | Census age bracket 0-17 |
| `rate_P_to_D_prime` | 0.0213 | Structural (1/47 years) | Census working years 18-64 |
| `rate_D_prime_to_death` | 0.039 | CDC WONDER mortality + Census | 2.1M deaths 65+ / 54M pop 65+ (2023) |
| `initial_pop_D_frac` | 0.215 | Census Bureau 2024 | 21.5% under 18 |
| `initial_pop_P_frac` | 0.605 | Census Bureau 2024 | 60.5% ages 18-64 |
| `initial_pop_D_prime_frac` | 0.180 | Census Bureau 2024 | 18.0% ages 65+ |
| `pension_coverage_rate` | 0.73 | BLS National Compensation Survey | 73% of workers have access |
| `home_ownership_rate` | 0.656 | Census Bureau 2024 | 65.6% overall |
| `ss_replacement_rate` | 0.426 | SSA Office of the Actuary | Medium earner replacement rate |

**Critical Correction**: The elderly mortality rate computes empirically to 0.039, substantially lower than a naive 1/15 = 0.067 heuristic. Actual life expectancy at age 65 is 19.5 years (CDC 2023). The spec's US1 acceptance scenario uses 0.067 as a test-only value, which is acceptable for testing but must not be the production default.

**Supplementary Data by Demographics**:

| Metric | Lowest Quartile | Highest Quartile | Source |
|--------|-----------------|-------------------|--------|
| Retirement plan access | 49% | 92% | BLS NCS by wage quartile |
| Homeownership (Black) | 44.2% | — | Census 2024 |
| Homeownership (White) | 75.1% | — | Census 2024 |
| Homeownership (under 35) | 37.9% | — | Census 2024 |
| Homeownership (65+) | 79.0% | — | Census 2024 |

### R-002: Chetty Opportunity Atlas Integration

**Decision**: Use Mobility Atlas CSV data for development-time parameter derivation only. Extract key metrics (KFR by race/income, mortality gaps, covariate correlations) to calibrate tunable coefficients. No runtime CSV ingestion.

**Rationale**: The Chetty data provides county-level class mobility measures that directly quantify the mechanisms FR-010 (differential transition rates) and FR-017 (class mobility) model. Parameterizing from this data grounds the model in empirical reality while keeping runtime free of file I/O.

**Alternatives Considered**:
- Runtime CSV parsing per county → rejected (3,191 counties × 9 files = slow; violates II.6 no DB I/O during tick)
- Ignore Chetty data entirely → rejected (loses empirical grounding for mobility parameters)

**Key Derived Parameters from Mobility Atlas**:

| Metric | Pooled | Black | White | Gap | Source File |
|--------|--------|-------|-------|-----|-------------|
| KFR at P25 (mean income rank of children from P25 parents) | 0.445 | 0.342 | 0.476 | 0.134 | Table 1 / Table 4 |
| KFR at P75 | ~0.580 | ~0.480 | ~0.600 | ~0.120 | Table 1 / Table 4 |
| Mortality by age 32 at P25 | — | 0.0051 | 0.0041 | 0.0010 | Table 4 |
| Jail incarceration rate at P25 | — | ~0.025 | ~0.009 | ~0.016 | Table 4 |

**Covariate Schema (Table 8)**: 39 covariates per county including Gini coefficient, poverty rate, employment rate, college graduation rate, single-parent household fraction, median income by race, and racial composition. These inform the `class_mobility_function` in `mobility.py`.

**Parameter Derivation for GameDefines**:
- `mobility_base_rate`: 0.445 (pooled KFR at P25 — probability a child from bottom quartile reaches median)
- `mobility_racial_gap`: 0.134 (Black-White KFR gap at P25)
- `carceral_transition_modifier`: Derived from Black/White jail incarceration ratio (~2.8x)
- `early_mortality_modifier`: Derived from Black/White mortality ratio at P25 (~1.24x)

### R-003: Bifurcation Integration Seam

**Decision**: Extend `_compute_legitimation()` in `bifurcation.py` to accept an optional lifecycle legitimation index, blending it with the existing agitation-inverse computation.

**Rationale**: The current implementation at `bifurcation.py:183` computes `legitimation = 1 - mean(agitation)`. FR-005 specifies a weighted blend: `w * structural_index + (1-w) * agitation_inverse`. This preserves backward compatibility (when no lifecycle data exists, w=0 gives the current behavior).

**Integration Point**: `bifurcation.py:103` where `legitimation = self._compute_legitimation(graph, fips)`. The method signature gains an optional `lifecycle_legitimation: float | None = None` parameter.

### R-004: Engine System Insertion

**Decision**: Insert `LifecycleSystem` at position 7 in the turn order (between CommunitySystem at 6 and SolidaritySystem at 7, shifting subsequent systems up).

**Rationale**: Lifecycle dynamics (population transitions, legitimation) must execute after community hyperedge state is updated (CommunitySystem) but before solidarity transmission (SolidaritySystem) uses the updated population data. This respects VI.1 Material Base First — population dynamics (material) before solidarity (superstructure).

**Current Turn Order** (18 systems):
```
0: VitalitySystem → 1: TerritorySystem → 2: ProductionSystem →
3: EconomicSystem → 4: RentSystem → 5: DecompositionSystem →
6: CommunitySystem → [INSERT: LifecycleSystem] → 7: SolidaritySystem →
8: ConsciousnessSystem → 9: ControlSystem → 10: MetabolismSystem →
11: SurvivalSystem → 12: StruggleSystem → 13: IdeologySystem →
14: ContradictionSystem
```

### R-005: Existing Lifecycle Infrastructure

**Decision**: Build on existing YOUTH/ADULT/ELDER CommunityType values from Feature 029. DPDState is the quantitative layer alongside the qualitative XGI hyperedge layer.

**Rationale**: Feature 029 already implemented:
- `CommunityType.YOUTH`, `CommunityType.ADULT`, `CommunityType.ELDER` (enums.py:467-469)
- `HyperedgeCategory.LIFECYCLE_PHASE` (enums.py:489)
- `LIFECYCLE_COMMUNITIES = frozenset({YOUTH, ADULT, ELDER})` (community.py)
- `CONSCIOUSNESS_DEFAULTS` entries for all three lifecycle phases
- Unit tests confirming lifecycle phases in test_community_models.py

Feature 030 adds the quantitative population dynamics layer (DPDState, transition rates, legitimation index) that the qualitative layer from Feature 029 lacks. Constitution II.7 Category 3 explicitly defines this relationship.

### R-006: Shadow Subsidy Integration

**Decision**: FR-023 generational shadow subsidy metric connects to `reproduction.py:63` where `_REPRO_EXTERNALIZATION_FACTOR = 0.2` has a TODO for demographics wiring.

**Rationale**: The existing `_REPRO_EXTERNALIZATION_FACTOR` represents the fraction of reproduction costs externalized to households (Dept III invisible labor). Feature 030's shadow subsidy metric quantifies the *generational* analog: capital receives trained workers without paying for D-phase investment. The `dual_circuit.py` module computes this metric and exposes it for `reproduction.py` to consume.
