/**
 * Unit tests for the critical-event map pulse (spec-113 Lane PULSE,
 * DESIGN_BIBLE.md §5.2 third channel). Covers the pure pieces:
 *
 * - `resolvePulseTargets` — which classified critical events ping, and WHERE
 *   (territory-id / h3 / county-fips resolution + honest nulls, III.11).
 * - `pulseRadius` / `pulseLineColor` — the expand + fade + reduced-motion
 *   geometry, and the ksbc crimson colour.
 * - `buildCriticalPulseLayers` — one stroked ring layer per pulse, wired with
 *   deck.gl-native transitions (perf budget) or a static ring under reduced
 *   motion.
 * - `prefersReducedMotion` — the matchMedia guard.
 *
 * `ScatterplotLayer` is the global setup.ts `vi.fn` mock, so a layer's props
 * are read off its captured constructor call (`.mock.calls`).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ScatterplotLayer } from "@deck.gl/layers";
import { cellToLatLng } from "h3-js";
import {
  resolvePulseTargets,
  buildCriticalPulseLayers,
  pulseRadius,
  pulseLineColor,
  prefersReducedMotion,
  PULSE_DURATION_MS,
  type PulseInstance,
} from "./criticalPulse";
import type { StreamEvent } from "@/lib/eventClassifier";
import type { ToastEntry } from "@/store/slices/eventsSlice";
import { makeTerritory, makeEvent } from "@/test/fixtures";

/** A resolvable Detroit-area H3 cell reused across the geographic tests. */
const H3 = "872a3072cffffff";

function streamEvent(overrides: Partial<StreamEvent> = {}): StreamEvent {
  return {
    id: "5-0",
    event: makeEvent({ type: "rupture", tick: 5 }),
    tick: 5,
    severity: "critical",
    category: "struggle",
    stream: "urgent",
    linkedEntityId: null,
    linkedEntityType: null,
    ...overrides,
  };
}

function toast(severity: ToastEntry["severity"], events: StreamEvent[]): ToastEntry {
  return { id: `t-${severity}`, tick: 5, severity, lifetime: "persistent", events };
}

/** Props captured by the Nth (default last) `new ScatterplotLayer(props)` call. */
function pulseLayerProps(index = -1): Record<string, unknown> {
  const calls = vi.mocked(ScatterplotLayer).mock.calls;
  const call = index < 0 ? calls.at(index) : calls[index];
  if (!call) throw new Error("ScatterplotLayer was never constructed");
  return call[0] as unknown as Record<string, unknown>;
}

describe("resolvePulseTargets", () => {
  it("pings a critical event linked to a territory row id, at that territory's h3 centroid", () => {
    const territories = [makeTerritory({ id: "T-crisis", h3_index: H3 })];
    const toasts = [
      toast("critical", [
        streamEvent({ linkedEntityId: "T-crisis", linkedEntityType: "territory" }),
      ]),
    ];
    const [lat, lng] = cellToLatLng(H3);
    expect(resolvePulseTargets(toasts, territories)).toEqual([{ id: "5-0", position: [lng, lat] }]);
  });

  it("resolves a linked id that is itself a raw valid H3 cell", () => {
    const toasts = [
      toast("critical", [streamEvent({ linkedEntityId: H3, linkedEntityType: "territory" })]),
    ];
    const [lat, lng] = cellToLatLng(H3);
    expect(resolvePulseTargets(toasts, [])).toEqual([{ id: "5-0", position: [lng, lat] }]);
  });

  it("resolves a county_fips link to the mean centroid of that county's hexes", () => {
    const a = "872a3072cffffff";
    const b = "872a3072dffffff";
    const territories = [
      makeTerritory({ id: "T-a", h3_index: a, county_fips: "26163" }),
      makeTerritory({ id: "T-b", h3_index: b, county_fips: "26163" }),
      makeTerritory({ id: "T-c", h3_index: "872a30720ffffff", county_fips: "26099" }),
    ];
    const toasts = [
      toast("critical", [streamEvent({ linkedEntityId: "26163", linkedEntityType: "territory" })]),
    ];
    const [latA, lngA] = cellToLatLng(a);
    const [latB, lngB] = cellToLatLng(b);
    expect(resolvePulseTargets(toasts, territories)).toEqual([
      { id: "5-0", position: [(lngA + lngB) / 2, (latA + latB) / 2] },
    ]);
  });

  it("does NOT ping a non-critical (notable) toast", () => {
    const territories = [makeTerritory({ id: "T1", h3_index: H3 })];
    const toasts = [
      toast("notable", [streamEvent({ linkedEntityId: "T1", linkedEntityType: "territory" })]),
    ];
    expect(resolvePulseTargets(toasts, territories)).toEqual([]);
  });

  it("does NOT ping a critical event with no resolvable geography (honest null, III.11)", () => {
    const territories = [makeTerritory({ id: "T1", h3_index: H3 })];
    const toasts = [
      toast("critical", [
        streamEvent({ linkedEntityId: "ORG-finance", linkedEntityType: "organization" }),
        streamEvent({ id: "5-1", linkedEntityId: null, linkedEntityType: null }),
      ]),
    ];
    expect(resolvePulseTargets(toasts, territories)).toEqual([]);
  });

  it("pings each of several simultaneous criticals independently", () => {
    const territories = [
      makeTerritory({ id: "T1", h3_index: "872a3072cffffff" }),
      makeTerritory({ id: "T2", h3_index: "872a3072dffffff" }),
    ];
    const toasts = [
      toast("critical", [
        streamEvent({ id: "5-0", linkedEntityId: "T1", linkedEntityType: "territory" }),
      ]),
      toast("critical", [
        streamEvent({ id: "5-1", linkedEntityId: "T2", linkedEntityType: "territory" }),
      ]),
    ];
    const targets = resolvePulseTargets(toasts, territories);
    expect(targets.map((t) => t.id)).toEqual(["5-0", "5-1"]);
  });
});

describe("pulseRadius / pulseLineColor", () => {
  const start: PulseInstance = { id: "a", position: [0, 0], expanded: false };
  const end: PulseInstance = { id: "a", position: [0, 0], expanded: true };

  it("expands the ring outward from start to expanded phase", () => {
    expect(pulseRadius(end, false)).toBeGreaterThan(pulseRadius(start, false));
  });

  it("fades the ring from full alpha to zero as it expands", () => {
    expect(pulseLineColor(start, false)[3]).toBeGreaterThan(0);
    expect(pulseLineColor(end, false)[3]).toBe(0);
  });

  it("colours the ring ksbc crimson (#dc143c → 220,20,60)", () => {
    const [r, g, b] = pulseLineColor(start, false);
    expect([r, g, b]).toEqual([220, 20, 60]);
  });

  it("under reduced motion holds ONE static radius and a legible (non-faded) alpha in both phases", () => {
    expect(pulseRadius(start, true)).toBe(pulseRadius(end, true));
    expect(pulseLineColor(start, true)[3]).toBeGreaterThan(0);
    expect(pulseLineColor(end, true)[3]).toBeGreaterThan(0);
    expect(pulseLineColor(start, true)[3]).toBe(pulseLineColor(end, true)[3]);
  });
});

describe("buildCriticalPulseLayers", () => {
  beforeEach(() => {
    vi.mocked(ScatterplotLayer).mockClear();
  });

  it("returns an empty list for no pulses (referentially inert when idle)", () => {
    expect(buildCriticalPulseLayers([], false)).toEqual([]);
    expect(ScatterplotLayer).not.toHaveBeenCalled();
  });

  it("builds one stroked (never filled) ring layer per pulse, id critical-pulse-<eventId>", () => {
    buildCriticalPulseLayers(
      [
        { id: "5-0", position: [-83, 42], expanded: false },
        { id: "5-1", position: [-84, 43], expanded: false },
      ],
      false,
    );
    expect(ScatterplotLayer).toHaveBeenCalledTimes(2);
    expect(pulseLayerProps(0).id).toBe("critical-pulse-5-0");
    expect(pulseLayerProps(1).id).toBe("critical-pulse-5-1");
    expect(pulseLayerProps(0).stroked).toBe(true);
    expect(pulseLayerProps(0).filled).toBe(false);
  });

  it("wires deck.gl-native transitions for the animated ring (no per-frame React rebuild)", () => {
    buildCriticalPulseLayers([{ id: "a", position: [0, 0], expanded: false }], false);
    const transitions = pulseLayerProps().transitions as {
      getRadius: { duration: number };
      getLineColor: { duration: number };
    };
    expect(transitions.getRadius.duration).toBe(PULSE_DURATION_MS);
    expect(transitions.getLineColor.duration).toBe(PULSE_DURATION_MS);
  });

  it("omits transitions entirely under reduced motion (static ring, not a ping)", () => {
    buildCriticalPulseLayers([{ id: "a", position: [0, 0], expanded: false }], true);
    expect(pulseLayerProps().transitions).toBeUndefined();
  });

  it("drives radius + colour from the per-datum accessors", () => {
    const pulse: PulseInstance = { id: "a", position: [0, 0], expanded: false };
    buildCriticalPulseLayers([pulse], false);
    const props = pulseLayerProps();
    const getRadius = props.getRadius as (d: PulseInstance) => number;
    const getLineColor = props.getLineColor as (d: PulseInstance) => number[];
    expect(getRadius(pulse)).toBe(pulseRadius(pulse, false));
    expect(getLineColor(pulse)).toEqual(pulseLineColor(pulse, false));
  });
});

describe("prefersReducedMotion", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns false when matchMedia is unavailable (jsdom default → motion allowed)", () => {
    expect(prefersReducedMotion()).toBe(false);
  });

  it("returns true when the reduce query matches", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    expect(prefersReducedMotion()).toBe(true);
  });

  it("returns false when the reduce query does not match", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false }));
    expect(prefersReducedMotion()).toBe(false);
  });
});
