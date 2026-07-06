/**
 * Unit tests for the DeckGLMap component (stubbed — WebGL mocked in setup.ts).
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";

describe("DeckGLMap", () => {
  it("renders without crashing", () => {
    const snapshot = makeSnapshot();
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders with territories", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "terr-1", name: "Downtown" }),
        makeTerritory({ id: "terr-2", name: "Suburbs" }),
      ],
    });
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders map controls container", () => {
    const snapshot = makeSnapshot();
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    // LayerControls removed in Phase 7 — verify map renders with legend container
    expect(container.querySelector("div")).toBeTruthy();
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

    render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} mapData={mapData} />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("lens-legend-label")).toHaveTextContent(/stance/i);
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
  });

  it("renders without a lens legend when mapData has no balkanization block (honest no-data, no crash)", () => {
    const snapshot = makeSnapshot();
    render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} mapData={null} />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("lens-legend-label")).not.toBeInTheDocument();
    // The lens mode control is always visible (cycling doesn't require data).
    expect(screen.getByTestId("map-mode-selector")).toBeInTheDocument();
  });
});
