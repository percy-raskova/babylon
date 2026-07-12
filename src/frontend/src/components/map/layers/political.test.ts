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

// Hermetic double for the FillStyleExtension so the unit test never loads @deck.gl/core
// (no WebGL device). tsc still checks political.ts against the real extension types.
vi.mock("@deck.gl/extensions", () => {
  class FillStyleExtension {
    opts: Record<string, unknown>;
    constructor(opts: Record<string, unknown> = {}) {
      this.opts = opts;
    }
  }
  return { FillStyleExtension };
});

import { buildPoliticalLayers, type PolityClaim } from "./political";
import { STRIPE_PATTERN_NAME, STRIPE_PATTERN_SCALE } from "./stripePattern";
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

// --- STRIPE lane: TRUE diagonal-stripe contested fill (bible §2.1 layer 3) ---------------

describe("buildPoliticalLayers — contested TRUE striping", () => {
  const twoClaimsOneContested: PolityClaim[] = [
    { polityId: "polity-a", name: "A", color: [255, 0, 0, 200], memberFips: ["00001", "00002"] },
    { polityId: "polity-b", name: "B", color: [0, 255, 0, 200], memberFips: ["00002", "00003"] },
  ];

  function contestedLayer() {
    const layers = buildPoliticalLayers({
      topology,
      counties,
      states,
      claims: twoClaimsOneContested,
    });
    return asMock(layers.find((l) => asMock(l).id === "political-contested-counties"));
  }

  it("applies a FillStyleExtension configured for pattern fill", () => {
    const extensions = contestedLayer().props.extensions as { opts: { pattern: boolean } }[];
    expect(extensions).toHaveLength(1);
    expect(extensions[0]?.opts.pattern).toBe(true);
  });

  it("supplies a generated PNG atlas, mapping, and mask (not a checked-in sprite)", () => {
    const props = contestedLayer().props;
    expect(props.fillPatternAtlas).toMatch(/^data:image\/png;base64,/);
    expect(props.fillPatternMask).toBe(true);
    const mapping = props.fillPatternMapping as Record<string, unknown>;
    expect(mapping[STRIPE_PATTERN_NAME]).toBeDefined();
  });

  it("names the stripe pattern for every contested feature at the tuned world scale", () => {
    const props = contestedLayer().props;
    const getFillPattern = props.getFillPattern as () => string;
    expect(getFillPattern()).toBe(STRIPE_PATTERN_NAME);
    expect(props.getFillPatternScale).toBe(STRIPE_PATTERN_SCALE);
    const triggers = props.updateTriggers as Record<string, unknown>;
    expect(triggers.getFillPattern).toBeDefined();
  });
});

// --- SHIMMER lane: deck-native claim-redraw transition + attributable cause (bible §2.2) -

describe("buildPoliticalLayers — claim-redraw shimmer", () => {
  const claim: PolityClaim = {
    polityId: "polity-a",
    name: "A",
    color: [255, 0, 0, 200],
    memberFips: ["00001", "00002"],
  };

  function layerProps(claims: PolityClaim[], id: string) {
    const layers = buildPoliticalLayers({ topology, counties, states, claims });
    return asMock(layers.find((l) => asMock(l).id === id)).props;
  }

  it("gives the polity fill a deck-native color transition of >= 600ms", () => {
    const transitions = layerProps([claim], "political-polity-fill-polity-a").transitions as Record<
      string,
      number
    >;
    expect(transitions.getFillColor).toBeGreaterThanOrEqual(600);
  });

  it("gives the claim border deck-native color + width transitions of >= 600ms", () => {
    const transitions = layerProps([claim], "political-polity-border-polity-a")
      .transitions as Record<string, number>;
    expect(transitions.getLineColor).toBeGreaterThanOrEqual(600);
    expect(transitions.getLineWidth).toBeGreaterThanOrEqual(600);
  });

  it("renders a settled claim border in the claim's own colour (no redrawCause)", () => {
    const props = layerProps([claim], "political-polity-border-polity-a");
    expect(props.getLineColor).toEqual(claim.color);
  });

  it("renders the border in a distinct redraw accent while a redrawCause is live", () => {
    const redrawing: PolityClaim = { ...claim, redrawCause: "liberation:detroit" };
    const props = layerProps([redrawing], "political-polity-border-polity-a");
    expect(props.getLineColor).not.toEqual(claim.color);
  });

  it("threads the redrawCause into updateTriggers so a wire headline can name the cause", () => {
    const redrawing: PolityClaim = { ...claim, redrawCause: "liberation:detroit" };
    const triggers = layerProps([redrawing], "political-polity-border-polity-a").updateTriggers as {
      getLineColor: unknown[];
    };
    expect(triggers.getLineColor).toContain("liberation:detroit");
  });

  it("changes the fill updateTrigger signature when membership changes (fires the redraw)", () => {
    const before = layerProps([claim], "political-polity-fill-polity-a").updateTriggers as {
      getFillColor: unknown[];
    };
    const grown: PolityClaim = { ...claim, memberFips: ["00001", "00002", "00003"] };
    const after = layerProps([grown], "political-polity-fill-polity-a").updateTriggers as {
      getFillColor: unknown[];
    };
    expect(after.getFillColor).not.toEqual(before.getFillColor);
  });
});
