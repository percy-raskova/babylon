# Tasks: Institution Base Model

**Input**: Design documents from `/specs/040-institution-base-model/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/institution_protocol.md, quickstart.md

**Tests**: Included per TDD mandate in CLAUDE.md — Red-Green-Refactor cycle.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Enums, configuration, data file, and deprecation scaffolding shared by ALL user stories

- [ ] T001 Add 5 new enums (ApparatusType, SocialFunction, ClassInscription, RulingClassFraction, LifecyclePhase) to src/babylon/models/enums.py following Feature 039 StrEnum pattern with feature comment header
- [ ] T002 Add 3 new EventType values (INSTITUTION_FACTION_SHIFT, INSTITUTION_REPRODUCTION, INSTITUTION_BONAPARTIST_MODE) to EventType enum in src/babylon/models/enums.py after Feature 039 section
- [ ] T003 Create InstitutionDefines section in src/babylon/config/defines.py with alpha_smoothing_rate, bonapartist_threshold, bonapartist_exclusion_threshold, and default_action_modifiers per ApparatusType (15 apparatus types × action cost modifiers from data-model.md)
- [ ] T004 Add `institution: InstitutionDefines` field to GameDefines class in src/babylon/config/defines.py after state_ai field, with Feature 040 comment header

**Checkpoint**: All enums, config defines, and data infrastructure ready for entity models

______________________________________________________________________

## Phase 2: Foundational (Core Entity Models)

**Purpose**: Frozen Pydantic models that ALL user stories depend on — MUST complete before any story phase

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Create InternalBalanceOfForces model in src/babylon/models/entities/institution.py with 3 faction weight fields (ge=0, le=1), internal_contestation field, @model_validator enforcing sum=1.0 (±0.01 tolerance following FactionBalance pattern), and @computed_field hegemonic_fraction returning RulingClassFraction with highest weight
- [ ] T006 [P] Create ReproductionMechanism model in src/babylon/models/entities/institution.py with 4 bool fields (recruitment_pipeline, training_program, succession_protocol, legal_self_perpetuation), budget_independence float (ge=0, le=1), and @computed_field reproduction_capacity = (sum(bools)/4)*0.7 + budget_independence*0.3
- [ ] T007 [P] Create SpawningBlueprint model in src/babylon/models/entities/institution.py with org_type (OrgType), default_class_character (ClassCharacter), base_attributes (dict[str, Any])
- [ ] T008 [P] Create InstitutionOrgRelation model in src/babylon/models/entities/institution.py with institution_id, organization_id (both str, min_length=1), resource_provision (float, ge=0, le=1), legal_cover (bool), legitimacy_transfer (float, ge=0, le=1), action_oversight (float, ge=0, le=1), factional_alignment (RulingClassFraction | None)
- [ ] T009 Create Institution model in src/babylon/models/entities/institution.py with all fields from data-model.md (apparatus_type, social_function, class_inscription, internal_balance, action_modifiers, budget, fixed_asset_territory_ids, legal_authorities, personnel_capacity, formalization_level, institutional_inertia, legitimacy, housed_org_ids, territory_ids, jurisdiction, lifecycle_function, reproduction, spawning_blueprints) — depends on T005-T008 for nested model types. Add @model_validator: jurisdiction only set for RSA_ types, action_modifiers values > 0.0
- [ ] T010 [P] Create FactionShiftEvent and ReproductionEvent frozen dataclass event types in src/babylon/models/entities/institution.py per FR-019 (FactionShiftEvent: institution_id, old_fraction, new_fraction, weights; ReproductionEvent: institution_id, spawned_org_type, blueprint)
- [ ] T011 [P] Write RED-phase unit tests for all entity models in tests/unit/models/test_institution.py — test InternalBalanceOfForces sum validator (valid, invalid, boundary), hegemonic_fraction computed field, ReproductionMechanism reproduction_capacity computation (all-true high, all-false low), Institution validator (jurisdiction RSA-only, action_modifier positive), SpawningBlueprint construction, InstitutionOrgRelation defaults, frozen immutability
- [ ] T012 Run GREEN phase: verify T011 tests pass against T005-T010 implementations, fix any model issues
- [ ] T013 Update src/babylon/models/entities/__init__.py to export Institution, InternalBalanceOfForces, ReproductionMechanism, InstitutionOrgRelation, SpawningBlueprint, FactionShiftEvent, ReproductionEvent

**Checkpoint**: All entity models validated and exported — user story implementation can begin

______________________________________________________________________

## Phase 3: User Story 1 — Instantiate RSA Institutions (Priority: P1) MVP

**Goal**: Create and persist RSA institutions (police, courts, military, prisons) that house Organizations. Destroying all housed orgs degrades but does not destroy the institution.

**Independent Test**: Instantiate DOJ as RSA_JUDICIAL with FBI housed, verify destroying FBI degrades capacity but DOJ persists with its social function and can reference a spawning blueprint for replacement.

### Tests for User Story 1

- [ ] T014 [P] [US1] Write RED-phase tests for RSA institution instantiation in tests/unit/institution/test_rsa_institutions.py — SC-001: DOJ as RSA_JUDICIAL with FBI housed_org_id, verify persistence attributes (formalization, inertia, legitimacy), territory footprint via territory_ids, jurisdiction set, spawning blueprint for STATE_APPARATUS replacement
- [ ] T015 [P] [US1] Write RED-phase tests for institution-org housing in tests/unit/institution/test_rsa_institutions.py — SC-006: multiple conflicting orgs (FBI Civil Rights LIBERAL vs Counterintel REVANCHIST) housed in same institution via separate InstitutionOrgRelation entries with different factional_alignment values
- [ ] T016 [P] [US1] Write RED-phase tests for degradation-not-destruction in tests/unit/institution/test_rsa_institutions.py — SC-001 scenario: given DOJ with housed_org_ids=["fbi"], removing "fbi" from housed_org_ids yields institution with empty housed_org_ids but intact social_function=ADJUDICATION, legal_authorities, fixed_asset_territory_ids, and non-zero reproduction_capacity

### Implementation for User Story 1

- [ ] T017 [US1] Add institutions dict and institution_relations list fields to WorldState in src/babylon/models/world_state.py per data-model.md graph integration section — `institutions: dict[str, Institution] = Field(default_factory=dict)` and `institution_relations: list[InstitutionOrgRelation] = Field(default_factory=list)`
- [ ] T018 [US1] Add institution serialization to WorldState.to_graph() in src/babylon/models/world_state.py — iterate institutions dict, add nodes with _node_type="institution" + model_dump(), add PRESENCE edges to territory_ids, add HOUSES edges to housed_org_ids
- [ ] T019 [US1] Add institution deserialization to WorldState.from_graph() in src/babylon/models/world_state.py — handle _node_type="institution" case, exclude computed fields (hegemonic_fraction, reproduction_capacity), reconstruct Institution from node data
- [ ] T020 [US1] Run GREEN phase: verify T014-T016 tests pass with WorldState integration (T017-T019), fix any issues
- [ ] T021 [P] [US1] Write RED-phase graph round-trip integration test in tests/integration/test_institution_graph.py — create WorldState with DOJ institution, call to_graph(), reconstruct via from_graph(), verify all institution fields survive round-trip including nested InternalBalanceOfForces and ReproductionMechanism
- [ ] T022 [US1] Run GREEN phase: verify T021 integration test passes, fix any graph serialization issues

**Checkpoint**: RSA institutions can be instantiated, stored in WorldState, and survive graph round-trips. SC-001, SC-006 validated.

______________________________________________________________________

## Phase 4: User Story 2 — Instantiate ISA Institutions (Priority: P1)

**Goal**: Create ISA institutions (schools, churches, media) with structural selectivity — certain actions cheaper, others more expensive for housed Organizations.

**Independent Test**: Instantiate Detroit Public Schools as ISA_EDUCATIONAL with lifecycle_function=D, verify EDUCATE modifier < 1.0 and REPRESS modifier > 1.0.

### Tests for User Story 2

- [ ] T023 [P] [US2] Write RED-phase tests for structural_selectivity() in tests/unit/institution/test_selectivity.py — SC-002: ISA_EDUCATIONAL makes EDUCATE cheap (modifier < 1.0) and REPRESS expensive (modifier > 1.0); SC-007: verify institution-level action_modifiers override apparatus-type defaults; test fallback to 1.0 for unmapped action types
- [ ] T024 [P] [US2] Write RED-phase tests for ISA institution instantiation in tests/unit/institution/test_isa_institutions.py — SC-002: Detroit Public Schools as ISA_EDUCATIONAL with lifecycle_function=D_DEPENDENT; SC-004: Catholic Church as ISA_RELIGIOUS queried for community embeddedness territories

### Implementation for User Story 2

- [ ] T025 [US2] Create src/babylon/institution/__init__.py with module docstring and __all__ exports
- [ ] T026 [US2] Implement structural_selectivity() pure function in src/babylon/institution/selectivity.py — takes Institution, ActionType, and defaults dict (loaded from InstitutionDefines.default_action_modifiers). Checks institution.action_modifiers first, falls back to defaults[apparatus_type][action_type], returns 1.0 if no modifier found
- [ ] T027 [US2] Run GREEN phase: verify T023-T024 tests pass with selectivity implementation (T026), fix any issues

**Checkpoint**: ISA institutions functional with structural selectivity. SC-002, SC-004, SC-007 validated.

______________________________________________________________________

## Phase 5: User Story 3 — Internal Balance of Forces (Priority: P1)

**Goal**: Institutions maintain dynamic factional balance that shifts under crisis conditions. Hegemonic fraction modulates housed Organization OODA orientation.

**Independent Test**: Create institution with {LIBERAL: 0.5, REVANCHIST: 0.3, BONAPARTIST: 0.2}, verify hegemonic=LIBERAL. Apply crisis (crisis_intensity=0.8, legitimacy=0.3) and verify REVANCHIST increases, LIBERAL decreases.

### Tests for User Story 3

- [ ] T028 [P] [US3] Write RED-phase tests for update_internal_balance() in tests/unit/institution/test_balance.py — SC-005: verify rising crisis increases REVANCHIST weight, falling legitimacy weakens LIBERAL, high external_threat activates BONAPARTIST. Test alpha smoothing (small delta per call). Test FactionShiftEvent returned when hegemonic fraction changes. Test BonapartistModeEvent when BONAPARTIST > threshold (0.4) and no other > exclusion threshold (0.35)
- [ ] T029 [P] [US3] Write RED-phase tests for hegemonic_fraction_effect() in tests/unit/institution/test_ooda_effects.py — SC-009: LIBERAL returns preferred_actions containing ASSIMILATE with high escalation_reluctance; REVANCHIST returns REPRESS preference with low escalation_reluctance; BONAPARTIST returns self-preservation behavior

### Implementation for User Story 3

- [ ] T030 [US3] Implement update_internal_balance() pure function in src/babylon/institution/balance.py — alpha-smoothed shift: crisis_intensity drives REVANCHIST up, legitimacy erosion drives LIBERAL down, external_threat drives BONAPARTIST up. Normalize weights to sum=1.0. Return (new_balance, events_list). Read alpha and thresholds from function params (caller loads from InstitutionDefines)
- [ ] T031 [US3] Implement hegemonic_fraction_effect() pure function in src/babylon/institution/ooda_effects.py — returns dict with preferred_actions, escalation_reluctance, and behavior hints per RulingClassFraction value. LIBERAL: [ASSIMILATE], reluctance=0.7. REVANCHIST: [REPRESS], reluctance=0.2. BONAPARTIST: self-preservation, reluctance=0.5
- [ ] T032 [US3] Run GREEN phase: verify T028-T029 tests pass with balance and OODA implementations (T030-T031), fix any issues

**Checkpoint**: Internal balance dynamics functional with event generation. SC-005, SC-009 validated.

______________________________________________________________________

## Phase 6: User Story 4 — Economic Institutions (Priority: P2)

**Goal**: Support economic institutions (firms, banks, extractive) housing Business Organizations with appropriate structural selectivity.

**Independent Test**: Instantiate Ford as ECONOMIC_PRODUCTIVE housing a Business org, verify budget allocation and action modifiers favor production/employment actions.

### Tests for User Story 4

- [ ] T033 [P] [US4] Write RED-phase tests for economic institution instantiation in tests/unit/institution/test_economic_institutions.py — SC-003: Ford as ECONOMIC_PRODUCTIVE housing Business org, verify EMPLOY modifier < 1.0, FUNDRAISE modifier < 1.0; ECONOMIC_FINANCIAL bank with budget_independence=0.9, verify high reproduction_capacity contribution

### Implementation for User Story 4

- [ ] T034 [US4] Run GREEN phase: verify T033 tests pass using existing models (Institution, structural_selectivity from T026) with ECONOMIC_* apparatus types and InstitutionDefines defaults — no new code expected, this validates the generic model covers economic use cases

**Checkpoint**: Economic institutions validated. SC-003 confirmed.

______________________________________________________________________

## Phase 7: User Story 5 — Institutional Reproduction (Priority: P2)

**Goal**: Institutions self-reproduce through formal mechanisms. High reproduction capacity resists degradation; low capacity is fragile.

**Independent Test**: Create two institutions — one with all reproduction mechanisms active (high budget_independence), one with none — verify reproduction_capacity > 0.8 vs < 0.2.

### Tests for User Story 5

- [ ] T035 [P] [US5] Write RED-phase tests for reproduction capacity scenarios in tests/unit/institution/test_reproduction.py — SC-008: full reproduction (all bools True, budget_independence=0.8) yields capacity > 0.8; minimal reproduction (all False, budget_independence=0.1) yields capacity < 0.2. Test intermediate cases. Verify spawning_blueprints are properly stored and accessible

### Implementation for User Story 5

- [ ] T036 [US5] Run GREEN phase: verify T035 tests pass using existing ReproductionMechanism computed field and Institution.spawning_blueprints — no new code expected, this validates the model-level reproduction mechanics

**Checkpoint**: Reproduction capacity validated. SC-008 confirmed.

______________________________________________________________________

## Phase 8: User Story 6 — Institutional Persistence and Social Function (Priority: P2)

**Goal**: Each institution carries a social function. Institutions persist as long as their social function is needed and unmet by alternatives.

**Independent Test**: Create RSA_POLICE with social_function=POLICING, verify social function is queryable per territory, and that the institution model captures all persistence attributes.

### Tests for User Story 6

- [ ] T037 [P] [US6] Write RED-phase tests for social function persistence in tests/unit/institution/test_persistence.py — verify institution with social_function=POLICING and territory_ids returns correct function-territory mapping; verify persistence attributes (formalization_level, institutional_inertia, legitimacy) are properly constrained [0, 1]; test legitimacy=0.0 edge case (terminal but not destroyed per spec)

### Implementation for User Story 6

- [ ] T038 [US6] Run GREEN phase: verify T037 tests pass using existing Institution model — no new code expected, this validates the model-level persistence semantics

**Checkpoint**: Social function and persistence validated. SC-001 persistence aspect confirmed.

______________________________________________________________________

## Phase 9: Graph Query Functions

**Purpose**: Pure query functions for institution-graph interactions used across multiple stories

- [ ] T039 [P] Write RED-phase tests for graph query functions in tests/unit/institution/test_queries.py — test community_embeddedness() returns dict[str, float] for institution's territory overlap with community hyperedges; test helper queries for territory_footprint and housed_orgs retrieval via GraphProtocol
- [ ] T040 Implement community_embeddedness() query function in src/babylon/institution/queries.py following ooda/initiative.py compute_community_embeddedness pattern — query institution territory_ids against MEMBERSHIP edges to compute overlap with community hyperedges
- [ ] T041 Run GREEN phase: verify T039 tests pass with query implementation (T040), fix any issues

______________________________________________________________________

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Deprecation, exports, and final validation

- [ ] T042 [P] Add DeprecationWarning to Organization.is_institution field access in src/babylon/models/entities/organization.py per FR-018 — use Pydantic field_validator or model_validator to emit warning when is_institution=True
- [ ] T043 [P] Add DeprecationWarning to Organization.institutional_persistence field access in src/babylon/models/entities/organization.py per FR-018
- [ ] T044 [P] Add deprecation notice header comment to src/babylon/schemas/entities/institution.schema.json per FR-017
- [ ] T045 [P] Update src/babylon/institution/__init__.py with complete __all__ exports for all public functions (update_internal_balance, structural_selectivity, hegemonic_fraction_effect, community_embeddedness)
- [ ] T046 Verify all existing Organization tests still pass (SC-010) — run `poetry run pytest tests/unit/organizations/ -v` and confirm no regressions from Institution layer introduction
- [ ] T047 Run full CI gate: `mise run check` — lint, format, typecheck, test:unit all green
- [ ] T048 Run quickstart.md validation: manually verify code examples from specs/040-institution-base-model/quickstart.md execute correctly against implemented models and functions

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001-T004 can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (enums, config) — BLOCKS all user stories
- **User Stories (Phases 3-8)**: All depend on Phase 2 completion
  - US1 (Phase 3): WorldState integration — foundational for graph round-trip
  - US2 (Phase 4): Requires US1 for WorldState context, plus new institution/ module
  - US3 (Phase 5): Independent of US1/US2 (pure functions on InternalBalanceOfForces)
  - US4 (Phase 6): Requires US2 (structural_selectivity function)
  - US5 (Phase 7): Independent (model-level validation only)
  - US6 (Phase 8): Independent (model-level validation only)
- **Graph Queries (Phase 9)**: Requires Phase 2 models + Phase 3 WorldState integration
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (RSA Institutions)**: After Phase 2 — No other story dependencies. MVP target.
- **US2 (ISA Institutions)**: After Phase 2 — Independent, but institution/ module created here
- **US3 (Balance of Forces)**: After Phase 2 — Fully independent (pure functions on models)
- **US4 (Economic Institutions)**: After US2 (needs structural_selectivity from Phase 4)
- **US5 (Reproduction)**: After Phase 2 — Fully independent (model computed fields)
- **US6 (Persistence)**: After Phase 2 — Fully independent (model constraints)

### Within Each User Story

- Tests written FIRST and FAIL before implementation (Red phase)
- Models before functions
- Functions before integration
- GREEN phase verifies tests pass

### Parallel Opportunities

- T001 + T002 can run in parallel (different enum sections)
- T003 + T004 sequential (T004 depends on T003)
- T005 + T006 + T007 + T008 + T010 + T011 all parallel (different models, different files)
- T014 + T015 + T016 parallel (test file, different test classes)
- T023 + T024 parallel (different test files)
- T028 + T029 parallel (different test files)
- US3, US5, US6 can run in parallel after Phase 2 (no cross-dependencies)
- T042 + T043 + T044 + T045 all parallel (different files)

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all model implementations in parallel:
Task T005: "Create InternalBalanceOfForces model in src/babylon/models/entities/institution.py"
Task T006: "Create ReproductionMechanism model in src/babylon/models/entities/institution.py"
Task T007: "Create SpawningBlueprint model in src/babylon/models/entities/institution.py"
Task T008: "Create InstitutionOrgRelation model in src/babylon/models/entities/institution.py"
Task T010: "Create FactionShiftEvent and ReproductionEvent in src/babylon/models/entities/institution.py"

# Then T009 (Institution main model) depends on T005-T008 completing
# Then T011 (tests) can run in parallel with T010 and T013
```

## Parallel Example: User Stories 3 + 5 + 6

```bash
# These three stories have no cross-dependencies after Phase 2:
# Agent A: US3 - Balance of Forces (T028 → T030 → T031 → T032)
# Agent B: US5 - Reproduction (T035 → T036)
# Agent C: US6 - Persistence (T037 → T038)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational models (T005-T013)
3. Complete Phase 3: User Story 1 — RSA Institutions (T014-T022)
4. **STOP and VALIDATE**: Run `poetry run pytest tests/unit/institution/ tests/integration/test_institution_graph.py -v`
5. Commit and verify SC-001, SC-006

### Incremental Delivery

1. Setup + Foundational → All models and enums ready
2. Add US1 (RSA) → WorldState integration → Graph round-trip works
3. Add US2 (ISA) → Structural selectivity function → Action modifiers work
4. Add US3 (Balance) → Balance dynamics → OODA modulation works
5. Add US4-US6 → Economic, Reproduction, Persistence validated
6. Polish → Deprecation, exports, CI green

### Recommended Single-Agent Order

For sequential execution by a single implementer:
1. Phase 1 (Setup): T001 → T002 → T003 → T004
2. Phase 2 (Models): T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013
3. Phase 3 (US1 RSA): T014-T016 → T017 → T018 → T019 → T020 → T021 → T022
4. Phase 4 (US2 ISA): T023-T024 → T025 → T026 → T027
5. Phase 5 (US3 Balance): T028-T029 → T030 → T031 → T032
6. Phase 6 (US4 Economic): T033 → T034
7. Phase 7 (US5 Reproduction): T035 → T036
8. Phase 8 (US6 Persistence): T037 → T038
9. Phase 9 (Queries): T039 → T040 → T041
10. Phase 10 (Polish): T042-T045 → T046 → T047 → T048

______________________________________________________________________

## Notes

- [P] tasks = different files or sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently testable after its phase checkpoint
- Commit after each phase completion
- All models frozen (ConfigDict(frozen=True)) — mutations via model_copy()
- No EventBus dependency in institution module — events returned as data
- All defaults from InstitutionDefines in defines.py — no magic constants
