# Babylon Frontend Course-Correction Prompt

**For the agent picking this up:** read this whole document before touching code. It encodes architectural decisions made across multiple prior conversations and a research phase on Paradox grand-strategy UI patterns. You are not free to relitigate those decisions — you are free to flag if you find a constraint that genuinely blocks the work. The phases are ordered. Do not skip ahead. Each phase produces a working frontend with passing tests; if a phase leaves the build broken, you have done the phase wrong.

The repo is at `https://github.com/percy-raskova/babylon`, branch `dev`. All work happens under `web/frontend/src/`. No simulation engine, no Postgres schema, no Django view changes unless explicitly called out.

---

## Mission

Three things are wrong with the current frontend, and one architectural pattern is missing. Fix all four.

1. **Data layer is fragmented.** `gameStore` (Zustand) is the unified path for `snapshot`, but `ActionPage` and `OrganizationsPage` duplicate inline `useEffect + apiGet` blocks for `/api/games/{id}/organizations/?player_only=true`. `ActionPage` also fetches `/api/games/{id}/actions/{verb}/targets/?org_id={id}` inline. Same endpoint hit in two files, two error-handling patterns, two loading flags.

2. **No selector / breakdown infrastructure exists.** `HexTooltip` calls `t.heat.toFixed(2)` — flat lookup, no provenance, no contributors. The constitution requires every derived number to trace to primitives or `GameDefines`. The frontend currently cannot honor that requirement because there is no representation of "where did this number come from" anywhere in the UI layer.

3. **The Briefing route is overstuffed.** `GameShell` (`web/frontend/src/components/layout/GameShell.tsx`) still embeds `<ActionComposer>`, full-size `<TimeSeries>`, `<GraphView>`, plus `<LensBar>` and `<LayerControls>` simultaneously. The verb pages, orgs page, and intel page already exist as separate routes — the GameShell is duplicating their functionality.

4. **Lens vs layer is unresolved.** `LensBar` at the bottom of GameShell coordinates with `mapStore.activeLayer`, but `LayerControls` inside `DeckGLMap` lets the user override the layer independently and sets `lensOverride: true`. Two selectors render simultaneously for the same conceptual space. Pick one.

The architectural addition is a Paradox-pattern selector and breakdown system — `BabylonScriptValue` plus a typed selector registry — that lands first as scaffolding, then gets applied incrementally. This is the only lever that makes the constitutional provenance requirement enforceable in UI.

---

## Constitutional Non-Negotiables

Read these once, then hold them in mind throughout. None are softenable.

- **Server-authoritative.** The React app is a presentation layer. No simulation logic in the browser. Every state mutation goes through Django → engine.
- **No magic constants in UI.** Numbers displayed to the user must trace to either (a) the snapshot from the server, (b) a constant pulled from `GameDefines` exposed via API, or (c) a `BabylonScriptValue` whose contributors trace to (a) or (b). Inline magic numbers in JSX are violations.
- **Empirical / Strategic separation.** Material conditions (organizations, hexes, edges, tensors) come from the snapshot. Strategic intervention (verbs, targeting, organizing) comes from player input. The UI must not invent material conditions client-side; the UI must not constrain strategic intervention beyond what the server says is legal.
- **Organizations are the agents.** Not individuals, not demographic blocks. UI primitives talk about organizations; pops/communities/classes appear as targets of verbs and as derived aggregates, never as agents.
- **Edge modes transform categorically.** EXTRACTIVE → SOLIDARISTIC requires TRANSACTIONAL intermediate. UI must never imply continuous interpolation between edge modes.
- **Community membership is a hyperedge, not pairwise edges.** Render as choropleth on hexes by dominant composition, badges on inspector panels, UpSet plots for intersection — never as a fan of individual edges from a community node.
- **AI observes, never controls.** No client-side LLM calls that determine mechanical outcomes. LLM narration is a fallback for missing localization keys and only narrates state changes the engine has already produced.

If you find yourself writing code that violates any of the above, stop and surface it.

---

## Current State Evidence

Before designing fixes, anchor on what's actually there:

```
web/frontend/src/
├── App.tsx                           # Routes: /games/:id, /games/:id/orgs,
│                                     # /games/:id/actions/:verb,
│                                     # /games/:id/intel/:target_type/:target_id
├── api/client.ts                     # 115 lines, get/post/postForm wrappers
├── stores/
│   ├── gameStore.ts                  # 184 lines, Zustand. Has snapshot, mapData,
│                                     # available, tickSummaries. Methods: fetchState,
│                                     # fetchMapData, submitAction, resolveTick.
│   ├── uiStore.ts                    # 314 lines, lens/breadcrumb/notifications/
│                                     # selection/panel state.
│   └── mapStore.ts                   # 55 lines, activeLayer + activeFraming +
│                                     # lensOverride flag.
├── hooks/
│   ├── useGameState.ts               # 87 lines, polling wrapper around gameStore.
│   ├── useLens.ts                    # 39 lines, switchLens coordinates uiStore +
│                                     # mapStore.
│   └── usePersistentUI.ts            # localStorage sync.
├── lib/
│   ├── lensDefinitions.ts            # 318 lines. INDICATOR_DEFINITIONS table with
│                                     # one-shot compute lambdas. LENS_DEFINITIONS
│                                     # table. THIS IS THE CLOSEST EXISTING
│                                     # ANALOGUE TO A SELECTOR REGISTRY.
│   └── eventClassifier.ts
├── types/game.ts                     # 547 lines. GameSnapshot, OrgState,
│                                     # TerritoryState, DerivedBlock, ValueTensor,
│                                     # ImperialRent, ClassAggregate, EdgeMode,
│                                     # HyperedgeCategory, etc.
├── components/
│   ├── ActionPage.tsx                # 456 lines. Inline fetch for orgs, inline
│                                     # fetch for targets, per-verb branching for
│                                     # form fields. The most refactor-needy file.
│   ├── OrganizationsPage.tsx         # 91 lines. Inline fetch for orgs duplicating
│                                     # ActionPage's fetch.
│   ├── IntelPage.tsx                 # 72 lines. Reads snapshot via useGameState,
│                                     # delegates to HexInspector or NodeInspector.
│   ├── layout/GameShell.tsx          # 245 lines. The over-stuffed Briefing route.
│   ├── layout/LensBar.tsx            # Bottom-of-screen lens selector.
│   ├── action/                       # ActionComposer, VerbSelector, TargetSelector,
│                                     # ActionPreview. Used by GameShell right panel.
│   ├── inspector/HexInspector.tsx    # 203 lines. Flat metric lookups, no breakdown.
│   ├── inspector/NodeInspector.tsx   # 210 lines. Same.
│   ├── map/HexTooltip.tsx            # Lens-prioritized flat metrics. No breakdown.
│   ├── map/LayerControls.tsx         # In-map layer selector — competes with LensBar.
│   └── map/DeckGLMap.tsx             # Renders LayerControls inside the map.
```

Backend contract reference: `specs/051-engine-frontend-integration/spec.md` and `specs/052-worldstate-snapshot-contract/`. Routes and shapes are fixed by those specs; frontend changes do not require new endpoints.

---

## Phase 1: Data Layer Unification

**Goal:** Every component reads from `gameStore`. No component calls `apiGet`/`apiPost` from `@/api/client` directly except `gameStore` itself, the auth flow (`LoginPage`, `App.tsx whoami`), and `GameList` (which is pre-game and outside the snapshot).

**Confidence: 95%.** This is a mechanical refactor. The pattern already exists in `gameStore.fetchState`; we're extending it to two more endpoints and migrating two callers.

### Steps

Add three new methods to `gameStore`:

```typescript
// stores/gameStore.ts
interface GameState {
  // ... existing fields
  playerOrgs: OrgState[]
  playerOrgsLoaded: boolean
  verbTargets: Record<string, VerbTargetData>  // keyed by `${verb}:${orgId}`

  fetchPlayerOrgs: (gameId: string) => Promise<void>
  fetchVerbTargets: (gameId: string, verb: PlayerVerb, orgId: string) => Promise<void>
  invalidateVerbTargets: () => void  // call on tick resolve
}
```

`fetchPlayerOrgs` hits `/api/games/{id}/organizations/?player_only=true` and stores in `playerOrgs`. `fetchVerbTargets` hits `/api/games/{id}/actions/{verb}/targets/?org_id={orgId}` and caches by composite key. `resolveTick` calls `invalidateVerbTargets` after success — targets are tick-stale.

Refactor `OrganizationsPage` to:

```typescript
const playerOrgs = useGameStore(s => s.playerOrgs)
const fetchPlayerOrgs = useGameStore(s => s.fetchPlayerOrgs)
useEffect(() => { void fetchPlayerOrgs(gameId) }, [gameId, fetchPlayerOrgs])
```

No more local `useState<OrgState[]>([])`, no more inline `apiGet`. Loading/error state comes from the store.

Refactor `ActionPage` to read both `playerOrgs` and `verbTargets[verb:orgId]` from the store. Its useEffects shrink to dispatch calls.

### Acceptance Criteria

- Zero `import { get, post } from "@/api/client"` outside `gameStore`, `LoginPage`, `App.tsx`, `GameList`.
- `OrganizationsPage` is under 60 lines (was 91; the inline fetch was ~30 of those).
- `ActionPage` is under 350 lines (was 456; remove inline fetch logic, but the per-verb form branching stays for now — Phase 4 handles that).
- All existing Vitest tests pass. New test: `gameStore.fetchPlayerOrgs` correctly populates `playerOrgs` and clears on `reset`.
- Playwright `game-loop` suite still passes.

### Anti-Patterns

- Don't introduce React Query / TanStack Query in this phase. The polling pattern in `useGameState` works; adding Query in parallel creates two data layers. Migration to Query is a future, separate decision.
- Don't add new endpoints. Use existing ones.
- Don't snapshot-merge `playerOrgs` into the main `snapshot` object. Keep them as separate fields in the store; they have different lifecycles and different invalidation triggers.

---

## Phase 2: Selector Registry and BabylonScriptValue

**Goal:** Build the Paradox-pattern selector and breakdown infrastructure. Don't apply it yet — just have it ready and tested.

**Confidence: 80%.** The Paradox `script_value` + `GetScriptValueBreakdown` pattern is well-understood. Translating to TypeScript without runtime-evaluated expressions (which would be the engine's job, not the client's) is the design problem. We resolve it with typed accessor functions that return both a value and a contributor list.

### Architecture

Create `web/frontend/src/lib/selectors/`:

```
selectors/
├── types.ts           # ScriptValue, Breakdown, Contributor types
├── registry.ts        # SelectorRegistry class + global instance
├── primitives.ts      # Leaf accessors (read directly from snapshot)
├── derived.ts         # Composed selectors (combine primitives + script values)
└── index.ts           # Public API
```

### `types.ts`

```typescript
export interface Contributor {
  /** Stable label shown in UI breakdown. */
  label: string
  /** The value this contributor adds (or multiplies, per `op`). */
  value: number
  /** How this contributor combines: 'add' | 'mult' | 'replace'. */
  op: 'add' | 'mult' | 'replace'
  /** Source citation: GameDefines key, snapshot path, or sub-script-value name. */
  source: SourceRef
  /** Nested breakdown if this contributor is itself a script value. */
  breakdown?: Breakdown
}

export type SourceRef =
  | { kind: 'snapshot'; path: string }                    // e.g. 'organizations[0].vanguard.cadre'
  | { kind: 'gamedefines'; key: string }                  // e.g. 'IMPERIAL_RENT_BASE'
  | { kind: 'reference'; dataset: string; rowKey: string } // e.g. QCEW row
  | { kind: 'script_value'; name: string }                // recursive
  | { kind: 'computed'; expression: string }              // for prediction deltas etc

export interface Breakdown {
  name: string
  total: number
  contributors: Contributor[]
}

export interface Scope {
  snapshot: GameSnapshot
  /** The "this" entity — org, hex, edge, hyperedge. */
  this: ScopeEntity | null
  /** The originating scope of the chain. */
  root: ScopeEntity | null
  /** Named bookmarks (Paradox `save_scope_as`). */
  saved: Record<string, ScopeEntity>
}

export type ScopeEntity =
  | { kind: 'org'; id: string }
  | { kind: 'hex'; id: string }
  | { kind: 'hyperedge'; id: string }
  | { kind: 'edge'; from: string; to: string }
  | { kind: 'institution'; id: string }

export interface ScriptValue<T = number> {
  name: string
  /** Resolve to a value. */
  evaluate: (scope: Scope) => T
  /** Resolve to a value plus the breakdown that produced it. */
  breakdown: (scope: Scope) => Breakdown
}
```

### `registry.ts`

```typescript
export class SelectorRegistry {
  private values = new Map<string, ScriptValue<unknown>>()

  register<T>(sv: ScriptValue<T>): void {
    if (this.values.has(sv.name)) {
      throw new Error(`Duplicate selector: ${sv.name}`)
    }
    this.values.set(sv.name, sv as ScriptValue<unknown>)
  }

  get<T>(name: string): ScriptValue<T> {
    const sv = this.values.get(name)
    if (!sv) throw new Error(`Unknown selector: ${name}`)
    return sv as ScriptValue<T>
  }

  has(name: string): boolean {
    return this.values.has(name)
  }

  /** Dump the full registry — Paradox `DumpDataTypes` analogue. */
  dump(): { name: string; signature: string }[] {
    return Array.from(this.values.entries()).map(([name, sv]) => ({
      name,
      signature: sv.toString(),
    }))
  }
}

export const selectors = new SelectorRegistry()
```

### `primitives.ts` (examples)

```typescript
export const orgCadre: ScriptValue<number> = {
  name: 'org.cadre',
  evaluate: (scope) => {
    if (scope.this?.kind !== 'org') return 0
    const org = scope.snapshot.organizations.find(o => o.id === scope.this.id)
    return org?.vanguard?.cadre ?? 0
  },
  breakdown: (scope) => {
    const total = orgCadre.evaluate(scope)
    return {
      name: 'org.cadre',
      total,
      contributors: scope.this?.kind === 'org' ? [{
        label: 'Cadre on hand',
        value: total,
        op: 'add',
        source: { kind: 'snapshot', path: `organizations[id=${scope.this.id}].vanguard.cadre` },
      }] : [],
    }
  },
}

export const hexHeat: ScriptValue<number> = {
  name: 'hex.heat',
  evaluate: (scope) => {
    if (scope.this?.kind !== 'hex') return 0
    return scope.snapshot.territories.find(t => t.id === scope.this.id)?.heat ?? 0
  },
  breakdown: (scope) => {
    const total = hexHeat.evaluate(scope)
    return {
      name: 'hex.heat',
      total,
      contributors: [{
        label: 'Heat (state attention)',
        value: total,
        op: 'add',
        source: { kind: 'snapshot', path: `territories[id=${scope.this?.id ?? '?'}].heat` },
      }],
    }
  },
}
```

### `derived.ts` (composition)

```typescript
export const orgEffectiveCadre: ScriptValue<number> = {
  name: 'org.effective_cadre',
  evaluate: (scope) => {
    const base = selectors.get<number>('org.cadre').evaluate(scope)
    const heatPenalty = hexHeatForOrg(scope) * GAMEDEFINES.HEAT_CADRE_PENALTY
    return Math.max(0, base * (1 - heatPenalty))
  },
  breakdown: (scope) => {
    const baseBd = selectors.get<number>('org.cadre').breakdown(scope)
    const heat = hexHeatForOrg(scope)
    const penalty = heat * GAMEDEFINES.HEAT_CADRE_PENALTY
    const total = Math.max(0, baseBd.total * (1 - penalty))
    return {
      name: 'org.effective_cadre',
      total,
      contributors: [
        {
          label: 'Base cadre',
          value: baseBd.total,
          op: 'add',
          source: { kind: 'script_value', name: 'org.cadre' },
          breakdown: baseBd,
        },
        {
          label: 'Heat penalty',
          value: -baseBd.total * penalty,
          op: 'add',
          source: { kind: 'computed', expression: `cadre × heat × ${GAMEDEFINES.HEAT_CADRE_PENALTY}` },
        },
      ],
    }
  },
}
```

`GAMEDEFINES` is a frozen object loaded once from the server at game start. Add a route reference: if the constants endpoint doesn't exist yet, add `/api/gamedefines/` returning the relevant subset. (Check whether this exists — if not, the engineer does add this small Django view, but only this one. Don't expand backend scope.)

### Acceptance Criteria

- `lib/selectors/` exists with the four files above.
- At least 6 primitive selectors and 3 derived selectors registered, all with breakdown methods.
- `selectors.dump()` returns a sorted, complete list — this becomes the typed surface for IntelPage and HexTooltip in later phases.
- Vitest test suite covers: register/get/duplicate-name error, evaluate vs breakdown consistency (every breakdown's `total` equals its `evaluate`), recursive breakdown traversal.
- No selector reaches into anything outside `Scope.snapshot` and `GAMEDEFINES`. No `fetch`, no store reads.

### Anti-Patterns

- **Don't introduce a runtime expression language.** Do not parse strings like `[org.cadre.divide(hex.heat)]` and eval them. Selectors are TypeScript functions. The Paradox bracket-language exists because it's a hot-reloadable scripting layer for non-engineers; you have a TypeScript codebase with hot-reload built in.
- **Don't mix selectors with React.** `lib/selectors/` is pure functions. No hooks, no JSX. React components consume selectors via a thin hook in Phase 4.
- **Don't force every UI value through selectors yet.** Phase 2 is scaffolding. Adoption is incremental in Phases 4 and 5.
- **Don't add async to selectors.** They evaluate synchronously against the in-memory snapshot. If a value isn't in the snapshot, the selector returns 0 / null and the contributor list is empty — the snapshot is the contract.

---

## Phase 3: Slot Primitive

**Goal:** Add a typed slot composition primitive analogous to Paradox's `block`/`blockoverride`. Don't apply it yet.

**Confidence: 75%.** React's `children` prop is single-slot; named slots require either compound components or a third-party library. The pattern below is hand-rolled but small and avoids a dependency. If the team prefers `@radix-ui/react-slot` or similar, swap; the API surface should match.

### Architecture

Create `web/frontend/src/lib/slots.tsx`:

```typescript
import { ReactNode, createContext, useContext } from 'react'

type SlotMap = Record<string, ReactNode>

const SlotContext = createContext<SlotMap>({})

interface SlotsProps {
  values: SlotMap
  children: ReactNode
}

/** Provide named slot content to descendants. */
export function Slots({ values, children }: SlotsProps) {
  const parent = useContext(SlotContext)
  return (
    <SlotContext.Provider value={{ ...parent, ...values }}>
      {children}
    </SlotContext.Provider>
  )
}

interface SlotProps {
  name: string
  fallback?: ReactNode
}

/** Render the named slot, or a fallback if not provided. */
export function Slot({ name, fallback = null }: SlotProps) {
  const slots = useContext(SlotContext)
  return <>{slots[name] ?? fallback}</>
}
```

Usage pattern:

```tsx
// Generic shell
function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="...">
      <header><Slot name="title" fallback={<h1>Untitled</h1>} /></header>
      <aside><Slot name="actions" /></aside>
      <main>{children}</main>
      <footer><Slot name="status" /></footer>
    </div>
  )
}

// Caller fills slots
<Slots values={{
  title: <h1 className="text-gold">Wayne County</h1>,
  actions: <VerbButtons orgId="..." />,
  status: <ResourcePanel playerOrg={...} />,
}}>
  <PageShell>{mainContent}</PageShell>
</Slots>
```

### Acceptance Criteria

- `lib/slots.tsx` exists with `Slots` provider and `Slot` consumer.
- Vitest tests cover: slot renders content, slot renders fallback when empty, nested `Slots` providers compose (inner overrides outer for matching keys).
- Public API is exactly `Slots` and `Slot`. Don't export internal context.

### Anti-Patterns

- Don't make slots stateful. They render content; they don't manage state. Stateful logic stays in the components passed as slot values.
- Don't add a third primitive ("OptionalSlot", "SingletonSlot", etc.). Just the two.
- Don't try to type-check slot names at compile time with template literal types unless trivial. The runtime fallback is fine for now.

---

## Phase 4: ActionPage Refactor

**Goal:** ActionPage becomes the template for verb pages. Apply Phase 1 (store reads), Phase 2 (selectors), Phase 3 (slots). The per-verb branching collapses into a verb-config table.

**Confidence: 85%.** The structure is clear; the risk is that one of the nine verbs has special-case rendering that doesn't fit the verb-config shape, in which case it gets a dedicated page rather than a config entry. That's fine — the template handles 7 of 9, edge cases are explicit.

### Architecture

Create `web/frontend/src/lib/verbs/`:

```
verbs/
├── types.ts                 # VerbConfig type
├── educate.ts               # Per-verb config
├── aid.ts
├── attack.ts
├── ... (one per verb)
├── registry.ts              # VERB_REGISTRY: Record<PlayerVerb, VerbConfig>
└── index.ts
```

```typescript
// types.ts
export interface VerbConfig {
  verb: PlayerVerb
  /** Human-readable label and description. */
  label: string
  description: string
  /** Required resource cost — selector that returns the cost in cadre/sympathy/etc. */
  cost: ScriptValue<{ cadre: number; sympathy: number; budget: number }>
  /** Target type expected by the API. */
  targetKind: 'community' | 'organization' | 'territory' | 'edge' | 'self'
  /** Target endpoint shape parser. */
  parseTargets: (raw: unknown) => VerbTarget[]
  /** Form fields beyond org and target. */
  paramFields: ParamField[]
  /** Predicted-effect breakdown selector — drives the preview tooltip. */
  predictedEffect?: ScriptValue<number>
}

export interface VerbTarget {
  id: string
  label: string
  /** What this target is, in scope-entity terms. */
  scope: ScopeEntity
}

export interface ParamField {
  name: string
  kind: 'select' | 'number' | 'text' | 'percent'
  label: string
  options?: { value: string; label: string }[]
  default?: unknown
}
```

`ActionPage` becomes:

```tsx
export function ActionPage({ username, onLogout }) {
  const { id: gameId, verb } = useParams()
  const config = VERB_REGISTRY[verb as PlayerVerb]
  if (!config) return <NotFound verb={verb} />

  const playerOrgs = useGameStore(s => s.playerOrgs)
  const verbTargets = useGameStore(s => s.verbTargets[`${verb}:${selectedOrgId}`])
  const fetchPlayerOrgs = useGameStore(s => s.fetchPlayerOrgs)
  const fetchVerbTargets = useGameStore(s => s.fetchVerbTargets)
  const submitAction = useGameStore(s => s.submitAction)

  // ... drive fetches off mounted gameId / selectedOrg

  return (
    <Slots values={{
      title: <h2>{config.label}</h2>,
      preview: config.predictedEffect && (
        <BreakdownTooltip selector={config.predictedEffect} scope={currentScope} />
      ),
    }}>
      <VerbShell>
        <OrgPicker orgs={playerOrgs} selected={selectedOrgId} onChange={setSelectedOrgId} />
        <TargetPicker
          kind={config.targetKind}
          targets={verbTargets ? config.parseTargets(verbTargets) : []}
          selected={selectedTargetId}
          onChange={setSelectedTargetId}
        />
        <ParamForm fields={config.paramFields} values={params} onChange={setParams} />
        <SubmitButton
          cost={config.cost}
          onSubmit={() => submitAction(gameId, { verb, org_id: selectedOrgId, target_id: selectedTargetId, params })}
        />
      </VerbShell>
    </Slots>
  )
}
```

`VerbShell` is a generic layout component using `Slot` for chrome (title, preview, status).

### Acceptance Criteria

- 9 verb config files, each with a registered config.
- `ActionPage.tsx` is under 150 lines (was 456). Per-verb branching is gone.
- Each verb's predicted-effect breakdown renders in the preview area when target is selected — this is the first user-visible application of `BabylonScriptValue`.
- All existing tests for ActionPage and ActionComposer pass. Add per-verb tests: each config's `parseTargets` correctly handles the API's response shape for that verb.
- One Playwright test per verb that walks through org → target → submit and verifies a tick advances.

### Anti-Patterns

- **Don't generalize prematurely.** If two verbs share `parseTargets`, fine; if six do, extract a helper. Don't build a generic `targetParserFromShape` engine.
- **Don't reintroduce the inline fetches.** All data flows through the store.
- **Don't ship verb-specific business logic to the frontend.** Cost computations should pull from `GAMEDEFINES` or be returned by the targets endpoint. Don't hardcode "Educate costs 2 cadre" in the React code; that's a magic constant.

---

## Phase 5: BreakdownTooltip Component and IntelPage Application

**Goal:** First user-facing breakdown tooltip. Land it on `HexInspector`'s top-three metrics, then expand.

**Confidence: 90%.** UI work, no architectural decisions left.

### `components/inspector/BreakdownTooltip.tsx`

```tsx
import { useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import type { ScriptValue, Scope, Breakdown } from '@/lib/selectors'

interface BreakdownTooltipProps {
  selector: ScriptValue<number>
  scope: Scope
  /** How to format the leaf value. */
  format?: (n: number) => string
  /** Trigger element (the value being labeled). */
  children: React.ReactNode
}

export function BreakdownTooltip({ selector, scope, format = (n) => n.toFixed(2), children }: BreakdownTooltipProps) {
  const [open, setOpen] = useState(false)
  const breakdown = selector.breakdown(scope)
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <span className="cursor-help underline decoration-dotted">{children}</span>
      </Popover.Trigger>
      <Popover.Content className="z-50 rounded-md border border-wet-concrete bg-dark-metal p-3 text-xs shadow-lg">
        <BreakdownTree breakdown={breakdown} format={format} depth={0} />
      </Popover.Content>
    </Popover.Root>
  )
}

function BreakdownTree({ breakdown, format, depth }: { breakdown: Breakdown; format: (n: number) => string; depth: number }) {
  return (
    <div style={{ paddingLeft: depth * 12 }}>
      <div className="flex justify-between gap-4 border-b border-soot pb-1 mb-1">
        <span className="font-semibold text-bone">{breakdown.name}</span>
        <span className="font-mono text-gold">{format(breakdown.total)}</span>
      </div>
      {breakdown.contributors.map((c, i) => (
        <div key={i} className="ml-2">
          <div className="flex justify-between gap-4 text-ash">
            <span>
              {c.label}
              {c.op === 'mult' && <span className="text-ash"> ×</span>}
            </span>
            <span className="font-mono">{format(c.value)}</span>
          </div>
          <div className="ml-2 text-[10px] text-wet-concrete">
            {sourceLabel(c.source)}
          </div>
          {c.breakdown && depth < 4 && (
            <BreakdownTree breakdown={c.breakdown} format={format} depth={depth + 1} />
          )}
        </div>
      ))}
    </div>
  )
}

function sourceLabel(s: SourceRef): string {
  switch (s.kind) {
    case 'snapshot': return `from snapshot.${s.path}`
    case 'gamedefines': return `GameDefines.${s.key}`
    case 'reference': return `${s.dataset}#${s.rowKey}`
    case 'script_value': return `→ ${s.name}`
    case 'computed': return s.expression
  }
}
```

`@radix-ui/react-popover` is already in deck dependencies (via shadcn). If not, add it; it's the standard for nested-popover correctness.

### Apply to `HexInspector`

Replace the top three `Stat` rows with `BreakdownTooltip`-wrapped values for `hex.heat`, `hex.imperial_rent`, and `hex.population`. The remaining rows stay as flat displays for now — incremental adoption.

### Apply to `HexTooltip` (the hover tooltip on the map)

Stretch goal for this phase: the hover tooltip becomes the top-level breakdown view, with the inspector being the persistent / clickable version. Defer if it complicates exit transitions; the inspector application is the must-have.

### Acceptance Criteria

- `BreakdownTooltip` exists and is tested (Vitest snapshots and interaction tests).
- `HexInspector` shows three breakdown-enabled metrics, each clicking through to a recursive contributor list at least 2 levels deep.
- One Playwright test: navigate to `/games/:id/intel/territory/:hex_id`, click the heat value, assert the breakdown popover shows expected contributors.
- Max breakdown nesting depth capped at 4 (per `BreakdownTree` `depth < 4` guard) — this prevents accidental cycles from rendering forever.

### Anti-Patterns

- Don't auto-open breakdown tooltips on hover. Click-to-open. Hover-to-open is fine for the simple `HexTooltip` (already exists), but the breakdown tooltip needs a stable target the user can move into. Paradox calls this "action lock"; without it, mouse-out dismisses the tip before the user can drill in.
- Don't render the source citation as raw JSON. Use `sourceLabel` to humanize. Add new `kind` cases as you encounter them.
- Don't flatten contributors with `op: 'mult'` into addition. The label needs to indicate the operation.

---

## Phase 6: Briefing Strip (Step 5 of April Plan)

**Goal:** `GameShell` becomes lean. Map + sparkline strip + tick narrative + End Turn. No verb composer, no full-size charts, no graph panel.

**Confidence: 95%.** Mechanical removal.

### Steps

In `GameShell.tsx`:

1. Remove `<ActionComposer>` from the right panel. The right panel becomes either (a) deleted entirely with the map filling the width, or (b) replaced with a `<TickNarrative>` component that displays the latest `events` from the snapshot in a readable feed. Prefer (a) for MVP; add `<TickNarrative>` as a follow-up.
2. Remove `<TimeSeries>` from the bottom panel. Replace with `<SparklineStrip>` showing 3 small (h-12) sparklines for `avg_heat`, `avg_consciousness`, `total_wealth` over the last 20 ticks. Use `tickSummaries` from `gameStore`.
3. Remove `<EventLog>` from the bottom panel. Move full-size event log to a future `/games/:id/log` route (out of scope for this prompt; just make the link work or stub the route).
4. Remove `<GraphView>` from the left panel. Move to a future `/games/:id/topology` route. The `graphPanelOpen` and `graphPanelWidth` UI state can stay in `uiStore` for later use.
5. Keep: `TopBar`, `ResourcePanel`, `TrapIndicator`, the map area, the End Turn button (which is in TopBar). Add a navigation strip somewhere visible with links to `/orgs`, `/actions/:verb` (defaulting to first verb), `/intel/...` (when something is selected).

The `TickResults` panel that appears after End Turn should remain — it's the immediate feedback Vic3 calls "predictable feedback for taken actions" — but render as a dismissible toast/modal rather than a permanent right-panel block.

### Acceptance Criteria

- `GameShell.tsx` is under 150 lines (was 245).
- Browser dev-tools shows no `<ActionComposer>`, `<TimeSeries>` (full version), `<EventLog>` (full version), or `<GraphView>` rendered at `/games/:id`.
- Sparklines render correctly with 20-tick history. Tested at tick 0 (empty), tick 5, tick 30.
- End Turn → resolves tick → TickResults toast appears → dismissible → sparklines update.
- Existing Playwright `game-loop` suite passes after updating selectors that referenced removed components.

### Anti-Patterns

- Don't keep the removed components "just in case." Delete the imports. They live at their dedicated routes now.
- Don't add a "compact mode" toggle that brings everything back. The whole point is fewer surfaces, not configurable density.

---

## Phase 7: Lens vs Layer Consolidation

**Goal:** One selector, one mental model. Pick lens.

**Confidence: 90%.** The decision is forced by the fact that lenses already define a `primaryLayer` and the layer override exists only as a side-channel from `LayerControls`. Removing the override eliminates the conflict.

### Steps

1. Delete `LayerControls.tsx` and remove its render from `DeckGLMap.tsx`.
2. Remove the `lensOverride` flag from `mapStore`. `setActiveLayer` becomes a private/internal action only callable from `useLens.switchLens`.
3. Lens definitions retain their `primaryLayer` mapping. When the user clicks a lens, the map's color encoding switches to that lens's primary layer. No way to override.
4. If a power user wants the old layer-switching freedom, that is a future consideration and lives behind a "developer mode" toggle, not on the main UI surface.
5. `MapLegend` renders the lens's primary layer name and color scale, sourced from `lensDefinitions.ts`.

### Acceptance Criteria

- `LayerControls.tsx` is deleted.
- `mapStore.lensOverride` is removed (delete the flag, delete `clearLensOverride`).
- One selector visible at `/games/:id`: the LensBar.
- Test: switching lenses changes both the right-panel emphasis (already worked) and the map color (already worked via `primaryLayer`); there is no path to make them disagree.

### Anti-Patterns

- Don't try to "preserve user choice" by keeping the layer override behind a config flag. The conflict is real: if the lens says "show me the political view" and the user has manually flipped to the heat layer, the legend, the sparklines, and the inspector are no longer telling a coherent story. One source of truth.
- Don't move LayerControls to a different page. Delete it.

---

## Cross-Cutting Anti-Patterns

These apply across all phases.

- **No new endpoints.** Use existing routes from `specs/051-engine-frontend-integration` and `specs/052-worldstate-snapshot-contract`. The single exception is `/api/gamedefines/` if it doesn't yet exist; add it with minimal Django plumbing, no engine changes.
- **No state mutation outside Zustand stores.** Components use store actions, never directly call `apiPost`. The auth flow is the only exception and that's already isolated.
- **No event handlers that make multiple network calls.** If clicking a button needs to fetch + submit + refetch, that's a store action — extract it.
- **No new dependencies without justification.** Radix Popover is fine (likely already in shadcn dependencies). React Query is not fine for this prompt's scope. D3, Sigma, and Recharts are already there for graphs/charts; don't add a fourth.
- **No client-side simulation logic.** A predicted-effect selector reads from the snapshot and `GAMEDEFINES`. It does not simulate forward N ticks; that's the engine's job. If you need a forward simulation for preview, that's a server-side endpoint (out of scope for this prompt).
- **No hyperedge visualization as pairwise edges.** Constitutional. If you find yourself drawing a fan of edges from a community node to its members, stop.

---

## Acceptance Criteria for the Whole Prompt

The work is done when all of the following hold:

1. `OrganizationsPage`, `ActionPage`, `IntelPage`, `GameShell` all read game data exclusively through `gameStore`. No inline `apiGet`/`apiPost` outside `gameStore`, the auth flow, and `GameList`.
2. `lib/selectors/` exists with at least 6 primitive and 3 derived selectors, each producing both a value and a breakdown.
3. `lib/slots.tsx` exists and is used by at least one component (`VerbShell`).
4. `lib/verbs/` exists with 9 verb configs. `ActionPage.tsx` is under 150 lines.
5. `BreakdownTooltip` renders on at least 3 metrics in `HexInspector`, with click-to-open and recursive drill-down.
6. `GameShell.tsx` is under 150 lines and renders only TopBar, ResourcePanel, TrapIndicator, map, sparkline strip, navigation links, and End Turn flow.
7. `LensBar` is the only map-color selector. `LayerControls` is deleted. `mapStore.lensOverride` is gone.
8. All existing Vitest tests pass. New tests cover store extensions, selectors, slots, breakdown tooltip, and verb configs.
9. All Playwright `game-loop` tests pass, possibly with updated selectors but no behavioral regressions.
10. No new Django endpoints except possibly `/api/gamedefines/`, no engine changes, no schema changes.

If a constraint conflicts with a phase, phases 1, 2, 3 are foundational and cannot be skipped. Phases 4, 5, 6, 7 can be reordered if there's a defensible reason; surface the reason before reordering.

---

## Sources / Prior Decisions

These are not optional reading; they are the substrate the agent should consult when making judgment calls. Read them in this order.

**Read first — repo-level context:**

- **`AGENTS.md`** — the OpenCode entry point. Schema for project identity, role, and the constitutional compact (MUST / MUST NOT). Skim once.
- **`docs/agents/index.md`** — the project wiki. Query before re-deriving anything from code. Per the Karpathy pattern documented in AGENTS.md, the wiki is the authoritative compounding knowledge base.
- **`docs/agents/architecture.md`** — read before Phase 2 (selector registry design).
- **`docs/agents/coding-standards.md`** — read before writing code in any phase.
- **`docs/agents/testing.md`** — read before writing tests.
- **`.specify/memory/constitution.md`** — full constitution. Source of every "non-negotiable" in this prompt. Consult on judgment calls.

**Read as needed — specs that bound the work:**

- **`specs/042-game-ui-overhaul/`** — the original Vic3-inspired UI overhaul spec that produced what's currently shipped (lenses, breadcrumbs, indicators). Useful background for Phases 6 and 7.
- **`specs/051-engine-frontend-integration/spec.md`** — the durable HTTP contract between Django and React. Don't violate.
- **`specs/052-worldstate-snapshot-contract/`** — the shape of `GameSnapshot` and `DerivedBlock`. The selector primitives in Phase 2 must align with these field paths.
- **`specs/044-spec_educate_api_endpoint.md` through `specs/050-spec_negotiate_api_endpoint.md`** — per-verb API shapes. Read the relevant one before writing each verb config in Phase 4.

**Read for design intent:**

- **April 16 2026 chat ("Frontend development progress")** — the original god-page diagnosis and 6-step extraction plan; Steps 1-4 are done, this prompt is Steps 5+ plus architectural additions.
- **Paradox UI extraction artifact** — the research document in this conversation series titled "Paradox Grand Strategy Architecture" that motivates `BabylonScriptValue` and the slot pattern. Specifically Section 11 ("Nested Tooltips and Provenance Breakdowns") and Section 10 (".gui Declarative UI Language") of that artifact.

**After completing significant work, ingest back to the wiki.** Per AGENTS.md: update relevant pages in `docs/agents/` with what you learned. The selector registry, slot primitive, and verb-config pattern are exactly the kind of compounding knowledge the wiki is for.

---

## Final Word

Don't build all of this in one merge. Phase 1 is one PR. Phase 2 is one PR. Phase 3 is one PR. Phases 4 and 5 can be a single PR if scoped tightly. Phases 6 and 7 should be one PR each.

If a phase reveals a constraint that genuinely blocks the work — surface it before continuing. But the bar for "blocked" is high: most "blockers" are missing context that's available by reading the codebase or the linked specs.

When in doubt, the constitution is the authority. When the constitution is silent, the current shipped code is the authority. When both are silent, the Paradox patterns from the research artifact are the default. When all three are silent, ask.
