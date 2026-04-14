/**
 * Color scale functions for map visualization layers.
 *
 * Each scale maps a normalized [0, 1] value to an RGBA tuple
 * suitable for deck.gl layer color properties.
 */

import type { MapLayer } from "@/types/game";

export type RGBAColor = [number, number, number, number];

/** Linearly interpolate between two colors. */
function lerp(a: RGBAColor, b: RGBAColor, t: number): RGBAColor {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
    Math.round(a[3] + (b[3] - a[3]) * t),
  ];
}

/** Heat scale: dark purple → crimson → gold. */
function heatScale(v: number): RGBAColor {
  if (v < 0.5) {
    return lerp([30, 10, 50, 200], [200, 40, 40, 220], v * 2);
  }
  return lerp([200, 40, 40, 220], [200, 168, 96, 240], (v - 0.5) * 2);
}

/** Consciousness scale: dark → royal blue → phosphor. */
function consciousnessScale(v: number): RGBAColor {
  if (v < 0.5) {
    return lerp([20, 20, 50, 180], [70, 130, 220, 220], v * 2);
  }
  return lerp([70, 130, 220, 220], [140, 200, 255, 240], (v - 0.5) * 2);
}

/** Wealth scale: dark → data-green → gold. */
function wealthScale(v: number): RGBAColor {
  if (v < 0.5) {
    return lerp([20, 30, 20, 180], [60, 180, 60, 220], v * 2);
  }
  return lerp([60, 180, 60, 220], [200, 168, 96, 240], (v - 0.5) * 2);
}

/** Rent scale: dark → purple → crimson. */
function rentScale(v: number): RGBAColor {
  if (v < 0.5) {
    return lerp([20, 10, 30, 180], [140, 60, 160, 220], v * 2);
  }
  return lerp([140, 60, 160, 220], [220, 60, 60, 240], (v - 0.5) * 2);
}

/** Biocapacity scale: crimson (low) → data-green (high). */
function biocapacityScale(v: number): RGBAColor {
  if (v < 0.5) {
    return lerp([180, 40, 30, 200], [180, 180, 60, 220], v * 2);
  }
  return lerp([180, 180, 60, 220], [40, 200, 80, 240], (v - 0.5) * 2);
}

/** Population scale: dark → grow-purple. */
function populationScale(v: number): RGBAColor {
  return lerp([20, 10, 40, 180], [160, 80, 220, 240], v);
}

/** Get color scale function for a given map layer. */
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
      return heatScale;
    case "org_presence":
      return consciousnessScale;
  }
}

/** Convert RGBA to CSS color string for use in non-deck.gl contexts. */
export function rgbaToCss(c: RGBAColor): string {
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] / 255).toFixed(2)})`;
}
