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

- [ ] T001 [US5] Add `TestGetEconomy` to `tests/unit/web/test_engine_bridge.py`: territory-not-found
  case, real-data case (node with `wealth`/`extraction_intensity` + incident EXTRACTIVE edge),
  no-data-yet case (`has_data: false`, honest zeros). Confirm RED against the current `{}` stub.
- [ ] T002 [US3] Add `TestBalkanizationMapFields` to `tests/unit/web/test_engine_bridge.py`:
  `get_map_snapshot` output includes a `balkanization` block (factions/sovereigns/
  territory_influence) built from `query_faction_influence_by_territory`/`query_sovereign_claims`/
  `query_territory_claims`, matching `contracts/map-balkanization.yaml`'s `BalkanizationBlock`
  schema. Confirm RED (field absent today).
- [ ] T003 [US4] Add `TestDefixturedVerbTargets` to `tests/unit/web/test_engine_bridge.py` covering
  all five methods (`get_educate_targets`, `get_aid_targets`, `get_mobilize_targets`,
  `get_attack_targets`, `get_reproduce_targets`): (a) org with multiple real territories — assert
  ALL are represented, not just the first; (b) org with zero territories — assert an honestly
  empty target list, no Wayne County fallback; (c) assert no returned field equals a hardcoded
  literal that also appears in the current fixture blocks (`"Wayne County"`, `"territory-26163"`,
  `0.25`/`0.55`/`0.20` r/l/f literals, `0.45` avg_agitation literal, `0.12` education_pressure
  literal). Confirm RED against current fixture behavior.
- [ ] T004 Run `PYTHONPATH=src poetry run pytest tests/unit/web/test_engine_bridge.py -k
  "GetEconomy or BalkanizationMapFields or DefixturedVerbTargets"` and confirm all new tests FAIL
  for the expected reason (stub/fixture, not a setup error).

## Phase 2 — Backend GREEN: implement get_economy, balkanization fields, de-fixture verbs

- [ ] T005 [US5] Implement `get_economy(session_id, territory_id=None)` in
  `web/game/engine_bridge.py` (near the `get_economy_dashboard` stub, line ~442): when
  `territory_id` given, aggregate `wealth`/`extraction_intensity` from nodes whose
  `territory_ids` include it, sum `value_flow` from incident `EXTRACTIVE`/`ANTAGONISTIC` edges,
  compute `exploitation_rate` via `calculate_exploitation_rate`
  (`src/babylon/formulas/unequal_exchange.py`), return `has_data: false` + honest zeros when no
  node/edge references the territory. Matches `contracts/economy.yaml`.
- [ ] T006 Update `web/game/api.py`'s `game_economy` view (line ~475) to read an optional
  `?territory_id=` query param and pass it through to `bridge.get_economy_dashboard`
  (or the new `get_economy` method — keep the URL/view name `game_economy` unchanged per
  plan.md's "no new routes expected").
- [ ] T007 [US3] Add balkanization block to `get_map_snapshot` in `web/game/engine_bridge.py`
  (near line ~218): for each territory with `>0` INFLUENCES edges, call
  `graph.query_faction_influence_by_territory(tid)`; derive `dominant_faction_id` (top row),
  `contested` (top-two influence delta below threshold — name the constant, cite
  `BalkanizationDefines.secession_influence_threshold` as the closest grounded reference even if
  not reused verbatim), `current_sovereign_id` (top row of `query_territory_claims(tid)`),
  `habitability` (`biocapacity / max_biocapacity`, clamped `[0,1]`). For each Sovereign node, call
  `query_sovereign_claims(sovereign_id)` to build `claimed_territory_ids`. Shape matches
  `contracts/map-balkanization.yaml`'s `BalkanizationBlock`.
- [ ] T008 [US4] Rewrite `get_educate_targets` (`web/game/engine_bridge.py:977`) to iterate ALL of
  `org_data.get("territory_ids", [])` (remove the `break` after first match), read real community
  `TernaryConsciousness` (`r`/`l`/`f` graph node attrs on `_node_type == "community"` nodes
  overlapping the territory) instead of the hardcoded `0.25/0.55/0.20` literals, read real
  `SocialClass.agitation` instead of the hardcoded `0.45` `avg_agitation` literal. Delete the
  `"Wayne County"` / `"territory-26163"` fallback block entirely; return an empty `targets` list
  (with an `unavailable_communities` explanatory entry) when the org has no territories.
- [ ] T009 [US4] Rewrite `get_aid_targets` (`engine_bridge.py:1119`) the same way: iterate all
  territories, derive `population_targets`/`org_targets` from real graph nodes located in each
  territory, delete the Wayne County fallback, honest-empty when no territories.
- [ ] T010 [US4] Rewrite `get_mobilize_targets` (`engine_bridge.py:1281`), `get_attack_targets`
  (`engine_bridge.py:1341`), and `get_reproduce_targets` (`engine_bridge.py:1563`) the same way:
  iterate all territories, derive targets from real graph state, delete any Wayne County /
  FIPS-26163 fallback, honest-empty when no territories.
- [ ] T011 [US4] Run `rg '26163' web/game/engine_bridge.py` and confirm it returns nothing (or only
  a real query-parameter usage, never a fixture literal). **This is a hard GATE — do not proceed
  until clean.**
- [ ] T012 Run `PYTHONPATH=src poetry run pytest tests/unit/web/test_engine_bridge.py` and confirm
  all tests (including T001-T003's new suites) are GREEN.
- [ ] T013 Run `PYTHONPATH=src poetry run pytest tests/unit/web/` (full suite) GREEN;
  `poetry run ruff check web/game/engine_bridge.py --fix`; `poetry run ruff format
  web/game/engine_bridge.py`; `poetry run mypy web/game/engine_bridge.py --strict` clean.
- [ ] T014 Commit via `mise run commit -- "feat(web): get_economy + balkanization map fields +
  de-fixture 5 verb-target endpoints (spec-093 backend)"`.

## Phase 3 — Contracts (already written and committed at `d12ca180`)

- [x] T015 `specs/093-territory-org-detail/contracts/economy.yaml` — pins `get_economy` response
  schema (`EconomyPayload`: `has_data`, `value_produced`, `wage_share`, `rent_extracted`,
  `exploitation_rate`, `extraction_intensity`).
- [x] T016 `specs/093-territory-org-detail/contracts/map-balkanization.yaml` — pins the
  `balkanization` block schema (`BalkanizationBlock`: `factions`, `sovereigns`,
  `territory_influence`).

## Phase 4 — Frontend contract RED: economy + balkanization MSW

- [ ] T017 [US5] Add `EconomyPayload`, `BalkanizationBlock`, `FactionInfluence`, `SovereignClaim`,
  `ColonialStance` types to `web/frontend/src/types/game.ts`, matching the two contract YAMLs
  field-for-field.
- [ ] T018 [US5] [P] Write `web/frontend/src/__tests__/integration/economy-contract.test.tsx`
  (red-first): fetch `/api/games/:id/economy/?territory_id=...` and assert the response matches
  `EconomyPayload`'s shape. Confirm RED (no MSW handler yet → request fails / unmocked).

## Phase 5 — Frontend contract GREEN: economy + balkanization MSW

- [ ] T019 [US5] Add `/api/games/:id/economy/` (territory_id-aware) and balkanization-extended
  `/api/games/:id/map/` handlers + fixtures to `web/frontend/src/test/handlers.ts`.
- [ ] T020 [US5] Confirm T018's contract test is GREEN.
- [ ] T021 [US5] [P] Add a `useEconomy(gameId, territoryId)` hook in
  `web/frontend/src/hooks/useEconomy.ts` (poll pattern matching `useTimeseries.ts`) with its own
  test.

## Phase 6 — Territory Detail (US1)

- [ ] T022 [US1] Write `web/frontend/src/components/pages/__tests__/intel-v2.test.tsx` additions
  (red-first): Territory Detail renders heat/rent/consciousness/wealth/biocapacity/population/
  eviction status from the snapshot; renders the economic panel from `useEconomy`; lists only
  organizations whose `territory_ids` include this territory; lists only events scoped to this
  territory; shows a not-found state for an unknown territory ID; every stat opens a
  `BreakdownTooltip` breakdown. Confirm RED against today's minimal inline renderer.
- [ ] T023 [US1] Add `territory.economy.*` selectors (value_produced, wage_share, rent_extracted,
  exploitation_rate, extraction_intensity) to `web/frontend/src/lib/selectors/primitives.ts` /
  `derived.ts`, registered in the selector registry, each with a real `SourceRef` (no
  `"gamedefines"`/`"derived"` source faked as `"snapshot_field"`).
- [ ] T024 [US1] Upgrade `IntelPageV2.tsx`'s `TerritoryDetail` renderer (lines 157-174) into a full
  detail view per `design/mockups/ui_kits/webapp/TerritoryDetail.jsx`'s layout: stat grid, economic
  panel, territory-scoped org list, territory-scoped recent events, `BreakdownTooltip` wrapping
  every numeric stat, not-found state.
- [ ] T025 [US1] Confirm T022's tests are GREEN.

## Phase 7 — Org Detail (US2)

- [ ] T026 [US2] Write `intel-v2.test.tsx` additions for Org Detail (red-first): vanguard economy
  block (cadre labor/sympathizer labor/reputation/heat) with trend indicator when
  `useTimeseries` has ≥2 points and a graceful "insufficient history" state otherwise; relations
  list derived from real edge `mode` (not a random ally/hostile label); org-scoped recent events;
  `BreakdownTooltip` on every stat. Confirm RED.
- [ ] T027 [US2] Add `org.vanguard.*` selectors to the selector system (cadre_labor,
  sympathizer_labor, reputation, heat, budget), each with a real `SourceRef`.
- [ ] T028 [US2] Upgrade `IntelPageV2.tsx`'s `OrgDetail` renderer (lines 176-188) into a full
  detail view per `design/mockups/ui_kits/webapp/OrgDetail.jsx`'s layout: vanguard economy block
  with trend indicators, OODA phase, relations list, org-scoped event history,
  `BreakdownTooltip` wrapping every numeric stat.
- [ ] T029 [US2] Confirm T026's tests are GREEN.

## Phase 8 — Map lens set (US3)

- [ ] T030 [US3] Write `web/frontend/src/components/map/__tests__/mapLensLayers.test.tsx`
  (red-first): for each of the 5 lens modes (stance/heat/habitability/faction/collapse), the
  layer-builder function produces a materially different `getFillColor`/layer set for the same
  input snapshot; a CLAIMS-hull layer is built ONLY from `SovereignSummary.claimed_territory_ids`
  data; **the VIII.9 assertion**: when the builder is called with a snapshot whose
  `hyperedges`/`HyperedgeState` data is populated, no hull/polygon/path layer is ever constructed
  from that data (assert on the constructed layer list's data source, not just visual output).
  Confirm RED (module doesn't exist yet).
- [ ] T031 [US3] Extract `web/frontend/src/components/map/mapLensLayers.ts`: a pure function
  `buildLensLayers(snapshot, lensMode, factionFilter?)` returning the deck.gl layer array for the
  active lens (stance fill + concentric rings, heat fill, habitability fill, faction-filter fill +
  desaturation, collapse-mode contested/transition highlighting) plus the CLAIMS-hull layer
  (client-side convex hull over `claimed_territory_ids` centroids) and state-boundary outline
  layer. Never reads `hyperedges`/`HyperedgeState`.
- [ ] T032 [US3] Add `lensMode` (+ `factionFilter`) state to `web/frontend/src/stores/mapStore.ts`,
  distinct from the existing `LensId` analytical-lens concept (per spec Assumptions — do not
  rename or remove `LensId`).
- [ ] T033 [US3] Add `web/frontend/src/components/map/MapModeSelector.tsx` (or `LensSelector.tsx`)
  — a visible control cycling `lensMode`, wired into `DeckGLMap.tsx`.
- [ ] T034 [US3] Wire `mapLensLayers.ts` into `DeckGLMap.tsx`'s `layers` memo; extend
  `MapLegend.tsx` and `HexTooltip.tsx` with per-mode content (stance/sovereign/influence fields).
- [ ] T035 [US3] Confirm T030's tests are GREEN, including the VIII.9 assertion.

## Phase 9 — Playwright lens-cycling gate (US3)

- [ ] T036 [US3] Write `web/frontend/e2e/map-lens-cycling.spec.ts` (route-mocked, backend-free
  pattern matching prior sprints' owner-run suites): seed a snapshot with balkanization fields via
  route mocking, cycle through all 5 lens modes via the `MapModeSelector` control, assert each
  produces a distinguishable rendering state and no uncaught page error.
- [ ] T037 [US3] Run the Playwright lens-cycling suite and confirm it passes (or, if
  environment-gated per prior sprints' precedent, confirm it skips cleanly without the gating
  env var and document the owner-run command in this spec's close-out).

## Phase 10 — Quality gate

- [ ] T038 Run `mise run web:check` (tsc + eslint + prettier + vitest) — confirm fully green,
  including all new suites from Phases 4-9.
- [ ] T039 Re-run `rg '26163' web/game/engine_bridge.py` — confirm still clean (regression guard
  before close-out).
- [ ] T040 Re-run the `get_economy` contract test (T018/T020) and the VIII.9 assertion (T030)
  standalone and confirm both green, as the two named spec-093 gate checks.

## Phase 11 — Close-out

- [ ] T041 Update `project/09-program-full-game.md` §2 spec-093 status, `ai-docs/state.yaml`.
- [ ] T042 Write `.superpowers/sdd/reports/093.md` (status, commit log, test counts, gate results,
  de-fixture data source, owner-queue items).
- [ ] T043 Final commit via `mise run commit -- "docs(spec-093): close-out — status, state.yaml,
  report"`.

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
