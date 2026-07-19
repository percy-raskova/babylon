/**
 * Unit tests for the solidarity-line map layer module (Track 1 / Task 6).
 * Backend twin: `_build_solidarity_edge_lines`, `web/game/engine_bridge.py`
 * (already fog-gated + territory-anchored server-side); this module is the
 * consumer side that was previously entirely missing (Constitution III.10 —
 * data computed but never rendered). Modeled directly on
 * `fieldFlow.test.ts`'s structure. Covers the pure pieces:
 *
 * - `resolveSolidarityLines` — territory resolution (reusing criticalPulse's
 *   `resolveEntityPosition`), honest drops, same-territory ring policy,
 *   deterministic ordering.
 * - `solidarityLineWidthPixels` — monotonic weight grading from
 *   `solidarity_strength`.
 * - `buildSolidarityLineLayers` — empty-in -> empty-out (Constitution III.11:
 *   no visible solidarity is a legitimate, honest state, never a
 *   placeholder/zero-weight line).
 *
 * deck.gl layers are constructed headlessly (mirrors `fieldFlow.test.ts`):
 * lightweight local classes capturing `.id`/`.props` so assertions read the
 * real constructor arguments `solidarityLines.ts` passed, without any
 * WebGL/canvas.
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@deck.gl/layers", () => {
  class LineLayer {
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
  return { LineLayer, ScatterplotLayer };
});

import { cellToLatLng } from "h3-js";
import {
  resolveSolidarityLines,
  solidarityLineWidthPixels,
  buildSolidarityLineLayers,
  type SolidarityLineSegment,
} from "./solidarityLines";
import { makeTerritory, makeSolidarityEdgeLine } from "@/test/fixtures";

const H3_A = "872a3072cffffff";
const H3_B = "872a3072dffffff";

describe("resolveSolidarityLines", () => {
  const territories = [
    makeTerritory({ id: "T-a", h3_index: H3_A }),
    makeTerritory({ id: "T-b", h3_index: H3_B }),
  ];
  const [latA, lngA] = cellToLatLng(H3_A);
  const [latB, lngB] = cellToLatLng(H3_B);

  it("resolves both endpoints to their territory's h3 centroid", () => {
    const edges = [
      makeSolidarityEdgeLine({
        source: "C001",
        target: "C002",
        source_territory: "T-a",
        target_territory: "T-b",
        solidarity_strength: 0.4,
      }),
    ];
    const segments = resolveSolidarityLines(edges, territories);
    expect(segments).toEqual([
      {
        id: "C001-C002",
        from: [lngA, latA],
        to: [lngB, latB],
        strength: 0.4,
        sameTerritory: false,
      },
    ]);
  });

  it("drops an edge with a null source_territory or target_territory (honest drop, III.11)", () => {
    const edges = [
      makeSolidarityEdgeLine({ source_territory: null, target_territory: "T-b" }),
      makeSolidarityEdgeLine({ source_territory: "T-a", target_territory: null }),
    ];
    expect(resolveSolidarityLines(edges, territories)).toEqual([]);
  });

  it("drops an edge whose territory id doesn't resolve to any known territory", () => {
    const edges = [
      makeSolidarityEdgeLine({ source_territory: "T-ghost", target_territory: "T-b" }),
    ];
    expect(resolveSolidarityLines(edges, territories)).toEqual([]);
  });

  it("marks both endpoints resolving to the SAME territory as sameTerritory", () => {
    const edges = [
      makeSolidarityEdgeLine({
        source_territory: "T-a",
        target_territory: "T-a",
        solidarity_strength: 0.2,
      }),
    ];
    const [segment] = resolveSolidarityLines(edges, territories);
    expect(segment?.sameTerritory).toBe(true);
    expect(segment?.from).toEqual(segment?.to);
  });

  it("orders segments deterministically by id, independent of input order", () => {
    const edges = [
      makeSolidarityEdgeLine({
        source: "C002",
        target: "C003",
        source_territory: "T-a",
        target_territory: "T-b",
      }),
      makeSolidarityEdgeLine({
        source: "C001",
        target: "C002",
        source_territory: "T-a",
        target_territory: "T-b",
      }),
    ];
    const forward = resolveSolidarityLines(edges, territories).map((s) => s.id);
    const reversed = resolveSolidarityLines([...edges].reverse(), territories).map((s) => s.id);
    expect(forward).toEqual(["C001-C002", "C002-C003"]);
    expect(reversed).toEqual(forward);
  });

  it("empty edges in -> empty segments out (no visible solidarity is honest, not an error)", () => {
    expect(resolveSolidarityLines([], territories)).toEqual([]);
  });
});

describe("solidarityLineWidthPixels — monotonic in solidarity_strength, never zero/negative", () => {
  it("grows monotonically with strength (below the cap)", () => {
    expect(solidarityLineWidthPixels(0)).toBeGreaterThan(0);
    expect(solidarityLineWidthPixels(0.2)).toBeGreaterThan(solidarityLineWidthPixels(0));
    expect(solidarityLineWidthPixels(0.5)).toBeGreaterThan(solidarityLineWidthPixels(0.2));
  });

  it("clamps negative strength to the floor rather than going negative/zero", () => {
    expect(solidarityLineWidthPixels(-1)).toBe(solidarityLineWidthPixels(0));
  });
});

describe("buildSolidarityLineLayers", () => {
  const lineSegment: SolidarityLineSegment = {
    id: "C001-C002",
    from: [-83, 42],
    to: [-84, 43],
    strength: 0.5,
    sameTerritory: false,
  };
  const ringSegment: SolidarityLineSegment = {
    id: "C003-C004",
    from: [-83.5, 42.5],
    to: [-83.5, 42.5],
    strength: 0.2,
    sameTerritory: true,
  };

  it("empty segments in -> empty layer list out (never a placeholder/zero-weight line, III.11)", () => {
    expect(buildSolidarityLineLayers([])).toEqual([]);
  });

  it("builds a LineLayer for cross-territory segments", () => {
    const layers = buildSolidarityLineLayers([lineSegment]);
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toContain("solidarity-lines");
  });

  it("a same-territory segment renders only a ring mark, not a (zero-length, invisible) line", () => {
    const layers = buildSolidarityLineLayers([ringSegment]);
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toEqual(["solidarity-lines-same-territory"]);
  });

  it("mixed line + ring segments both render, each routed to its own layer", () => {
    const layers = buildSolidarityLineLayers([lineSegment, ringSegment]);
    const ids = layers.map((l) => (l as { id: string }).id);
    expect(ids).toContain("solidarity-lines");
    expect(ids).toContain("solidarity-lines-same-territory");
  });

  it("line width derives from solidarity_strength (weight, not hue)", () => {
    const strong: SolidarityLineSegment = { ...lineSegment, strength: 0.9 };
    const weak: SolidarityLineSegment = { ...lineSegment, id: "weak", strength: 0.1 };
    const layers = buildSolidarityLineLayers([strong, weak]);
    const lineLayer = layers.find((l) => (l as { id: string }).id === "solidarity-lines") as {
      props: Record<string, unknown>;
    };
    const getWidth = lineLayer.props.getWidth as (d: SolidarityLineSegment) => number;
    expect(getWidth(strong)).toBeGreaterThan(getWidth(weak));
  });
});
