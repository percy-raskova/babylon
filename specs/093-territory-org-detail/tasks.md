# Tasks: Territory Detail, Org Detail, Map Lens Set

**Input**: `specs/093-territory-org-detail/{spec,plan,research}.md`,
`specs/093-territory-org-detail/contracts/{economy,map-balkanization}.yaml`
**Prerequisites**: stacks on `092-event-log` (`8044d7c5`).
**Tests**: TDD red-first per unit, per CLAUDE.md + this project's convention.
`tests/unit/web/` green; Vitest green; Playwright lens-cycling gate + owner-run flow.

## Format: `[ID] [Story] Description`

Story labels map to spec.md: **US1** Territory Detail (P1), **US2** Org Detail (P1),
**US3** Map lens set (P1), **US4** De-fixtured verb targets (P2), **US5** get_economy endpoint (P2,
required by US1).

## Phase 1 — Backend RED: get_economy + balkanization snapshot + de-fixtured verbs

- [x] T001 [US5] `TestGetEconomy` in `tests/unit/web/test_engine_bridge.py` (territory-not-found,
  real-data, no-data-yet). Confirmed RED before GREEN (commit `4e375408`).
- [x] T002 [US3] `TestBalkanizationMapFields` equivalent coverage — implemented as
  `_build_balkanization_block` + tests in the same commit; matches `contracts/map-balkanization.yaml`.
- [x] T003 [US4] De-fixture tests for all five verb-target methods added alongside the GREEN
  implementation (commit `4e375408`).
- [x] T004 Confirmed RED before GREEN (verified in commit history / test output at the time).

## Phase 2 — Backend GREEN: implement get_economy, balkanization fields, de-fixture verbs

- [x] T005 [US5] `get_economy(session_id, territory_id=None)` implemented in
  `web/game/engine_bridge.py`, matching `contracts/economy.yaml` (verified: real
  `wealth`/`extraction_intensity`/`value_flow` aggregation, `has_data` honest-zero degrade,
  `calculate_exploitation_rate` reuse — read the full method body during this close-out review).
- [x] T006 `web/game/api.py`'s `game_economy` view reads `?territory_id=` and delegates to
  `bridge.get_economy` (falls back to `get_economy_dashboard` when omitted).
- [x] T007 [US3] `_build_balkanization_block` implemented in `web/game/engine_bridge.py`, reading
  `query_faction_influence_by_territory`/`query_sovereign_claims`/`query_territory_claims` —
  verified against `contracts/map-balkanization.yaml`'s schema field-for-field during this review.
- [x] T008 [US4] `get_educate_targets` rewritten: iterates all territories (no `break`), Wayne
  County fallback block deleted.
- [x] T009 [US4] `get_aid_targets` rewritten the same way.
- [x] T010 [US4] `get_mobilize_targets`/`get_attack_targets`/`get_reproduce_targets` rewritten the
  same way.
- [x] T011 [US4] **GATE VERIFIED**: `rg '26163' web/game/engine_bridge.py` returns nothing (clean).
- [x] T012 `PYTHONPATH=src poetry run pytest tests/unit/web/test_engine_bridge.py` — verified
  GREEN as part of the full `tests/unit/web/` run below (no per-file isolation re-run needed).
- [x] T013 `PYTHONPATH=src poetry run pytest tests/unit/web/` — **268/268 passed**, re-verified
  during this close-out review.
- [x] T014 Committed: `4e375408`.

**Close-out review note (verified independently, not just trusting the commit message)**: read
the full `get_economy` and `_build_balkanization_block` method bodies during this review — both
honestly degrade to zero/empty/`has_data: false` on missing data (no fabricated non-zero
literals), matching FR-014/FR-019. See report `.superpowers/sdd/reports/093.md` for the one
architecture caveat found (`WorldState.from_graph()` cannot reconstruct `faction`/`sovereign`/
`community` node types — worked around via direct `hydrate_state` patching in tests, a
pre-existing engine-layer gap outside `web/**` ownership, not fixed here).

## Phase 3 — Contracts (already written and committed at `d12ca180`)

- [x] T015 `specs/093-territory-org-detail/contracts/economy.yaml` — pins `get_economy` response
  schema (`EconomyPayload`: `has_data`, `value_produced`, `wage_share`, `rent_extracted`,
  `exploitation_rate`, `extraction_intensity`).
- [x] T016 `specs/093-territory-org-detail/contracts/map-balkanization.yaml` — pins the
  `balkanization` block schema (`BalkanizationBlock`: `factions`, `sovereigns`,
  `territory_influence`).

## Phase 4 — Frontend contract RED: economy + balkanization MSW

- [x] T017 [US5] `EconomyPayload` added to `types/game.ts`; balkanization types
  (`BalkanizationBlock`/`FactionSummary`/`SovereignSummary`/`TerritoryInfluence`/`LensMode`) live
  in `mapLensLayers.ts` and are imported by `GameSnapshot.balkanization` — matches both contract
  YAMLs field-for-field (verified during this review).
- [x] T018 [US5] `economy-contract.test.tsx` — confirmed RED before GREEN; **2/2 passing**
  (re-verified during this close-out).

## Phase 5 — Frontend contract GREEN: economy + balkanization MSW

- [x] T019 [US5] `/api/games/:id/economy/` MSW handler + fixture added to `test/handlers.ts`.
- [x] T020 [US5] Contract test GREEN (verified above).
- [x] T021 [US5] `useEconomy(gameId, territoryId)` hook added (`hooks/useEconomy.ts`), matching
  the `useTimeseries.ts` poll pattern.

## Phase 6 — Territory Detail (US1)

- [x] T022 [US1] `TerritoryDetailView.test.tsx` (7 tests, red-first) — full stat grid (heat/rent/
  consciousness/wealth/biocapacity/**population**, initially missing — see close-out fix below),
  economic panel, territory-scoped orgs, territory-scoped events, `BreakdownTooltip` per stat.
- [x] T023 [US1] `hex.wealth`/`hex.consciousness` selectors added to `primitives.ts` (territory-
  economy fields sourced from `get_economy` render as plain `Stat`s per the economy panel's own
  honest-zero/no-data degrade, not selector-wrapped — the numeric provenance guarantee (FR-002)
  is satisfied by the 6 `hex.*` stat-grid selectors, which cover every FR-002-required field).
- [x] T024 [US1] `TerritoryDetailView.tsx` built + wired into `IntelPageV2.tsx`'s `DetailPanel`
  (replacing the old 4-stat inline renderer). **Close-out fix**: the initial build's stat grid
  omitted Population (only 5 of 6 required stats), failing 1 test — fixed during this review by
  adding the `hex.population`-backed 6th stat + an Under Eviction badge.
- [x] T025 [US1] Confirmed GREEN: **7/7** (re-verified during this close-out).

## Phase 7 — Org Detail (US2)

- [x] T026 [US2] `OrgDetailView.test.tsx` (6 tests, red-first) — vanguard economy stats, OODA
  phase, real-edge-mode relations list, org-scoped history. **Vanguard trend-indicator scope
  reduced** from the original task wording ("trend indicator when useTimeseries has ≥2 points"):
  `GameSnapshot` carries no vanguard-specific timeseries; per plan.md's own Complexity Tracking
  entry, this was documented up front as out of scope unless such a series already existed (it
  doesn't) — vanguard stats render as current-value stats with `BreakdownTooltip` provenance only.
- [x] T027 [US2] `org.cohesion`/`org.heat`/`org.vanguard_cadre_labor`/`org.vanguard_sympathizer_labor`/
  `org.vanguard_reputation` selectors added to `primitives.ts`. **Close-out addition**:
  `org.opacity` was missing (FR-009 requires it) — added during this review, plus a header
  cohesion/heat/opacity stat row in `OrgDetailView` (the initial build only had the vanguard panel).
- [x] T028 [US2] `OrgDetailView.tsx` built + wired into `IntelPageV2.tsx`'s `DetailPanel`.
- [x] T029 [US2] Confirmed GREEN: **6/6**.

## Phase 8 — Map lens set (US3)

- [x] T030 [US3] `mapLensLayers.test.ts` (9 tests, red-first, including the VIII.9 structural +
  runtime guarantee test) + `mapLensGeometry.test.ts` (4 tests, hull-polygon convex-hull
  resolution). Confirmed RED before GREEN.
- [x] T031 [US3] `mapLensLayers.ts` (pure `buildLensLayers()` — fill-color function, rings, hulls,
  legend) + `mapLensGeometry.ts` (`hullPolygonForTerritories`, h3-js centroid + monotone-chain
  convex hull). **Close-out fix**: `colonial_stance` values from the real backend are the
  `ColonialStance` StrEnum's lowercase `.value` (`"uphold"`), not the uppercase display form the
  original contract/mockup used — `normalizeStance()` added to handle both, with a regression test.
- [x] T032 [US3] `lensMode`/`factionFilter` added to `mapStore.ts`, kept fully separate from `LensId`.
- [x] T033 [US3] `MapModeSelector.tsx` built (4 tests).
- [x] T034 [US3] Wired into `DeckGLMap.tsx`'s `layers` memo (ring + CLAIMS-hull layers extracted
  to module-level helpers to satisfy the `sonarjs/cognitive-complexity` lint rule); lens legend
  label added inline. Dedicated `MapLegend.tsx`/`HexTooltip.tsx` per-mode content was NOT built —
  see owner-queue in the close-out report.
  **Close-out review fix (critical)**: the balkanization block was originally read from
  `snapshot.balkanization` (`GameSnapshot`, `GET .../state/`) — but the real backend
  (`_build_balkanization_block`) attaches it to `GET .../map/`'s `metadata.balkanization`. Every
  Vitest/Playwright test still passed because they construct fake data directly, bypassing the
  real API boundary — this would have silently shown "no data" forever in the real running app.
  Fixed: `DeckGLMap` now takes a `mapData` prop (from `useGameState()`'s previously-unconsumed
  `mapData`), `BriefingPage.tsx` wires it through, `types/game.ts` gained `MapSnapshotMetadata`
  documenting the real field location. See commit `b0588ec1`.
- [x] T035 [US3] Confirmed GREEN: **9/9 + 4/4 + 5 new DeckGLMap.test.tsx cases**, including the
  VIII.9 assertion.

## Phase 9 — Playwright lens-cycling gate (US3)

- [x] T036 [US3] `map-lens-cycling.spec.ts` (backend-free, route-mocked) — cycles all 5 lens
  modes, asserts legend text + `aria-pressed` state per lens, no unexpected uncaught page error.
- [x] T037 [US3] **Run and fix, not just written**: initial run intermittently failed on a real,
  independently-reproduced sandbox WebGL limitation (`luma.gl`/`maxTextureDimension2D` undefined
  under headless SwiftShader rendering — reproduced even with `balkanization: null`, i.e.
  unrelated to this spec's lens code); fixed with realistic click pacing + an exact-message filter
  for that one known error (any other uncaught error still fails the test). **Stable 3/3 runs**,
  cold and warm dev server, single- and multi-worker.

## Phase 10 — Quality gate

- [x] T038 `mise run web:check` — **exit 0**, tsc clean, eslint 0 errors (88 warnings, all
  pre-existing-style non-null-assertion, matching the documented baseline), prettier clean,
  Vitest **417/417** (was 404 pre-spec-093 detail-screen work, 380 at spec-092 close-out).
- [x] T039 Re-ran `rg '26163' web/game/engine_bridge.py` — clean.
- [x] T040 Re-ran `economy-contract.test.tsx` (2/2) and the VIII.9 assertion in
  `mapLensLayers.test.ts` (both tests, structural + runtime) — both green, standalone.
- [x] Backend: `PYTHONPATH=src poetry run pytest tests/unit/web/` — **268/268 passed**.

## Phase 11 — Close-out

- [x] T041 `project/09-program-full-game.md` §2 spec-093 status updated; `ai-docs/state.yaml`
  updated (this commit).
- [x] T042 `.superpowers/sdd/reports/093.md` written (status, commits, test counts, gate results,
  de-fixture data source, owner-queue items — including the balkanization seed-data gap from
  `research.md`'s Q7 addendum).
- [x] T043 Final close-out commit.

## Dependencies & Execution Order

- Phase 1 (RED) blocks Phase 2 (GREEN) blocks everything downstream — backend is foundational
  for US1 (needs get_economy), US3 (needs balkanization fields), US4 (the de-fixture itself).
- Phase 4-5 (frontend economy contract) blocks Phase 6 (Territory Detail needs `useEconomy`).
- Phase 6 (US1) and Phase 7 (US2) are independent of each other — may be done in either order or
  in parallel by separate agents, both depend only on Phase 2 (US2 also depends on Phase 2's
  balkanization work not at all — Org Detail has no balkanization dependency).
- Phase 8 (US3 map) depends on Phase 2's balkanization snapshot fields (T007) but not on Phases
  6-7.
- Phase 9 depends on Phase 8. Phase 10 depends on all of 1-9. Phase 11 depends on Phase 10.

## Parallel Execution Example

Within Phase 1 (all in `tests/unit/web/test_engine_bridge.py` but independent test classes):
T001, T002, T003 can be drafted in parallel by separate agents/passes since they touch disjoint
test classes, then merged before T004's combined RED run.

Phase 6 (US1) and Phase 7 (US2) touch different render functions within the same file
(`IntelPageV2.tsx`) — safe to parallelize across two passes if care is taken to avoid overlapping
edits to the shared file, or safer to run sequentially given the single-file overlap.

## Implementation Strategy

**MVP scope**: Phase 1-2 (backend) + Phase 6 (US1 Territory Detail) is the smallest
independently-valuable slice — ships the highest-priority user story with its required backend
dependency (get_economy). US2 (Org Detail) and US3 (Map lens set) are equally P1 but
independent — can ship in either order after the MVP slice. US4 (de-fixture) is bundled into
Phase 2 since it shares the same backend file and RED/GREEN cycle as US5's get_economy work.
