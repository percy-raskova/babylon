# Feature Specification: Territory Detail, Org Detail, Map Lens Set

**Feature Branch**: `093-territory-org-detail`
**Created**: 2026-07-04
**Status**: Draft
**Input**: User description: "Territory Detail and Org Detail intel sub-route screens, a full Map lens-set upgrade (state outlines, faction-influence concentric rings, heat overlay, CLAIMS hulls, ColonialStance Blood/Blue/Phosphor encoding, lens modes stance/heat/habitability/faction/collapse, Collapse-Moment mode) over spec-070 balkanization data, BreakdownTooltip provenance on every displayed number in the two new detail screens, a new get_economy engine-bridge endpoint powering Territory Detail's economic panel, de-fixturing the five hardcoded verb-target endpoints in web/game/engine_bridge.py which currently return hardcoded Wayne County fixture data, and the state->BEA-EA->county LOD mechanism at Michigan scope."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drill into a territory's full material and political record (Priority: P1)

A player scanning the map or the Intel index wants to understand *why* a
given county behaves the way it does: who claims it, how contested it is,
what its economy looks like, and what's happened there recently. Today
`IntelPageV2` shows four numbers and a name. The player needs the same
depth of provenance-backed detail the rest of the v2 UI already offers
elsewhere (Briefing, Analysis), applied to a single territory.

**Why this priority**: Territory Detail is the single most-used drill-down
target — every hex on the map and every territory row in Intel links here.
Without it, the map upgrade (US3) has nowhere to send a click.

**Independent Test**: Navigate to `/games/:id/intel/territory/:territoryId`
for a territory that exists in the current snapshot. The page renders
material stats (heat, rent, consciousness, wealth, biocapacity), an
economic panel, active organizations present in the territory, and recent
events — all sourced from the live snapshot, with no placeholder or
`Math.random()` data. Every numeric stat opens a breakdown on click showing
its computed contributors and sources.

**Acceptance Scenarios**:

1. **Given** a game with an existing territory, **When** the player opens
   that territory's detail route, **Then** the page shows the territory's
   name, county FIPS, current heat/rent/consciousness/wealth/biocapacity,
   and does not fabricate any value not derivable from the snapshot or the
   new economy endpoint.
2. **Given** a territory detail page is open, **When** the player clicks a
   displayed stat, **Then** a breakdown popover opens showing the
   contributors and source (snapshot field / GameDefines / derived) that
   produced that value.
3. **Given** a territory hosts one or more organizations, **When** the
   player views the territory detail page, **Then** those organizations
   are listed with their relationship to the territory (own/hostile/ally
   as derivable from edges), not a hardcoded roster.
4. **Given** a territory ID that does not exist in the current snapshot,
   **When** the player navigates to its detail route, **Then** the page
   shows a clear "not found" state rather than crashing or showing another
   territory's data.

---

### User Story 2 - Drill into an organization's vanguard economy and relations (Priority: P1)

A player managing their own organization, or scouting a rival, wants the
full picture: resource levels over time, OODA phase, cohesion/heat/opacity,
relations to other known organizations, and a history of what the org has
done. Today `IntelPageV2` shows three stats and an OODA phase string.

**Why this priority**: Equal priority to Territory Detail — it is the
other universal drill-down target (every org row in Intel, every org
reference in the Wire/events, links here), and the player's own vanguard
economy is otherwise invisible outside the action composer.

**Independent Test**: Navigate to `/games/:id/intel/org/:orgId` for an
organization in the current snapshot. The page renders the vanguard
economy (cadre labor, sympathizer labor, reputation, heat, budget) with
history where available, relations to other known organizations, and a
recent-events history — all from live data, all breakdown-tooltipped.

**Acceptance Scenarios**:

1. **Given** an org exists in the current snapshot, **When** the player
   opens its detail route, **Then** the page shows org type, class
   character, member/cadre counts, cohesion, heat, OODA phase, and (for
   the player's own org) vanguard resource levels — all sourced from the
   snapshot, not fabricated.
2. **Given** the org detail page is open, **When** the player clicks a
   displayed stat, **Then** a breakdown popover opens with contributors and
   sources, matching the pattern used elsewhere in the v2 UI.
3. **Given** two organizations share territory or an edge, **When** the
   player views one org's detail page, **Then** the other appears in a
   relations list with a relationship classification derived from the
   actual edge mode (not a random "ally"/"hostile" label).

---

### User Story 3 - Read the political-topology map through multiple lenses (Priority: P1)

A player watching the country fracture wants a map that shows *who
controls what*: state outlines for orientation, which faction dominates
each territory (with concentric rings showing the full influence split,
not just the winner), which areas are hot with state attention, which are
becoming uninhabitable, and — after a sovereign collapses — which
territories flipped to a new claimant. This is the map upgrade described
in spec-070 as deferred to the UI-overhaul spec; that spec is this one.

**Why this priority**: This is the single biggest visible payoff of the
sprint and the direct payoff of spec-070's balkanization simulation, which
has been computing this data with nobody able to see it.

**Independent Test**: Open the map with a game whose territories have
sovereign CLAIMS and faction INFLUENCES data. Cycle through the five lens
modes (stance, heat, habitability, faction, collapse) via a visible
control; each produces a materially different fill/overlay without a page
reload, and sovereign CLAIMS boundaries render as map-level hull outlines
distinct from any hyperedge/community rendering.

**Acceptance Scenarios**:

1. **Given** a game with balkanization data, **When** the player selects
   the "stance" lens, **Then** each territory's dominant ColonialStance
   colors its fill (Blood=uphold, Blue=ignore, Phosphor=abolish) and, where
   more than one faction holds meaningful influence, concentric rings show
   the secondary/tertiary split.
2. **Given** the same game, **When** the player selects "heat", **Then**
   the fill switches to the heat overlay and stance becomes a thin outline
   or is suppressed, without altering the underlying data.
3. **Given** the same game, **When** the player selects "habitability",
   **Then** fill reflects the metabolic-rift/biocapacity gradient.
4. **Given** the same game, **When** the player selects "faction" and
   picks one faction, **Then** territories below a meaningful-influence
   threshold desaturate and the rest shade by that faction's influence
   level.
5. **Given** a sovereign has collapsed and territories have transitioned
   claimants, **When** the player selects "collapse" (Collapse-Moment)
   mode, **Then** contested/transitioning territories are visually
   distinguished from stable ones.
6. **Given** any lens is active, **When** sovereign CLAIMS boundaries are
   shown, **Then** they render as geographic hull outlines over the actual
   territories a sovereign holds — and community/hyperedge membership is
   NEVER rendered this way anywhere on the map (choropleth/badge/UpSet
   only, per Constitution VIII.9).

---

### User Story 4 - Real verb targets instead of Wayne County fixtures (Priority: P2)

A player anywhere in Michigan (not just Wayne County) opens the Educate,
Aid, Mobilize, Attack, or Reproduce action composer and expects to see
targets that reflect *their* organization's actual territories and
neighbors, not a hardcoded Detroit-area fixture that appears regardless of
where the org actually operates.

**Why this priority**: Lower priority than the two detail screens and the
map because it's a correctness fix to already-shipped verb flows rather
than new surface area, but it blocks the game from being played anywhere
outside Wayne County and is explicitly called out as required for this
spec's gate.

**Independent Test**: Create a game, place a player org in a territory
other than FIPS 26163, and open each of the five verb composers. Every
target list reflects that org's real territory/edge/community graph state;
no response contains the literal string "Wayne" or FIPS `26163` unless the
org's real territory happens to be Wayne County.

**Acceptance Scenarios**:

1. **Given** a player org whose `territory_ids` includes a non-Wayne
   territory, **When** the player opens the Educate composer, **Then**
   the returned targets reference that territory's real name/ID and
   real (or honestly zeroed, per FR-020) consciousness/material data.
2. **Given** an org with no territories, **When** any of the five target
   endpoints is queried, **Then** the response reflects that empty state
   (empty target list with an explanatory `unavailable_*` entry) rather
   than falling back to a Wayne County default.

---

### User Story 5 - Territory economic panel via a real endpoint (Priority: P2)

The Territory Detail page needs an economic summary (value produced,
wages, extraction, local price/exchange distortion) sourced from the
engine's real economics pipeline, not invented on the frontend.

**Why this priority**: Directly required by User Story 1's acceptance
criteria; broken out as its own story because it is independently
testable as a contract (`get_economy`) before the panel that consumes it
exists.

**Independent Test**: Call the new economy endpoint for a territory ID
that exists in a live session. The response matches a pinned contract
schema and every field is traceable to a real snapshot/derived-block
source (no literal fixture values).

**Acceptance Scenarios**:

1. **Given** a territory with production/rent data present in the graph,
   **When** `get_economy` is called for it, **Then** the response includes
   value produced, wage share, rent/extraction level, and imperial-rent
   contribution, each attributable to a real field.
2. **Given** a territory with no economic data yet computed (e.g., before
   the first tick resolves), **When** `get_economy` is called, **Then**
   the response returns honest zeros/nulls with a status the frontend can
   render as "no data yet" rather than a fabricated number.

---

### Edge Cases

- A territory or org ID in the URL doesn't exist in the current snapshot
  (typo, stale link, or the entity was removed by simulation) → detail
  page shows a "not found" state, not a crash or another entity's data.
- A territory has no sovereign CLAIMS or faction INFLUENCES yet (very
  early game, or a scenario that hasn't run the balkanization systems) →
  map lenses that depend on that data degrade to a neutral/ungoverned
  rendering rather than erroring or showing stale mock data.
- Two sovereigns have overlapping CLAIMS on the same territory
  (`DUAL_POWER_ACTIVE`, permitted transiently per spec-070) → the CLAIMS
  hull rendering and the territory detail page both surface this rather
  than picking one arbitrarily and hiding the conflict.
- An org has zero recorded history (freshly created) → Org Detail's
  history/sparkline areas show an empty/flat state, not fabricated
  historical values.
- The five verb-target endpoints are called for an org whose territories
  span multiple counties → results must reflect all of them, not just the
  first one found (todays fixture code `break`s after the first match).
- The map is viewed for a session outside Michigan scope (should not occur
  in this spec's scope, but the LOD mechanism must not silently mislabel
  out-of-scope data as Michigan).

## Requirements *(mandatory)*

### Functional Requirements

**Territory Detail**

- **FR-001**: System MUST provide a Territory Detail view reachable at the
  existing `/games/:id/intel/territory/:targetId` intel sub-route, replacing
  the current minimal inline renderer with a full-detail screen ported from
  the visual design in `design/mockups/ui_kits/webapp/TerritoryDetail.jsx`.
- **FR-002**: The view MUST display, at minimum: territory name, county
  FIPS, heat, rent level, consciousness (where available), wealth,
  biocapacity, population, and eviction status — all sourced from the live
  `GameSnapshot`.
- **FR-003**: The view MUST display an economic panel sourced from the new
  `get_economy` endpoint (FR-013 - FR-015).
- **FR-004**: The view MUST list organizations with a presence in the
  territory, derived from real `territory_ids` / edge data, not a
  hardcoded roster.
- **FR-005**: The view MUST list recent events affecting the territory,
  filtered from the live event stream (not randomly sampled).
- **FR-006**: Every numeric stat on the page MUST be wrapped so a user
  action reveals its provenance breakdown (contributors + source),
  reusing the existing `BreakdownTooltip` + selector-registry pattern.
- **FR-007**: When the requested territory ID is not present in the
  current snapshot, the view MUST render a clear not-found state.

**Org Detail**

- **FR-008**: System MUST provide an Org Detail view reachable at the
  existing `/games/:id/intel/org/:targetId` intel sub-route, replacing the
  current minimal inline renderer with a full-detail screen ported from
  `design/mockups/ui_kits/webapp/OrgDetail.jsx`.
- **FR-009**: The view MUST display org type, class character, cohesion,
  heat, opacity, OODA phase, and — for the player's own organization(s) —
  vanguard economy levels (cadre labor, sympathizer labor, reputation,
  budget, heat) against their known maxima.
- **FR-010**: The view MUST list relations to other known organizations,
  with a relationship classification derived from real edge data (mode /
  tension / value_flow) rather than a hardcoded label.
- **FR-011**: The view MUST list recent events involving the organization.
- **FR-012**: Every numeric stat on the page MUST be wrapped with the same
  `BreakdownTooltip` provenance pattern as Territory Detail.

**Economy endpoint**

- **FR-013**: System MUST implement `EngineBridge.get_economy_dashboard`
  (today a `{}` stub already wired to the existing
  `GET /api/games/{id}/economy/` endpoint, per
  `project/01-state-of-the-world.md`'s stub inventory and
  `project/09-program-full-game.md` line 296's "`get_economy` → 093"),
  returning real global economy aggregates (from `DerivedBlock.economy` /
  `class_aggregates`) plus a per-territory breakdown keyed by territory ID
  (value produced, wage share/received, rent/extraction level,
  imperial-rent contribution) so Territory Detail's economic panel can
  index into the same dashboard response by its `territoryId` rather than
  requiring a second new endpoint.
- **FR-014**: `get_economy` MUST return an honest no-data state (not a
  fabricated value) when the requested territory has no economic data yet.
- **FR-015**: `get_economy`'s response schema MUST be pinned by a contract
  test before any UI consumes it (TDD red-first).

**De-fixturing verb targets**

- **FR-016**: `get_educate_targets`, `get_aid_targets`,
  `get_mobilize_targets`, `get_attack_targets`, and `get_reproduce_targets`
  in `web/game/engine_bridge.py` MUST derive every returned target from
  the requesting org's real graph state (its `territory_ids`, incident
  edges, and reachable communities/organizations) rather than a hardcoded
  Wayne County / FIPS 26163 fallback block.
- **FR-017**: These five endpoints MUST iterate over ALL of an org's
  territories when building target lists, not stop after the first match.
- **FR-018**: When an org has no territories (or no data satisfying a
  given verb's targeting criteria), the corresponding endpoint MUST return
  an honestly empty target list (with an explanatory `unavailable_*`
  entry where the response shape already supports one) rather than
  falling back to fixture data.
- **FR-019**: Where a target field has no real per-tick-computed
  counterpart yet in the engine (e.g., certain projected-feedforward
  sub-fields), the endpoint MUST either compute it from real inputs or
  omit/zero it with a clear marker — it MUST NOT emit an invented non-zero
  constant presented as if measured.
- **FR-020**: A repository-wide check (`rg '26163'
  web/game/engine_bridge.py`) MUST show no remaining hardcoded fixture
  blocks after this work (only real query parameters, if any, may contain
  that string).

**Map lens set**

- **FR-021**: System MUST render state-boundary outlines on the map as
  geographic context beneath the hex/territory layer.
- **FR-022**: System MUST render, for each territory, the dominant
  faction's ColonialStance as a fill color using the three-color encoding
  (uphold=Blood/crimson, ignore=Blue, abolish=Phosphor/green), with
  concentric rings representing secondary/tertiary faction influence
  shares where more than one faction holds meaningful influence.
- **FR-023**: System MUST provide a heat-overlay lens mode using the
  existing heat metric.
- **FR-024**: System MUST provide a habitability lens mode reflecting
  metabolic-rift/biocapacity state.
- **FR-025**: System MUST provide a faction-filter lens mode that,
  given a selected faction, shades territories by that faction's
  influence level and visually desaturates territories below a
  meaningful-influence threshold.
- **FR-026**: System MUST provide a Collapse-Moment lens mode that
  visually distinguishes contested/recently-transitioned territories
  from stable ones, sourced from real sovereignty-transition data (not a
  scripted animation).
- **FR-027**: System MUST render sovereign CLAIMS as geographic hull
  outlines over the territories each sovereign actually holds, derived
  from real CLAIMS-edge data.
- **FR-028**: System MUST allow switching between lens modes without a
  full page reload, and the active lens MUST be visible in the UI.
- **FR-029**: System MUST NEVER render hyperedge/community membership as
  a spatial hull or pairwise-fan on the geographic map (Constitution
  VIII.9); community/hyperedge relationships continue to render only as
  choropleth, badge, or UpSet-style widgets elsewhere in the UI.

**Michigan LOD mechanism**

- **FR-030**: System MUST support aggregating map/detail data across the
  state → BEA Economic Area → county level-of-detail hierarchy at
  Michigan scope, reusing the existing admin-framing mechanism
  (`AdminLevel`, `FramingSelector`) and the BEA-EA authority defined in
  `specs/040-michigan-statewide-scope`.
- **FR-031**: The LOD mechanism MUST NOT claim national coverage; Michigan
  is the scope for this spec, with national framing explicitly deferred
  to a later spec per the program plan.

### Key Entities

- **Territory** (existing): the county/hex-level entity now getting a
  full detail view and a real economy summary.
- **Organization** (existing): the agent entity now getting a full detail
  view including vanguard economy and relation classification.
- **Sovereign** (spec-070, existing engine entity, newly surfaced to the
  API/UI): an authority holding CLAIMS on territories; drives the map's
  hull rendering and the Collapse-Moment lens.
- **BalkanizationFaction** (spec-070, existing engine entity, newly
  surfaced): holds a ColonialStance and INFLUENCES edges to territories;
  drives the stance/faction lenses and concentric rings.
- **Economy summary** (new, derived): a per-territory read-only
  projection of value produced, wages, rent/extraction, and imperial-rent
  share, returned by `get_economy`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player can reach full detail (all FR-002/FR-009 fields,
  with working breakdowns) for any territory or organization in the
  current game within two clicks from the map or Intel index.
- **SC-002**: Every numeric value shown on the two detail screens has a
  working provenance breakdown; zero values are hardcoded/fabricated.
- **SC-003**: A player can cycle through all five map lens modes and see
  a materially different, data-driven rendering each time, with no lens
  switch taking longer than a single render frame to reflect (no reload).
- **SC-004**: A player whose organization operates entirely outside Wayne
  County sees verb targets specific to their own territory, never a
  Wayne County / FIPS 26163 fixture.
- **SC-005**: `rg '26163' web/game/engine_bridge.py` returns no hardcoded
  fixture blocks after this work ships.
- **SC-006**: No community/hyperedge relationship ever renders as a
  spatial hull or pairwise fan on the geographic map, verified by an
  automated rendering assertion.

## Assumptions

- The existing `intel/:targetType/:targetId` route and `IntelPageV2`
  shell are the correct integration point for the two new detail screens
  (they already dispatch on `targetType`); this spec upgrades the
  `territory`/`org` detail renderers in place rather than introducing a
  parallel routing scheme.
- "Lens modes" for the map (stance/heat/habitability/faction/collapse)
  are a map-specific rendering concept, distinct from the existing
  four-value analytical `LensId` (economic/political/social/strategic)
  used elsewhere in the v2 UI. Both concepts coexist; this spec does not
  rename or remove the existing analytical lens system.
- Sovereign/BalkanizationFaction/CLAIMS/INFLUENCES data already exists
  in the live simulation graph (spec-070 systems run every tick); this
  spec is responsible for surfacing it through the bridge and API, not
  for computing it.
- "Real data" for the de-fixtured verb endpoints means: derived from the
  requesting session's actual graph state at query time. Where the
  engine does not yet compute a specific sub-metric the mockup/fixture
  envisioned (e.g., certain projected feedforward deltas), this spec
  computes the best available real approximation from existing formulas
  and documents any field that must degrade to zero/omitted rather than
  inventing a plausible-looking constant.
- Michigan remains the game's operating scope for this spec (per the
  program plan, national framing flips on after a later spec); the LOD
  mechanism is built to be extended later, not to already cover the
  nation.
- The existing Playwright route-mocking pattern (backend-free, live
  browser) is an acceptable and sufficient way to satisfy this spec's
  lens-cycling Playwright gate, consistent with prior sprints' e2e
  suites.
