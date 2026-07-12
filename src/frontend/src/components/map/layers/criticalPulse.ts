/**
 * Critical-event map pulse — spec-113 Lane PULSE (DESIGN_BIBLE.md §5.2's
 * THIRD channel: "Critical events fire on three channels at once — wire
 * entry + toast + map-anchored visual on the affected geography").
 *
 * When a CRITICAL event that carries a resolvable geography arrives on the
 * classified urgent stream (`eventsSlice`'s critical toasts), the map fires a
 * ONE-SHOT expanding crimson ring at that location — pulling the player's eye
 * to WHERE the rupture is. The ring expands outward and fades to nothing over
 * `PULSE_DURATION_MS` (~1.8s, inside the bible's 1.5–2s window) then removes
 * itself: there is NO persistent loop (integration-ledger PERFORMANCE BUDGET).
 * Multiple simultaneous criticals each get their own independent ring layer.
 *
 * Motion policy (integration-ledger PERFORMANCE BUDGET — "nothing animates
 * the deck.gl render path except deck-native layer transitions"): the
 * expand + fade runs entirely on deck.gl's own `transitions` interpolation on
 * the GPU. React never rebuilds the layer per frame — it renders the ring
 * twice (start phase, then expanded phase) and deck.gl interpolates between.
 *
 * prefers-reduced-motion (index.css §"kill every loop, reduce one-shots to
 * fades"): the JS `matchMedia` check drops the transition entirely and
 * renders a STATIC crimson ring for the same lifetime instead of a ping.
 *
 * Colour is ksbc `--ksbc-accent-crimson` (`#dc143c` → rgb 220,20,60,
 * index.css §9b / DESIGN_BIBLE.md §9b — "red as rule/banner"), the map's
 * single structural urgency accent. The ring is STROKED, never filled, so it
 * never paints over the map data underneath (Tufte; DESIGN_BIBLE.md §6).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { ScatterplotLayer } from "@deck.gl/layers";
import { cellToLatLng, isValidCell } from "h3-js";
import type { RGBAColor } from "@/theme/colors";
import type { TerritoryState } from "@/types/game";
import type { StreamEvent } from "@/lib/eventClassifier";
import type { ToastEntry } from "@/store/slices/eventsSlice";

/** One-shot pulse lifetime — inside DESIGN_BIBLE.md §5.2's 1.5–2s window. */
export const PULSE_DURATION_MS = 1800;

/** Ring radius (metres) at the start and end of the expand transition. */
const PULSE_START_RADIUS_M = 2000;
const PULSE_END_RADIUS_M = 32000;
/** The single fixed radius used for the reduced-motion static ring. */
const PULSE_STATIC_RADIUS_M = 14000;
/** Cap the on-screen ring so a low zoom never fills the viewport. */
const PULSE_RADIUS_MAX_PX = 140;
/** Ring stroke width, in screen pixels. */
const PULSE_LINE_WIDTH_PX = 2.5;

/** ksbc `--ksbc-accent-crimson` (#dc143c) as an RGB triple. */
const CRIMSON: readonly [number, number, number] = [220, 20, 60];
/** Ring alpha: full at the start of the ping, transitioned to 0 as it expands. */
const PULSE_ALPHA_FULL = 220;
const PULSE_ALPHA_FADED = 0;
/** A reduced-motion ring holds one legible alpha for its whole lifetime. */
const PULSE_ALPHA_STATIC = 170;

/** A geography the map should ping — one per critical event, keyed by its stream id. */
export interface PulseTarget {
  /** The critical `StreamEvent.id` (`${tick}-${index}`) — one pulse per event. */
  id: string;
  /** deck.gl `[lng, lat]` centroid of the affected geography. */
  position: [number, number];
}

/** A live pulse: a target plus which transition phase it is in. */
export interface PulseInstance extends PulseTarget {
  /**
   * `false` on the first render (start radius, full alpha), flipped `true` on
   * the next frame so deck.gl transitions the ring OUTWARD and to zero alpha.
   */
  expanded: boolean;
}

/** deck.gl `[lng, lat]` centroid of an H3 cell (`cellToLatLng` returns `[lat, lng]`). */
function centroidOf(h3Index: string): [number, number] {
  const [lat, lng] = cellToLatLng(h3Index);
  return [lng, lat];
}

/** Naive mean of `[lng, lat]` centroids — honest enough for a county-scale ping (no US dateline concern). */
function meanCentroid(h3Indexes: string[]): [number, number] | null {
  if (h3Indexes.length === 0) return null;
  let sumLng = 0;
  let sumLat = 0;
  for (const h3 of h3Indexes) {
    const [lng, lat] = centroidOf(h3);
    sumLng += lng;
    sumLat += lat;
  }
  return [sumLng / h3Indexes.length, sumLat / h3Indexes.length];
}

/**
 * Resolve a single critical event's linked entity to a map `[lng, lat]`, or
 * `null` when it has no geography (Constitution III.11: a non-spatial
 * event — e.g. an org-linked one — pings nowhere rather than fabricating a
 * location). Tries, in order: a territory row-id match, a territory
 * `h3_index` match, a raw valid H3 cell, then a `county_fips` match (pinging
 * the mean centroid of that county's hexes). The match attempts ARE the
 * geographic gate — a non-geographic id resolves to `null`.
 */
function resolveEventPosition(
  event: StreamEvent,
  territories: TerritoryState[],
): [number, number] | null {
  const id = event.linkedEntityId;
  if (!id) return null;

  const byId = territories.find((t) => t.id === id);
  if (byId?.h3_index) return centroidOf(byId.h3_index);

  const byH3 = territories.find((t) => t.h3_index === id);
  if (byH3?.h3_index) return centroidOf(byH3.h3_index);

  if (isValidCell(id)) return centroidOf(id);

  const countyHexes = territories
    .filter((t): t is TerritoryState & { h3_index: string } => t.county_fips === id && !!t.h3_index)
    .map((t) => t.h3_index);
  if (countyHexes.length > 0) return meanCentroid(countyHexes);

  return null;
}

/**
 * Extract the pulse targets from the classified urgent stream: every CRITICAL
 * toast's events that resolve to a real geography. Notable/ambient toasts and
 * geographyless criticals contribute nothing (honest nulls). Pure — the hook
 * below owns the one-shot lifecycle.
 */
export function resolvePulseTargets(
  toasts: ToastEntry[],
  territories: TerritoryState[],
): PulseTarget[] {
  const targets: PulseTarget[] = [];
  for (const toast of toasts) {
    if (toast.severity !== "critical") continue;
    for (const event of toast.events) {
      const position = resolveEventPosition(event, territories);
      if (position) targets.push({ id: event.id, position });
    }
  }
  return targets;
}

/** Ring radius (metres) for a pulse's current phase / motion policy. */
export function pulseRadius(pulse: PulseInstance, reducedMotion: boolean): number {
  if (reducedMotion) return PULSE_STATIC_RADIUS_M;
  return pulse.expanded ? PULSE_END_RADIUS_M : PULSE_START_RADIUS_M;
}

/** Ring alpha for a pulse's current phase / motion policy. */
function pulseAlpha(pulse: PulseInstance, reducedMotion: boolean): number {
  if (reducedMotion) return PULSE_ALPHA_STATIC;
  return pulse.expanded ? PULSE_ALPHA_FADED : PULSE_ALPHA_FULL;
}

/** Crimson ring colour for a pulse's current phase / motion policy. */
export function pulseLineColor(pulse: PulseInstance, reducedMotion: boolean): RGBAColor {
  return [CRIMSON[0], CRIMSON[1], CRIMSON[2], pulseAlpha(pulse, reducedMotion)];
}

/**
 * Build one stroked crimson `ScatterplotLayer` ring per live pulse. Animated
 * rings carry deck.gl-native `transitions` (the only motion the perf budget
 * permits on the render path); reduced-motion rings omit them and hold a
 * static radius/alpha. Empty in → empty out (referentially inert when idle,
 * so `DeckGLMap`'s layers array stays stable — the stability contract).
 */
export function buildCriticalPulseLayers(
  pulses: PulseInstance[],
  reducedMotion: boolean,
): ScatterplotLayer<PulseInstance>[] {
  return pulses.map(
    (pulse) =>
      new ScatterplotLayer<PulseInstance>({
        id: `critical-pulse-${pulse.id}`,
        data: [pulse],
        getPosition: (d) => d.position,
        getRadius: (d) => pulseRadius(d, reducedMotion),
        getLineColor: (d) => pulseLineColor(d, reducedMotion),
        getLineWidth: PULSE_LINE_WIDTH_PX,
        stroked: true,
        filled: false,
        radiusUnits: "meters",
        radiusMaxPixels: PULSE_RADIUS_MAX_PX,
        lineWidthUnits: "pixels",
        lineWidthMinPixels: PULSE_LINE_WIDTH_PX,
        pickable: false,
        transitions: reducedMotion
          ? undefined
          : {
              getRadius: { type: "interpolation", duration: PULSE_DURATION_MS },
              getLineColor: { type: "interpolation", duration: PULSE_DURATION_MS },
            },
        updateTriggers: {
          getRadius: [pulse.expanded, reducedMotion],
          getLineColor: [pulse.expanded, reducedMotion],
        },
      }),
  );
}

/**
 * True when the viewer asked for reduced motion. Guards for jsdom / SSR where
 * `matchMedia` is absent (treated as "motion allowed"). A JS check is the
 * sanctioned honouring path for a deck.gl (non-CSS) animation (spec-113 Lane
 * PULSE brief) — index.css's `@media (prefers-reduced-motion)` can't reach a
 * WebGL layer.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** `setPulses` updater: flip the fresh rings to their expanded phase. Lifted to
 * module scope so the `setTimeout` callbacks below don't nest closures too deep
 * (sonarjs/no-nested-functions). */
function expandPulses(freshIds: Set<string>) {
  return (prev: PulseInstance[]): PulseInstance[] =>
    prev.map((p) => (freshIds.has(p.id) ? { ...p, expanded: true } : p));
}

/** `setPulses` updater: drop one ring once its transition has run. */
function removePulse(id: string) {
  return (prev: PulseInstance[]): PulseInstance[] => prev.filter((p) => p.id !== id);
}

/**
 * Own the one-shot pulse lifecycle for a set of `targets` and return the
 * deck.gl ring layers to merge into the map. New targets (by id, deduped
 * against everything ever seen) fire a ring; each ring flips to its expanded
 * phase on the next macrotask (so deck.gl has a start frame to transition
 * FROM) and is removed after `PULSE_DURATION_MS`. Idle (no new targets) it
 * holds a stable empty layer list and schedules no work — the map's
 * render-count/stability contract is untouched when nothing is rupturing.
 */
export function useCriticalPulses(targets: PulseTarget[]): ScatterplotLayer<PulseInstance>[] {
  const [pulses, setPulses] = useState<PulseInstance[]>([]);
  const seenRef = useRef<Set<string>>(new Set());
  const timersRef = useRef<number[]>([]);
  const reducedMotion = prefersReducedMotion();

  // A one-shot must never setState on an unmounted map — clear in-flight
  // timers when DeckGLMap goes away.
  useEffect(
    () => () => {
      for (const handle of timersRef.current) window.clearTimeout(handle);
      timersRef.current = [];
    },
    [],
  );

  useEffect(() => {
    const fresh = targets.filter((t) => !seenRef.current.has(t.id));
    if (fresh.length === 0) return;
    for (const t of fresh) seenRef.current.add(t.id);

    setPulses((prev) => [
      ...prev,
      ...fresh.map((t) => ({ id: t.id, position: t.position, expanded: false })),
    ]);

    // Next-macrotask flip → deck.gl transitions the ring outward + to zero
    // alpha (skipped under reduced motion: the ring stays static).
    if (!reducedMotion) {
      const freshIds = new Set(fresh.map((t) => t.id));
      const expand = window.setTimeout(() => {
        setPulses(expandPulses(freshIds));
        timersRef.current = timersRef.current.filter((h) => h !== expand);
      }, 0);
      timersRef.current.push(expand);
    }

    // One-shot lifetime: remove each ring once its transition has run.
    for (const t of fresh) {
      const removal = window.setTimeout(() => {
        setPulses(removePulse(t.id));
        timersRef.current = timersRef.current.filter((h) => h !== removal);
      }, PULSE_DURATION_MS);
      timersRef.current.push(removal);
    }
  }, [targets, reducedMotion]);

  return useMemo(() => buildCriticalPulseLayers(pulses, reducedMotion), [pulses, reducedMotion]);
}
