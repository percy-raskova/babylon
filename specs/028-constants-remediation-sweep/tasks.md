# Tasks: Constants Remediation Sweep

**Input**: Design documents from `/specs/028-constants-remediation-sweep/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md
**Branch**: `028-constants-remediation-sweep`

**Organization**: Tasks are grouped by user story and follow the execution order from plan.md (US2 before US1 per FR-001 phased execution). Story priority labels reflect spec.md value ordering (US1=P1 highest value), while phase position reflects dependency ordering.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same phase)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

______________________________________________________________________

## Phase 1: Setup (Baseline Establishment)

**Purpose**: Generate regression baselines from current codebase state before any modifications. This is Phase A from plan.md.

- [ ] T001 Generate fresh regression baselines with `mise run qa:regression-generate` in `tests/baselines/`
- [ ] T002 Verify baselines pass with `mise run qa:regression`
- [ ] T003 Verify clean starting state with `mise run check` (lint + format + typecheck + test:unit)

**Checkpoint**: Baselines captured. Any future regression failures indicate behavioral changes from remediation.

______________________________________________________________________

## Phase 2: US2 — Tier B Dead Code Elimination (Priority: P2)

**Goal**: Remove all 34 Tier B constants (duplicates, deprecated fallbacks, dead code) with zero behavioral change. Reduces constant surface area by 14%.

**Independent Test**: After completion, `mise run check` + `mise run qa:regression` pass with identical outcomes to Phase 1 baselines.

**Execution order**: US2 executes before US1 per FR-001 because dead code removal has zero behavioral impact and cleans the GameDefines surface for accurate cascade analysis.

### B.1: Extract New Fields to GameDefines

> 19 of the 34 "Tier B" constants lack GameDefines fields. They must be extracted INTO GameDefines first, before their inline sources can be removed.

- [ ] T004 [US2] Add 10 DynamicBalance fields to `EconomyDefines` in `src/babylon/config/defines.py`: pool_high_threshold(0.7), pool_low_threshold(0.3), pool_critical_threshold(0.1), bribery_wage_delta(0.05), austerity_wage_delta(-0.05), iron_fist_repression_delta(0.10), crisis_wage_delta(-0.15), crisis_repression_delta(0.20), bribery_tension_threshold(0.3), iron_fist_tension_threshold(0.5). Add `Field(ge=, le=, description=)` with ordering constraints documented.
- [ ] T005 [US2] Add 5 TopologyMonitor fields to `TopologyDefines` in `src/babylon/config/defines.py`: brittle_multiplier(2.0), solidarity_sympathizer_threshold(0.1), solidarity_cadre_threshold(0.5), resilience_removal_rate(0.2), resilience_survival_threshold(0.4). Add `Field(ge=, le=, description=)`.
- [ ] T006 [US2] Add 4 remaining fields to existing subsections in `src/babylon/config/defines.py`: `precision.death_threshold`(0.001), `consciousness.solidarity_activation_threshold`(0.3), `metabolism.entropy_factor`(1.2), `metabolism.overshoot_max_ratio`(999.0), `topology.curvature_alpha`(0.5), `economy.trpf_efficiency_floor`(0.1). Add `Field(ge=, le=, description=)`.

### B.2: Delete Deprecated Module Constants (Pure Delete)

> These constants already have GameDefines equivalents. Just delete the module-level constant and update any test imports.

- [ ] T007 [P] [US2] Delete 5 deprecated module constants from `src/babylon/engine/observers/endgame_detector.py` (lines 53-61: PERCOLATION_THRESHOLD, CONSCIOUSNESS_THRESHOLD, OVERSHOOT_THRESHOLD, OVERSHOOT_CONSECUTIVE_TICKS, FASCIST_NODES_THRESHOLD). Update any test files that import these constants.
- [ ] T008 [P] [US2] Delete GASEOUS_THRESHOLD and CONDENSATION_THRESHOLD from `src/babylon/engine/topology_monitor.py` (lines 55-56). These are already deprecated — code uses constructor-injected values.

### B.3: Extract + Delete (Update Callers Then Remove Defaults)

> After T004-T006 add the GameDefines fields, update each caller to use the GameDefines path, then remove the inline default.

- [ ] T009 [US2] Update `calculate_bourgeoisie_decision()` in `src/babylon/formulas/dynamic_balance.py` — remove 10 function parameter defaults (lines 28-39), require caller to pass explicit GameDefines values. Update all call sites in `src/babylon/engine/systems/` to pass `defines.economy.*` values.
- [ ] T010 [P] [US2] Update `TopologyMonitor` in `src/babylon/engine/topology_monitor.py` — accept 5 extracted constants via `__init__` from GameDefines.topology (brittle_multiplier, solidarity thresholds, resilience params). Delete module constants (lines 57-65).
- [ ] T011 [P] [US2] Extract DEATH_THRESHOLD to `GameDefines.precision.death_threshold` — update `src/babylon/engine/observers/metrics.py` (line 41) to use defines. Remove duplicate from `tools/shared.py` (line 82), update `tools/regression_test.py` if it references the shared constant.
- [ ] T012 [P] [US2] Update `calculate_solidarity_transmission()` in `src/babylon/formulas/solidarity.py` — remove `activation_threshold=0.3` default (line 14), require explicit `defines.consciousness.solidarity_activation_threshold`.
- [ ] T013 [P] [US2] Update `src/babylon/formulas/metabolic_rift.py` — remove `entropy_factor=1.2` default and `max_ratio=999.0` default, require explicit `defines.metabolism.*` values.
- [ ] T014 [P] [US2] Update `src/babylon/formulas/curvature.py` — remove `alpha=0.5` default (line 32), require explicit `defines.topology.curvature_alpha`.
- [ ] T015 [P] [US2] Update `src/babylon/formulas/trpf.py` — remove `floor=0.1` default (line 25), require explicit `defines.economy.trpf_efficiency_floor`.

### B.4: Redirect FormulaConstant Callers

- [ ] T016 [US2] Redirect importers of `LOSS_AVERSION_COEFFICIENT` from `formulas.constants` to use `GameDefines.behavioral.loss_aversion_lambda` directly — update `src/babylon/formulas/fundamental_theorem.py`, `survival_calculus.py`, `ideological_routing.py`.
- [ ] T017 [P] [US2] Redirect importers of `EPSILON` from `formulas.constants` to use `GameDefines.precision.epsilon` — update `survival_calculus.py`. Remove shadow `EPSILON = 1e-9` from `specs/024-capital-volume-iii/contracts/distribution_formulas.py` (line 15).

### B.5: Verification

- [ ] T018 [US2] Update `tests/unit/config/test_constants_sync.py` for new GameDefines fields and removed constants. Verify all new fields are tested.
- [ ] T019 [US2] Run `mise run check` + `mise run qa:regression` to verify zero behavioral change from all Tier B modifications.
- [ ] T020 [US2] Regenerate regression baselines with `mise run qa:regression-generate` — baselines now reflect new GameDefines hash (added fields).

**Checkpoint**: 34 Tier B constants eliminated. Test suite and regression pass with identical outcomes. GameDefines has ~19 new fields. Baseline regenerated for Phase 3.

______________________________________________________________________

## Phase 3: US1 — Wire Pipeline-Ready Constants to Federal Data (Priority: P1)

**Goal**: Wire 12 pipeline-ready Tier A constants to their federal data sources via existing SQLite adapters. Values derived programmatically at simulation initialization.

**Independent Test**: Initialize simulation with Wayne County FIPS 26163. Assert 12 constants hold data-derived values, not GameDefines scalar defaults. Run regression — deviations documented per FR-005.

### C.1: Hydration Functions (TDD)

- [ ] T021 [US1] Write integration tests for constant hydration in `tests/integration/test_constant_hydration.py` — test that `hydrate_class_shares("26163", 2022)` returns non-default values from Census/QCEW data, that `hydrate_economy_constants("26163", 2022)` returns non-default extraction_efficiency/shadow_wage/subsistence, and that fallback to GameDefines defaults works when FIPS data is missing. Tests should FAIL initially (RED phase).
- [ ] T022 [US1] Implement `hydrate_class_shares(fips, year, session)` in `src/babylon/data/reference/hydrator.py` — query Census/QCEW for 5 class shares + unemployment rate, return dict keyed by class name. Fallback to GameDefines defaults on missing data with logged warning.
- [ ] T023 [US1] Implement `hydrate_economy_constants(fips, year, session)` in `src/babylon/data/reference/hydrator.py` — compute extraction_efficiency via MarxianHydrator s/(c+v) ratio, shadow_wage_hourly via ATUSDBLoader, base_subsistence via Census ACS poverty threshold, min/max_wage_rate via QCEW percentiles + BEA value-added. Fallback to GameDefines defaults on missing data.
- [ ] T024 [US1] Implement `hydrate_reserve_army(fips, year, session)` in `src/babylon/data/reference/hydrator.py` — derive sigmoid_r0 from FRED UNRATE series for target county/state. Fallback to GameDefines default on missing data.

### C.2: Wire Constants at Initialization

- [ ] T025 [US1] Wire class share hydration into `_bootstrap_county_states()` in `src/babylon/economics/tick/system.py` (lines 320-342) — call `hydrate_class_shares()` to populate `dist_dict` BEFORE the `.get()` fallback calls. Keep current hardcoded values as fallback only.
- [ ] T026 [US1] Wire economy constants at simulation initialization — override GameDefines defaults for extraction_efficiency, shadow_wage_hourly, base_subsistence, min_wage_rate, max_wage_rate with hydrated values. Use `defines.model_copy(update={...})` pattern.
- [ ] T027 [US1] Wire reserve_army.sigmoid_r0 at simulation initialization from FRED-derived value.

### C.3: Documentation (FR-004, FR-005)

- [ ] T028 [US1] Write falsifiability statements for each of the 12 wired constants in `specs/028-constants-remediation-sweep/reports/falsifiability-statements.md` — for each constant, document: derivation equation, data source, and what Wayne/Oakland County observation would disprove it (FR-004).
- [ ] T029 [US1] Run `mise run qa:regression` — document all value deviations in `specs/028-constants-remediation-sweep/reports/deviation-log.md` with: old value, new data-derived value, data source, theoretical justification (FR-005).

### C.4: Verification

- [ ] T030 [US1] Run `mise run check` + `mise run test:all` to verify engine stability with data-derived constants.

**Checkpoint**: 12 Tier A constants data-derived at initialization. Integration tests pass. Regression deviations documented. Falsifiability statements complete.

______________________________________________________________________

## Phase 4: US3 — Centralize and Sweep Tier C Calibration Constants (Priority: P3)

**Goal**: Centralize 28 inline Tier C constants into GameDefines with explicit sweep bounds. Verify all 63+ Tier C constants are visible to parameter sweep infrastructure.

**Independent Test**: Run `mise run tune:morris 20` — all 63+ Tier C constants produce importance rankings. No Tier C constant missing from search space.

### D.1: Centralize Non-Edge-Transition Constants (12)

- [ ] T031 [US3] Add 12 non-edge-transition inline Tier C constants to GameDefines in `src/babylon/config/defines.py`: `consciousness.routing_scale`(0.1), `consciousness.agitation_decay_rate`(0.1), `vitality.attrition_base_factor`(0.5), `struggle.consciousness_solidarity_boost`(0.5), `community.overlap_solidarity_bonus`(0.1), `community.rent_solidarity_penalty`(0.05), `community.organizer_maintenance_factor`(0.1), `dispossession.transfer_scale`(0.01), `crisis.stagnation_credit_growth`(0.01). Add new `class_dynamics` subsection with `alpha_21`(0.0006), `gamma_3`(0.0057), `equilibrium_target`(tuple). All with `Field(ge=, le=, description=)`.
- [ ] T032 [US3] Update `src/babylon/formulas/ideological_routing.py` — replace `_ROUTING_SCALE` module constant (line 39) and `agitation_decay` default (line 82) with GameDefines.consciousness reads.
- [ ] T033 [P] [US3] Update `src/babylon/formulas/vitality.py` — replace hardcoded attrition base `0.5` (line 42) with GameDefines.vitality.attrition_base_factor.
- [ ] T034 [P] [US3] Update `src/babylon/formulas/class_dynamics.py` — replace ClassDynamicsParams.alpha_21 (line 60), gamma_3 (line 71), SecondOrderParams.equilibrium (line 91) with GameDefines.class_dynamics reads.
- [ ] T035 [P] [US3] Update `src/babylon/engine/systems/struggle.py` — replace hardcoded consciousness boost `0.5` (line 370) with GameDefines.struggle.consciousness_solidarity_boost.
- [ ] T036 [P] [US3] Update `src/babylon/formulas/community.py` — replace overlap_bonus (line 21), rent_penalty (line 22), maintenance_factor (line 81) defaults with GameDefines.community reads.
- [ ] T037 [P] [US3] Update `src/babylon/engine/systems/dispossession_events.py` — replace transfer scale `0.01` (line 91) with GameDefines.dispossession.transfer_scale. Update `src/babylon/economics/credit/types.py` — replace STAGNATION_CREDIT_GROWTH (line 93) with GameDefines.crisis.stagnation_credit_growth.

### D.2: Centralize Edge Transition Thresholds (16)

- [ ] T038 [US3] Add 16 edge transition threshold fields to GameDefines in `src/babylon/config/defines.py` — either extend `ContradictionFieldDefines` or create new `EdgeTransitionDefines` subsection. Fields: extraction_contested_threshold(5.0), extraction_broken_threshold(2.0), concessions_exploitation_threshold(3.0), concessions_rent_threshold(2.0), mutual_aid_threshold(2.0), market_failure_threshold(1.0), power_asymmetry_threshold(5.0), co_optive_power_threshold(3.0), solidarity_degrades_threshold(6.0), betrayal_threshold(3.0), conflict_resolved_threshold(3.0), shared_enemy_threshold(7.0), reform_rent_threshold(3.0), co_optation_normalizes_threshold(2.0), co_optive_breakdown_threshold(1.0), concessions_withdrawn_threshold(1.0). All with `Field(ge=0.0, le=10.0, description=)`.
- [ ] T039 [US3] Update `src/babylon/engine/systems/edge_transition.py` — replace all 16 hardcoded threshold values (lines 103-433) in predicate functions with GameDefines reads. Each predicate function should accept defines parameter or read from injected config.

### D.3: Verify Sweep Space

- [ ] T040 [US3] Verify all Tier C constants appear in parameter sweep search space — run `mise run tune:morris 20` and confirm all 63+ constants (47 existing + 12 newly centralized + 16 edge transition) produce importance rankings.
- [ ] T041 [US3] Run `mise run check` + `mise run qa:regression` to verify engine stability after centralization.

**Checkpoint**: 28 inline Tier C constants centralized. All 63+ Tier C constants visible to parameter sweep. Regression passes.

______________________________________________________________________

## Phase 5: US4 — Triage Feature-Gated and Document Design Constants (Priority: P4)

**Goal**: Document disposition for all 138 remaining constants (25 gated Tier A, 14 Tier D, 99 Tier E). Close the audit loop — every constant in the 247 inventory has an explicit disposition.

**Independent Test**: Triage report contains exactly 247 entries. Sum: wired(12) + eliminated(34) + centralized(~28) + documented(113) + deferred(25) = ~247 (adjusted if inline constant count differs from estimate).

### E.1: Tier D Engineering Documentation (14 constants)

- [ ] T042 [P] [US4] Add constraint rationale to `description=` for 14 Tier D engineering constants in `src/babylon/config/defines.py` — document why each value is structurally determined (e.g., `precision.epsilon`: "Division-by-zero guard. Must satisfy epsilon < 10^-decimal_places", `precision.exp_clamp_low/high`: "Prevents math.exp overflow", `timescale.tick_duration_days`: "Physical constant: 7 days/week").

### E.2: Tier E Game Design Documentation (99 constants)

- [ ] T043 [P] [US4] Add "Game design" labels to `description=` for Tier E constants in `src/babylon/config/defines.py` — for each, add text: "Game design: [brief rationale]. Not data-derived." Organize by subsection: struggle(8), endgame(5), carceral(4), working_day(6), initial(3), inline mechanics(45+), other(28+).

### E.3: Gated Tier A Triage (25 constants)

- [ ] T044 [US4] Document 25 feature-gated Tier A constants in `specs/028-constants-remediation-sweep/reports/triage-report.md` — for each: constant path, blocking feature (002/013/021/024), required adapter (PWT/Census Trade/US Courts/ATTOM/Fed SCF/Fed Z.1), and estimated unblock condition.

### E.4: Complete Triage Report

- [ ] T045 [US4] Generate complete triage report with all 247 dispositions in `specs/028-constants-remediation-sweep/reports/triage-report.md` — consolidate US1 wired (12), US2 eliminated (34), US3 centralized (28+), US4 documented (113), US4 deferred (25). Validate against `contracts/disposition-schema.yaml`. Verify sum = 247 (FR-008).
- [ ] T046 [US4] Run `mise run check` to verify description updates pass typecheck and linting.

**Checkpoint**: All 247 constants have documented dispositions. Triage report validates against schema. Sum verified.

______________________________________________________________________

## Phase 6: Polish & Final Verification

**Purpose**: Full verification across all user stories. Update project documentation.

- [ ] T047 Run `mise run test:all` — full non-AI test suite passes
- [ ] T048 Run `mise run qa:regression` — final baseline comparison (if baselines regenerated, compare against Phase 3 baselines)
- [ ] T049 Validate FR-008 accountability: confirm disposition count in triage report matches 247
- [ ] T050 Update `ai-docs/state.yaml` with feature 028 completion status, new test counts, and component changes

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US2 (Phase 2)**: Depends on Setup completion — executes FIRST per FR-001 (zero behavioral change)
- **US1 (Phase 3)**: Depends on US2 completion — needs clean GameDefines surface + regenerated baselines
- **US3 (Phase 4)**: Depends on US2 completion — needs clean GameDefines surface for field additions
- **US4 (Phase 5)**: Can start after US1 + US3 — needs final constant disposition counts
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

```text
Phase 1: Setup
    │
    ▼
Phase 2: US2 (Tier B elimination — zero behavioral change)
    │
    ├──────────────────┐
    ▼                  ▼
Phase 3: US1       Phase 4: US3
(Tier A wiring)    (Tier C centralization)
    │                  │
    └──────┬───────────┘
           ▼
    Phase 5: US4 (Triage & documentation)
           │
           ▼
    Phase 6: Polish
```

- **US1 and US3 can run in parallel** after US2 completes (different files, different constant tiers)
- **US4 depends on US1 + US3** to know final disposition counts for the triage report

### Within Each User Story

- GameDefines field additions BEFORE caller updates (T004-T006 before T007-T015)
- Caller updates marked [P] can run in parallel (different files)
- Verification tasks AFTER all implementation tasks
- Commit after each logical sub-phase (B.1, B.2, B.3, etc.)

### Parallel Opportunities

**Within Phase 2 (US2):**
- T007+T008 in parallel (different files: endgame_detector.py, topology_monitor.py)
- T009-T015 in parallel after T004-T006 complete (different formula/engine files)
- T016+T017 in parallel (different formula files)

**Between Phases 3 and 4:**
- Phase 3 (US1) and Phase 4 (US3) can execute in parallel — US1 modifies hydrator.py + tick/system.py, US3 modifies formula modules + edge_transition.py. No file conflicts.

**Within Phase 4 (US3):**
- T033-T037 in parallel after T031 complete (different formula/engine files)

**Within Phase 5 (US4):**
- T042+T043 in parallel (both modify defines.py descriptions but different constants — can be batched)

______________________________________________________________________

## Parallel Example: US2 Caller Updates

```bash
# After T004-T006 (GameDefines field additions) complete, launch in parallel:
T009: Update dynamic_balance.py callers
T010: Update topology_monitor.py constants
T011: Extract DEATH_THRESHOLD to GameDefines
T012: Update solidarity.py defaults
T013: Update metabolic_rift.py defaults
T014: Update curvature.py defaults
T015: Update trpf.py defaults
```

## Parallel Example: US1 + US3

```bash
# After US2 completes, launch both in parallel:
# Agent A: Phase 3 (US1 — Tier A wiring)
T021-T030: Hydration functions + wiring + documentation

# Agent B: Phase 4 (US3 — Tier C centralization)
T031-T041: GameDefines additions + formula updates + sweep verification
```

______________________________________________________________________

## Implementation Strategy

### MVP First (US2 Only)

1. Complete Phase 1: Setup (baselines)
2. Complete Phase 2: US2 — Tier B Elimination
3. **STOP and VALIDATE**: `mise run check` + `mise run qa:regression` — zero behavioral change
4. Result: 34 dead constants removed, 19 new GameDefines fields, 14% surface reduction

### Incremental Delivery

1. Setup → Baselines captured
2. US2 → Dead code eliminated, GameDefines cleaned (MVP foundation)
3. US1 → 12 constants data-derived, falsifiability documented (highest value)
4. US3 → 28 inline constants centralized, sweep-ready (calibration enabled)
5. US4 → All 247 constants dispositioned, audit loop closed (completeness)
6. Each story adds value without breaking previous stories

### Parallel Agent Strategy

With two agents after US2:
- **Agent A**: US1 (hydrator.py, tick/system.py, reports/)
- **Agent B**: US3 (defines.py, formula modules, edge_transition.py)
- **Reconvene**: US4 (triage report consolidation)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks at same level
- [US*] label maps task to specific user story for traceability
- US2 executes before US1 despite lower priority — zero behavioral impact makes it safe to do first
- US1 and US3 can run in parallel after US2 — no file conflicts between tiers
- Commit after each sub-phase (B.1, B.2, etc.) per CLAUDE.md "Commit Early, Commit Often"
- GameDefines is a SINGLE file — tasks modifying it cannot truly run in parallel. [P] markers on defines.py tasks mean "parallel with OTHER file tasks", not with each other.
- Edge transition thresholds (16) are a separate centralization effort from the 12 non-edge Tier C constants — budget accordingly
