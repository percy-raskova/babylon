# Tasks: Hypergraph Community Layer

**Input**: Design documents from `/specs/022-hypergraph-community-layer/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: TDD is mandatory per project standards. Each user story phase includes RED tests before implementation, followed by GREEN verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Add enums, configuration, and service container extension needed by all user stories.

- [x] T001 Add CommunityType, LegalStatus, MembershipRole enums to src/babylon/models/enums.py following StrEnum convention with lowercase snake_case values and feature reference comment
- [x] T002 [P] Add CommunityDefines config section to src/babylon/config/defines.py with alpha-smoothing rates (heat_decay, cohesion_decay, infrastructure_decay), community_overlap_bonus, rent_differential_penalty, and LEGAL_STATUS_MULTIPLIERS dict
- [x] T003 [P] Add community_hypergraph optional field (Any = field(default=None)) to ServiceContainer in src/babylon/engine/services.py and matching kwarg to create() factory

**Checkpoint**: Enums importable, defines accessible via `services.defines.community`, service container accepts hypergraph.

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and formula stubs that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create CommunityState and CommunityMembership frozen Pydantic models in src/babylon/models/entities/community.py using constrained types (Probability for heat/cohesion/infrastructure/visibility, Coefficient for modifiers) per data-model.md
- [x] T005 [P] Add community_memberships (list[CommunityMembership], default=[]) and community_cost_modifier (float, default=1.0) fields to SocialClass in src/babylon/models/entities/social_class.py; update model_validator to handle serialization
- [x] T006 [P] Create formula stubs (calculate_solidarity_potential, calculate_threat_score, calculate_infrastructure_decay, calculate_solidarity_amplification) in src/babylon/formulas/community.py with correct signatures and NotImplementedError
- [x] T007 [P] Register community formulas in FormulaRegistry.default() in src/babylon/engine/formula_registry.py

**Checkpoint**: Foundation ready — `CommunityState()` and `CommunityMembership()` constructible, SocialClass accepts community fields, formulas registered in registry.

______________________________________________________________________

## Phase 3: User Story 1 — Community Membership as Hyperedge Structure (Priority: P1)

**Goal**: Build and query the XGI hypergraph from agent community memberships. Compute overlap matrix.

**Independent Test**: Create agents with memberships, build hypergraph, verify membership queries and overlap matrix.

### TDD RED Phase

- [x] T008 [P] [US1] Write RED tests for CommunityState and CommunityMembership model validation (field constraints, frozen immutability, effective_visibility property, enum values) in tests/unit/models/test_community_models.py
- [x] T009 [P] [US1] Write RED tests for build_community_hypergraph(), shared_communities(), and community_overlap_matrix() covering: multi-membership agents, empty community exclusion, role/strength accessibility, diagonal=community_count in tests/unit/engine/systems/test_community_system.py

### Implementation

- [x] T010 [US1] Implement effective_visibility computed property on CommunityMembership (returns 1.0 if overt else base visibility) in src/babylon/models/entities/community.py
- [x] T011 [US1] Implement build_community_hypergraph(agents, community_states) using XGI add_edge(members, idx=community_type.value, **state_attrs) in src/babylon/engine/systems/community.py
- [x] T012 [US1] Implement shared_communities(H, agent_a, agent_b) and community_overlap_matrix(H) using xgi.incidence_matrix(sparse=True) and I @ I.T in src/babylon/engine/systems/community.py

### GREEN Phase

- [x] T013 [US1] Verify all US1 tests pass; refactor if needed

**Checkpoint**: Hypergraph builds from agent memberships. Overlap matrix computable. All US1 acceptance scenarios verified.

______________________________________________________________________

## Phase 4: User Story 2 — Solidarity Potential from Community Overlap (Priority: P2)

**Goal**: Compute solidarity potential from community overlap and amplify solidarity_strength on existing SOLIDARITY edges.

**Independent Test**: Construct agents with known overlaps and rent differentials, verify formula values and solidarity_strength amplification.

### TDD RED Phase

- [x] T014 [P] [US2] Write RED tests for calculate_solidarity_potential() covering: positive overlap bonus, rent differential penalty, zero-overlap baseline in tests/unit/formulas/test_community_formulas.py
- [x] T015 [P] [US2] Write RED tests for solidarity transmission amplification covering: infrastructure×cohesion×strength scaling, no amplification without shared communities, amplified value written to SOLIDARITY edge in tests/unit/engine/systems/test_community_system.py

### Implementation

- [x] T016 [US2] Implement calculate_solidarity_potential(base_solidarity, shared_count, rent_a, rent_b, overlap_bonus, rent_penalty) in src/babylon/formulas/community.py
- [x] T017 [US2] Implement calculate_solidarity_amplification(base_strength, shared_communities, community_states, membership_strength_a, membership_strength_b) in src/babylon/formulas/community.py
- [x] T018 [US2] Implement solidarity amplification phase in CommunitySystem.step(): iterate SOLIDARITY edges, compute shared communities for each pair, amplify solidarity_strength via graph.update_edge() in src/babylon/engine/systems/community.py

### GREEN Phase

- [x] T019 [US2] Verify all US2 tests pass; refactor if needed

**Checkpoint**: Solidarity potential computed from overlap. SOLIDARITY edges amplified by community infrastructure. All US2 acceptance scenarios verified.

______________________________________________________________________

## Phase 5: User Story 3 — State Repression Targeting Communities (Priority: P3)

**Goal**: Compute threat scores, implement community-level repression actions, legal status escalation.

**Independent Test**: Designate a community as extremist, verify threat scores increase for all visible members. Disrupt infrastructure, verify reproduction costs rise.

### TDD RED Phase

- [x] T020 [P] [US3] Write RED tests for calculate_threat_score() covering: cumulative multi-community score, effective_visibility from overt flag, legal_status_multiplier weighting in tests/unit/formulas/test_community_formulas.py
- [x] T021 [P] [US3] Write RED tests for repression actions (designate_extremist raises heat + legal_status, infiltrate reduces cohesion, disrupt_infrastructure reduces infrastructure, arrest_organizers removes CORE_ORGANIZERs) in tests/unit/engine/systems/test_community_system.py

### Implementation

- [x] T022 [US3] Implement calculate_threat_score(memberships, community_states) with cumulative heat×effective_visibility×role_weight×legal_multiplier in src/babylon/formulas/community.py
- [x] T023 [US3] Implement repression action functions (designate, infiltrate, disrupt_infrastructure, arrest_organizers) as methods on CommunitySystem returning updated CommunityState via model_copy() in src/babylon/engine/systems/community.py
- [x] T024 [US3] Implement legal_status_escalate() enforcing one-way ratchet (LEGAL→SURVEILLED→...→CRIMINALIZED, never reverse) in src/babylon/engine/systems/community.py
- [x] T025 [US3] Implement threat score computation phase in CommunitySystem.step(): compute per-agent threat_score, write to graph node attribute via graph.update_node() in src/babylon/engine/systems/community.py

### GREEN Phase

- [x] T026 [US3] Verify all US3 tests pass; refactor if needed

**Checkpoint**: Threat scores aggregate across memberships. Legal status one-way ratchet enforced. All repression actions produce correct community state changes. All US3 acceptance scenarios verified.

______________________________________________________________________

## Phase 6: User Story 4 — Reproduction Cost Modification (Priority: P4)

**Goal**: Community membership modifies agent reproduction costs multiplicatively and rent access.

**Independent Test**: Create agents with community memberships, verify reproduction costs compound correctly.

### TDD RED Phase

- [x] T027 [P] [US4] Write RED tests for community_cost_modifier computation (multiplicative compounding across memberships, no-membership baseline=1.0, rent_access_modifier reduction) in tests/unit/models/test_community_models.py

### Implementation

- [x] T028 [US4] Implement compute_community_cost_modifier(memberships, community_states) returning product of reproduction_cost_modifiers in src/babylon/formulas/community.py
- [x] T029 [US4] Implement reproduction cost and rent access modification in CommunitySystem.step(): for each agent, compute compound modifier, write community_cost_modifier to graph node via graph.update_node() in src/babylon/engine/systems/community.py

### GREEN Phase

- [x] T030 [US4] Verify all US4 tests pass; refactor if needed

**Checkpoint**: Reproduction costs compound multiplicatively. Rent access reduced for affected communities. All US4 acceptance scenarios verified.

______________________________________________________________________

## Phase 7: Integration & Engine Registration

**Purpose**: Wire CommunitySystem into the engine pipeline, implement alpha-smoothing, run full integration.

- [x] T031 Implement alpha-smoothing decay phase in CommunitySystem.step(): heat decays toward 0, cohesion decays toward 0, infrastructure decays toward 0 with core_organizer maintenance factor, using CommunityDefines rates in src/babylon/engine/systems/community.py
- [x] T032 Register CommunitySystem at position 6 in _DEFAULT_SYSTEMS (before SolidaritySystem) in src/babylon/engine/simulation_engine.py with import and materialist-causality comment
- [ ] T033 [P] Write integration tests for full pipeline: community layer active during multi-tick simulation, solidarity amplification visible to SolidaritySystem, threat scores aggregate correctly across ticks in tests/integration/test_community_integration.py
- [x] T034 [P] Add community model and enum exports to src/babylon/models/__init__.py and system exports to src/babylon/engine/systems/__init__.py
- [ ] T035 Run mise run check to verify lint (ruff), type checking (mypy --strict on new files), and all tests pass

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3) must complete before US2 (Phase 4) — US2 needs hypergraph builder
  - US3 (Phase 5) and US4 (Phase 6) can start after US1 completes (parallel if staffed)
  - US2, US3, US4 are independent of each other
- **Integration (Phase 7)**: Depends on all user stories complete

### Within Each User Story

- RED tests MUST be written and FAIL before implementation
- Implementation tasks within a story are sequential (models before services)
- GREEN verification after all implementation tasks
- Commit after each story completes

### Parallel Opportunities

```bash
# Phase 1: All setup tasks in parallel after T001
T001 (enums first — others depend on types)
T002, T003 (parallel after T001)

# Phase 2: Three tasks parallel after T004
T004 (models first — others depend on types)
T005, T006, T007 (parallel after T004)

# Phase 3 (US1): RED tests in parallel
T008, T009 (parallel)
T010, T011, T012 (sequential)

# Phase 4 (US2): RED tests in parallel
T014, T015 (parallel)
T016, T017 (parallel — different functions)
T018 (depends on T016, T017)

# Phase 5 (US3): RED tests in parallel
T020, T021 (parallel)
T022, T023, T024 (sequential)
T025 (depends on T022-T024)

# After US1 completes: US3 and US4 can run in parallel with US2
Phase 4 (US2) || Phase 5 (US3) || Phase 6 (US4)

# Phase 7: Integration tasks in parallel
T031, T032 (sequential — system before registration)
T033, T034 (parallel)
T035 (final — depends on all above)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
1. Complete Phase 2: Foundational
1. Complete Phase 3: User Story 1 (community membership as hyperedge)
1. **STOP and VALIDATE**: Hypergraph builds, queries work, overlap matrix correct
1. Commit: `feat(022): community membership hyperedge structure`

### Incremental Delivery

1. Setup + Foundational → Foundation ready
1. Add US1 → Test independently → Commit (MVP)
1. Add US2 → Test independently → Commit (solidarity potential)
1. Add US3 → Test independently → Commit (state repression)
1. Add US4 → Test independently → Commit (reproduction costs)
1. Integration + Engine Registration → Full pipeline test → Commit

### Commit Strategy

Each user story = one commit. Final integration = one commit. Total: ~6 commits for the feature.

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- RED tests MUST fail before implementation begins (TDD discipline)
- Commit after each story or logical group
- XGI uses `idx` parameter (not `id`) for custom hyperedge IDs — breaking change in v0.9
- Auto-wrap guard required in CommunitySystem.step() per codebase convention
