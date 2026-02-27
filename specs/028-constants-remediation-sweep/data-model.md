# Data Model: Constants Remediation Sweep

**Feature**: 028-constants-remediation-sweep
**Date**: 2026-02-27

## Entity Overview

This feature does not introduce new persistent entities. It modifies the shape of one existing entity (GameDefines) and produces documentation artifacts. The data model below documents the changes to GameDefines and the structure of output artifacts.

## Entity: GameDefines (Modified)

**Location**: `src/babylon/config/defines.py`
**Type**: Frozen Pydantic model (immutable after construction)
**Current size**: 25 subsection classes, ~136 fields

### New Fields (Tier B Extraction — ~19 fields)

These fields currently exist only as inline constants or function parameter defaults. They must be added to GameDefines before their inline sources can be removed.

#### EconomyDefines (10 new fields from DynamicBalance)

| Field | Type | Default | ge | le | Description |
|-------|------|---------|----|----|-------------|
| pool_high_threshold | float | 0.7 | 0.0 | 1.0 | Rent pool ratio triggering BRIBERY policy |
| pool_low_threshold | float | 0.3 | 0.0 | 1.0 | Rent pool ratio triggering AUSTERITY |
| pool_critical_threshold | float | 0.1 | 0.0 | 1.0 | Rent pool ratio triggering CRISIS policy |
| bribery_wage_delta | float | 0.05 | 0.0 | 0.5 | Wage increase during BRIBERY |
| austerity_wage_delta | float | -0.05 | -0.5 | 0.0 | Wage cut during AUSTERITY |
| iron_fist_repression_delta | float | 0.10 | 0.0 | 0.5 | Repression increase during IRON_FIST |
| crisis_wage_delta | float | -0.15 | -0.5 | 0.0 | Emergency wage cut during CRISIS |
| crisis_repression_delta | float | 0.20 | 0.0 | 0.5 | Repression spike during CRISIS |
| bribery_tension_threshold | float | 0.3 | 0.0 | 1.0 | Max tension for BRIBERY |
| iron_fist_tension_threshold | float | 0.5 | 0.0 | 1.0 | Min tension for IRON_FIST |

**Ordering Constraint**: pool_critical < pool_low < pool_high; bribery_tension < iron_fist_tension

#### TopologyDefines (5 new fields from TopologyMonitor)

| Field | Type | Default | ge | le | Description |
|-------|------|---------|----|----|-------------|
| brittle_multiplier | float | 2.0 | 1.0 | 10.0 | Brittle movement detection ratio |
| solidarity_sympathizer_threshold | float | 0.1 | 0.0 | 1.0 | Min SOLIDARITY edge strength for sympathizer |
| solidarity_cadre_threshold | float | 0.5 | 0.0 | 1.0 | Min SOLIDARITY edge strength for cadre |
| resilience_removal_rate | float | 0.2 | 0.0 | 1.0 | Node removal rate for resilience test |
| resilience_survival_threshold | float | 0.4 | 0.0 | 1.0 | Min connectivity for survival |

**Ordering Constraint**: solidarity_sympathizer < solidarity_cadre

#### PrecisionDefines (1 new field from Metrics)

| Field | Type | Default | ge | le | Description |
|-------|------|---------|----|----|-------------|
| death_threshold | float | 0.001 | 0.0 | 1.0 | Wealth below which entity is considered dead |

#### Formula-level extractions (to existing subsections)

| Target Subsection | Field | Default | Description |
|-------------------|-------|---------|-------------|
| consciousness | solidarity_activation_threshold | 0.3 | Min consciousness to enable solidarity transmission |
| metabolism | entropy_factor | 1.2 | Ecological cost multiplier for extraction |
| topology | curvature_alpha | 0.5 | Self-loop weight in Ollivier-Ricci curvature |
| economy | trpf_efficiency_floor | 0.1 | Minimum TRPF multiplier |
| metabolism | overshoot_max_ratio | 999.0 | Overshoot cap when biocapacity depleted |

### Deleted Fields/Constants (Tier B Elimination)

| Source | Constants Removed | Count |
|--------|------------------|-------|
| EndgameDetector module-level | PERCOLATION_THRESHOLD, CONSCIOUSNESS_THRESHOLD, OVERSHOOT_THRESHOLD, OVERSHOOT_CONSECUTIVE_TICKS, FASCIST_NODES_THRESHOLD | 5 |
| TopologyMonitor module-level | GASEOUS_THRESHOLD, CONDENSATION_THRESHOLD (+ 5 above after extraction) | 7 |
| DynamicBalance param defaults | 10 function parameter defaults (after extraction) | 10 |
| FormulaConstant re-exports | LOSS_AVERSION_COEFFICIENT, EPSILON redirected | 2 |
| Metrics module-level | DEATH_THRESHOLD (after extraction) | 1 |
| Formula module defaults | 5 function parameter defaults (after extraction) | 5 |
| tools/shared.py | DEATH_THRESHOLD duplicate | 1 |
| specs/024 contracts | EPSILON shadow | 1 |

## Artifact: Triage Record (New — FR-003 Output)

**Location**: `specs/028-constants-remediation-sweep/reports/triage-report.md`
**Format**: Markdown table with structured fields

| Field | Type | Description |
|-------|------|-------------|
| constant_path | string | GameDefines path or inline location (e.g., `economy.extraction_efficiency`) |
| tier | enum(A,B,C,D,E) | Classification from 027 audit |
| disposition | enum | One of: WIRED, ELIMINATED, CENTRALIZED, QUARANTINED, DOCUMENTED, DEFERRED |
| reason | string | Why this disposition was chosen |
| blocking_feature | string? | Feature number blocking remediation (Tier A gated only) |
| data_source | string? | Constitution III.4 data source (Tier A only) |

## Artifact: Falsifiability Statement (New — FR-004 Output)

**Location**: Inline in triage report and as code comments at wiring points

| Field | Type | Description |
|-------|------|-------------|
| constant_path | string | The constant being wired |
| derivation | string | How the value is computed from data |
| falsifying_observation | string | What Wayne/Oakland County observation would disprove this |
| data_source | string | Constitution III.4 source used |

## Artifact: Deviation Record (New — FR-005 Output)

**Location**: `specs/028-constants-remediation-sweep/reports/deviation-log.md`

| Field | Type | Description |
|-------|------|-------------|
| constant_path | string | The constant that changed |
| old_value | float | Previous hardcoded value |
| new_value | float | Data-derived value |
| data_source | string | Where new value comes from |
| justification | string | Why the deviation is acceptable |
| regression_impact | string | Which regression scenario(s) affected |

## State Transitions

No entity lifecycle state transitions. Constants move through a one-way disposition pipeline:

```
INVENTORIED (027 audit)
  → WIRED (US1: data-derived at init)
  → ELIMINATED (US2: deleted from codebase)
  → CENTRALIZED (US3: moved to GameDefines with sweep bounds)
  → DOCUMENTED (US4: Tier D/E with description text)
  → DEFERRED (US4: Tier A gated by upstream features)
```

Each constant enters exactly one terminal state. Sum of all terminal states = 247.
