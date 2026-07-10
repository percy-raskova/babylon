import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { TimeseriesChart } from "./TimeseriesChart";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeTimeseriesPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("TimeseriesChart", () => {
  it("renders the chart once real /timeseries/ data loads", async () => {
    render(<TimeseriesChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("timeseries-chart")).toBeInTheDocument());
  });

  it("shows a loud empty state when the payload has no ticks", async () => {
    server.use(
      http.get("/api/games/:id/timeseries/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeTimeseriesPayload({
            ticks: [],
            imperial_rent: [],
            consciousness: [],
            solidarity: [],
            heat: [],
            wealth: [],
            biocapacity: [],
          }),
        }),
      ),
    );
    render(<TimeseriesChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByText("No timeseries data yet.")).toBeInTheDocument());
  });

  it("shows a loud error on a failed fetch", async () => {
    server.use(
      http.get("/api/games/:id/timeseries/", () =>
        HttpResponse.json({ status: "error", message: "Timeseries unavailable" }, { status: 500 }),
      ),
    );
    render(<TimeseriesChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Timeseries unavailable"),
    );
  });

  it("mounts and unmounts the timeseries panel", async () => {
    const { unmount } = render(<TimeseriesChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.timeseries.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.timeseries.mounted).toBe(false);
  });
});
