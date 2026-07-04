# Phase 0 Research: Territory Detail, Org Detail, Map Lens Set

## Q1: What backs `get_economy`'s per-territory economic panel?

**Decision**: `get_economy_dashboard` (the existing stub at
`web/game/engine_bridge.py:442`, wired at `GET /api/games/{id}/economy/`)
gains an optional `territory_id` parameter. When present, it returns a
per-territory summary derived from real graph state:

- **Value produced / wealth**: `wealth` on `SocialClass`/`Organization`
  nodes whose `territory_ids` include the requested territory (written by
  `ProductionSystem`, `src/babylon/engine/systems/production.py:167-184` —
  `graph.update_node(node.id, wealth=current_wealth + produced_value)`).
- **Extraction intensity**: `extraction_intensity` on the same nodes
  (`production.py:254`).
- **Rent / imperial-rent contribution and exploitation rate**: summed from
  incident `EdgeState` records in `EXTRACTIVE`/`ANTAGONISTIC` mode
  (`value_flow`, `tension`, `repression_flow` — already surfaced in
  `GameSnapshot.edges`), passed through the existing
  `calculate_exploitation_rate`/`calculate_exchange_ratio` formulas in
  `src/babylon/formulas/unequal_exchange.py` rather than re-deriving a new
  formula.
- **No-data state**: when no node/edge in the graph references the
  territory yet (e.g. tick 0 before production has run), the endpoint
  returns explicit zeros plus a `has_data: false` flag — never a
  fabricated nonzero literal.

**Rationale**: Territory itself carries no value/wage fields (confirmed:
`src/babylon/models/entities/territory.py` has `heat`, `rent_level`,
`population`, `biocapacity`; no `value_produced`/`wage`). The real
economic activity lives on the `SocialClass`/`Organization` nodes located
in a territory and the edges between them — the same graph traversal
pattern the five verb-target methods already use
(`org_data.get("territory_ids", [])`). Reusing existing formula functions
(rather than inventing new economics) keeps this a pure read/aggregation
feature per the spec's Assumptions.

**Alternatives considered**: Building a new territory-scoped tensor read
via `src/babylon/economics/` (the full Leontief/tensor pipeline, specs
011/057) — rejected for this spec because it operates at hex/BEA-EA scale
with its own hydration lifecycle and is not yet wired to per-tick graph
state the bridge can cheaply read; adopting it is a larger, separate
effort better suited to a future spec once the map's Michigan LOD work
(FR-030) matures. Using `src/babylon/engine/systems/phi_distribution.py`
(`distribute_phi_week_to_counties`) — rejected because it operates on
weekly BEA-EA I-O exposure distribution to *counties from external
nodes*, a different scope (national trade inflow) than a single
territory's local production/rent picture.

## Q2: Is ternary consciousness (r/l/f) a stored field anywhere reachable from a Territory?

**Decision**: Yes. `TernaryConsciousness` (`src/babylon/models/entities/
consciousness.py:51-78`) is a real Pydantic model with `r`/`l`/`f`
`Probability` fields, and `CommunityConsciousness` is a type alias for it
(`src/babylon/models/entities/community.py:152`). Community/hyperedge
graph nodes (`_node_type == "community"`, per spec-055's detector) carry
real `r`/`l`/`f` values — not the flat literal (`0.25`/`0.55`/`0.20`)
hardcoded in today's `get_educate_targets` fixture. De-fixturing EDUCATE
targets (User Story 4) reads the real community's `TernaryConsciousness`
via its graph node attrs (`r`, `l`, `f` keys) for any community whose
membership overlaps the requested territory's population, instead of a
literal.

**Rationale**: Confirmed by direct model inspection this session; no
further engine work is required to satisfy FR-016/FR-019 for the
consciousness sub-fields.

**Alternatives considered**: Approximating r/l/f from `SocialClass.
class_consciousness`/`national_identity` (the older `IdeologicalProfile`
scalar pair) — rejected now that the real ternary fields are confirmed to
exist; using the older scalar pair would be a regression, not a proxy.

## Q3: Map lens architecture — deck.gl layers vs. SVG

**Decision**: Extend `DeckGLMap.tsx`'s existing deck.gl layer array with
additional `PolygonLayer`/`GeoJsonLayer` instances for: state-boundary
outlines (static reference geometry), sovereign CLAIMS hull outlines
(computed client-side from claimed-territory centroids per sovereign,
convex-hull, same algorithm shape as the mockup's `convexHull()` but
implemented in TS and fed by real `/api/games/{id}/economy/` /
balkanization data, not mock hex generation), and a
per-territory concentric-ring encoding achieved via a second
`H3HexagonLayer` (or `ScatterplotLayer` fallback) instance rendering a
smaller inset hex per territory for the secondary faction share. Lens
switching is a `mapStore` state transition that swaps `getFillColor`
callbacks and toggles layer visibility — no new rendering library.

**Rationale**: `design/mockups/themap/*.jsx` are explicitly flagged as
throwaway SVG prototypes for visual reference; the production map already
has a working deck.gl + MapLibre + H3 pipeline (`DeckGLMap.tsx`,
`mapStore.ts`) that the whole rest of the v2 UI depends on. Reimplementing
as SVG would fork the map into two incompatible rendering systems.

**Alternatives considered**: A parallel SVG overlay for balkanization-
specific lenses composited over the deck.gl canvas — rejected: breaks
pan/zoom/pick coordination between the two rendering systems for no
benefit, since deck.gl already supports arbitrary polygon/line layers.

## Q4: Balkanization data surface — new endpoint or extend existing snapshot?

**Decision**: Extend `GameSnapshot`/the map snapshot payload with a new
optional `balkanization` block (factions, sovereigns, per-territory
influence shares, per-territory current claimant) computed in
`get_map_snapshot`/`get_snapshot`, sourced via the existing
`graph.query_faction_influence_by_territory` / `query_sovereign_claims` /
`query_territory_claims` protocol methods. Frontend types add
`ColonialStance`, `FactionInfluence`, `SovereignClaim` to `types/game.ts`.

**Rationale**: These protocol methods already exist and are exercised by
engine-side tests (`tests/unit/engine/test_graph_protocol.py`); the bridge
just needs to call them per territory/sovereign and shape the result.
Extending the existing snapshot avoids a second polling loop.

**Alternatives considered**: A dedicated `/api/games/{id}/balkanization/`
endpoint — reasonable, but rejected in favor of extending the existing map
snapshot so the map's lens rendering has single-request data-consistency
across all lenses at a given tick (per acceptance scenario "the same
territory's data is consistent across lenses").

## Q5: VIII.9 rendering-assertion test strategy

**Decision**: A Vitest test renders `DeckGLMap` (or the lens-layer builder
function extracted for testability) with a snapshot containing both (a)
sovereign CLAIMS data and (b) hyperedge/community membership data, and
asserts via the constructed deck.gl layer list that: a `PolygonLayer`/hull
is built from CLAIMS data, and no layer is ever constructed from
`hyperedges`/`HyperedgeState` data with hull/polygon/path geometry. A
second unit test asserts the community-rendering code path (wherever
communities are shown — badges, choropleth) never imports or calls the
hull-construction helper.

**Rationale**: This is testable at the "which layers got built from which
inputs" level without needing a full WebGL canvas assertion, matching how
`DeckGLMap.test.tsx` already tests layer construction (confirmed existing
file: `web/frontend/src/components/map/DeckGLMap.test.tsx`).

## Q6: Michigan BEA-EA LOD mechanism

**Decision**: Reuse `_aggregate_hex_features` (`engine_bridge.py:301-381`)
and the frontend `AdminLevel`/`FramingSelector` unchanged; no new grouping
mechanism. `specs/040-michigan-statewide-scope/spec.md` is a 12-line stub
with no usable BEA-EA detail and is not a dependency for this spec beyond
confirming Michigan is the intended scope.

**Rationale**: The real, working LOD mechanism already exists and groups
by `state_fips`/`bea_ea_code`/`msa_code`/`county_fips`; spec-093 only
needs to ensure the new economy/balkanization data can be read at whatever
zoom level the map is already rendering at — no new aggregation code.
