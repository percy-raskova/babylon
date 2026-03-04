# Tasks: Game UI Overhaul

**Input**: Design documents from `/specs/042-game-ui-overhaul/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/action-preview.yaml

**Tests**: Integration tests included per project TDD convention (CLAUDE.md). Tests are written in the user story phase they validate, before the implementation tasks they cover.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `web/game/` (Django)
- **Frontend**: `web/frontend/src/` (React/TypeScript)
- **Tests**: `web/frontend/src/__tests__/integration/` (Vitest)

## Phase 1: Setup (Shared Type Definitions)

**Purpose**: Add all new TypeScript types and library modules that multiple user stories depend on

- [ ] T001 Add LensId, LensDefinition, EventSeverity, ClassifiedEvent, NotificationGroup, BreadcrumbEntry, IndicatorId, IndicatorThresholds, IndicatorDefinition, UIPreferences, ActionPreviewResult types to `web/frontend/src/types/game.ts` per data-model.md
- [ ] T002 [P] Create event classifier module with type-to-severity mapping table and classifyEvent() function in `web/frontend/src/lib/eventClassifier.ts` per research.md R-002
- [ ] T003 [P] Create lens definitions module with 4 lens configs (economic, political, social, strategic), indicator definitions with compute functions and thresholds, and getLensById() helper in `web/frontend/src/lib/lensDefinitions.ts` per research.md R-004 and R-009

______________________________________________________________________

## Phase 2: Foundational (Store Extensions & Shared Infrastructure)

**Purpose**: Extend Zustand stores and create shared hooks/components that MUST be complete before user story work begins

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Extend uiStore with activeLens (default: "political"), breadcrumbs (BreadcrumbEntry[]), notifications (ClassifiedEvent[]), unreadCount, notificationGroupsForTick, rightPanelWidth (default: 360), bottomPanelHeight (default: 260), pinnedIndicators (default 4 IndicatorIds), and all new actions (setActiveLens, pushBreadcrumb, popBreadcrumbTo, clearBreadcrumbs, addEvents, markEventRead, markAllEventsRead, setRightPanelWidth, setBottomPanelHeight, setPinnedIndicators, resetPreferences) in `web/frontend/src/stores/uiStore.ts` per data-model.md UIState extensions
- [ ] T005 [P] Extend mapStore with lensOverride boolean (default: false) and update setActiveLayer to set lensOverride=true in `web/frontend/src/stores/mapStore.ts` per data-model.md MapState extension
- [ ] T006 [P] Extend gameStore to accumulate ClassifiedEvent[] from tick snapshots in a bounded 500-event ring buffer by importing classifyEvent from eventClassifier and calling addEvents on uiStore after each fetchState/resolveTick in `web/frontend/src/stores/gameStore.ts` per research.md R-003
- [ ] T007 [P] Create usePersistentUI hook that syncs uiStore panel states (rightPanelWidth, rightPanelOpen, bottomPanelHeight, bottomPanelOpen, bottomTab, activeLens, pinnedIndicators) to/from localStorage key "babylon:ui-preferences" with version field for migration in `web/frontend/src/hooks/usePersistentUI.ts` per research.md R-005
- [ ] T008 [P] Create useLens hook that coordinates lens switching: sets uiStore.activeLens, sets mapStore.activeLayer to lens.primaryLayer unless lensOverride is true, and resets lensOverride on explicit lens switch in `web/frontend/src/hooks/useLens.ts` per data-model.md Lens State Machine
- [ ] T009 [P] Create IndicatorChip reusable component that displays label, formatted value, delta arrow (up/down from previous tick), and urgency color based on IndicatorThresholds (SILVER normal, warning-amber warning, CRIMSON critical) in `web/frontend/src/components/ui/IndicatorChip.tsx` per spec FR-022 and research.md R-009
- [ ] T010 Add action preview endpoint: add preview_action method to EngineBridge that computes estimated consciousness_delta, heat_delta, action_point_cost, success_probability, affected_territory_ids, and warnings without mutating graph state; add POST view function with SubmitActionSerializer validation; add URL pattern at `games/<str:game_id>/actions/preview/` in `web/game/engine_bridge.py`, `web/game/api.py`, and `web/game/urls.py` per contracts/action-preview.yaml
- [ ] T011 [P] Add MSW handler for POST `/api/games/:id/actions/preview/` returning fixture ActionPreviewResult in `web/frontend/src/test/handlers.ts` and add makeActionPreview() factory to `web/frontend/src/test/fixtures.ts`
- [ ] T012 Update test setup to reset new uiStore fields (activeLens, breadcrumbs, notifications, pinnedIndicators, panel sizes) and mapStore.lensOverride in afterEach block in `web/frontend/src/test/setup.ts`

**Checkpoint**: Foundation ready — all stores extended, shared hooks and components created, backend preview endpoint available. User story implementation can now begin.

______________________________________________________________________

## Phase 3: User Story 1 — Understand Game State at a Glance (Priority: P1) MVP

**Goal**: Player immediately understands simulation state (stable/tense/crisis) without clicking anything via persistent top bar indicators with urgency colors and a default choropleth map with legend

**Independent Test**: Load a game at various tick states and verify indicators show correct values with urgency-appropriate colors, and the map displays a meaningful default choropleth with legend

### Tests for User Story 1

- [ ] T013 [US1] Write integration test in `web/frontend/src/__tests__/integration/indicator-urgency.test.tsx` that: (1) renders GameShell with a snapshot at tick 1, verifies 4+ indicator chips are visible with labels and values; (2) renders with a high-heat snapshot, verifies at least one indicator shows CRIMSON urgency color; (3) renders with a stable snapshot, verifies all indicators show SILVER normal color; (4) verifies map legend is visible with layer name and color gradient

### Implementation for User Story 1

- [ ] T014 [US1] Update PersistentIndicators to render from pinnedIndicators array in uiStore, using IndicatorDefinition.compute() from lensDefinitions.ts for values and IndicatorChip for display with threshold-based urgency colors in `web/frontend/src/components/charts/PersistentIndicators.tsx`
- [ ] T015 [US1] Update TopBar to use updated PersistentIndicators, ensure tick counter and resolve button remain prominent, and add subtle background color tint that shifts based on the highest-severity indicator (normal=none, warning=faint amber, critical=faint crimson) in `web/frontend/src/components/layout/TopBar.tsx`
- [ ] T016 [US1] Verify MapLegend renders correctly for the default active layer (political lens → consciousness) with color gradient, metric name, and min/max labels — fix if needed in `web/frontend/src/components/map/MapLegend.tsx`

**Checkpoint**: Player can load any game and immediately read simulation health from 4+ urgency-colored indicators and a labeled choropleth map. US1 independently testable.

______________________________________________________________________

## Phase 4: User Story 2 — Drill Down from Map to Entity Detail (Priority: P1)

**Goal**: Player can hover a hex for tooltip, click it for territory detail, click an org within for org detail, and navigate back via breadcrumbs — all within 2 clicks of the map

**Independent Test**: Click through hover → click → detail → sub-detail chain on any territory and verify each layer adds information without losing navigation context

### Tests for User Story 2

- [ ] T017 [US2] Write integration test in `web/frontend/src/__tests__/integration/breadcrumb-navigation.test.tsx` that: (1) clicks a hex, verifies territory detail opens in right panel with breadcrumb showing "Overview > Territory Name"; (2) clicks an org within territory detail, verifies org detail opens with breadcrumb "Overview > Territory > Org Name"; (3) clicks "Territory" breadcrumb, verifies return to territory detail; (4) presses Escape, verifies panel clears and breadcrumbs empty; (5) verifies tooltip still appears on hover while detail panel is open

### Implementation for User Story 2

- [ ] T018 [P] [US2] Create Breadcrumbs component that renders the breadcrumb stack from uiStore as clickable chips (Overview > Territory > Org), with popBreadcrumbTo on click and clearBreadcrumbs on "Overview" click in `web/frontend/src/components/inspector/Breadcrumbs.tsx`
- [ ] T019 [US2] Update Inspector to render Breadcrumbs at top, route to HexInspector or NodeInspector based on last breadcrumb entry's entityType, and call pushBreadcrumb when selection changes in `web/frontend/src/components/inspector/Inspector.tsx`
- [ ] T020 [P] [US2] Update HexInspector to show territory's full state (all metrics, sector type, profile, eviction status), list all organizations present in the territory as clickable rows that call pushBreadcrumb + setSelectedNode, and show recent events affecting this territory in `web/frontend/src/components/inspector/HexInspector.tsx`
- [ ] T021 [P] [US2] Update NodeInspector to show organization/entity/institution detail with all fields, list occupied territories as clickable rows, show key figures, and display available actions for the selected org in `web/frontend/src/components/inspector/NodeInspector.tsx`
- [ ] T022 [US2] Update HexTooltip to display territory name plus top 4-6 metrics prioritized by active lens (using inspectorPriority from lensDefinitions), and show eviction warning if under_eviction is true in `web/frontend/src/components/map/HexTooltip.tsx`
- [ ] T023 [US2] Wire Escape key handler in GameShell to clearBreadcrumbs + setSelectedHex(null) + setSelectedNode(null) and verify clicking map background also clears selection in `web/frontend/src/components/layout/GameShell.tsx`

**Checkpoint**: Full drill-down chain works: hover → tooltip, click → territory detail, click org → org detail, breadcrumb navigation back. US2 independently testable.

______________________________________________________________________

## Phase 5: User Story 3 — Compose and Execute Strategic Actions (Priority: P1)

**Goal**: Player can compose actions through guided Org → Verb → Target → Preview → Confirm flow with estimated effects preview and clear feedback on unavailable options

**Independent Test**: Walk through complete action composition from org selection to confirmation, verify preview shows estimated effects, verify back navigation preserves state

### Tests for User Story 3

- [ ] T024 [US3] Write integration test in `web/frontend/src/__tests__/integration/action-preview.test.tsx` that: (1) selects an org and verb, selects target, verifies preview endpoint is called and estimated effects are displayed; (2) verifies unavailable verbs show grayed-out state with explanation tooltip; (3) verifies back navigation from preview returns to target selection with prior selections preserved; (4) verifies action submission shows immediate visual feedback

### Implementation for User Story 3

- [ ] T025 [US3] Update VerbSelector to show grayed-out styling for unavailable verbs with a tooltip explaining why each is unavailable (e.g., "Insufficient budget", "No valid targets") based on AvailableAction data in `web/frontend/src/components/action/VerbSelector.tsx`
- [ ] T026 [US3] Update ActionPreview to call POST `/api/games/:id/actions/preview/` when target is selected, display estimated_consciousness_delta, estimated_heat_delta, action_point_cost, success_probability, affected territories, and any warnings; show loading spinner during API call in `web/frontend/src/components/action/ActionPreview.tsx`
- [ ] T027 [US3] Update ActionComposer to disable all inputs and show "Resolving tick..." overlay when gameStore.loading is true (tick resolution in progress), and re-enable on completion in `web/frontend/src/components/action/ActionComposer.tsx`

**Checkpoint**: Full action flow works with preview estimates, unavailability explanations, and resolution blocking. US3 independently testable.

______________________________________________________________________

## Phase 6: User Story 5 — Navigate Between Game Lenses (Priority: P2)

**Goal**: Player can switch between Economic, Political, Social, and Strategic lenses via a single click, recontextualizing the map layer, top bar indicators, and panel content within 300ms

**Independent Test**: Switch between all 4 lenses and verify map choropleth, indicator emphasis, and inspector field priority change coherently for each

### Tests for User Story 5

- [ ] T028 [US5] Write integration test in `web/frontend/src/__tests__/integration/lens-switching.test.tsx` that: (1) clicks Economic lens button, verifies mapStore.activeLayer changes to "rent" and top indicators reorder; (2) clicks Political lens, verifies activeLayer changes to "consciousness"; (3) manually changes layer via LayerControls, verifies lensOverride is set; (4) switches lens again, verifies layer resets to lens primary (lensOverride cleared)

### Implementation for User Story 5

- [ ] T029 [US5] Create LensBar component as a horizontal bar of 4 lens buttons (Economic, Political, Social, Strategic) with icons from lucide-react, active state highlighting in GOLD, and onClick calling useLens().switchLens() in `web/frontend/src/components/layout/LensBar.tsx`
- [ ] T030 [US5] Update GameShell to render LensBar between the map area and BottomPanel, and initialize usePersistentUI hook for localStorage sync in `web/frontend/src/components/layout/GameShell.tsx`
- [ ] T031 [US5] Update TopBar to reorder PersistentIndicators based on activeLens.emphasizedIndicators (first 4-6 indicators from the active lens definition) in `web/frontend/src/components/layout/TopBar.tsx`

**Checkpoint**: All 4 lenses switch cleanly with coherent map/indicator/panel updates. US5 independently testable.

______________________________________________________________________

## Phase 7: User Story 4 — Analyze Trends Over Time (Priority: P2)

**Goal**: Player can view time-series charts with Tufte-aligned styling (data-ink ratio >0.8), select metrics, and hover for exact values

**Independent Test**: Load a game with 10+ ticks and verify charts show accurate trend lines matching tick summary data, with metric selection and hover inspection working

### Implementation for User Story 4

- [ ] T032 [US4] Update TimeSeries to apply Tufte-aligned styling: remove CartesianGrid or use very faint dashed lines, suppress redundant axis labels (show only first/last tick), use constitutional palette for series (CRIMSON for extraction, GOLD for solidarity, SILVER for mass), remove background fills/borders/shadows; add metric selector dropdown that lets player choose which metrics to chart from available IndicatorDefinitions in `web/frontend/src/components/charts/TimeSeries.tsx`
- [ ] T033 [US4] Ensure BottomPanel analytics tab renders TimeSeries with default metrics from the active lens (defaultChartMetrics from LensDefinition) and verify hover-to-inspect tooltips show exact value and tick number in `web/frontend/src/components/layout/BottomPanel.tsx`

**Checkpoint**: Charts show meaningful trends with Tufte-aligned minimal styling and metric selection. US4 independently testable.

______________________________________________________________________

## Phase 8: User Story 6 — Monitor Notifications and Events (Priority: P2)

**Goal**: Player receives tiered event notifications after tick resolution — critical events as prominent alerts requiring acknowledgment, important as feed items, informational as logged background; grouped when volume is high; each clickable to navigate to relevant entity

**Independent Test**: Resolve ticks that produce events of varying severity, verify each tier displays appropriately, verify clicking events navigates to correct entity

### Tests for User Story 6

- [ ] T034 [US6] Write integration test in `web/frontend/src/__tests__/integration/notification-flow.test.tsx` that: (1) resolves a tick with a RUPTURE event, verifies NotificationToast appears with critical styling; (2) resolves a tick with 5 HEAT_CHANGE events, verifies they are grouped into a single "5 territories..." summary; (3) clicks a notification, verifies navigation to the linked territory; (4) verifies total visible notification cards per tick never exceeds 5

### Implementation for User Story 6

- [ ] T035 [US6] Create NotificationToast component as a fixed-position overlay that renders critical ClassifiedEvents with CRIMSON border, event summary text, linked entity name, acknowledge button (calls markEventRead), and navigate button (calls pushBreadcrumb + setSelectedHex/Node) in `web/frontend/src/components/events/NotificationToast.tsx`
- [ ] T036 [US6] Update EventLog to display NotificationGroups sorted by severity (critical first), with grouped events showing count + summary, individual events showing type + tick + linked entity as clickable row; implement notification grouping logic per research.md R-006 (group when >2 of same type, max 5 visible cards) in `web/frontend/src/components/events/EventLog.tsx`
- [ ] T037 [US6] Add "notifications" tab option to BottomPanel alongside existing timeseries/events/graph tabs; render EventLog in notifications tab with unread badge count from uiStore.unreadCount in `web/frontend/src/components/layout/BottomPanel.tsx`
- [ ] T038 [US6] Wire NotificationToast rendering into GameShell: after tick resolution, if any critical events exist in notificationGroupsForTick, render NotificationToast overlay above the map in `web/frontend/src/components/layout/GameShell.tsx`

**Checkpoint**: Full notification pipeline works from tick resolution through classification, grouping, display, and entity navigation. US6 independently testable.

______________________________________________________________________

## Phase 9: User Story 7 — Visualize Network Relationships (Priority: P3)

**Goal**: Player can view the solidarity/exploitation network as a force-directed graph with edge type filtering and node-click navigation to entity detail

**Independent Test**: Open graph view with established relationships, filter by edge type, verify correct edges shown, click node to open detail panel

### Implementation for User Story 7

- [ ] T039 [US7] Update GraphView to add an edge type filter control (dropdown or button group for SOLIDARITY, EXPLOITATION, WAGES, TRIBUTE, etc.) that filters visible edges by type while keeping all nodes visible (unconnected nodes dimmed to ASH opacity); add edge hover tooltip showing relationship type, strength value, and connected entity names in `web/frontend/src/components/graph/GraphView.tsx`
- [ ] T040 [US7] Wire GraphView node clicks to pushBreadcrumb + setSelectedNode so clicking a graph node opens the same entity detail panel as the map drill-down path in `web/frontend/src/components/graph/GraphView.tsx`

**Checkpoint**: Graph visualization shows filterable network with entity navigation. US7 independently testable.

______________________________________________________________________

## Phase 10: User Story 8 — Customize UI Layout and Preferences (Priority: P3)

**Goal**: Player can resize panels, choose which indicators appear in the top bar, and all preferences persist across browser sessions via localStorage

**Independent Test**: Adjust panel sizes and indicator selections, refresh browser, verify all customizations restored

### Tests for User Story 8

- [ ] T041 [US8] Write integration test in `web/frontend/src/__tests__/integration/panel-persistence.test.tsx` that: (1) sets rightPanelWidth to 500 via uiStore, triggers usePersistentUI save, reads localStorage and verifies value persisted; (2) initializes uiStore from localStorage with saved preferences, verifies panel width is 500; (3) calls resetPreferences, verifies all values return to defaults; (4) verifies pinnedIndicators changes persist and restore

### Implementation for User Story 8

- [ ] T042 [P] [US8] Update RightPanel to support drag-to-resize via a left-edge drag handle (mousedown → mousemove tracking → setRightPanelWidth clamped between 280-600px) and read width from uiStore.rightPanelWidth instead of hardcoded 360px in `web/frontend/src/components/layout/RightPanel.tsx`
- [ ] T043 [P] [US8] Update BottomPanel to support drag-to-resize via a top-edge drag handle (mousedown → mousemove tracking → setBottomPanelHeight clamped between 180-400px) and read height from uiStore.bottomPanelHeight instead of hardcoded 260px in `web/frontend/src/components/layout/BottomPanel.tsx`
- [ ] T044 [US8] Add indicator selection popover to TopBar: a gear icon button that opens a dropdown listing all IndicatorDefinitions with checkboxes, allowing player to select 4-6 metrics to pin; save selections via setPinnedIndicators; add "Reset to Defaults" button that calls resetPreferences in `web/frontend/src/components/layout/TopBar.tsx`

**Checkpoint**: Panel resizing and indicator customization work and persist across sessions. US8 independently testable.

______________________________________________________________________

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Visual alignment, accessibility, and final quality verification

- [ ] T045 Audit all components for constitutional visual compliance: verify all colors use palette tokens (no hardcoded hex), all interactive elements have hover/focus states (VII.5), color semantics are invariant across views (VII.6), no chartjunk or decorative elements (VII.10) across all updated files in `web/frontend/src/components/`
- [ ] T046 [P] Verify WCAG AA contrast ratios (minimum 4.5:1) for all text/background combinations in the dark theme; adjust any failing combinations in `web/frontend/src/index.css` @theme tokens
- [ ] T047 [P] Add keyboard navigation support: Tab through lens buttons, indicators, and action composer steps; Enter to select; Escape to dismiss panels and clear breadcrumbs across `web/frontend/src/components/layout/` and `web/frontend/src/components/action/`
- [ ] T048 Run `mise run web:check` (tsc + eslint + prettier + vitest) and fix all errors, warnings, and test failures
- [ ] T049 Run quickstart.md validation: follow all steps in `specs/042-game-ui-overhaul/quickstart.md` in a clean environment to verify developer onboarding works

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (types must exist before stores use them) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no dependencies on other stories
- **US2 (Phase 4)**: Depends on Phase 2 — no dependencies on other stories
- **US3 (Phase 5)**: Depends on Phase 2 — uses preview endpoint from T010
- **US5 (Phase 6)**: Depends on Phase 2 — no dependencies on other stories
- **US4 (Phase 7)**: Depends on Phase 2 — benefits from US5 (lens-aware chart defaults) but works independently
- **US6 (Phase 8)**: Depends on Phase 2 — uses eventClassifier from T002
- **US7 (Phase 9)**: Depends on Phase 2 — no dependencies on other stories
- **US8 (Phase 10)**: Depends on Phase 2 — uses usePersistentUI from T007
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent after Foundation — can start first
- **US2 (P1)**: Independent after Foundation — can start in parallel with US1
- **US3 (P1)**: Independent after Foundation — can start in parallel with US1/US2
- **US5 (P2)**: Independent after Foundation — enhances US1/US2/US4 but not required by them
- **US4 (P2)**: Independent after Foundation — benefits from US5 lens defaults
- **US6 (P2)**: Independent after Foundation — enhances US2 (event navigation) but not required
- **US7 (P3)**: Independent after Foundation — shares entity navigation with US2
- **US8 (P3)**: Independent after Foundation — enhances all panel-using stories

### Within Each User Story

- Tests written and FAIL before implementation
- UI components before wiring/integration
- Core display before interaction/navigation
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel (Phase 1, different files)
- T004-T012 foundational tasks: T005, T006, T007, T008, T009, T011 can all run in parallel
- After Foundation: US1, US2, US3 can start in parallel (all P1)
- After P1 stories: US4, US5, US6 can start in parallel (all P2)
- After P2 stories: US7, US8 can start in parallel (all P3)
- Within US2: T018, T020, T021 can run in parallel (different files)
- Within US8: T042, T043 can run in parallel (different files)

______________________________________________________________________

## Parallel Example: User Story 2 (Drill-Down)

```text
# Write test first:
T017: breadcrumb-navigation integration test

# Launch parallel component creation:
T018: Create Breadcrumbs.tsx (new file)
T020: Update HexInspector.tsx (existing file)
T021: Update NodeInspector.tsx (existing file)

# Sequential wiring (depends on above):
T019: Update Inspector.tsx routing
T022: Update HexTooltip.tsx
T023: Wire Escape key in GameShell.tsx
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T012)
3. Complete Phase 3: User Story 1 (T013-T016)
4. **STOP and VALIDATE**: Load game, verify 4+ indicators with urgency colors visible
5. Deploy/demo if ready — player can read simulation health at a glance

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Overview) → Deploy/Demo (MVP!)
3. Add US2 (Drill-Down) → Deploy/Demo — player can investigate anomalies
4. Add US3 (Actions) → Deploy/Demo — player can act with preview feedback
5. Add US5 (Lenses) → Deploy/Demo — player can switch analytical perspectives
6. Add US4 (Analytics) → Deploy/Demo — player can see trends
7. Add US6 (Notifications) → Deploy/Demo — player gets tiered event alerts
8. Add US7 (Graph) → Deploy/Demo — player can see network topology
9. Add US8 (Customization) → Deploy/Demo — player can personalize layout
10. Polish → Final quality pass

### Parallel Team Strategy

With multiple developers after Foundation is complete:

- Developer A: US1 (Overview) → US5 (Lenses) → US8 (Customization)
- Developer B: US2 (Drill-Down) → US4 (Analytics) → US7 (Graph)
- Developer C: US3 (Actions) → US6 (Notifications) → Polish

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group per CLAUDE.md convention
- Stop at any checkpoint to validate story independently
- All colors must use constitutional palette tokens (VII.2) — no hardcoded hex values
- All interactive elements must have hover/focus affordances (VII.5)
- Chart styling must achieve data-ink ratio >0.8 (SC-007)
- Interaction feedback within 200ms (SC-008)
