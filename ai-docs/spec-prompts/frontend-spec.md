# Frontend Specification: Babylon React Client

**Status**: Draft
**Date**: 2026-03-01
**Depends On**: Postgres Spec, Django API, Constitution Article VII (Visual Design)
**Supersedes**: PyQt6 GUI (`babylon/ui/`), God Mode Dashboard (Feature 007)

---

## Scope

This spec defines the React frontend that serves as the browser-based presentation layer for Babylon. The client is a read-only observer of simulation state between turns and an action submission interface during turns. All computation happens server-side. The client renders, it does not compute.

The spec covers: library stack, component hierarchy, state management, data flow, design system translation, and the specific rendering approach for each visualization concern (hex map, network topology, hypergraph membership, time series, events, action interface).

---

## Library Stack

| Concern | Library | Version Target | Rationale |
|---|---|---|---|
| Framework | React | 19.x | Industry default, vibe-code friendly, deck.gl native |
| Build tool | Vite | 6.x | Fast HMR, simple config, ESM-native |
| Language | TypeScript | 5.x | Type safety for game state shapes |
| Hex map | deck.gl (`@deck.gl/react`, `@deck.gl/geo-layers`) | 9.x | H3HexagonLayer purpose-built for our data |
| Basemap | MapLibre GL JS (`react-map-gl`) | 4.x / 5.x | Open-source Mapbox fork, no API key, dark themes |
| Network graph | Sigma.js + Graphology | 3.x / 0.25.x | WebGL rendering, NetworkX-compatible data model |
| Charts | Recharts | 2.x | React-native, declarative, good AI output |
| State management | Zustand | 5.x | Minimal boilerplate, multiple stores, works outside React |
| Styling | Tailwind CSS | 4.x | Utility-first, AI-friendly, consistent vocabulary |
| Components | shadcn/ui | latest | Tailwind-based, accessible, composable primitives |
| HTTP client | `fetch` (native) | — | No axios needed for simple JSON API |
| Icons | Lucide React | latest | Clean, consistent, MIT licensed |

### Not Included (and Why)

- **Redux**: More machinery than the problem requires. Turn-based game with server-authoritative state doesn't need action/reducer ceremony. See Zustand rationale below.
- **Next.js**: SSR adds complexity for zero benefit. The client is a SPA talking to Django. No SEO concerns for a game.
- **Socket.io / WebSockets**: Turn-based. Plain HTTP request/response. Revisit only if real-time features emerge.
- **Leaflet**: deck.gl subsumes it for H3 rendering. MapLibre handles the basemap.
- **D3 (as primary)**: SVG-based, requires hand-building everything. Sigma.js is better for graph viz. D3 used only for UpSet plots and any bespoke SVG needs.
- **Cytoscape.js**: Canvas-based, heavier API. Sigma + Graphology is leaner and faster for dyadic graphs.

---

## State Management Architecture

Three independent Zustand stores. They don't know about each other. Components subscribe to whichever stores they need.

### `useGameStore`

Server-authoritative game state. Replaced wholesale on every turn resolution.

```typescript
interface GameStore {
  sessionId: string | null
  tick: number
  status: 'active' | 'paused' | 'completed' | 'abandoned'
  worldState: WorldStateJSON | null    // Full WorldState from Django
  hexGrid: HexCellJSON[] | null        // Current tick hex data for map
  graphData: GraphJSON | null          // Nodes + edges for topology view
  events: SimulationEventJSON[]        // Current tick events
  tickSummaries: TickSummaryJSON[]     // All ticks for time series

  // Actions
  createGame: (scenario: string) => Promise<void>
  submitTurn: (turn: TurnSubmission) => Promise<void>
  loadState: (sessionId: string) => Promise<void>
  loadTickState: (tick: number) => Promise<void>  // God Mode: view any tick
}
```

All data in this store comes from Django API responses. The store never computes derived quantities — that's the engine's job.

### `useUIStore`

Client-only interaction state. Never sent to server. Resets on page reload.

```typescript
interface UIStore {
  // Selection
  selectedNodeId: string | null
  selectedHexIndex: string | null
  hoveredNodeId: string | null
  hoveredHexIndex: string | null

  // Panel visibility
  inspectorOpen: boolean
  timeSeriesOpen: boolean
  eventLogOpen: boolean
  graphViewOpen: boolean

  // Action composition (building a turn before submission)
  pendingVerb: PlayerVerb | null
  pendingOrgId: string | null
  pendingTargetId: string | null
  pendingParams: Record<string, unknown>

  // Actions
  selectNode: (id: string | null) => void
  selectHex: (h3Index: string | null) => void
  setPendingAction: (verb: PlayerVerb, orgId: string) => void
  clearPendingAction: () => void
  togglePanel: (panel: PanelName) => void
}
```

### `useMapStore`

Map viewport state. Separate because deck.gl manages its own view state and we need to sync it.

```typescript
interface MapStore {
  viewState: {
    longitude: number   // Default: -83.1 (Detroit center)
    latitude: number    // Default: 42.35
    zoom: number        // Default: 10
    pitch: number       // Default: 0
    bearing: number     // Default: 0
  }
  activeLayer: MapLayer  // Which quantity drives hex color
  layerOpacity: number   // 0.0 - 1.0
  showCountyBoundaries: boolean
  showEdgeOverlay: boolean  // Solidarity/extraction edges on map

  // Actions
  setViewState: (vs: Partial<ViewState>) => void
  setActiveLayer: (layer: MapLayer) => void
  setLayerOpacity: (opacity: number) => void
}
```

`MapLayer` enum: `'profit_rate' | 'exploitation_rate' | 'imperial_rent' | 'dept_classification' | 'employment' | 'consciousness' | 'heat'`

---

## Component Hierarchy

```
<App>
├── <AuthGate>                         // Login/register, wraps authenticated content
│   └── <GameShell>                    // Main layout container
│       ├── <TopBar>                   // Game session info, tick counter, status
│       │   ├── <TickDisplay>          // Current tick, game status
│       │   ├── <PersistentIndicators> // Imperial rent, repression, profit rate, percolation
│       │   └── <UserMenu>            // Logout, settings
│       ├── <MainPanel>               // Center: map + overlays
│       │   ├── <HexMap>              // deck.gl + MapLibre
│       │   │   ├── <DeckGLOverlay>   // H3HexagonLayer + edge overlay
│       │   │   ├── <LayerControls>   // Layer toggle, opacity slider
│       │   │   └── <HexTooltip>      // Hover tooltip for hex data
│       │   └── <MapLegend>           // Color scale for active layer
│       ├── <RightPanel>              // Collapsible side panel
│       │   ├── <Inspector>           // Selected node/hex detail view
│       │   │   ├── <NodeInspector>   // SocialClass/Org/Territory attributes
│       │   │   ├── <HexInspector>    // HexEconomicState attributes
│       │   │   └── <MembershipTags>  // Community hyperedge badges
│       │   └── <ActionComposer>      // Turn submission interface
│       │       ├── <VerbSelector>    // 3x3 grid: Build/Project/Manage
│       │       ├── <TargetSelector>  // Filtered by verb target type
│       │       ├── <ParamFields>     // Verb-specific parameters
│       │       ├── <ActionPreview>   // Feedforward: predicted effects
│       │       └── <SubmitButton>    // POST to Django
│       ├── <BottomPanel>             // Collapsible bottom panel
│       │   ├── <TimeSeries>          // Recharts sparklines: r, Φ, OCC, s/v
│       │   ├── <EventLog>           // Scrolling event feed with icons
│       │   └── <GraphView>          // Sigma.js network topology
│       │       ├── <SigmaContainer>  // Sigma renderer + Graphology graph
│       │       ├── <GraphControls>   // Layout toggle, filter by edge mode
│       │       └── <GraphLegend>     // Node type shapes, edge mode colors
│       └── <GodModeDrawer>           // Developer analytics (toggle)
│           ├── <TickScrubber>        // Slider to view any historical tick
│           ├── <SQLConsole>          // Raw query interface (admin only)
│           └── <UpSetPlot>           // Hypergraph membership intersections
```

### Layout Strategy

The layout is a single-page application with collapsible panels arranged around a central map. The map is always visible and occupies the remaining space after panels are accounted for. Panels collapse to icons at the edge of the screen.

No routing. One page. The game is one view with configurable panel visibility. This avoids SPA routing complexity and keeps all visualization synchronized — selecting a hex on the map highlights it in the inspector and the graph view simultaneously.

---

## Design System Translation

Constitution Article VII defines the visual language. The PyQt6 implementation used `BunkerPalette` and `BUNKER_CONSTRUCTIVISM` constants. The React frontend translates these to Tailwind CSS custom properties.

### Tailwind Theme Extension

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // Constitution VII.2 Primary Palette
        'blood-void': '#1a0000',
        'void': '#050505',
        'crimson': '#dc143c',
        'gold': '#ffd700',
        'silver': '#c0c0c0',
        'ash': '#606060',
        // Extended palette (from BunkerPalette)
        'wet-concrete': '#1a1a1a',
        'soot': '#2d2d2d',
        'dark-metal': '#404040',
        'data-green': '#39FF14',
        'phosphor-red': '#D40000',
        'royal-blue': '#4169E1',
        'grow-purple': '#9D00FF',
        'warning-amber': '#ff8c00',
      },
      fontFamily: {
        'mono': ['"Roboto Mono"', '"Source Code Pro"', 'monospace'],
        'sans': ['"Inter"', 'system-ui', 'sans-serif'],  // For alerts per VII.9
      },
    },
  },
}
```

### Semantic Color Bindings (CSS Custom Properties)

Applied globally and consumed by both Tailwind classes and JavaScript visualization libraries.

```css
:root {
  /* Node types */
  --color-bourgeoisie: var(--crimson);
  --color-proletariat: var(--silver);
  --color-labor-aristocracy: var(--royal-blue);
  --color-organization-player: var(--gold);
  --color-organization-state: var(--crimson);
  --color-territory: var(--ash);

  /* Edge modes (Constitution I.6) */
  --color-edge-extractive: var(--crimson);
  --color-edge-solidaristic: var(--gold);
  --color-edge-transactional: var(--ash);
  --color-edge-antagonistic: var(--phosphor-red);
  --color-edge-cooptive: var(--grow-purple);

  /* UI semantics */
  --color-player-action: var(--gold);
  --color-alert: var(--gold);
  --color-critical: var(--crimson);
  --color-background-primary: var(--wet-concrete);
  --color-background-deep: var(--void);
  --color-text-primary: var(--silver);
  --color-text-muted: var(--ash);
}
```

### Typography Rules (VII.9)

- Body text: `font-mono`, silver (#c0c0c0)
- Active/selected labels: `font-mono`, gold (#ffd700)
- System alerts: `font-sans`, gold, uppercase
- Axis labels: `font-mono`, ash (#606060), smaller size
- Two typeface families maximum. No exceptions.

### Visual Prohibitions (VII.10) — Enforced in Code Review

- No decorative glow/bloom unless luminosity maps to a variable
- No hardcoded hex colors — all via Tailwind theme tokens or CSS custom properties
- No chartjunk — every visual element encodes data or enables navigation
- No hidden state — critical indicators always visible in `<PersistentIndicators>`
- No animation for its own sake — animation shows process (value flow, edge transitions)
- No context-dependent color meaning — CRIMSON always means extraction/power
- No more than two typeface families

---

## Hex Map Specification

### Data Flow

```
Django: GET /api/games/{id}/hexgrid/
  → JSON array: [{h3_index, county_fips, c, v, s, employment, dept_shares, profit_rate, exploitation_rate}, ...]
  → useGameStore.hexGrid
  → <HexMap> reads hexGrid from store
  → H3HexagonLayer renders ~1,500 hexes
```

### Layer Configuration

Each `MapLayer` option maps a data field to the `getFillColor` accessor:

| Layer | Field | Color Scale | Notes |
|---|---|---|---|
| `profit_rate` | `profit_rate` | phosphor-red (3%) → data-green (12%) | Piketty bounds, linear interpolation |
| `exploitation_rate` | `exploitation_rate` | silver (low) → crimson (high) | s/v ratio |
| `imperial_rent` | derived from `c, v, s` | ash (low) → gold (high) | Φ computed client-side from primitives |
| `dept_classification` | `dept_shares` | Categorical: I=blue, IIa=green, IIb=teal, III=purple | Dominant department |
| `employment` | `employment` | white (low) → gold (high) | Absolute count |
| `consciousness` | from `node_state` overlay | silver (assimilationist) → gold (revolutionary) | Requires spatial join with class data |
| `heat` | from territorial control | ash (cold) → phosphor-red (hot) | Repression/surveillance intensity |

### Interaction

- **Hover**: Tooltip shows hex data for active layer (e.g., "Profit Rate: 4.7%")
- **Click**: Sets `selectedHexIndex` in UIStore → Inspector shows full `HexEconomicState`
- **Pan/zoom**: Updates MapStore view state, deck.gl handles smoothly
- **County boundaries**: Optional `GeoJsonLayer` overlay from PostGIS (toggle in MapStore)
- **Edge overlay**: Optional `ArcLayer` showing value flows or solidarity edges between hexes (toggle in MapStore)

### Basemap

MapLibre GL JS with a dark vector tile style. Free tile sources: MapTiler (free tier), Stadia Maps, or self-hosted tiles. The basemap is muted — roads, water, labels in dark grays. The hex layer is the visual focus. MapLibre configured with `attributionControl: false` and `logoPosition: 'bottom-left'` to minimize chrome.

### Multi-Resolution

Deck.gl's `H3ClusterLayer` enables resolution switching. At high zoom (z > 11), show res 7 individual hexes. At medium zoom (z 9-11), aggregate to res 6 parents. At low zoom (z < 9), aggregate to res 5. The API endpoint accepts a `resolution` query parameter: `GET /api/games/{id}/hexgrid/?resolution=6`. Conservation check: client verifies `sum(children) ≈ parent` for displayed metrics.

---

## Network Topology Specification

### Data Flow

```
Django: GET /api/games/{id}/graph/
  → JSON: {nodes: [{id, type, attributes}, ...], edges: [{source, target, edge_type, edge_mode, attributes}, ...]}
  → useGameStore.graphData
  → <GraphView> constructs Graphology graph from JSON
  → Sigma.js renders via WebGL
```

### Node Rendering

| Node Type | Shape | Base Color | Size Driver |
|---|---|---|---|
| `social_class` (bourgeoisie) | Circle | crimson | `wealth` |
| `social_class` (proletariat) | Circle | silver | `population` |
| `social_class` (labor aristocracy) | Circle | royal-blue | `population` |
| `organization` (player) | Diamond | gold | `effective_capacity` |
| `organization` (state) | Diamond | crimson | `effective_capacity` |
| `organization` (business) | Square | ash | `effective_capacity` |
| `organization` (civil society) | Triangle | silver | `effective_capacity` |
| `territory` | Hexagon | ash | fixed |
| `key_figure` | Small circle | parent org color | fixed |

Node size scales logarithmically with the driver attribute. Minimum size enforced so small nodes remain visible and clickable.

### Edge Rendering

| Edge Mode | Color | Style | Width Driver |
|---|---|---|---|
| EXTRACTIVE | crimson | Solid | `value_flow` |
| SOLIDARISTIC | gold | Solid | `solidarity_strength` |
| TRANSACTIONAL | ash | Dashed | fixed thin |
| ANTAGONISTIC | phosphor-red | Solid | `tension` |
| CO-OPTIVE | grow-purple | Dotted | fixed medium |
| (no mode — mechanical types) | dark-metal | Thin solid | fixed minimal |

Edge width scales linearly with the driver attribute. Directed edges show arrowheads. Edges without an `edge_mode` (purely mechanical types like WAGES, TENANCY, PRESENCE) render as minimal dark-metal lines.

### Layout

ForceAtlas2 via Graphology's `graphology-layout-forceatlas2`. This is the standard force-directed layout for Sigma.js. The layout runs for a fixed number of iterations on initial render, then settles. User can drag nodes to reposition. Layout parameters tuned to cluster connected components while keeping the four-node pattern visible.

### Interaction

- **Hover**: Highlight node + all connected edges. Dim everything else. Show tooltip with node type and key attributes.
- **Click**: Set `selectedNodeId` in UIStore → Inspector shows full attribute dump. Highlight 1-hop neighborhood.
- **Filter**: Controls to show/hide edges by mode (checkboxes). Hide TRANSACTIONAL edges to see only meaningful relationships.
- **Sync with map**: Clicking a territory node pans the hex map to that territory's centroid. Clicking a hex on the map highlights its territory node in the graph.

---

## Hypergraph Membership Visualization

Hyperedges (XGI community memberships) are NOT rendered as a separate graph. They are visualized through two complementary mechanisms.

### Mechanism 1: Membership Tags (Inspector)

When a node is selected, the Inspector shows its community memberships as colored badges.

```
Selected: "Wayne County Proletariat"
Communities: [NEW_AFRIKAN] [WOMEN] [INCARCERATED]
```

Each badge uses the community type's assigned color (defined in the Tailwind theme extension). Clicking a badge highlights all nodes sharing that community membership in both the graph view and the hex map.

Community categories (from Constitution II.7):
- **Category 1 (Contradiction Pairs)**: Display both sides. SETTLER ↔ NEW_AFRIKAN, PATRIARCHAL ↔ WOMEN/TRANS.
- **Category 2 (Institutional Exclusion)**: Display marginalized side only. DISABLED, QUEER, UNDOCUMENTED, INCARCERATED.
- **Category 3 (Lifecycle)**: Display as phase indicator, not badge. "Phase: ADULT (D-P-D' Productive)"

### Mechanism 2: UpSet Plot (God Mode)

For analytical deep dives, the GodModeDrawer contains an UpSet intersection plot showing community membership overlaps. This answers questions like "how many nodes are in both NEW_AFRIKAN and INCARCERATED communities?" and "which intersection has the highest average consciousness?"

Built with D3 directly (no off-the-shelf UpSet React library is mature enough). The plot is interactive — clicking an intersection set filters the graph and map views to show only those nodes.

### Data Flow

```
Django: GET /api/games/{id}/communities/
  → JSON: {communities: [{type, category, members: [node_id, ...], heat, cohesion, consciousness}, ...]}
  → Stored in useGameStore.worldState (nested under communities)
  → <MembershipTags> reads for selected node
  → <UpSetPlot> reads all communities for intersection analysis
```

---

## Time Series Specification

### Data Flow

```
Django: GET /api/games/{id}/timeseries/
  → JSON array: [{tick, profit_rate, exploitation_rate, imperial_rent, consciousness, solidarity_edges, ...}, ...]
  → useGameStore.tickSummaries
  → <TimeSeries> renders Recharts LineCharts
```

### Charts

Four persistent sparklines in the BottomPanel, each a Recharts `<LineChart>` with `<Line>` components:

| Chart | Metrics | Colors | Y-Axis |
|---|---|---|---|
| Value dynamics | `profit_rate`, `exploitation_rate` | data-green, crimson | Percentage |
| Imperial rent | `imperial_rent` | gold | Currency |
| Consciousness | `avg_consciousness` by tendency | gold (revolutionary), ash (liberal), crimson (fascist) | 0.0 - 1.0 |
| Organization | `solidarity_edge_count`, `uprising_count` | gold, phosphor-red | Count |

Shared X-axis: tick number. Vertical line marker at current tick. Click any point to load that tick's state via `loadTickState()` (God Mode time travel).

All charts use `<ResponsiveContainer>` for resize handling. Tooltip on hover shows exact values. No animation on data update (VII.10 — animation must show process).

### Persistent Indicators (TopBar)

Four always-visible numbers, per Constitution VII.8 (Continuous Legibility):

| Indicator | Source | Color Logic |
|---|---|---|
| Imperial Rent Pool (Φ) | `tick_summary.imperial_rent` | Gold, brightness = magnitude |
| Repression Level | derived from state REPRESS actions | Ash → phosphor-red as level rises |
| Profit Rate (r) | `tick_summary.profit_rate` | phosphor-red (3%) → data-green (12%) |
| Solidarity Percolation | `tick_summary.solidarity_edge_count / max_possible` | Ash → gold as ratio rises |

These are NOT in collapsible panels. They are always visible in the TopBar.

---

## Action Composer Specification

The player interacts with the simulation through the ActionComposer in the RightPanel. This implements Constitution Article V's 9-verb vocabulary.

### Turn Composition Flow

1. Player selects their organization from a dropdown (if they control multiple orgs)
2. Player selects a verb from the 3×3 grid (Build / Project / Manage × 3 verbs each)
3. UI filters valid targets based on verb's target type (org / population / actor)
4. Player selects target from filtered list or by clicking the map/graph
5. Player fills verb-specific parameters (if any)
6. **Feedforward preview** shows predicted effects (VII.8) — highlighted edges/nodes that would change
7. Player submits → `POST /api/games/{id}/turn/`
8. Server validates (OODA constraints, AP cost, target validity)
9. Server runs tick → returns new state → all stores update → all views re-render

### Verb Grid Layout (Player-Facing Grouping)

```
┌─────────────┬─────────────┬─────────────┐
│  BUILD ORG  │ PROJECT PWR │ MANAGE RES  │
├─────────────┼─────────────┼─────────────┤
│  Educate    │  Attack     │  Aid        │
│  Reproduce  │  Mobilize   │  Move       │
│  Investigate│  Campaign   │  Negotiate  │
└─────────────┴─────────────┴─────────────┘
```

Each verb cell shows: verb name, AP cost for current org, and a brief description. Verbs that exceed available AP are visually dimmed (ash color) but still clickable (Constitution I.11: all verbs always available, consequences modeled, choices not restricted).

### Turn Submission Payload

```typescript
interface TurnSubmission {
  org_id: string           // Acting organization
  verb: PlayerVerb         // One of 9 constitutional verbs
  target_id: string | null // Target node (null for self-targeted verbs)
  params: Record<string, unknown>  // Verb-specific parameters
}
```

Django validates:
- `org_id` belongs to the authenticated player's game session
- `verb` is a valid PlayerVerb enum value
- `target_id` exists in the current WorldState (if provided)
- OODA constraints: org has sufficient AP, action is within org's operational profile
- Constitution compliance: all 9 verbs accepted regardless of consequences

### Error Handling

Validation errors return JSON with field-level error messages. The ActionComposer displays them inline next to the relevant field. Server errors (500) show a toast notification. Network errors trigger a retry with exponential backoff (max 3 retries).

---

## API Contract Summary

All endpoints prefixed with `/api/`. All return JSON. All require token authentication except `/api/auth/`.

| Method | Endpoint | Request | Response | Store |
|---|---|---|---|---|
| POST | `/api/auth/register/` | `{username, email, password}` | `{token, user}` | — |
| POST | `/api/auth/login/` | `{username, password}` | `{token, user}` | — |
| POST | `/api/games/` | `{scenario}` | `{session_id, status}` | gameStore |
| GET | `/api/games/{id}/state/` | — | Full WorldState JSON | gameStore |
| GET | `/api/games/{id}/hexgrid/` | `?resolution=7` | HexEconomicState[] | gameStore |
| GET | `/api/games/{id}/graph/` | — | `{nodes, edges}` | gameStore |
| GET | `/api/games/{id}/timeseries/` | — | TickSummary[] | gameStore |
| GET | `/api/games/{id}/events/` | `?tick=N` or `?from=A&to=B` | SimulationEvent[] | gameStore |
| GET | `/api/games/{id}/communities/` | — | Community membership data | gameStore |
| POST | `/api/games/{id}/turn/` | TurnSubmission | New WorldState JSON | gameStore |
| GET | `/api/games/{id}/state/?tick=N` | — | WorldState at tick N | gameStore (God Mode) |

### Response Size Estimates

| Endpoint | Rows | Est. Size | Frequency |
|---|---|---|---|
| `/hexgrid/` | ~1,500 | ~200 KB | Every turn |
| `/graph/` | ~80 nodes + ~50 edges | ~30 KB | Every turn |
| `/timeseries/` | ticks × metrics | ~50 KB at tick 100 | Every turn (append) |
| `/events/` | ~5-20 per tick | ~5 KB | Every turn |
| `/state/` | Full WorldState | ~500 KB | On demand |

Total per turn: ~285 KB. Trivial for modern networks. No pagination needed at beta scale.

---

## Build and Deployment

### Development

```bash
# Start dev server (hot reload)
cd frontend/
npm run dev        # Vite dev server on localhost:5173
                   # Proxies /api/* to Django on localhost:8000
```

Vite proxy config handles CORS in development — all `/api/` requests forwarded to Django. No `django-cors-headers` needed locally.

### Production Build

```bash
npm run build      # Outputs to frontend/dist/
```

Static files copied to Django's `STATIC_ROOT` or served directly by nginx. The React app is a single `index.html` + JS/CSS bundles. Nginx serves these statically; all `/api/` routes proxy to Django/Gunicorn.

### File Structure

```
frontend/
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx                    // Entry point
│   ├── App.tsx                     // Root component + AuthGate
│   ├── stores/
│   │   ├── gameStore.ts            // useGameStore
│   │   ├── uiStore.ts             // useUIStore
│   │   └── mapStore.ts            // useMapStore
│   ├── api/
│   │   ├── client.ts              // fetch wrapper with auth token
│   │   └── types.ts               // TypeScript interfaces for API responses
│   ├── components/
│   │   ├── layout/
│   │   │   ├── GameShell.tsx
│   │   │   ├── TopBar.tsx
│   │   │   ├── MainPanel.tsx
│   │   │   ├── RightPanel.tsx
│   │   │   └── BottomPanel.tsx
│   │   ├── map/
│   │   │   ├── HexMap.tsx         // deck.gl + MapLibre composition
│   │   │   ├── LayerControls.tsx
│   │   │   ├── HexTooltip.tsx
│   │   │   └── MapLegend.tsx
│   │   ├── graph/
│   │   │   ├── GraphView.tsx      // Sigma.js container
│   │   │   ├── GraphControls.tsx
│   │   │   └── GraphLegend.tsx
│   │   ├── inspector/
│   │   │   ├── Inspector.tsx
│   │   │   ├── NodeInspector.tsx
│   │   │   ├── HexInspector.tsx
│   │   │   └── MembershipTags.tsx
│   │   ├── action/
│   │   │   ├── ActionComposer.tsx
│   │   │   ├── VerbSelector.tsx
│   │   │   ├── TargetSelector.tsx
│   │   │   └── ActionPreview.tsx
│   │   ├── charts/
│   │   │   ├── TimeSeries.tsx
│   │   │   └── PersistentIndicators.tsx
│   │   ├── events/
│   │   │   └── EventLog.tsx
│   │   └── godmode/
│   │       ├── GodModeDrawer.tsx
│   │       ├── TickScrubber.tsx
│   │       └── UpSetPlot.tsx
│   ├── theme/
│   │   ├── colors.ts              // Palette constants + color scale functions
│   │   └── mapStyles.ts           // MapLibre dark style config
│   └── utils/
│       ├── colorScales.ts         // profit_rate_to_rgb equivalent
│       └── graphBuilder.ts        // JSON → Graphology graph construction
```

---

## Synchronization Between Views

The hex map, network graph, and inspector are synchronized through the UIStore.

- **Select hex on map** → `uiStore.selectHex(h3Index)` → Inspector shows hex data. If hex belongs to a territory node, that node highlights in the graph.
- **Select node in graph** → `uiStore.selectNode(nodeId)` → Inspector shows node data. If node is a territory, map pans to territory centroid and highlights its hexes.
- **Click community badge in inspector** → All nodes with that community membership highlight in both graph and map.
- **Click a tick on time series** → `gameStore.loadTickState(tick)` → All views re-render with historical state. TopBar shows "Viewing tick N" indicator.

This synchronization is achieved through Zustand subscriptions, not prop drilling. Each component subscribes to the specific store slice it needs. When a selection changes, all subscribed components re-render independently.

---

## Open Questions

1. **Mobile responsiveness**: The current spec assumes desktop. For mobile, the map goes full-screen and panels become bottom sheets. Worth speccing separately or deferring past beta?

2. **Keyboard shortcuts**: Power users (including Percy) will want keyboard shortcuts for common actions. Define a shortcut map or defer?

3. **Offline capability**: Service workers could cache the latest game state for offline viewing. Overkill for beta.

4. **Sound design**: Constitution doesn't address audio. Turn resolution confirmation sounds? Event type audio cues? Defer unless someone asks.

5. **Accessibility**: The dark theme and color-heavy design needs careful contrast checking. WCAG compliance for the beta, or defer?

6. **AI Narrative display**: The NarrativeDirector generates text from simulation events. Where does this render? A dedicated narrative panel? Overlay on the event log? The "FBI file" aesthetic described in project docs suggests a distinct presentation — intercepted transmission style.
