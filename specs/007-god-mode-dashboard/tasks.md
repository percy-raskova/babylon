# Tasks: God Mode Dashboard (Phase 1)

**Input**: Design documents from `/specs/007-god-mode-dashboard/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Tests ARE included per project TDD requirements (CLAUDE.md specifies TDD workflow).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/babylon/ui/dashboard/` for implementation
- **Tests**: `tests/unit/ui/dashboard/` for unit tests, `tests/integration/ui/` for integration

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and shared modules

- [x] T001 Verify PyQt6 and pydeck dependencies in pyproject.toml per plan.md
- [x] T002 [P] Add pytest-qt to dev dependencies in pyproject.toml
- [x] T003 [P] Create dashboard package structure at src/babylon/ui/dashboard/__init__.py
- [x] T004 [P] Add pytest-qt fixture to tests/conftest.py
- [x] T005 Create data models (HexDisplayData, InspectorDisplayData, ConnectionStatus) in src/babylon/ui/dashboard/models.py

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create Bunker Constructivism theme constants in src/babylon/ui/dashboard/theme.py
- [x] T007 Implement profit_rate_to_rgb() color mapping function in src/babylon/ui/dashboard/theme.py
- [x] T008 [P] Create test fixtures importing MockSimulation from src/babylon/ui/dashboard/testing.py in tests/unit/ui/dashboard/conftest.py
- [x] T009 [P] Write unit tests for color mapping boundary values in tests/unit/ui/dashboard/test_theme.py
- [x] T010 Create H3 index and FIPS validation utilities in src/babylon/ui/dashboard/validators.py

**Checkpoint**: Foundation ready - user story implementation can now begin

______________________________________________________________________

## Phase 3: User Story 1 - View Detroit Region Map (Priority: P1) 🎯 MVP

**Goal**: Display real-time H3 hexagonal map of Detroit region colored by profit_rate

**Independent Test**: Launch dashboard, verify hexagons render with correct colors for Detroit geography

**Requirements Covered**: FR-001, FR-002, FR-011, SC-001, SC-005

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Write unit test for MapViewport initialization in tests/unit/ui/dashboard/test_map_viewport.py
- [x] T012 [P] [US1] Write unit test for pydeck HTML generation in tests/unit/ui/dashboard/test_map_viewport.py
- [x] T013 [P] [US1] Write unit test for incremental color update (setProps pattern) in tests/unit/ui/dashboard/test_map_viewport.py

### Implementation for User Story 1

- [x] T014 [US1] Create MapViewport widget skeleton (QWidget + QWebEngineView) in src/babylon/ui/dashboard/map_viewport.py
- [x] T015 [US1] Implement MapViewport.initialize() with pydeck HTML generation in src/babylon/ui/dashboard/map_viewport.py
- [x] T016 [US1] Inject QWebChannel bridge JavaScript into pydeck HTML in src/babylon/ui/dashboard/map_viewport.py
- [x] T017 [US1] Implement MapViewport.update_colors() with deck.setProps() pattern (FR-011) in src/babylon/ui/dashboard/map_viewport.py
- [x] T018 [US1] Add tooltip support for hex hover (profit_rate display) in src/babylon/ui/dashboard/map_viewport.py

**Checkpoint**: Map renders Detroit hexes with profit_rate colors - User Story 1 independently testable

______________________________________________________________________

## Phase 4: User Story 2 - Inspect Selected Territory (Priority: P2)

**Goal**: Click hex to view territory details (Value Tensor) in Inspector panel

**Independent Test**: Click hexagon, verify Inspector panel shows all TerritoryState properties

**Requirements Covered**: FR-003, FR-004, FR-008, FR-009, FR-014, SC-002

### Tests for User Story 2 ⚠️

- [ ] T019 [P] [US2] Write unit test for InspectorPanel display modes (territory, no_selection, unclaimed, error with red border) in tests/unit/ui/dashboard/test_inspector_panel.py
- [ ] T020 [P] [US2] Write unit test for HexBridge hex click handling in tests/unit/ui/dashboard/test_hex_bridge.py
- [ ] T021 [P] [US2] Write unit test for territory lookup via get_node_by_spatial_index() in tests/unit/ui/dashboard/test_hex_bridge.py

### Implementation for User Story 2

- [ ] T022 [US2] Create InspectorPanel widget with QLabel layout in src/babylon/ui/dashboard/inspector_panel.py
- [ ] T023 [US2] Implement InspectorPanel.display_territory() with Value Tensor fields in src/babylon/ui/dashboard/inspector_panel.py
- [ ] T024 [US2] Implement InspectorPanel.display_no_selection() and display_unclaimed() in src/babylon/ui/dashboard/inspector_panel.py
- [ ] T025 [US2] Implement InspectorPanel.display_error() with red border indicator in src/babylon/ui/dashboard/inspector_panel.py
- [ ] T026 [US2] Create HexBridge QObject with pyqtSignal definitions in src/babylon/ui/dashboard/hex_bridge.py
- [ ] T027 [US2] Implement HexBridge.on_hex_click() slot with territory resolution in src/babylon/ui/dashboard/hex_bridge.py
- [ ] T028 [US2] Implement HexBridge.on_background_click() slot in src/babylon/ui/dashboard/hex_bridge.py
- [ ] T029 [US2] Add QWebChannel registration in MapViewport for HexBridge in src/babylon/ui/dashboard/map_viewport.py
- [ ] T030 [US2] Implement MapViewport.highlight_territory() for selected hex borders (FR-014) in src/babylon/ui/dashboard/map_viewport.py
- [ ] T031 [US2] Implement MapViewport.clear_highlight() in src/babylon/ui/dashboard/map_viewport.py
- [ ] T032 [US2] Connect HexBridge signals to InspectorPanel methods in src/babylon/ui/dashboard/main_window.py

**Checkpoint**: Hex clicks update Inspector with territory details - User Story 2 independently testable

______________________________________________________________________

## Phase 5: User Story 3 - Observe Real-Time Tick Updates (Priority: P3)

**Goal**: Map and Inspector auto-update on each simulation tick with 30 FPS throttling

**Independent Test**: Step simulation, verify both map colors and Inspector values update automatically

**Requirements Covered**: FR-005, FR-006, FR-007, FR-012, SC-003, SC-004, SC-006

### Tests for User Story 3 ⚠️

- [ ] T033 [P] [US3] Write unit test for DashboardObserver throttling (30 FPS) in tests/unit/ui/dashboard/test_observer.py
- [ ] T034 [P] [US3] Write unit test for state coalescing (rapid ticks) in tests/unit/ui/dashboard/test_observer.py
- [ ] T035 [P] [US3] Write integration test for end-to-end tick updates in tests/integration/ui/test_dashboard_simulation.py

### Implementation for User Story 3

- [ ] T036 [US3] Create DashboardObserver with QTimer throttling in src/babylon/ui/dashboard/observer.py
- [ ] T037 [US3] Implement DashboardObserver.on_tick() with 33ms coalescing in src/babylon/ui/dashboard/observer.py
- [ ] T038 [US3] Implement tick_processed signal emission in src/babylon/ui/dashboard/observer.py
- [ ] T039 [US3] Implement InspectorPanel.update_from_snapshot() for tick updates in src/babylon/ui/dashboard/inspector_panel.py
- [ ] T040 [US3] Add register_observer() call in DashboardWindow.__init__ in src/babylon/ui/dashboard/main_window.py
- [ ] T041 [US3] Implement unregister_observer() in DashboardWindow.closeEvent() (FR-012) in src/babylon/ui/dashboard/main_window.py
- [ ] T042 [US3] Connect DashboardObserver.tick_processed to MapViewport.update_colors() in src/babylon/ui/dashboard/main_window.py
- [ ] T043 [US3] Connect DashboardObserver.tick_processed to InspectorPanel.update_from_snapshot() in src/babylon/ui/dashboard/main_window.py

**Checkpoint**: Simulation step() triggers automatic UI updates - User Story 3 independently testable

______________________________________________________________________

## Phase 6: User Story 4 - Launch Dashboard with Themed UI (Priority: P4)

**Goal**: Dashboard window with Bunker Constructivism theme and proper layout

**Independent Test**: Launch dashboard, verify dark theme colors and 70/30 map/inspector split

**Requirements Covered**: FR-010, FR-013, FR-015

### Tests for User Story 4 ⚠️

- [ ] T044 [P] [US4] Write unit test for DashboardWindow layout (QSplitter 70/30) in tests/unit/ui/dashboard/test_main_window.py
- [ ] T045 [P] [US4] Write unit test for theme application (QSS) in tests/unit/ui/dashboard/test_main_window.py
- [ ] T045a [P] [US4] Write unit test for DEBUG logging on connection state changes (FR-013) in tests/unit/ui/dashboard/test_main_window.py

### Implementation for User Story 4

- [ ] T046 [US4] Create DashboardWindow skeleton (QMainWindow) in src/babylon/ui/dashboard/main_window.py
- [ ] T047 [US4] Implement QSplitter layout with 70% map, 30% inspector in src/babylon/ui/dashboard/main_window.py
- [ ] T048 [US4] Apply QSS_THEME stylesheet to DashboardWindow in src/babylon/ui/dashboard/main_window.py
- [ ] T049 [US4] Set minimum window size (1460×820) per layout spec in src/babylon/ui/dashboard/main_window.py
- [ ] T050 [US4] Add status bar with connection indicator in src/babylon/ui/dashboard/main_window.py
- [ ] T051 [US4] Add debug logging for errors and connection state changes (FR-013) in src/babylon/ui/dashboard/main_window.py
- [ ] T052 [US4] Implement graceful exception handling per FR-015 in src/babylon/ui/dashboard/main_window.py

**Checkpoint**: Dashboard launches with complete theme - User Story 4 independently testable

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, cleanup, and validation

- [ ] T053 [P] Add __main__.py entry point for `python -m babylon.ui.dashboard` in src/babylon/ui/dashboard/__main__.py
- [ ] T054 [P] Implement MockSimulation.with_detroit_territories() for dev/test in src/babylon/ui/dashboard/testing.py
- [ ] T055 Update src/babylon/ui/__init__.py to export dashboard module
- [ ] T056 Run full integration test suite in tests/integration/ui/test_dashboard_simulation.py
- [ ] T057 Validate quickstart.md scenarios work end-to-end
- [ ] T058 Memory leak verification: run 10,000 ticks, verify <50MB growth
- [ ] T059 Performance verification: verify no frame exceeds 100ms render time

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T005)
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3 → P4)
  - Some parallelization possible between stories (see below)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 (needs MapViewport for click handling)
- **User Story 3 (P3)**: Depends on US1 (needs MapViewport.update_colors())
- **User Story 4 (P4)**: Depends on US1, US2, US3 (DashboardWindow integrates all components)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Foundation components before dependent components
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

Phase 1 Setup:
- T002, T003, T004 can run in parallel (different files)

Phase 2 Foundational:
- T008, T009 can run in parallel

User Story 1 Tests:
- T011, T012, T013 can run in parallel

User Story 2 Tests:
- T019, T020, T021 can run in parallel

User Story 3 Tests:
- T033, T034, T035 can run in parallel

User Story 4 Tests:
- T044, T045, T045a can run in parallel

Phase 7 Polish:
- T053, T054 can run in parallel

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit test for MapViewport initialization in tests/unit/ui/dashboard/test_map_viewport.py"
Task: "Write unit test for pydeck HTML generation in tests/unit/ui/dashboard/test_map_viewport.py"
Task: "Write unit test for incremental color update in tests/unit/ui/dashboard/test_map_viewport.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready - Map renders Detroit hexes with colors

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP complete** (map renders)
3. Add User Story 2 → Test independently → Hex selection works
4. Add User Story 3 → Test independently → Real-time updates work
5. Add User Story 4 → Test independently → Theme applied, window polished
6. Each story adds value without breaking previous stories

### Sequential Execution (Recommended)

Due to UI component dependencies, sequential execution is recommended:

1. **Phase 1-2**: Setup + Foundational (8 tasks)
2. **Phase 3**: User Story 1 - Map (8 tasks) → VALIDATE
3. **Phase 4**: User Story 2 - Inspector (14 tasks) → VALIDATE
4. **Phase 5**: User Story 3 - Observer (11 tasks) → VALIDATE
5. **Phase 6**: User Story 4 - Window (10 tasks) → VALIDATE
6. **Phase 7**: Polish (7 tasks) → FINAL VALIDATION

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

## Summary

| Phase | Tasks | User Story | Key Deliverable |
|-------|-------|------------|-----------------|
| Phase 1 | 5 | Setup | Package structure, dependencies |
| Phase 2 | 5 | Foundational | Theme, color mapping, mock simulation |
| Phase 3 | 8 | US1 - Map (P1) 🎯 | H3 hexagonal map with profit_rate colors |
| Phase 4 | 14 | US2 - Inspector (P2) | Click-to-inspect with Value Tensor |
| Phase 5 | 11 | US3 - Observer (P3) | 30 FPS throttled real-time updates |
| Phase 6 | 10 | US4 - Theme (P4) | Bunker Constructivism window |
| Phase 7 | 7 | Polish | Entry point, testing, validation |
| **Total** | **60** | | |

**MVP Scope**: Phases 1-3 (18 tasks) delivers a working map visualization
