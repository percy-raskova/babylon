/**
 * political.test.ts — layer construction contract for `buildPoliticalLayers` (spec-113
 * §7 task 3). deck.gl layers are constructed headlessly (no real WebGL/canvas needed for
 * `new GeoJsonLayer(...)` — only `.id`/`.props` are inspected).
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@deck.gl/layers", () => {
  class GeoJsonLayer {
    id: string;
    props: Record<string, unknown>;
    constructor(props: Record<string, unknown>) {
      this.id = props.id as string;
      this.props = props;
    }
  }
  return { GeoJsonLayer };
});

import { buildPoliticalLayers, type PolityClaim } from "./political";
import type { CountyTopology } from "@/lib/geo/topology";
import miniCounties from "@/lib/geo/__fixtures__/mini-counties.topojson.json";
import { countyFeatures } from "@/lib/geo/topology";

const topology = miniCounties as unknown as CountyTopology;
const counties = countyFeatures(topology);
// Minimal state feature collection — political.ts only reads it as opaque GeoJsonLayer data.
const states = {
  type: "FeatureCollection" as const,
  features: [
    {
      type: "Feature" as const,
      properties: { STATEFP: "99" },
      geometry: { type: "MultiPolygon" as const, coordinates: [] },
    },
  ],
};

function asMock(layer: unknown): { id: string; props: Record<string, unknown> } {
  return layer as unknown as { id: string; props: Record<string, unknown> };
}

describe("buildPoliticalLayers", () => {
  it("always emits the county-hairline and state-border base layers", () => {
    const layers = buildPoliticalLayers({ topology, counties, states });
    const ids = layers.map((l) => asMock(l).id);
    expect(ids).toContain("political-county-hairlines");
    expect(ids).toContain("political-state-borders");
    expect(layers).toHaveLength(2);
  });

  it("county hairlines are stroked, unfilled, and carry an updateTriggers entry", () => {
    const layers = buildPoliticalLayers({ topology, counties, states });
    const hairlines = asMock(layers[0]);
    expect(hairlines.props.stroked).toBe(true);
    expect(hairlines.props.filled).toBe(false);
    expect(hairlines.props.updateTriggers).toBeDefined();
  });

  it("emits a fill + border layer pair per claim", () => {
    const claims: PolityClaim[] = [
      {
        polityId: "polity-a",
        name: "Polity A",
        color: [255, 0, 0, 200],
        memberFips: ["00001", "00002"],
      },
    ];
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    const ids = layers.map((l) => asMock(l).id);
    expect(ids).toContain("political-polity-fill-polity-a");
    expect(ids).toContain("political-polity-border-polity-a");
    // base(2) + fill + border = 4
    expect(layers).toHaveLength(4);
  });

  it("polity fill layer is filled/unstroked; border layer is stroked/unfilled", () => {
    const claims: PolityClaim[] = [
      {
        polityId: "polity-a",
        name: "Polity A",
        color: [255, 0, 0, 200],
        memberFips: ["00001", "00002"],
      },
    ];
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    const fill = asMock(layers.find((l) => asMock(l).id === "political-polity-fill-polity-a"));
    const border = asMock(layers.find((l) => asMock(l).id === "political-polity-border-polity-a"));
    expect(fill.props.filled).toBe(true);
    expect(fill.props.stroked).toBe(false);
    expect(border.props.filled).toBe(false);
    expect(border.props.stroked).toBe(true);
    expect(fill.props.updateTriggers).toBeDefined();
    expect(border.props.updateTriggers).toBeDefined();
  });

  it("emits one fill+border pair per claim, for multiple claims", () => {
    const claims: PolityClaim[] = [
      { polityId: "polity-a", name: "A", color: [255, 0, 0, 200], memberFips: ["00001"] },
      { polityId: "polity-b", name: "B", color: [0, 255, 0, 200], memberFips: ["00004"] },
    ];
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    const ids = layers.map((l) => asMock(l).id);
    expect(ids).toContain("political-polity-fill-polity-a");
    expect(ids).toContain("political-polity-fill-polity-b");
    expect(ids).toContain("political-polity-border-polity-a");
    expect(ids).toContain("political-polity-border-polity-b");
    expect(layers).toHaveLength(6); // base(2) + 2*(fill+border)
  });

  it("adds a contested-counties layer when a county is claimed by more than one polity", () => {
    const claims: PolityClaim[] = [
      { polityId: "polity-a", name: "A", color: [255, 0, 0, 200], memberFips: ["00001", "00002"] },
      { polityId: "polity-b", name: "B", color: [0, 255, 0, 200], memberFips: ["00002", "00003"] },
    ];
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    const contested = asMock(layers.find((l) => asMock(l).id === "political-contested-counties"));
    expect(contested).toBeDefined();
    const data = contested.props.data as { features: { properties: { GEOID: string } }[] };
    expect(data.features.map((f) => f.properties.GEOID)).toEqual(["00002"]);
  });

  it("omits the contested-counties layer when no county is doubly claimed", () => {
    const claims: PolityClaim[] = [
      { polityId: "polity-a", name: "A", color: [255, 0, 0, 200], memberFips: ["00001"] },
      { polityId: "polity-b", name: "B", color: [0, 255, 0, 200], memberFips: ["00004"] },
    ];
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    expect(layers.find((l) => asMock(l).id === "political-contested-counties")).toBeUndefined();
  });

  it("suppresses the contested-counties layer entirely when showContested is false", () => {
    const claims: PolityClaim[] = [
      { polityId: "polity-a", name: "A", color: [255, 0, 0, 200], memberFips: ["00001", "00002"] },
      { polityId: "polity-b", name: "B", color: [0, 255, 0, 200], memberFips: ["00002", "00003"] },
    ];
    const layers = buildPoliticalLayers({
      topology,
      counties,
      states,
      claims,
      showContested: false,
    });
    expect(layers.find((l) => asMock(l).id === "political-contested-counties")).toBeUndefined();
  });

  it("no claims and no states/counties data still returns exactly the two base layers", () => {
    const layers = buildPoliticalLayers({ topology, counties, states, claims: [] });
    expect(layers).toHaveLength(2);
  });
});
