# Research: Constants Remediation Sweep

**Feature**: 028-constants-remediation-sweep
**Date**: 2026-02-27
**Status**: Complete

## 1. GameDefines Architecture

### Decision: Use existing GameDefines subsection pattern for all constant centralization
### Rationale: GameDefines already has 20+ frozen Pydantic subsection classes with `Field(ge=, le=, description=)`. All new constants follow this pattern.
### Alternatives Considered: Separate YAML config file (rejected — fragments constant management), environment variables (rejected — not appropriate for simulation parameters)

**Key Findings:**
- `src/babylon/config/defines.py` — 1,568 lines, 25 subsection classes
- All subsections frozen: `model_config = ConfigDict(frozen=True)`
- Fields use `Field(default=X, ge=LO, le=HI, description="...")`
- YAML loading via `GameDefines.load_from_yaml()` with per-subsection defaults
- Existing subsections: crisis, economy, survival, vitality, solidarity, behavioral, tension, consciousness, territory, topology, metabolism, struggle, carceral, endgame, initial, precision, timescale, external_data, contradiction_field, reserve_army, dispossession, working_day, community

### New Subsections Required (Phase 4 — Tier C centralization)
None strictly required — inline constants map to existing subsections:
- Ideological routing → `consciousness`
- Vitality attrition → `vitality`
- Class dynamics ODE → new `class_dynamics` subsection (3+ constants with tuple type)
- Struggle consciousness → `struggle`
- Community system → `community`
- Edge transition → `contradiction_field` or new `edge_transition` subsection (16 thresholds)
- Dispossession scale → `dispossession`
- Credit cycle → `crisis`

## 2. Tier B Elimination — Reclassification Finding

### Decision: Tier B remediation splits into three action groups, not a single "delete" operation
### Rationale: Research revealed that 19 of 34 "Tier B" constants do NOT yet have GameDefines fields. They must be extracted INTO GameDefines first, then the inline/parameter defaults removed.
### Alternatives Considered: Direct deletion (rejected — would break callers that pass no explicit value)

**Three Action Groups:**

| Group | Action | Constants | Count |
|-------|--------|-----------|-------|
| A — Pure Delete | Delete module constant; callers already use GameDefines | EndgameDetector (5), TopologyMonitor GASEOUS/CONDENSATION (2) | 7 |
| B — Extract + Delete | Add to GameDefines, update callers, then delete inline default | DynamicBalance params (10), TopologyMonitor extras (5), Formula defaults (5+), Metrics DEATH_THRESHOLD (1) | ~21 |
| C — Redirect Callers | FormulaConstant already references GameDefines; redirect direct importers | LOSS_AVERSION_COEFFICIENT (1), EPSILON (1) | 2 |

**Total**: ~30 confirmed + 4 edge cases requiring verification = 34

**Detailed Tier B Inventory (verified locations):**

EndgameDetector (`src/babylon/engine/observers/endgame_detector.py`):
- Line 53: `PERCOLATION_THRESHOLD = 0.7` → `endgame.revolutionary_percolation_threshold`
- Line 54: `CONSCIOUSNESS_THRESHOLD = 0.8` → `endgame.revolutionary_consciousness_threshold`
- Line 57: `OVERSHOOT_THRESHOLD = 2.0` → `endgame.ecological_overshoot_threshold`
- Line 58: `OVERSHOOT_CONSECUTIVE_TICKS = 5` → `endgame.ecological_sustained_ticks`
- Line 61: `FASCIST_NODES_THRESHOLD = 3` → `endgame.fascist_majority_threshold`

TopologyMonitor (`src/babylon/engine/topology_monitor.py`):
- Line 55: `GASEOUS_THRESHOLD = 0.1` → `topology.gaseous_threshold`
- Line 56: `CONDENSATION_THRESHOLD = 0.5` → `topology.condensation_threshold`
- Line 57: `BRITTLE_MULTIPLIER = 2` → NEEDS GameDefines field
- Line 60: `POTENTIAL_MIN_STRENGTH = 0.1` → NEEDS GameDefines field
- Line 61: `ACTUAL_MIN_STRENGTH = 0.5` → NEEDS GameDefines field
- Line 64: `DEFAULT_REMOVAL_RATE = 0.2` → NEEDS GameDefines field
- Line 65: `DEFAULT_SURVIVAL_THRESHOLD = 0.4` → NEEDS GameDefines field

DynamicBalance (`src/babylon/formulas/dynamic_balance.py`, lines 28-39):
- 10 function parameter defaults (high_threshold=0.7, low_threshold=0.3, critical_threshold=0.1, bribery_wage_delta=0.05, austerity_wage_delta=-0.05, iron_fist_repression_delta=0.10, crisis_wage_delta=-0.15, crisis_repression_delta=0.20, bribery_tension_threshold=0.3, iron_fist_tension_threshold=0.5)
- ALL 10 need GameDefines fields in `economy` subsection

Metrics (`src/babylon/engine/observers/metrics.py`):
- Line 41: `DEATH_THRESHOLD = 0.001` → NEEDS GameDefines field; also duplicated in `tools/shared.py:82`

Formula module defaults:
- `solidarity.py:14` — `activation_threshold=0.3` → NEEDS `consciousness.solidarity_activation_threshold`
- `metabolic_rift.py:14` — `entropy_factor=1.2` → NEEDS `metabolism.entropy_factor`
- `curvature.py:32` — `alpha=0.5` → NEEDS `topology.curvature_alpha`
- `trpf.py:25` — `floor=0.1` → NEEDS `economy.trpf_efficiency_floor`
- `metabolic_rift.py:59` — `max_ratio=999.0` → NEEDS `metabolism.overshoot_max_ratio`

FormulaConstants (`src/babylon/formulas/constants.py`):
- Line 17: `LOSS_AVERSION_COEFFICIENT` — already loads from GameDefines.behavioral; callers import from formulas.constants instead of GameDefines directly
- Line 21: `EPSILON` — already loads from GameDefines.precision; shadow in `specs/024/contracts/distribution_formulas.py:15`

## 3. Tier A Pipeline-Ready Constants — Wiring Points

### Decision: Wire at simulation initialization via existing hydrator and adapter infrastructure
### Rationale: All 12 constants have working adapter pipelines. The `hydrate_territories()` pattern in `src/babylon/data/reference/hydrator.py` demonstrates the pattern: SQLite → adapter → computed value.
### Alternatives Considered: Lazy loading at first access (rejected — complicates frozen model pattern), pre-computed lookup table (rejected — loses FIPS-specific derivation)

**12 Pipeline-Ready Constants and Their Wiring Points:**

| # | Constant | Current Value | Adapter | Wiring Point |
|---|----------|--------------|---------|-------------|
| 1 | economy.extraction_efficiency | 0.8 | MarxianHydrator | compute_initial_profit_rate() already computes s/(c+v); extraction_efficiency derivable |
| 2 | economy.shadow_wage_hourly | 15.43 | ATUSDBLoader | load_county_summary() returns reproductive labor hours |
| 3 | economy.base_subsistence | 0.0005 | CensusLoader + FRED | ACS poverty threshold + CPI conversion |
| 4 | economy.min_wage_rate | 0.05 | SQLiteQCEWSource | QCEW wage distribution percentiles |
| 5 | economy.max_wage_rate | 0.35 | SQLiteQCEWSource + BEA | QCEW + BEA value-added ratio |
| 6 | reserve_army.sigmoid_r0 | 0.08 | FredAPIClient | FRED UNRATE series |
| 7 | tick init: bourgeoisie share | 0.01 | CensusLoader | Census ACS income distribution |
| 8 | tick init: petit_b share | 0.09 | CensusLoader | Census ACS income distribution |
| 9 | tick init: labor_aristocracy share | 0.40 | CensusLoader | Census ACS income distribution |
| 10 | tick init: proletariat share | 0.35 | CensusLoader | Census ACS income distribution |
| 11 | tick init: lumpen share | 0.15 | CensusLoader | Census ACS income distribution |
| 12 | tick init: unemployment rate | 0.05 | FredAPIClient | FRED UNRATE series (county-level proxy) |

**Tick Initializer Location**: `src/babylon/economics/tick/system.py` lines 320-342 (`_bootstrap_county_states()`)

**Critical Pattern**: The tick initializer uses `dist_dict.get("bourgeoisie", 0.01)` fallback pattern. The fix is to populate `dist_dict` from Census data BEFORE the `.get()` calls, keeping the hardcoded value as fallback only.

## 4. Tier C Inline Constants — Centralization Inventory

### Decision: 28 inline constants found (12 non-edge-transition + 16 edge transition thresholds)
### Rationale: The 027 audit identified "16 inline Tier C constants" + "16 edge transition thresholds" separately. Both groups need centralization into GameDefines.

**Non-Edge-Transition (12):**
1. `ideological_routing.py:39` — `_ROUTING_SCALE = 0.1` → `consciousness`
2. `ideological_routing.py:82` — `agitation_decay = 0.1` → `consciousness`
3. `vitality.py:42` — attrition base `0.5` → `vitality`
4. `class_dynamics.py:60` — `alpha_21 = 0.0006` → new `class_dynamics` subsection
5. `class_dynamics.py:71` — `gamma_3 = 0.0057` → new `class_dynamics` subsection
6. `class_dynamics.py:91` — equilibrium tuple `(0.305, 0.382, 0.294, 0.020)` → new `class_dynamics` subsection
7. `struggle.py:370` — consciousness boost `0.5` → `struggle`
8. `community.py:21` — `overlap_bonus = 0.1` → `community`
9. `community.py:22` — `rent_penalty = 0.05` → `community`
10. `community.py:81` — `maintenance_factor = 0.1` → `community`
11. `dispossession_events.py:91` — transfer scale `0.01` → `dispossession`
12. `credit/types.py:93` — `STAGNATION_CREDIT_GROWTH = 0.01` → `crisis`

**Edge Transition Thresholds (16 predicates in `edge_transition.py`):**
Lines 103-433, values range from 0.0 to 7.0 across 16 compound predicates controlling edge mode transitions (EXTRACTIVE↔TRANSACTIONAL↔SOLIDARISTIC↔ANTAGONISTIC↔CO_OPTIVE). Each predicate uses 1-2 threshold values.

## 5. Regression Infrastructure

### Decision: Use existing `tools/regression_test.py` with `TOLERANCE=1e-5` for gating
### Rationale: Infrastructure already exists with 5 scenarios, checkpoint capture at 10-tick intervals, GameDefines hash tracking, and CLI for generate/compare.

**Key Files:**
- `tools/regression_test.py` — generate and compare commands
- `tests/baselines/*.json` — stored baseline files
- `tools/shared.py` — shared constants (ADR036)

**Scenarios:** imperial_circuit, two_node, starvation, glut, fascist_bifurcation

**Workflow:** Before remediation, generate fresh baselines. After each cluster, compare against baselines. Tolerance: 1e-5.

**GameDefines Hash:** Baselines store SHA256 of GameDefines. When we add new fields (Tier B extraction), the hash changes. Must regenerate baselines after Tier B extraction but BEFORE Tier A wiring (to capture the "old behavior with clean GameDefines" state).

## 6. Parameter Sweep Infrastructure

### Decision: Existing `tools/tune_agent.py` with Optuna/Morris/Sobol infrastructure is sufficient
### Rationale: All 47 existing GameDefines Tier C constants already have `Field(ge=, le=)` bounds. The 16 inline constants just need to be added to GameDefines with similar bounds.

**Sweep Search Space Definition:** Introspected from GameDefines field metadata (Pydantic `model_fields`). Constants with `ge` and `le` constraints are automatically included.

**Coupled Cluster Constraints:** Must be enforced via Optuna's `suggest_float()` ordering or constraint callbacks. 10 clusters identified in 027 audit.
