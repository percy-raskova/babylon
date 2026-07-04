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

/** Monotone-chain convex hull over `[lng, lat]` points (same algorithm shape as the mockup's `convexHull()`, ported to TS). */
function convexHull(points: [number, number][]): [number, number][] {
  if (points.length < MIN_HULL_POINTS) return points;
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: [number, number], a: [number, number], b: [number, number]): number =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

  const lower: [number, number][] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2]!, lower[lower.length - 1]!, p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }
  const upper: [number, number][] = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i]!;
    while (upper.length >= 2 && cross(upper[upper.length - 2]!, upper[upper.length - 1]!, p) <= 0) {
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
  if (hull.length < MIN_HULL_POINTS) return null;
  return [...hull, hull[0]!]; // close the ring
}
