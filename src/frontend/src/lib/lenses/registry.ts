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
  TERRITORY_TYPE_COLOR,
  TERRITORY_TYPE_LABELS,
  VISION_STATE_COLOR,
  VISION_STATE_LABELS,
  type BalkanizationBlock,
} from "@/components/map/mapLensLayers";
import { DATA_RAMPS, FIELD_FLOW_COLOR, rampForLayer, type RGBAColor } from "@/theme/colors";
import type { LensGroupId } from "./groups";

/**
 * `vector` (Wave 3 §11's gradient-wind addition — the first non-ramp,
 * non-categorical legend kind): direction + magnitude render as flow
 * GEOMETRY (width/opacity), not a color scale or a discrete swatch list, so
 * neither `ramp` nor `categorical` honestly describes the encoding.
 * `color` is the wind's one fixed hue (weather-grammar law 1: hue stays
 * subordinate — the SAME triple `fieldFlow.ts`'s layers actually render,
 * `theme/colors.ts`'s `FIELD_FLOW_COLOR`, never a second duplicated value);
 * `description` is the direction/width key `MapLegend.tsx` renders verbatim.
 */
export type LensLegend =
  | { kind: "ramp"; stops: string[] }
  | { kind: "categorical"; entries: { label: string; color: RGBAColor }[] }
  | { kind: "vector"; color: RGBAColor; description: string }
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
 * Wave 2 Round 2's `territory_type` categorical legend — one entry per real
 * `TerritoryType` enum value, built from the SAME `TERRITORY_TYPE_COLOR`/
 * `TERRITORY_TYPE_LABELS` palette `mapLensLayers.ts`'s hex-native and
 * `regionFill.ts`'s aggregated fills both read — one source of truth, no
 * duplicated color table (mirrors `CLASS_COMPOSITION_LEGEND` above).
 */
const TERRITORY_TYPE_LEGEND: LensLegend = {
  kind: "categorical",
  entries: Object.entries(TERRITORY_TYPE_LABELS).map(([type, label]) => ({
    label,
    color: TERRITORY_TYPE_COLOR[type] ?? [58, 53, 48, 160],
  })),
};

/**
 * Wave 5's `vision_state` categorical legend — one entry per corpus
 * vision state (desert/mud/water), built from the SAME
 * `VISION_STATE_COLOR`/`VISION_STATE_LABELS` palette `mapLensLayers.ts`'s
 * hex-native and `regionFill.ts`'s aggregated fills both read — one source
 * of truth, no duplicated color table (mirrors `TERRITORY_TYPE_LEGEND`).
 */
const VISION_STATE_LEGEND: LensLegend = {
  kind: "categorical",
  entries: Object.entries(VISION_STATE_LABELS).map(([state, label]) => ({
    label,
    color: VISION_STATE_COLOR[state] ?? [58, 53, 48, 160],
  })),
};

/** Fixed legend swatch alpha for the vector lens (matches the ramp swatches' `RAMP_ALPHA`-adjacent legibility). */
const FIELD_FLOW_LEGEND_ALPHA = 220;

/**
 * `field_flow_exploitation`'s vector legend (Wave 3 §11). `color` reuses
 * `theme/colors.ts`'s `FIELD_FLOW_COLOR` — the exact hue `fieldFlow.ts`
 * renders the wind in — so the legend swatch never drifts from the map.
 */
const FIELD_FLOW_EXPLOITATION_LEGEND: LensLegend = {
  kind: "vector",
  color: [FIELD_FLOW_COLOR[0], FIELD_FLOW_COLOR[1], FIELD_FLOW_COLOR[2], FIELD_FLOW_LEGEND_ALPHA],
  description:
    "Width/opacity grade |Δexploitation|; arrow marks the value-transfer direction (source→target when the gradient is positive, reversed when negative).",
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
  {
    id: "throughput_position",
    group: "extraction",
    label: "Throughput Position",
    tooltip:
      "Circulation intensity — county's supply-chain throughput vs. the national baseline (Pi = τ_through / τ_national)",
    legend: { kind: "ramp", stops: DATA_RAMPS.wealth },
    toLens: () => ({ kind: "metric", metric: "throughput_position" }),
    availableWhen: hasMetric("throughput_position"),
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
  {
    // Audit Wave 4 straggler (task #76, reports/epochs-vision-gap-audit.md
    // "critical-nodes/centrality map lens" / "Topology legibility"). Placed
    // next to solidarity_index — both are network-topology-derived
    // (SOLIDARITY-edge density vs. org-network degree-centrality), distinct
    // from agitation's per-class ideological scalar.
    id: "centrality",
    group: "struggle",
    label: "Centrality",
    tooltip:
      "Structurally-critical territories — degree-centrality within the org-network topology (organizations/institutions linked by PRESENCE/HOUSES)",
    legend: { kind: "ramp", stops: DATA_RAMPS.population },
    toLens: () => ({ kind: "metric", metric: "centrality" }),
    availableWhen: hasMetric("centrality"),
  },
  {
    id: "agitation",
    group: "struggle",
    label: "Agitation",
    tooltip:
      "Accumulated political energy — routes to fascism or revolution depending on solidarity (legitimately 0 absent a crisis tick)",
    legend: { kind: "ramp", stops: DATA_RAMPS.consciousness },
    toLens: () => ({ kind: "metric", metric: "agitation" }),
    availableWhen: hasMetric("agitation"),
  },
  {
    // Wave 5 receptivity pair (Epistemic Horizon Phase 1 honest display).
    // Struggle group, not reproduction: M_r reads the mass-line
    // RELATIONSHIP — desperation (P(S|A), Survival) x class consciousness x
    // class factor over the SAME TENANCY-linked class state agitation and
    // solidarity already read — class-struggle intelligence, "you know what
    // the masses tell you". Reproduction is the metabolic/ecological group
    // (habitability); receptivity has no metabolic content. Placed adjacent
    // to agitation (its nearest input cousin), before the vector lens.
    id: "mass_receptivity",
    group: "struggle",
    label: "Mass Receptivity",
    tooltip:
      "The masses' willingness to be your eyes — M_r = desperation × consciousness × class factor (Epistemic Horizon; honest display, no masking)",
    legend: { kind: "ramp", stops: DATA_RAMPS.receptivity },
    toLens: () => ({ kind: "metric", metric: "mass_receptivity" }),
    availableWhen: hasMetric("mass_receptivity"),
  },
  {
    // Wave 5 receptivity pair, categorical half — same struggle-group
    // reasoning as mass_receptivity above (it IS mass_receptivity, cut at
    // the corpus's own thresholds). "Fish in water": Water = the masses
    // are your eyes; Mud = partial information; Desert = blind and exposed.
    id: "vision_state",
    group: "struggle",
    label: "Vision State",
    tooltip:
      "Fish-in-water partition — Water: the masses are your eyes; Mud: partial information; Desert: you are blind and exposed",
    legend: VISION_STATE_LEGEND,
    toLens: () => ({ kind: "vision_state" }),
    availableWhen: hasMetric("vision_state"),
  },
  {
    // Wave 3 §11's "gradient wind" — the first VECTOR lens kind. Struggle
    // (not Extraction) group: the System-19/20 contradiction-field stack
    // (exploitation/atomization) directly FEEDS StruggleSystem/Consciousness
    // downstream — the same class-struggle-intensity family heat/
    // solidarity_index/agitation already occupy — rather than Extraction,
    // which reads material-throughput rates (profit_rate/imperial_rent),
    // not contradiction-field dynamics. Sourced from GET /field_state/, not
    // the /map/ payload every other lens reads — so `availableWhen` can't
    // gate on `available_metrics` (that array never advertises field_state
    // fields); the honest-empty degradation lives at render time instead
    // (DeckGLMap's "— no data" legend suffix when the tick's edges are
    // empty), matching how political lenses degrade (registry never hides
    // them; NO_DATA fill + a legend suffix carries the signal).
    id: "field_flow_exploitation",
    group: "struggle",
    label: "Gradient Wind · Exploitation",
    tooltip:
      "Contradiction-field gradient wind — direction + magnitude of exploitation-field transfer between classes (System 19/20)",
    legend: FIELD_FLOW_EXPLOITATION_LEGEND,
    toLens: () => ({ kind: "field_flow", field: "exploitation" }),
    availableWhen: alwaysAvailable,
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
  {
    id: "territory_type",
    group: "political",
    label: "Territory Type",
    tooltip:
      "Settler-colonial territorial classification — Core/Periphery/Reservation/Penal Colony/Concentration Camp",
    legend: TERRITORY_TYPE_LEGEND,
    toLens: () => ({ kind: "territory_type" }),
    availableWhen: hasMetric("territory_type"),
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
