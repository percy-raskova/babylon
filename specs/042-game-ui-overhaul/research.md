# Research: Game UI Overhaul

**Feature**: 042-game-ui-overhaul | **Date**: 2026-03-03

## Decision Log

### R-001: Action Preview — Server-Side vs Client-Side Estimation

**Context**: Spec FR-017 requires showing "a preview of expected action effects (estimated metric changes, resource costs) before requiring confirmation." The current API has no preview endpoint.

**Decision**: Lightweight server-side preview endpoint.

**Rationale**: The simulation engine's `step()` function is the source of truth for how actions affect state. Client-side estimation would duplicate engine logic in JavaScript, violating II.8 (Client as Presentation Layer) and creating drift risk. Instead, add a `POST /api/games/:id/actions/preview/` endpoint that runs a read-only partial tick evaluation — the engine computes the expected effects of a single action without persisting any state changes.

**Alternatives considered**:
- **Client-side heuristic**: Rejected — violates II.8. Would require duplicating consciousness drift, heat calculation, and resource cost formulas in TypeScript. High maintenance burden and drift risk.
- **No preview**: Rejected — spec FR-017 is P1 requirement. Players need feedforward per VII.8.
- **Full simulation preview**: Rejected — running a complete tick with all systems for a single action preview is overkill and slow. Only the direct effects of the action need estimation.

**Implementation**: The preview endpoint calls the engine's action-effect calculation (already isolated in `StruggleSystem` and `TerritorySystem`) with the proposed action and returns estimated deltas without mutating the graph. Cost is read from `ActionType` definitions. Estimated consciousness/heat deltas come from the existing formula registry.

---

### R-002: Event Severity Classification — Frontend vs Backend

**Context**: Spec FR-025 requires 3 severity tiers (critical/important/informational). The backend `GameEvent` model has `type` and `data` but no severity field.

**Decision**: Frontend classification with a static type-to-severity mapping.

**Rationale**: Event severity is a presentation concern, not a simulation concern. The simulation engine produces events based on what happened mechanically (RUPTURE, EVICTION, SOLIDARITY_FORMED, etc.). How urgently those events should be communicated to the player is a UI decision that may change without affecting the engine. A static mapping table in the frontend (`eventClassifier.ts`) maps each `EventType` to a severity tier.

**Alternatives considered**:
- **Backend severity field**: Rejected — couples presentation concerns to the engine. Event severity may vary by game state context (an eviction in a territory the player controls is critical; in a distant territory, informational). Frontend classification enables context-sensitivity.
- **Configurable severity per event type**: Considered for future — players should eventually be able to adjust notification preferences (Victoria 3's notification settings pattern). The static mapping is the foundation; configuration is an enhancement.

**Mapping** (initial classification):

| Event Type | Severity | Rationale |
|---|---|---|
| RUPTURE | Critical | Threshold breach — existential state change |
| REVOLUTIONARY_VICTORY | Critical | Terminal endgame |
| ECOLOGICAL_COLLAPSE | Critical | Terminal endgame |
| FASCIST_CONSOLIDATION | Critical | Terminal endgame |
| EVICTION (player territory) | Critical | Player's organization displaced |
| BIFURCATION | Important | Phase transition — strategic shift |
| SOLIDARITY_FORMED | Important | New edge — strategic opportunity |
| SOLIDARITY_BROKEN | Important | Edge loss — strategic setback |
| EXCESSIVE_FORCE | Important | George Floyd Dynamic — narrative event |
| UPRISING | Important | Population action — narrative event |
| EVICTION (other territory) | Informational | Background change |
| VALUE_TRANSFER | Informational | Normal economic flow |
| CONSCIOUSNESS_SHIFT | Informational | Gradual change |
| HEAT_CHANGE | Informational | Gradual change |

---

### R-003: Event History — Accumulation Strategy

**Context**: Spec FR-029 requires "an event history log accessible through the bottom panel, with events sorted chronologically and filterable by type and severity." The current frontend accumulates `TickSummary` objects (aggregate stats) but not individual events across ticks.

**Decision**: Client-side event accumulation in the game store with a bounded buffer.

**Rationale**: The backend already returns `events[]` in every state snapshot. The frontend currently discards individual events after computing tick summaries. Instead, the `gameStore` will accumulate events from each tick's snapshot into a bounded ring buffer (max 500 events). This avoids a new API endpoint while providing sufficient history for UI display. For games with 100+ ticks, the oldest events naturally age out.

**Alternatives considered**:
- **New API endpoint for historical events**: Rejected for MVP — adds backend complexity. The existing `GET .../state/` already returns current tick events. Accumulating client-side is simpler and sufficient for the notification panel.
- **Unbounded accumulation**: Rejected — memory concern. At ~1KB per event, 500 events = ~500KB, well within browser limits. Events beyond 500 are informational-only by definition (critical/important events are always recent).

---

### R-004: Lens Architecture — Pure Frontend State

**Context**: Spec FR-005 requires lens-based navigation that recontextualizes map, indicators, and panels.

**Decision**: Lenses are purely frontend state objects defined in `lensDefinitions.ts`. No backend awareness of lenses.

**Rationale**: A lens is a UI filter/emphasis configuration. The backend returns the full game state regardless of which lens is active. The lens determines: (1) which `MapLayer` to set in `mapStore`, (2) which indicators to emphasize in `TopBar`, (3) which fields to prioritize in inspector panels, (4) which default charts to show in analytics. This is entirely a presentation concern per II.8.

**Lens definitions** (initial set):

| Lens | Primary Map Layer | Emphasized Indicators | Inspector Priority Fields |
|---|---|---|---|
| Economic | rent | Imperial Rent, Total Wealth, Inequality, Extraction Rate | wealth, rent_level, value_flow |
| Political | consciousness | Avg Consciousness, Organization Strength, Agitation, Repression | consciousness, organization, agitation, repression |
| Social | heat | Avg Heat, Eviction Rate, Biocapacity, Population | heat, under_eviction, biocapacity, population |
| Strategic | consciousness | P(Revolution), P(Acquiescence), Solidarity Edges, Org Count | p_revolution, p_acquiescence, solidarity_strength, cohesion |

---

### R-005: Panel Persistence — localStorage

**Context**: Spec FR-041-043 require persisting panel configurations across browser sessions.

**Decision**: localStorage with a namespaced key and JSON serialization.

**Rationale**: UI preferences (panel sizes, open/closed states, indicator selections) are per-browser, not per-user-account. localStorage is the standard browser mechanism for this. The key `babylon:ui-preferences` stores a JSON object with panel states, active lens, and indicator selections. A version field enables safe migration when the preference schema changes.

**Alternatives considered**:
- **Server-side preferences**: Rejected — adds a Django model, API endpoint, and migration for presentation-layer data. Violates II.8 spirit (UI preferences are not game state).
- **IndexedDB**: Rejected — overkill for ~1KB of preferences. localStorage is simpler and synchronous.
- **Zustand persist middleware**: Considered — Zustand has built-in `persist` middleware that uses localStorage. This is the preferred implementation approach for the `uiStore`.

---

### R-006: Notification Grouping Strategy

**Context**: Spec FR-027 requires grouping similar events when a threshold is exceeded. Spec SC-011 caps individual event cards at 5 per tick.

**Decision**: Group by event type when >2 events of the same type occur in a single tick.

**Rationale**: The grouping threshold of 2 means that 1-2 events of a type are shown individually, and 3+ are grouped into "N territories reached elevated heat" style summaries. Combined with the SC-011 cap of 5 cards, this prevents notification flood while preserving specificity for rare events. Critical events are never grouped — each critical event is shown individually regardless of count.

**Grouping rules**:
1. Critical events: always individual, always shown first
2. Important events: group if >2 of same type; show up to 3 groups
3. Informational events: group if >2 of same type; overflow into "and N more" summary
4. Total visible cards per tick: max 5 (critical + important groups + informational summary)

---

### R-007: Breadcrumb Navigation State

**Context**: Spec FR-013 requires breadcrumb navigation in the detail panel.

**Decision**: Stack-based breadcrumb state in `uiStore` with max depth of 3.

**Rationale**: The drill-down chain is Map → Territory → Organization/Entity. Each navigation step pushes an entry onto a breadcrumb stack. Clicking a breadcrumb pops back to that level. The stack stores: `{ entityType, entityId, displayName, lensContext }`. Max depth of 3 aligns with spec FR-015 (max 2 clicks from map).

---

### R-008: Chart Styling — Tufte Alignment

**Context**: Spec FR-024, FR-033, SC-007 require Tufte-aligned data visualization with data-ink ratio >0.8.

**Decision**: Custom Recharts theme with suppressed grid, range-frame axes, and direct data labeling.

**Rationale**: Recharts supports extensive customization of grid, axes, and styling. Tufte principles are applied via:
1. Remove Cartesian grid entirely or use very faint dashed lines
2. Use range-frame style axes (axis line extends only to data min/max, not full scale)
3. Suppress redundant axis labels (show only first/last tick numbers)
4. Direct label the most recent data point value
5. Use the constitutional color palette for data series (CRIMSON for extraction metrics, GOLD for solidarity metrics, SILVER for mass/population)
6. Remove chart background fills, borders, and shadows

**Alternatives considered**:
- **D3.js direct rendering**: Rejected — Recharts is already installed and provides sufficient customization. Switching to D3 adds complexity without proportional benefit.
- **Observable Plot**: Rejected — additional dependency. Recharts covers the use case.
- **visx (Airbnb)**: Rejected — lower-level than needed. Recharts + custom theme is simpler.

---

### R-009: Indicator Urgency Thresholds

**Context**: Spec FR-022 requires indicators to communicate urgency through visual encoding when values cross thresholds.

**Decision**: Three-tier threshold system per indicator: normal (SILVER), warning (GOLD/warning-amber), critical (CRIMSON).

**Rationale**: Each indicator defines its own threshold boundaries based on the simulation's meaningful ranges:
- **Imperial Rent**: normal (<0.5 extraction rate), warning (0.5-0.8), critical (>0.8)
- **Consciousness**: normal (<0.3 avg), warning (0.3-0.7), critical (>0.7)
- **Heat**: normal (<0.3 avg), warning (0.3-0.6), critical (>0.6)
- **Organization**: inverse — normal (>0.5 strength), warning (0.3-0.5), critical (<0.3)

Thresholds are defined in `lensDefinitions.ts` alongside lens configs, making them data-driven and adjustable without code changes.

---

### R-010: Performance at National Scale

**Context**: Spec SC-009 requires support for 3000+ county-level territories without perceptible lag.

**Decision**: deck.gl handles this natively; add level-of-detail optimization for zoomed-out views.

**Rationale**: deck.gl's H3HexagonLayer uses WebGL instanced rendering, which handles 10,000+ hexagons at 60fps. The existing implementation already renders the national scale. For zoomed-out views, we add a resolution-based LOD: at zoom levels <5, show state-level aggregated hexagons (50 polygons) instead of county-level (3000+). This improves label readability and reduces visual noise at overview zoom.

**Alternatives considered**:
- **TanStack Virtual for hex lists**: Not applicable — deck.gl handles spatial rendering, not list rendering. TanStack Virtual would be relevant for the entity sidebar if entity counts exceed ~50 items.
- **Canvas-based rendering**: Rejected — deck.gl already uses WebGL, which is faster than canvas for this use case.
