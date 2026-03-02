# Tasks: Ternary Consciousness Model

**Input**: Design documents from `/specs/034-ternary-consciousness/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included per project TDD standards (CLAUDE.md) and plan.md test directives.

**Organization**: Tasks grouped by user story in priority order. US3 (backward compat, P1) precedes US1 (computation, P1) because the model must exist before computation can be built on it.

**Deferred**: US4 (Ternary Visualization, P3) is out of scope per spec boundary section — deferred to dashboard spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US5)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Baseline Verification)

**Purpose**: Verify existing tests pass before any modifications, establishing the regression baseline

- [ ] T001 Run existing community and bifurcation tests as baseline: `poetry run pytest tests/unit/models/test_community_models.py tests/unit/engine/systems/test_community_system.py tests/unit/formulas/test_community_formulas.py tests/unit/bifurcation/ -v`

______________________________________________________________________

## Phase 2: Foundational (Core Models)

**Purpose**: Create TernaryConsciousness, SubstrateFloor, and ProvenanceLevel models that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T002 Write unit tests for TernaryConsciousness model in tests/unit/models/test_ternary_consciousness.py: simplex constraint enforcement (r+l+f=1.0 within 1e-6), rejection of invalid coordinates (negative values, sum != 1.0), frozen model immutability, edge cases (all-revolutionary r=1.0, all-liberal l=1.0, all-fascist f=1.0, equal thirds)
- [ ] T003 [P] Write unit tests for backward-compat computed properties in tests/unit/models/test_ternary_consciousness.py: collective_identity returns r, dominant_tendency returns argmax mapped to ConsciousnessTendency enum, ideological_contestation returns normalized Shannon entropy of (r,l,f), assimilation_ratio returns f/(l+f) with l+f near-zero edge case returning 0.5
- [ ] T004 [P] Write unit tests for SubstrateFloor model in tests/unit/models/test_ternary_consciousness.py: construction with all ProvenanceLevel values, SYNTHETIC provenance logs warning, frozen model immutability, default field values

### Implementation for Foundation

- [ ] T005 Create src/babylon/models/entities/consciousness.py with ProvenanceLevel enum (HIGH, MEDIUM, LOW, SYNTHETIC) following existing enum patterns in src/babylon/models/enums.py
- [ ] T006 Add TernaryConsciousness frozen Pydantic model to src/babylon/models/entities/consciousness.py with Probability fields r, l, f, model_validator enforcing simplex constraint abs(r+l+f-1.0) < 1e-6, and computed properties: collective_identity (returns r), dominant_tendency (argmax to ConsciousnessTendency), ideological_contestation (normalized Shannon entropy), assimilation_ratio (f/(l+f) with near-zero guard)
- [ ] T007 Add SubstrateFloor frozen Pydantic model to src/babylon/models/entities/consciousness.py with fields: community_type (CommunityType), floor_value (Probability, default 0.0), confidence (ProvenanceLevel, default SYNTHETIC), data_sources (list[str], default []), computation_method (str, default ""). Log warning on construction when confidence is SYNTHETIC
- [ ] T008 Export TernaryConsciousness, SubstrateFloor, ProvenanceLevel from src/babylon/models/entities/__init__.py and update src/babylon/models/__init__.py __all__ list
- [ ] T009 Verify all foundational model tests pass: `poetry run pytest tests/unit/models/test_ternary_consciousness.py -v`

**Checkpoint**: TernaryConsciousness, SubstrateFloor, and ProvenanceLevel models exist and pass all tests. User story implementation can now begin.

______________________________________________________________________

## Phase 3: User Story 3 - Backward Compatibility (Priority: P1)

**Goal**: Replace CommunityConsciousness internal representation with TernaryConsciousness while preserving all existing computed fields and downstream consumers. Specs 029, 031, 032, and 033 continue to function without modification.

**Independent Test**: Run all existing community consciousness tests after replacing the internal model. All must pass unchanged.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [US3] Write migration verification tests in tests/unit/models/test_ternary_consciousness.py: for each of 14 CONSCIOUSNESS_DEFAULTS entries, verify r equals old collective_identity, argmax(r,l,f) matches old dominant_tendency, Shannon entropy approximates old ideological_contestation within tolerance, and r+l+f=1.0. Use migration table from data-model.md

### Implementation for User Story 3

- [ ] T011 [US3] Create ternary CONSCIOUSNESS_DEFAULTS dict in src/babylon/models/entities/community.py mapping all 14 CommunityType values to TernaryConsciousness instances using migration table from data-model.md (r=old_CI, l and f split to preserve dominant_tendency argmax and approximate ideological_contestation entropy)
- [ ] T012 [US3] Replace CommunityState.consciousness field type from CommunityConsciousness to TernaryConsciousness in src/babylon/models/entities/community.py. Update the consciousness field default factory to use new ternary defaults. Ensure infiltration_resistance computed field still works (reads consciousness.collective_identity which now returns r)
- [ ] T013 [US3] Update import-time exhaustiveness check in src/babylon/models/entities/community.py (lines 341-343) to validate all 14 CommunityType values have ternary defaults
- [ ] T014 [US3] Update build_community_hypergraph() in src/babylon/engine/systems/community.py (lines 82-84) to bridge TernaryConsciousness attributes to XGI hyperedge attributes (consciousness_ci from r, consciousness_tendency from dominant_tendency, consciousness_contestation from ideological_contestation)
- [ ] T015 [US3] Verify ALL existing tests pass unchanged: `poetry run pytest tests/unit/models/test_community_models.py tests/unit/engine/systems/test_community_system.py tests/unit/formulas/test_community_formulas.py tests/unit/bifurcation/ -v` — zero modifications to existing test files

**Checkpoint**: TernaryConsciousness replaces CommunityConsciousness. All existing consumers work without modification. SC-001 and SC-005 verified.

______________________________________________________________________

## Phase 4: User Story 1 - Compute from Organizational Landscape (Priority: P1)

**Goal**: Compute each community hyperedge's consciousness from the organizations operating within it, weighted by organizational capacity relative to community population. Consciousness becomes a derived quantity with a material referent.

**Independent Test**: Seed a community with known organizations of known tendencies and membership counts. Verify computed ternary coordinates match expected values. Remove all organizations. Verify revert to liberal default plus substrate floor.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [US1] Write tests for compute_ternary_consciousness() in tests/unit/formulas/test_consciousness_computation.py covering all 6 acceptance scenarios: (AS1) community with rev+liberal orgs produces expected r/l/f, (AS2) no-org community returns substrate_floor/liberal default, (AS3) doubling rev org membership increases r proportionally, (AS4) COINTELPRO scenario — destroy all rev orgs, r drops to substrate_floor not zero, (AS5) identical org landscapes with different substrate floors produce r differing by floor differential, (AS6) backward-compat properties derivable from computed coordinates
- [ ] T017 [P] [US1] Write edge case tests in tests/unit/formulas/test_consciousness_computation.py: single-tendency dominance (pinned near vertex), zero-population community returns (0,1,0) with warning, substrate floor exceeding org computation (floor dominates), organizations spanning multiple communities (weighted by per-community membership)

### Implementation for User Story 1

- [ ] T018 [US1] Create compute_ternary_consciousness() pure function in src/babylon/formulas/consciousness.py. Inputs: community_type (CommunityType), org_landscape (list of dicts with tendency, membership_density, cadre_level, cohesion), substrate_floor (float). Algorithm per plan.md Phase 3: sum weighted org contributions per tendency (w_i = membership_density_i * cadre_level_i * cohesion_i), unorganized fraction defaults to liberal, apply substrate floor as r minimum, normalize to simplex. Return TernaryConsciousness
- [ ] T019 [US1] Wire compute_ternary_consciousness() into CommunitySystem.step() in src/babylon/engine/systems/community.py after building hypergraph. For each community hyperedge: query org-community MEMBERSHIP overlaps (reuse pattern from action_costs.py:85-120), build org_landscape list, call computation, update CommunityState with new TernaryConsciousness
- [ ] T020 [US1] Remove direct consciousness mutation in src/babylon/ooda/layer3.py (lines 89-91, 263-264). Replace collective_identity_delta writes with org landscape mutations. EDUCATE/AGITATE/ORGANIZE actions modify membership and edge types; ternary computation reads these changes automatically
- [ ] T021 [US1] Verify computation tests pass and existing system tests still pass: `poetry run pytest tests/unit/formulas/test_consciousness_computation.py tests/unit/engine/systems/test_community_system.py -v`

**Checkpoint**: Consciousness is now a derived quantity computed from organizational landscape each tick. SC-002, SC-003, SC-004, SC-008 verified.

______________________________________________________________________

## Phase 5: User Story 2 - Substrate Floor from Empirical Proxies (Priority: P2)

**Goal**: Derive substrate floor from traceable empirical proxies (Vera incarceration data, Chetty mobility data) rather than stipulating magic constants. Every floor value carries provenance metadata.

**Independent Test**: Compute substrate floor for a community using proxy data. Verify value is reproducible from input data alone. Verify NEW_AFRIKAN floor > SETTLER floor.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [US2] Write tests for SUBSTRATE_FLOOR_DEFAULTS and substrate floor computation in tests/unit/models/test_ternary_consciousness.py: all 14 community types have entries, INCARCERATED and NEW_AFRIKAN have highest floors, SETTLER/PATRIARCHAL/YOUTH/ADULT have floor_value=0.0, all entries have non-SYNTHETIC provenance where proxy data exists, provenance metadata includes named data sources

### Implementation for User Story 2

- [ ] T023 [US2] Create SUBSTRATE_FLOOR_DEFAULTS dict in src/babylon/models/entities/consciousness.py mapping all 14 CommunityType values to SubstrateFloor instances with calibrated floor_value, confidence level, data_sources list, and computation_method per data-model.md ranges. Use Vera incarceration + Chetty mobility as primary proxies for MVP
- [ ] T024 [US2] Wire SUBSTRATE_FLOOR_DEFAULTS into compute_ternary_consciousness() in src/babylon/formulas/consciousness.py so that substrate floor is looked up by community_type and applied as minimum r before simplex normalization
- [ ] T025 [US2] Verify substrate floor tests pass and COINTELPRO scenario confirmed: `poetry run pytest tests/unit/models/test_ternary_consciousness.py tests/unit/formulas/test_consciousness_computation.py -v`

**Checkpoint**: Substrate floors are empirically grounded with provenance metadata. SC-004, SC-007 verified.

______________________________________________________________________

## Phase 6: User Story 5 - Bifurcation Integration (Priority: P2)

**Goal**: Bifurcation topology analysis consumes ternary model's richer information — assimilation_ratio and distinction between high-r and low-r solidarity — so the assimilation trap is detectable.

**Independent Test**: Construct two scenarios with identical cross-line solidarity density but different r values. Verify bifurcation analysis produces different outcomes (revolutionary vs. fascist).

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [US5] Write tests for assimilation trap detection in tests/unit/bifurcation/test_assimilation_trap.py: (AS1) high solidarity + high r → revolutionary outcome, (AS2) high solidarity + low r → fascist outcome (assimilation trap), (AS3) existing consciousness_weighted_solidarity produces identical results for same effective r values, (AS5) high assimilation_ratio + low r identified as fascist-vulnerable

### Implementation for User Story 5

- [ ] T027 [US5] Add crisis-fragile marker logic to consciousness_weighted_solidarity in src/babylon/bifurcation/consciousness.py: solidarity edges between communities with r below a threshold are marked crisis-fragile regardless of edge density. The marker is a boolean attribute on the edge weight computation
- [ ] T028 [US5] Add assimilation_ratio consumption to BifurcationResult in src/babylon/bifurcation/consciousness.py: include mean_assimilation_ratio in results, flag communities with high assimilation_ratio + low r as fascist-vulnerable in the dominant_tendency_distribution
- [ ] T029 [US5] Verify all bifurcation tests pass including new assimilation trap tests: `poetry run pytest tests/unit/bifurcation/ -v`

**Checkpoint**: Bifurcation analysis distinguishes revolutionary from fascist outcomes based on r values. SC-006 verified.

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Persistence migration, observation gap anisotropy, final verification

### Persistence Migration

- [ ] T030 [P] Add r, l, f FLOAT columns to community_state table DDL in src/babylon/persistence/postgres_schema.py (lines 149-151). Keep old columns (collective_identity, dominant_tendency, ideological_contestation) as computed/derived for backward-compat window
- [ ] T031 [P] Update INSERT/UPDATE/SELECT statements in src/babylon/persistence/postgres_runtime.py (lines 317-331) to read/write r, l, f columns. Reconstruct TernaryConsciousness from stored r, l, f on read. Derive old columns from TernaryConsciousness on write

### Observation Gap Anisotropy (FR-009)

- [ ] T032 Create anisotropic observation error model in src/babylon/bifurcation/consciousness.py: higher observation error on r component than on l/f ratio for state intelligence estimates. Export as a function that takes TernaryConsciousness and returns observed TernaryConsciousness with anisotropic noise applied

### Final Verification

- [ ] T033 Run full test suite: `mise run check` (lint + format + typecheck + test:unit). All must pass
- [ ] T034 Verify all 8 success criteria from spec.md are met: SC-001 (migration correctness), SC-002 (substrate persistence), SC-003 (proportional increase), SC-004 (floor differential), SC-005 (backward compat), SC-006 (assimilation trap), SC-007 (empirical grounding), SC-008 (simplex stability over 100 ticks)

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately to establish baseline
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US3 (Phase 3)**: Depends on Phase 2 — must complete before US1 (US1 computation needs the model and defaults)
- **US1 (Phase 4)**: Depends on Phase 3 — needs TernaryConsciousness model and CONSCIOUSNESS_DEFAULTS in place
- **US2 (Phase 5)**: Depends on Phase 2 — can run in parallel with US1 after Phase 3 model is available
- **US5 (Phase 6)**: Depends on Phase 2 — can run in parallel with US1/US2 (reads r via collective_identity property, which already exists from Phase 2)
- **Polish (Phase 7)**: Depends on all user story phases being complete

### User Story Dependencies

```text
Phase 1: Setup
    |
Phase 2: Foundational (models)
    |
Phase 3: US3 (backward compat) ──────────────────────┐
    |                                                  |
Phase 4: US1 (computation) ───┬── Phase 5: US2 ──┬── Phase 6: US5
                              |   (substrate)     |   (bifurcation)
                              |                   |
                              └───────────────────┘
                                       |
                              Phase 7: Polish
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services/functions
- Core implementation before integration
- Verification checkpoint at end of each phase
- Commit after each task or logical group

### Parallel Opportunities

- **Phase 2**: T002, T003, T004 can run in parallel (different test categories)
- **Phase 4+5+6**: After US3 completes, US1/US2/US5 can theoretically proceed in parallel since they touch different files — but US1 is recommended first as US2 and US5 build on its computation function
- **Phase 7**: T030 and T031 can run in parallel (different persistence files)

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all foundational tests together (they test different aspects):
Task T002: "TernaryConsciousness simplex + edge case tests"
Task T003: "Backward-compat computed property tests"
Task T004: "SubstrateFloor model tests"

# Then implement sequentially (same file):
Task T005: "ProvenanceLevel enum"
Task T006: "TernaryConsciousness model"
Task T007: "SubstrateFloor model"
Task T008: "Export from __init__.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (US3 + US1 = Phases 1-4)

1. Complete Phase 1: Setup (baseline)
2. Complete Phase 2: Foundational (core models)
3. Complete Phase 3: US3 (backward compatibility)
4. Complete Phase 4: US1 (ternary computation)
5. **STOP and VALIDATE**: All P1 stories complete, backward compat verified, consciousness is now a derived quantity
6. Commit and verify: `mise run check`

### Incremental Delivery

1. Phases 1-4 (MVP) -> Ternary model replaces scalar model, consciousness derived from org landscape
2. Add Phase 5 (US2) -> Substrate floors grounded in empirical data
3. Add Phase 6 (US5) -> Bifurcation detects assimilation trap
4. Add Phase 7 (Polish) -> Persistence migration, observation gap, final verification

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US4 (Ternary Visualization, P3) is DEFERRED per spec boundary — not included in tasks
- FR-009 (Observation Gap Anisotropy) is partially implemented in Phase 7 (model only); full integration with AttentionThread deferred to org-topology Phase 3
- Design decision D1: Use cadre_level * cohesion as org capacity factor, NOT budget (per plan.md D4)
- Design decision D3: OODA layer3.py direct CI writes removed in T020; org landscape mutations are the path
- All test files follow project TDD standards: red phase tests written first, then implementation
- Commit after each task or logical group per CLAUDE.md workflow guidelines
