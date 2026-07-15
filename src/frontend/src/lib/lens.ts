/**
 * The unified map `Lens` — spec-110 B2's one redesign in this lane.
 *
 * Before this module, the map carried two independent, overlapping "lens"
 * axes: `mapStore.activeLayer: MapLayer` (the single-metric color ramp) and
 * `mapStore.lensMode: LensMode` (spec-070/093's political-topology lens —
 * stance/heat/habitability/faction/collapse). Both had their own notion of
 * "heat", set independently, with no relationship enforced between them.
 *
 * `Lens` collapses both into one value. The five spec-093 modes are
 * primary — they're the ratified political-topology lens set and the ones
 * with dedicated fill logic in `mapLensLayers.ts`. Everything else
 * `web/game/map_contract.py`'s `MAP_METRIC_PROPERTIES` advertises (the raw
 * `/map/` feature properties) lives under one `{ kind: "metric"; metric }`
 * sub-select — except `heat` and `habitability`, which are deliberately
 * excluded from `SELECTABLE_METRICS` because they already have a dedicated
 * kind. There is exactly one way to ask for either: `{ kind: "heat" }` /
 * `{ kind: "habitability" }`, never `{ kind: "metric", metric: "heat" }`.
 */

import { DATA_RAMPS, rampForLayer, type RGBAColor } from "@/theme/colors";
import type { MapLayer } from "@/types/game";

// ---------------------------------------------------------------------------
// MapMetric — mirrors web/game/map_contract.py's MAP_METRIC_PROPERTIES
// ---------------------------------------------------------------------------

/**
 * Every numeric property the backend's ``/map/`` endpoint actually emits on
 * hex/county features (`_hex_feature_properties`, `metadata.available_metrics`).
 * Order matches ``MAP_METRIC_PROPERTIES`` exactly — kept as a single source
 * of truth on the frontend side, the same way ``map_contract.py`` is on the
 * backend side.
 */
/**
 * Spec-113 Lane D added two more `MAP_METRIC_PROPERTIES` entries to the
 * backend contract (`web/game/map_contract.py`): `dominant_class` (a
 * categorical `SocialRole` string) and `solidarity_index` (numeric,
 * SOLIDARITY-edge density). `solidarity_index` joins this numeric list —
 * `dominant_class` deliberately does NOT (this array is numeric-ramp
 * metrics only): it drives the dedicated categorical `class_composition`
 * `Lens` kind instead, the same way `heat`/`habitability` get dedicated
 * kinds rather than a `{kind:"metric"}` sub-select.
 *
 * Wave 2 Round 2 (`reports/wave2-implementation-map.md`) adds two more:
 * `throughput_position` (Pi = τ_through / τ_national, ruling 1 — wired for
 * real this round, no longer the frozen `1.0` constant) and `agitation`
 * (`SocialClass.ideology.agitation` aggregated per territory —
 * DECLARED_CONDITIONAL: legitimately `0.0` absent a falling-wage/rent/Φ/g₃₃
 * crisis tick, never fabricated warmth). A third contract addition this
 * round, `territory_type` (the real `TerritoryType` enum —
 * `src/babylon/models/enums/territory.py` — NOT `stub_bridge.py`'s legacy
 * `"URBAN"/"SUBURBAN"/"PERIURBAN"` vocabulary), is categorical like
 * `dominant_class` and likewise excluded here; it drives the dedicated
 * `territory_type` `Lens` kind instead.
 */
export const MAP_METRICS = [
  "profit_rate",
  "exploitation_rate",
  "occ",
  "imperial_rent",
  "heat",
  "org_presence",
  "population",
  "habitability",
  "solidarity_index",
  "throughput_position",
  "agitation",
] as const;

export type MapMetric = (typeof MAP_METRICS)[number];

/**
 * `MAP_METRICS` minus the two that already have a dedicated `Lens` kind
 * (`heat`, `habitability`). This is the metric list a "metric" picker UI
 * should offer — selecting either of the excluded two through the
 * `{kind:"metric"}` sub-select would be a second, redundant way to express
 * a lens that `{kind:"heat"}`/`{kind:"habitability"}` already covers.
 */
export const SELECTABLE_METRICS: readonly MapMetric[] = MAP_METRICS.filter(
  (m): m is Exclude<MapMetric, "heat" | "habitability"> => m !== "heat" && m !== "habitability",
);

// ---------------------------------------------------------------------------
// LensMode — the 5 spec-093 political-topology kinds
// ---------------------------------------------------------------------------

export const LENS_MODES = ["stance", "heat", "habitability", "faction", "collapse"] as const;

export type LensMode = (typeof LENS_MODES)[number];

// ---------------------------------------------------------------------------
// Lens — the discriminated union
// ---------------------------------------------------------------------------

/**
 * `class_composition` (spec-113 Lane B, bible §9's `dominant_class`
 * addition): the population-weighted-majority `SocialRole` per
 * hex/territory. Categorical like stance/faction/collapse, but NOT
 * balkanization-derived (it reads `hex_latest`'s own `dominant_class`
 * column via TENANCY membership, not the spec-070 factions/sovereigns
 * block) — so it gets its own top-level kind rather than joining
 * `LensMode`, whose `RING_AND_HULL_KINDS`/`BALKANIZATION_LENSES` sets in
 * `mapLensLayers.ts` are keyed to the balkanization block specifically.
 *
 * `territory_type` (Wave 2 Round 2): the real `TerritoryType` enum
 * (settler-colonial hierarchy — core/periphery/reservation/penal_colony/
 * concentration_camp) per territory, population-weighted-mode at
 * region/county framing (ruling 4). Categorical for the same reason
 * `class_composition` is — it gets its own top-level kind (not a
 * `{kind:"metric"}` sub-select, which is numeric-only) and is territory-
 * local, never balkanization-derived.
 */
export type Lens =
  | { kind: LensMode }
  | { kind: "metric"; metric: MapMetric }
  | { kind: "class_composition" }
  | { kind: "territory_type" };

/**
 * DESIGN_BIBLE.md §9 amendment 1 (binding): the default lens is Imperial
 * Rent Φ, not the political-topology "stance" lens — a GDP-style/political
 * default would reproduce the "backwardness" ideology the game refutes
 * (Amin). Political claims remain the layer-2 substrate under every lens
 * (`layers/political.ts`), so switching away from "stance" loses nothing —
 * the claims/borders are always drawn, independent of the active lens.
 */
export const DEFAULT_LENS: Lens = { kind: "metric", metric: "imperial_rent" };

/** Structural equality — two lenses are the same lens. */
export function isSameLens(a: Lens, b: Lens): boolean {
  if (a.kind !== b.kind) return false;
  if (a.kind === "metric" && b.kind === "metric") return a.metric === b.metric;
  return true;
}

/**
 * Lens modes whose fill is derived from spec-070's balkanization block
 * (factions/sovereigns/territory_influence) — degrades to a "no data"
 * legend when that block is absent/empty (see `mapLensLayers.ts`).
 * Territory-local modes (heat/habitability) and all metric lenses render
 * from data that's always present on a `TerritoryState`/feature, so they
 * are never balkanization lenses.
 */
export function isBalkanizationLens(lens: Lens): boolean {
  return lens.kind === "stance" || lens.kind === "faction" || lens.kind === "collapse";
}

/** Stable identity string — safe for React `key` props and deck.gl `updateTriggers` arrays. */
export function lensKey(lens: Lens): string {
  return lens.kind === "metric" ? `metric:${lens.metric}` : lens.kind;
}

const MODE_LEGEND_LABELS: Record<LensMode, string> = {
  stance: "Colonial Stance · Influence",
  heat: "Heat · State Attention",
  habitability: "Habitability · Metabolic Rift",
  faction: "Faction Filter · Influence",
  collapse: "Collapse Moment · Territory Transitions",
};

const METRIC_LABELS: Record<MapMetric, string> = {
  profit_rate: "Profit Rate",
  exploitation_rate: "Exploitation Rate",
  occ: "Organic Composition of Capital",
  imperial_rent: "Imperial Rent",
  heat: "Heat · State Attention",
  org_presence: "Organizational Presence",
  population: "Population",
  habitability: "Habitability · Metabolic Rift",
  solidarity_index: "Solidarity · SOLIDARITY-Edge Density",
  throughput_position: "Throughput Position · Circulation Intensity",
  agitation: "Agitation · Political Energy",
};

/** Human-readable legend text for a lens (mode label or metric name). */
export function lensLegendLabel(lens: Lens): string {
  if (lens.kind === "metric") return METRIC_LABELS[lens.metric];
  if (lens.kind === "class_composition") return "Class Composition · Dominant Social Role";
  if (lens.kind === "territory_type") return "Territory Type · Settler-Colonial Hierarchy";
  return MODE_LEGEND_LABELS[lens.kind];
}

/**
 * The `MapLayer` a metric name reuses for its data ramp. `MapMetric` and
 * `MapLayer` overlap on every metric except `habitability`/`solidarity_index`
 * (spec-109 A2 / spec-113 Lane B additions) and, as of Wave 2 Round 2,
 * `throughput_position`/`agitation` — all four predate/sit outside
 * `MapLayer` and have no ramp of their own there — each resolves its real
 * ramp directly in `lensRampStops` instead of through `rampForLayer`.
 */
function metricToMapLayer(metric: MapMetric): MapLayer | null {
  return metric === "habitability" ||
    metric === "solidarity_index" ||
    metric === "throughput_position" ||
    metric === "agitation"
    ? null
    : (metric as MapLayer);
}

/**
 * Resolve the canon ramp (hex stops) for a lens, or `null` for the
 * categorical kinds (stance/faction/collapse/class_composition/
 * territory_type) whose fill is a discrete per-entity color, not a single
 * continuous ramp.
 */
export function lensRampStops(lens: Lens): string[] | null {
  switch (lens.kind) {
    case "stance":
    case "faction":
    case "collapse":
    case "class_composition":
    case "territory_type":
      return null;
    case "habitability":
      return DATA_RAMPS.biocapacity;
    case "heat":
      return DATA_RAMPS.heat;
    case "metric": {
      if (lens.metric === "solidarity_index") return DATA_RAMPS.solidarity;
      // Wave 2 Round 2: throughput_position picks the wealth ramp (an
      // economic-circulation metric, distinct from rent's extraction/
      // violence terminal already claimed by imperial_rent/
      // exploitation_rate) and agitation picks the consciousness ramp
      // (raw political energy — the same "awakening" ramp org_presence
      // uses — distinct from heat's alarm terminal and solidarity's green,
      // its nearest struggle-group cousins). Both are of the 3 canonical
      // ramps (consciousness/wealth/population) not yet bound to any
      // REGISTERED lens before this round; population is left unclaimed.
      if (lens.metric === "throughput_position") return DATA_RAMPS.wealth;
      if (lens.metric === "agitation") return DATA_RAMPS.consciousness;
      const layer = metricToMapLayer(lens.metric);
      return layer === null ? DATA_RAMPS.biocapacity : rampForLayer(layer);
    }
  }
}

/** Sample a hex-stop ramp at normalized t in [0,1] into an RGBA tuple. */
export function sampleRampStops(stops: string[], t: number, alpha = 220): RGBAColor {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
  const hexToRgb = (hex: string): [number, number, number] => {
    const h = hex.replace(/^#/, "");
    const num = parseInt(h, 16);
    return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
  };
  const rgb = stops.map(hexToRgb);
  const first = rgb[0] ?? [0, 0, 0];
  if (rgb.length === 1) return [first[0], first[1], first[2], alpha];
  const seg = clamped * (rgb.length - 1);
  const i = Math.min(Math.floor(seg), rgb.length - 2);
  const f = seg - i;
  const a = rgb[i] ?? [0, 0, 0];
  const b = rgb[i + 1] ?? [0, 0, 0];
  return [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
    alpha,
  ];
}
