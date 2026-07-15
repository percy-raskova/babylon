/**
 * Unit tests for the storm-marker map layer (spec-113 Wave 3 Round 2a,
 * DESIGN_BIBLE.md §11 "the weather grammar"). Mirrors
 * `criticalPulse.test.ts`'s shape: pure resolution/grading functions, then
 * the deck.gl layer builder.
 *
 * Covers:
 * - `resolveStormTargets` — UPRISING events anchored via
 *   `resolveEntityPosition` (criticalPulse's shared geographic gate) off the
 *   bridge-enriched `data.territory_id` (W3 R2a-fix), falling back to
 *   `data.node_id` for pre-enrichment payloads; RUPTURE never produces a map
 *   glyph (it is global); an unresolvable UPRISING is honestly dropped (III.11).
 * - `stormRadius` — monotonic in `agitation`.
 * - `buildStormMarkerLayers` — one filled (never stroked), untransitioned
 *   (hard-cut, law 2/3) marker layer per target.
 * - `maoScore` — Mao's principal-contradiction ranking formula, verified
 *   against the shipped `defines.yaml` `principal_rate_weight: 10.0` default.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { ScatterplotLayer } from "@deck.gl/layers";
import { cellToLatLng } from "h3-js";
import {
  resolveStormTargets,
  buildStormMarkerLayers,
  stormRadius,
  maoScore,
  MAO_SCORE_RATE_WEIGHT,
  type StormTarget,
} from "./stormMarkers";
import type { StreamEvent } from "@/lib/eventClassifier";
import type { ToastEntry } from "@/store/slices/eventsSlice";
import { makeTerritory, makeEvent } from "@/test/fixtures";

/** A resolvable Detroit-area H3 cell reused across the geographic tests. */
const H3 = "872a3072cffffff";

function streamEvent(overrides: Partial<StreamEvent> = {}): StreamEvent {
  return {
    id: "5-0",
    event: makeEvent({ type: "uprising", tick: 5, data: { node_id: "T-crisis", agitation: 1.5 } }),
    tick: 5,
    severity: "notable",
    category: "struggle",
    stream: "urgent",
    linkedEntityId: null,
    linkedEntityType: null,
    ...overrides,
  };
}

function toast(events: StreamEvent[], severity: ToastEntry["severity"] = "notable"): ToastEntry {
  return { id: `t-${severity}`, tick: 5, severity, lifetime: "ephemeral", events };
}

/** Props captured by the Nth (default last) `new ScatterplotLayer(props)` call. */
function stormLayerProps(index = -1): Record<string, unknown> {
  const calls = vi.mocked(ScatterplotLayer).mock.calls;
  const call = index < 0 ? calls.at(index) : calls[index];
  if (!call) throw new Error("ScatterplotLayer was never constructed");
  return call[0] as unknown as Record<string, unknown>;
}

describe("resolveStormTargets", () => {
  it("anchors an UPRISING event via its payload node_id, at that territory's h3 centroid", () => {
    const territories = [makeTerritory({ id: "T-crisis", h3_index: H3 })];
    const toasts = [
      toast([
        streamEvent({
          event: makeEvent({
            type: "uprising",
            tick: 5,
            data: { node_id: "T-crisis", agitation: 1.5 },
          }),
        }),
      ]),
    ];
    const [lat, lng] = cellToLatLng(H3);
    expect(resolveStormTargets(toasts, territories)).toEqual([
      { id: "5-0", position: [lng, lat], intensity: 1.5 },
    ]);
  });

  it("anchors via the bridge-enriched territory_id — the production path (W3 R2a-fix)", () => {
    const territories = [makeTerritory({ id: "T-detroit", h3_index: H3 })];
    const toasts = [
      toast([
        streamEvent({
          event: makeEvent({
            type: "uprising",
            tick: 5,
            data: { node_id: "C001", territory_id: "T-detroit", agitation: 1.5 },
          }),
        }),
      ]),
    ];
    const [lat, lng] = cellToLatLng(H3);
    expect(resolveStormTargets(toasts, territories)).toEqual([
      { id: "5-0", position: [lng, lat], intensity: 1.5 },
    ]);
  });

  it("drops an UPRISING whose territory_id is honestly null and node_id matches nothing", () => {
    const territories = [makeTerritory({ id: "T-detroit", h3_index: H3 })];
    const toasts = [
      toast([
        streamEvent({
          event: makeEvent({
            type: "uprising",
            tick: 5,
            data: { node_id: "C001", territory_id: null, agitation: 1.5 },
          }),
        }),
      ]),
    ];
    expect(resolveStormTargets(toasts, territories)).toEqual([]);
  });

  it("does NOT anchor a RUPTURE event — it is global, no fabricated position (III.11)", () => {
    const territories = [makeTerritory({ id: "T-crisis", h3_index: H3 })];
    const toasts = [
      toast(
        [
          streamEvent({
            id: "5-1",
            severity: "critical",
            event: makeEvent({
              type: "rupture",
              tick: 5,
              data: { opposition: "capital_labor", gap: 0.6, rate: 0.2 },
            }),
          }),
        ],
        "critical",
      ),
    ];
    expect(resolveStormTargets(toasts, territories)).toEqual([]);
  });

  it("drops an UPRISING event whose node_id resolves to no territory (honest omission, not a fabricated position)", () => {
    const territories = [makeTerritory({ id: "T-other", h3_index: H3 })];
    const toasts = [
      toast([
        streamEvent({
          event: makeEvent({
            type: "uprising",
            tick: 5,
            data: { node_id: "C001", agitation: 1.5 },
          }),
        }),
      ]),
    ];
    expect(resolveStormTargets(toasts, territories)).toEqual([]);
  });

  it("drops an UPRISING event with a non-finite/missing agitation — never fabricates an intensity", () => {
    const territories = [makeTerritory({ id: "T-crisis", h3_index: H3 })];
    const toasts = [
      toast([
        streamEvent({
          event: makeEvent({ type: "uprising", tick: 5, data: { node_id: "T-crisis" } }),
        }),
      ]),
    ];
    expect(resolveStormTargets(toasts, territories)).toEqual([]);
  });

  it("anchors each of several simultaneous uprisings independently", () => {
    const territories = [
      makeTerritory({ id: "T1", h3_index: "872a3072cffffff" }),
      makeTerritory({ id: "T2", h3_index: "872a3072dffffff" }),
    ];
    const toasts = [
      toast([
        streamEvent({
          id: "5-0",
          event: makeEvent({ type: "uprising", tick: 5, data: { node_id: "T1", agitation: 0.5 } }),
        }),
        streamEvent({
          id: "5-1",
          event: makeEvent({ type: "uprising", tick: 5, data: { node_id: "T2", agitation: 2.0 } }),
        }),
      ]),
    ];
    const targets = resolveStormTargets(toasts, territories);
    expect(targets.map((t) => t.id)).toEqual(["5-0", "5-1"]);
  });
});

describe("stormRadius", () => {
  it("grades monotonically in agitation", () => {
    expect(stormRadius(2.0)).toBeGreaterThan(stormRadius(1.0));
    expect(stormRadius(1.0)).toBeGreaterThan(stormRadius(0.0));
  });

  it("never returns a negative or zero radius for zero agitation", () => {
    expect(stormRadius(0)).toBeGreaterThan(0);
  });
});

describe("buildStormMarkerLayers", () => {
  beforeEach(() => {
    vi.mocked(ScatterplotLayer).mockClear();
  });

  it("returns an empty list for no targets", () => {
    expect(buildStormMarkerLayers([])).toEqual([]);
    expect(ScatterplotLayer).not.toHaveBeenCalled();
  });

  it("builds one filled (never stroked) marker layer per target, id storm-marker-<eventId>", () => {
    const targets: StormTarget[] = [
      { id: "5-0", position: [-83, 42], intensity: 1.0 },
      { id: "5-1", position: [-84, 43], intensity: 2.0 },
    ];
    buildStormMarkerLayers(targets);
    expect(ScatterplotLayer).toHaveBeenCalledTimes(2);
    expect(stormLayerProps(0).id).toBe("storm-marker-5-0");
    expect(stormLayerProps(1).id).toBe("storm-marker-5-1");
    expect(stormLayerProps(0).filled).toBe(true);
    expect(stormLayerProps(0).stroked).toBe(false);
  });

  it("carries no deck.gl transitions — static glyphs, hard-cut appear/disappear (weather grammar law 2/3)", () => {
    buildStormMarkerLayers([{ id: "a", position: [0, 0], intensity: 1.0 }]);
    expect(stormLayerProps().transitions).toBeUndefined();
  });

  it("drives radius from the per-datum agitation accessor", () => {
    const target: StormTarget = { id: "a", position: [0, 0], intensity: 1.5 };
    buildStormMarkerLayers([target]);
    const getRadius = stormLayerProps().getRadius as (d: StormTarget) => number;
    expect(getRadius(target)).toBe(stormRadius(target.intensity));
  });
});

describe("maoScore", () => {
  it("matches the engine's principal-contradiction ranking (opposition.py: gap * (1 + rate_weight * |rate|))", () => {
    expect(maoScore(0.6, 0.2)).toBeCloseTo(0.6 * (1 + 10 * 0.2), 10);
  });

  it("defaults its rate weight to the shipped defines.yaml principal_rate_weight (10.0)", () => {
    expect(MAO_SCORE_RATE_WEIGHT).toBe(10);
  });

  it("is symmetric in the sign of rate (only |rate| matters)", () => {
    expect(maoScore(0.5, -0.3)).toBeCloseTo(maoScore(0.5, 0.3), 10);
  });
});
