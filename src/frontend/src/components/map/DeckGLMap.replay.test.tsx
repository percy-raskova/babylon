/**
 * DeckGLMap — RADAR LOOP replay value-override (Program 17 Wave 3,
 * Frontend-W3R3). Covers the ONE new prop this lane adds to `DeckGLMap`'s
 * otherwise-controlled contract: `replay: MapReplayFillOverride | null`.
 *
 * Two invariants, both checked at the mocked deck.gl layer level (mirrors
 * `DeckGLMap.test.tsx`'s `H3HexagonLayer`/`H3ClusterLayer` capture idiom):
 *
 * 1. **County value reflected while active** — with `replay` set, a
 *    territory/region's fill color is computed from the frame's per-county
 *    reading, not the live snapshot value (hex AND region framing).
 * 2. **Exact restore on exit** — dropping the `replay` prop back to `null`
 *    (what `MapStage.tsx` does the instant `mapReplay.active` flips false)
 *    reproduces the live-only fill byte-for-byte (frame invariance, no
 *    residual override state anywhere in `DeckGLMap`).
 *
 * A missing county in the frame's `values` map renders the honest NO_DATA
 * fill (Constitution III.11) — never a silent fallback to the live value.
 */

import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { H3HexagonLayer, H3ClusterLayer } from "@deck.gl/geo-layers";
import { DeckGLMap, type MapReplayFillOverride } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";
import type { AdminFeatureProperties } from "@/types/game";
import type { FeatureCollection } from "geojson";

vi.mock("@deck.gl/geo-layers", () => ({
  H3HexagonLayer: vi.fn(),
  H3ClusterLayer: vi.fn(),
}));

function makeRegionFeature(overrides?: Partial<AdminFeatureProperties>): {
  type: "Feature";
  id: string;
  geometry: null;
  properties: AdminFeatureProperties;
} {
  return {
    type: "Feature",
    id: "26163",
    geometry: null,
    properties: {
      group_key: "26163",
      group_name: "Wayne",
      group_level: "county",
      hex_count: 2,
      member_h3: ["872a3072cffffff", "872a3072dffffff"],
      county_fips: "26163",
      state_fips: "26",
      state_name: "",
      cz_id: "",
      cz_name: "",
      bea_ea_code: "",
      bea_ea_name: "",
      msa_code: "",
      msa_name: "",
      heat: 0.5,
      consciousness: 0,
      wealth: 0,
      rent: 0,
      biocapacity: 0,
      population: 2000,
      profit_rate: 0.1,
      exploitation_rate: 0.4,
      occ: 2,
      imperial_rent: 5,
      org_presence: 3,
      ...overrides,
    },
  };
}

function makeRegionMapData(...features: ReturnType<typeof makeRegionFeature>[]): FeatureCollection {
  return { type: "FeatureCollection", features } as unknown as FeatureCollection;
}

/** Latest `getFillColor` accessor off a mocked layer's most recent constructor call. */
function latestGetFillColor(
  mock: typeof H3HexagonLayer | typeof H3ClusterLayer,
): (arg: unknown) => unknown {
  const calls = vi.mocked(mock).mock.calls;
  const last = calls.at(-1)?.[0] as { getFillColor?: (arg: unknown) => unknown } | undefined;
  if (!last?.getFillColor) throw new Error("layer mock was never called with getFillColor");
  return last.getFillColor;
}

describe("DeckGLMap — RADAR LOOP replay value-override (hex framing)", () => {
  it("reflects the frame's county value in the hex fill while replay is active", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "t1", h3_index: "872a3072cffffff", county_fips: "26163", heat: 0.1 }),
      ],
    });
    const replay: MapReplayFillOverride = {
      metric: "heat",
      valuesByCounty: { "26163": 0.9 },
    };

    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" replay={replay} />);
    const getFillColor = latestGetFillColor(H3HexagonLayer);
    const replayed = getFillColor({ id: "t1", h3_index: "872a3072cffffff" });

    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" replay={null} />);
    const live = latestGetFillColor(H3HexagonLayer)({ id: "t1", h3_index: "872a3072cffffff" });

    // A high replayed heat (0.9) must render differently than the low live
    // heat (0.1) the same territory otherwise carries.
    expect(replayed).not.toEqual(live);
  });

  it("renders honest NO_DATA for a county the frame's window has no reading for (never falls back to the live value)", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "t1", h3_index: "872a3072cffffff", county_fips: "26163", heat: 0.7 }),
      ],
    });
    const replay: MapReplayFillOverride = {
      metric: "heat",
      // "26163" deliberately absent — this county has no reading this tick.
      valuesByCounty: { "99999": 0.5 },
    };

    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" replay={replay} />);
    const getFillColor = latestGetFillColor(H3HexagonLayer);
    const result = getFillColor({ id: "t1", h3_index: "872a3072cffffff" });

    // Mirrors mapLensLayers.ts's private NO_DATA constant.
    expect(result).toEqual([58, 53, 48, 160]);
  });

  it("leaves an UNRELATED metric's fill untouched by a heat replay override (only the replay's own metric is overridden)", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "t1", h3_index: "872a3072cffffff", county_fips: "26163", heat: 0.1 }),
      ],
    });
    const replay: MapReplayFillOverride = { metric: "heat", valuesByCounty: { "26163": 0.9 } };

    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "habitability" }}
        framing="hex"
        replay={replay}
      />,
    );
    const withReplay = latestGetFillColor(H3HexagonLayer)({
      id: "t1",
      h3_index: "872a3072cffffff",
    });

    render(
      <DeckGLMap snapshot={snapshot} lens={{ kind: "habitability" }} framing="hex" replay={null} />,
    );
    const withoutReplay = latestGetFillColor(H3HexagonLayer)({
      id: "t1",
      h3_index: "872a3072cffffff",
    });

    expect(withReplay).toEqual(withoutReplay);
  });

  it("exact restore on exit: re-rendering with replay=null reproduces the original live fill byte-for-byte (frame invariance)", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "t1", h3_index: "872a3072cffffff", county_fips: "26163", heat: 0.42 }),
      ],
    });

    const { rerender } = render(
      <DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" replay={null} />,
    );
    const beforeReplay = latestGetFillColor(H3HexagonLayer)({
      id: "t1",
      h3_index: "872a3072cffffff",
    });

    rerender(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "heat" }}
        framing="hex"
        replay={{ metric: "heat", valuesByCounty: { "26163": 0.05 } }}
      />,
    );
    const duringReplay = latestGetFillColor(H3HexagonLayer)({
      id: "t1",
      h3_index: "872a3072cffffff",
    });
    expect(duringReplay).not.toEqual(beforeReplay);

    rerender(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" replay={null} />);
    const afterExit = latestGetFillColor(H3HexagonLayer)({ id: "t1", h3_index: "872a3072cffffff" });

    expect(afterExit).toEqual(beforeReplay);
  });
});

describe("DeckGLMap — RADAR LOOP replay value-override (region framing)", () => {
  // Region-framing fills are DOMAIN-normalized (regionFillForLens's
  // normalizedRampFill) — a single-feature FeatureCollection has a
  // degenerate [min,max] domain (span 0) that renders honest NO_DATA
  // regardless of the value, live or replayed (Constitution III.11's
  // "no fabricated floor" rule, DeckGLMap.tsx's computeFillDomain). Every
  // test below carries a second, untouched "control" feature purely to
  // give the live domain real spread, so the assertions exercise the
  // override itself rather than the unrelated degenerate-domain path.
  function makeMapDataWithControl(target: ReturnType<typeof makeRegionFeature>): FeatureCollection {
    const control = makeRegionFeature({
      group_key: "26165",
      county_fips: "26165",
      heat: 0.9,
      population: 9000,
    });
    return makeRegionMapData(target, control);
  }

  it("reflects the frame's county value in the region fill while replay is active", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature({ county_fips: "26163", population: 100 });
    const mapData = makeMapDataWithControl(feature);
    const replay: MapReplayFillOverride = {
      metric: "population",
      valuesByCounty: { "26163": 500000 },
    };

    render(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "metric", metric: "population" }}
        framing="county"
        replay={replay}
      />,
    );
    const replayed = latestGetFillColor(H3ClusterLayer)(feature);

    render(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "metric", metric: "population" }}
        framing="county"
        replay={null}
      />,
    );
    const live = latestGetFillColor(H3ClusterLayer)(feature);

    expect(replayed).not.toEqual(live);
  });

  it("region framing: honest NO_DATA for a county absent from the frame's window", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature({ county_fips: "26163", heat: 0.5 });
    const mapData = makeMapDataWithControl(feature);
    const replay: MapReplayFillOverride = { metric: "heat", valuesByCounty: { "99999": 0.9 } };

    render(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "heat" }}
        framing="county"
        replay={replay}
      />,
    );
    const result = latestGetFillColor(H3ClusterLayer)(feature);

    // Mirrors DeckGLMap.tsx's own REGION_NO_DATA_FILL constant.
    expect(result).toEqual([58, 53, 48, 160]);
  });

  it("exact restore on exit for region framing too", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature({ county_fips: "26163", heat: 0.1 });
    const mapData = makeMapDataWithControl(feature);

    const { rerender } = render(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "heat" }}
        framing="county"
        replay={null}
      />,
    );
    const beforeReplay = latestGetFillColor(H3ClusterLayer)(feature);

    rerender(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "heat" }}
        framing="county"
        replay={{ metric: "heat", valuesByCounty: { "26163": 0.95 } }}
      />,
    );
    expect(latestGetFillColor(H3ClusterLayer)(feature)).not.toEqual(beforeReplay);

    rerender(
      <DeckGLMap
        snapshot={snapshot}
        mapData={mapData}
        lens={{ kind: "heat" }}
        framing="county"
        replay={null}
      />,
    );
    expect(latestGetFillColor(H3ClusterLayer)(feature)).toEqual(beforeReplay);
  });
});
