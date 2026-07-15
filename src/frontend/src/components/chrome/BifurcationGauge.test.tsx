/**
 * BifurcationGauge tests — the "George Jackson dial" v1 HUD widget
 * (Wave 3 Round 2a). TDD red phase written before the implementation.
 * Standard 4-test suite shape (EconomyDashboard/SurvivalDuelPanel) plus an
 * aggregation unit test.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import {
  BifurcationGauge,
  aggregateBifurcationScore,
  aggregateFascistAlignment,
} from "./BifurcationGauge";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import {
  makeSnapshot,
  makeTerritory,
  makeFieldStatePayload,
  makeFieldStateNode,
} from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

function seedTerritories(territories: ReturnType<typeof makeTerritory>[]): void {
  useStore.setState((s) => ({
    world: { ...s.world, snapshot: makeSnapshot({ territories }) },
  }));
}

describe("BifurcationGauge", () => {
  it("renders both needles once real data loads (territory bifurcation_score + field_state fascist_alignment)", async () => {
    seedTerritories([
      makeTerritory({ id: "t1", bifurcation_score: -0.4, population: 100 }),
      makeTerritory({ id: "t2", bifurcation_score: 0.2, population: 300 }),
    ]);
    server.use(
      http.get("/api/games/:id/field_state/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeFieldStatePayload({
            nodes: [
              makeFieldStateNode({ id: "C001", fascist_alignment: 0.5 }),
              makeFieldStateNode({ id: "C002", fascist_alignment: 0.1 }),
            ],
          }),
        }),
      ),
    );

    render(<BifurcationGauge gameId={DEFAULT_GAME_ID} />);

    await waitFor(() =>
      expect(screen.getByTestId("bifurcation-needle-fascist")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("bifurcation-needle-territory")).toBeInTheDocument();
    // weighted: (-0.4*100 + 0.2*300) / 400 = 0.05
    expect(screen.getByTestId("bifurcation-territory-line")).toHaveTextContent("0.05");
    // plain mean: (0.5 + 0.1) / 2 = 0.30
    expect(screen.getByTestId("bifurcation-fascist-line")).toHaveTextContent("0.30");
  });

  it("shows an honest empty state for both sources when neither carries real data", async () => {
    seedTerritories([makeTerritory({ id: "t1", bifurcation_score: null })]);
    render(<BifurcationGauge gameId={DEFAULT_GAME_ID} />);

    await waitFor(() =>
      expect(screen.getByTestId("bifurcation-fascist-line")).toHaveTextContent("no data yet"),
    );
    expect(screen.getByTestId("bifurcation-territory-line")).toHaveTextContent("no data yet");
    expect(screen.queryByTestId("bifurcation-needle-territory")).not.toBeInTheDocument();
    expect(screen.queryByTestId("bifurcation-needle-fascist")).not.toBeInTheDocument();
  });

  it("shows a loud error for the fascist-alignment source on a failed field_state fetch, independent of the territory source", async () => {
    seedTerritories([makeTerritory({ id: "t1", bifurcation_score: -0.6, population: 10 })]);
    server.use(
      http.get("/api/games/:id/field_state/", () =>
        HttpResponse.json({ status: "error", message: "Field state unavailable" }, { status: 500 }),
      ),
    );

    render(<BifurcationGauge gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    // The territory source is unaffected by the field_state fetch failing —
    // fascist_alignment may legitimately be unavailable while bifurcation_score isn't.
    expect(screen.getByTestId("bifurcation-territory-line")).toHaveTextContent("-0.60");
  });

  it("mounts collapsed/expanded via the ui.chrome.bifurcationOpen toggle", async () => {
    render(<BifurcationGauge gameId={DEFAULT_GAME_ID} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "true");

    await userEvent.click(button);
    expect(useStore.getState().ui.chrome.bifurcationOpen).toBe(false);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});

describe("aggregateBifurcationScore", () => {
  it("population-weights across territories carrying a real score", () => {
    const territories = [
      makeTerritory({ bifurcation_score: -1, population: 100 }),
      makeTerritory({ bifurcation_score: 1, population: 300 }),
    ];
    expect(aggregateBifurcationScore(territories)).toBeCloseTo(0.5, 10);
  });

  it("falls back to a plain mean when no territory carries a usable population weight", () => {
    const territories = [
      makeTerritory({ bifurcation_score: -0.5, population: 0 }),
      makeTerritory({ bifurcation_score: 0.5, population: 0 }),
    ];
    expect(aggregateBifurcationScore(territories)).toBeCloseTo(0, 10);
  });

  it("returns null when no territory carries a real score (never a fabricated zero)", () => {
    const territories = [makeTerritory({ bifurcation_score: null })];
    expect(aggregateBifurcationScore(territories)).toBeNull();
  });

  it("ignores territories with no score while still weighting the ones that have one", () => {
    const territories = [
      makeTerritory({ bifurcation_score: null, population: 1000 }),
      makeTerritory({ bifurcation_score: 0.4, population: 50 }),
    ];
    expect(aggregateBifurcationScore(territories)).toBeCloseTo(0.4, 10);
  });
});

describe("aggregateFascistAlignment", () => {
  it("plain-means fascist_alignment across nodes that carry it", () => {
    const nodes = [
      makeFieldStateNode({ fascist_alignment: 0.2 }),
      makeFieldStateNode({ fascist_alignment: 0.6 }),
    ];
    expect(aggregateFascistAlignment(nodes)).toBeCloseTo(0.4, 10);
  });

  it("returns null when no node carries fascist_alignment", () => {
    expect(aggregateFascistAlignment([makeFieldStateNode()])).toBeNull();
  });
});
