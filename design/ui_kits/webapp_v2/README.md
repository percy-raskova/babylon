# Babylon Web App — Frontend Reset (v2)

> **For the implementing engineer / coding agent.**
> This is a high-fidelity, interactive design prototype of a proposed
> rewrite of the Babylon web frontend. It is not production code, but
> every screen, route, and component shape is intended to map 1:1 onto
> the production React Router app. Read this README in full before
> touching the backend wiring.

______________________________________________________________________

## TL;DR — What This Is

The existing Babylon web frontend (`web/frontend/` on `dev` branch) is a
single-page "war room" — every system (map, topology graph, action
composer, time series, resource bar, event log, org list) is fused onto
one viewport. After review against the constitution
(`docs/concepts/babylon-constitution.md`) and Paradox's UX patterns
(scope/datacontext, slot system, datamodel iteration), it became clear
that the god-page was producing several anti-patterns:

- A right-rail accordion crammed all 9 verbs under invented
  "BUILD ORG / PROJECT PWR" tabs that don't exist in the constitution.
- A single target dropdown mixed hyperedges (communities, territories)
  with dyadic nodes (orgs) — violating Article IV's separation.
- Enemy orgs (WCSD, DFB, S3) showed up on the player's action surface,
  collapsing the scope of "things I can act with" and "things I can act
  on."
- `LAYER` and `LENS` selectors competed on the same map.
- Stats like `Avg Organization 0.50` averaged discrete agents.

**v2 splits the god-page into 16 React Router routes**, each with one
primary task, one data contract, and one performance envelope. The map,
graph, and Zustand stores synchronize across routes — but they don't
fuse into one screen.

______________________________________________________________________

## Files In This Kit

```
canvas.html              ★ Open this first — design canvas with all 16 routes
                           side-by-side as artboards, plus the architectural brief
index.html               ★ Open this second — full clickable prototype, navigate
                           via the left rail and verb tiles

mock-data.jsx            All in-memory state: 4 player orgs, ~12 enemy orgs,
                         9 verbs, communities, territories, edges, tick log,
                         and a tiny pseudo-Zustand store.
shell.jsx                Persistent chrome: TopBar (tick + RESOLVE),
                         left NavRail, FrameChip, HexMap (SVG), and shared
                         primitives (BblButton, BblCard, BblLabel, BblBadge,
                         tooltip-with-breakdown).
pages-pregame.jsx        LoginPage, GamesLobbyPage. No game chrome.
pages-core.jsx           BriefingPage (newspaper), OrgsPage (3×3 verb grid),
                         IntelPage (org / territory / edge / community
                         inspector — gated by URL param), ResultsPage,
                         AnalysisPage.
pages-verbs.jsx          VerbPage — one component, parameterized by verb
                         spec from mock-data. Renders the correct target
                         picker based on verb.target_type.
design-canvas.jsx        DesignCanvas / DCSection / DCArtboard — pan/zoom
                         scaffold for canvas.html.

colors_and_type.css      All Bunker Constructivism CSS variables. Identical
                         to the project-root file.
assets/                  Cover art, falling-Babel image.
```

______________________________________________________________________

## The 16 Routes (Architectural Inventory)

### Pre-Game (2 routes — no game chrome)

| Path     | Component        | Purpose                                      |
| -------- | ---------------- | -------------------------------------------- |
| `/login` | `LoginPage`      | Username/password, gradient void background. |
| `/games` | `GamesLobbyPage` | List of player's games; create new game.     |

### Core Game Loop (7 routes — wrapped in `GameRouteShell`)

| Path                                 | Component      | Primary Task                                                                                                                                                           |
| ------------------------------------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/games/:id`                         | `BriefingPage` | Newspaper-style summary of the prior tick: top events, sparklines (Cohesion, Heat, Consciousness), call-to-action chips routing to verbs.                              |
| `/games/:id/orgs`                    | `OrgsPage`     | The player's actor surface. Lists the 4 player orgs; the central panel is a 3×3 grid of verb tiles, each linking to its verb route. **Enemy orgs do not appear here.** |
| `/games/:id/intel/org/:orgId`        | `IntelPage`    | Inspector for one enemy org. Class composition, leadership, current actions, observed edges.                                                                           |
| `/games/:id/intel/territory/:terrId` | `IntelPage`    | Inspector for one territory hex. Hyperedge memberships rendered as choropleth on a small map.                                                                          |
| `/games/:id/intel/edge/:edgeId`      | `IntelPage`    | Inspector for one edge — its endpoints, weight provenance, history.                                                                                                    |
| `/games/:id/intel/community/:commId` | `IntelPage`    | Inspector for one community. Member orgs, ideology distribution, current campaigns targeting it.                                                                       |
| `/games/:id/results`                 | `ResultsPage`  | Mechanical summary of the just-resolved tick. Action outcomes, deltas, system events.                                                                                  |

### Verb Pages (9 routes — Article V atomic verbs)

| Path                   | `target_type`            | Notes                      |
| ---------------------- | ------------------------ | -------------------------- |
| `/actions/educate`     | `community`              | Hyperedge target.          |
| `/actions/mobilize`    | `community`              | Hyperedge target.          |
| `/actions/campaign`    | `territory \| community` | Hyperedge target (either). |
| `/actions/aid`         | `org \| territory`       | Dyadic.                    |
| `/actions/attack`      | `org \| territory`       | Dyadic.                    |
| `/actions/move`        | `territory`              | Dyadic.                    |
| `/actions/investigate` | `any`                    | The universal verb.        |
| `/actions/reproduce`   | `org`                    | Dyadic — internal.         |
| `/actions/negotiate`   | `org`                    | Dyadic.                    |

The single `VerbPage` component reads `verb.target_type` from the
verb spec and renders the **correct target list**. There is no
unified target dropdown.

### Post-MVP (1 route)

| Path                  | Component      | Notes                                                                                                          |
| --------------------- | -------------- | -------------------------------------------------------------------------------------------------------------- |
| `/games/:id/analysis` | `AnalysisPage` | Read-only. Full-bleed time series, UpSet plot of community memberships, tick scrubber. Cut from MVP if needed. |

______________________________________________________________________

## Constitution Anchors

Every architectural choice in v2 is traceable to a constitution article.
When you re-implement, preserve these mappings:

| Article    | What It Says                                                              | How v2 Honors It                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **III**    | LLM is observer-only.                                                     | The composer queues a schema-validated `{verb, target_id, params}`. The server resolves; the client never simulates. The Action Composer is a *form*, not an agent.                                                     |
| **IV**     | Dyadic vs. hyperedge separation.                                          | Verb target pickers are gated by `target_type`. Educate/Mobilize/Campaign target hyperedges (communities, territories). Aid/Attack/Move/Negotiate target nodes. They never share a list.                                |
| **V**      | All 9 verbs always available; no phase gating.                            | `/orgs` shows all 9 verb tiles unconditionally. Disabled state is per-verb (e.g., no available targets), never per-phase.                                                                                               |
| **VII**    | Color = meaning, luminosity = magnitude.                                  | Class colors are categorical (CRIMSON proletariat, ROYAL BLUE labor aristocracy, etc.). Heat / Consciousness / Cohesion use luminosity ramps. See `colors_and_type.css`.                                                |
| **VIII.9** | Hyperedges render as choropleth, badges, hulls — never as pairwise edges. | Map hexes are colored by which hyperedges they participate in. Inspector panels show hyperedge badges. The topology graph (when implemented) uses BubbleSets hulls. The analysis page uses UpSet, not a wiring diagram. |

______________________________________________________________________

## Paradox UX Patterns Adopted

These are the patterns lifted from Paradox's grand-strategy UX
codebase. When you wire the production app, preserve them:

1. **Tooltip breakdowns.** Every aggregate stat (Heat, Cohesion,
   Legitimacy, Consciousness) opens a `Base + contributors` provenance
   on hover. The mock implements this in `shell.jsx` (`<Breakdown>`).
   The production analog is `GetScriptValueBreakdown`. **Every numeric
   value the player sees should have a breakdown route.**

1. **Datacontext / scopes.** `Scope.getOrg(id)`, `getCommunity(id)`,
   `getTerritory(id)` — chained accessors that promote from a single
   typed registry. The mock implements this as plain object accessors
   on the store; production should use a Zustand selector hook factory.

1. **Datamodel iteration.** Verb target lists are server-shaped arrays
   passed to one renderer. There is no per-verb bespoke fetch. Add a
   verb → add a row to the verb spec → done.

1. **Slot pattern.** Every panel exposes named slots (`title`, `right`,
   `body`). Scenario authors override one section without forking the
   whole panel. In React this means each panel component takes
   `titleSlot?`, `rightSlot?`, `children` props.

1. **Persistent shell.** `GameRouteShell` (TopBar + NavRail) mounts
   once per game-id and stays across all in-game route changes. Use
   `<Outlet/>` from React Router for the body; never re-mount the
   shell.

______________________________________________________________________

## Data Contracts (from `mock-data.jsx`)

Treat these as the canonical client-side shapes. Server payloads
should denormalize into them.

```ts
type Org = {
  id: string;            // e.g. "ORG001"
  name: string;
  faction: "PLAYER" | "NPC";
  ideology: string;      // "MLM-TW", "Liberal", "Reactionary", ...
  cl: number;            // Cadre Labor (current)
  sl: number;            // Sympathizer Labor
  rep: number;           // Reputation (-100 .. +100)
  budget: number;        // currency
  heat: number;          // 0..100, surveillance pressure
  cohesion: number;      // 0..1
  legitimacy: number;    // 0..1
  opacity: number;       // 0..1, inverse of how observable they are
  territory: string;     // primary territory id
  members: number;
};

type Community = {
  id: string;            // e.g. "C-DEARBORN-PROLE"
  name: string;
  classComposition: { proletariat: number; laborAristocracy: number;
                      pettyBourgeois: number; lumpen: number; };
  consciousness: number; // 0..1
  population: number;
  territories: string[]; // hyperedge — communities span multiple hexes
};

type Territory = {
  id: string;            // e.g. "T-DETROIT-CENTRAL"
  name: string;
  hex: { q: number; r: number };  // axial coords
  population: number;
  wealth: number;        // 0..1
  rent: number;          // imperial rent extraction rate
  biocapacity: number;   // 0..1
  controllingOrg?: string;
};

type Edge = {
  id: string;
  type: "solidarity" | "exploitation" | "rivalry" | "patronage";
  source: string;        // org id
  target: string;        // org id
  weight: number;        // 0..1
  history: TickEvent[];
};

type Verb = {
  verb: "educate" | "mobilize" | "campaign" | "aid" | "attack" |
        "move" | "investigate" | "reproduce" | "negotiate";
  target_type: "community" | "territory" | "org" | "any" |
               "org|territory" | "territory|community";
  cost: { cl?: number; sl?: number; budget?: number };
  description: string;
};

type QueuedAction = {
  actorOrgId: string;
  verb: string;
  targetId: string;
  params: Record<string, any>;
};
```

The composer's only job is to produce `QueuedAction[]`. RESOLVE TICK
posts it to the server and waits for the new tick state.

______________________________________________________________________

## Anti-Patterns Excised (Do Not Reintroduce)

- ❌ A 9-verb accordion in a right rail — verbs deserve their own routes.
- ❌ Invented tab labels like "BUILD ORG" or "PROJECT PWR" that aren't
  in the constitution.
- ❌ A single target list mixing hyperedges and dyadic nodes.
- ❌ Enemy orgs on the player's action surface. They live in `/intel/*`.
- ❌ A mini org-graph that duplicates the right-rail org list.
- ❌ Three full-size time-series panels on the briefing page (use sparklines;
  full charts live on `/analysis`).
- ❌ `LAYER` and `LENS` selectors competing on the same map. Pick one
  per route — the chip in the TopBar.
- ❌ `Avg Organization 0.50` and similar averaged-agent stats. Per-org
  values only; aggregate at the community/territory level if needed.

______________________________________________________________________

## Implementation Order (Suggested)

1. **Scaffold routes.** Stand up React Router with the 16 paths above.
   Render an empty page per route. Confirm shell mount/unmount behavior
   (`GameRouteShell` mounts once per `:id`).
1. **Move CSS tokens.** `colors_and_type.css` → Tailwind config or CSS
   custom properties. The existing project already has the variables
   defined; reconcile.
1. **Port `BblButton` / `BblCard` / `BblLabel` / `BblBadge` / tooltip-
   with-breakdown** as real TS components. Replace the inline-style
   versions in `shell.jsx`.
1. **Port `HexMap`** to deck.gl with an `H3HexagonLayer` or your
   existing hex layer. The mock SVG version is correct only in shape;
   data binding (community → hex membership) is what matters.
1. **Port `BriefingPage`** as the smoke-test page. Wire to the real
   tick log + a sparkline lib.
1. **Port `OrgsPage`.** This is the highest-value page — it's the
   action surface. The 3×3 verb grid should be a static layout, not
   data-driven.
1. **Port `VerbPage` once.** Feed it from a `verbs` config array. All
   nine verb routes share the component.
1. **Port `IntelPage` four times** (org / territory / edge / community)
   — each variant is a different inspector layout. Share the chrome.
1. **Port `ResultsPage`.** Wire to the post-RESOLVE response.
1. **(Post-MVP) Port `AnalysisPage`** with the time-series + UpSet libs.

______________________________________________________________________

## What's Faithful, What's Mocked, What's Missing

| Concern               | State in v2                                                               |
| --------------------- | ------------------------------------------------------------------------- |
| Routing               | ✅ Faithful — 16-route structure is the spec.                             |
| Visual language       | ✅ Faithful — Bunker Constructivism palette + type.                       |
| Component shapes      | ✅ Faithful — every panel is a porting target.                            |
| Data contracts        | ✅ Faithful — `mock-data.jsx` types are canonical.                        |
| Hex map               | ⚠️ Mocked — SVG hexes, not deck.gl. Geometry only.                        |
| Topology graph        | ⚠️ Sketched — not interactive. BubbleSets/Sigma is the production target. |
| Tooltip breakdowns    | ⚠️ One reference impl in `shell.jsx`. Extend.                             |
| RESOLVE TICK          | ⚠️ Logs to console; no server.                                            |
| WebSocket tick stream | ❌ Missing — production needs subscription.                               |
| Auth / sessions       | ❌ Missing — `LoginPage` is a form only.                                  |
| Time series / UpSet   | ❌ Sketched only on `/analysis`.                                          |

______________________________________________________________________

## Dependencies (What The Production App Will Need)

Already in the existing `web/frontend/`:

- React 18 + TypeScript
- Tailwind CSS v4
- Lucide React
- Zustand
- React Router

Likely additions for v2:

- **deck.gl** + `@deck.gl/geo-layers` — hex map.
- **sigma.js** or **react-force-graph** + **bubblesets-js** — topology
  graph with hyperedge hulls.
- **visx** or **uplot** — sparklines on briefing, full series on analysis.
- **upset.js** or a custom UpSet renderer — community membership matrix.
- **zod** — schema-validate `QueuedAction` before posting.

______________________________________________________________________

## Where To Start Reading The Code

1. `mock-data.jsx` — understand the entity shapes and the registry.
1. `shell.jsx` — understand `GameRouteShell`, the TopBar, the NavRail,
   and the shared primitives. This file is the visual contract.
1. `pages-core.jsx` → start with `OrgsPage`. It is the heart of the
   prototype.
1. `pages-verbs.jsx` → `VerbPage` — see how `target_type` gating works.
1. `pages-core.jsx` → `IntelPage` — see the four-variant inspector.
1. `canvas.html` → the `BriefArtboard` component at the bottom is a
   visual restatement of this README.

______________________________________________________________________

## Questions To Resolve Before Implementation

These are flagged for the product owner (Persephone) before you
start writing production code:

1. **Sub-routing within `/orgs`.** Does selecting an actor org on
   `/orgs` push state to the URL (`/orgs/:actorId`), or live in Zustand?
1. **Edge inspector access.** Is `/intel/edge/:id` reachable from the
   topology graph only, or also from inspector panels that mention an edge?
1. **`/analysis` MVP cut.** Confirmed cuttable? If yes, hide the
   nav-rail entry until tick > 10.
1. **RESOLVE concurrency.** What does the UI do during the server-side
   resolve? Block the shell? Show an overlay? The mock currently does
   nothing.
1. **Multi-game state.** When a player has 3 active games, does the
   `GameRouteShell` cache per-game state in memory, or refetch on
   route change?

______________________________________________________________________

*Generated by the Babylon design template. The prototype lives at
`canvas.html` (overview) and `index.html` (clickable). When in doubt,
the constitution wins.*
