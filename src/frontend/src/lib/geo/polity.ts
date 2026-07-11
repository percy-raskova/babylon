/**
 * Client-side polity dissolve — de facto political claims over the immutable county mesh
 * (Lane Carto, spec-113 §7; DESIGN_BIBLE.md §2.1 layer 2, §2.2 "geometry never animates,
 * claims do"). A polity's fill and border are computed by merging its member counties'
 * shared arcs, never by shipping separate geometry — so a border "redraw" is always a
 * cheap re-dissolve of the same immutable substrate, not new data.
 */

import type { MultiLineString, MultiPolygon } from "geojson";
import { merge, mesh } from "topojson-client";
import type {
  GeometryCollection as TopoGeometryCollection,
  GeometryObject as TopoGeometryObject,
  MultiPolygon as TopoMultiPolygon,
  Polygon as TopoPolygon,
} from "topojson-specification";
import type { CountyProperties, CountyTopology } from "./topology";

/** County geometries are always Polygon or MultiPolygon in TIGER data — never lines/points. */
type CountyGeometry = TopoPolygon<CountyProperties> | TopoMultiPolygon<CountyProperties>;

function isCountyPolygon(g: TopoGeometryObject<CountyProperties>): g is CountyGeometry {
  return g.type === "Polygon" || g.type === "MultiPolygon";
}

/** Stable, order-independent cache key for a polity's county membership. */
function membershipKey(fipsList: string[]): string {
  return Array.from(new Set(fipsList)).sort().join(",");
}

function memberGeometries(topo: CountyTopology, fipsList: string[]): CountyGeometry[] {
  const members = new Set(fipsList);
  return topo.objects.counties.geometries.filter(
    (g): g is CountyGeometry => isCountyPolygon(g) && members.has(g.properties?.GEOID ?? ""),
  );
}

const polityFillCache = new Map<string, MultiPolygon>();
const polityOutlineCache = new Map<string, MultiLineString>();

/**
 * Merge a polity's member counties into one `MultiPolygon` (shared-arc dissolve — no
 * interior seams between adjacent members). Disconnected clusters of members produce
 * multiple polygon rings, which is correct: a polity can hold non-contiguous territory.
 *
 * Memoized by a stable hash of the sorted, de-duplicated FIPS list: repeat calls for the
 * same membership return the identical cached object reference (important for deck.gl's
 * `updateTriggers` — an unchanged reference means no GPU re-upload).
 */
export function mergePolity(topo: CountyTopology, fipsList: string[]): MultiPolygon {
  const key = membershipKey(fipsList);
  const cached = polityFillCache.get(key);
  if (cached) {
    return cached;
  }
  const merged = merge(topo, memberGeometries(topo, fipsList));
  polityFillCache.set(key, merged);
  return merged;
}

/**
 * Compute the polity's outer claim border via `topojson.mesh` with an exterior-only
 * filter (`a === b`, i.e. arcs used by exactly one member — the standard topojson-client
 * idiom for an outline, as opposed to `a !== b` for interior county seams). Interior
 * seams between member counties never appear in the result.
 *
 * Memoized identically to `mergePolity`.
 */
export function mergePolityOutline(topo: CountyTopology, fipsList: string[]): MultiLineString {
  const key = membershipKey(fipsList);
  const cached = polityOutlineCache.get(key);
  if (cached) {
    return cached;
  }
  const members = memberGeometries(topo, fipsList);
  const collection: TopoGeometryCollection<CountyProperties> = {
    type: "GeometryCollection",
    geometries: members,
  };
  const outline = mesh(topo, collection, (a, b) => a === b);
  polityOutlineCache.set(key, outline);
  return outline;
}

/** Test-only: reset the memoization caches between test cases. */
export function resetPolityCache(): void {
  polityFillCache.clear();
  polityOutlineCache.clear();
}
