import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { SurvivalDuelPanel } from "./SurvivalDuelPanel";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeClassHistoryPayload, makeClassHistoryPoint, makeEvent } from "@/test/fixtures";

const CLASS_ID = "C002";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("SurvivalDuelPanel", () => {
  it("renders the sparkline once real history loads", async () => {
    server.use(
      http.get("/api/games/:id/node/:entityId/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeClassHistoryPayload({
            class_id: CLASS_ID,
            history: [
              makeClassHistoryPoint({ tick: 0 }),
              makeClassHistoryPoint({ tick: 1, p_acquiescence: 0.5, p_revolution: 0.4 }),
            ],
          }),
        }),
      ),
    );
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() => expect(screen.getByTestId("duel-sparkline")).toBeInTheDocument());
  });

  it("shows an honest empty state when the class has no history yet", async () => {
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() => expect(screen.getByTestId("duel-sparkline-empty")).toBeInTheDocument());
  });

  it("shows a loud error on a failed history fetch", async () => {
    server.use(
      http.get("/api/games/:id/node/:entityId/history/", () =>
        HttpResponse.json({ status: "error", message: "History unavailable" }, { status: 500 }),
      ),
    );
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() => expect(screen.getByTestId("survival-duel-error")).toBeInTheDocument());
  });

  it("renders a rupture marker from the history payload's server-filtered ruptures", async () => {
    server.use(
      http.get("/api/games/:id/node/:entityId/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeClassHistoryPayload({
            class_id: CLASS_ID,
            history: [makeClassHistoryPoint({ tick: 3 })],
            ruptures: [
              makeEvent({
                id: "evt-uprising-1",
                type: "uprising",
                tick: 3,
                data: { node_id: CLASS_ID, trigger: "revolutionary_pressure" },
              }),
            ],
          }),
        }),
      ),
    );
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("duel-sparkline-marker-evt-uprising-1")).toBeInTheDocument(),
    );
  });

  it("defense-in-depth: drops a rupture row belonging to a different class", async () => {
    // The server already filters by node; the client re-applies the owner
    // ruling-3 predicate so a backend regression cannot fabricate a marker.
    server.use(
      http.get("/api/games/:id/node/:entityId/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeClassHistoryPayload({
            class_id: CLASS_ID,
            history: [makeClassHistoryPoint({ tick: 3 })],
            ruptures: [
              makeEvent({
                id: "evt-other-class",
                type: "uprising",
                tick: 3,
                data: { node_id: "C999", trigger: "revolutionary_pressure" },
              }),
            ],
          }),
        }),
      ),
    );
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() => expect(screen.getByTestId("duel-sparkline")).toBeInTheDocument());
    expect(screen.queryByTestId("duel-sparkline-marker-evt-other-class")).not.toBeInTheDocument();
  });

  it("defense-in-depth: drops a spark-triggered UPRISING (revolutionary_pressure only)", async () => {
    server.use(
      http.get("/api/games/:id/node/:entityId/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeClassHistoryPayload({
            class_id: CLASS_ID,
            history: [makeClassHistoryPoint({ tick: 3 })],
            ruptures: [
              makeEvent({
                id: "evt-spark",
                type: "uprising",
                tick: 3,
                data: { node_id: CLASS_ID, trigger: "spark" },
              }),
            ],
          }),
        }),
      ),
    );
    render(<SurvivalDuelPanel gameId={DEFAULT_GAME_ID} classId={CLASS_ID} />);
    await waitFor(() => expect(screen.getByTestId("duel-sparkline")).toBeInTheDocument());
    expect(screen.queryByTestId("duel-sparkline-marker-evt-spark")).not.toBeInTheDocument();
  });
});
