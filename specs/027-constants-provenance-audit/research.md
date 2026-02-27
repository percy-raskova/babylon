# Research: Magic Constants Provenance Audit

**Feature**: 027-constants-provenance-audit
**Date**: 2026-02-27

## R-001: Actual Constants Count and Structure

**Decision**: The audit scope is **136 in-scope scalar numerical constants** across 22 in-scope subsection models in `defines.py` (140 total across 25 models; 4 ServicesDefines layer numbers excluded per spec scope), plus ~50+ inline simulation-behavior literals throughout `src/babylon/`.

**Rationale**: Direct introspection of `src/babylon/config/defines.py` (1569 lines) reveals:

| Subsection Model | int | float | Total |
|---|---|---|---|
| CrisisDefines | 4 | 8 | 12 |
| EconomyDefines | 0 | 29 | 29 |
| SurvivalDefines | 0 | 6 | 6 |
| VitalityDefines | 0 | 2 | 2 |
| SolidarityDefines | 0 | 5 | 5 |
| BehavioralDefines | 0 | 1 | 1 |
| TensionDefines | 0 | 1 | 1 |
| ConsciousnessDefines | 0 | 2 | 2 |
| TerritoryDefines | 0 | 12 | 12 |
| TopologyDefines | 0 | 3 | 3 |
| MetabolismDefines | 0 | 3 | 3 |
| StruggleDefines | 0 | 8 | 8 |
| CarceralDefines | 4 | 3 | 7 |
| EndgameDefines | 2 | 3 | 5 |
| InitialDefines | 1 | 2 | 3 |
| PrecisionDefines | 1 | 2 | 3 |
| ServicesDefines | 4 | 0 | 4 |
| TimescaleDefines | 2 | 0 | 2 |
| ContradictionFieldDefines | 2 | 5 | 7 |
| ReserveArmyDefines | 0 | 4 | 4 |
| DispossessionDefines | 0 | 9 | 9 |
| WorkingDayDefines | 0 | 6 | 6 |
| CommunityDefines | 0 | 6 | 6 |
| ArcGISDefines | 0 | 0 | 0 (all strings) |
| ExternalDataDefines | 0 | 0 | 0 (nested models) |
| **TOTAL (all models)** | **20** | **120** | **140** |
| **In-scope total** | **16** | **120** | **136** |

**Scope exclusion**: ServicesDefines (4 int fields — all ArcGIS layer numbers) is excluded per spec Out of Scope: "External data source configuration (URLs, hosts, layer numbers) in ExternalDataDefines, ArcGISDefines, ServicesDefines." The **136** in-scope count is the validation target for SC-001.

**Non-scalar exclusions** (correctly omitted from counts above):
- `CrisisDefines.dispossession_cascade_milestones` (list[float], not scalar)
- `TerritoryDefines.displacement_priority_mode` (str, not numerical)
- `PrecisionDefines.rounding_mode` (str, not numerical)

Additionally, `defines.yaml` contains 14 sections but 6 subsections (crisis, contradiction_field, reserve_army, dispossession, working_day, community) use Python class defaults only — they have no YAML entries.

`formulas/constants.py` re-exports exactly 2 constants: `LOSS_AVERSION_COEFFICIENT` (2.25) and `EPSILON` (1e-9).

**Alternatives considered**: Counting only YAML-backed constants (would miss ~30 that use class defaults only). Rejected — the spec requires zero omissions from `defines.py`.

## R-002: Inline Literal Landscape

**Decision**: The inline literal audit will target ~50+ distinct simulation-behavior literals identified across 6 categories of inline usage patterns.

**Rationale**: Research identified the following non-centralized inline literal categories:

### Category 1: STUB/TODO/PLACEHOLDER/MAGIC markers (8 locations)
- `engine/simulation.py:768` — `_MVP_DECAY_RATE = 0.05` (explicitly STUB)
- `data/reference/hydrator.py:212` — `return 0.04` (explicitly STUB)
- 6 additional TODO markers in economics modules

### Category 2: Module-level constants not in GameDefines (~5 locations)
- `formulas/ideological_routing.py:39` — `_ROUTING_SCALE = 0.1`
- `formulas/ideological_routing.py:82` — `agitation_decay: float = 0.1`
- `formulas/vitality.py:42` — `0.5` base factor in attrition formula
- `engine/topology_monitor.py:55-65` — 7 deprecated constants still in use
- `engine/observers/endgame_detector.py:53-61` — 5 legacy constants (deprecated but retained)

### Category 3: Formula signature defaults duplicating GameDefines (~15 locations)
- `formulas/dynamic_balance.py:28-39` — all 10 bourgeoisie policy defaults
- `formulas/solidarity.py:14`, `formulas/metabolic_rift.py:14,59`, `formulas/trpf.py:25`
- `formulas/community.py:21,22,81` — 3 defaults

### Category 4: Hardcoded empirical coefficients (~20 values)
- `formulas/class_dynamics.py:57-91` — `ClassDynamicsParams` + `SecondOrderParams` (FRED-fitted ODE coefficients)
- `economics/gamma/adapters.py` — care-fraction NAICS coefficients (0.60, 0.30, 1.00)
- `economics/dynamics/hardcoded_data.py` — explicitly named hardcoded dataset

### Category 5: Edge transition thresholds (~17 values)
- `engine/systems/edge_transition.py` — all `PredicateCondition.threshold` values in `_TRANSITIONS` list

### Category 6: Factory/scenario defaults (~30 values)
- `engine/factories.py` — `create_proletariat()`, `create_bourgeoisie()` defaults
- `engine/scenarios.py` — scenario preset values and function defaults
- `engine/systems/metabolism.py:86-95` — fallback `attrs.get()` values
- `engine/systems/struggle.py:445,457` — fallback subsistence/organization values

### Category 7: Replicated defaults across files
- `national_identity = 0.5` default replicated across `ideology.py`, `struggle.py`, `solidarity.py`
- `consciousness_boost = solidarity_gain * 0.5` coefficient in `struggle.py:370`

**Alternatives considered**: Counting all 3,986 raw floating-point regex matches. Rejected — most are type-boundary clamps (0.0, 1.0), mathematical identities, or data-model field defaults that are structurally required.

## R-003: Derivable Infrastructure (Tier A Assessment Capability)

**Decision**: The existing tensor pipeline provides concrete derivation paths for a subset of constants, particularly in the economics domain. Feature 002 and 021 specs provide planned derivation paths for territory and struggle constants.

**Rationale**:

### Currently Available Infrastructure
| Infrastructure | Location | Derivable Constants |
|---|---|---|
| ValueTensor4x3 | `economics/tensor.py` | Exploitation rate (s/v), OCC (c/v), imperial rent, profit rate — can replace `extraction_efficiency`, `trpf_coefficient` |
| MELT Calculator | `economics/melt/` | τ = GDP/L, γ_basket, τ_effective — can replace `super_wage_rate`, `superwage_multiplier` |
| ClassPositionClassifier | `economics/melt/class_position.py` | Wealth percentile thresholds — can replace `worker_wealth`, `owner_wealth` |
| TensorRegistry | `economics/tensor_registry.py` | County-level tensor cache — enables per-county derivation |
| MarxianHydrator | `economics/hydrator.py` | Full QCEW → tensor pipeline — can derive department-level ratios |
| Gamma Visibility | `economics/gamma/` | γ_III, γ_import, γ_basket — can replace shadow wage assumptions |

### Planned Infrastructure (Feature 002)
- Contradiction field spatial gradients → can replace `TerritoryDefines` heat parameters
- Edge mode transition thresholds → can be empirically calibrated against Detroit data
- Ollivier-Ricci curvature → topology-derived thresholds replacing `TopologyDefines`

### Planned Infrastructure (Feature 021)
- Reserve army dynamics → can derive `ReserveArmyDefines` sigmoid parameters from BLS data
- Dispossession events → can derive dispossession weights from Eviction Lab/CoreLogic data
- Working day classification → can derive `WorkingDayDefines` thresholds from BLS hours data

## R-004: Calibration Infrastructure (Tier C Assessment Capability)

**Decision**: The existing parameter sweep tooling (Optuna + SALib) can calibrate any `GameDefines` field that is already part of the tunable parameter space.

**Rationale**:
- `tools/shared.py:get_tunable_parameters()` introspects all `GameDefines` fields with `Ge`/`Le`/`Gt`/`Lt` bounds
- Morris screening identifies which parameters matter most (mu* ranking)
- Sobol decomposition quantifies variance contribution (S1, ST indices)
- Optuna TPE finds optimal values within bounds
- `tools/tune_agent.py:OPTIMIZATION_BOUNDS` already defines tighter bounds for 11 high-priority parameters
- All tools use `run_simulation()` + `calculate_carceral_equilibrium_score()` as the objective

**Gap**: Constants NOT in GameDefines (inline literals, FRED-fitted coefficients) are NOT in the parameter sweep search space. These would need to be centralized first before calibration is possible.

## R-005: Constitution Article III Compliance Assessment

**Decision**: The audit directly serves Constitution Article III.1 ("No Magic Constants") and III.4 ("Data Source Traceability"). Every recommendation must comply with the approved data source table.

**Rationale**: The Constitution's approved data source list (III.4) includes:
QCEW, Census/ACS, BEA, FRED, HIFLD, BTS, FCC, ATUS, CDC WONDER, Piketty/WID, PWT, Census Trade, Eviction Lab, US Courts, ATTOM/CoreLogic, Fed SCF, Fed Z.1 Financial Accounts.

Anti-pattern VIII.6 ("Constants Without Data Sources") directly references III.1 and III.4.

The audit is the systematic enforcement mechanism for these principles.

## R-006: Bourgeoisie Policy Delta Cluster Analysis Scope

**Decision**: The bourgeoisie cluster (FR-010) encompasses **10 constants** in `EconomyDefines` plus the entire `calculate_bourgeoisie_decision()` formula in `formulas/dynamic_balance.py`.

**Rationale**: The cluster includes:
- `bribery_wage_delta` (0.05)
- `austerity_wage_delta` (-0.05)
- `iron_fist_repression_delta` (0.10)
- `crisis_wage_delta` (-0.15)
- `crisis_repression_delta` (0.20)
- `bribery_tension_threshold` (0.3)
- `iron_fist_tension_threshold` (0.5)
- `pool_high_threshold` (0.7)
- `pool_low_threshold` (0.3)
- `pool_critical_threshold` (0.1)

These form a coherent policy-decision subsystem consumed by `ImperialRentSystem._process_decision_phase`. The formula in `dynamic_balance.py` also duplicates all 10 values as default arguments. The sub-report must assess whether the Organization-as-Agent pattern (from Feature 017) can replace this entire hardcoded policy tree.

## R-007: TerritoryDefines Collapse Potential

**Decision**: The territory cluster (FR-011) encompasses 12 numerical constants, most of which have potential derivation paths through Feature 002's dialectical field topology.

**Rationale**: The 12 constants are:
- Heat dynamics: `heat_decay_rate`, `high_profile_heat_gain`, `eviction_heat_threshold`, `heat_spillover_rate`
- Rent/displacement: `rent_spike_multiplier`, `displacement_rate`
- Carceral geography: `clarity_profile_coefficient`, `concentration_camp_decay_rate`
- Thresholds: `elimination_rent_threshold`, `elimination_tension_threshold`, `containment_rent_threshold`, `containment_tension_threshold`

Feature 002's contradiction field spatial gradients and Ollivier-Ricci curvature provide a geometry-based alternative to these hardcoded heat/spillover parameters. The sub-report must assess which constants become redundant when the dialectical field is implemented.
