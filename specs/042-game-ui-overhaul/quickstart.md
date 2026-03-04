# Quickstart: Game UI Overhaul (Feature 042)

**Branch**: `042-game-ui-overhaul`

## Prerequisites

```bash
# Backend
cd /home/user/projects/game/babylon
poetry install
mise run web:migrate

# Frontend
cd web/frontend
npm install
```

## Development Servers

```bash
# From repo root — starts both Django (8000) + Vite (5173) as background daemons
mise run web:dev

# Or run individually in foreground:
mise run web:backend   # Django on port 8000
mise run web:frontend  # Vite on port 5173
```

Open `http://localhost:5173` in browser. Vite proxies `/api` and `/accounts` to Django.

## Key Files to Understand

| File | Purpose |
|---|---|
| `web/frontend/src/types/game.ts` | All TypeScript interfaces — start here |
| `web/frontend/src/stores/uiStore.ts` | UI state: selection, panels, lens, breadcrumbs |
| `web/frontend/src/stores/gameStore.ts` | Game state: snapshot, events, tick summaries |
| `web/frontend/src/stores/mapStore.ts` | Map state: active layer, opacity |
| `web/frontend/src/components/layout/GameShell.tsx` | Root layout container |
| `web/frontend/src/index.css` | Tailwind v4 @theme design tokens |
| `web/frontend/src/theme/colors.ts` | deck.gl RGBA color scales |
| `web/frontend/src/api/client.ts` | API client (get/post/postForm) |

## Architecture Patterns

### State Management

Three Zustand stores — no React Context needed:

```typescript
import { useGameStore } from "@/stores/gameStore"
import { useUIStore } from "@/stores/uiStore"
import { useMapStore } from "@/stores/mapStore"

// In component:
const snapshot = useGameStore(s => s.snapshot)
const activeLens = useUIStore(s => s.activeLens)
const activeLayer = useMapStore(s => s.activeLayer)
```

### Lens System (new in 042)

Lenses are defined in `src/lib/lensDefinitions.ts`. Each lens specifies:
- `primaryLayer` — which choropleth to show on map
- `emphasizedIndicators` — which metrics to highlight in top bar
- `inspectorPriority` — which fields to show first in detail panels
- `defaultChartMetrics` — which time-series to display by default

Switching a lens updates `uiStore.activeLens` which triggers coordinated updates across map, top bar, inspector, and charts.

### Design Token System

All colors are defined as CSS custom properties in `index.css` `@theme {}` block and used as Tailwind utilities:

```tsx
// Use Tailwind utility classes referencing theme tokens
<div className="bg-dark-metal text-bone border-soot">
  <span className="text-gold">Active</span>
  <span className="text-crimson">Danger</span>
  <span className="text-silver">Default</span>
  <span className="text-ash">Muted</span>
</div>
```

Per constitution VII.2, colors encode meaning. CRIMSON = power/extraction, GOLD = action/solidarity, SILVER = mass/default, ASH = muted/inactive.

### API Communication

All API calls go through `src/api/client.ts`:

```typescript
import { get, post } from "@/api/client"

// GET with typed response
const resp = await get<GameSnapshot>(`/api/games/${id}/state/`)
if (resp.status === "ok") { /* use resp.data */ }

// POST with body
const resp = await post<ActionPreviewResult>(`/api/games/${id}/actions/preview/`, {
  org_id: "org_1", verb: "educate", target_id: "territory_abc"
})
```

## Testing

```bash
# Run all frontend tests
mise run web:test

# Run specific test file
cd web/frontend && npx vitest run src/__tests__/integration/lens-switching.test.tsx

# Run with coverage
cd web/frontend && npx vitest run --coverage

# Full quality check (tsc + eslint + prettier + vitest)
mise run web:check
```

### Test Patterns

- **MSW handlers** in `src/test/handlers.ts` mock all API endpoints
- **Fixtures** in `src/test/fixtures.ts` provide factory functions for test data
- **Store reset** happens automatically in `afterEach` via `src/test/setup.ts`
- **New feature tests** go in `src/__tests__/integration/`

```typescript
import { renderWithProviders } from "@/test/render"
import { makeSnapshot } from "@/test/fixtures"

it("switches lens and updates map layer", async () => {
  const snap = makeSnapshot({ /* overrides */ })
  // ... test lens switching behavior
})
```

## Common Tasks

### Add a new indicator

1. Add `IndicatorId` variant to `types/game.ts`
2. Add `IndicatorDefinition` to `lib/lensDefinitions.ts` with compute function and thresholds
3. Add to relevant lens `emphasizedIndicators` arrays
4. `PersistentIndicators.tsx` auto-renders from pinned indicator list

### Add a new lens

1. Add `LensId` variant to `types/game.ts`
2. Add `LensDefinition` object to `lib/lensDefinitions.ts`
3. `LensBar.tsx` auto-renders from lens definition list

### Add a new event type classification

1. Add mapping to `lib/eventClassifier.ts` type-to-severity table
2. If critical, add summary template for `NotificationToast.tsx`

### Add a new map layer

1. Add `MapLayer` variant to `types/game.ts`
2. Add color scale function to `theme/colors.ts`
3. Add layer option to `LayerControls.tsx`
4. Associate with relevant lens(es) in `lensDefinitions.ts`
