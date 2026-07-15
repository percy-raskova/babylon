/**
 * Unit tests for the gradient-wind vector lens's layer module (DESIGN_BIBLE.md
 * §11, Wave 3 — "the vector lens (gradient wind) is law 1's first extensive
 * citizen"). Covers the pure pieces:
 *
 * - `edgesForField` — filters a mixed field_state edge list down to one field.
 * - `resolveFlowSegments` — territory resolution (reusing criticalPulse's
 *   `resolveEntityPosition`), honest drops, same-territory swirl policy,
 *   gradient-sign direction, deterministic ordering.
 * - `flowWidthPixels` / `flowOpacity` / `swirlRadiusMeters` — monotonic
 *   magnitude grading (weather-grammar law 1: geometry encodes magnitude,
 *   hue stays fixed).
 * - `tripCurrentTime` — the animated trail's pure loop-phase math.
 * - `buildFieldFlowLayers` — reduced-motion static variant, no transitions
 *   (hard cut between ticks), empty-in -> empty-out.
 *
 * deck.gl layers are constructed headlessly (mirrors `political.test.ts`):
 * lightweight local classes capturing `.id`/`.props` so assertions read the
 * real constructor arguments `fieldFlow.ts` passed, without any WebGL/canvas.
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@deck.gl/layers", () => {
  class PathLayer {
    id: string;
    props: Record<string, unknown>;
    constructor(props: Record<string, unknown>) {
      this.id = props.id as string;
      this.props = props;
    }
  }
  class ScatterplotLayer {
    id: string;
    props: Record<string, unknown>;
    constructor(props: Record<string, unknown>) {
      this.id = props.id as string;
      this.props = props;
    }
  }
  return { PathLayer, ScatterplotLayer };
});

vi.mock("@deck.gl/geo-layers", () => {
  class TripsLayer {
    id: string;
    props: Record<string, unknown>;
    constructor(props: Record<string, unknown>) {
      this.id = props.id as string;
      this.props = props;
    }
  }
  return { TripsLayer };
});

// Hermetic double (mirrors political.test.ts's FillStyleExtension double) so
// this unit test never loads @deck.gl/core's WebGL device machinery — tsc
// still checks fieldFlow.ts against the real extension types.
vi.mock("@deck.gl/extensions", () => {
  class PathStyleExtension {
    opts: Record<string, unknown>;
    constructor(opts: Record<string, unknown> = {}) {
      this.opts = opts;
    }
  }
  return { PathStyleExtension };
});

import { cellToLatLng } from "h3-js";
import {
  edgesForField,
  resolveFlowSegments,
  flowWidthPixels,
  flowOpacity,
  swirlRadiusMeters,
  tripCurrentTime,
  buildFieldFlowLayers,
  FLOW_LOOP_DURATION_MS,
  type FlowSegment,
} from "./fieldFlow";
import { makeTerritory, makeFieldStateEdge } from "@/test/fixtures";

const H3_A = "872a3072cffffff";
const H3_B = "872a3072dffffff";

describe("edgesForField", () => {
  it("keeps only edges matching the requested field", () => {
    const edges = [
      makeFieldStateEdge({ field: "exploitation", source: "a", target: "b" }),
      makeFieldStateEdge({ field: "atomization", source: "c", target: "d" }),
    ];
    expect(edgesForField(edges, "exploitation")).toEqual([edges[0]]);
  });

  it("returns an empty array when nothing matches", () => {
    const edges = [makeFieldStateEdge({ field: "atomization" })];
    expect(edgesForField(edges, "exploitation")).toEqual([]);
  });
});

describe("resolveFlowSegments", () => {
  const territories = [
    makeTerritory({ id: "T-a", h3_index: H3_A }),
    makeTerritory({ id: "T-b", h3_index: H3_B }),
  ];
  const [latA, lngA] = cellToLatLng(H3_A);
  const [latB, lngB] = cellToLatLng(H3_B);

  it("resolves both endpoints to their territory's h3 centroid, positive gradient flows source->target", () => {
    const edges = [
      makeFieldStateEdge({
        source: "C001",
        target: "C002",
        source_territory: "T-a",
        target_territory: "T-b",
        gradient: 0.4,
      }),
    ];
    const segments = resolveFlowSegments(edges, territories);
    expect(segments).toEqual([
      {
        id: "C001->C002",
        flowFrom: [lngA, latA],
        flowTo: [lngB, latB],
        gradient: 0.4,
        magnitude: 0.4,
        sameTerritory: false,
      },
    ]);
  });

  it("a negative gradient reverses the rendered flow direction (target->source is the honest transfer direction)", () => {
    const edges = [
      makeFieldStateEdge({
        source: "C001",
        target: "C002",
        source_territory: "T-a",
        target_territory: "T-b",
        gradient: -0.4,
      }),
    ];
    const [segment] = resolveFlowSegments(edges, territories);
    expect(segment?.flowFrom).toEqual([lngB, latB]);
    expect(segment?.flowTo).toEqual([lngA, latA]);
    expect(segment?.magnitude).toBe(0.4);
  });

  it("drops an edge with a null source_territory or target_territory (honest drop, III.11)", () => {
    const edges = [
      makeFieldStateEdge({ source_territory: null, target_territory: "T-b" }),
      makeFieldStateEdge({ source_territory: "T-a", target_territory: null }),
    ];
    expect(resolveFlowSegments(edges, territories)).toEqual([]);
  });

  it("drops an edge whose territory id doesn't resolve to any known territory (unresolvable id)", () => {
    const edges = [makeFieldStateEdge({ source_territory: "T-ghost", target_territory: "T-b" })];
    expect(resolveFlowSegments(edges, territories)).toEqual([]);
  });

  it("marks both endpoints resolving to the SAME territory as sameTerritory (single-county scenarios)", () => {
    const edges = [
      makeFieldStateEdge({ source_territory: "T-a", target_territory: "T-a", gradient: 0.2 }),
    ];
    const [segment] = resolveFlowSegments(edges, territories);
    expect(segment?.sameTerritory).toBe(true);
    expect(segment?.flowFrom).toEqual(segment?.flowTo);
  });

  it("orders segments deterministically by id, independent of input order", () => {
    const edges = [
      makeFieldStateEdge({
        source: "C002",
        target: "C003",
        source_territory: "T-a",
        target_territory: "T-b",
      }),
      makeFieldStateEdge({
        source: "C001",
        target: "C002",
        source_territory: "T-a",
        target_territory: "T-b",
      }),
    ];
    const forward = resolveFlowSegments(edges, territories).map((s) => s.id);
    const reversed = resolveFlowSegments([...edges].reverse(), territories).map((s) => s.id);
    expect(forward).toEqual(["C001->C002", "C002->C003"]);
    expect(reversed).toEqual(forward);
  });

  it("empty edges in -> empty segments out", () => {
    expect(resolveFlowSegments([], territories)).toEqual([]);
  });
});

describe("magnitude grading — monotonic in |gradient|, never zero/negative", () => {
  it("flowWidthPixels grows monotonically with magnitude (below the cap)", () => {
    expect(flowWidthPixels(0)).toBeGreaterThan(0);
    expect(flowWidthPixels(0.2)).toBeGreaterThan(flowWidthPixels(0));
    expect(flowWidthPixels(0.5)).toBeGreaterThan(flowWidthPixels(0.2));
  });

  it("flowOpacity grows monotonically with magnitude and stays within a legible [floor, 255] band", () => {
    const low = flowOpacity(0);
    const mid = flowOpacity(0.4);
    const high = flowOpacity(1);
    expect(low).toBeGreaterThan(0);
    expect(mid).toBeGreaterThan(low);
    expect(high).toBeGreaterThan(mid);
    expect(high).toBeLessThanOrEqual(255);
  });

  it("swirlRadiusMeters grows monotonically with magnitude and is never zero-sized", () => {
    expect(swirlRadiusMeters(0)).toBeGreaterThan(0);
    expect(swirlRadiusMeters(0.5)).toBeGreaterThan(swirlRadiusMeters(0));
  });
});

describe("tripCurrentTime — the animated trail's pure loop-phase math", () => {
  it("starts at 0 at clock time 0", () => {
    expect(tripCurrentTime(0)).toBe(0);
  });

  it("loops back to 0 after exactly one full FLOW_LOOP_DURATION_MS period", () => {
    expect(tripCurrentTime(FLOW_LOOP_DURATION_MS)).toBe(0);
    expect(tripCurrentTime(FLOW_LOOP_DURATION_MS * 3)).toBe(0);
  });

  it("is monotonically increasing within one loop period", () => {
    const quarter = tripCurrentTime(FLOW_LOOP_DURATION_MS * 0.25);
    const half = tripCurrentTime(FLOW_LOOP_DURATION_MS * 0.5);
    expect(half).toBeGreaterThan(quarter);
  });
});

describe("buildFieldFlowLayers", () => {
  const pathSegment: FlowSegment = {
    id: "C001->C002",
    flowFrom: [-83, 42],
    flowTo: [-84, 43],
    gradient: 0.5,
    magnitude: 0.5,
    sameTerritory: false,
  };
  const swirlSegment: FlowSegment = {
    id: "C003->C004",
    flowFrom: [-83.5, 42.5],
    flowTo: [-83.5, 42.5],
    gradient: 0.2,
    magnitude: 0.2,
    sameTerritory: true,
  };

  it("empty segments in -> empty layer list out (never fabricated arrows, III.11)", () => {
    expect(buildFieldFlowLayers([], { reducedMotion: false, time: 0 })).toEqual([]);
    expect(buildFieldFlowLayers([], { reducedMotion: true, time: 0 })).toEqual([]);
  });

  it("motion-allowed: builds a static dashed path + arrowhead + an animated TripsLayer", () => {
    const layers = buildFieldFlowLayers([pathSegment], { reducedMotion: false, time: 500 });
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toContain("field-flow-static");
    expect(ids).toContain("field-flow-arrowheads");
    expect(ids).toContain("field-flow-trips");
  });

  it("reduced motion: static dashes + arrowheads only, NO TripsLayer (fully static directional marks)", () => {
    const layers = buildFieldFlowLayers([pathSegment], { reducedMotion: true, time: 500 });
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toContain("field-flow-static");
    expect(ids).toContain("field-flow-arrowheads");
    expect(ids).not.toContain("field-flow-trips");
  });

  it("no-transitions-on-appearance: every layer is a hard cut, none carry a deck.gl `transitions` prop", () => {
    const layers = buildFieldFlowLayers([pathSegment], { reducedMotion: false, time: 0 });
    for (const layer of layers) {
      expect((layer as { props: Record<string, unknown> }).props.transitions).toBeUndefined();
    }
  });

  it("a same-territory segment renders only the swirl mark, not a (zero-length, invisible) path", () => {
    const layers = buildFieldFlowLayers([swirlSegment], { reducedMotion: false, time: 0 });
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toEqual(["field-flow-swirl"]);
  });

  it("mixed path + swirl segments both render, each routed to its own layer", () => {
    const layers = buildFieldFlowLayers([pathSegment, swirlSegment], {
      reducedMotion: true,
      time: 0,
    });
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toContain("field-flow-static");
    expect(ids).toContain("field-flow-swirl");
  });
});
