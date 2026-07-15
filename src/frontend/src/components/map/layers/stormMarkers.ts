/**
 * Storm markers — spec-113 Wave 3 Round 2a, DESIGN_BIBLE.md §11 "the weather
 * grammar". Map-anchored glyphs for UPRISING events; RUPTURE is deliberately
 * NOT rendered here (see below).
 *
 * A sibling to `criticalPulse.ts`, not a repurposing of it: criticalPulse's
 * one-shot expand+fade ring is reserved for the classified urgent stream's
 * CRITICAL toasts. Storm markers are STATIC (weather grammar law 2/3 — no
 * ambient pulse, one motion budget per tick and it belongs to the principal
 * contradiction, not to a weather glyph) and appear/disappear as hard cuts.
 *
 * **Lifetime/window convention.** Deliberately does NOT duplicate
 * `criticalPulse.ts`'s `useCriticalPulses` timer-owned one-shot lifecycle —
 * that machinery exists to run a 1.8s GPU expand/fade transition, which
 * storm markers never do. Instead `resolveStormTargets` reads the exact same
 * `s.events.toasts` array `resolvePulseTargets` does: a marker exists for as
 * long as its UPRISING event's toast is live (persistent-until-dismissed for
 * a critical severity, or the batched-ephemeral 12s window `EventToasts` owns
 * for a notable one — UPRISING's own severity, `eventClassifier.ts`'s
 * `EVENT_SEVERITY_MAP`). Riding the SAME source array as criticalPulse *is*
 * "the same lifetime/window convention" here — no new timer state to
 * duplicate or drift out of sync with the toast/tray model already governing
 * every other event-driven map visual.
 *
 * **UPRISING anchoring.** The engine's UPRISING payload (`struggle.py`)
 * carries `data.node_id` — a `social_class` node id, never a territory id.
 * The bridge enriches every uprising event with `data.territory_id` (W3
 * R2a-fix, `_serialize_event` in `web/game/engine_bridge.py`: node_id →
 * territory via the TENANCY resolution, honestly `null` when the class has
 * no territory). `resolveStormTargets` anchors on `territory_id` first and
 * falls back to `node_id` only for payloads predating the enrichment (a
 * class id never matches the territory namespace in production, so the
 * fallback is effectively inert there). Unresolvable events are omitted
 * rather than pinned to a guessed location (Constitution III.11).
 *
 * **RUPTURE is global.** Its payload (`contradiction.py`) is
 * `{opposition, gap, rate}` — no node/territory reference at all, by
 * construction (it names a graph-wide principal-contradiction crossing, not
 * a located event). It never gets a map glyph; `maoScore` below grades its
 * copy on the toast channel instead (`EventToasts.tsx`), which already
 * carries every RUPTURE toast (its severity is "critical" in
 * `EVENT_SEVERITY_MAP`) — no new chrome invented for it.
 */

import { ScatterplotLayer } from "@deck.gl/layers";
import type { RGBAColor } from "@/theme/colors";
import type { TerritoryState } from "@/types/game";
import type { ToastEntry } from "@/store/slices/eventsSlice";
import { resolveEntityPosition } from "./criticalPulse";

/** A live storm glyph — one per anchored UPRISING event, keyed by its stream id. */
export interface StormTarget {
  /** The UPRISING `StreamEvent.id` (`${tick}-${index}`) — one glyph per event. */
  id: string;
  /** deck.gl `[lng, lat]` position, resolved via `resolveEntityPosition`. */
  position: [number, number];
  /** The event's own `data.agitation` — the only intensity signal graded (never fabricated). */
  intensity: number;
}

/** Marker radius (metres) at zero agitation — never zero-sized (a storm with
 *  no measured agitation still needs a legible, if minimal, glyph). */
const STORM_RADIUS_BASE_M = 6000;
/** Radius growth (metres) per unit of `agitation` — monotonic size grading
 *  (weather grammar law 1: "intensity encodes as size/color, not motion"). */
const STORM_RADIUS_PER_AGITATION_M = 8000;
/** Cap the on-screen marker so a low zoom / high-agitation outlier never fills the viewport. */
const STORM_RADIUS_MAX_PX = 90;

/** ksbc `--babylon-heat` (#d97a2c) — the same "notable" severity tone
 *  `EventToasts.tsx`'s `SEVERITY_BORDER` uses for UPRISING's tier, reused
 *  here (not the pulse's crimson) so a storm glyph reads as a distinct,
 *  lower-tier signal from a critical-event ring at a glance. */
const STORM_COLOR: readonly [number, number, number] = [217, 122, 44];
const STORM_ALPHA = 210;

/** Marker radius (metres) for a given agitation value — monotonic, floor-clamped. */
export function stormRadius(intensity: number): number {
  const raw = STORM_RADIUS_BASE_M + Math.max(0, intensity) * STORM_RADIUS_PER_AGITATION_M;
  return Math.max(STORM_RADIUS_BASE_M, raw);
}

/** Storm marker fill colour — fixed (this layer has exactly one event kind
 *  and one intensity channel, already spent on size; DESIGN_BIBLE §11 law 1
 *  reserves color grading for cases with their own independent signal). */
function stormFillColor(): RGBAColor {
  return [STORM_COLOR[0], STORM_COLOR[1], STORM_COLOR[2], STORM_ALPHA];
}

/**
 * Extract storm targets from the classified toast stream: every UPRISING
 * event (any toast severity — unlike `resolvePulseTargets`, storms are
 * gated on event TYPE, not toast severity) that resolves to a real geography
 * AND carries a finite `agitation`. RUPTURE, geographyless UPRISINGs, and
 * UPRISINGs missing a usable agitation contribute nothing (honest nulls,
 * III.11). Pure — no lifecycle state; see the module docstring for why none
 * is needed.
 */
export function resolveStormTargets(
  toasts: ToastEntry[],
  territories: TerritoryState[],
): StormTarget[] {
  const targets: StormTarget[] = [];
  for (const toast of toasts) {
    for (const event of toast.events) {
      if (event.event.type !== "uprising") continue;
      const target = stormTargetFromUprising(event.id, event.event.data, territories);
      if (target) targets.push(target);
    }
  }
  return targets;
}

/**
 * Resolve one UPRISING event's payload to a storm target, or `null` when it
 * has no real geography or no finite `agitation` (honest omission, III.11).
 * Anchor preference: the bridge-enriched `territory_id` (W3 R2a-fix:
 * `_serialize_event` resolves node_id -> territory via TENANCY, honestly
 * `null` when unresolvable), falling back to `node_id` only for payloads
 * predating the enrichment — a social_class id never matches the territory
 * namespace in production, so the fallback is effectively inert there.
 */
function stormTargetFromUprising(
  eventId: string,
  data: Record<string, unknown>,
  territories: TerritoryState[],
): StormTarget | null {
  const { territory_id: territoryId, node_id: nodeId, agitation } = data;
  const anchorId = typeof territoryId === "string" ? territoryId : nodeId;
  const position = resolveEntityPosition(
    typeof anchorId === "string" ? anchorId : null,
    territories,
  );
  if (!position) return null;
  if (typeof agitation !== "number" || !Number.isFinite(agitation)) return null;
  return { id: eventId, position, intensity: agitation };
}

/**
 * Build one filled (never stroked — visually distinct from criticalPulse's
 * stroked-only ring), static `ScatterplotLayer` per storm target. No
 * `transitions` prop at all: appearance/disappearance is a hard cut by
 * construction (weather grammar law 2), and with zero motion code there is
 * nothing for `prefers-reduced-motion` to disable — the glyphs trivially
 * respect it. Empty in → empty out (referentially inert when idle, matching
 * `buildCriticalPulseLayers`'s stability contract).
 */
export function buildStormMarkerLayers(targets: StormTarget[]): ScatterplotLayer<StormTarget>[] {
  return targets.map(
    (target) =>
      new ScatterplotLayer<StormTarget>({
        id: `storm-marker-${target.id}`,
        data: [target],
        getPosition: (d) => d.position,
        getRadius: (d) => stormRadius(d.intensity),
        getFillColor: stormFillColor(),
        filled: true,
        stroked: false,
        radiusUnits: "meters",
        radiusMaxPixels: STORM_RADIUS_MAX_PX,
        pickable: false,
      }),
  );
}

/**
 * Mao's principal-contradiction ranking (`opposition.py::_score`,
 * `contradiction.py:284-306`'s RUPTURE gate): sharp gap AND fast-developing
 * rate outrank a large-but-static one. `rateWeight` defaults to the shipped
 * `defines.yaml` `principal_rate_weight: 10.0` — the RUPTURE event payload
 * itself carries only `{opposition, gap, rate}`, never the weight, so this
 * is the frontend's best-effort grading against the default a modded game
 * could in principle override (display grading of served values only per
 * the brief; the two served numbers, `gap`/`rate`, are real).
 */
export const MAO_SCORE_RATE_WEIGHT = 10;

export function maoScore(gap: number, rate: number, rateWeight = MAO_SCORE_RATE_WEIGHT): number {
  return gap * (1 + rateWeight * Math.abs(rate));
}
