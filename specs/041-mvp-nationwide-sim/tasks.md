# Tasks: MVP Nationwide Simulation

**Input**: Design documents from `/specs/041-mvp-nationwide-sim/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: Included — CLAUDE.md mandates TDD (Red-Green-Refactor) and SC-006 requires 20+ Django backend tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Test Infrastructure)

**Purpose**: Create Django test infrastructure that all user story tests depend on

- [x] T001 Create Django test package with conftest fixtures in `web/game/tests/__init__.py` and `web/game/tests/conftest.py` — fixtures for authenticated client, game session factory, engine bridge mock
- [x] T002 [P] Create verb mapping constant `VERB_TO_ACTION_TYPE` in `web/game/engine_bridge.py` — static dict mapping 9 UI verbs to ActionType enum values per research.md mapping table
- [x] T003 [P] Create canonical verb set constant `CANONICAL_VERBS` in `web/game/engine_bridge.py` — frozenset of the 9 valid player verbs for validation

______________________________________________________________________

## Phase 2: Foundational (Defect Fixes)

**Purpose**: Fix 3 blocking defects that must be resolved before any user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests (Red Phase)

- [x] T004 [P] Write test for import boundary compliance in `web/game/tests/test_import_boundary.py` — verify `web/game/apps.py` does not import from `babylon.*` directly (mirrors existing `tests/unit/web/test_import_boundary.py` pattern)
- [x] T005 [P] Write test for GameEventLog migration in `web/game/tests/test_migrations.py` — verify `game_event_log` table exists after migrations run

### Implementation (Green Phase)

- [x] T006 Fix import boundary violation in `web/game/apps.py` — move `PostgresRuntime` initialization into `web/game/engine_bridge.py` as a bridge function (e.g., `init_persistence()`), have `apps.py` call only bridge functions (FR-008)
- [x] T007 [P] Create Django migration for GameEventLog in `web/game/migrations/` — run `python manage.py makemigrations game` from `web/` directory, verify migration applies cleanly (FR-009)
- [x] T008 [P] Fix TypeScript error in `web/frontend/src/components/HexMap.tsx` — add null/undefined guard at the possibly-undefined invocation, verify with `cd web/frontend && npx tsc --noEmit` (FR-010)

**Checkpoint**: Import boundary test passes, `npm run build` succeeds, migration applies. Commit with `fix: resolve 3 blocking defects (import boundary, migration, TS error)`.

______________________________________________________________________

## Phase 3: User Story 1 — Play a Complete Game Session (Priority: P1) 🎯 MVP

**Goal**: A player can create a game, submit actions that affect the simulation, resolve ticks with visible results, and see endgame conditions.

**Independent Test**: Create a game, submit 3 actions across 3 ticks, verify (a) simulation state changes meaningfully, (b) action results appear with success/failure status, (c) time series charts show diverging data.

### Tests (Red Phase)

- [x] T009 [P] [US1] Write test for action injection in `tests/unit/web/test_engine_bridge.py` — test that `resolve_tick()` reads pending turns and passes them as `persistent_context["player_actions"]` to `step()`
- [x] T010 [P] [US1] Write test for ActionResult persistence in `tests/unit/web/test_engine_bridge.py` — test that after `resolve_tick()`, ActionResult rows exist in DB with non-null deltas for submitted actions
- [x] T011 [P] [US1] Write test for action validation in `tests/unit/web/test_api.py` — test that invalid verb (not in canonical 9) returns 400 error
- [x] T012 [P] [US1] Write test for idempotency guard in `tests/unit/web/test_api.py` — test that concurrent resolve requests are rejected when session status is "resolving"
- [x] T013 [P] [US1] Write test for endgame detection in `tests/unit/web/test_engine_bridge.py` — test that when EndgameDetector fires, snapshot includes endgame event data

### Implementation (Green Phase)

- [x] T014 [US1] Wire player actions into engine step in `web/game/engine_bridge.py` — in `resolve_tick()`, call `self.get_pending_actions(session_id, state.tick)`, format as `{"player_actions": {org_id: [action_dicts]}}` using `VERB_TO_ACTION_TYPE`, pass as `persistent_context` to `step()`
- [x] T015 [US1] Snapshot pre-step state for delta computation in `web/game/engine_bridge.py` — before calling `step()`, capture `class_consciousness` and `heat` values from graph nodes for each action's `target_id`
- [x] T016 [US1] Persist ActionResult records in `web/game/engine_bridge.py` — after `step()`, compute consciousness_delta and heat_delta by diffing pre/post graph node values, write one ActionResult row per submitted action via Django ORM or persistence layer
- [x] T017 [US1] Add server-side action validation in `web/game/api.py` — verify verb is in `CANONICAL_VERBS` before calling `bridge.submit_action()`, return 400 with descriptive error message for invalid verbs (FR-003)
- [x] T018 [US1] Add idempotency guard to resolve endpoint in `web/game/api.py` — wrap in `transaction.atomic()`, use `GameSession.objects.select_for_update().get()`, check `status == "active"`, set `status = "resolving"` before step, restore to "active" after, rollback on failure (FR-004)
- [x] T019 [US1] Integrate endgame detection in `web/game/engine_bridge.py` — after `step()`, check events for REVOLUTIONARY_VICTORY, ECOLOGICAL_COLLAPSE, FASCIST_CONSOLIDATION and add `endgame` field to snapshot with outcome type and summary (FR-007)
- [x] T020 [US1] Add endgame notification UI in `web/frontend/src/components/layout/GameShell.tsx` — after `resolveTick()` returns, check snapshot for endgame data, display modal overlay with outcome type (Revolutionary Victory, Ecological Collapse, Fascist Consolidation) and summary text
- [x] T021 [US1] Disable resolve button during resolution in `web/frontend/src/components/TopBar.tsx` and `web/frontend/src/components/action/ActionComposer.tsx` — already implemented: both components accept `resolving` prop and disable buttons with "Resolving..." text

**Checkpoint**: Submit an action, resolve tick, see ActionResult with deltas. Endgame notification displays on terminal condition. Double-click on resolve is prevented. Invalid actions are rejected. Commit with `feat(game-loop): wire player actions into engine and persist results (FR-001 through FR-007)`.

______________________________________________________________________

## Phase 4: User Story 2 — Understand the Simulation State (Priority: P2)

**Goal**: A player can inspect territories, entities, and organizations to understand material conditions.

**Independent Test**: Click 3 different territories and 2 organizations, verify each inspector shows distinct, non-zero, changing data.

### Implementation

- [ ] T022 [US2] Verify territory inspector renders real data in `web/frontend/src/components/Inspector.tsx` — manually test that clicking a hex shows heat, sector type, operational profile, rent level, biocapacity, population. If any fields are missing from the snapshot, add them to `_serialize_territory()` in `web/game/engine_bridge.py`
- [ ] T023 [US2] Verify entity inspector renders survival probabilities in `web/frontend/src/components/Inspector.tsx` — confirm P(Acquiescence), P(Revolution), wealth, consciousness, organization, agitation display correctly. If any fields are missing, add them to `_serialize_entity()` in `web/game/engine_bridge.py`
- [ ] T024 [US2] Verify time series charts accumulate across ticks in `web/frontend/src/components/TimeSeries.tsx` — confirm `tickSummaries` in `gameStore.ts` appends new data points after each resolve, and Recharts displays multi-tick trends

**Checkpoint**: All inspector views show meaningful, changing data across ticks. Commit with `feat(inspectors): verify state visibility for territories and entities (US2)`.

______________________________________________________________________

## Phase 5: User Story 3 — Make Strategic Decisions (Priority: P2)

**Goal**: A player can evaluate organizations, understand verb effects, and see action consequences.

**Independent Test**: Submit "Educate" targeting two different territories over 5 ticks, verify consciousness values diverge.

### Implementation

- [ ] T025 [US3] Filter org list to player-controlled factions in `web/frontend/src/components/action/ActionComposer.tsx` — filter the organizations list from snapshot to only show orgs where `org_type === "POLITICAL_FACTION"` and `is_player === true`
- [ ] T026 [P] [US3] Enhance verb tooltips in `web/frontend/src/components/action/VerbSelector.tsx` — add HTML `title` attributes to each verb button using the existing `description` field from `VERB_GRID`, ensuring hover tooltips appear (FR-012)
- [ ] T027 [US3] Verify action results display deltas in `web/frontend/src/components/TickResults.tsx` — confirm that after Phase 3 ActionResult persistence, the `MetricPill` components show signed consciousness_delta and heat_delta values with green/red coloring

**Checkpoint**: Only player-controlled orgs appear in action composer. Verb tooltips visible on hover. Action results show per-action deltas. Commit with `feat(strategy): org filtering, verb tooltips, and result deltas (US3, FR-012)`.

______________________________________________________________________

## Phase 6: User Story 4 — Return to a Game in Progress (Priority: P3)

**Goal**: A player can close browser, return later, and resume at the correct tick via a bookmarkable URL.

**Independent Test**: Create a game, play 5 ticks, close tab, reopen app at `/games/{id}`, verify game loads at tick 5 with full state.

### Tests (Red Phase)

- [ ] T028 [P] [US4] Write frontend test for route rendering in `web/frontend/src/App.test.tsx` — test that `/login`, `/games`, and `/games/:id` routes render the correct components

### Implementation (Green Phase)

- [ ] T029 [US4] Replace View state machine with React Router in `web/frontend/src/App.tsx` — wrap app in `BrowserRouter`, define `Routes`: `/login` → `LoginPage`, `/games` → `GameList`, `/games/:id` → `GameShell`. Use `Navigate` for redirects. Preserve `checkAuth` logic via route guards (FR-011)
- [ ] T030 [US4] Update navigation handlers in `web/frontend/src/App.tsx` — replace `setView()` calls with `useNavigate()` hooks: `handleLogin` → `navigate("/games")`, `handleSelectGame(id)` → `navigate("/games/${id}")`, `handleBackToGames` → `navigate("/games")`, `handleLogout` → `navigate("/login")`
- [ ] T031 [US4] Update GameShell to read game ID from URL in `web/frontend/src/components/layout/GameShell.tsx` — use `useParams()` to get `id` instead of receiving it as a prop, pass to `useGameState(id)`
- [ ] T032 [US4] Update Vite proxy for client-side routing in `web/frontend/vite.config.ts` — ensure the dev server returns `index.html` for all non-API routes (SPA fallback) so direct URL access works

**Checkpoint**: Navigate to `/games/{id}` directly, page loads at correct tick. Browser refresh preserves state. Back button works. Commit with `feat(routing): URL-based navigation with react-router-dom (FR-011)`.

______________________________________________________________________

## Phase 7: User Story 5 — Choose a Scenario (Priority: P3)

**Goal**: A player can select from available scenarios when creating a new game.

**Independent Test**: Create games with two different scenarios, verify territory counts and entity compositions differ.

### Tests (Red Phase)

- [ ] T033 [P] [US5] Write test for scenario list endpoint in `web/game/tests/test_api.py` — test `GET /api/scenarios/` returns at least 2 scenarios with key, name, description, territory_count

### Implementation (Green Phase)

- [ ] T034 [US5] Add scenario list endpoint in `web/game/api.py` — `GET /api/scenarios/` that queries available scenario factory functions from `babylon.engine.scenarios` and returns metadata (key, name, description, approximate territory count) (FR-013)
- [ ] T035 [US5] Accept scenario parameter in game creation in `web/game/api.py` — modify `POST /api/games/` to accept optional `scenario` field in request body, pass to `engine_bridge.create_game()`, default to `us_nationwide`
- [ ] T036 [US5] Add scenario selector to game creation UI in `web/frontend/src/components/GameList.tsx` — fetch `GET /api/scenarios/` on mount, display scenario cards/dropdown in the "New Game" flow, send selected scenario key with create request

**Checkpoint**: Create a game with the small scenario, verify fewer territories. Create with nationwide, verify ~1,100 territories. Commit with `feat(scenarios): scenario selection for game creation (FR-013)`.

______________________________________________________________________

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete test coverage requirements and verify all success criteria

- [ ] T037 Verify all existing engine tests pass with `mise run test:unit` — ensure zero regressions (SC-005)
- [ ] T038 [P] Verify all existing frontend tests pass with `mise run web:check` — ensure zero regressions (SC-005)
- [ ] T039 [P] Verify `npm run build` succeeds in `web/frontend/` — confirm no TypeScript errors remain (SC-007)
- [ ] T040 Count Django backend tests and fill gaps in `web/game/tests/` — ensure at least 20 tests exist covering game creation, action submission, tick resolution, validation errors, idempotency, action results, endgame, and scenario selection (SC-006)
- [ ] T041 Update Playwright E2E tests in `web/frontend/e2e/` — update `auth.spec.ts`, `game-loop.spec.ts`, `navigation.spec.ts` to run against live server covering login, game creation, action submission, tick resolution, and result verification (SC-008)
- [ ] T042 Run full integration smoke test — create game, submit 3 actions across 3 ticks, verify ActionResults, play to tick 10 within 15 minutes (SC-001, SC-002)
- [ ] T043 Update `ai-docs/state.yaml` with new test counts and feature status

**Checkpoint**: All 8 success criteria verified. Commit with `feat(041): MVP nationwide simulation complete — all success criteria met`.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — core game loop, MVP
- **US2 (Phase 4)**: Depends on US1 (needs working tick resolution to verify changing data)
- **US3 (Phase 5)**: Depends on US1 (needs ActionResult data to verify deltas)
- **US4 (Phase 6)**: Depends on Foundational only — can parallel with US1 (independent routing work)
- **US5 (Phase 7)**: Depends on Foundational only — can parallel with US1 (independent scenario work)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    v
Phase 2 (Foundational: Defect Fixes)
    │
    ├──────────────┬────────────────┐
    v              v                v
Phase 3 (US1)   Phase 6 (US4)   Phase 7 (US5)
    │              │                │
    ├──────┐       │                │
    v      v       │                │
Phase 4  Phase 5   │                │
(US2)    (US3)     │                │
    │      │       │                │
    v      v       v                v
Phase 8 (Polish & Verification)
```

### Within Each User Story

- Tests (Red Phase) MUST be written and FAIL before implementation
- Implementation tasks within a story execute sequentially unless marked [P]
- Story complete = checkpoint verification passes
- Commit after each checkpoint

### Parallel Opportunities

**Phase 2 parallel group** (after T004-T005 tests written):
```
T006 (import boundary fix)
T007 (migration)          ← all different files, run in parallel
T008 (TypeScript fix)
```

**Phase 3 test parallel group**:
```
T009 (action injection test)
T010 (result persistence test)
T011 (validation test)         ← all in different test files, run in parallel
T012 (idempotency test)
T013 (endgame test)
```

**Phase 3 implementation parallel group** (after T014 completes):
```
T015 + T016 (delta computation + result persistence — same file, sequential)
T017 (API validation — different file, parallel with T015-T016)
T018 (idempotency — different file, parallel with T015-T016)
```

**Cross-story parallel** (after Phase 2):
```
Phase 3 (US1) ← sequential, MVP
Phase 6 (US4) ← can run in parallel with US1 (routing is independent)
Phase 7 (US5) ← can run in parallel with US1 (scenarios are independent)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational defect fixes (T004-T008)
3. Complete Phase 3: User Story 1 — core game loop (T009-T021)
4. **STOP and VALIDATE**: Create a game, submit actions, resolve ticks, see results
5. This alone makes the game playable

### Incremental Delivery

1. Setup + Foundational → Defects fixed, CI green
2. Add US1 → Game is playable with action→result loop (MVP!)
3. Add US2+US3 → Player can understand and strategize
4. Add US4 → Games survive browser refresh
5. Add US5 → Multiple scenarios available
6. Polish → Full test coverage, E2E passing

### Solo Developer Strategy (Recommended)

Work phases sequentially in priority order:
1. Phase 1 + Phase 2 (foundation) — ~2 hours
2. Phase 3 (US1 MVP) — ~4 hours
3. Phase 4 + Phase 5 (US2+US3) — ~2 hours
4. Phase 6 (US4 routing) — ~1 hour
5. Phase 7 (US5 scenarios) — ~1 hour
6. Phase 8 (polish) — ~2 hours

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests MUST fail before implementing (TDD Red-Green-Refactor per CLAUDE.md)
- Commit after each checkpoint with conventional commit format
- The engine (`src/babylon/`) is read-only — all modifications are in `web/game/` (bridge layer) and `web/frontend/src/`
