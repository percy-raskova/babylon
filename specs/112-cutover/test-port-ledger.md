# spec-112 Test-Port Ledger — `web/frontend` deletion

**Scope**: every test in the retired app — 68 vitest files, 12 Playwright specs,
1 auth setup — dispositioned before deletion. Program 12 Phase D requirement:
*"nothing deleted whose behavior-guard didn't land."*
**Authority**: `project/programs/12-cockpit.md` (Phase D / spec-112);
ADR061; Percy's explicit go, 2026-07-10 ("finish it all" ruling, plan approved).
**Method**: full inventory sweep (read-only agent) + per-file disposition +
spot-verification of every flagged rewrite + two live parity runs (evidence below).

## Disposition counts

| Disposition | vitest | e2e | Meaning |
| --- | --- | --- | --- |
| PORTED | 19 | 6 + setup | Same guard, same-name/renamed file in `src/frontend` |
| REWRITTEN | 28 | 2 | Guard survives under a new shape; covering test named per row |
| RE-GUARDED | 2 | 0 | Constitution contracts ported in this arc (`d845c368`) |
| RETIRED | 19 | 4 | Surface deliberately not ported; authority cited per row |
| **Total** | **68** | **12** (+1 setup) | |

## Vitest ledger

### PORTED (19)

| Old (`web/frontend/src/`) | New (`src/frontend/src/`) |
| --- | --- |
| `api/client.test.ts` | `api/client.test.ts` |
| `components/action/ActionComposer.test.tsx` | `components/action/ActionComposer.test.tsx` |
| `components/charts/TimeSeries.test.tsx` | `components/timeseries/TimeseriesChart.test.tsx` |
| `components/events/EventLog.test.tsx` | `components/events/EventsFeed.test.tsx` |
| `components/LoginPage.test.tsx` | `routes/LoginRoute.test.tsx` |
| `components/map/DeckGLMap.test.tsx` | `components/map/DeckGLMap.test.tsx` |
| `components/map/mapLensGeometry.test.ts` | `components/map/mapLensGeometry.test.ts` |
| `components/map/mapLensLayers.test.ts` | `components/map/mapLensLayers.test.ts` |
| `components/map/MapModeSelector.test.tsx` | `components/map/MapModeSelector.test.tsx` |
| `lib/selectors/__tests__/selectors.test.ts` | `lib/selectors/__tests__/selectors.test.ts` |
| `lib/__tests__/eventClassifier.test.ts` | `lib/__tests__/eventClassifier.test.ts` |
| `lib/__tests__/verb-config.test.ts` | `lib/__tests__/verb-config.test.ts` |
| `lib/verbs/__tests__/payloads.test.ts` | `lib/verbs/__tests__/payloads.test.ts` |
| `lib/verbs/__tests__/verbs.test.ts` | `lib/verbs/__tests__/verbs.test.ts` |
| `observatory/__tests__/api.contract.test.tsx` | `observatory/__tests__/api.contract.test.tsx` |
| `observatory/__tests__/deep.test.tsx` | `observatory/__tests__/deep.test.tsx` |
| `observatory/__tests__/page.test.tsx` | `observatory/__tests__/page.test.tsx` (+ new `route.test.tsx`) |
| `theme/colors.test.ts` | `theme/colors.test.ts` |
| `utils/logger.test.ts` | `utils/logger.test.ts` |

### RE-GUARDED (2) — Constitution contracts, ported this arc

| Old | New | Note |
| --- | --- | --- |
| `theme/tokens.contract.test.ts` | `theme/tokens.contract.test.ts` | C1–C5 verbatim; C6 rewritten for the unified `Lens` union (`lensRampStops`), old `lensDefinitions` retired in B2. Mutation-checked. |
| `theme/type-roles.contract.test.ts` | `theme/type-roles.contract.test.ts` | Verbatim (35 role tokens + spire/solidarity accents). |

### REWRITTEN (28) — guard verified in the covering test

| Old | Covering new test(s) |
| --- | --- |
| `App.test.tsx` | `App.test.tsx` (routing rewritten for cockpit routes) |
| `components/action/TargetSelector.test.tsx` | `lib/verbs/__tests__/fetchVerbTargets.test.ts` + `components/action/TargetPicker.test.tsx` |
| `components/action/VerbSelector.test.tsx` | `components/action/VerbGrid.test.tsx` + `ActionComposer.test.tsx` |
| `components/GameList.test.tsx` | `routes/LobbyRoute.test.tsx` |
| `components/inspector/HexInspector.test.tsx` | `components/inspector/InspectorPanel.test.tsx` |
| `components/inspector/NodeInspector.test.tsx` | `components/inspector/InspectorPanel.test.tsx` |
| `components/inspector/__tests__/BreakdownTooltip.test.tsx` | `InspectorPanel.test.tsx` (breakdown asserts verified present) |
| `components/layout/__tests__/shell-v2.test.tsx` | `components/shell/AppShell.test.tsx` + `Outliner`/`RightDock`/`BottomStrip` tests |
| `components/layout/TopBar.test.tsx` | `components/shell/StatusBar.test.tsx` |
| `components/pages/briefing-map.test.tsx` | `components/shell/MapPanel.test.tsx` |
| `components/pages/event-log-page.test.tsx` | `components/events/EventsFeed.test.tsx` |
| `components/pages/pages-v2.test.tsx` | cockpit shell tests (pages concept dropped by canon) |
| `components/pages/tick-resolution-page.test.tsx` | `store/slices/timeSlice.test.ts` + e2e `end-turn-flow` |
| `components/pages/verb-page.test.tsx` | `ActionComposer.test.tsx` + e2e `verb-submit` |
| `components/wire/__tests__/wire-app.test.tsx` | `components/takeovers/wire/wire.contracts.test.ts` + `TakeoverOverlay.test.tsx` |
| `stores/gameStore.test.ts` | `store/slices/worldSlice.test.ts` + `sessionSlice.test.ts` + `store/orchestrator.test.ts` |
| `stores/mapStore.test.ts` | `store/slices/mapSlice.test.ts` |
| `stores/uiStore.test.ts` | `store/slices/uiSlice.test.ts` |
| `__tests__/integration/action-flow.test.tsx` | `store/slices/actionsSlice.test.ts` + e2e `verb-submit` |
| `__tests__/integration/error-handling.test.tsx` | `api/client.test.ts` (12 error-path asserts verified) |
| `__tests__/integration/event-log-flow.test.tsx` | `components/events/EventsFeed.test.tsx` |
| `__tests__/integration/game-lifecycle.test.tsx` | `sessionSlice.test.ts` + `routes/GameRoute.test.tsx` + e2e `real-loop` |
| `__tests__/integration/GameView.contract.test.tsx` | `store/slices/worldSlice.test.ts` |
| `__tests__/integration/map-contract.test.tsx` | `store/slices/mapSlice.test.ts` + e2e `map-lens-cycling` |
| `__tests__/integration/panel-layout.test.tsx` | shell tests + `store/slices/panels/panelFactory.test.ts` |
| `__tests__/integration/tick-resolution.test.tsx` | `store/slices/timeSlice.test.ts` + e2e `end-turn-flow` |
| `__tests__/integration/wire-contract.test.tsx` | `components/takeovers/wire/wire.contracts.test.ts` |
| `utils/__tests__/colorScale.test.ts` | `theme/colors.test.ts` (getColorScale coverage verified) + `lib/__tests__/lens.test.ts` |

### RETIRED (19) — surface deliberately not ported

Authority for the dropped surfaces: the Program 12 canon scope
(`project/programs/12-cockpit.md` — "the canon cockpit defines REQUIRED
panels"; B2/B3 port decisions) and POST_ASSESSMENT's ~20% orphaned-module
finding. Rows marked †
carry partial behavior into named tests.

| Old | Retire reason |
| --- | --- |
| `components/bbl/__tests__/bbl-primitives.test.tsx` | Old bbl primitive set replaced by cockpit `components/bbl/` (own tests) |
| `components/charts/PersistentIndicators.test.tsx` | Surface not in canon cockpit |
| `components/graph/GraphView.test.tsx` | Graph view not ported (Outliner topology deferred by canon) |
| `components/intel/__tests__/OrgDetailView.test.tsx` | Intel pages not in canon; Inspector covers org detail † (`InspectorPanel.test.tsx`) |
| `components/intel/__tests__/TerritoryDetailView.test.tsx` | Intel pages not in canon; Inspector covers territory † |
| `components/pages/intel-v2.test.tsx` | Intel page not in canon |
| `components/pages/briefing-map-errorboundary.test.tsx` | v2-page error boundary; cockpit map honest-empties instead † (`MapPanel.test.tsx`) |
| `components/action/ActionPreview.test.tsx` | Confirm-card surface dropped by the B3 composer design (direct submit + pending list) † (`VerbForm`/`ActionComposer` tests, e2e `verb-submit`) |
| `lib/slots.test.tsx` | Slots layout primitive not ported |
| `utils/graphBuilder.test.ts` | Graph surface not ported |
| `__tests__/integration/consolidation.test.ts` | spec-091 consolidation view not in canon; classifier logic † (`eventClassifier.test.ts`) |
| `__tests__/integration/contradiction-contract.test.tsx` | Dialectic surface re-shipped as takeover; contract † (`TakeoverOverlay.test.tsx` + design-sync graded previews) |
| `__tests__/integration/county-exposure-contract.test.tsx` | spec-103 US5 panel not in canon cockpit |
| `__tests__/integration/economy-contract.test.tsx` | spec-093 US5 panel superseded by `/economy/` bridge tests (`tests/integration/web/test_dashboards.py`) † |
| `__tests__/integration/endgame-contract.test.tsx` | Endgame ships as Chronicle/EndState takeover † (`TakeoverOverlay.test.tsx`) |
| `__tests__/integration/journal-alerts-contract.test.tsx` | Journal/alerts pages not in canon; events feed covers per-tick surface † |
| `__tests__/integration/objectives-contract.test.tsx` | Objectives re-shipped as dock tab † (`ObjectivesTracker` design-sync graded; panel factory tests) |
| `__tests__/integration/trade-flows-contract.test.tsx` | spec-103 trade panel not in canon cockpit (Wire BlocFlowLines carries the surface †) |
| `__tests__/integration/trade-panel-contract.test.tsx` | As above |

## Playwright ledger

| Old spec | CI canon | Disposition |
| --- | --- | --- |
| `auth.setup.ts` | setup | PORTED → `e2e/auth.setup.ts` |
| `auth.spec.ts` | yes | PORTED |
| `briefing-map-smoke.spec.ts` | yes | PORTED |
| `end-turn-flow.spec.ts` | yes | PORTED |
| `map-lens-cycling.spec.ts` | yes | PORTED |
| `real-loop.spec.ts` | yes | PORTED |
| `verb-submit.spec.ts` | yes | PORTED |
| `polling-tick-aligned.spec.ts` | no | REWRITTEN → `store/orchestrator.test.ts` (heartbeat unit) |
| `wire-50-tick.spec.ts` | no | REWRITTEN → `wire.contracts.test.ts` + `TakeoverOverlay.test.tsx` |
| `briefing-live-data.spec.ts` | no (owner-run) | RETIRED — owner-run live-data spec, briefing page not in canon |
| `orgs-live-data.spec.ts` | no (owner-run) | RETIRED — orgs page not in canon (Outliner + Inspector cover) |
| `intel-results-analysis.spec.ts` | no (owner-run) | RETIRED — intel page not in canon |
| `visual.spec.ts` | no (excluded) | RETIRED — old-app snapshot canon; cockpit visual baselines deferred to post-C3 design sessions (program C3 note) |

## Parity evidence

Two consecutive live full-suite runs bracket the cutover (Phase D
pre-condition, pragmatic reading ratified in the approved 2026-07-10 plan).

### Run 1 — pre-cutover dev HEAD

- Date/HEAD: 2026-07-10, dev @ `28683951` (all four Wave-1 lanes merged)
- Command: `cd src/frontend && npx playwright test` — webServer auto-boot
  :5174, live Django :8000 (real EngineBridge, seeded `wayne_county`),
  fresh storageState
- Result: **25 passed** (29.4s) — the 23-spec parity baseline + the two
  new C5 specs (Q/E lens-cycling, framing-county smoke); setup +
  chromium + chromium-authenticated projects

### Run 2 — post-cutover dev HEAD

- Date/HEAD: _pending (Wave 5)_
- Command: _pending_
- Result: _pending_
