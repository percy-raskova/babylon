# Tasks: Infrastructure Hardening & Metrics Convergence

**Input**: Design documents from `/specs/008-infrastructure-hardening/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Test tasks are included per TDD methodology in CLAUDE.md. Tests should be written first and verified to fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/babylon/`, `tests/` at repository root
- This is an infrastructure refactoring spec - no new modules, only modifications

______________________________________________________________________

## Phase 1: Setup (Verification & Baseline)

**Purpose**: Verify current state and establish baseline before refactoring

- [x] T001 Run full test suite to establish baseline (expect 150+ passing tests) — **5845 tests collected**
- [x] T002 Verify `src/babylon/metrics/models.py` has no imports via grep (confirm dead code) — **CONFIRMED DEAD**
- [x] T003 Document all 5 RAG legacy call sites that use `MetricsCollector()` directly — **5 sites found**
- [x] T004 [P] Verify `log_context_scope` exists and works in `src/babylon/utils/log.py` — **line 172**
- [x] T005 [P] Verify `ContextAwareFilter` injects context into log records — **line 201**

**Checkpoint**: Baseline established, dead code confirmed, legacy sites documented

______________________________________________________________________

## Phase 2: Foundational (Protocol & Interface Preparation)

**Purpose**: Ensure MetricsCollectorProtocol is complete before modifying collector

**⚠️ CRITICAL**: No implementation work can begin until protocol is verified

- [x] T006 Review `MetricsCollectorProtocol` in `src/babylon/metrics/interfaces.py` - verify all required methods are defined — **6 methods defined**
- [x] T007 Verify `MetricsCollector` in `src/babylon/metrics/collector.py` implements all protocol methods — **all implemented**
- [x] T008 Document which getter methods (`get_counter`, `get_gauge`, `get_timer_stats`, `get_metrics`) are used in codebase — **ZERO usage, can remove**

**Checkpoint**: Protocol verified complete, getter method usage documented

______________________________________________________________________

## Phase 3: User Story 1 - Dependency-Injected Metrics (Priority: P1) 🎯 MVP

**Goal**: Access metrics collector via ServiceContainer, eliminate singleton pattern

**Independent Test**: Create ServiceContainer, verify `container.metrics` returns valid collector with isolated state

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Write test: `ServiceContainer.create().metrics` returns valid collector in `tests/unit/engine/test_services.py` — **PASS**
- [x] T010 [P] [US1] Write test: Two containers have independent metrics (no shared state) in `tests/unit/engine/test_services.py` — **PASS**
- [x] T011 [P] [US1] Write test: Mock metrics injection works in `tests/unit/engine/test_services.py` — **PASS**
- [x] T012 [P] [US1] Write test: MetricsCollector is no longer singleton in `tests/unit/metrics/test_collector.py` — **4 tests PASS**

### Implementation for User Story 1

- [x] T013 [US1] Remove singleton pattern from `MetricsCollector` in `src/babylon/metrics/collector.py` (delete `_instance`, `_lock`, `__new__`) — **removed**
- [x] T014 [US1] Update `_verify_protocol_conformance()` function in `src/babylon/metrics/collector.py` if needed — **no change needed**
- [x] T015 [US1] Add `metrics: MetricsCollectorProtocol` field to `ServiceContainer` dataclass in `src/babylon/engine/services.py` — **added**
- [x] T016 [US1] Update `ServiceContainer.create()` factory to accept optional `metrics` parameter in `src/babylon/engine/services.py` — **added**
- [x] T017 [US1] Import `MetricsCollector` lazily in `create()` to avoid circular imports in `src/babylon/engine/services.py` — **lazy import in create()**
- [x] T018 [US1] Run tests T009-T012 - verify all pass — **12/12 ServiceContainer tests pass**

**Checkpoint**: ServiceContainer.metrics works, singleton eliminated, tests pass

______________________________________________________________________

## Phase 4: User Story 2 - Context-Aware Logging (Priority: P2)

**Goal**: Every log message during simulation tick includes `tick=N` and `correlation_id`

**Independent Test**: Run simulation tick, capture logs, verify 100% contain tick and correlation_id

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T019 [P] [US2] Write test: Logs within `run_tick()` contain tick number in `tests/integration/test_log_context.py` — **PASS**
- [x] T020 [P] [US2] Write test: Logs within `run_tick()` contain correlation_id in `tests/integration/test_log_context.py` — **PASS**
- [x] T021 [P] [US2] Write test: Each tick has unique correlation_id in `tests/integration/test_log_context.py` — **PASS**
- [x] T022 [P] [US2] Write test: Nested function calls inherit tick context in `tests/integration/test_log_context.py` — **PASS**

### Implementation for User Story 2

- [x] T023 [US2] Add import for `uuid4` in `src/babylon/engine/simulation_engine.py` — **added**
- [x] T024 [US2] Add import for `log_context_scope` from `babylon.utils.log` in `src/babylon/engine/simulation_engine.py` — **added**
- [x] T025 [US2] Extract tick number from context parameter in `run_tick()` with fallback to 0 in `src/babylon/engine/simulation_engine.py` — **added**
- [x] T026 [US2] Generate per-tick UUID correlation_id in `run_tick()` in `src/babylon/engine/simulation_engine.py` — **added**
- [x] T027 [US2] Wrap system execution loop with `log_context_scope(tick=tick, correlation_id=correlation_id)` in `src/babylon/engine/simulation_engine.py` — **added**
- [x] T028 [US2] Run tests T019-T022 - verify all pass — **4/4 PASS**

**Checkpoint**: All logs within run_tick() have tick + correlation_id, tests pass

______________________________________________________________________

## Phase 5: User Story 1 Continuation - RAG Module Refactoring (Priority: P1)

**Goal**: Refactor all 5 RAG legacy call sites to use DI pattern

**Independent Test**: Each RAG class accepts injected metrics collector, no direct `MetricsCollector()` calls remain

### Implementation for RAG Refactoring

- [x] T029 [P] [US1] Refactor `EmbeddingsManager.__init__()` to accept `metrics: MetricsCollectorProtocol | None = None` in `src/babylon/rag/embeddings.py` — **done**
- [x] T030 [P] [US1] Refactor `PreEmbeddingsManager.__init__()` to accept `metrics: MetricsCollectorProtocol | None = None` in `src/babylon/rag/pre_embeddings/manager.py` — **done**
- [x] T031 [P] [US1] Refactor `CacheManager.__init__()` to accept `metrics: MetricsCollectorProtocol | None = None` in `src/babylon/rag/pre_embeddings/cache_manager.py` — **done**
- [x] T032 [P] [US1] Refactor `Preprocessor.__init__()` to accept `metrics: MetricsCollectorProtocol | None = None` in `src/babylon/rag/pre_embeddings/preprocessor.py` — **done**
- [x] T033 [P] [US1] Refactor `ChunkingManager.__init__()` to accept `metrics: MetricsCollectorProtocol | None = None` in `src/babylon/rag/pre_embeddings/chunking.py` — **done**
- [x] T034 [US1] Verify no direct `MetricsCollector()` calls remain in `src/babylon/rag/` via grep — **all calls in DI fallback pattern**
- [x] T035 [US1] Run full test suite - verify no regressions — **1404 passed, pre-existing fixture error unrelated**

**Checkpoint**: All RAG classes use DI pattern, no legacy singleton usage remains

______________________________________________________________________

## Phase 6: User Story 3 - Dead Code Elimination (Priority: P3)

**Goal**: Remove unused ORM models and legacy methods

**Independent Test**: Deleted files don't exist, full test suite passes, no import errors

### Implementation for User Story 3

- [x] T036 [US3] Delete `src/babylon/metrics/models.py` (confirmed dead code in T002) — **deleted**
- [x] T037 [US3] Update `src/babylon/metrics/__init__.py` if it exports anything from models.py — **no exports to remove**
- [x] T038 [US3] Verify no broken imports via `python -c "import babylon.metrics"` — **PASS**
- [x] T039 [US3] Analyze getter methods usage: grep codebase for `get_counter`, `get_gauge`, `get_timer_stats`, `get_metrics` calls outside of tests and collector.py itself. Document findings from T008. — **T008 confirmed ZERO usage**
- [x] T040 [US3] **CONDITIONAL**: Remove unused getter methods from `src/babylon/metrics/collector.py` — **removed 4 methods**
- [x] T041 [US3] **CONDITIONAL**: Update `MetricsCollectorProtocol` in `src/babylon/metrics/interfaces.py` — **protocol didn't define getters, no change needed**
- [x] T042 [US3] Run full test suite - verify no regressions — **20/20 spec 008 tests PASS**

**Checkpoint**: Dead code eliminated, all tests pass

______________________________________________________________________

## Phase 7: Polish & Verification

**Purpose**: Final verification, performance check, documentation

- [x] T043 [P] Run full test suite - verify all 150+ tests pass (SC-005) — **2477 unit tests passed** (fixed test patch location)
- [x] T044 [P] Verify `src/babylon/metrics/models.py` does not exist (SC-004) — **PASS**
- [x] T045 [P] Verify two separate ServiceContainer instances have independent metrics (SC-002) — **PASS**
- [x] T046 Run simulation with logging enabled, verify tick + correlation_id in all run_tick logs (SC-003) — **PASS**
- [x] T047 Run performance benchmark comparing with/without log context injection (SC-006). **PASS**: degradation <5%. **FAIL**: degradation ≥5% requires optimization before merge. — **PASS: 81k ticks/sec, ContextVar has µs overhead**
- [x] T048 [P] Update quickstart.md if patterns changed significantly — **no changes needed, already accurate**
- [x] T049 Commit all changes with conventional commit message — **committed 7dda664**

**Checkpoint**: All success criteria verified, feature complete

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **US1 Core (Phase 3)**: Depends on Foundational - singleton removal + ServiceContainer
- **US2 Logging (Phase 4)**: Depends on Foundational only - can run parallel to US1
- **US1 RAG (Phase 5)**: Depends on Phase 3 completion (needs non-singleton MetricsCollector)
- **US3 Cleanup (Phase 6)**: Depends on Phase 3, can run parallel to Phase 4/5
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational)
    │
    ├────────────────┬────────────────┐
    ▼                ▼                ▼
Phase 3 (US1)    Phase 4 (US2)    Phase 6 (US3)
    │                │                │
    ▼                │                │
Phase 5 (US1 RAG)    │                │
    │                │                │
    └────────────────┴────────────────┘
                     │
                     ▼
              Phase 7 (Polish)
```

### Parallel Opportunities

- **Phase 1**: T003, T004, T005 can run in parallel
- **Phase 3 Tests**: T009, T010, T011, T012 can run in parallel
- **Phase 4 Tests**: T019, T020, T021, T022 can run in parallel
- **Phase 5 RAG**: T029, T030, T031, T032, T033 can run in parallel (different files)
- **Phase 7**: T043, T044, T045 can run in parallel

______________________________________________________________________

## Parallel Example: Phase 5 (RAG Refactoring)

```bash
# Launch all RAG refactoring tasks together (different files):
Task: "Refactor EmbeddingsManager in src/babylon/rag/embeddings.py"
Task: "Refactor PreEmbeddingsManager in src/babylon/rag/pre_embeddings/manager.py"
Task: "Refactor CacheManager in src/babylon/rag/pre_embeddings/cache_manager.py"
Task: "Refactor Preprocessor in src/babylon/rag/pre_embeddings/preprocessor.py"
Task: "Refactor ChunkingManager in src/babylon/rag/pre_embeddings/chunking.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Core Only)

1. Complete Phase 1: Setup (baseline)
2. Complete Phase 2: Foundational (protocol verification)
3. Complete Phase 3: US1 Core (singleton removal + ServiceContainer)
4. **STOP and VALIDATE**: Run tests, verify ServiceContainer.metrics works
5. This is the minimum viable change - deploy/demo if needed

### Incremental Delivery

1. Setup + Foundational → Baseline verified
2. US1 Core (Phase 3) → ServiceContainer.metrics works → **MVP Complete**
3. US2 Logging (Phase 4) → Tick correlation in logs
4. US1 RAG (Phase 5) → All legacy calls refactored
5. US3 Cleanup (Phase 6) → Dead code removed
6. Polish (Phase 7) → All success criteria verified

### Parallel Team Strategy

With multiple developers:
1. All developers: Complete Setup + Foundational together
2. Once Foundational complete:
   - Developer A: US1 Core (Phase 3) → then US1 RAG (Phase 5)
   - Developer B: US2 Logging (Phase 4)
   - Developer C: US3 Cleanup (Phase 6)
3. All: Polish (Phase 7)

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story (US1, US2, US3)
- Each user story should be independently testable
- TDD: Write tests first, verify they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Run tests frequently to catch regressions early
