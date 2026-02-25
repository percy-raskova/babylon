# Tasks: Dialectical Field Topology

**Input**: Design documents from `/specs/002-dialectical-field-topology/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per project TDD mandate (CLAUDE.md). Red-Green-Refactor cycle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/babylon/` at repository root
- **Tests**: `tests/unit/`, `tests/integration/` at repository root
- **Contracts**: `specs/002-dialectical-field-topology/contracts/` for reference

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new enum, dependency, and configuration before any system work

- [ ] T001 Add `EdgeMode` enum with 5 values (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO_OPTIVE) to `src/babylon/models/enums.py`
- [ ] T002 Add scipy to project dependencies via `pyproject.toml` (for Ollivier-Ricci curvature LP solver)
- [ ] T003 [P] Add `ContradictionFieldDefines` frozen Pydantic model to `src/babylon/config/defines.py` with field normalization bounds (exploitation: [0, 5], immiseration: [0, 3], imperial_rent: [0, 2], displacement: [-0.1, 0.1]) and transition thresholds
- [ ] T004 [P] Add new `EventType` values to `src/babylon/models/enums.py` for edge mode transitions: EDGE_MODE_TRANSITION, PRINCIPAL_CONTRADICTION_SHIFT, CO_OPTIVE_BREAKDOWN, LATENT_CONTRADICTION_RELEASE, ASPECT_REVERSAL. Add `ContradictionCharacter` enum with values ANTAGONISTIC, NON_ANTAGONISTIC to `src/babylon/models/enums.py`.

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the field registry and register it with ServiceContainer. All user stories depend on this.

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create `FieldRegistryProtocol` and `DefaultFieldRegistry` in `src/babylon/engine/field_registry.py` per contract `contracts/field_registry.py`. Registry maps field names to `(computation_fn, normalization_fn)` tuples. Must be field-name-agnostic.
- [ ] T006 Register 4 initial fields in `DefaultFieldRegistry`: exploitation (from `exploitation_rate` node attr, normalize via [0, 5] → [0, 10]), immiseration (from wage decline rate), imperial_rent (from `imperial_rent_share` differential to graph mean), displacement (from population change rate). Each field needs a computation callable and a normalization callable.
- [ ] T007 [P] Write unit tests for field registry in `tests/unit/engine/test_field_registry.py`: test registration, duplicate name rejection, field-name-agnostic iteration, compute/normalize round-trip for all 4 fields, extensibility (register 5th field without touching core code)
- [ ] T008 Add `field_registry` to `ServiceContainer` in `src/babylon/engine/services.py` as an optional dependency. Systems access it via `services.field_registry`.

**Checkpoint**: Field registry functional with 4 fields. All user stories can now begin.

______________________________________________________________________

## Phase 3: User Story 1 — Contradiction Field Computation (Priority: P1) MVP

**Goal**: Every social-class node carries named contradiction fields computed each tick from existing economic outputs.

**Independent Test**: Run a 10-tick simulation and verify every social-class node has defined values for all 4 fields at every tick after tick 0.

### Tests for User Story 1

> **Write these FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Write unit tests for ContradictionFieldSystem in `tests/unit/engine/test_contradiction_field_system.py`: test field computation for all 4 fields using known node attributes, test normalization clamping (EC-007: values outside [0, 10] are clamped with log), test history rolling window (3 ticks max), test no economic calculation duplication (system reads but does not recompute exploitation rate)
- [ ] T010 [P] [US1] Write test for history persistence in `tests/unit/engine/test_contradiction_field_system.py`: verify `persistent_data["contradiction_history"]` stores rolling window of 3 values per node per field, verify oldest entry evicted when window exceeds 3

### Implementation for User Story 1

- [ ] T011 [US1] Create `ContradictionFieldSystem` class in `src/babylon/engine/systems/contradiction_field.py` per contract. Implement `step()`: auto-wrap guard, iterate social-class nodes via `graph.query_nodes(node_type="social_class")`, compute each registered field from node attributes, normalize, clamp (EC-007), write `contradiction_fields` dict to node via `graph.update_node()`, update history in `persistent_data["contradiction_history"]` with rolling window of 3.
- [ ] T012 [US1] Make tests from T009 and T010 pass. Iterate until all green.
- [ ] T013 [US1] Add `ContradictionFieldSystem` export to `src/babylon/engine/systems/__init__.py`

**Checkpoint**: US1 complete. Contradiction fields computed per tick. History persisted. Proceed to US2.

______________________________________________________________________

## Phase 4: User Story 2 — Spatial and Temporal Derivatives (Priority: P1)

**Goal**: Spatial derivatives (gradient along edges, Laplacian at nodes) and temporal derivatives (df/dt, d2f/dt2) computed each tick.

**Independent Test**: Set up a graph with known field values, verify gradients, Laplacian, and temporal finite differences match analytically expected results.

**Depends on**: US1 (needs contradiction_fields on nodes and history in persistent_data)

### Tests for User Story 2

> **Write these FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US2] Write unit tests for spatial derivatives in `tests/unit/engine/test_field_derivative_system.py`: test gradient computation (f(j) - f(i)) for a 3-node triangle graph with known field values, test Laplacian at high-value node (should be negative — pressure peak), test Laplacian at low-value node (positive or zero), test isolated node Laplacian = 0.0 with warning (EC-002)
- [ ] T015 [P] [US2] Write unit tests for temporal derivatives in `tests/unit/engine/test_field_derivative_system.py`: test df/dt with known linear growth over 3 ticks (error < 1e-6), test d2f/dt2 with known quadratic growth, test df/dt is None at tick 0 (EC-001), test d2f/dt2 is None at ticks 0 and 1 (EC-001)

### Implementation for User Story 2

- [ ] T016 [US2] Create `FieldDerivativeSystem` class in `src/babylon/engine/systems/field_derivative.py` per contract. Implement `step()`: auto-wrap guard, for each registered field — compute edge gradients via `graph.query_edges()` and write `field_gradients` to edges, compute node Laplacian from neighbor field values (handle isolated nodes per EC-002), compute df/dt and d2f/dt2 from `persistent_data["contradiction_history"]` (return None when insufficient history per EC-001), write `field_derivatives` dict to nodes.
- [ ] T017 [US2] Make tests from T014 and T015 pass. Iterate until all green.
- [ ] T018 [US2] Add `FieldDerivativeSystem` export to `src/babylon/engine/systems/__init__.py`

**Checkpoint**: US2 complete. Spatial and temporal derivatives computed per tick. Edge cases handled.

______________________________________________________________________

## Phase 5: User Story 3 — Principal Contradiction Identification (Priority: P2)

**Goal**: Identify the principal contradiction (field with largest max |df/dt| across all nodes) at each tick.

**Independent Test**: Configure a scenario where one field dominates df/dt, then switch dominance, and verify correct identification and event emission.

**Depends on**: US2 (needs df/dt values)

### Tests for User Story 3

- [ ] T019 [P] [US3] Write unit tests for principal contradiction in `tests/unit/engine/test_field_derivative_system.py`: test correct identification when exploitation has largest |df/dt|, test switch detection (changed=True) when principal changes between ticks, test tie-breaking by total magnitude (EC-004), test tie-breaking by exploitation preference when magnitudes also tied (EC-004), test principal_contradiction is None or skipped when no df/dt available (tick 0)

### Implementation for User Story 3

- [ ] T020 [US3] Add principal contradiction identification logic to `FieldDerivativeSystem.step()` in `src/babylon/engine/systems/field_derivative.py`: after computing all derivatives, find field with max |df/dt| across all nodes, apply tie-breaking (total magnitude, then exploitation preferred), write `principal_contradiction` dict to graph attr via `graph.set_graph_attr()`, detect change from previous tick via `persistent_data`, emit PRINCIPAL_CONTRADICTION_SHIFT event via `services.event_bus` when principal changes
- [ ] T021 [US3] Make tests from T019 pass. Iterate until all green.

**Checkpoint**: US3 complete. Principal contradiction identified per tick with change detection.

______________________________________________________________________

## Phase 6: User Story 4 — Compound State Transition Predicates (Priority: P2)

**Goal**: Specify discrete state transitions as declarative compound predicates over field values and derivatives. Define edge mode transition state machine.

**Independent Test**: Define a compound predicate (f > 0.7 AND df/dt > 0 AND Lf < 0), register it for EXTRACTIVE → ANTAGONISTIC, verify it fires only when all conjuncts are satisfied.

**Depends on**: US2 (predicates reference field values and derivatives)

### Tests for User Story 4

- [ ] T022 [P] [US4] Write unit tests for compound predicate evaluation in `tests/unit/engine/test_edge_transition_system.py`: test predicate with all conjuncts met → True, test predicate with one conjunct unmet → False, test predicate referencing d2f/dt2 at tick 1 (insufficient history) → False (EC-001), test predicate referencing edge_mode → correct comparison
- [ ] T023 [P] [US4] Write unit tests for transition state machine in `tests/unit/engine/test_edge_transition_system.py`: test each permissible transition from FR-010 (17 transitions including ANTAGONISTIC → SOLIDARISTIC from I.15), test prohibited transition (EXTRACTIVE → SOLIDARISTIC) raises error, test multiple eligible transitions resolved by priority (EC-003), test self-transition ANTAGONISTIC → ANTAGONISTIC (conflict persists)

### Implementation for User Story 4

- [ ] T024 [US4] Create `CompoundPredicate`, `PredicateCondition`, and `EdgeModeTransition` frozen Pydantic models in `src/babylon/engine/systems/edge_transition.py`. `PredicateCondition` has fields: field (str), metric (str: "value"|"df_dt"|"d2f_dt2"|"laplacian"|"curvature"|"edge_mode"), operator (str), threshold (float|str), scope (str: "source"|"target"|"edge"). `CompoundPredicate` has conditions list. `EdgeModeTransition` has from_mode, to_mode, predicate, priority, description.
- [ ] T025 [US4] Implement predicate evaluation function in `src/babylon/engine/systems/edge_transition.py`: given a `CompoundPredicate`, source node attrs, target node attrs, and edge attrs, evaluate all conjuncts. Return False if any conjunct references undefined derivative. Return True only when ALL conjuncts True.
- [ ] T026 [US4] Define the 17 permissible transitions from FR-010 as a list of `EdgeModeTransition` objects in `src/babylon/engine/systems/edge_transition.py`. Include ANTAGONISTIC → SOLIDARISTIC (constitution I.15: shared enemy produces alliance). Include default compound predicates for each transition based on the conditions described in FR-010 (thresholds from GameDefines).
- [ ] T027 [US4] Create `EdgeTransitionSystem` class in `src/babylon/engine/systems/edge_transition.py` per contract. Implement `step()`: auto-wrap guard, iterate all edges with `edge_mode` attribute, for each edge collect eligible transitions from current mode, evaluate predicates, select highest-priority firing transition (EC-003), apply transition via `graph.update_edge()`, emit EDGE_MODE_TRANSITION event.
- [ ] T028 [US4] Make tests from T022 and T023 pass. Iterate until all green.
- [ ] T029 [US4] Add `EdgeTransitionSystem` export to `src/babylon/engine/systems/__init__.py`
- [ ] T029b [P] [US4] Write unit tests for contradiction character flag (FR-018) in `tests/unit/engine/test_edge_transition_system.py`: test that edges carry `contradiction_character` attribute (ANTAGONISTIC or NON_ANTAGONISTIC), test compound predicate can reference character flag, test that character flag is independent of edge mode (TRANSACTIONAL edge can be ANTAGONISTIC character)
- [ ] T029c [P] [US4] Write unit tests for aspect reversal event (FR-019) in `tests/unit/engine/test_edge_transition_system.py`: test that when dominant side of contradiction switches, ASPECT_REVERSAL event is emitted with edge identifier and new dominant party
- [ ] T029d [US4] Implement contradiction character flag on edges in `EdgeTransitionSystem`: ensure all edges with `edge_mode` also carry `contradiction_character` (default NON_ANTAGONISTIC), make character flag available to compound predicate evaluation. Implement aspect reversal detection and ASPECT_REVERSAL event emission when dominant party switches on a directed edge.

**Checkpoint**: US4 complete. Edge mode transitions fire based on declarative compound predicates.

______________________________________________________________________

## Phase 7: User Story 8 — CO-OPTIVE Edge Mode and George Jackson Bifurcation (Priority: P2)

**Goal**: CO-OPTIVE edges suppress df/dt at co-opted nodes, accumulate latent contradiction, and release it on breakdown with bifurcation direction determined by solidarity topology.

**Independent Test**: Configure CO-OPTIVE edges, verify df/dt suppression during stable co-optation, trigger breakdown, verify latent contradiction spike and correct bifurcation direction.

**Depends on**: US1 (field values), US2 (derivatives), US4 (transition system)

### Tests for User Story 8

- [ ] T030 [P] [US8] Write unit tests for CO-OPTIVE suppression in `tests/unit/engine/test_edge_transition_system.py`: test df/dt suppressed proportional to concession magnitude at co-opted node (FR-014), test per-edge field suppression declaration (imperial rent edge suppresses exploitation + immiseration, welfare edge suppresses immiseration only), test principal contradiction correctly avoids suppressed field during stable co-optation (FR-016)
- [ ] T031 [P] [US8] Write unit tests for latent contradiction in `tests/unit/engine/test_edge_transition_system.py`: test latent accumulation in `persistent_data["latent_contradictions"]`, test release as df/dt spike when CO-OPTIVE transitions away (EC-008), test multiple CO-OPTIVE edges at one node with independent suppression/release (EC-009), test CO-OPTIVE edge with zero material flow must transition (EC-010)
- [ ] T032 [P] [US8] Write unit tests for George Jackson bifurcation direction in `tests/unit/engine/test_edge_transition_system.py`: test upward (revolutionary) when cross-divide solidarity > within-group (SC-011), test lateral (fascist) when within-group > cross-divide (SC-011), test appropriate event emission (REVOLUTIONARY_OFFENSIVE or FASCIST_REVANCHISM)

### Implementation for User Story 8

- [ ] T033 [US8] Add CO-OPTIVE suppression phase to `EdgeTransitionSystem.step()` in `src/babylon/engine/systems/edge_transition.py`: before predicate evaluation, iterate CO-OPTIVE edges, read `co_optive_suppressed_fields` from edge attrs, suppress df/dt at co-opted node proportional to `concession_magnitude` edge attr, accumulate suppressed amount in `persistent_data["latent_contradictions"]` keyed by (node_id, field_name, edge_key), validate material flow > 0 (EC-010: trigger transition if zero)
- [ ] T034 [US8] Add latent contradiction release to `EdgeTransitionSystem.step()`: when a CO-OPTIVE edge transitions away, read accumulated latent for that edge from `persistent_data["latent_contradictions"]`, add as spike to the node's df/dt for affected fields (registered as named mechanism "co_optive_release" in continuity accounting), handle multiple CO-OPTIVE edges at one node (EC-009: only release portion attributable to broken edge)
- [ ] T035 [US8] Add George Jackson bifurcation direction logic to `EdgeTransitionSystem.step()`: on CO-OPTIVE → ANTAGONISTIC transition, compute cross-divide solidarity strength (sum of solidarity_strength on edges crossing the colonial divide at co-opted node) vs within-group solidarity strength, direct antagonism upward if cross-divide > within-group (emit REVOLUTIONARY_OFFENSIVE), lateral if within-group > cross-divide (emit FASCIST_REVANCHISM)
- [ ] T036 [US8] Make tests from T030, T031, T032 pass. Iterate until all green.

**Checkpoint**: US8 complete. CO-OPTIVE mechanics functional with suppression, latent contradiction, and bifurcation.

______________________________________________________________________

## Phase 8: User Story 5 — Continuity Accounting (Priority: P3)

**Goal**: Per-tick continuity residual for each contradiction field at each node: change minus gradient-implied flow.

**Independent Test**: Run a closed system and verify total contradiction conserved. Run open scenario and verify residuals flagged with named mechanisms.

**Depends on**: US2 (needs gradients and field changes)

### Tests for User Story 5

- [ ] T037 [P] [US5] Write unit tests for continuity residuals in `tests/unit/engine/test_field_derivative_system.py`: test closed system conservation (total contradiction constant within tolerance), test non-zero residual flagged with diagnostic, test named mechanism accounting (e.g., "wage_increase" zeroes residual), test CO-OPTIVE suppression shows up as named mechanism "co_optive_suppression"

### Implementation for User Story 5

- [ ] T038 [US5] Add continuity residual computation to `FieldDerivativeSystem.step()` in `src/babylon/engine/systems/field_derivative.py`: for each node and field, compute delta_f (current - previous), compute net_flow (sum of gradients along adjacent edges), compute residual = delta_f - net_flow, look up named mechanism from a mechanism registry (e.g., "wage_increase", "co_optive_suppression"), write `continuity_residuals` dict to node via `graph.update_node()`
- [ ] T039 [US5] Make tests from T037 pass. Iterate until all green.

**Checkpoint**: US5 complete. Continuity accounting provides diagnostic residuals per node per field.

______________________________________________________________________

## Phase 9: User Story 6 — Ollivier-Ricci Curvature as Structural Context (Priority: P3)

**Goal**: Ollivier-Ricci curvature computed for each edge as a structural property, cached between topology changes.

**Independent Test**: Compute curvature on a known graph, verify values. Verify cache is used when topology unchanged.

**Depends on**: None (curvature is a graph property), but integrates with US2 (stored on edges for derivative system)

### Tests for User Story 6

- [ ] T040 [P] [US6] Write unit tests for Ollivier-Ricci curvature formula in `tests/unit/formulas/test_curvature.py`: test curvature on a complete graph (K4: expected positive curvature), test curvature on a path graph (expected negative curvature at bridge edges), test curvature on star graph (hub edges), test self-loop alpha=0.5 parameter, test degree-1 node handling (EC-006)
- [ ] T041 [P] [US6] Write unit tests for curvature caching in `tests/unit/engine/test_field_derivative_system.py`: test curvature written to edge attrs with tick stamp, test no recomputation when topology unchanged between ticks, test recomputation triggered when node/edge added

### Implementation for User Story 6

- [ ] T042 [US6] Create `compute_ollivier_ricci` function in `src/babylon/formulas/curvature.py`: implement Wasserstein-1 distance between neighborhood probability distributions using `scipy.optimize.linprog()`. Parameters: graph (GraphProtocol), alpha (float, default 0.5). Returns dict mapping edge tuples to curvature floats. Handle degree-1 nodes (EC-006). Algorithm: for each edge (u,v), construct mu_u/mu_v distributions over neighborhoods + self-loop, compute cost matrix (shortest path distances), solve LP for W1 distance, curvature = 1 - W1/d(u,v).
- [ ] T043 [US6] Integrate curvature computation into `FieldDerivativeSystem.step()`: check if topology has changed since last curvature computation (compare node/edge counts or use a topology hash stored in `persistent_data`), if changed call `compute_ollivier_ricci()` and write `ricci_curvature` and `ricci_computed_tick` to all edges via `graph.update_edge()`, if unchanged skip computation.
- [ ] T044 [US6] Update `src/babylon/formulas/__init__.py` to export `compute_ollivier_ricci`
- [ ] T045 [US6] Make tests from T040 and T041 pass. Iterate until all green.

**Checkpoint**: US6 complete. Curvature computed and cached. Available as predicate metric in compound predicates.

______________________________________________________________________

## Phase 10: User Story 7 — Detroit Metro Empirical Validation (Priority: P3)

**Goal**: Compare computed field values and gradients against QCEW-derived quantities for Metro Detroit (2010-2025).

**Independent Test**: Load QCEW data, verify exploitation gradients and temporal derivative patterns match known economic geography.

**Depends on**: US1 (field values), US2 (derivatives)

### Tests for User Story 7

- [ ] T046 [P] [US7] Write integration test for exploitation field geography in `tests/integration/test_field_topology_integration.py`: load Detroit metro graph with QCEW-derived economic attributes, run 10-tick simulation, assert Wayne County exploitation > Oakland County exploitation (SC-001, SC-002), assert exploitation gradient Wayne→Oakland is negative (SC-008)
- [ ] T047 [P] [US7] Write integration test for Laplacian signs in `tests/integration/test_field_topology_integration.py`: assert Laplacian at Wayne County proletariat is negative (pressure peak), assert Laplacian at Oakland County petit bourgeoisie is positive or near-zero (SC-002)
- [ ] T047b [P] [US7] Write integration test for temporal derivative year-range patterns in `tests/integration/test_field_topology_integration.py`: given Wayne County data for 2010-2014 (post-crisis recovery), assert d2f/dt2 is positive (accelerating contradiction); given data for 2018-2022 (gentrification period), assert d2f/dt2 is negative (decelerating contradiction), consistent with gentrification timeline (US7-AS3)

### Implementation for User Story 7

- [ ] T048 [US7] Create test fixture with Detroit metro graph and QCEW-derived economic attributes in `tests/integration/conftest.py`: create nodes for Wayne County proletariat, Oakland County petit bourgeoisie, and at least one connecting edge with realistic exploitation rates, wages, and population values from QCEW data
- [ ] T049 [US7] Make tests from T046, T047, and T047b pass by verifying existing system implementations produce correct results with realistic data. If tests fail, investigate whether field computation or normalization needs calibration and adjust normalization bounds in `ContradictionFieldDefines`.

**Checkpoint**: US7 complete. Detroit empirical validation confirms field framework reproduces known economic geography.

______________________________________________________________________

## Phase 11: System Registration & Integration

**Purpose**: Wire the 3 new systems into the simulation engine execution order and run full integration

- [ ] T050 Register all 3 new systems in `src/babylon/engine/simulation_engine.py`: add imports for ContradictionFieldSystem, FieldDerivativeSystem, EdgeTransitionSystem. Append to `_DEFAULT_SYSTEMS` list at positions 14, 15, 16 (after ContradictionSystem). Update docstring to reflect 16-system order.
- [ ] T051 Write multi-tick integration test in `tests/integration/test_field_topology_integration.py`: run 10-tick simulation with full engine (all 16 systems), verify contradiction fields evolve over ticks, verify derivatives computed from tick 1 onward, verify edge mode transitions fire when conditions met, verify no runtime errors across all systems
- [ ] T052 Make integration test from T051 pass. Debug any system interaction issues.

______________________________________________________________________

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T053 [P] Add type stubs and ensure `mypy --strict` passes for all new files: `src/babylon/engine/field_registry.py`, `src/babylon/engine/systems/contradiction_field.py`, `src/babylon/engine/systems/field_derivative.py`, `src/babylon/engine/systems/edge_transition.py`, `src/babylon/formulas/curvature.py`
- [ ] T054 [P] Run `mise run check` (lint + format + typecheck + test:unit) and fix any issues
- [ ] T055 Run quickstart.md validation: verify all commands in `specs/002-dialectical-field-topology/quickstart.md` work correctly and update if needed
- [ ] T056 Commit final state with conventional commit message

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 for EdgeMode, T003 for defines) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (field registry must exist)
- **US2 (Phase 4)**: Depends on US1 (needs contradiction_fields on nodes)
- **US3 (Phase 5)**: Depends on US2 (needs df/dt values)
- **US4 (Phase 6)**: Depends on US2 (predicates reference derivatives)
- **US8 (Phase 7)**: Depends on US1, US2, US4 (needs fields, derivatives, transition system)
- **US5 (Phase 8)**: Depends on US2 (needs gradients for flow accounting)
- **US6 (Phase 9)**: No story dependencies (graph property), but integrates with US2 and enables curvature predicates in US4
- **US7 (Phase 10)**: Depends on US1, US2 (needs field values and derivatives)
- **Integration (Phase 11)**: Depends on all story phases complete
- **Polish (Phase 12)**: Depends on Integration

### User Story Dependencies

```
Setup → Foundational → US1 (P1) → US2 (P1) → US3 (P2) ─┐
                                      │                    │
                                      ├── US4 (P2) ───────┼── US8 (P2)
                                      │                    │
                                      ├── US5 (P3)        │
                                      │                    │
                                      └── US7 (P3)        │
                                                           │
                         US6 (P3, independent) ────────────┘
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD Red phase)
2. Implementation makes tests pass (TDD Green phase)
3. Refactor if needed (TDD Refactor phase)
4. Commit after story complete

### Parallel Opportunities

**Within Phase 1 (Setup)**:
- T003 and T004 can run in parallel (different sections of different files)

**Within Phase 2 (Foundational)**:
- T007 can run in parallel with T005/T006 (test file vs source file)

**Within each User Story**:
- Test tasks marked [P] can be written in parallel
- After tests written, implementation is sequential

**Across User Stories (after US2 complete)**:
- US3, US4, US5, US6, US7 can all start in parallel (if staffed)
- US8 must wait for US4

______________________________________________________________________

## Parallel Example: User Story 2

```bash
# Launch both test tasks in parallel (different test focuses, same file):
Task: "Write unit tests for spatial derivatives in tests/unit/engine/test_field_derivative_system.py"
Task: "Write unit tests for temporal derivatives in tests/unit/engine/test_field_derivative_system.py"

# Then implement sequentially (single source file):
Task: "Create FieldDerivativeSystem in src/babylon/engine/systems/field_derivative.py"
Task: "Make tests pass"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: US1 — Contradiction Field Computation (T009-T013)
4. **STOP and VALIDATE**: Run `poetry run pytest tests/unit/engine/test_contradiction_field_system.py -v`
5. Commit: `feat(fields): implement contradiction field computation (US1)`

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. US1 → Field values on nodes → Commit (MVP!)
3. US2 → Spatial + temporal derivatives → Commit
4. US3 → Principal contradiction → Commit
5. US4 → Compound predicates + state machine → Commit
6. US8 → CO-OPTIVE mechanics + bifurcation → Commit
7. US5 → Continuity accounting → Commit
8. US6 → Ollivier-Ricci curvature → Commit
9. US7 → Detroit validation → Commit
10. Integration + Polish → Final commit

### Single Developer Strategy

Follow phases sequentially in priority order. Each phase is independently committable. Stop at any checkpoint to validate.

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD mandate: write tests first, verify they fail, then implement
- Commit after each completed user story (CLAUDE.md: commit after each unit of work)
- Auto-wrap guard pattern required in all 3 new systems
- GraphProtocol only — no direct NetworkX access
- Nested dict writes via copy-modify-writeback pattern
