/**
 * Cold Collapse data ramps + map-layer colour scales (spec-090).
 *
 * The six luminance-monotonic ramps are the ratified canon
 * (``design/mockups/preview/colors-data.html``): a single hue family per
 * ramp, lightness encodes magnitude — no ``dark-purple → crimson → gold``
 * rainbows. Semantic alarm terminals (heat → laser, rent → thermal) and the
 * diverging biocapacity ramp are intentional; see
 * ``specs/090-cold-collapse/research.md`` R3.
 *
 * Each scale maps a normalized [0, 1] value to an RGBA tuple suitable for
 * deck.gl layer colour properties.
 */

import type { MapLayer } from "@/types/game";

export type RGBAColor = [number, number, number, number];

/** Map layers that own a canonical data ramp. */
export type RampLayer =
  "heat" | "consciousness" | "rent" | "biocapacity" | "wealth" | "population" | "solidarity";

/**
 * The six canonical data ramps.
 *
 * Luminance-monotonic (lightness encodes magnitude) **except** the two named
 * alarm terminals — heat → laser (``#ff3344``) and rent → thermal
 * (``#b8321f``) — which sacrifice strict top-end luminance monotonicity for
 * danger signalling, and the diverging ``biocapacity`` ramp (collapse-red ↔
 * regenerate-green). Per the Article VII amendment these are intentional,
 * bounded exceptions, not rainbows.
 *
 * Source of truth: ``design/mockups/preview/colors-data.html``. Stop lists are
 * byte-identical to the canon swatches (pinned by the token-contract test).
 */
export const DATA_RAMPS: Record<RampLayer, string[]> = {
  // Surveillance pressure — ember body, laser alarm terminal.
  heat: ["#0d1016", "#3a3530", "#7a4720", "#b8581f", "#d97a2c", "#ff3344"],
  // Awakening — ends in spire glow.
  consciousness: ["#0d1016", "#1f2c3d", "#345670", "#4a86a0", "#6bbcc8", "#4dd9e6"],
  // Extraction → violence.
  rent: ["#0d1016", "#2e2236", "#56356b", "#8b4d9e", "#a83a78", "#b8321f"],
  // Diverging — depleted (collapse-red) ↔ healthy (regenerate-green).
  biocapacity: ["#b8321f", "#7a3525", "#3d4250", "#3a6b48", "#5fbf7a"],
  // Ends at scarcity-gold.
  wealth: ["#0d1016", "#2a251f", "#4d3f28", "#8a6a2a", "#d4a02c"],
  // Single hue, lightness only.
  population: ["#0d1016", "#23223a", "#3d3868", "#5a4f95", "#7a6db8", "#a89dd0"],
  // Spec-113 Lane B addition (bible §3.2's Struggle-group Solidarity lens):
  // single hue, ends at the canon --babylon-solidarity green (#5fbf7a) — the
  // same terminal `mapLensLayers.ts`'s STANCE_COLOR.ABOLISH already uses, so
  // "high solidarity" reads consistently with the stance lens's ABOLISH tone.
  solidarity: ["#0d1016", "#132a1c", "#1e4a2a", "#2f7a3f", "#48a85c", "#5fbf7a"],
};

/** Fill alpha for deck.gl hex layers (near-opaque, as pre-090). */
const RAMP_ALPHA = 220;

/** Parse a ``#rrggbb`` hex string into an RGB triple. */
function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace(/^#/, "");
  const num = parseInt(h, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

/** Linearly interpolate between two RGB triples. */
function lerpRgb(
  a: [number, number, number],
  b: [number, number, number],
  t: number,
): [number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

/**
 * Build a scale function that interpolates a normalized value over a ramp's
 * hex stops and returns an RGBA tuple.
 */
function rampScale(stops: string[], alpha: number = RAMP_ALPHA): (v: number) => RGBAColor {
  const rgb = stops.map(hexToRgb);
  return (v: number): RGBAColor => {
    const t = Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));
    if (rgb.length === 1) {
      const only = rgb[0] ?? [94, 100, 112];
      return [only[0], only[1], only[2], alpha];
    }
    const seg = t * (rgb.length - 1);
    const i = Math.min(Math.floor(seg), rgb.length - 2);
    const f = seg - i;
    const [r, g, b] = lerpRgb(rgb[i] ?? [0, 0, 0], rgb[i + 1] ?? [0, 0, 0], f);
    return [r, g, b, alpha];
  };
}

// Pre-built scales (one per ramp; aliases reuse the semantically-nearest ramp).
const heatScale = rampScale(DATA_RAMPS.heat);
const consciousnessScale = rampScale(DATA_RAMPS.consciousness);
const rentScale = rampScale(DATA_RAMPS.rent);
const biocapacityScale = rampScale(DATA_RAMPS.biocapacity);
const wealthScale = rampScale(DATA_RAMPS.wealth);
const populationScale = rampScale(DATA_RAMPS.population);

/** Get the colour-scale function for a given map layer. */
export function getColorScale(layer: MapLayer): (v: number) => RGBAColor {
  switch (layer) {
    case "heat":
      return heatScale;
    case "consciousness":
      return consciousnessScale;
    case "wealth":
      return wealthScale;
    case "rent":
      return rentScale;
    case "biocapacity":
      return biocapacityScale;
    case "population":
      return populationScale;
    case "profit_rate":
      return wealthScale;
    case "exploitation_rate":
      return rentScale;
    case "occ":
      return wealthScale;
    case "imperial_rent":
      return rentScale; // extraction → the rent ramp
    case "org_presence":
      return consciousnessScale; // presence → the spire (agency) ramp
  }
}

/**
 * Resolve the canonical ramp (hex stop list) for any map layer, including the
 * derived aliases. Single source of truth shared by the map fill
 * (``getColorScale``) and the lens legend (``lensDefinitions``).
 */
export function rampForLayer(layer: MapLayer): string[] {
  switch (layer) {
    case "heat":
      return DATA_RAMPS.heat;
    case "consciousness":
    case "org_presence":
      return DATA_RAMPS.consciousness;
    case "rent":
    case "exploitation_rate":
    case "imperial_rent":
      return DATA_RAMPS.rent;
    case "biocapacity":
      return DATA_RAMPS.biocapacity;
    case "wealth":
    case "profit_rate":
    case "occ":
      return DATA_RAMPS.wealth;
    case "population":
      return DATA_RAMPS.population;
  }
}

/**
 * Gradient-wind vector lens (DESIGN_BIBLE.md §11, "the weather grammar" —
 * law 1: extensive/flow visuals render as geometry, hue stays FIXED and
 * subordinate, never a ramp). `DATA_RAMPS.rent`'s terminal stop (`#b8321f`)
 * as a plain RGB triple — ties the wind's one fixed hue to the same
 * extraction/violence family `imperial_rent`/`exploitation_rate` already
 * render in, rather than inventing a new hex literal. Single source of
 * truth shared by `components/map/layers/fieldFlow.ts` (the actual layer
 * fill) and `lib/lenses/registry.ts` (the legend swatch) — never a second
 * duplicated triple.
 */
export const FIELD_FLOW_COLOR: readonly [number, number, number] = [184, 50, 31];

/** Convert RGBA to a CSS colour string for use in non-deck.gl contexts. */
export function rgbaToCss(c: RGBAColor): string {
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] / 255).toFixed(2)})`;
}
