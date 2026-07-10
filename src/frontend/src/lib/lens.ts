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
export const MAP_METRICS = [
  "profit_rate",
  "exploitation_rate",
  "occ",
  "imperial_rent",
  "heat",
  "org_presence",
  "population",
  "habitability",
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

export type Lens = { kind: LensMode } | { kind: "metric"; metric: MapMetric };

/** Matches the old `mapStore` default (`lensMode: "stance"`). */
export const DEFAULT_LENS: Lens = { kind: "stance" };

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
};

/** Human-readable legend text for a lens (mode label or metric name). */
export function lensLegendLabel(lens: Lens): string {
  return lens.kind === "metric" ? METRIC_LABELS[lens.metric] : MODE_LEGEND_LABELS[lens.kind];
}

/**
 * The `MapLayer` a metric name reuses for its data ramp. `MapMetric` and
 * `MapLayer` overlap on every metric except `habitability` (a spec-109 A2
 * addition that predates `MapLayer` and has no ramp of its own — it reuses
 * the diverging biocapacity ramp, matching the old `habitabilityFill`).
 */
function metricToMapLayer(metric: MapMetric): MapLayer | null {
  return metric === "habitability" ? null : (metric as MapLayer);
}

/**
 * Resolve the canon ramp (hex stops) for a lens, or `null` for the three
 * balkanization-derived modes (stance/faction/collapse) whose fill is a
 * per-faction stance color, not a single continuous ramp.
 */
export function lensRampStops(lens: Lens): string[] | null {
  switch (lens.kind) {
    case "stance":
    case "faction":
    case "collapse":
      return null;
    case "habitability":
      return DATA_RAMPS.biocapacity;
    case "heat":
      return DATA_RAMPS.heat;
    case "metric": {
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
