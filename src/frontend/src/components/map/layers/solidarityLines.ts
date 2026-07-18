/**
 * Solidarity-line map layer (Track 1 / Task 6) — draws SOLIDARITY edges as
 * literal lines on the geographic map.
 *
 * Data source: `GET /api/games/{id}/map/`'s `metadata.solidarity_edges`
 * (`SolidarityEdgeLine`, `types/game.ts`), built server-side by
 * `_build_solidarity_edge_lines` (`web/game/engine_bridge.py`) — already
 * fog-gated (BOTH endpoints must be in the viewer's organizing reach, or the
 * edge is omitted entirely — an edge's existence is itself political
 * information) and territory-anchored (TENANCY resolution). This module
 * never fetches; `DeckGLMap.tsx` reads `mapData.metadata.solidarity_edges`
 * (already present on the one-shot-per-tick `/map/` response it fetches for
 * every other lens) and hands the edges in directly.
 *
 * Territory -> map position resolves via `criticalPulse.ts`'s
 * `resolveEntityPosition` (reused, not duplicated) — an edge with a null or
 * unresolvable `source_territory`/`target_territory` is honestly dropped
 * (Constitution III.11: never a fabricated line). Both endpoints resolving
 * to the SAME territory (single-county scenarios, or two classes tenanted
 * in the same county) render as a small static ring mark instead of a line —
 * mirrors `fieldFlow.ts`'s same-territory swirl policy: a zero-length line
 * would render invisibly, and dropping the edge would silently hide real,
 * fog-cleared solidarity data.
 *
 * Unlike the gradient-wind vector lens (`fieldFlow.ts`), solidarity has no
 * direction — `source`/`target` are an unordered pair — so there is no
 * sign-correction step and no animated flow trail; only line WEIGHT (never
 * hue) carries `solidarity_strength`, via `LineLayer` (`@deck.gl/layers`).
 *
 * Absence must be honest (Track 1 / Task 6 brief): `solidarity_edges` empty
 * or missing is a legitimate state (the player has organized no visible
 * allies yet) — `buildSolidarityLineLayers` returns an empty list, never a
 * placeholder or zero-weight line.
 */

import { LineLayer, ScatterplotLayer } from "@deck.gl/layers";
import { SOLIDARITY_LINE_COLOR } from "@/theme/colors";
import type { SolidarityEdgeLine } from "@/types/game";
import { resolveEntityPosition, type TerritoryPositionSource } from "./criticalPulse";

// ---------------------------------------------------------------------------
// Pure data resolution
// ---------------------------------------------------------------------------

/** One resolved solidarity-line segment ready for layer construction. */
export interface SolidarityLineSegment {
  /** `${edge.source}-${edge.target}` (class ids — always present, unlike the territory ids). Unordered, unlike fieldFlow's directional `id`. */
  id: string;
  /** deck.gl `[lng, lat]` — the source class's territory position. */
  from: [number, number];
  /** deck.gl `[lng, lat]` — the target class's territory position. */
  to: [number, number];
  /** The edge's `solidarity_strength`, unchanged. */
  strength: number;
  /** True when both endpoints resolved to the same territory (single-county scenarios). */
  sameTerritory: boolean;
}

/**
 * Resolve `edges` into renderable line segments: both territory endpoints
 * resolved via `resolveEntityPosition`, same-territory pairs flagged for the
 * ring-mark policy, and the result sorted by `id` for a deterministic,
 * input-order-independent render. Honest drops (Constitution III.11): a null
 * or unresolvable territory endpoint contributes nothing, never a guessed
 * position.
 */
export function resolveSolidarityLines(
  edges: SolidarityEdgeLine[],
  territories: TerritoryPositionSource[],
): SolidarityLineSegment[] {
  const segments: SolidarityLineSegment[] = [];
  for (const edge of edges) {
    if (!edge.source_territory || !edge.target_territory) continue;
    const from = resolveEntityPosition(edge.source_territory, territories);
    const to = resolveEntityPosition(edge.target_territory, territories);
    if (!from || !to) continue;

    segments.push({
      id: `${edge.source}-${edge.target}`,
      from,
      to,
      strength: edge.solidarity_strength,
      sameTerritory: edge.source_territory === edge.target_territory,
    });
  }
  return segments.sort((a, b) => a.id.localeCompare(b.id));
}

// ---------------------------------------------------------------------------
// Weight grading (weight, never hue, carries solidarity_strength)
// ---------------------------------------------------------------------------

const LINE_WIDTH_MIN_PX = 2;
const LINE_WIDTH_PER_UNIT_PX = 10;
const LINE_WIDTH_MAX_PX = 14;

/** Line width in pixels — monotonic in `strength`, floor-clamped (never a hairline), capped. */
export function solidarityLineWidthPixels(strength: number): number {
  const clamped = Math.max(0, strength);
  return Math.min(LINE_WIDTH_MAX_PX, LINE_WIDTH_MIN_PX + clamped * LINE_WIDTH_PER_UNIT_PX);
}

const RING_RADIUS_BASE_M = 4000;
const RING_RADIUS_PER_UNIT_M = 8000;
/** Cap the on-screen ring so a low zoom / high-strength outlier never fills the viewport. */
export const SOLIDARITY_RING_RADIUS_MAX_PX = 40;

/** Same-territory ring-mark radius in metres — monotonic in `strength`, never zero-sized. */
export function solidarityRingRadiusMeters(strength: number): number {
  return RING_RADIUS_BASE_M + Math.max(0, strength) * RING_RADIUS_PER_UNIT_M;
}

// ---------------------------------------------------------------------------
// Layer construction
// ---------------------------------------------------------------------------

type SolidarityLineLayer =
  LineLayer<SolidarityLineSegment> | ScatterplotLayer<SolidarityLineSegment>;

/** Straight solidarity line between two territories — width-graded, fixed hue. */
function buildLinesLayer(segments: SolidarityLineSegment[]): LineLayer<SolidarityLineSegment> {
  return new LineLayer<SolidarityLineSegment>({
    id: "solidarity-lines",
    data: segments,
    getSourcePosition: (d) => d.from,
    getTargetPosition: (d) => d.to,
    getColor: SOLIDARITY_LINE_COLOR,
    getWidth: (d) => solidarityLineWidthPixels(d.strength),
    widthUnits: "pixels",
    widthMinPixels: LINE_WIDTH_MIN_PX,
    pickable: false,
  });
}

/** Stroked ring at the shared position — the same-territory policy's honest mark (never an invisible zero-length line). */
function buildRingsLayer(
  segments: SolidarityLineSegment[],
): ScatterplotLayer<SolidarityLineSegment> {
  return new ScatterplotLayer<SolidarityLineSegment>({
    id: "solidarity-lines-same-territory",
    data: segments,
    getPosition: (d) => d.from,
    getRadius: (d) => solidarityRingRadiusMeters(d.strength),
    getLineColor: SOLIDARITY_LINE_COLOR,
    lineWidthMinPixels: 2,
    radiusUnits: "meters",
    radiusMaxPixels: SOLIDARITY_RING_RADIUS_MAX_PX,
    stroked: true,
    filled: false,
    pickable: false,
  });
}

/**
 * Build the solidarity-line layers for one tick's resolved segments. Empty
 * in -> empty out (Constitution III.11 — no visible solidarity is honest, not
 * an error; also keeps `DeckGLMap`'s referential-stability contract cheap to
 * satisfy when the player has organized no visible allies). Cross-territory
 * segments get a straight width-graded line; same-territory segments get the
 * ring mark instead (never a zero-length line).
 */
export function buildSolidarityLineLayers(
  segments: SolidarityLineSegment[],
): SolidarityLineLayer[] {
  if (segments.length === 0) return [];

  const lineSegments = segments.filter((s) => !s.sameTerritory);
  const ringSegments = segments.filter((s) => s.sameTerritory);

  const layers: SolidarityLineLayer[] = [];
  if (lineSegments.length > 0) {
    layers.push(buildLinesLayer(lineSegments));
  }
  if (ringSegments.length > 0) {
    layers.push(buildRingsLayer(ringSegments));
  }
  return layers;
}
