# Tasks: Bifurcation Topology Analysis

**Input**: Design documents from `/specs/033-bifurcation-topology/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/analysis.md, quickstart.md
**Branch**: `033-bifurcation-topology`

**Tests**: Included per project TDD mandate (Red-Green-Refactor). Write tests FIRST, verify they FAIL, then implement.

**Organization**: Tasks grouped by user story. Each story is independently testable after Phase 2 (foundational) is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Create package structure and register new enum/event types in existing models

- [ ] T001 Create `src/babylon/bifurcation/` package with `__init__.py` (empty, exports added in Polish phase)
- [ ] T002 [P] Add `BIFURCATION_TENDENCY_CHANGE` value to `EventType` enum in `src/babylon/models/enums.py`
- [ ] T003 [P] Add `BifurcationTendencyEvent` model to `src/babylon/models/events.py` (inherits TopologyEvent, fields: previous_tendency, new_tendency, consciousness_weighted_cross_solidarity, mean_collective_identity_marginalized, bridge_potential_weighted, legitimation_index)
- [ ] T004 Update `EventType` count assertion in `tests/unit/topology/test_phase_transition.py` to account for new enum value

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types, configuration, store protocol, and test fixtures that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Add `BifurcationDefines` frozen Pydantic model to `src/babylon/config/defines.py` (12 fields: consciousness_sigmoid_midpoint=0.4, consciousness_sigmoid_steepness=10.0, consciousness_filter_threshold=0.2, indeterminate_dead_zone=0.2, axis_tendency_epsilon=0.001, legitimation_amplifier_scale=2.0, wage_ceiling_high_ratio=10.0, wage_ceiling_low_ratio=2.0, wage_ceiling_min=0.3, wage_ceiling_max=0.9, shared_exploitation_bonus=0.2, purge_removal_rate=0.2) and add `bifurcation: BifurcationDefines` field to `GameDefines`
- [ ] T006 [P] Create Pydantic result types in `src/babylon/bifurcation/types.py`: BifurcationResult (20 fields, frozen), BifurcationSnapshot (tick + result), AxisTendency (7 fields), BridgeInfo (7 fields), SolidarityCeiling (6 fields) per data-model.md
- [ ] T007 [P] Create `CommunityStateStore` protocol and `InMemoryCommunityStateStore` in `src/babylon/engine/community_state_store.py` per research.md R1
- [ ] T008 Create shared test fixtures in `tests/unit/bifurcation/conftest.py`: graph builders (star, mesh, disconnected), hypergraph builders (with community memberships spanning axes), community states at varying CI levels (0.1, 0.4, 0.7, 0.8), BifurcationDefines fixture, agent_memberships helper

**Checkpoint**: Foundation ready — user story implementation can begin

______________________________________________________________________

## Phase 3: User Story 1 — Consciousness-Weighted Solidarity (Priority: P1)

**Goal**: Weight solidarity edges by nonlinear sigmoid of community collective_identity. Assimilated solidarity (low CI) produces near-zero weight; oppositional consciousness (high CI) produces near-full weight.

**Independent Test**: Construct SOLIDARITY edges between agents at varying CI levels. Verify weighted values reflect consciousness quality, not just edge count.

### Tests (RED phase)

- [ ] T009 [US1] Write tests in `tests/unit/bifurcation/test_consciousness.py`: consciousness_sigmoid boundary values (CI=0.0→~0, CI=0.5→~0.73, CI=1.0→~1.0), breakage cliff (CI=0.1→<0.05, CI=0.8→>0.98), configurable midpoint/steepness, overflow clamp safety, consciousness_weighted_solidarity for high-CI edge vs low-CI edge vs no-marginalized-communities case vs multi-community agent (mean CI)

### Implementation (GREEN phase)

- [ ] T010 [US1] Implement `consciousness_sigmoid()` in `src/babylon/bifurcation/consciousness.py` per contracts/analysis.md (logistic sigmoid with midpoint, steepness, overflow clamp ±500)
- [ ] T011 [US1] Implement `consciousness_weighted_solidarity()` in `src/babylon/bifurcation/consciousness.py` per contracts/analysis.md (edge resilience * sigmoid(min(source_ci, target_ci)))

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_consciousness.py -v` — all GREEN

______________________________________________________________________

## Phase 4: User Story 2 — Per-Axis Contradiction Analysis (Priority: P2)

**Goal**: Compute solidarity vs antagonism balance along each contradiction axis independently. Cross-line solidarity weighted by consciousness; lateral/upward antagonism classified by EdgeType+EdgeMode.

**Independent Test**: Construct graphs with varying solidarity/antagonism balances per axis. Verify tendency ratios are >1.0 (solidarity-dominant) or <1.0 (antagonism-dominant) correctly.

**Depends on**: US1 (consciousness_weighted_solidarity used in axis tendency computation)

### Tests (RED phase)

- [ ] T012 [US2] Write tests in `tests/unit/bifurcation/test_axis.py`: crosses_contradiction_axis (hegemonic↔marginalized=True, same-side=False, neither-on-axis=False), classify_edge_antagonism (lateral/upward/downward/none for EXPLOITATION, REPRESSION, COMPETITION, ANTAGONISTIC-mode edges), compute_axis_tendency (solidarity-dominant axis→ratio>1.0, antagonism-dominant→ratio<1.0, mixed with both axes, empty-axis edge case)

### Implementation (GREEN phase)

- [ ] T013 [P] [US2] Implement `crosses_contradiction_axis()` in `src/babylon/bifurcation/axis.py` per contracts/analysis.md
- [ ] T014 [P] [US2] Implement `classify_edge_antagonism()` in `src/babylon/bifurcation/axis.py` per contracts/analysis.md (EXPLOITATION/REPRESSION/COMPETITION EdgeTypes + ANTAGONISTIC EdgeMode)
- [ ] T015 [US2] Implement `compute_axis_tendency()` in `src/babylon/bifurcation/axis.py` per contracts/analysis.md (depends on T013, T014, and US1 consciousness weighting)

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_axis.py -v` — all GREEN

______________________________________________________________________

## Phase 5: User Story 3 — Community Bridge Detection (Priority: P3)

**Goal**: Detect institutional exclusion communities spanning contradiction axes. Weight bridge potential by infrastructure * sigmoid(CI). Lifecycle communities excluded.

**Independent Test**: Construct hypergraph with DISABLED/INCARCERATED communities spanning axes at varying CI. Verify bridge potential activates above consciousness threshold and lifecycle communities are excluded.

**Depends on**: US1 (consciousness_sigmoid used for bridge weighting)

### Tests (RED phase)

- [ ] T016 [US3] Write tests in `tests/unit/bifurcation/test_bridges.py`: DISABLED with high CI→active bridge, DISABLED with low CI→near-zero potential, INCARCERATED spanning multiple axes→multi-axis bridge, lifecycle community (YOUTH)→excluded, community with zero members on one side→not a bridge, bridge weighted_potential = infrastructure * sigmoid(CI)

### Implementation (GREEN phase)

- [ ] T017 [US3] Implement `detect_bridges()` in `src/babylon/bifurcation/bridges.py` per contracts/analysis.md (filter to INSTITUTIONAL_EXCLUSION, verify members on both sides, compute sigmoid-weighted potential)

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_bridges.py -v` — all GREEN

______________________________________________________________________

## Phase 6: User Story 4 — Topological Resilience Metrics (Priority: P4)

**Goal**: Compute Betti numbers, equivalence classes, critical singletons/cutsets, and targeted purge resilience on solidarity subgraphs. Two-pass: raw (all SOLIDARITY) + consciousness-filtered.

**Independent Test**: Construct known topologies (star, mesh, ring, disconnected). Verify Betti numbers and resilience scores match graph-theoretic expectations.

**No dependencies on US1-US3** (operates on plain nx.Graph subgraphs)

### Tests (RED phase)

- [ ] T018 [US4] Write tests in `tests/unit/bifurcation/test_resilience.py`: compute_betti_numbers (star→β₀=1,β₁=0; mesh K₅→β₀=1,β₁=6; ring→β₀=1,β₁=1; disconnected 3 components→β₀=3; empty graph→β₀=0,β₁=0), compute_equivalence_classes (mesh→all same class; star→hub singleton + leaf class), find_critical_singletons (star hub=articulation point; mesh=none), find_critical_cutsets (bridge edge=size-1 cutset), compute_purge_resilience (star→low; mesh→high)

### Implementation (GREEN phase)

- [ ] T019 [P] [US4] Implement `compute_betti_numbers()` in `src/babylon/bifurcation/resilience.py` per contracts/analysis.md (β₀=connected_components, β₁=|E|-|V|+β₀)
- [ ] T020 [P] [US4] Implement `compute_equivalence_classes()` in `src/babylon/bifurcation/resilience.py` per contracts/analysis.md (group by frozenset of neighbors)
- [ ] T021 [P] [US4] Implement `find_critical_singletons()` in `src/babylon/bifurcation/resilience.py` per contracts/analysis.md (nx.articulation_points wrapper)
- [ ] T022 [P] [US4] Implement `find_critical_cutsets()` in `src/babylon/bifurcation/resilience.py` per contracts/analysis.md (nx.minimum_edge_cut per component, bounded by max_cutset_size)
- [ ] T023 [US4] Implement `compute_purge_resilience()` in `src/babylon/bifurcation/resilience.py` per contracts/analysis.md (remove top-degree nodes at removal_rate, compare post-purge L_max to pre-purge L_max)

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_resilience.py -v` — all GREEN

______________________________________________________________________

## Phase 7: User Story 6 — Material Solidarity Ceiling (Priority: P6)

**Goal**: Compute material constraints on solidarity formation: wage gap ratio interpolation, exploitation bonus, community bonus, geographic proximity check.

**Independent Test**: Compute ceilings for agent pairs with known wage gaps, shared exploitation sources, and community memberships.

**No dependencies on US1-US5** (standalone utility, not used by bifurcation_tendency orchestrator)

### Tests (RED phase)

- [ ] T024 [US6] Write tests in `tests/unit/bifurcation/test_ceiling.py`: wage_gap>10→ceiling≤0.3, wage_gap<2→ceiling≤0.9, wage_gap=5→interpolated, shared_exploitation_source→+0.2 bonus, shared_community→community_bonus>0, effective_ceiling clamped to [0,1], boundary values (exactly 2.0 and 10.0 ratios)

### Implementation (GREEN phase)

- [ ] T025 [US6] Implement `compute_solidarity_ceiling()` in `src/babylon/bifurcation/ceiling.py` per contracts/analysis.md (wage gap interpolation between thresholds, bonuses, clamp to [0,1])

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_ceiling.py -v` — all GREEN

______________________________________________________________________

## Phase 8: User Story 7 — Legitimation Crisis Amplifier (Priority: P7)

**Goal**: Aggregate DPD legitimation indices from territory nodes into a crisis amplifier. Low legitimation → amplifier > 1.0, intensifying bifurcation.

**Independent Test**: Set territory legitimation_index attributes at known values. Verify population-weighted aggregation and amplifier computation.

**No dependencies on US1-US6** (reads territory node attributes directly)

### Tests (RED phase)

- [ ] T026 [US7] Write tests in `tests/unit/bifurcation/test_legitimation.py`: high legitimation (0.8)→amplifier≈1.0, low legitimation (0.2)→amplifier>1.0 (up to legitimation_amplifier_scale), population-weighted mean across territories, no territories→amplifier=1.0 (graceful degradation), legitimation=0→amplifier=legitimation_amplifier_scale

### Implementation (GREEN phase)

- [ ] T027 [US7] Implement `compute_legitimation_amplifier()` in `src/babylon/bifurcation/legitimation.py` per contracts/analysis.md (read legitimation_index from territory nodes, population-weighted mean, invert to amplifier with configurable scale)

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_legitimation.py -v` — all GREEN

______________________________________________________________________

## Phase 9: User Story 5 — Full Bifurcation Computation (Priority: P5)

**Goal**: Orchestrate all analysis functions into a unified `bifurcation_tendency()` that produces BifurcationResult with weakest-link classification. The critical validation: the assimilation trap MUST classify as "fascist".

**Independent Test**: Construct complete scenarios (graph + hypergraph + consciousness) covering all validation criteria from spec.md.

**Depends on**: US1 (consciousness), US2 (axis), US3 (bridges), US4 (resilience), US7 (legitimation)

### Tests (RED phase)

- [ ] T028 [US5] Write tests in `tests/unit/bifurcation/test_analysis.py`: within-group-only solidarity→"fascist", cross-line + high CI (≥0.7) + mesh topology→"revolutionary", **assimilation trap** (high cross-line density + CI≤0.2)→"fascist" (raw_beta_1>0, filtered_beta_1=0), colonial solidarity-dominant + patriarchal antagonism-dominant→per-axis split + overall not "revolutionary", low legitimation amplifies crisis, degenerate cases (no edges→"fascist", no marginalized communities→"indeterminate", empty hypergraph→unweighted fallback)

### Implementation (GREEN phase)

- [ ] T029 [US5] Implement helper to extract solidarity subgraph (raw + consciousness-filtered) in `src/babylon/bifurcation/analysis.py`
- [ ] T030 [US5] Implement helper to collect agent memberships from graph node attributes in `src/babylon/bifurcation/analysis.py`
- [ ] T031 [US5] Implement `bifurcation_tendency()` orchestrator in `src/babylon/bifurcation/analysis.py` per contracts/analysis.md — combines per-axis tendency (weakest-link), bridge potential, legitimation amplifier, two-pass topology (raw + filtered Betti), classification logic (revolutionary/fascist/indeterminate), including FR-014 degenerate case handling (no SOLIDARITY edges→"fascist", no marginalized communities→"indeterminate", empty hypergraph→unweighted fallback with warning)

**Checkpoint**: `poetry run pytest tests/unit/bifurcation/test_analysis.py -v` — all GREEN, including the assimilation trap

______________________________________________________________________

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Engine integration, package exports, and integration testing

- [ ] T032 Implement `BifurcationMonitor` in `src/babylon/engine/bifurcation_monitor.py` — extends TopologyMonitor, overrides `_record_snapshot()` to call `super()` then `_record_bifurcation()`, accepts `CommunityStateStore` via DI, rebuilds XGI hypergraph per tick using `build_community_hypergraph()`, stores BifurcationSnapshot history, emits BifurcationTendencyEvent on tendency change
- [ ] T033 Write integration test in `tests/integration/topology/test_bifurcation_integration.py` — register BifurcationMonitor with InMemoryCommunityStateStore, run multi-tick simulation, verify bifurcation_history populated, verify tendency change events emitted, verify TopologyMonitor base functionality preserved
- [ ] T034 [P] Populate `src/babylon/bifurcation/__init__.py` with public API exports per plan.md (bifurcation_tendency, consciousness_weighted_solidarity, compute_betti_numbers, detect_bridges, compute_solidarity_ceiling, compute_legitimation_amplifier, all types)
- [ ] T035 Run full test suite `poetry run pytest tests/unit/bifurcation/ tests/integration/topology/test_bifurcation_integration.py -v` and fix any failures
- [ ] T036 Run `poetry run mypy src/babylon/bifurcation/ src/babylon/engine/bifurcation_monitor.py src/babylon/engine/community_state_store.py --strict` and fix type errors
- [ ] T037 [P] Benchmark `bifurcation_tendency()` performance per SC-007 — construct a representative graph (50+ nodes, 100+ edges), time the full analysis, verify <10% overhead vs baseline tick duration (use `time.perf_counter` or `pytest-benchmark`)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (needs EventType enum for types) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no other story dependencies
- **US2 (Phase 4)**: Depends on Phase 2 + US1 (uses consciousness_weighted_solidarity)
- **US3 (Phase 5)**: Depends on Phase 2 + US1 (uses consciousness_sigmoid)
- **US4 (Phase 6)**: Depends on Phase 2 only — independent of US1-US3
- **US6 (Phase 7)**: Depends on Phase 2 only — independent of all other stories
- **US7 (Phase 8)**: Depends on Phase 2 only — independent of all other stories
- **US5 (Phase 9)**: Depends on US1 + US2 + US3 + US4 + US7 — the capstone integration
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependency Graph

```text
Phase 2 (Foundational)
    │
    ├──► US1 (Consciousness) ──┬──► US2 (Axis) ──────┐
    │                          └──► US3 (Bridges) ────┤
    ├──► US4 (Resilience) ────────────────────────────┤
    ├──► US6 (Ceiling) — standalone, no downstream    │
    └──► US7 (Legitimation) ──────────────────────────┤
                                                      ▼
                                               US5 (Full Bifurcation)
                                                      │
                                                      ▼
                                               Phase 10 (Polish)
```

### Parallel Opportunities

After Phase 2 completes:

- **Wave 1**: US1 + US4 + US6 + US7 (all independent, 4 parallel tracks)
- **Wave 2**: US2 + US3 (both depend on US1 only, can run in parallel with each other)
- **Wave 3**: US5 (depends on US1-US4 + US7)
- **Wave 4**: Phase 10 (integration)

______________________________________________________________________

## Parallel Example: Wave 1 (after Phase 2)

```bash
# Launch 4 independent user stories simultaneously:
Task: "US1 — tests + impl in src/babylon/bifurcation/consciousness.py"
Task: "US4 — tests + impl in src/babylon/bifurcation/resilience.py"
Task: "US6 — tests + impl in src/babylon/bifurcation/ceiling.py"
Task: "US7 — tests + impl in src/babylon/bifurcation/legitimation.py"
```

## Parallel Example: Wave 2 (after US1)

```bash
# Launch 2 dependent stories simultaneously:
Task: "US2 — tests + impl in src/babylon/bifurcation/axis.py"
Task: "US3 — tests + impl in src/babylon/bifurcation/bridges.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 — Consciousness-Weighted Solidarity
4. **STOP and VALIDATE**: `poetry run pytest tests/unit/bifurcation/test_consciousness.py -v`
5. Consciousness weighting works independently — core innovation proven

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Consciousness weighting proven (MVP)
3. US4 + US6 + US7 → Resilience, ceiling, legitimation (parallel, independent)
4. US2 + US3 → Axis analysis + bridges (depend on US1)
5. US5 → Full bifurcation with assimilation trap validation (capstone)
6. Polish → BifurcationMonitor integration, exports, full test suite

### Parallel Agent Strategy

With multiple agents:

1. All agents complete Setup + Foundational together
2. Once Foundational is done:
   - Agent A: US1 (consciousness) → US2 (axis)
   - Agent B: US4 (resilience) → US3 (bridges, after US1 done)
   - Agent C: US6 (ceiling) + US7 (legitimation)
3. After Waves 1+2: Agent A takes US5 (capstone)
4. Agent B: Phase 10 (integration + polish)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD mandatory: write tests (RED), verify they FAIL, then implement (GREEN)
- Commit after each task or logical group (per CLAUDE.md)
- US5 assimilation trap test (T028) is the critical validation — if this fails, the feature is incorrect
- US6 (ceiling) has no downstream dependencies — it can be deferred without blocking anything
- Stop at any checkpoint to validate story independently
