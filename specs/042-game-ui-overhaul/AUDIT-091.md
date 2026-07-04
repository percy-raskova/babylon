# spec-042 Evidence Audit (per program ruling R-042)

**Auditor**: Lane-W agent (spec-091), 2026-07-03.
**Ruling**: `project/09-program-full-game.md` §1 **R-042** — "042 is audited, then closed as
superseded. 042 (Vic3 UI overhaul) is formally 0/49 but its artifacts partially shipped via specs
051/061 and the course-correction. Spec-091 opens with an evidence audit of the 49 tasks
(done-with-evidence / superseded / residual→assigned to 092/093/095). 042 is never executed
as-written."

## Method

Each of the 49 tasks (`tasks.md` T001–T049) was checked against the live `web/` tree on branch
`091-frontend-consolidation` (parent `42232a15`). Classification:

- **DONE** — the task's deliverable artifact exists and ships (file citation).
- **SUPERSEDED** — the artifact shipped but was replaced by the spec-051/061 **16-route
  architecture** (`components/pages/*` + `GameRouteShell` + `NavRail`) or by the frontend
  course-correction Phase 7 (lens/layer consolidation). The god-page shell it targeted
  (`GameShell`, `RightPanel`, `BottomPanel`, `LensBar`) has been **deleted** from the tree.
- **RESIDUAL** — not shipped / wiring incomplete; assigned to the scheduled consumer spec
  (092 Event Log + Tick Resolution, 093 Territory/Org Detail + map lenses + provenance,
  095 Endgame chronicle + Dialectic/topology).

## Headline

**042 shipped its shared LIBRARY layer** (types, `eventClassifier`, `lensDefinitions`, store
extensions, `IndicatorChip`, `PersistentIndicators`, `MapLegend`, `HexTooltip`, `TimeSeries`,
`EventLog`, `GraphView`, `NotificationToast`, the `preview_action` backend endpoint) — these
survive and are consumed by the current app. **042's god-page COMPOSITION was superseded** —
`GameShell`/`RightPanel`/`BottomPanel`/`LensBar` and their integration tests are gone, replaced by
the 16-route `pages/*` architecture (051/061) and the course-correction. Remaining panels
(notifications, analytics, graph, customization) are residual, folded into 092/093/095.

## Audit table

| Task | Deliverable | Status | Evidence / assignment |
|------|-------------|--------|-----------------------|
| T001 | New TS types (`LensId`…`ActionPreviewResult`) | **DONE** | `web/frontend/src/types/game.ts` (547 lines) |
| T002 | `eventClassifier.ts` | **DONE** | `web/frontend/src/lib/eventClassifier.ts` (`classifyEvents`) |
| T003 | `lensDefinitions.ts` (4 lenses, indicators) | **DONE** | `web/frontend/src/lib/lensDefinitions.ts` (318 lines) |
| T004 | uiStore extensions (activeLens, breadcrumbs, notifications, pinned, panel sizes) | **DONE** | `web/frontend/src/stores/uiStore.ts` |
| T005 | mapStore `lensOverride` (+ setActiveLayer sets it) | **SUPERSEDED** | Added by 042, **removed by course-correction Phase 7** — `mapStore.ts` header: "Phase 7: lensOverride removed. LensBar is the sole layer selector." |
| T006 | gameStore accumulates ClassifiedEvent ring buffer | **DONE** | `gameStore.ts:66-67` (`classifyEvents` → `useUIStore.addEvents`) |
| T007 | `usePersistentUI` hook | **DONE** | `web/frontend/src/hooks/usePersistentUI.ts` |
| T008 | `useLens` hook | **DONE** | `web/frontend/src/hooks/useLens.ts` |
| T009 | `IndicatorChip` component | **DONE** | `web/frontend/src/components/ui/IndicatorChip.tsx` |
| T010 | `preview_action` backend endpoint | **DONE** | `engine_bridge.py:1769`, `api.py:715`, `urls.py:74` (`games/<id>/actions/preview/`) |
| T011 | MSW handler + fixture for preview | **SUPERSEDED** | No `preview` handler in `src/test/handlers.ts`; the `action-preview.test.tsx` was removed. Backend endpoint is covered by `tests/unit/web`. |
| T012 | Test-setup resets new store fields | **DONE** | `web/frontend/src/test/setup.ts` (stores reset in afterEach) |
| T013 | `indicator-urgency` integration test (GameShell) | **SUPERSEDED** | File **absent**; GameShell deleted. Indicator display covered by `PersistentIndicators.test.tsx` + `TopBar.test.tsx`. |
| T014 | `PersistentIndicators` from pinned array | **DONE** | `web/frontend/src/components/charts/PersistentIndicators.tsx` |
| T015 | TopBar severity tint | **SUPERSEDED** | god-page TopBar composition; live shell is `GameRouteShell` + `TopBarV2.tsx`. `TopBar.tsx` retained/tested. |
| T016 | `MapLegend` for default layer | **DONE** | `web/frontend/src/components/map/MapLegend.tsx` |
| T017 | `breadcrumb-navigation` test | **SUPERSEDED** | File **absent**; drill-down is now route-based (`IntelPageV2`). |
| T018 | `Breadcrumbs` component | **SUPERSEDED** | `inspector/Breadcrumbs.tsx` shipped, but only consumed by the legacy `Inspector` — **deleted in spec-091** with the god-page cluster. |
| T019 | `Inspector` routing (panel drill-down) | **SUPERSEDED** | Panel `Inspector` replaced by route `/games/:id/intel/:targetType/:targetId` → `IntelPageV2`; **deleted in spec-091**. |
| T020 | `HexInspector` full territory detail | **DONE** (artifact) → **RESIDUAL (wiring) → 093** | `inspector/HexInspector.tsx` exists (with `BreakdownTooltip` provenance on 3 metrics) but is unrouted; live Territory Detail + provenance-on-every-number is **spec-093** (program §2). |
| T021 | `NodeInspector` org/entity detail | **DONE** (artifact) → **RESIDUAL (wiring) → 093** | `inspector/NodeInspector.tsx` exists, unrouted; Org Detail is **spec-093**. |
| T022 | `HexTooltip` lens-prioritized | **DONE** | `web/frontend/src/components/map/HexTooltip.tsx` (consumed by `DeckGLMap`) |
| T023 | Escape handler in GameShell | **SUPERSEDED** | GameShell deleted. |
| T024 | `action-preview` integration test | **SUPERSEDED** | File **absent**; verb flow is `VerbPage` (061). |
| T025 | `VerbSelector` unavailable styling | **SUPERSEDED** | `action/VerbSelector.tsx` shipped but the composer cluster is unrouted; live verbs = `VerbPage` (`lib/verb-config.ts`, `DISABLED_VERBS`). |
| T026 | `ActionPreview` calls preview endpoint | **SUPERSEDED** | `action/ActionPreview.tsx` shipped, unrouted; preview UI folds into later verb work. |
| T027 | `ActionComposer` resolving overlay | **SUPERSEDED** | `action/ActionComposer.tsx` shipped, unrouted. |
| T028 | `lens-switching` test (lensOverride) | **SUPERSEDED** | File **absent**; lensOverride removed (Phase 7). |
| T029 | `LensBar` component | **SUPERSEDED** | `LensBar.tsx` **deleted** (Phase 7 — lens is the sole selector via `useLens`). |
| T030 | GameShell renders LensBar | **SUPERSEDED** | GameShell + LensBar deleted. |
| T031 | TopBar reorders by lens | **SUPERSEDED** | god-page composition removed. |
| T032 | `TimeSeries` Tufte styling + metric select | **DONE** (artifact) → **RESIDUAL (wiring) → 093** | `web/frontend/src/components/charts/TimeSeries.tsx` exists; full analysis wiring is `AnalysisPage`/lens work (093). |
| T033 | BottomPanel analytics tab | **SUPERSEDED** | BottomPanel deleted; analytics is the `/analysis` route (`AnalysisPage`). |
| T034 | `notification-flow` test | **RESIDUAL → 092** | File **absent**; event/notification surface is **spec-092**. |
| T035 | `NotificationToast` | **DONE** (artifact) → **RESIDUAL (wiring) → 092** | `events/NotificationToast.tsx` exists; tick-resolution/toast wiring is **092**. |
| T036 | `EventLog` grouped notifications | **DONE** (artifact) → **RESIDUAL (wiring) → 092** | `events/EventLog.tsx` (+ test) exists; `/log` route still renders "coming soon" (App.tsx) → **092**. |
| T037 | BottomPanel notifications tab | **SUPERSEDED** | BottomPanel deleted. |
| T038 | NotificationToast in GameShell | **SUPERSEDED → 092** | GameShell deleted; toast-on-tick is **092**. |
| T039 | `GraphView` edge-type filter | **DONE** (artifact) → **RESIDUAL (wiring) → 095** | `graph/GraphView.tsx` exists; live topology/dialectic surface is **spec-095** (Dialectic screen). |
| T040 | GraphView node-click nav | **RESIDUAL → 095** | topology/dialectic navigation is **095**. |
| T041 | `panel-persistence` test | **SUPERSEDED** | File **absent**; panel-resize model replaced by the route architecture. `panel-layout.test.tsx` covers the new layout. |
| T042 | RightPanel drag-resize | **SUPERSEDED** | RightPanel deleted. |
| T043 | BottomPanel drag-resize | **SUPERSEDED** | BottomPanel deleted. |
| T044 | TopBar indicator-selection popover | **RESIDUAL → 093** | Not shipped; indicator customization rides with the detail/analysis surfaces (**093**); a deeper customization pass is X-layer (experience). |
| T045 | Constitutional visual compliance audit | **SUPERSEDED → 090** | Palette/token compliance was executed by **spec-090** (Cold Collapse) + its `tokens.contract.test.ts`. |
| T046 | WCAG AA contrast | **RESIDUAL → 093** | Verified per-surface by each consuming spec; the map/detail surfaces land in 093. (Deeper a11y is X-layer.) |
| T047 | Keyboard navigation | **RESIDUAL → 093** | Route-level keyboard nav rides with the detail surfaces (093); full a11y is X-layer. |
| T048 | `mise run web:check` green | **DONE** (ongoing gate) | `web:check` is the standing CI gate (Vitest 357/357 at parent). |
| T049 | quickstart.md validation | **SUPERSEDED** | 042 quickstart pertains to the superseded god-page; not re-validated (spec closed). |

## Summary counts

- **DONE (artifact shipped)**: T001, T002, T003, T004, T006, T007, T008, T009, T010, T012, T014,
  T016, T022, T048 (+ artifact-shipped-then-residual-wiring: T020, T021, T032, T035, T036, T039).
- **SUPERSEDED**: T005, T011, T013, T015, T017, T018, T019, T023, T024, T025, T026, T027, T028,
  T029, T030, T031, T033, T037, T038, T041, T042, T043, T045, T049.
- **RESIDUAL**: → **092**: T034, T035(wiring), T036(wiring), T038. → **093**: T020(wiring),
  T021(wiring), T032(wiring), T044, T046, T047. → **095**: T039(wiring), T040.

## Disposition

Per **R-042**, spec-042 is **CLOSED AS SUPERSEDED** — never executed as-written. Its library layer
lives on in the 16-route app; its god-page composition is gone; its residual panels are scheduled
into 092/093/095 above. `specs/042-game-ui-overhaul/spec.md` is marked superseded.
