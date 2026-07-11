/**
 * registry.ts — the lens registry (spec-113 architecture §3.1, DESIGN_BIBLE.md
 * §2.2/§3/§9.1/§9.2/§9.5). Presentation metadata OVER the existing `Lens`
 * union (`@/lib/lens`) — `lib/lens.ts`, `mapLensLayers.ts`, `regionFill.ts`
 * remain the fill engine; this module never computes a fill color itself.
 *
 * `MapLensBar`/`MapLegend` render from this registry instead of hardcoding
 * the lens roster (the old `MapModeSelector` did); `useLensCycleShortcut`
 * (Q/E, `store/orchestrator.ts`) cycles `LENS_REGISTRY`'s declaration order
 * instead of the narrower `LENS_MODES` tuple, so every registered lens
 * (including metric/class_composition ones) is reachable by keyboard.
 */

import { DEFAULT_LENS, lensKey, type Lens } from "@/lib/lens";
import {
  STANCE_COLOR,
  SOCIAL_ROLE_COLOR,
  SOCIAL_ROLE_LABELS,
  type BalkanizationBlock,
} from "@/components/map/mapLensLayers";
import { DATA_RAMPS, rampForLayer, type RGBAColor } from "@/theme/colors";
import type { LensGroupId } from "./groups";

export type LensLegend =
  | { kind: "ramp"; stops: string[] }
  | { kind: "categorical"; entries: { label: string; color: RGBAColor }[] }
  | { kind: "none" };

/**
 * What `availableWhen` reads to decide whether a *starred* lens (bible
 * §3.2's "needs an additive `/map/` property" entries — `class_composition`,
 * `solidarity_index`) is shown yet. `undefined`/missing `availableMetrics`
 * means "unknown, e.g. before the first `/map/` response" and is treated as
 * available — a lens never flickers hidden-then-shown on the very first
 * paint. Political lenses (stance/faction/collapse) are pre-existing, not
 * starred, and stay unconditionally available (`alwaysAvailable` below) —
 * matching `MapModeSelector`'s prior behavior of always rendering every mode
 * button; their honest "no data yet" degradation stays where it already
 * lived, at fill time (`mapLensLayers.ts`'s `buildLensLayers`, NO_DATA gray
 * + a "— no data" legend-label suffix), not at registry/button level.
 */
export interface LensAvailabilityContext {
  balkanization?: BalkanizationBlock | null;
  /** `mapData.metadata.available_metrics` — the real `/map/` payload's advertised metric list. */
  availableMetrics?: readonly string[];
}

export interface MapLensDef {
  id: string;
  group: LensGroupId;
  label: string;
  tooltip: string;
  hotkey?: string;
  legend: LensLegend;
  toLens: () => Lens;
  availableWhen: (ctx: LensAvailabilityContext) => boolean;
}

function hasMetric(name: string): (ctx: LensAvailabilityContext) => boolean {
  return (ctx) => (ctx.availableMetrics ? ctx.availableMetrics.includes(name) : true);
}

function alwaysAvailable(): boolean {
  return true;
}

const STANCE_ENTRIES: { label: string; color: RGBAColor }[] = [
  { label: "Uphold", color: STANCE_COLOR.UPHOLD },
  { label: "Ignore", color: STANCE_COLOR.IGNORE },
  { label: "Abolish", color: STANCE_COLOR.ABOLISH },
];

const STANCE_LEGEND: LensLegend = { kind: "categorical", entries: STANCE_ENTRIES };

const COLLAPSE_LEGEND: LensLegend = {
  kind: "categorical",
  entries: [...STANCE_ENTRIES, { label: "Contested", color: [255, 180, 50, 220] }],
};

const CLASS_COMPOSITION_LEGEND: LensLegend = {
  kind: "categorical",
  entries: Object.entries(SOCIAL_ROLE_LABELS).map(([role, label]) => ({
    label,
    color: SOCIAL_ROLE_COLOR[role] ?? [58, 53, 48, 160],
  })),
};

/**
 * The lens roster — DESIGN_BIBLE.md §3.2's table, filtered to lenses backed
 * by real data today (the "if a metric backs it" starred entries — wage
 * hierarchy, control ratio — are omitted rather than registered
 * permanently-unavailable). Declaration order is bar order AND Q/E cycle
 * order.
 */
export const LENS_REGISTRY: readonly MapLensDef[] = [
  // --- Extraction ---------------------------------------------------------
  {
    id: "imperial_rent",
    group: "extraction",
    label: "Imperial Rent",
    tooltip: "Net value extraction Φ — drained vs. enriched (THE DEFAULT LENS)",
    legend: { kind: "ramp", stops: rampForLayer("imperial_rent") },
    toLens: () => ({ kind: "metric", metric: "imperial_rent" }),
    availableWhen: hasMetric("imperial_rent"),
  },
  {
    id: "exploitation_rate",
    group: "extraction",
    label: "Exploitation Rate",
    tooltip: "Wage hierarchy — value produced vs. value paid (W_c / V_c)",
    legend: { kind: "ramp", stops: rampForLayer("exploitation_rate") },
    toLens: () => ({ kind: "metric", metric: "exploitation_rate" }),
    availableWhen: hasMetric("exploitation_rate"),
  },
  // --- Struggle ------------------------------------------------------------
  {
    id: "heat",
    group: "struggle",
    label: "Heat",
    tooltip: "State attention / surveillance pressure",
    legend: { kind: "ramp", stops: DATA_RAMPS.heat },
    toLens: () => ({ kind: "heat" }),
    availableWhen: alwaysAvailable,
  },
  {
    id: "solidarity_index",
    group: "struggle",
    label: "Solidarity",
    tooltip: "SOLIDARITY-edge density among a territory's working class",
    legend: { kind: "ramp", stops: DATA_RAMPS.solidarity },
    toLens: () => ({ kind: "metric", metric: "solidarity_index" }),
    availableWhen: hasMetric("solidarity_index"),
  },
  // --- Political -------------------------------------------------------
  {
    id: "stance",
    group: "political",
    label: "Stance",
    tooltip: "Colonial Stance + faction influence rings",
    legend: STANCE_LEGEND,
    toLens: () => ({ kind: "stance" }),
    availableWhen: alwaysAvailable,
  },
  {
    id: "faction",
    group: "political",
    label: "Faction",
    tooltip: "Single-faction influence filter",
    legend: STANCE_LEGEND,
    toLens: () => ({ kind: "faction" }),
    availableWhen: alwaysAvailable,
  },
  {
    id: "collapse",
    group: "political",
    label: "Collapse",
    tooltip: "Collapse-moment contested territories",
    legend: COLLAPSE_LEGEND,
    toLens: () => ({ kind: "collapse" }),
    availableWhen: alwaysAvailable,
  },
  {
    id: "class_composition",
    group: "political",
    label: "Class Composition",
    tooltip: "Population-weighted dominant social role (national oppression, MIM lexicon)",
    legend: CLASS_COMPOSITION_LEGEND,
    toLens: () => ({ kind: "class_composition" }),
    availableWhen: hasMetric("dominant_class"),
  },
  // --- Reproduction ----------------------------------------------------
  {
    id: "habitability",
    group: "reproduction",
    label: "Habitability",
    tooltip: "Metabolic-rift biocapacity gradient — ecology paired with extraction, never siloed",
    legend: { kind: "ramp", stops: DATA_RAMPS.biocapacity },
    toLens: () => ({ kind: "habitability" }),
    availableWhen: alwaysAvailable,
  },
];

/** `LENS_REGISTRY[0]` is the default lens — kept in sync with `lib/lens.ts`'s `DEFAULT_LENS`. */
export const DEFAULT_LENS_ID = "imperial_rent";

/** Find a registry entry whose `toLens()` produces the same lens (by `lensKey` identity). */
export function lensDefForLens(lens: Lens): MapLensDef | undefined {
  const key = lensKey(lens);
  return LENS_REGISTRY.find((def) => lensKey(def.toLens()) === key);
}

/** The registry entries whose `availableWhen` passes for `ctx` — degrades honestly, never hides by default. */
export function availableLensRegistry(ctx: LensAvailabilityContext): MapLensDef[] {
  return LENS_REGISTRY.filter((def) => def.availableWhen(ctx));
}

/** Groups `defs` (or the full registry) by `LensGroupId`, preserving `LENS_REGISTRY` order within each group. */
export function lensRegistryByGroup(ctx?: LensAvailabilityContext): Map<LensGroupId, MapLensDef[]> {
  const defs = ctx ? availableLensRegistry(ctx) : LENS_REGISTRY;
  const map = new Map<LensGroupId, MapLensDef[]>();
  for (const def of defs) {
    const bucket = map.get(def.group);
    if (bucket) {
      bucket.push(def);
    } else {
      map.set(def.group, [def]);
    }
  }
  return map;
}

// Sanity guard evaluated at module-load: DEFAULT_LENS and LENS_REGISTRY[0]
// must name the same lens, or Q/E cycling's "index 0 is the default" and
// MapLensBar's initial highlighted button would silently disagree.
const registryFirstEntry = LENS_REGISTRY[0];
if (!registryFirstEntry || lensKey(registryFirstEntry.toLens()) !== lensKey(DEFAULT_LENS)) {
  throw new Error("lib/lenses/registry.ts: LENS_REGISTRY[0] must match lib/lens.ts's DEFAULT_LENS");
}
