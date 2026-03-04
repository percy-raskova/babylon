# Data Model: Game UI Overhaul

**Feature**: 042-game-ui-overhaul | **Date**: 2026-03-03

## New Types (additions to `src/types/game.ts`)

### Lens System

```typescript
/** Analytical perspective that recontextualizes the entire UI */
interface LensDefinition {
  id: LensId
  name: string
  icon: string                        // lucide-react icon name
  primaryLayer: MapLayer              // choropleth layer for map
  emphasizedIndicators: IndicatorId[] // top bar indicator order
  inspectorPriority: string[]         // field names to show first in detail panels
  defaultChartMetrics: string[]       // time-series metrics to show by default
  description: string                 // tooltip for lens button
}

type LensId = "economic" | "political" | "social" | "strategic"
```

### Notification System

```typescript
/** Severity tier for event classification */
type EventSeverity = "critical" | "important" | "informational"

/** Classified game event with UI-specific metadata */
interface ClassifiedEvent {
  id: string                          // unique: `${tick}-${index}`
  event: GameEvent                    // original engine event
  severity: EventSeverity
  tick: number
  read: boolean
  linkedEntityId: string | null       // entity/territory/org to navigate to
  linkedEntityType: "territory" | "organization" | "entity" | "institution" | null
}

/** Grouped notification for display */
interface NotificationGroup {
  severity: EventSeverity
  eventType: string
  count: number
  events: ClassifiedEvent[]
  summary: string                     // "3 territories reached elevated heat"
  representativeEvent: ClassifiedEvent // first event for navigation
}
```

### Breadcrumb Navigation

```typescript
/** Single entry in the drill-down navigation stack */
interface BreadcrumbEntry {
  entityType: "overview" | "territory" | "organization" | "entity" | "institution"
  entityId: string | null             // null for overview
  displayName: string
  lensId: LensId                      // lens active at time of navigation
}
```

### Indicator System

```typescript
/** Identifier for a trackable simulation metric */
type IndicatorId =
  | "imperial_rent" | "avg_consciousness" | "avg_heat" | "avg_organization"
  | "total_wealth" | "total_population" | "org_count" | "edge_count"
  | "eviction_rate" | "biocapacity_avg" | "p_revolution_max" | "p_acquiescence_min"
  | "repression_avg" | "agitation_avg" | "inequality_avg" | "solidarity_edges"

/** Threshold configuration for urgency coloring */
interface IndicatorThresholds {
  warning: number                     // above this → warning color
  critical: number                    // above this → critical color
  invert: boolean                     // true = low values are critical (e.g., organization)
}

/** Indicator definition for the top bar */
interface IndicatorDefinition {
  id: IndicatorId
  label: string
  unit: string                        // "", "%", "$", "count"
  format: "decimal" | "percent" | "integer" | "currency"
  thresholds: IndicatorThresholds
  compute: (snapshot: GameSnapshot) => number  // derived from snapshot
}
```

### Panel Persistence

```typescript
/** Persisted UI preferences (localStorage) */
interface UIPreferences {
  version: number                     // schema version for migration
  rightPanelWidth: number             // pixels, min 280, max 600
  rightPanelOpen: boolean
  bottomPanelHeight: number           // pixels, min 180, max 400
  bottomPanelOpen: boolean
  bottomTab: BottomTab
  activeLens: LensId
  pinnedIndicators: IndicatorId[]     // which indicators shown in top bar (4-6)
  graphEdgeFilter: string | null      // edge type filter in GraphView
}
```

### Action Preview

```typescript
/** Server response for action preview */
interface ActionPreviewResult {
  estimated_consciousness_delta: number
  estimated_heat_delta: number
  action_point_cost: number
  success_probability: number
  affected_territory_ids: string[]
  warnings: string[]                  // e.g., "This territory is under eviction"
}
```

## Modified Types (changes to existing interfaces)

### GameSnapshot (add optional `notifications` accumulation)

No changes to `GameSnapshot` interface itself. The `events` field already carries per-tick events. Classification happens at the store layer.

### UIState Store (extended)

```typescript
// Additions to UIState interface in uiStore.ts:
interface UIState {
  // ... existing fields ...

  // Lens
  activeLens: LensId                  // default: "political"

  // Breadcrumbs
  breadcrumbs: BreadcrumbEntry[]      // stack, max depth 3

  // Notifications
  notifications: ClassifiedEvent[]    // accumulated, bounded buffer (500 max)
  unreadCount: number
  notificationGroupsForTick: NotificationGroup[] // computed per-tick display

  // Panel sizing
  rightPanelWidth: number
  bottomPanelHeight: number

  // Indicator customization
  pinnedIndicators: IndicatorId[]

  // New actions
  setActiveLens(lens: LensId): void
  pushBreadcrumb(entry: BreadcrumbEntry): void
  popBreadcrumbTo(index: number): void
  clearBreadcrumbs(): void
  addEvents(events: ClassifiedEvent[]): void
  markEventRead(id: string): void
  markAllEventsRead(): void
  setRightPanelWidth(width: number): void
  setBottomPanelHeight(height: number): void
  setPinnedIndicators(ids: IndicatorId[]): void
  resetPreferences(): void
}
```

### MapState Store (lens-driven)

```typescript
// mapStore.ts — activeLayer now driven by lens but overridable
interface MapState {
  // ... existing fields ...
  lensOverride: boolean               // true when user manually changed layer
  // setActiveLayer now also sets lensOverride = true
}
```

## Entity Relationships

```
LensDefinition ─────────┬──→ MapLayer (1:1 primary)
                         ├──→ IndicatorId[] (1:N emphasized)
                         └──→ string[] (1:N inspector fields)

ClassifiedEvent ────────┬──→ GameEvent (1:1 wraps)
                        └──→ entity/territory/org (0..1 navigation target)

NotificationGroup ──────→ ClassifiedEvent[] (1:N grouped events)

BreadcrumbEntry ────────→ entity/territory/org (0..1 navigation target)

IndicatorDefinition ────→ GameSnapshot (computes from snapshot)
                    ────→ IndicatorThresholds (1:1 urgency config)

UIPreferences ──────────→ localStorage (serialized)
```

## State Transitions

### Lens State Machine

```
[Any Lens] --click lens button--> [Target Lens]
  Effects:
  1. uiStore.activeLens = target
  2. mapStore.activeLayer = target.primaryLayer (unless lensOverride)
  3. TopBar reorders indicators per target.emphasizedIndicators
  4. Inspector re-renders with target.inspectorPriority
  5. BottomPanel default charts update per target.defaultChartMetrics
```

### Breadcrumb State Machine

```
[Empty] --click hex on map--> [Overview → Territory]
[Overview → Territory] --click org in detail--> [Overview → Territory → Organization]
[Overview → Territory → Organization] --click breadcrumb "Territory"--> [Overview → Territory]
[Any] --click map background or Escape--> [Empty]
[Any] --click breadcrumb "Overview"--> [Empty] (clears selection)
```

### Notification Lifecycle

```
[Tick Resolved]
  → events[] from snapshot
  → eventClassifier maps each to ClassifiedEvent
  → addEvents() pushes to bounded buffer
  → computeNotificationGroups() groups for display
  → Critical events trigger NotificationToast overlay
  → Player acknowledges toast → markEventRead()
  → Player clicks event → navigates to linked entity
```
