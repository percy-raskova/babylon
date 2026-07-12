/**
 * Unit tests for the DeckGLMap component (deck.gl/maplibre mocked in
 * setup.ts). Adapted (spec-110 B2): DeckGLMap no longer reads
 * `mapStore`/`useNavigate`/`useParams` (stores + routing are B3 territory)
 * — it's now a controlled component driven by a `lens: Lens` prop plus
 * optional callbacks, so these tests render it with no Router at all.
 *
 * Spec-112 C5 adds region (county/cz/msa/bea_ea/state) framing, rendered
 * via `H3ClusterLayer` — setup.ts's global `@deck.gl/geo-layers` mock only
 * stubs `H3HexagonLayer`, so the region-framing describe blocks below
 * locally override that mock (Vitest: a file-local `vi.mock` call takes
 * precedence over a `setupFiles` one for that file) to also stub
 * `H3ClusterLayer`.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { DeckGL } from "@deck.gl/react";
import { H3HexagonLayer, H3ClusterLayer } from "@deck.gl/geo-layers";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";
import type { AdminFeatureProperties } from "@/types/game";
import type { FeatureCollection } from "geojson";

vi.mock("@deck.gl/geo-layers", () => ({
  H3HexagonLayer: vi.fn(),
  H3ClusterLayer: vi.fn(),
}));

/** A region (aggregated, non-hex) `/map/` feature — carries `properties.member_h3`. */
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
  // Real aggregated features ship geometry: null (the backend defers real
  // polygons to the frontend) — the `geojson` package's Feature type
  // doesn't express that possibility, so this constructs the honest shape
  // and casts through `unknown` rather than widening the shared type.
  return { type: "FeatureCollection", features } as unknown as FeatureCollection;
}

describe("DeckGLMap", () => {
  it("renders without crashing", () => {
    const snapshot = makeSnapshot();
    const { container } = render(<DeckGLMap snapshot={snapshot} lens={{ kind: "stance" }} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders with territories", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "terr-1", name: "Downtown" }),
        makeTerritory({ id: "terr-2", name: "Suburbs" }),
      ],
    });
    const { container } = render(<DeckGLMap snapshot={snapshot} lens={{ kind: "stance" }} />);
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders the map-mode selector, controlled by the lens prop", () => {
    const snapshot = makeSnapshot();
    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} />);
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
    expect(screen.getByTestId("lens-mode-heat")).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onLensChange when a lens-mode button is clicked", () => {
    const snapshot = makeSnapshot();
    const onLensChange = vi.fn();
    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "stance" }} onLensChange={onLensChange} />);
    screen.getByTestId("lens-mode-collapse").click();
    expect(onLensChange).toHaveBeenCalledWith({ kind: "collapse" });
  });

  it("renders the lens legend + mode selector when mapData carries balkanization data (spec-093)", () => {
    // Spec-093: balkanization lives under mapData.metadata.balkanization
    // (GET /api/games/{id}/map/), NOT on GameSnapshot (GET .../state/) —
    // see types/game.ts's MapSnapshotMetadata docstring.
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "T1", h3_index: "872a3072cffffff" })],
    });
    const mapData = {
      type: "FeatureCollection" as const,
      features: [],
      metadata: {
        balkanization: {
          factions: [{ id: "FAC_A", colonial_stance: "UPHOLD" }],
          sovereigns: [
            {
              id: "SOV_A",
              ruling_faction_id: "FAC_A",
              legitimacy: 0.5,
              claimed_territory_ids: [],
            },
          ],
          territory_influence: [
            {
              territory_id: "T1",
              influences: [{ faction_id: "FAC_A", influence_level: 0.6, support_type: "material" }],
              dominant_faction_id: "FAC_A",
              current_sovereign_id: null,
              contested: false,
              habitability: 0.5,
            },
          ],
        },
      },
    };

    render(<DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "stance" }} />);

    expect(screen.getByTestId("lens-legend-label")).toHaveTextContent(/stance/i);
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
  });

  it("renders without a lens legend when mapData has no balkanization block (honest no-data, no crash)", () => {
    const snapshot = makeSnapshot();
    render(<DeckGLMap snapshot={snapshot} mapData={null} lens={{ kind: "stance" }} />);
    expect(screen.queryByTestId("lens-legend-label")).not.toBeInTheDocument();
    // The lens mode control is always visible (cycling doesn't require data).
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
  });

  it("calls onTerritoryClick instead of navigating internally (no routing dependency)", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: "882a100d2bfffff" })],
    });
    const onTerritoryClick = vi.fn();
    // Regression guard: DeckGLMap must not require a Router context to render.
    expect(() =>
      render(
        <DeckGLMap
          snapshot={snapshot}
          lens={{ kind: "stance" }}
          onTerritoryClick={onTerritoryClick}
        />,
      ),
    ).not.toThrow();
  });

  // Phase V live-run regression (spec-113): the hex InspectionCard resolves
  // via GET /api/games/:id/hex/:h3_index/ (web/game/urls.py inspector-hex),
  // so the click must surface the picked territory's H3 INDEX — feeding the
  // territory row id produced an unresolvable ref (HTTP 403/404 card).
  it("passes the picked territory's h3_index (not its row id) to onTerritoryClick", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: "882a100d2bfffff" })],
    });
    const onTerritoryClick = vi.fn();
    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "stance" }}
        onTerritoryClick={onTerritoryClick}
      />,
    );
    const deckProps = vi.mocked(DeckGL).mock.calls.at(-1)?.[0] as {
      onClick?: (info: { object?: unknown }) => void;
    };
    deckProps.onClick?.({ object: { id: "terr-1", h3_index: "882a100d2bfffff" } });
    expect(onTerritoryClick).toHaveBeenCalledWith("882a100d2bfffff", expect.any(Object));
  });

  it("falls back to the territory row id when the picked territory has no h3_index", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: undefined })],
    });
    const onTerritoryClick = vi.fn();
    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "stance" }}
        onTerritoryClick={onTerritoryClick}
      />,
    );
    const deckProps = vi.mocked(DeckGL).mock.calls.at(-1)?.[0] as {
      onClick?: (info: { object?: unknown }) => void;
    };
    deckProps.onClick?.({ object: { id: "terr-1" } });
    expect(onTerritoryClick).toHaveBeenCalledWith("terr-1", expect.any(Object));
  });

  // spec-113 Phase-V polish: get_inspector_hex is stubbed, so the click hands
  // the InspectionStack the clicked feature's OWN state as inline data — the
  // same authoritative values the hover tooltip shows — instead of a bare id
  // that fetches an empty card.
  it("passes the clicked feature's own state as inline inspection data", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: "882a100d2bfffff" })],
    });
    const onTerritoryClick = vi.fn();
    render(
      <DeckGLMap
        snapshot={snapshot}
        lens={{ kind: "stance" }}
        onTerritoryClick={onTerritoryClick}
      />,
    );
    const deckProps = vi.mocked(DeckGL).mock.calls.at(-1)?.[0] as {
      onClick?: (info: { object?: unknown }) => void;
    };
    deckProps.onClick?.({
      object: {
        id: "terr-1",
        h3_index: "882a100d2bfffff",
        name: "Wayne County",
        population: 8000,
        heat: 0.4,
        rent_level: 1.2,
        biocapacity: 3.3,
        habitability: 0.8,
      },
    });
    expect(onTerritoryClick).toHaveBeenCalledWith(
      "882a100d2bfffff",
      expect.objectContaining({
        county_name: "Wayne County",
        population: 8000,
        heat: 0.4,
        rent_level: 1.2,
        biocapacity: 3.3,
        habitability: 0.8,
      }),
    );
  });
});

describe("DeckGLMap — region framing (spec-112 C5)", () => {
  beforeEach(() => {
    vi.mocked(H3HexagonLayer).mockClear();
    vi.mocked(H3ClusterLayer).mockClear();
  });

  it("with framing='county', renders the region layer reading member_h3 and not the base hex-fill layer", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature();
    const mapData = makeRegionMapData(feature);

    render(
      <DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} framing="county" />,
    );

    expect(H3ClusterLayer).toHaveBeenCalled();
    const regionLayerProps = vi.mocked(H3ClusterLayer).mock.calls[0]?.[0] as {
      id: string;
      getHexagons: (f: typeof feature) => string[];
    };
    expect(regionLayerProps.id).not.toBe("h3-hexagons");
    expect(regionLayerProps.getHexagons(feature)).toEqual(feature.properties.member_h3);

    // The base hex-fill layer must not be constructed at county framing.
    expect(
      vi.mocked(H3HexagonLayer).mock.calls.some(([props]) => props?.id === "h3-hexagons"),
    ).toBe(false);
  });

  it("with framing='hex' (today's default), the layer set is exactly today's: h3-hexagons built, no region layer", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: "882a100d2bfffff" })],
    });

    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} framing="hex" />);

    expect(
      vi.mocked(H3HexagonLayer).mock.calls.some(([props]) => props?.id === "h3-hexagons"),
    ).toBe(true);
    expect(H3ClusterLayer).not.toHaveBeenCalled();
  });

  it("omitting framing entirely defaults to hex — byte-identical to passing framing='hex'", () => {
    const snapshot = makeSnapshot({
      territories: [makeTerritory({ id: "terr-1", h3_index: "882a100d2bfffff" })],
    });

    render(<DeckGLMap snapshot={snapshot} lens={{ kind: "heat" }} />);

    expect(
      vi.mocked(H3HexagonLayer).mock.calls.some(([props]) => props?.id === "h3-hexagons"),
    ).toBe(true);
    expect(H3ClusterLayer).not.toHaveBeenCalled();
  });

  it("hovering a region produces a tooltip from AdminFeatureProperties (group_name + aggregates)", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature({ group_name: "Wayne County", heat: 0.42 });
    const mapData = makeRegionMapData(feature);

    render(
      <DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} framing="county" />,
    );

    const deckglProps = vi.mocked(DeckGL).mock.calls.at(-1)?.[0] as {
      onHover: (info: { object: unknown; x: number; y: number }) => void;
    };

    act(() => {
      deckglProps.onHover({ object: feature, x: 10, y: 20 });
    });

    expect(screen.getByTestId("region-tooltip")).toHaveTextContent("Wayne County");
  });

  it("does not produce a tooltip when the region hover clears (info.object is undefined)", () => {
    const snapshot = makeSnapshot();
    const feature = makeRegionFeature();
    const mapData = makeRegionMapData(feature);

    render(
      <DeckGLMap snapshot={snapshot} mapData={mapData} lens={{ kind: "heat" }} framing="county" />,
    );

    const deckglProps = vi.mocked(DeckGL).mock.calls.at(-1)?.[0] as {
      onHover: (info: { object: unknown; x: number; y: number }) => void;
    };

    act(() => {
      deckglProps.onHover({ object: feature, x: 10, y: 20 });
    });
    expect(screen.getByTestId("region-tooltip")).toBeInTheDocument();

    act(() => {
      deckglProps.onHover({ object: undefined, x: 10, y: 20 });
    });
    expect(screen.queryByTestId("region-tooltip")).not.toBeInTheDocument();
  });
});
