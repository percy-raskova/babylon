/**
 * Unit tests for the DeckGLMap component (deck.gl/maplibre mocked in
 * setup.ts). Adapted (spec-110 B2): DeckGLMap no longer reads
 * `mapStore`/`useNavigate`/`useParams` (stores + routing are B3 territory)
 * — it's now a controlled component driven by a `lens: Lens` prop plus
 * optional callbacks, so these tests render it with no Router at all.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";

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
});
