/**
 * FundamentalTheoremMeter tests — Track 2 / T2-6 (spec-117). TDD red phase
 * written before the implementation.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { FundamentalTheoremMeter } from "./FundamentalTheoremMeter";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeEconomyDashboardPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("FundamentalTheoremMeter", () => {
  it("renders the meter once real /economy/ data loads", async () => {
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-meter")).toBeInTheDocument(),
    );
  });

  it("shows Wc/Vc and the signed gap reading", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({
            wage_flow_total: 150,
            value_produced: 100,
            imperial_rent_gap: 50,
          }),
        }),
      ),
    );
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);

    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-narrative")).toHaveTextContent(
        /imperial subsidy/,
      ),
    );
    expect(screen.getByTestId("fundamental-theorem-narrative")).toHaveTextContent("150.0");
    expect(screen.getByTestId("fundamental-theorem-narrative")).toHaveTextContent("100.0");
  });

  it("shows a loud empty state when has_data is false", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({ has_data: false }),
        }),
      ),
    );
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-no-data")).toBeInTheDocument(),
    );
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({ status: "error", message: "Economy unavailable" }, { status: 500 }),
      ),
    );
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Economy unavailable"));
  });

  it("mounts and unmounts the economy panel", async () => {
    const { unmount } = render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.economy.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.economy.mounted).toBe(false);
  });

  it("shows an honest empty region list when no territory has a positive-population tenant", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({ imperial_rent_gap_by_region: [] }),
        }),
      ),
    );
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-regions-empty")).toBeInTheDocument(),
    );
  });

  it("renders the per-region breakdown sorted worst-subsidy-first", async () => {
    server.use(
      http.get("/api/games/:id/economy/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeEconomyDashboardPayload({
            imperial_rent_gap_by_region: [
              {
                territory_id: "T1",
                population: 100,
                wc_per_capita: 0.1,
                vc_per_capita: 0.5,
                gap_per_capita: -0.4,
              },
              {
                territory_id: "T2",
                population: 200,
                wc_per_capita: 0.9,
                vc_per_capita: 0.2,
                gap_per_capita: 0.7,
              },
            ],
          }),
        }),
      ),
    );
    render(<FundamentalTheoremMeter gameId={DEFAULT_GAME_ID} />);

    await waitFor(() =>
      expect(screen.getByTestId("fundamental-theorem-regions")).toBeInTheDocument(),
    );
    const rows = screen.getAllByTestId(/fundamental-theorem-region-/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual([
      "fundamental-theorem-region-T2",
      "fundamental-theorem-region-T1",
    ]);
  });
});
