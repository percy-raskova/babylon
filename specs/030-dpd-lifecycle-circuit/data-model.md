# Data Model: D-P-D' Lifecycle Circuit

**Feature**: 030-dpd-lifecycle-circuit | **Date**: 2026-02-27

## Entities

### DPDState

**Purpose**: Frozen Pydantic model storing per-county population distribution across lifecycle phases plus transition rates and wealth data for a single tick.

**Relationship**: One per county per tick. Stored as node attribute on the county graph node. Computed by `LifecycleSystem.step()`.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| `pop_D` | `float` | >= 0 | Population in D phase (pre-productive) |
| `pop_P` | `float` | >= 0 | Population in P phase (productive) |
| `pop_D_prime` | `float` | >= 0 | Population in D' phase (post-productive) |
| `rate_D_to_P` | `Coefficient` | [0, 1] | Annual transition rate D → P |
| `rate_P_to_D_prime` | `Coefficient` | [0, 1] | Annual transition rate P → D' |
| `rate_D_prime_to_death` | `Coefficient` | [0, 1] | Annual mortality rate in D' |
| `birth_rate` | `Coefficient` | [0, 1] | Births per P-phase person per tick |
| `wealth_D_prime` | `Currency` | >= 0 | Aggregate wealth held by D' cohort |

**Computed Fields** (derived, never stored):
- `dependency_ratio: float` = `(pop_D + pop_D_prime) / pop_P`
- `total_population: float` = `pop_D + pop_P + pop_D_prime`

**Validation Rules**:
- Population conservation: `|total_pop[t] - total_pop[t-1] - births + deaths| / total_pop[t-1] < 0.001` (FR-002)
- All population fields must be non-negative
- Model is frozen (`ConfigDict(frozen=True)`)

**State Transitions**: Population flows each tick:
```
births → pop_D
pop_D × rate_D_to_P → pop_P
pop_P × rate_P_to_D_prime → pop_D_prime
pop_D_prime × rate_D_prime_to_death → [removed]
```

### LegitimationState

**Purpose**: Frozen Pydantic model storing legitimation index components and computed composite score per county.

**Relationship**: One per county per tick. Embedded within or alongside DPDState on graph node.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| `pension_coverage` | `Probability` | [0, 1] | Fraction of P-phase with pension access |
| `ss_replacement_rate` | `Probability` | [0, 1] | Social Security replacement ratio |
| `healthcare_security` | `Probability` | [0, 1] | Fraction with secure D' healthcare |
| `home_ownership_rate` | `Probability` | [0, 1] | P-phase home ownership rate |
| `retirement_confidence` | `Probability` | [0, 1] | Subjective D' security assessment |

**Computed Fields**:
- `legitimation_index: Probability` = weighted sum per FR-004 weights (0.25/0.25/0.25/0.15/0.10)
- `crisis_classification: str` = "CRISIS" if < 0.3, "UNSTABLE" if < 0.5, else "STABLE" (FR-006)

**Validation Rules**:
- All component fields in [0, 1]
- Legitimation index is a Probability (auto-clamped)
- Crisis classification is an enum, not a free string

### InheritanceFlow

**Purpose**: Frozen Pydantic model representing aggregate intergenerational wealth transfer at D' terminus for a county per tick.

**Relationship**: One per county per tick. Computed from `wealth_D_prime` and mortality rate.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| `total_transferred` | `Currency` | >= 0 | Total wealth transferred at D' death |
| `care_consumed` | `Currency` | >= 0 | Wealth consumed by D' care costs |
| `net_inheritance` | `Currency` | >= 0 | `total_transferred - care_consumed` |
| `inheritance_gini` | `Gini` | [0, 1] | Inequality of distribution |

**Validation Rules**:
- `care_consumed <= total_transferred`
- `net_inheritance = total_transferred - care_consumed`
- Gini computed via Pareto distribution (α parameter from wealth distribution)

**Pareto Distribution Parameters**:
- Top 1% owns ~33% → α ≈ 1.5 (derived from Fed SCF)
- Applied at familial unit level, not individual
- `inheritance_gini` must exceed income Gini for the same county (SC-003)

### LifecycleTransitionEvent

**Purpose**: Event emitted when population transitions between phases or when legitimation classification changes.

**Relationship**: Zero or more per county per tick. Published via EventBus.

| Field | Type | Source |
|-------|------|--------|
| `event_type` | `EventType` | One of new lifecycle event types |
| `fips` | `str` | County FIPS code |
| `tick` | `int` | Simulation tick |
| `detail` | `dict` | Event-specific payload |

**New EventType Values**:
- `LIFECYCLE_TRANSITION`: Population moved between phases (routine)
- `LEGITIMATION_CRISIS`: Classification changed to CRISIS
- `LEGITIMATION_RECOVERY`: Classification improved from CRISIS
- `INHERITANCE_TRANSFER`: D' death triggered inheritance flow
- `DUAL_CIRCUIT_INTERFERENCE`: Resource competition or dispossession short-circuit detected

### ClassMobilityParams

**Purpose**: Frozen Pydantic model storing Chetty-derived class mobility parameters per county.

**Relationship**: One per county, set at initialization (not updated per tick). Read-only during simulation.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| `mobility_base_rate` | `Coefficient` | [0, 1] | KFR pooled at P25 (default 0.445) |
| `mobility_racial_gap` | `Coefficient` | [0, 1] | Black-White KFR gap (default 0.134) |
| `carceral_modifier` | `Coefficient` | [0, 10] | Incarceration rate multiplier |
| `early_mortality_modifier` | `Coefficient` | [0, 10] | Premature death multiplier |

**Validation Rules**:
- `mobility_racial_gap <= mobility_base_rate` (gap cannot exceed base)
- All fields are Coefficients with documented provenance

### LifecycleDefines

**Purpose**: GameDefines category for all lifecycle circuit tunable parameters. Follows the existing category pattern in `defines.py`.

**Relationship**: One global instance, loaded from YAML or defaults.

| Field | Default | Type | Provenance |
|-------|---------|------|------------|
| `birth_rate` | 0.0107 | `Coefficient` | CDC NVSS 2023 |
| `rate_D_to_P` | 0.0556 | `Coefficient` | 1/18 years (Census) |
| `rate_P_to_D_prime` | 0.0213 | `Coefficient` | 1/47 years (Census) |
| `rate_D_prime_to_death` | 0.039 | `Coefficient` | CDC WONDER + Census 2023 |
| `initial_pop_D_frac` | 0.215 | `Probability` | Census 2024 |
| `initial_pop_P_frac` | 0.605 | `Probability` | Census 2024 |
| `initial_pop_D_prime_frac` | 0.180 | `Probability` | Census 2024 |
| `pension_coverage_rate` | 0.73 | `Probability` | BLS NCS 2024 |
| `home_ownership_rate` | 0.656 | `Probability` | Census 2024 |
| `ss_replacement_rate` | 0.426 | `Probability` | SSA 2024 |
| `healthcare_security` | 0.60 | `Probability` | Estimated composite |
| `retirement_confidence` | 0.50 | `Probability` | EBRI RCS survey |
| `legitimation_blend_weight` | 0.6 | `Probability` | Structural vs agitation weight |
| `legitimation_crisis_threshold` | 0.3 | `Probability` | FR-006 boundary |
| `legitimation_unstable_threshold` | 0.5 | `Probability` | FR-006 boundary |
| `pareto_alpha` | 1.5 | `Coefficient` | Fed SCF wealth dist |
| `care_cost_fraction` | 0.4 | `Probability` | Fraction of D' wealth consumed by care |
| `mobility_base_rate` | 0.445 | `Coefficient` | Chetty KFR pooled P25 |
| `mobility_racial_gap` | 0.134 | `Coefficient` | Chetty Black-White KFR gap P25 |
| `carceral_transition_modifier` | 2.8 | `Coefficient` | Chetty jail ratio |
| `early_mortality_modifier` | 1.24 | `Coefficient` | Chetty mortality ratio |
| `ideology_caregiver_weight` | 0.7 | `Probability` | FR-009 caregiver influence |
| `ideology_institutional_weight` | 0.3 | `Probability` | FR-009 institutional influence |
| `sandwich_squeeze_threshold` | 0.6 | `Probability` | FR-022 dependency ratio threshold |

**Validation Rules**:
- `initial_pop_D_frac + initial_pop_P_frac + initial_pop_D_prime_frac ≈ 1.0` (within 0.01)
- `legitimation_crisis_threshold < legitimation_unstable_threshold`
- `ideology_caregiver_weight + ideology_institutional_weight ≈ 1.0`

## Entity Relationships

```
LifecycleDefines (global)
    │
    │ provides defaults to
    ▼
DPDState (per county, per tick)
    │
    ├── computed from ──► LegitimationState (per county, per tick)
    │                         │
    │                         └── feeds ──► BifurcationRiskMetric.legitimation
    │
    ├── computed from ──► InheritanceFlow (per county, per tick)
    │                         │
    │                         └── modifies ──► SocialClass.wealth (next generation)
    │
    ├── emits ──► LifecycleTransitionEvent (via EventBus)
    │
    └── reads ──► ClassMobilityParams (per county, static)
                      │
                      └── modifies ──► rate_D_to_P, rate_P_to_D_prime (differential)
```
