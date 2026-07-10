/**
 * mapLensGeometry.ts — hull-polygon geometry resolution for sovereign
 * CLAIMS hulls (spec-093 US3). Pure function, no deck.gl dependency.
 *
 * Resolves H3 hex centroids (via `h3-js`) for a set of territory IDs and
 * computes their convex hull as a closed `[lng, lat]` ring, matching the
 * coordinate order deck.gl's `PolygonLayer`/GeoJSON consumers expect (the
 * same `[lng, lat]` order the backend's `get_map_snapshot` already uses
 * for `h3.cell_to_boundary`, `web/game/engine_bridge.py:253-255`).
 */

import { cellToLatLng } from "h3-js";

export interface HullGeometryTerritory {
  id: string;
  h3_index: string | null;
}

/** Minimum real-geometry points required for a meaningful hull. */
const MIN_HULL_POINTS = 3;

/**
 * True when the last two points of `chain` plus candidate `p` make a
 * non-left (clockwise or collinear) turn — the monotone-chain algorithm's
 * pop condition. Reads the last two entries via bounds-checked lookups
 * (never `!`) so it stays honest under `noUncheckedIndexedAccess`.
 */
function makesNonLeftTurn(chain: [number, number][], p: [number, number]): boolean {
  const o = chain[chain.length - 2];
  const a = chain[chain.length - 1];
  if (o === undefined || a === undefined) return false;
  return (a[0] - o[0]) * (p[1] - o[1]) - (a[1] - o[1]) * (p[0] - o[0]) <= 0;
}

/** Monotone-chain convex hull over `[lng, lat]` points (same algorithm shape as the mockup's `convexHull()`, ported to TS). */
function convexHull(points: [number, number][]): [number, number][] {
  if (points.length < MIN_HULL_POINTS) return points;
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  const lower: [number, number][] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && makesNonLeftTurn(lower, p)) {
      lower.pop();
    }
    lower.push(p);
  }
  const upper: [number, number][] = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    if (p === undefined) continue; // unreachable: i stays within [0, sorted.length)
    while (upper.length >= 2 && makesNonLeftTurn(upper, p)) {
      upper.pop();
    }
    upper.push(p);
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

/**
 * Resolve a closed `[lng, lat]` convex-hull ring over the H3-cell centroids
 * of the given territory IDs. Returns `null` when fewer than
 * `MIN_HULL_POINTS` territories resolve real geometry (no `h3_index`,
 * unknown ID) — the caller renders no hull rather than a degenerate shape.
 */
export function hullPolygonForTerritories(
  territoryIds: string[],
  territories: HullGeometryTerritory[],
): [number, number][] | null {
  const byId = new Map(territories.map((t) => [t.id, t]));
  const points: [number, number][] = [];
  for (const id of territoryIds) {
    const territory = byId.get(id);
    if (!territory?.h3_index) continue;
    const [lat, lng] = cellToLatLng(territory.h3_index);
    points.push([lng, lat]);
  }
  if (points.length < MIN_HULL_POINTS) return null;

  const hull = convexHull(points);
  const first = hull[0];
  if (hull.length < MIN_HULL_POINTS || first === undefined) return null;
  return [...hull, first]; // close the ring
}
