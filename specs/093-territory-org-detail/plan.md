# Implementation Plan: Territory Detail, Org Detail, Map Lens Set

**Branch**: `093-territory-org-detail` (stacks on `092-event-log`) | **Spec**:
`specs/093-territory-org-detail/spec.md`
**Program**: 09 Full-Game Build — Lane W. Kit refs: `project/09-program-full-game.md` §2
(spec-093 entry, lines 227-252), §3 (Lane W file ownership).

## Summary

Upgrade the two minimal inline detail renderers in `IntelPageV2` (`TerritoryDetail`, `OrgDetail`)
into full detail screens with provenance-tooltipped stats, ported from
`design/mockups/ui_kits/webapp/{TerritoryDetail,OrgDetail}.jsx`. Add a `get_economy` bridge method
+ REST endpoint powering Territory Detail's economic panel. Surface spec-070's balkanization
graph data (Sovereign / BalkanizationFaction / CLAIMS / INFLUENCES — computed every tick, never
exposed) through a new map-snapshot extension and a new `MapMode` lens concept
(stance/heat/habitability/faction/collapse) layered onto `DeckGLMap`, distinct from the existing
four-value analytical `LensId`. De-fixture the five verb-target bridge methods that currently
`break` after a hardcoded Wayne County (FIPS 26163) block, replacing them with real per-org
graph queries iterating all of the org's territories.

## Technical Context

**Language**: Python 3.12 (backend), TypeScript 5.7 (frontend).
**Stack**: Django 5.x + psycopg3 (`PostgresRuntime`), React 19 + Zustand 5 + deck.gl 9 + MapLibre
GL 5 + Vite 6 + Vitest 4 + Playwright 1.58 — all already installed (shared `node_modules`/`.venv`
symlinks, no install/`poetry install`).
**Constraints**: `mise run web:check` green; backend `poetry run pytest tests/unit/web/` green;
Vitest green (baseline + new suites); no engine dynamics changed — this spec reads existing
spec-070 graph state, it does not add new Systems or formulas. Sovereign/BalkanizationFaction
node types and CLAIMS/INFLUENCES edges are read via `graph.nodes`/edges exactly like every other
bridge method (no new persistence tables; the 0025 migration's SQL tables are audit-only, not the
live-session source of truth).
**Scope of ownership (Lane W)**: `web/**` (product) ONLY, including the shared hot file
`web/game/engine_bridge.py` (spec-092 owned it before this spec; 093 stacks after and inherits its
changes). MUST NOT touch `src/babylon/**` (engine — another lane owns it; this spec is read-only
against spec-070's already-shipped engine systems). `design/mockups/**` is READ-ONLY visual
source of truth.

## Constitution Check

*GATE: Must pass before implementation. Constitution v2.7.0 (Amendments K + L ratified).* UI work
is bound by Article VII + VIII.9.

| Gate | Requirement | This feature | Status |
|------|-------------|--------------|--------|
| **VIII.9 Community as Pairwise Edge / hyperedge anti-pattern** | Hyperedges never pairwise-fan or spatial hull | The map's new CLAIMS-hull rendering is Sovereign→Territory (dyadic-edge-derived geographic overlay), NOT hyperedge/community data. Community/hyperedge rendering elsewhere in the UI (IntelPageV2's existing `CommunityDetail`) is untouched — still choropleth/badge. A Vitest assertion checks the map component tree never receives hyperedge data as hull input. | PASS (guarded by new test) |
| **II.11 Subsystem Table Ownership** | Cross-subsystem reads via declared interfaces (views/RPC/events), not direct table access | `get_economy` and the map-snapshot extension read via `graph.nodes`/edges through `hydrate_state()`, the same declared interface every existing bridge method uses. No new SQL against `runtime_sovereigns`/`runtime_claims_edges`/`runtime_influences_edges` (those are FR-046 audit tables owned by the balkanization subsystem, not a cross-subsystem read path). | PASS |
| **III.1 No Magic Numbers** | Constants trace to a grounded source | Meaningful-influence threshold for the faction lens desaturation and any AP/cost constants introduced are named module constants with docstrings citing their source (spec-070 defines or this spec's own documented default). | PASS |
| **III.8 Data-Grounding** | Claims trace to data/code | De-fixtured verb targets read real `territory_ids`/edges; any field the engine doesn't yet compute (e.g. certain feedforward projections) is zeroed/omitted with a comment, never a plausible invented constant (FR-019). | PASS |
| **I.20 / IV Layering** | `engine_bridge.py` sole `web/` importer of `babylon.*` | Unchanged pattern; new bridge methods (`get_economy`, balkanization-aware map fields, de-fixtured target methods) live in the same file, same import discipline. | PASS |
| **VII Visual Design** | Color = meaning; no decorative glow | ColonialStance Blood/Blue/Phosphor mapping reuses `theme/colors.ts` semantic tokens (crimson/cadre-blue/solidarity-green), not new arbitrary hex; concentric rings encode real influence share, not decoration. | PASS |
| **Amendment E Michigan Statewide** | BEA EA aggregation tier, Michigan canonical scope | LOD mechanism reuses existing `AdminLevel`/`FramingSelector`/`_aggregate_hex_features` (already BEA-EA-aware per spec-041); this spec does not expand scope beyond Michigan. | PASS |

**Gate resolution**: No conflicts. This is presentation + read-path bridge work over already-shipped
engine systems (spec-070); no new engine dynamics, no hyperedge-as-hull violations, no cross-
subsystem table reads.

## Project Structure — touched files

```
web/game/engine_bridge.py                                  # + get_economy, balkanization map fields; de-fixture 5 verb-target methods (shared hot file)
tests/unit/web/test_engine_bridge.py                        # red-first: TestGetEconomy, TestDefixturedVerbTargets, TestBalkanizationMapFields

web/frontend/src/types/game.ts                              # + EconomySummary, MapMode, ColonialStance/Sovereign/Faction snapshot types
web/frontend/src/stores/mapStore.ts                         # + mapMode state (stance/heat/habitability/faction/collapse), factionFilter
web/frontend/src/lib/selectors/primitives.ts                # + territory.economy.* / org vanguard selectors (BreakdownTooltip provenance)
web/frontend/src/lib/selectors/derived.ts                   # + any composed economy/vanguard selectors
web/frontend/src/hooks/useEconomy.ts                        # NEW — GET /api/games/:id/territories/:tid/economy/
web/frontend/src/components/pages/IntelPageV2.tsx           # TerritoryDetail/OrgDetail renderers upgraded in place
web/frontend/src/components/map/DeckGLMap.tsx                # CLAIMS hull layer, stance fill, concentric rings, heat gloom
web/frontend/src/components/map/MapModeSelector.tsx          # NEW — lens-mode control (stance/heat/habitability/faction/collapse)
web/frontend/src/components/map/MapLegend.tsx                # + per-mode legend content
web/frontend/src/components/map/HexTooltip.tsx               # + stance/sovereign/influence fields when mapMode requires them
web/frontend/src/test/handlers.ts                            # + economy + balkanization-aware map MSW fixtures
web/frontend/src/mocks/*.json                                 # updated verb-target fixtures reflecting de-fixtured shape (if needed for tests)

web/frontend/src/components/pages/__tests__/intel-v2.test.tsx           # + Territory/Org Detail provenance + not-found tests
web/frontend/src/components/map/DeckGLMap.test.tsx                       # + lens-mode rendering + VIII.9 hull-source assertion
web/frontend/src/__tests__/integration/economy-contract.test.tsx         # NEW, red-first
web/frontend/e2e/map-lens-cycling.spec.ts                     # NEW — Playwright gate (route-mocked, backend-free pattern)

specs/093-territory-org-detail/contracts/economy.yaml          # NEW
specs/093-territory-org-detail/contracts/map-balkanization.yaml # NEW (documents the map-snapshot extension shape)
```

**Structure Decision**: Reuses the existing v2 web app structure (Django `web/game` backend +
React `web/frontend` SPA). No new top-level directories. The two detail screens are NOT new route
components — they replace the `TerritoryDetail`/`OrgDetail` render functions already inline in
`IntelPageV2.tsx` at the existing `intel/:targetType/:targetId` route, per the spec's Assumptions.
The map lens set is a `mapMode` addition to the existing `useMapStore`, kept separate from the
existing `LensId` analytical-lens concept (see spec Assumptions) to avoid overloading a shipped
type.

## Phased Approach (each phase = one commit, TDD red-first)

1. **Backend RED** → failing tests in `test_engine_bridge.py` for `get_economy` (territory not
   found / real data / no-data-yet cases) and for each of the 5 de-fixtured verb-target methods
   (multi-territory org, zero-territory org, no literal "26163"/"Wayne" in non-parameter output).
2. **Backend GREEN** → implement `get_economy` reading production/rent graph fields via
   `hydrate_state`; rewrite the 5 verb-target methods to loop over `org_data["territory_ids"]`
   (no `break`), derive targets from real territory/edge/community graph state, and return honest
   empty lists + `unavailable_*` entries when data is absent. Add balkanization-aware fields
   (dominant stance, per-faction influence, sovereign id/hull membership) to `get_map_snapshot`.
   Confirm `rg '26163' web/game/engine_bridge.py` clean.
3. **Backend contract** → `specs/093-territory-org-detail/contracts/economy.yaml` +
   `map-balkanization.yaml` pinning the new response shapes.
4. **Frontend contract RED** → `economy-contract.test.tsx` against unmocked routes.
5. **Frontend contract GREEN** → `useEconomy` hook + MSW handler/fixture.
6. **Territory Detail** → upgrade `IntelPageV2`'s `TerritoryDetail` renderer: full stat grid,
   economic panel (via `useEconomy`), org-presence list, recent-events list, `BreakdownTooltip` on
   every stat (new `territory.*` selectors where missing), not-found state. Tests first.
7. **Org Detail** → upgrade `IntelPageV2`'s `OrgDetail` renderer: vanguard economy block, OODA
   phase, relations list (derived from real edge mode, not a random label), recent-events list,
   `BreakdownTooltip` on every stat. Tests first.
8. **Map lens set** → `mapStore` `mapMode` state; `MapModeSelector` control; `DeckGLMap` stance
   fill + concentric rings + CLAIMS hulls + heat/habitability/faction/collapse fills; `MapLegend` +
   `HexTooltip` per-mode content. VIII.9 assertion test (hull source is CLAIMS-edge derived, never
   hyperedge/community data) written red-first alongside the hull-rendering code.
9. **Playwright lens-cycling gate** → `e2e/map-lens-cycling.spec.ts`, route-mocked backend-free
   pattern (matches `briefing-map-smoke.spec.ts` precedent): seed a snapshot with balkanization
   fields, cycle all 5 modes, assert distinguishable rendering state per mode and no uncaught page
   error.
10. **Quality gate** → `mise run web:check`; `poetry run pytest tests/unit/web/`; re-run
    `rg '26163' web/game/engine_bridge.py` clean-check.
11. **Close-out** → `project/09-program-full-game.md` §2 spec-093 status, `ai-docs/state.yaml`,
    this plan + tasks.md + contracts, report at `.superpowers/sdd/reports/093.md`.

## Complexity Tracking

| Divergence from the mockup | Why unavoidable | Resolution |
|---|---|---|
| `TerritoryDetail.jsx`/`OrgDetail.jsx` render from `window.MOCK` global fixtures and `Math.random()` event sampling | Violates III.8 data-grounding; this spec's whole point is replacing fixtures with live data | Visual layout/tokens ported; all data sourced from `GameSnapshot` + `useEconomy`, event sampling replaced with a real recency-sorted filter |
| `map-canvas.jsx`'s hex grid + regions are a fully synthetic stylized-US SVG (not real geography) | The product map is deck.gl + MapLibre over real H3 hexes/county polygons, not an SVG mock | Lens semantics (stance fill, concentric rings, CLAIMS hulls, heat gloom, contested dashing) ported onto `DeckGLMap`'s real geographic layers; the synthetic region/city layout itself is not ported |
| Mockup's `OrgDetail` sparklines (`history_cl`, `history_sl`, etc.) imply per-tick history arrays | `GameSnapshot` is current-tick only; timeseries history is a separate endpoint (`useTimeseries`) with a fixed 6-metric schema that doesn't include vanguard resources | Vanguard stats render as current-value stats with `BreakdownTooltip` provenance; sparkline history is out of scope for this spec unless `useTimeseries`-equivalent vanguard series already exist — documented as a follow-up if not |
