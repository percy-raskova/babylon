# Tasks: Community Hyperedge Layer Upgrade

**Input**: Design documents from `/specs/029-community-hyperedge-upgrade/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — project uses TDD (CLAUDE.md mandate). Red-Green-Refactor per story.

**Organization**: Tasks grouped by user story (P1→P5). Stories are sequential because each builds on the previous (US2 needs US1 category, US4 needs US3 consciousness, US5 integrates all).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Verify clean baseline before any changes

- [x] T001 Run `mise run check` to verify clean lint/typecheck/test state
- [x] T002 Run existing community tests to establish passing baseline: `poetry run pytest tests/unit/models/test_community_models.py tests/unit/engine/systems/test_community_system.py tests/unit/formulas/test_community_formulas.py -v`

______________________________________________________________________

## Phase 2: Foundational (New Enums)

**Purpose**: Add HyperedgeCategory and ConsciousnessTendency enums that all user stories depend on

**CRITICAL**: No user story work can begin until these enums exist

- [x] T003 Add `HyperedgeCategory` enum (CONTRADICTION_PAIR, INSTITUTIONAL_EXCLUSION, LIFECYCLE_PHASE) to `src/babylon/models/enums.py` after CommunityType
- [x] T004 Add `ConsciousnessTendency` enum (ASSIMILATIONIST_LIBERAL, ASSIMILATIONIST_FASCIST, REVOLUTIONARY) to `src/babylon/models/enums.py` after HyperedgeCategory
- [x] T005 Update `src/babylon/models/enums.py` `__all__` or package exports in `src/babylon/models/__init__.py` to include new enums

**Checkpoint**: New enums importable, `mise run check` passes

______________________________________________________________________

## Phase 3: User Story 1 — Three-Category Taxonomy (Priority: P1)

**Goal**: Every CommunityType maps to exactly one HyperedgeCategory with exhaustive validation

**Independent Test**: Verify all 14 CommunityType members map to one category, exhaustiveness check catches missing types

### Tests (RED phase)

- [x] T006 [US1] Write failing tests for COMMUNITY_CATEGORY_MAP in `tests/unit/models/test_community_models.py`: all 14 types mapped, exhaustive (no unmapped), correct categories per contract (SETTLER→CONTRADICTION_PAIR, DISABLED→INSTITUTIONAL_EXCLUSION, YOUTH→LIFECYCLE_PHASE)
- [x] T007 [US1] Write failing tests for category sets (HEGEMONIC_COMMUNITIES, MARGINALIZED_COMMUNITIES, LIFECYCLE_COMMUNITIES) in `tests/unit/models/test_community_models.py`: correct membership, union covers all 14 types

### Implementation (GREEN phase)

- [x] T008 [US1] Add `COMMUNITY_CATEGORY_MAP` dict mapping all 14 CommunityType→HyperedgeCategory in `src/babylon/models/entities/community.py`
- [x] T009 [US1] Add `HEGEMONIC_COMMUNITIES`, `MARGINALIZED_COMMUNITIES`, `LIFECYCLE_COMMUNITIES` as frozensets in `src/babylon/models/entities/community.py`
- [x] T010 [US1] Add import-time exhaustiveness validation: `assert set(COMMUNITY_CATEGORY_MAP.keys()) == set(CommunityType)` in `src/babylon/models/entities/community.py`
- [x] T011 [US1] Add `category` field (HyperedgeCategory) to CommunityState with `@model_validator(mode="after")` that auto-assigns from COMMUNITY_CATEGORY_MAP in `src/babylon/models/entities/community.py`
- [x] T012 [US1] Verify all T006-T007 tests now pass (GREEN) and all 43 pre-existing tests still pass

**Checkpoint**: Taxonomy complete. Every CommunityState has a category. `mise run check` passes.

______________________________________________________________________

## Phase 4: User Story 2 — Contradiction Axis Formalization (Priority: P2)

**Goal**: Two contradiction axes (Colonial, Patriarchal) with query functions for hegemonic/marginalized status and opposing communities

**Independent Test**: `get_contradiction_axis(SETTLER)` returns COLONIAL_AXIS, `get_opposing_communities(SETTLER)` returns [NEW_AFRIKAN, FIRST_NATIONS, CHICANO], `get_contradiction_axis(DISABLED)` returns None

### Tests (RED phase)

- [x] T013 [US2] Write failing tests for ContradictionAxis model and COLONIAL_AXIS/PATRIARCHAL_AXIS constants in `tests/unit/models/test_community_models.py`: correct hegemonic/marginalized members per contract
- [x] T014 [US2] Write failing tests for axis query functions in `tests/unit/models/test_community_models.py`: `get_contradiction_axis`, `is_hegemonic`, `is_marginalized`, `get_opposing_communities`, `shared_marginalized_communities` per contracts/taxonomy-api.md test cases

### Implementation (GREEN phase)

- [x] T015 [US2] Add `ContradictionAxis` frozen Pydantic model to `src/babylon/models/entities/community.py` with fields: id, name, hegemonic (CommunityType), marginalized (list[CommunityType]), extraction_mechanism, exclusive, permeable
- [x] T016 [US2] Add `COLONIAL_AXIS`, `PATRIARCHAL_AXIS`, and `CONTRADICTION_AXES` list constants in `src/babylon/models/entities/community.py`
- [x] T017 [US2] Implement `get_contradiction_axis(community) -> ContradictionAxis | None` in `src/babylon/models/entities/community.py`
- [x] T018 [US2] Implement `is_hegemonic(community) -> bool` and `is_marginalized(community) -> bool` in `src/babylon/models/entities/community.py`
- [x] T019 [US2] Implement `get_opposing_communities(community) -> list[CommunityType]` in `src/babylon/models/entities/community.py`
- [x] T020 [US2] Implement `shared_marginalized_communities(set, set) -> set[CommunityType]` in `src/babylon/models/entities/community.py`
- [x] T021 [US2] Verify all T013-T014 tests now pass (GREEN) and all pre-existing tests still pass

**Checkpoint**: Axis queries functional. `mise run check` passes.

______________________________________________________________________

## Phase 5: User Story 3 — Community Consciousness Model (Priority: P3)

**Goal**: CommunityConsciousness model with collective_identity, dominant_tendency, ideological_contestation; SYNTHETIC defaults for all 14 types; JSON serialization roundtrip

**Independent Test**: All 14 types have defaults, INCARCERATED=REVOLUTIONARY, consciousness survives model_dump→model_validate roundtrip

### Tests (RED phase)

- [ ] T022 [US3] Write failing tests for CommunityConsciousness model in `tests/unit/models/test_community_models.py`: creation, validation (CI and contestation constrained to [0,1]), frozen immutability
- [ ] T023 [US3] Write failing tests for CONSCIOUSNESS_DEFAULTS in `tests/unit/models/test_community_models.py`: all 14 types present, INCARCERATED=REVOLUTIONARY, FIRST_NATIONS=REVOLUTIONARY CI=0.6, SETTLER=ASSIMILATIONIST_LIBERAL, YOUTH contestation=0.5
- [ ] T024 [P] [US3] Write failing test for consciousness serialization roundtrip in `tests/unit/models/test_community_models.py`: model_dump(mode="json")→model_validate preserves all fields exactly for all 14 defaults

### Implementation (GREEN phase)

- [ ] T025 [US3] Add `CommunityConsciousness` frozen Pydantic model to `src/babylon/models/entities/community.py` with fields: collective_identity (Probability, default 0.3), dominant_tendency (ConsciousnessTendency, default ASSIMILATIONIST_LIBERAL), ideological_contestation (Probability, default 0.2)
- [ ] T026 [US3] Add `consciousness` field (CommunityConsciousness, default_factory) to CommunityState in `src/babylon/models/entities/community.py`
- [ ] T027 [US3] Add `CONSCIOUSNESS_DEFAULTS` dict mapping all 14 CommunityType→CommunityConsciousness with SYNTHETIC values per spec in `src/babylon/models/entities/community.py`
- [ ] T028 [US3] Add import-time exhaustiveness validation for CONSCIOUSNESS_DEFAULTS (same pattern as T010) in `src/babylon/models/entities/community.py`
- [ ] T029 [US3] Verify all T022-T024 tests now pass (GREEN) and all pre-existing tests still pass

**Checkpoint**: Consciousness model complete. Serialization verified. `mise run check` passes.

______________________________________________________________________

## Phase 6: User Story 4 — Infiltration Resistance (Priority: P4)

**Goal**: Computed infiltration_resistance on CommunityState, effective_infiltration_ceiling function

**Independent Test**: CI=0.9/cohesion=0.8 → resistance≈0.852, effective ceiling significantly reduced for high-resistance communities

### Tests (RED phase)

- [ ] T030 [US4] Write failing tests for `infiltration_resistance` computed field in `tests/unit/models/test_community_models.py`: 6 test cases from contracts/consciousness-api.md (high/low CI×cohesion, boundary 0/0 and 1/1, moderate combinations)
- [ ] T031 [US4] Write failing tests for `effective_infiltration_ceiling` in `tests/unit/models/test_community_models.py`: empty list returns base unchanged, high-resistance reduces ceiling, test cases from contract

### Implementation (GREEN phase)

- [ ] T032 [US4] Add named constants `INFILTRATION_CI_WEIGHT`, `INFILTRATION_COHESION_WEIGHT`, `INFILTRATION_INTERACTION_WEIGHT`, `INFILTRATION_CEILING_FACTOR` in `src/babylon/models/entities/community.py`
- [ ] T033 [US4] Add `infiltration_resistance` as `@computed_field` on CommunityState in `src/babylon/models/entities/community.py` using the formula: `CI*0.6 + cohesion*0.3 + CI*cohesion*0.1`
- [ ] T034 [US4] Implement `effective_infiltration_ceiling(base_ceiling, target_community_states) -> float` in `src/babylon/models/entities/community.py`
- [ ] T035 [US4] Verify all T030-T031 tests now pass (GREEN) and all pre-existing tests still pass

**Checkpoint**: Infiltration mechanics complete. `mise run check` passes.

______________________________________________________________________

## Phase 7: User Story 5 — Cross-Class Bridge Detection and Integration (Priority: P5)

**Goal**: Bridge detection for institutional exclusion communities spanning contradiction axes; build_community_hypergraph includes consciousness; all existing tests pass

**Independent Test**: DISABLED with members from both SETTLER and NEW_AFRIKAN identified as bridge; updated hypergraph includes consciousness attributes; 43 pre-existing tests pass

### Tests (RED phase)

- [ ] T036 [US5] Write failing test for `is_cross_class_bridge` computed field in `tests/unit/models/test_community_models.py`: True for INSTITUTIONAL_EXCLUSION, False for CONTRADICTION_PAIR and LIFECYCLE_PHASE
- [ ] T037 [US5] Write failing test for `communities_spanning_axis` in `tests/unit/engine/systems/test_community_system.py`: synthetic hypergraph with DISABLED members on both sides of colonial axis → DISABLED is bridge; QUEER only on marginalized side → not bridge
- [ ] T038 [US5] Write failing test for updated `build_community_hypergraph` in `tests/unit/engine/systems/test_community_system.py`: hyperedge attributes include consciousness_ci, consciousness_tendency, consciousness_contestation, category

### Implementation (GREEN phase)

- [ ] T039 [US5] Add `is_cross_class_bridge` as `@computed_field` on CommunityState in `src/babylon/models/entities/community.py`
- [ ] T040 [US5] Implement `communities_spanning_axis(H, axis) -> list[CommunityType]` in `src/babylon/engine/systems/community.py`
- [ ] T041 [US5] Update `build_community_hypergraph` in `src/babylon/engine/systems/community.py` to include consciousness and category attributes on hyperedges
- [ ] T042 [US5] Verify all T036-T038 tests now pass (GREEN)
- [ ] T043 [US5] Run all 43 pre-existing community tests and confirm zero failures (FR-008 backward compatibility)

**Checkpoint**: Full feature complete. All stories functional. `mise run check` passes.

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, exports, and documentation

- [ ] T044 Update `__init__.py` exports: add HyperedgeCategory, ConsciousnessTendency, CommunityConsciousness, ContradictionAxis, and all new functions/constants to package `__all__` in `src/babylon/models/__init__.py` and `src/babylon/models/entities/__init__.py`
- [ ] T045 Run `mise run check` (lint + format + typecheck + test:unit)
- [ ] T046 Run `mise run test:unit` (full unit suite, not just community tests)
- [ ] T047 Validate quickstart.md scenarios: execute each integration scenario from `specs/029-community-hyperedge-upgrade/quickstart.md` in a test or REPL
- [ ] T048 Commit final implementation with conventional commit message

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 Taxonomy (Phase 3)**: Depends on Foundational (needs HyperedgeCategory enum)
- **US2 Axes (Phase 4)**: Depends on US1 (needs COMMUNITY_CATEGORY_MAP, HEGEMONIC_COMMUNITIES)
- **US3 Consciousness (Phase 5)**: Depends on Foundational (needs ConsciousnessTendency enum); independent of US1/US2 at model level, but logically follows
- **US4 Infiltration (Phase 6)**: Depends on US3 (needs consciousness.collective_identity on CommunityState)
- **US5 Integration (Phase 7)**: Depends on US1 + US2 + US3 + US4 (integration story)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 2 (Foundational)
  ├── US1 (Taxonomy) ────┐
  │     └── US2 (Axes) ──┤
  └── US3 (Consciousness)│
        └── US4 (Resist.) │
                          └── US5 (Integration + Compat)
                                └── Phase 8 (Polish)
```

### Within Each User Story

1. Write failing tests (RED)
2. Implement models/constants/functions (GREEN)
3. Verify tests pass + pre-existing tests pass
4. Commit checkpoint

### Parallel Opportunities

- **T003 and T004**: Could be combined (same file, adjacent sections) but kept separate for granular tracking
- **T006 and T007**: Both write tests in same file — sequential
- **T013 and T014**: Both write tests in same file — sequential
- **T022, T023, T024**: T024 marked [P] (serialization test is independent of default-value tests)
- **T036, T037, T038**: Write to different test files — T036 and T037/T038 are parallelizable across files

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# T003 and T004 modify same file — run sequentially
Task: "Add HyperedgeCategory enum to src/babylon/models/enums.py"
Task: "Add ConsciousnessTendency enum to src/babylon/models/enums.py"
# T005 follows (exports update)
```

## Parallel Example: User Story 5

```bash
# These test tasks target DIFFERENT files — can run in parallel:
Task: "T036 [US5] is_cross_class_bridge test in test_community_models.py"
Task: "T037 [US5] communities_spanning_axis test in test_community_system.py"
Task: "T038 [US5] build_community_hypergraph test in test_community_system.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify baseline)
2. Complete Phase 2: Foundational (add enums)
3. Complete Phase 3: User Story 1 (taxonomy mapping)
4. **STOP and VALIDATE**: Every CommunityState has a category, exhaustiveness checked
5. Commit and verify

### Incremental Delivery

1. Setup + Foundational → Enums available
2. US1 (Taxonomy) → Category mapping works → Commit
3. US2 (Axes) → Axis queries work → Commit
4. US3 (Consciousness) → Consciousness model and defaults → Commit
5. US4 (Infiltration) → Resistance formula works → Commit
6. US5 (Integration) → Hypergraph updated, all 43 tests pass → Commit
7. Polish → Exports, full suite, quickstart validation → Final commit

### Note on Sequential Dependencies

Unlike many feature specs where user stories are independent, this feature's stories build on each other:
- Category (US1) is required by consciousness defaults (US3) and bridge detection (US5)
- Axes (US2) are required by bridge detection (US5)
- Consciousness (US3) is required by infiltration resistance (US4)

This means **stories must be implemented in priority order (P1→P2→P3→P4→P5)**, not in parallel. Each story adds an independently testable layer.

______________________________________________________________________

## Notes

- All new models use `ConfigDict(frozen=True)` per project convention
- All [0,1] fields use `Probability` constrained type, not raw float
- CONSCIOUSNESS_DEFAULTS are SYNTHETIC — flag in code comments per FR-004
- Infiltration resistance coefficients are named constants for tuning discoverability
- `build_community_hypergraph` backward compatibility: new attributes are additive, existing attributes unchanged
- 43 pre-existing tests must pass at every checkpoint (FR-008)
