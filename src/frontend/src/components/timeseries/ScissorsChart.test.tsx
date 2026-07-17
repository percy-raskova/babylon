import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { ScissorsChart } from "./ScissorsChart";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeTimeseriesPayload } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("ScissorsChart", () => {
  it("renders the chart once real /timeseries/ data loads", async () => {
    render(<ScissorsChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(screen.getByTestId("scissors-chart")).toBeInTheDocument());
  });

  it("shows the honest empty state when the market axis never computed", async () => {
    server.use(
      http.get("/api/games/:id/timeseries/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeTimeseriesPayload({
            price_index: [null, null],
            fictitious_ratio: [null, null],
          }),
        }),
      ),
    );
    render(<ScissorsChart gameId={DEFAULT_GAME_ID} />);
    await waitFor(() =>
      expect(
        screen.getByText("No market axis yet — the phenomenal form awaits its substance."),
      ).toBeInTheDocument(),
    );
  });
});
