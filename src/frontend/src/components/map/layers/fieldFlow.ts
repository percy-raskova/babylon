/**
 * Gradient-wind vector lens — DESIGN_BIBLE.md §11 ("the weather grammar",
 * Wave 3, binding): "the vector lens (gradient wind) is law 1's first
 * extensive citizen." Law 1: direction + magnitude render as GEOMETRY
 * (width/opacity/length), hue stays fixed and subordinate — never a color
 * ramp. Law 2 permits continuous animation for field evolution / value
 * flows (this lens qualifies), but `prefers-reduced-motion` must degrade to
 * fully static directional marks — no exceptions.
 *
 * Data source: `GET /api/games/{id}/field_state/`'s `edges[]`
 * (`FieldStateEdge`, `types/game.ts`) — one row per class<->class
 * contradiction-field gradient, `gradient = f(target) - f(source)` (positive
 * = value transfer flows source->target on that field). This module never
 * fetches; `DeckGLMap.tsx` owns the one-shot-per-tick fetch and hands the
 * already-field-filtered edges in (`edgesForField`).
 *
 * Territory -> map position resolves via `criticalPulse.ts`'s
 * `resolveEntityPosition` (reused, not duplicated) — an edge with a null or
 * unresolvable `source_territory`/`target_territory` is honestly dropped
 * (Constitution III.11: never a fabricated arrow). Both endpoints resolving
 * to the SAME territory (single-county scenarios) render as a small static
 * swirl mark instead of a path — a zero-length line would either error or
 * overlap-render invisibly, and dropping the edge would silently hide a real
 * gradient.
 *
 * Layer choice: `TripsLayer` (extends `PathLayer`, `@deck.gl/geo-layers`) is
 * deck.gl's own animated-flow-trail primitive — a `currentTime` prop sweeps
 * a fading trail from `flowFrom` to `flowTo` on the GPU (a lightweight
 * uniform update per frame, unlike re-generating `PathStyleExtension`'s
 * static `getDashArray` every frame to fake a "marching ants" offset).
 * Always paired with a static dashed `PathLayer` (`PathStyleExtension`) plus
 * a filled arrowhead dot at `flowTo` — together these ARE the "static
 * directional marks (arrows/dashes)" the reduced-motion contract requires;
 * under full motion the `TripsLayer` trail rides ON TOP of that same static
 * base, so direction never depends on the animation being visible.
 */

import { useEffect, useRef, useState } from "react";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import { TripsLayer } from "@deck.gl/geo-layers";
import { PathStyleExtension, type PathStyleExtensionProps } from "@deck.gl/extensions";
import { FIELD_FLOW_COLOR, type RGBAColor } from "@/theme/colors";
import type { FieldStateEdge } from "@/types/game";
import { resolveEntityPosition, type TerritoryPositionSource } from "./criticalPulse";

// ---------------------------------------------------------------------------
// Pure data resolution
// ---------------------------------------------------------------------------

/** One resolved, direction-corrected gradient-wind segment ready for layer construction. */
export interface FlowSegment {
  /** `${edge.source}->${edge.target}` (class ids — always present, unlike the territory ids). */
  id: string;
  /** deck.gl `[lng, lat]` — the value-transfer ORIGIN (already sign-corrected, see below). */
  flowFrom: [number, number];
  /** deck.gl `[lng, lat]` — the value-transfer DESTINATION. */
  flowTo: [number, number];
  /** The edge's own signed gradient, unchanged. */
  gradient: number;
  /** `Math.abs(gradient)` — magnitude grading never cares about sign. */
  magnitude: number;
  /** True when both endpoints resolved to the same territory (single-county scenarios). */
  sameTerritory: boolean;
}

/** Keep only the edges for one contradiction field — `field_state` mixes every field in one array. */
export function edgesForField(edges: FieldStateEdge[], field: string): FieldStateEdge[] {
  return edges.filter((e) => e.field === field);
}

/**
 * Resolve `edges` (already filtered to one field — see `edgesForField`) into
 * renderable flow segments: both territory endpoints resolved via
 * `resolveEntityPosition`, direction corrected so `flowFrom -> flowTo`
 * always reads as the ACTUAL value-transfer direction (`gradient >= 0` means
 * source->target per `FieldStateEdge`'s contract; a negative gradient
 * reverses it rather than rendering a technically-wrong-facing arrow),
 * same-territory pairs flagged for the swirl-mark policy, and the result
 * sorted by `id` for a deterministic, input-order-independent render.
 * Honest drops (Constitution III.11): a null or unresolvable territory
 * endpoint contributes nothing, never a guessed position.
 */
export function resolveFlowSegments(
  edges: FieldStateEdge[],
  territories: TerritoryPositionSource[],
): FlowSegment[] {
  const segments: FlowSegment[] = [];
  for (const edge of edges) {
    if (!edge.source_territory || !edge.target_territory) continue;
    const sourcePosition = resolveEntityPosition(edge.source_territory, territories);
    const targetPosition = resolveEntityPosition(edge.target_territory, territories);
    if (!sourcePosition || !targetPosition) continue;

    const forward = edge.gradient >= 0;
    segments.push({
      id: `${edge.source}->${edge.target}`,
      flowFrom: forward ? sourcePosition : targetPosition,
      flowTo: forward ? targetPosition : sourcePosition,
      gradient: edge.gradient,
      magnitude: Math.abs(edge.gradient),
      sameTerritory: edge.source_territory === edge.target_territory,
    });
  }
  return segments.sort((a, b) => a.id.localeCompare(b.id));
}

// ---------------------------------------------------------------------------
// Magnitude grading (weather-grammar law 1 — geometry, never hue)
// ---------------------------------------------------------------------------

const FLOW_WIDTH_MIN_PX = 4;
const FLOW_WIDTH_PER_UNIT_PX = 60;
const FLOW_WIDTH_MAX_PX = 26;

/** Path/trail width in pixels — monotonic in `magnitude`, floor-clamped (never a hairline), capped. */
export function flowWidthPixels(magnitude: number): number {
  const clamped = Math.max(0, magnitude);
  return Math.min(FLOW_WIDTH_MAX_PX, FLOW_WIDTH_MIN_PX + clamped * FLOW_WIDTH_PER_UNIT_PX);
}

const FLOW_OPACITY_FLOOR = 140;
const FLOW_OPACITY_CEIL = 255;
/** Magnitude at which opacity saturates — real gradients are ~[0,1]-scaled field differences. */
const FLOW_OPACITY_SATURATION_MAGNITUDE = 1;

/** Alpha channel [0,255] — monotonic in `magnitude`, floor-clamped so the faintest flow is still legible. */
export function flowOpacity(magnitude: number): number {
  const t = Math.max(0, Math.min(1, magnitude / FLOW_OPACITY_SATURATION_MAGNITUDE));
  return Math.round(FLOW_OPACITY_FLOOR + (FLOW_OPACITY_CEIL - FLOW_OPACITY_FLOOR) * t);
}

const SWIRL_RADIUS_BASE_M = 5000;
const SWIRL_RADIUS_PER_UNIT_M = 15000;
/** Cap the on-screen swirl so a low zoom / high-magnitude outlier never fills the viewport. */
export const SWIRL_RADIUS_MAX_PX = 60;

/** Swirl-mark radius in metres — monotonic in `magnitude`, never zero-sized. */
export function swirlRadiusMeters(magnitude: number): number {
  return SWIRL_RADIUS_BASE_M + Math.max(0, magnitude) * SWIRL_RADIUS_PER_UNIT_M;
}

/** The wind's one fixed hue (`theme/colors.ts`'s `FIELD_FLOW_COLOR`) at a magnitude-graded alpha. */
function flowColor(magnitude: number): RGBAColor {
  return [FIELD_FLOW_COLOR[0], FIELD_FLOW_COLOR[1], FIELD_FLOW_COLOR[2], flowOpacity(magnitude)];
}

// ---------------------------------------------------------------------------
// Layer construction
// ---------------------------------------------------------------------------

const FLOW_DASH_ARRAY: [number, number] = [3, 2];
const ARROWHEAD_RADIUS_SCALE = 1.6;

/** Static, always-on dashed base path — direction-agnostic on its own, but never absent (the honest fallback under reduced motion). */
function buildStaticFlowLayer(segments: FlowSegment[]): PathLayer<FlowSegment> {
  return new PathLayer<FlowSegment, PathStyleExtensionProps>({
    id: "field-flow-static",
    data: segments,
    getPath: (d) => [d.flowFrom, d.flowTo],
    getColor: (d) => flowColor(d.magnitude),
    getWidth: (d) => flowWidthPixels(d.magnitude),
    widthUnits: "pixels",
    widthMinPixels: FLOW_WIDTH_MIN_PX,
    getDashArray: FLOW_DASH_ARRAY,
    dashJustified: true,
    extensions: [new PathStyleExtension({ dash: true })],
    capRounded: true,
    pickable: false,
  });
}

/** Filled dot at `flowTo` — marks the value-transfer DESTINATION, the direction cue dashes alone can't carry. */
function buildArrowheadLayer(segments: FlowSegment[]): ScatterplotLayer<FlowSegment> {
  return new ScatterplotLayer<FlowSegment>({
    id: "field-flow-arrowheads",
    data: segments,
    getPosition: (d) => d.flowTo,
    getRadius: (d) => flowWidthPixels(d.magnitude) * ARROWHEAD_RADIUS_SCALE,
    getFillColor: (d) => flowColor(d.magnitude),
    radiusUnits: "pixels",
    radiusMinPixels: FLOW_WIDTH_MIN_PX,
    filled: true,
    stroked: false,
    pickable: false,
  });
}

/** Stroked ring at the shared position — the same-territory policy's honest mark (never an invisible zero-length path). */
function buildSwirlLayer(segments: FlowSegment[]): ScatterplotLayer<FlowSegment> {
  return new ScatterplotLayer<FlowSegment>({
    id: "field-flow-swirl",
    data: segments,
    getPosition: (d) => d.flowFrom,
    getRadius: (d) => swirlRadiusMeters(d.magnitude),
    getLineColor: (d) => flowColor(d.magnitude),
    lineWidthMinPixels: 2,
    radiusUnits: "meters",
    radiusMaxPixels: SWIRL_RADIUS_MAX_PX,
    stroked: true,
    filled: false,
    pickable: false,
  });
}

/** One full source->target sweep, ms — `tripCurrentTime`'s loop period. */
export const FLOW_LOOP_DURATION_MS = 3000;
/** Arbitrary path-timestamp unit `getTimestamps`/`currentTime` share (not real ms — TripsLayer's own units). */
const TRIP_TIMESTAMP_END = 100;
const TRIP_TRAIL_LENGTH = 40;

/**
 * Pure loop-phase math for the animated trail: maps an elapsed-ms clock
 * value onto `[0, TRIP_TIMESTAMP_END)`, wrapping every `FLOW_LOOP_DURATION_MS`
 * so the wind sweeps source->target on a continuous, seamless loop.
 */
export function tripCurrentTime(clockMs: number): number {
  const phase = ((clockMs % FLOW_LOOP_DURATION_MS) + FLOW_LOOP_DURATION_MS) % FLOW_LOOP_DURATION_MS;
  return (phase / FLOW_LOOP_DURATION_MS) * TRIP_TIMESTAMP_END;
}

/** Animated flowing trail, motion-allowed only — deck.gl's own currentTime uniform, not a per-frame prop rebuild. */
function buildTripsLayer(segments: FlowSegment[], clockMs: number): TripsLayer<FlowSegment> {
  return new TripsLayer<FlowSegment>({
    id: "field-flow-trips",
    data: segments,
    getPath: (d) => [d.flowFrom, d.flowTo],
    getTimestamps: () => [0, TRIP_TIMESTAMP_END],
    getColor: (d) => flowColor(d.magnitude),
    getWidth: (d) => flowWidthPixels(d.magnitude),
    widthUnits: "pixels",
    widthMinPixels: FLOW_WIDTH_MIN_PX,
    trailLength: TRIP_TRAIL_LENGTH,
    fadeTrail: true,
    currentTime: tripCurrentTime(clockMs),
    capRounded: true,
    pickable: false,
  });
}

export interface FieldFlowLayerOptions {
  /** True to render ONLY static directional marks (arrows/dashes) — no TripsLayer, no motion. */
  reducedMotion: boolean;
  /** Elapsed-ms animation clock (`useFlowAnimationClock`) — ignored under reduced motion. */
  time: number;
}

type FieldFlowLayer =
  PathLayer<FlowSegment> | ScatterplotLayer<FlowSegment> | TripsLayer<FlowSegment>;

/**
 * Build the gradient-wind's deck.gl layers for one field's resolved
 * segments. Empty in -> empty out (Constitution III.11 — no data means no
 * layers, never a fabricated arrow; also keeps `DeckGLMap`'s referential-
 * stability contract cheap to satisfy when the lens is inactive). Path
 * segments get the static dashed base + arrowhead always, plus the animated
 * trail only when motion is allowed; same-territory segments get the swirl
 * mark instead (never a path — see the module docstring).
 */
export function buildFieldFlowLayers(
  segments: FlowSegment[],
  options: FieldFlowLayerOptions,
): FieldFlowLayer[] {
  if (segments.length === 0) return [];

  const pathSegments = segments.filter((s) => !s.sameTerritory);
  const swirlSegments = segments.filter((s) => s.sameTerritory);

  const layers: FieldFlowLayer[] = [];
  if (pathSegments.length > 0) {
    layers.push(buildStaticFlowLayer(pathSegments));
    layers.push(buildArrowheadLayer(pathSegments));
    if (!options.reducedMotion) {
      layers.push(buildTripsLayer(pathSegments, options.time));
    }
  }
  if (swirlSegments.length > 0) {
    layers.push(buildSwirlLayer(swirlSegments));
  }
  return layers;
}

// ---------------------------------------------------------------------------
// Animation clock (rAF-driven, pauses off-screen, only runs while active)
// ---------------------------------------------------------------------------

/**
 * Own the gradient-wind's rAF-driven animation clock — returns elapsed ms
 * since the clock last (re)started. The caller passes `paused` (typically
 * `!active || reducedMotion`): while paused, NO `requestAnimationFrame` is
 * ever scheduled and no `setState` ever fires, so this hook is completely
 * inert — zero re-renders — for every lens other than an active,
 * motion-allowed `field_flow` (DeckGLMap's referential-stability contract
 * for its `layers` memo depends on this: an idle clock must never tick).
 *
 * Also pauses (cancels the in-flight frame, schedules nothing new) whenever
 * the tab is hidden, resuming cleanly when it becomes visible again — the
 * wind never animates off-screen, and the rAF loop is always torn down on
 * unmount or when `paused` flips true.
 */
export function useFlowAnimationClock(paused: boolean): number {
  const [time, setTime] = useState(0);
  const frameRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (
      paused ||
      typeof window === "undefined" ||
      typeof window.requestAnimationFrame !== "function"
    ) {
      return undefined;
    }
    let cancelled = false;

    function step(now: number): void {
      if (cancelled) return;
      if (startRef.current === null) startRef.current = now;
      setTime(now - (startRef.current ?? now));
      frameRef.current = window.requestAnimationFrame(step);
    }

    function handleVisibilityChange(): void {
      if (document.hidden) {
        if (frameRef.current !== null) {
          window.cancelAnimationFrame(frameRef.current);
          frameRef.current = null;
        }
        return;
      }
      if (frameRef.current === null && !cancelled) {
        // Resume the sweep phase cleanly (re-anchor `startRef`) rather than
        // jumping the trail forward by however long the tab was hidden.
        startRef.current = null;
        frameRef.current = window.requestAnimationFrame(step);
      }
    }

    frameRef.current = window.requestAnimationFrame(step);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      if (frameRef.current !== null) window.cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [paused]);

  return paused ? 0 : time;
}
