# Frontend Course-Correction Verification (spec-091, task 2)

**Verifier**: Lane-W agent, 2026-07-03, against `091-frontend-consolidation` (parent `42232a15`).
**Source of truth**: `docs/agents/babylon-frontend-paradox-course-correction.md` (7 phases) and
`docs/agents/babylon-frontend-reset-prompt.md` (16-route vision).

## Executive finding

The course-correction was written against the **old god-page** (`GameShell` + `ActionPage`).
Since then, **spec-061 rebuilt the frontend as the 16-route `pages/*` architecture** on the `bbl`
component kit. The course-correction's structural goals are therefore met by a *different*
implementation than the phases literally describe:

- The **god-page is gone** (Phase 6/7 goals achieved — `GameShell`/`RightPanel`/`BottomPanel`/
  `LensBar` deleted; one lens selector).
- The course-correction's **Phase-4/5 artifacts** (`ActionPage`+`VerbShell`+`lib/verbs`,
  `HexInspector`+`BreakdownTooltip`) were built but then **unrouted/superseded** by the 061 pages
  (`VerbPage` uses `lib/verb-config.ts`; `IntelPageV2` uses `bbl.Stat` panels). The infra exists
  and is unit-tested; wiring provenance into the live screens is **spec-093** (program §2:
  "`BreakdownTooltip` provenance on every displayed number").

## Phase-by-phase

| Phase | Goal | Verdict | Evidence |
|-------|------|---------|----------|
| **1 — Data-layer unification** | all components read `gameStore` | **MET** | `gameStore.ts` has `playerOrgs`, `fetchPlayerOrgs`, `fetchVerbTargets`, `invalidateVerbTargets`; live pages read the store via `useGameState`. The only files that fetched inline (`ActionPage`, `OrganizationsPage`) are the **deleted** legacy siblings. |
| **2 — Selector registry + BabylonScriptValue** | `lib/selectors/` scaffolding | **MET** | `lib/selectors/{types,registry,primitives,derived,gamedefines,index}.ts` + `__tests__/selectors.test.ts` (15 tests). |
| **3 — Slot primitive** | `lib/slots.tsx` | **MET** | `lib/slots.tsx` + `lib/slots.test.tsx`. |
| **4 — ActionPage → verb-config template** | config-driven verb page, no per-verb branching | **MET (structurally) — DIVERGED (impl)** | `lib/verbs/{9 configs,registry,types}` + `action/VerbShell.tsx` exist and are tested (`verbs.test.ts`, 12 tests), but the **routed** verb page is spec-061's `pages/VerbPage.tsx` (uses `lib/verb-config.ts` + `resolveTargets`, target-type-gated). The course-correction `ActionPage` (VerbShell/VERB_REGISTRY) is **unrouted** → deleted in spec-091. Registry/VerbShell infra **preserved**. |
| **5 — BreakdownTooltip + IntelPage application** | provenance tooltip on ≥3 inspector metrics | **MET (artifact) — DIVERGED (live wiring)** | `inspector/BreakdownTooltip.tsx` renders on 3 metrics in `inspector/HexInspector.tsx` (`hex.heat`, `hex.rent_level`, `hex.biocapacity`) with recursive drill-down + tests. BUT `HexInspector` is reachable only through the **deleted** legacy `IntelPage`/`Inspector`; the **live** `IntelPageV2` shows raw `bbl.Stat` values without breakdown. Live provenance wiring = **spec-093**. Infra preserved. |
| **6 — Briefing strip** | lean Briefing: map + sparklines + narrative + End Turn; no composer/full charts/graph | **MET** | `pages/BriefingPage.tsx` (148 lines): Situation-Map panel + 6 `bbl.Sparkline`s + Priority-Dispatch feed + "Take Actions" CTA. No `ActionComposer`/full `TimeSeries`/`EventLog`/`GraphView`. **Gap closed by spec-091 US2**: the map panel rendered the SVG `HexMapPlaceholder`; spec-091 promotes it to the live `DeckGLMap`. |
| **7 — Lens vs Layer consolidation** | one selector; delete `LayerControls`; remove `lensOverride` | **MET** | `LayerControls.tsx` deleted (only a comment in `DeckGLMap.test.tsx` references its removal); `mapStore.ts` header documents "Phase 7: lensOverride removed. LensBar is the sole layer selector." No `lensOverride` in source. |

## Gaps closed by spec-091

- **Phase 6 map**: `BriefingPage` promoted from `HexMapPlaceholder` (SVG) to the live `DeckGLMap`
  (US2 / FR-004).
- **Consolidation**: the unrouted Phase-4/5-era siblings (`ActionPage`, `IntelPage`, the panel
  `Inspector` cluster) that caused the two-generation confusion are deleted (US1).

## Gaps deferred (with owner-visible assignment)

- **Live provenance tooltips** (Phase-5 intent applied to `IntelPageV2`/`VerbPage`): **spec-093**
  ("provenance on every displayed number"). The `lib/selectors` + `BreakdownTooltip` +
  `HexInspector`/`NodeInspector` infra is **preserved intact** for 093 to consume.
- **Verb registry wiring** (`lib/verbs`/`VerbShell` into the live `VerbPage`): not required by
  091's gates; the 061 `VerbPage` is the working, Playwright-covered surface. Left as available
  infra; any future unification is a scoped decision, not a 091 blocker.

## Conclusion

Phases 1, 2, 3, 6, 7 are **satisfied**. Phases 4 and 5 are **satisfied at the infra level** but
their live wiring **diverged** to the spec-061 pages; the divergence is documented and the
outstanding live-wiring is correctly scheduled into spec-093. No course-correction constitutional
non-negotiable is regressed.
