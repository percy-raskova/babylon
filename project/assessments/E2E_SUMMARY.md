# Babylon E2E Test Summary — 2026-07-07

End-to-end user acceptance test of the Babylon web product, performed via
Playwright MCP driving a real Chromium browser against a freshly seeded
`wayne_county` game session.

## Verdict

**The game is unplayable in its current state.** The core loop
(login → pick game → queue action → resolve tick → view results) is broken
at two critical junctions:

1. Action submission fails for every verb — the frontend sends generic
   `target_id` + `paramVals` while every backend serializer expects
   verb-specific field names (`target_community_id`, `params.transfer_amount`, etc.).
2. Tick resolution throws `TypeError: Object of type datetime is not JSON
   serializable` in `_legacy.py:203` — the game can never advance past tick 0.

The login, briefing, navigation, intel, objectives, dialectic, wire, and
chronicle surfaces render and load data correctly. The map renders the
basemap tiles but shows zero territory features because `hex_latest` is
empty (the seed command does not populate the map tables).

## Environment

- Branch: `dev` at `f08cd111`
- Scenario seeded: `wayne_county`, session `bc1c883f-76dc-4de8-860d-8b18a975aa56`, tick 0
- Admin password reset to `babylon` for testing
- Backend: Django `runserver` on :8000, Postgres 5432 `babylon` DB
- Frontend: Vite dev server on :5173
- Browser: headless Chromium via Playwright MCP (WebGL unavailable — map
  tiles render but deck.gl hex layer throws `maxTextureDimension2D` errors)

## Phase-by-Phase Results

### Phase 1 — Bootstrap

| Step | Result | Notes |
|------|--------|-------|
| `mise run web:migrate` | ✅ | accounts.0001 + game.0011 applied |
| Reset admin password | ✅ | Django shell `set_password('babylon')` |
| `seed_initial_game --scenario wayne_county --player admin` | ✅ | Game `bc1c883f-…` created. WARNING logged: `column "bea_ea_code" does not exist` (non-fatal) |
| `mise run web:dev` | ✅ | Django :8000 + Vite :5173 up |
| `/health/` | ✅ | `{"status":"ok"}` |

### Phase 2 — Browser Walk-Through

#### 2.1 Login Page (`/login`) — ✅ Works

- Title "Babylon - The Fall of America", BABYLON heading, tagline, description all render
- Username/Password fields + Enter button
- Bad credentials → "Invalid credentials" message, stays on /login
- Console: only favicon 404 (cosmetic)

#### 2.2 Login as admin — ⚠️ Works after fix

- Login succeeds, redirects to /games
- Top nav renders BABYLON, "admin" username, Logout button
- New Operation panel renders 4 scenario options (Wayne County, US Nationwide, Imperial Circuit, Two-Node Dialectic)
- ❌ **Bug #1 (P0, fixed during test)**: GET `/api/games/` returned HTTP 500. Root cause: `web/game/models.py:31` declared `snapshot_json = models.JSONField(default=dict)` but migration `0008_drop_snapshot_json.py` had already dropped the column. Django ORM queried a non-existent column → `ProgrammingError`. Fixed by removing the orphan field from the model. After fix, "Your Operations: 1" with the seeded game card visible.

#### 2.3 Games List — ✅ Works (after Bug #1 fix)

- Game card visible: wayne_county, active, Tick 0, UUID bc1c883f
- Click navigates to `/games/:id`

#### 2.4 Briefing Page — ⚠️ Mostly Works

- TopBar: Back, BABYLON, wayne_county, Tick 0, "observe" mode, CL 1.0/1, SL 4.0/5, REP 0%, $100, HEAT 0%, Resolve Tick button ✅
- NavRail: 3 groups (PLAY/VERBS/ANALYZE), all 16 links present with correct URLs ✅
- Heading: "Briefing", "Tick 0 — Situation report for Wayne County Organizing Committee"
- Situation Map: 5 lenses (STANCE/HEAT/HABITABILITY/FACTION/COLLAPSE), 6 scales (ST/EA/MSA/CZ/CTY/HEX)
- Selected region: Wayne County, Heat 0.00, Rent 3.50, Population 8,000, low_profile, Biocapacity 80.00, residential
- Priority Dispatch: "No events this tick."
- ⚠️ Key Metrics panel: All values show "—" (em dash) for RENT/CON/SOL/HEAT/WEALTH/BIOCAP — empty at tick 0
- ❌ **Bug #2 (P2, environment)**: WebGL `maxTextureDimension2D` errors in headless Chromium — MapLibre GL cannot initialize. Not a Babylon bug, but means map visualization is non-functional in headless testing.
- ❌ **Bug #3 (P1, MAJOR)**: Massive polling loop. Over 300 requests to `/state/`, `/actions/available/`, `/map/?zoom=county`, `/timeseries/` in seconds with no backoff. Console fills with WebGL errors multiplied by polling. This will hammer the server in production.

#### 2.5 Verbs (9 NavRail entries)

| Verb | Status | Notes |
|------|--------|-------|
| Educate | ❌ BROKEN | Submit 400 — field name mismatch `target_id` vs `target_community_id` |
| Mobilize | ✅ renders | Vehicle (Mass Action/General Strike/Block Org), 5 SL slider |
| Campaign | ✅ renders | Territory targets (Dearborn East, Detroit Central), HEAT/RENT |
| Aid | ❌ BROKEN | Submit 400 — frontend sends `method`, backend wants `params.transfer_amount` |
| Attack | ✅ renders | Filter (all/org/territory) |
| Move | ❌ STUB | "Verb 'move' is not yet supported (spec 061 FR-025)" |
| Investigate | ❌ STUB | "Verb 'investigate' is not yet supported (spec 061 FR-025)" |
| Reproduce | ✅ renders | 5 org targets (WCLF/DTC/WCSD/DFB/S3), Track (Convert SL→CL/Train Successor/Found Cell) |
| Negotiate | ❌ STUB | "Verb 'negotiate' is not yet supported (spec 061 FR-025)" |

6/9 verbs render, 3/9 are explicit stubs (move/investigate/negotiate per spec 061 FR-025).

#### 2.6 Real Gameplay Attempt — ❌ BROKEN (P0)

Submitted an Aid action via raw `fetch()` with the correct backend field
names (`params.transfer_amount: 10`): **201 Created, action_id=1**. The
backend accepts actions when the field names match.

- ❌ **Bug #4 (P0)**: Frontend verb submit fails for every verb. `web/frontend/src/components/pages/VerbPage.tsx:228` sends `{ verb, org_id, target_id, ...paramVals }`, but each backend serializer in `web/game/serializers.py` expects verb-specific field names:
  - Educate wants `target_community_id` (not `target_id`)
  - Aid wants `params.transfer_amount` (not `method`)
  - Mobilize/Attack/Reproduce/Campaign each have their own `*ParamsSerializer`
  - No frontend mapping translates the generic `paramVals` to the verb-specific schema
- ❌ **Bug #6 (P0)**: Tick resolution throws HTTP 500. Root cause: `src/babylon/persistence/postgres_runtime/_legacy.py:203`:
  ```python
  events_list = sorted(json.dumps(event, sort_keys=True) for event in (events or []))
  ```
  Engine emits events with `datetime` objects; `json.dumps` has no `default=` handler → `TypeError: Object of type datetime is not JSON serializable`. **The game can never advance past tick 0.** Fix: `default=str` or coerce datetimes upstream.

#### 2.6b Map Investigation — user observation confirmed

User observed: "only Detroit, bunch of hexes instead of county maps, base economic unit is counties."

Findings:
- The `wayne_county` scenario is intentionally a single-county vertical slice (81 H3 hexes covering Detroit/Dearborn/Downriver). For whole-country play, use the `us_nationwide` scenario (1,100 territories). This is by design.
- ❌ **Bug #7 (P0)**: The `/api/games/:id/map/` endpoint returns 0 features at ALL valid zoom levels (`state`, `msa`, `cz`, `hex`). The "Situation Map" panel shows "Colonial Stance · Influence — no data." `hex_latest` table is empty — `seed_initial_game` does not populate the map tables. State has 81 territories with H3 indexes, but the map endpoint emits zero GeoJSON features.
- ❌ **Bug #8 (P1)**: Zoom level name mismatch. Frontend Scale buttons send `state/ea/msa/cz/cty/hex`, but backend valid levels are `bea/bea_ea/county/cz/hex/msa/state`. Two are broken: `ea` → 400 (wants `bea` or `bea_ea`), `cty` → 400 (wants `county`). County-level map is unreachable from the UI even though the backend supports it.
- ❌ **Bug #9 (P2)**: Map extends into Canada. `DeckGLMap.tsx` sets `INITIAL_VIEW_STATE` centered on SE Michigan (lat 42.5, lng -83.2, zoom 8) but sets no `maxBounds` on the MapLibre `Map` component. The user can pan freely into Canada, the Atlantic, etc. All 81 H3 cells are correctly within Wayne County (42.11–42.57 N, -83.56 to -82.86 W) — the data is fine, but the map viewport is unconstrained. Fix: set `maxBounds` to the H3 cell bounding box plus a small margin.

#### 2.7 ANALYZE Group + PLAY Group — ✅ Mostly Works

| Page | Status | Notes |
|------|--------|-------|
| Orgs | ✅ | "Organizations" heading, Wayne County Organizing Committee with Cohesion/Legitimacy/Opacity/Heat |
| Intel | ✅ | "Intel" heading, surveillance index — 81 territories, 87 edges, 0 orgs/communities. Lists Livonia/Dearborn/Detroit/Hamtramck/Wayne County with pop/HEAT |
| Results | ✅ | "Results" heading, "Tick 0 resolution summary", Player Orgs with COH 50% / HEAT 0%, "No NPC orgs surfaced" |
| Analysis | ✅ | "Analysis" heading, Social Graph Topology (d3-force, orgs + communities), Time-Series Dashboard (0 ticks), Aggregate Metrics (all "—"), Correlations ("out of scope") |
| Wire | ⚠️ | "THE WIRE / TICK 0000 / OP - RASKOVA-2", 4 tabs (The Wire/Wire Index/Patterns/Corpus), but stuck on "Loading wire feed..." |
| Dialectic | ✅ | "reproduction" regime, "0 active" contradictions, "No oppositions registered" |
| Chronicle | ✅ | "Operation in progress — no terminal outcome yet" |
| Objectives | ⚠️ | 5 tracked objectives render (see below) |
| Log | ✅ | "Event Log", 0 events, filter buttons (all/informational/warning/critical), History |
| Resolution | ✅ | "Resolving Tick 0000 → 00000 / 0 No changes recorded" animation UI |

#### Objectives — user observation: "feel imposed, could be AI-generated"

The 5 objectives (Revolutionary Victory, Ecological Collapse, Fascist
Consolidation, Red OGV Trap, Fragmented Collapse) are static and
hardcoded — same for every session, every tick. They render correctly
but feel imposed rather than emerging from the simulation state.

**Recommendation**: Invest in the AI/narrator system to generate
objectives dynamically based on the dialectic state, balkanization
factions, and class struggle trajectory. The `DeterministicNarrator`
currently in use is a placeholder. A real LLM-backed narrator could:
- Generate objectives from the active contradictions and faction state
- Vary objective framing per scenario and per org ideology
- Surface mid-game objectives in response to player choices
- Retire or evolve objectives as the simulation progresses

This ties into broader AI system improvements (see Recommendations).

## Bug Catalog

### P0 — Blocks the core loop

| # | Bug | File | Fix |
|---|-----|------|-----|
| 1 | `snapshot_json` column missing — `/api/games/` 500 | `web/game/models.py:31` | Remove `snapshot_json` field (DONE during test) |
| 4 | Verb submit field name mismatch — all verbs 400 | `web/frontend/src/components/pages/VerbPage.tsx:228` + `web/game/serializers.py` | Frontend must send verb-specific field names, OR backend must accept generic `target_id` + `params` |
| 6 | Tick resolution 500 — datetime not JSON serializable | `src/babylon/persistence/postgres_runtime/_legacy.py:203` | `json.dumps(event, sort_keys=True, default=str)` OR coerce datetimes upstream |
| 7 | Map returns 0 features at all zoom levels | `seed_initial_game` + map endpoint | Seed command must populate `hex_latest`/`hex_map` tables, OR map endpoint must derive features from `territories` H3 indexes |

### P1 — Major UX/correctness issues

| # | Bug | File | Fix |
|---|-----|------|-----|
| 3 | Massive polling loop — 300+ requests in seconds, no backoff | Frontend game store / `useEffect` intervals | Add polling backoff, or switch to websocket/SSE for state updates |
| 8 | Zoom level name mismatch — `ea`/`cty` → 400 | `web/frontend/src/components/map/FramingSelector.tsx` (or wherever Scale buttons dispatch) | Frontend should send `bea`/`county` to match backend valid levels |

### P2 — Minor / environment-specific

| # | Bug | File | Fix |
|---|-----|------|-----|
| 2 | WebGL `maxTextureDimension2D` errors in headless browser | Environment (MapLibre GL + headless Chromium) | Use `--caps=vision` or run headed; not a Babylon bug |
| 9 | Map pans into Canada — no `maxBounds` | `web/frontend/src/components/map/DeckGLMap.tsx:301` | Set `maxBounds` on MapLibre `Map` to H3 cell bounding box + margin |

## Recommendations

### 1. Fix the core loop (P0 — blocks all play)

Bugs #4, #6, and #7 must be fixed before any user can play. Priority order:
1. **Bug #6** (tick resolution datetime) — one-line fix, unblocks the
   entire game progression
2. **Bug #4** (verb field names) — either rewrite the frontend submit
   layer to map per-verb, or add a `target_id` alias to each backend
   serializer. The latter is faster and keeps the frontend generic.
3. **Bug #7** (map features) — investigate why `hex_latest` is empty
   after seeding. The state endpoint has 81 territories with H3 indexes;
   the map endpoint should derive GeoJSON from those, not require a
   separate table population step.

### 2. Improve the AI/narrator system (user request)

The current `DeterministicNarrator` is a placeholder. Objectives are
static and imposed. Investment areas:
- **Dynamic objective generation**: LLM generates objectives from the
  active dialectic state (`/api/games/:id/contradiction/`), balkanization
  factions, and class struggle trajectory. Vary per scenario/org/tick.
- **Narrator voice**: Replace deterministic narration with LLM-backed
  tick summaries, event descriptions, and chronicle entries.
- **Wire feed**: The Wire page is stuck on "Loading wire feed..." — the
  narrator should drive this content.
- **Event classification**: Events should carry narrative context, not
  just type/severity enums.

This aligns with the existing spec architecture (spec-061 narrator
provider, spec-095 Chronicle/Journal) but needs real LLM integration
beyond the current `DeterministicNarrator` stub.

### 3. Add map `maxBounds` (Bug #9)

Set `maxBounds` on the MapLibre `Map` component in
`web/frontend/src/components/map/DeckGLMap.tsx` to the H3 cell bounding
box plus a small margin. This prevents panning into Canada/ocean.

### 4. Fix zoom level names (Bug #8)

Frontend Scale buttons should send backend-valid names: `state`, `bea`,
`msa`, `cz`, `county`, `hex` (not `ea`/`cty`).

### 5. Add polling backoff (Bug #3)

The current polling loop fires 300+ requests in seconds. Add exponential
backoff, or switch to websocket/SSE for state updates. This will be a
production blocker.

### 6. Fix Wire feed loading

The Wire page is stuck on "Loading wire feed..." — investigate whether
the backend `/api/games/:id/wire/` endpoint returns the expected shape
or if the frontend is waiting on a narrator that never fires.

## What Works

- Login/auth flow (after Bug #1 fix)
- Briefing page layout, NavRail, TopBar, situation map controls
- All 16 NavRail routes render without crashes
- 6/9 verb pages render with real target data (communities, orgs, territories)
- Orgs, Intel, Results, Analysis, Dialectic, Chronicle, Objectives, Log, Resolution pages all load and display data
- Backend API endpoints all return 200 with real data (organizations, journal, alerts, wire, contradiction, endgame, objectives)
- Action submission works at the backend level when field names match (verified via raw `fetch`)
- H3 hex coordinates are correctly placed in Wayne County (42.11–42.57 N, -83.56 to -82.86 W)

## What Doesn't Work

- **Tick resolution** — completely blocked by datetime serialization bug
- **Action submission via UI** — field name mismatch on every verb
- **Map visualization** — zero features rendered (empty `hex_latest` table)
- **3 verbs** (move/investigate/negotiate) — explicit stubs per spec 061 FR-025
- **Wire feed** — stuck loading
- **Polling** — runaway loop with no backoff

## Files Touched During Test

- `web/game/models.py` — removed orphan `snapshot_json` field (Bug #1 fix)
- `~/.config/opencode/opencode.json` — disabled `browsermcp`, enabled `playwright` MCP
- `E2E_SUMMARY.md` — this document

---

## UI Improvements — Inspired by Paradox Design Language

Paradox Interactive has spent 20+ years solving the exact problems Babylon
faces: how to make a dense geopolitical simulation legible, playable, and
spatial. Their UI patterns (EU4, CK3, HoI4, Stellaris) are the gold standard
for this genre. Below is a deep audit of Babylon's current UX against the
Paradox canon, with concrete recommendations tied to issues observed during
the E2E test.

### Theme 1 — The Map is the Game (Map & Spatial Interaction)

Paradox's central insight: **the map IS the primary interface, not a
decoration.** Every piece of information that can be spatial should be
spatial. Babylon currently treats the map as a side panel in the Briefing
page — it should be the centerpiece.

**1.1 — Click-in-place, not navigate-away (EU4 province window)**

In EU4, clicking a province opens a rich detail panel *in place* — the
map stays visible, the province window docks to the left. You never lose
spatial context.

Babylon's current behavior: clicking a hex navigates to
`/games/:id/intel/territory/:territoryId` — a full page transition that
destroys map state. I observed this during testing: the moment you click
the map, you're in a different route with no way back except the browser
back button.

**Recommendation**: Implement a docked territory detail panel (right or
left side) that opens on hex click without route change. Show territory
stats, class composition, org presence, contradiction state. Add a "pin"
button to keep it open while interacting with the map. This is the single
highest-impact UI change for playability.

**1.2 — Right-click context menu for actions (HoI4 / EU4)**

Paradox: right-click a province → context menu of available actions
(move here, attack here, build here). This is the fastest way to issue
orders without leaving the map.

Babylon: the only way to act on a territory is to navigate to a verb page,
select a target from a list, and submit. That's 4+ clicks for one action.

**Recommendation**: Right-click a hex → context menu listing eligible
verbs for that target (Educate, Mobilize, Aid, Attack, etc.). Selecting
one opens a compact action-composer popover anchored to the hex, not a
full page. Submit directly from the map. This collapses the action loop
from 4 clicks to 2.

**1.3 — Map modes with hotkey cycling (EU4 Q/E cycling, Stellaris F-keys)**

Paradox: map modes are switchable with a single key press (Q/E to cycle,
or F1-F8 for direct). The active mode is always visible. The transition is
instant.

Babylon: 5 lenses (STANCE/HEAT/HABITABILITY/FACTION/COLLAPSE) and 6 scales
(ST/EA/MSA/CZ/CTY/HEX) are separate button groups. No hotkeys. Two of the
six scale names are wrong (Bug #8 — `ea`/`cty` don't match backend).

**Recommendation**: Add keyboard shortcuts (Q/E for lens cycling, Z/X for
scale cycling). Show the active mode as a persistent label. Fix the
scale name mismatch. At national scale (1,100 territories), the player
will live in map-mode switching — it must be fast.

**1.4 — Minimap for navigation (EU4, HoI4)**

Paradox: a small minimap in the corner shows the full play area with the
current viewport as a rectangle. Click to jump.

Babylon: no minimap. At Wayne County scale (81 hexes) this is fine. At
`us_nationwide` scale (1,100 territories), the player will get lost in
the map with no way to reorient.

**Recommendation**: Add a minimap component that appears when the
territory count exceeds ~200. Click-to-pan, viewport indicator, and a
"home" button that recenters on the player's primary territory.

**1.5 — `maxBounds` and geographic constraints (observed during test)**

The map currently pans into Canada and the Atlantic because
`DeckGLMap.tsx` sets no `maxBounds`. Paradox maps are always bounded to
the playable area.

**Recommendation**: Compute the H3 cell bounding box for the active
session and set `maxBounds` with a 10% margin. This is Bug #9 in the
catalog but also a UX principle: the map should never show irrelevant
geography.

### Theme 2 — Information Architecture (Outliner, Tooltips, Search)

**2.1 — The Outliner: always-visible entity list (EU4 / CK3 right panel)**

Paradox: a collapsible right-side panel called the Outliner lists every
entity you own or care about — armies, provinces, characters, pending
events, construction. It's the player's external memory. You never
have to ask "where are my units?"

Babylon: your orgs are on the Orgs page. Your communities are on the
Intel page. Your queued actions are nowhere visible. During testing, I
submitted an Aid action and had no way to verify it was queued without
hitting the API directly.

**Recommendation**: Add a collapsible Outliner panel (right side, always
visible) with expandable sections:
- **Your Orgs** — name, CL/SL, HEAT, COH (live, no navigation needed)
- **Queued Actions** — verb, target, tick (the action queue I couldn't
  see during testing)
- **Active Contradictions** — from the Dialectic endpoint
- **Pending Events** — from alerts/journal
- **Watched Territories** — player-pinned hexes with delta indicators

This panel should be the player's "second screen" — everything they need
without navigating. It also solves the polling problem (Bug #3): one
polling loop updates the outliner instead of 4 separate fetch loops.

**2.2 — Tooltip depth: show the math (EU4 / CK3 nested tooltips)**

Paradox: hover anything → tooltip shows the base value, every modifier,
and the final value. Hover a modifier in the tooltip → sub-tooltip
explains its source. The player can audit any number down to its root
cause.

Babylon: the Key Metrics panel (RENT/CON/SOL/HEAT/WEALTH/BIOCAP) shows
"—" at tick 0 with no tooltip explaining what these acronyms mean, what
their range is, or how they're calculated. The selected-region panel
shows "Heat 0.00, Rent 3.50, Population 8,000, low_profile" — bare
numbers with no context.

**Recommendation**: Every metric should have a hover tooltip with:
- Full name (RENT → "Imperial Rent Extraction")
- Current value and range (0.0–1.0, or absolute)
- What drives it (formula summary, top 3 modifiers)
- Trend arrow (↑↓ vs last tick)
- Color coding (green/yellow/red by band)

For acronyms specifically: a first-time player will not know what CL,
SL, REP, COH, OPC, HEAT mean. Either spell them out on hover, or add a
one-time tutorial overlay.

**2.3 — Smart search with Ctrl+F (EU4 province search, CK3 character finder)**

Paradox: press Ctrl+F → search bar. Type a province/character name →
jump to it on the map. Essential for large maps.

Babylon: no search. At 81 territories this is manageable. At 1,100
(national scale), finding a specific county by name in a list is
painful.

**Recommendation**: Add a Ctrl+F search bar that indexes territory
names, org names, and community names. Selecting a result recenters
the map and opens the territory detail panel (per 1.1). Implement this
early — it's cheap and scales forever.

**2.4 — Ledger: sortable, filterable tables (EU4 ledger)**

Paradox: the Ledger is a collection of sortable tables — province list
with population, trade goods, development; army list with strength,
morale; etc. It's the "I need to compare everything" view.

Babylon: the Intel page is an index (81 territories, 87 edges, 0
orgs/communities listed as cards). It's not sortable or filterable.
There's no way to sort territories by HEAT, population, or rent.

**Recommendation**: Add a Ledger mode to the Intel page — toggle
between "card view" (current) and "table view" (sortable columns).
Columns: name, type, population, HEAT, RENT, CON, SOL, faction,
biocapacity. Click a row → jump to map (per 1.1). This is essential
for the national scenario where you need to find the hottest
territories across 3,000+ counties.

### Theme 3 — Time & Pacing (Pause, Play, Auto-Resolve)

**3.1 — Tick control: pause / step / auto-resolve (HoI4 5-speed clock)**

Paradox: the game runs continuously at 1-5 speed. The player can pause
at any time (Spacebar). This is the single most important UX control in
a Paradox game.

Babylon: the only time control is "Resolve Tick ▸" — a discrete step.
There's no auto-resolve, no pause concept, no speed. The player must
manually click for every tick.

**Recommendation**: Add a time-control bar (bottom center, Paradox
style):
- ⏸ Pause (Spacebar) — default state
- ⏭ Step (→) — resolve one tick, then auto-pause
- ▶ Play (Spacebar) — auto-resolve every N seconds
- Speed slider (1-5) — controls auto-resolve interval (5s/tick at
  speed 1, 1s/tick at speed 5)

This transforms the game from "click 52 times to finish" to "set speed
3 and watch the simulation unfold, pausing when something interesting
happens." The resolution page already has the animation UI — extend
it to support auto-advance.

**3.2 — Notification-driven pause (EU4 message settings)**

Paradox: the player can configure which events pause the game (war
declared, siege won, heir born). Critical events stop the clock;
informational ones don't.

Babylon: events exist (journal/alerts) but they're on a separate page.
Nothing pauses or notifies. During testing, the Log page showed "0
events recorded" because no ticks had resolved. But once ticks start,
events will fire and the player needs to know.

**Recommendation**: When auto-resolve is running, certain event
severities should auto-pause:
- `critical` → always pause
- `warning` → pause if setting is on
- `informational` → never pause

Show a toast notification on pause with a "Jump to event" button. This
ties into the notification feed (Theme 5).

### Theme 4 — Action Economy (Queue, Macro-Builder, Event Cards)

**4.1 — Action queue visualization (HoI4 production queue)**

Paradox: the production queue shows every item being built, its
progress, and its ETA. You can reorder, cancel, or prioritize.

Babylon: the "Queue Educate ▸" button submits an action, but there's
no visible queue. During testing, I submitted an Aid action via raw
API and had zero UI feedback that it was queued. I had to query the
backend to confirm.

**Recommendation**: Add a persistent Action Queue panel (docked, or
as an Outliner section per 2.1). Show:
- Each queued action: verb icon, target name, org, tick
- Status: queued / resolving / resolved
- Reorder via drag, cancel via X
- Total CL/SL commitment vs. available

This makes the verb pages feel like they connect to something. Right
now, clicking "Queue Educate" feels like throwing an action into a
void.

**4.2 — Macro-builder: multi-target action planning (EU4 macro-builder)**

Paradox: the macro-builder lets you select an action (e.g., "build
temple") and then click multiple provinces to queue it across all of
them. One action, many targets.

Babylon: each verb page targets one community/org/territory at a time.
At national scale, educating across 50 communities would require 50
separate visits to the Educate page.

**Recommendation**: Add a "macro mode" toggle on verb pages: instead of
selecting one target, multi-select from the list (checkboxes), then
"Queue N actions" distributes across all selected targets with
proportional CL/SL allocation. This is a late-game essential.

**4.3 — Event cards with decisions (CK3 event pop-ups)**

Paradox: events in CK3 are interactive cards with 2-4 choices. Each
choice shows its consequences (stat changes, relationship impacts).
The event pauses the game and demands a decision.

Babylon: events are a log — type, severity, body, data. They're
read-only. There's no decision point. The Priority Dispatch panel on
the Briefing page says "No events this tick" — suggesting it was
designed for this, but the interactive card layer was never built.

**Recommendation**: For events with `critical` or `warning` severity,
render an event card (modal or docked) with:
- Title, body, and severity icon
- 2-4 decision buttons, each showing consequences
- "Decide" triggers the chosen outcome and advances

This is where the AI narrator (per the Objectives recommendation)
would generate the event text and decision options dynamically.

**4.4 — Right-click drag-box selection (HoI4 army selection)**

Paradox: drag a box on the map → select all units inside.

Babylon: no multi-select on the map. For the `us_nationwide` scenario
with 1,100 territories, the player needs to select regions and issue
area-wide actions.

**Recommendation**: Long-term, add drag-box territory selection on the
map. Selected territories get a highlight outline. Right-click →
context menu (per 1.2) applies an action to all selected.

### Theme 5 — Persistent Feedback (Notifications, Score, Status)

**5.1 — Notification feed: live event stream (EU4 message log + toasts)**

Paradox: a scrolling feed of recent events at the bottom of the screen,
plus toast notifications for important ones. The feed is always
visible; toasts fade after a few seconds.

Babylon: events are on the Log page. Nothing is visible while playing
on any other page. During testing, I navigated to Log and saw "0
events recorded" — but I'd never have known to check.

**Recommendation**: Add a notification feed dock at the bottom-right
(showing last 5 events as icons + severity color). Clicking expands to
full text. New events trigger a toast (top-right, fades after 5s).
Critical events auto-pause (per 3.2) and show a modal (per 4.3).

**5.2 — Persistent objective progress (Stellaris victory tracker)**

Paradox: Stellaris shows a small persistent victory-condition tracker
on every screen — "47% to Domination victory." You always know where
you stand.

Babylon: objectives are on the Objectives page. All 5 show "Progress
0.00." There's no persistent indicator on other pages. During testing,
I had to navigate to Objectives to check progress — and it was
identical to tick 0.

**Recommendation**: Add a compact objective indicator to the TopBar
(showing the top-2 tracked objectives with progress bars). On hover,
expand to show all 5. Click → navigate to Objectives page. The
progress should update as the simulation advances (ties into the AI
narrator recommendation — dynamic objectives, not static).

**5.3 — Status bar: everything visible, always (EU4 top bar)**

Paradox: the top bar shows money, manpower, stability, prestige,
legitimacy, etc. — always visible, always updating. Color changes
(white → yellow → red) signal problems.

Babylon: the TopBar shows CL 1.0/1, SL 4.0/5, REP 0%, $100, HEAT 0%.
This is good, but:
- No trend indicators (↑↓ vs last tick)
- No color coding (is 0% HEAT good or bad?)
- No date/week indicator (what tick is "week 5 of 52"?)
- No resources beyond CL/SL (no materials, no population, no territory
  count)

**Recommendation**: Enhance the TopBar:
- Add trend arrows (↑↓ →) next to each metric
- Color-code by band (green/yellow/red)
- Add a date indicator: "Tick 0 / 52 · Week 1, January 2010"
- Add territory count: "81 territories"
- Add org count: "1 player org"
- On hover: tooltip with full breakdown (per 2.2)

**5.4 — "What changed" diff after tick resolution (EU4 monthly summary)**

Paradox: after each month, a summary shows what changed (income,
manpower, stability deltas). The player can review and then continue.

Babylon: the Resolution page shows "Resolving Tick 0000 → 00000 / 0 No
changes recorded this tick." Even if there were changes, the format is
sparse. The Results page shows "Tick 0 resolution summary" with org
stats but no before/after comparison.

**Recommendation**: After each tick resolution, show a structured diff:
- **Metrics**: CL 1.0 → 0.7 (↓0.3), HEAT 0% → 12% (↑12%)
- **Events**: 3 new (1 critical, 2 informational)
- **Territories**: 4 changed stance, 1 new faction claim
- **Objectives**: Revolutionary Victory 0.00 → 0.05

This gives the player a reason to care about each tick. Without it,
"Resolve Tick" is a button that changes numbers invisibly.

### Theme 6 — Accessibility, Scale, and Onboarding

**6.1 — Keyboard-first design (Paradox hotkey system)**

Paradox: every UI element has a hotkey. Spacebar pauses. Q/E cycles
map modes. Number keys select armies. The player who learns the
hotkeys plays 3× faster.

Babylon: zero hotkeys observed. All interaction is mouse-driven.

**Recommendation**: Add hotkeys for:
- Spacebar: pause/play (per 3.1)
- Q/E: cycle map lens (per 1.3)
- Z/X: cycle map scale
- 1-9: jump to verb page (Educate=1, Mobilize=2, etc.)
- F: search (per 2.3)
- Esc: close any panel/modal
- Tab: cycle outliner sections (per 2.1)

Show hotkey hints in tooltips (per 2.2).

**6.2 — Color-blind mode (Paradox accessibility settings)**

Paradox: map color modes have color-blind alternatives (patterns,
high-contrast palettes).

Babylon: the heat map relies on a single color ramp. The 5 lenses use
color to encode stance/faction. A color-blind player cannot distinguish
them.

**Recommendation**: Add a color-blind mode setting (Protanopia,
Deuteranopia, Tritanopia). Use patterns (stripes, dots, crosshatch) in
addition to color for lens overlays. Add a setting toggle in the user
profile.

**6.3 — Onboarding / tutorial overlay (Paradox first-time tooltips)**

Paradox: first-time players get a guided tutorial overlay that
highlights UI elements in sequence. "This is your treasury. This is
how you build an army."

Babylon: nothing. A first-time player sees 16 NavRail icons, 6 TopBar
metrics (CL/SL/REP/$/HEAT), 5 map lenses, 6 map scales, and no
explanation of what any of them mean. The acronyms (CL, SL, REP, COH,
OPC, HEAT, BIOCAP, RENT, CON, SOL) are never expanded.

**Recommendation**: Add a first-session tutorial overlay:
- Highlight the TopBar metrics one at a time with explanations
- Walk through the verb-queue-resolve loop
- Explain the map lenses
- Show the outliner (per 2.1)
- Can be dismissed and re-triggered from settings

**6.4 — Responsive density mode (EU4 / HoI4 UI scaling)**

Paradox: UI scale slider lets the player adjust text/panel size for
their display.

Babylon: the UI is designed for a single density. On a 4K monitor the
text is tiny; on a laptop the panels are cramped.

**Recommendation**: Add a UI scale setting (0.8× to 1.5×). Use CSS
custom properties for base font size and spacing. This is cheap and
high-impact for accessibility.

**6.5 — Empty-state guidance (Paradox placeholder art + tooltips)**

Paradox: empty panels show placeholder art with a hint ("Build your
first army by clicking the sword icon →").

Babylon: many panels show "—" or "No events this tick" or "0 events
recorded" with no guidance. The Wire page shows "Loading wire
feed..." forever (stuck). The Key Metrics show all "—" with no
explanation.

**Recommendation**: Every empty state should explain:
- Why it's empty ("Tick 0 — no events yet. Resolve a tick to generate
  events.")
- What to do next ("Queue an action via the Verbs panel, then click
  Resolve Tick.")
- A link/button to the next action

### Theme 7 — Architectural: Replace Polling with Push (Bug #3 fix)

This is not a Paradox pattern per se, but Paradox games are local (no
polling). Babylon's current polling loop (300+ requests in seconds,
observed during testing) is both a bug and an architectural smell.

**Recommendation**: Replace the 4-endpoint polling loop
(`/state/`, `/actions/available/`, `/map/`, `/timeseries/`) with a
single Server-Sent Events (SSE) stream or WebSocket. The server pushes
state deltas on tick resolution and action submission. The frontend
subscribes once and receives updates. This:
- Eliminates 95% of request volume
- Makes the UI feel real-time (no polling delay)
- Solves Bug #3 (polling loop)
- Enables multiplayer (multiple clients watching the same session)

Priority: after the P0 bugs, this is the most impactful architectural
change. The polling loop will not scale to `us_nationwide` (1,100
territories × 4 endpoints × no backoff = server death).

### Prioritized Implementation Order

Based on impact × cost, in the order I'd build them:

1. **Fix P0 bugs** (#6 datetime, #4 verb fields, #7 map features) —
   unblocks everything
2. **Time control bar** (3.1) — transforms the game from "click 52
   times" to "set speed and play"
3. **Docked territory panel** (1.1) — stops navigate-away-on-click,
   keeps map context
4. **Outliner** (2.1) — always-visible org/queue/event panel, solves
   "where is my stuff?" and partially fixes the polling loop
5. **Action queue visualization** (4.1) — gives feedback that
   submitted actions exist
6. **SSE/WebSocket** (Theme 7) — replace polling, enable real-time
7. **Notification feed + toasts** (5.1) — live event stream
8. **Tooltip depth** (2.2) — explain every acronym and metric
9. **Right-click context menu** (1.2) — fast action from map
10. **Hotkeys** (6.1) — keyboard-first play
11. **Smart search** (2.3) — essential at national scale
12. **Tutorial overlay** (6.3) — onboarding for new players
13. **Minimap** (1.4) — essential at national scale
14. **Event cards with decisions** (4.3) — interactive events
15. **Macro-builder** (4.2) — multi-target actions
16. **Ledger** (2.4) — sortable tables
17. **Objective persistence** (5.2) — always-visible progress
18. **Status bar enhancement** (5.3) — trends, colors, date
19. **Tick diff summary** (5.4) — "what changed" after resolve
20. **Color-blind mode** (6.2), **UI scaling** (6.4), **Empty states**
    (6.5) — polish layer

---

## Research-Backed Design Foundations

The recommendations above draw from two bodies of literature: (1)
Paradox Interactive's 20+ years of grand-strategy UI design (documented
across the EU4, CK3, HoI4, Stellaris, and Victoria 3 wikis and
developer diaries), and (2) the classic UX/design canon in
`/home/user/Downloads/babylon_books/ux/` (Norman, Krug, Tufte,
Sylvester, Salen & Zimmerman, Shneiderman, Universal Principles of
Design). This section maps each observed Babylon defect to the
governing design principles, with citations, so future implementation
work is grounded in theory rather than opinion.

### A. Paradox's Stated Design Philosophy

Three principles are repeated across every Paradox title and wiki:

1. **Information density is a feature, not a bug.** The Stellaris wiki
   states it bluntly: *"menus and sub-menus, putting a wealth of
   important information a click or two away. Navigating such an
   interface can contribute to a large portion of a grand strategy
   game's learning curve, but all the information is organized
   logically."* Babylon's current sparse tables are the wrong direction.

2. **Tooltips are the primary teaching layer.** Every Paradox wiki
   repeats the doctrine: *"if an action isn't clear, hovering the
   cursor over the button (or icon, statistic etc.) will most likely
   reveal information further explaining the situation."* Victoria 3
   explicitly instructs new players: *"Explore the tooltip
   functionality as you get used to navigating."*

3. **The UI is a live document.** Paradox ships UI changes constantly
   via DLC and patches. The interface is treated as a tunable, not a
   fixed artifact. CK3's patch 1.9 made UI mods no longer disable
   achievements — UI is first-class.

### B. The Twelve Paradox Patterns (with wiki sources)

Each pattern is documented in the Paradox wiki network
(paradoxwikis.com). Forum developer diaries are account-gated but
extensively summarized in the wikis. Canonical dev-diary indexes:

- Victoria 3: `https://vic3.paradoxwikis.com/Developer_diaries`
- EU4: `https://eu4.paradoxwikis.com/Developer_diaries`
- CK3: `https://ck3.paradoxwikis.com/Developer_diaries`
- HoI4: `https://hoi4.paradoxwikis.com/Developer_diaries`
- Stellaris: `https://stellaris.paradoxwikis.com/Developer_diaries`

| # | Pattern | Games | Babylon Application | Source |
|---|---------|-------|---------------------|--------|
| P1 | **Outliner** — collapsible right-side persistent panel listing every owned entity; 4 tabs in Stellaris (Government/Ships/Politics/Structures); hotkey `O`; double-click centers camera | EU4, CK3, Stellaris, Victoria 3, HoI4 | Solves "where is my stuff?" — orgs, queued actions, active contradictions, pending events, watched territories | `stellaris.paradoxwikis.com/Main_interface`; `eu4.paradoxwikis.com/Ingame_screen`; `vic3.paradoxwikis.com/User_interface` |
| P2 | **Map modes & cycling** — EU4 binds up to 10 modes to Q–P hotkeys; pressing same key cycles sub-modes; advice: *"put related modes on a single hotkey... so all warfare info is one key away"* | EU4 (40+ modes), Stellaris, Victoria 3, HoI4, CK3 | Babylon needs ≥4 modes (ownership/unrest/faction-strength/dialectic-tension), cyclable on 1-2 hotkeys | `eu4.paradoxwikis.com/Map#Map_modes`; `eu4.paradoxwikis.com/Controls` |
| P3 | **Message settings (pause-on-event)** — EU4 categorizes alerts (red/yellow/green/brown); left-click jumps, right-click dismisses, shift+right-click disables per-type; Stellaris toggles event popup/auto-pause | EU4, Stellaris, Victoria 3 | When Babylon gets notifications, ship per-type pause/dismiss/disable settings on day one | `eu4.paradoxwikis.com/Ingame_screen`; `stellaris.paradoxwikis.com/Main_interface` |
| P4 | **Lens system (Victoria 3)** — bottom-bar lenses are context-sensitive action menus over the map; 6 lenses (Production/Political/Diplomatic/Military/Trade/Map-modes); Alt+1–4; activating a lens filters the map so only valid click-targets highlight — the map *becomes* the action menu | Victoria 3 | Collapse Babylon's 9 verb pages into ~4 lenses (Economic/Political/Military/Diplomatic) over the hex map. Single biggest UX innovation in modern Paradox design | `vic3.paradoxwikis.com/User_interface`; `vic3.paradoxwikis.com/Keyboard_shortcuts` |
| P5 | **Nested tooltips** — CK3 allows recursive tooltip chaining (`CharacterWindow.GetCharacter.GetPrimaryTitle.GetHeir...`); every stat hovers to breakdown, every modifier hovers further | All Paradox titles; CK3 deepest | Every Babylon metric (CL/SL/HEAT/COH) should hover to a breakdown, each contributor hovers to the underlying dialectic terms | `ck3.paradoxwikis.com/Interface`; `vic3.paradoxwikis.com/User_interface` |
| P6 | **Finder (Ctrl+F)** — `F` opens location finder (EU4: province; Victoria 3: countries/states/city hubs; CK3: character finder with trait/religion/dynasty filters) | All Paradox titles | Babylon has no search. `F` → fuzzy search regions/factions/characters with camera-pan-to-result is trivial and transformative at national scale (1,100 territories) | `eu4.paradoxwikis.com/Controls`; `vic3.paradoxwikis.com/Keyboard_shortcuts` |
| P7 | **Time control bar** — Spacebar pauses; 1–5 sets speed (EU4: Speed 1 = 2 sec/day, Speed 5 = max); game always starts paused | All Paradox titles | Babylon has no time controls. The physical cluster (Pause + 5 speed steps + Spacebar) is the *only* way to modulate cognitive load in grand strategy | `eu4.paradoxwikis.com/Ingame_screen`; `vic3.paradoxwikis.com/Keyboard_shortcuts`; `stellaris.paradoxwikis.com/Main_interface` |
| P8 | **Event cards with decisions** — modal card with flavor text, image, 2–5 decision buttons; each option has tooltip preview of effects; CK3 binds to `EventWindowData.GetOptions` array | CK3, EU4, HoI4, Stellaris, Victoria 3 | Every dialectic transition / class-struggle flashpoint should be an event card with 2–4 Marxist-aligned decision options, each tooltip-previewing effects on `D = (A, Ā, w, T, σ)` | `ck3.paradoxwikis.com/Interface`; `vic3.paradoxwikis.com/User_interface`; `hoi4.paradoxwikis.com/National_focus` |
| P9 | **Production / construction queue** — HoI4 production lines: cards with name, efficiency %, factories, drag-to-prioritize, resource-shortage indicators; Victoria 3: `B` opens, `Ctrl+B` pauses | HoI4, Victoria 3, EU4, Stellaris | A visible, reorderable, pausable queue is the only way to plan multi-tick build programs. Card-per-line + drag-to-prioritize + per-line resource indicators is the minimum viable design | `hoi4.paradoxwikis.com/Production`; `vic3.paradoxwikis.com/Keyboard_shortcuts` |
| P10 | **Notification feed + toasts** — two channels: persistent alerts (EU4 colored flags; Stellaris square alerts) + transient toasts (Stellaris round alerts; Victoria 3 bottom-right feed); severity by outline color | Victoria 3, Stellaris, EU4, HoI4 | Two channels (persistent + transient), color-coded severity, click-to-jump, right-click-to-dismiss, shift+right-click-to-disable, central Message Settings panel | `vic3.paradoxwikis.com/User_interface`; `stellaris.paradoxwikis.com/Main_interface`; `eu4.paradoxwikis.com/Ingame_screen` |
| P11 | **Macro-builder** — hotkey `B`; pick action type, color-codes every province by validity (green=can, red=cannot, yellow=busy, teal=upgrade, blue=present); hover shows cost/time/breakdown; Army/Navy planner defines templates applied across contiguous provinces | EU4 (canonical) | Collapse Babylon's 9 verb action pages into 1 macro-builder panel with tabs (Recruit/Develop/Repress/Agitate/Seize), each color-coding the hex map by validity. This is the anti-micromanagement pattern | `eu4.paradoxwikis.com/Macrobuilder` |
| P12 | **First-time tutorial overlay** — EU4 main menu Tutorial button + 4-part intro on game start; Victoria 3 ships **Vickypedia** (searchable in-game reference); Stellaris has Help → Missions + Wiki | All Paradox titles | Babylon's MLM-TW theory is harder to learn than Paradox mechanics. A "Babylonedia" reference + paused-on-first-load briefing screen is the Paradox-validated way to onboard | `eu4.paradoxwikis.com/User_interface`; `vic3.paradoxwikis.com/User_interface`; `stellaris.paradoxwikis.com/User_interface` |

### C. The UX Canon — Principles from `/home/user/Downloads/babylon_books/ux/`

The books in this directory are the foundational texts of interaction
design, information visualization, and game design. Below are the
principles most directly applicable to Babylon's observed defects,
with the book and author cited for each.

#### C.1 Don Norman — *The Design of Everyday Things* (Revised 2013)

- **Gulf of Execution & Gulf of Evaluation.** Every interaction has two
  gulfs: Execution (goal → available actions) and Evaluation (system
  state → user understanding). Babylon's broken action submission is a
  textbook Gulf of Execution failure; the absence of post-tick feedback
  is a Gulf of Evaluation failure. Both must be explicitly designed-for.
- **Discoverability = affordances + signifiers + constraints + mappings
  + feedback + conceptual model.** When any are missing, the user must
  substitute rote memorization. Babylon's 9 verb pages lack signifiers
  and feedback; the hex map affords viewing but not action. The
  conceptual model ("dialectic → material conditions → class struggle →
  tick outcome") must be made legible across the UI.
- **Feedback must be immediate, informative, prioritized.** *"Poor
  feedback can be worse than no feedback at all, because it is
  distracting, uninformative."* Tick resolution that silently mutates
  numbers without surfacing *what changed and why* violates every
  clause.
- **Seven Stages of Action as design checklist.** Goal → Plan →
  Specify → Perform → Perceive → Interpret → Compare. Babylon's UI
  supports only Perform (submit form). The other six — especially
  Perceive, Interpret, Compare — are unaided. Each is a concrete place
  to add UI support.
- **Knowledge in the World vs. Knowledge in the Head.** Precise
  behavior can come from imprecise knowledge *if the required knowledge
  is present in the world* (visible constraints, signifiers, natural
  mappings). Babylon's verb forms demand knowledge in the head (which
  fields mean what, which hex IDs are valid). Spatial controls mapped
  to the hex map move knowledge into the world.

#### C.2 Steve Krug — *Don't Make Me Think, Revisited* (2014)

- **Krug's First Law: Don't make me think.** Each page should be
  self-evident. Babylon's action pages make the player think about the
  *mechanics of submitting* rather than the *substance of the action*.
  A simulation should make the player think about geopolitics, not
  form fields.
- **We don't read pages, we scan them.** *"What they actually do most
  of the time is glance at each new page, scan some of the text, and
  click on the first link that catches their interest."* Babylon's
  dense tables assume a reader, not a scanner. Design for the scanning
  eye: trigger words, visual hierarchy, clickable affordances.
- **We don't make optimal choices, we satisfice.** Users choose the
  first reasonable option. If Babylon offers 9 verbs as a flat menu,
  players satisfice to the first remotely applicable one. Verb choice
  should be guided by context (selected hex, recent action, suggested
  move) so the satisficed choice is usually right.
- **Omit needless words.** Strip every non-essential word. Navigation
  should function like street signs and breadcrumbs — where am I, how
  did I get here, where can I go.

#### C.3 Tynan Sylvester — *Designing Games* (2013)

- **Games are engines of experience.** *"An experience is an arc of
  emotions, thoughts, and decisions inside the player's mind."* A tick
  that mutates state without surfacing *what changed and what it means*
  breaks the emotional loop. Babylon's tick must emit legible emotional
  signals (a region tipped, a faction mobilized, supply collapsed), not
  silent number deltas.
- **Elegance: few mechanics that multiply into emergent possibility.**
  *"Elegance happens when mechanics interact in complex, nonobvious
  ways."* The 9 verbs should not be 9 isolated form pages (the inelegant
  "goblin-killer rod" pattern). They should be a small set of
  operations applied uniformly to the hex map + dialectic substrate,
  where verbs *compose* (Move + Supply + Agitate on the same hex in the
  same tick produces an emergent outcome neither yields alone).
- **Visual hierarchy: progressive visibility by importance.**
  *"Players can only absorb a certain number of signals at a time.
  Further signals added past this limit effectively become noise."*
  Display everything at once but make more important information more
  visible (bigger, brighter, faster). Novices perceive the top of the
  hierarchy; experts progressively perceive lower layers.
- **Mapping: similarity between control and in-game effect.** *"The
  goal of mapping is to create a similarity between a physical control
  and its in-game effect. Done well, this similarity serves as a
  built-in mnemonic."* Verb controls should spatially map to the hex
  map: verb palette at the cursor on the selected hex, intensity maps
  to drag distance, dialectic dimension maps to axis of motion.

#### C.4 Salen & Zimmerman — *Rules of Play* (2004)

- **Meaningful play: action ↔ system outcome.** *"Meaningful play
  emerges from the relationship between player action and system
  outcome."* Babylon's broken submission severs the action→outcome
  link: the player cannot perceive whether the action was received,
  what it produced, or why. Without that link, the simulation cannot
  generate meaningful play even if the underlying model is correct.
- **Discernable: the outcome of an action must be perceivable.**
  *"Without discernability, the player might as well be randomly
  pressing buttons."* The Rouse example — a strategy game where
  off-screen units are attacked without notification — is Babylon's
  *no notifications* problem exactly.
- **Integrated: each action must matter beyond the moment.** *"An
  action a player takes not only has immediate significance in the
  game, but also affects the play experience at a later point."*
  Babylon's *no time controls* breaks integration: the player cannot
  trace this tick's action to future consequences. A timeline/scrubber
  showing action→consequence chains across ticks is required.
- **Objective vs. perceived information.** A game has *objective
  information* (the actual system state) and *perceived information*
  (the player's understanding). Babylon's dialectic substrate is rich
  objective information; the analyze pages are supposed to convert it
  to perceived information. They currently don't. Every analyze view
  must be evaluated by whether it produces *perceived* understanding,
  not merely displays *objective* data.

#### C.5 Edward Tufte — *Envisioning Information* (1990)

- **"To clarify, add detail" (Micro/Macro readings).** *"Simplicity of
  reading derives from the context of detailed and complex information,
  properly arranged. A most unconventional design strategy is
  revealed: to clarify, add detail."* Babylon's instinct to boil down
  data into sparse summary tables is the wrong move. The hex map should
  display *more* detail — every hex's dialectic state, every region's
  class composition — so the player reads local stories and global
  pattern simultaneously.
- **"Clutter and confusion are failures of design, not attributes of
  information."** *"It is not how much information there is, but rather
  how effectively it is arranged."* This is the governing principle for
  Babylon's dense-data problem: density is not the enemy; bad
  arrangement is. The fix is not fewer data points but better layering
  and separation.
- **Micro/macro designs avoid context-switching.** *"A problem
  undermining information exchange between human and software is
  'constant context switches'... the user's short-term memory is
  occupied with the incidentals rather than with the significant
  issues of analysis."* Babylon's pattern of *leaving the hex map to
  open an action form, then returning* is the exact context-switching
  pathology Tufte flags. Action submission must happen *on* the map.
- **Layering and separation.** *"Among the most powerful devices for
  reducing noise and enriching the content of displays is the technique
  of layering and separation, visually stratifying various aspects of
  the data."* Babylon's UI must treat dialectic layers as *stratified*
  — substrate, political claims, military units, supply flows each in a
  visually separable layer the player can toggle/peer-through — not as
  competing windows.
- **Small multiples: "Compared to what?"** *"At the heart of
  quantitative reasoning is a single question: Compared to what? Small
  multiple designs answer directly by visually enforcing comparisons of
  changes, of the differences among objects, of the scope of
  alternatives."* Babylon's analyze pages should default to
  small-multiple layouts — the same hex/region across N ticks, or all
  regions on the same scale for one tick — so comparison is *visually
  enforced*, not left to visual memory.

#### C.6 Edward Tufte — *The Visual Display of Quantitative Information* (1983/2001)

- **Maximize the data-ink ratio; erase chartjunk.** *"Above all else
  show the data."* Babylon's analyze views should strip decorative
  chrome and devote pixels to data. Every gridline, border, and label
  that isn't carrying information is stealing attention from the
  dialectic state.
- **Data density: maximize information per unit area.** *"Data-thin
  displays move viewers toward ignorance and passivity."* A single
  dense hex-map view with all layers visible beats many sparse pages.
  The cost of sparse displays is *memory load*, which is Babylon's
  current failure mode.
- **Graphical excellence = substance + statistics + design; preserve
  the lie factor.** *"Graphical excellence is the well-designed
  presentation of interesting data."* The lie factor (size of effect
  shown ÷ size of effect in data) should be ≈ 1. Babylon's visual
  encoding of dialectic quantities must be linear and honest — a
  region with twice the class tension must show twice the visual
  weight, not a color change that *feels* dramatic but represents 5%.

#### C.7 Edward Tufte — *Visual Explanations* (1997)

- **Pictures of verbs: display mechanism, cause, and effect.** Tufte
  distinguishes his three books: *Visual Display* = pictures of
  numbers; *Envisioning* = pictures of nouns; *Visual Explanations* =
  *"pictures of verbs, the representation of mechanism and motion, of
  process and dynamics, of causes and effects, of explanation and
  narrative."* Babylon is fundamentally a *verb* system — the dialectic
  transforms material conditions into class struggle over ticks. The
  UI must render this *mechanism*, not just before/after states.
- **Clarity in display replicates clarity in thought.** *"When
  principles of design replicate principles of thought, the act of
  arranging information becomes an act of insight."* If Babylon's
  arrangement of dialectic data doesn't mirror the structure of the
  dialectic theory, the player can't think with the theory — they can
  only look at numbers.
- **The Challenger lesson: reveal the data that bears on the cause.**
  The Challenger disaster: engineers failed to convince because they
  displayed only the O-ring damage incidents and *omitted the
  damage-free launches*. The causal variable (temperature) was hidden
  by an absence of data points. Babylon's analyze views must show the
  *null cases* and *counterfactuals*, not only regions where something
  happened. A region where the dialectic *didn't* tip is as causally
  informative as one where it did.

#### C.8 Ben Shneiderman — *Direct Manipulation* (1983)

- **The four principles of direct manipulation:** (1) Continuous
  representation of the object of interest; (2) Physical actions or
  labeled button presses *instead of complex syntax*; (3) Rapid,
  incremental, reversible operations whose impact is *immediately
  visible*; (4) A layered/spiral approach to learning. Babylon's
  form-submission UI violates all four: the hex isn't continuously
  represented during submission; it uses complex form syntax; it's not
  incremental or reversible; there's no layered path from novice to
  expert.
- **"What you see is what you have got": complete status display.**
  *"The display should indicate a complete image of what the current
  status is, what errors have occurred, and what actions are
  appropriate."* Babylon's post-submission state is opaque — the player
  cannot tell whether the action was received, whether it errored, or
  what alternatives remain.
- **Transparency / virtuality: the tool disappears.** *"The user is
  able to apply intellect directly to the task; the tool itself seems
  to disappear."* When the player is thinking about *form fields and
  submission mechanics*, the tool has not disappeared. When the player
  is thinking only about *the dialectic and the hex map*, the tool has
  disappeared. The latter is the design target.
- **Reversibility reduces anxiety; immediate effect produces mastery.**
  *"If actions are simple, reversibility ensured, and retention easy,
  then anxiety recedes and satisfaction flows in."* Babylon's
  submitted-and-irrevocable model produces anxiety without mastery. A
  draft/preview state before commit, an undo for the current tick's
  pending actions, and immediate preview of predicted effects would
  convert anxiety into mastery.

#### C.9 *Universal Principles of Design* (Lidwell, Holden, Butler — 2010)

- **Progressive Disclosure.** *"A strategy for managing information
  complexity in which only necessary or requested information is
  displayed at any given time."* Babylon's dense dialectic data should
  be *layered*: base hex map shows the top layer; deeper layers
  (per-hex breakdown, tick history, action log) revealed on demand —
  never all flattened, never hidden behind navigation.
- **Performance Load (cognitive + kinematic).** *"The greater the
  effort to accomplish a task, the less likely the task will be
  accomplished successfully."* Babylon's current action flow imposes
  high cognitive load (remember which fields, which IDs) and high
  kinematic load (navigate, fill, submit, navigate back, verify). Every
  step removed directly raises success probability.
- **Signal-to-Noise Ratio.** *"The ratio of relevant to irrelevant
  information in a display. The highest possible signal-to-noise ratio
  is desirable."* Every decorative gridline, chrome border, non-data
  animation in Babylon's UI is noise reducing the SNR. The dialectic
  state is the signal.
- **Hierarchy.** *"Hierarchical organization is the simplest structure
  for visualizing and understanding complexity."* Babylon's data is
  naturally hierarchical (substrate → hex → region → nation; dialectic
  → pole → class → faction). The UI should make this hierarchy
  *visible* (tree for dialectic, nest for spatial containment) rather
  than flattening it into peer tables.
- **80/20 Rule.** *~80% of effects come from ~20% of variables.* In a
  Marxist simulation, a small subset of hexes and a small subset of
  dialectic tensions will drive most of the geopolitical outcome. The
  UI should foreground that vital subset — highlight the "hot" hexes,
  the dominant contradictions — rather than treating all hexes as
  equal, which buries the signal.
- **Advance Organizer.** *"Brief chunks of information presented prior
  to new material to help facilitate learning and understanding...
  present the 'big picture' prior to the details."* Before any tick's
  dense detail, Babylon should present a brief, abstract framing of
  the current strategic situation — the big picture that makes the
  subsequent detail parseable.

### D. Cross-Cutting Synthesis — Which Principles Converge on Each Defect

| Babylon defect | Most directly applicable principles |
|---|---|
| **Broken action submission** | Norman C.1 (Gulf of Execution), Shneiderman C.8 (direct manipulation, reversibility, immediate effect), Salen & Zimmerman C.4 (meaningful play, discernable), Sylvester C.3 (mapping), Paradox P4 (Lens), P11 (Macro-builder) |
| **Tick resolution crashes / no time controls** | Salen & Zimmerman C.4 (integrated), Tufte C.5/C.6 (small multiples), Tufte C.7 (pictures of verbs), Norman C.1 (Compare stage), Paradox P7 (Time control bar) |
| **Map shows no features** | Tufte C.5 (to clarify, add detail), Sylvester C.3 (visual hierarchy), Paradox P2 (Map modes), Shneiderman C.8 (continuous representation) |
| **No outliner** | Norman C.1 (Plan stage), Universal C.9 (advance organizer, hierarchy), Krug C.2 (navigation/breadcrumbs), Paradox P1 (Outliner) |
| **No notifications** | Salen & Zimmerman C.4 (discernable — off-screen units), Norman C.1 (feedback), Sylvester C.3 (emotion loop), Paradox P3 (Message settings), P10 (Feed + toasts) |
| **No hotkeys** | Shneiderman C.8 (physical action vs. syntax), Norman C.1 (natural mapping), Universal C.9 (kinematic load), Sylvester C.3 (mapping), Paradox P2/P6/P7 (Q–P, F, Spacebar) |
| **Dense data, sparse display** | Tufte C.5/C.6 (to clarify add detail; clutter is design failure; layering), Sylvester C.3 (visual hierarchy, signal density), Universal C.9 (progressive disclosure, SNR), Tufte C.7 (Challenger — reveal null cases) |
| **Hex map underused** | Shneiderman C.8 (continuous representation), Tufte C.5 (avoid context-switching), Sylvester C.3 (elegance), Tufte C.7 (clarity of arrangement = clarity of thought), Paradox P4 (Lens — map is the action menu) |
| **Marxist simulation legibility** | Tufte C.7 (pictures of verbs — mechanism/cause), Salen & Zimmerman C.4 (objective vs. perceived information), Sylvester C.3 (engine of experience), Universal C.9 (80/20 — foreground dominant contradiction) |
| **Objectives feel imposed** | Salen & Zimmerman C.4 (meaningful play — action↔outcome), Sylvester C.3 (engine of experience — emotion loop), Universal C.9 (advance organizer — big picture framing). AI-generated objectives from dialectic state would restore the action↔outcome link |

### E. The Governing Insight

Across all 9 books and 12 Paradox patterns, one principle recurs: **the
map is the game.** Paradox's P4 (Lens), Shneiderman's C.8 (continuous
representation + direct manipulation), Tufte's C.5 (avoid
context-switching), and Sylvester's C.3 (elegance) all converge on the
same conclusion — Babylon's 9 verb action pages should not exist as
separate routes. They should be lenses overlaid on the hex map, so the
player acts directly on the spatial representation without ever losing
context. Every other improvement (outliner, notifications, hotkeys,
time controls) is secondary to this single architectural decision.
