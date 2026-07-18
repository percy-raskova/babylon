import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { BriefingRoute } from "./BriefingRoute";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog } from "@/test/handlers";
import { makeObjective, makeObjectivesTracker } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

/** The five real objective ids `get_journal_objectives` emits, at tick 0. */
const FIVE_PATTERNS = makeObjectivesTracker({
  tick: 0,
  objectives: [
    makeObjective({ progress: 0.01 }),
    makeObjective({
      id: "ecological_collapse",
      title: "Ecological Collapse",
      category: "collapse",
      progress: 0.02,
    }),
    makeObjective({
      id: "fascist_consolidation",
      title: "Fascist Consolidation",
      category: "fascist",
      progress: 0.0,
    }),
    makeObjective({ id: "red_ogv", title: "Red OGV Trap", category: "red_ogv", progress: 0.0 }),
    makeObjective({
      id: "fragmented_collapse",
      title: "Fragmented Collapse",
      category: "fragmented",
      progress: 0.0,
    }),
  ],
});

function renderBriefing(): void {
  render(
    <MemoryRouter initialEntries={["/game/game-001/briefing"]}>
      <Routes>
        <Route path="/game/:id/briefing" element={<BriefingRoute />} />
        <Route path="/game/:id" element={<div>GAME SHELL</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BriefingRoute", () => {
  it("renders the operation codename, scenario, and fixed-horizon stakes", async () => {
    renderBriefing();
    await waitFor(() =>
      expect(screen.getByTestId("briefing-codename")).toHaveTextContent(
        "OPERATION CRIMSON HARVEST",
      ),
    );
    expect(screen.getByText("Wayne County Organizer")).toBeInTheDocument();
    // Owner ruling 2026-07-17: 100-year fixed horizon, patterns not terminators.
    expect(screen.getByTestId("briefing-horizon").textContent).toContain("100 years");
    expect(screen.getByTestId("briefing-horizon").textContent).toContain("5,200");
  });

  it("lists all five patterns from the real objectives payload, win condition named", async () => {
    server.use(
      http.get("/api/games/:id/objectives/", () =>
        HttpResponse.json({ status: "ok", data: FIVE_PATTERNS }),
      ),
    );
    renderBriefing();
    await waitFor(() => expect(screen.getAllByTestId(/^briefing-pattern-/)).toHaveLength(5));

    const revolution = screen.getByTestId("briefing-pattern-revolution");
    expect(within(revolution).getByTestId("briefing-win-badge")).toBeInTheDocument();
    expect(within(revolution).getByText("Revolutionary Victory")).toBeInTheDocument();
    // Only the win condition carries the badge.
    expect(screen.getAllByTestId("briefing-win-badge")).toHaveLength(1);
  });

  it("Begin Operation hands off to the cockpit — and no heartbeat ran before it", async () => {
    renderBriefing();
    await waitFor(() => expect(screen.getByTestId("briefing-begin")).toBeInTheDocument());
    // The briefing must not start GameRoute's polling machinery (recon gotcha).
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(0);

    await userEvent.click(screen.getByTestId("briefing-begin"));

    expect(screen.getByText("GAME SHELL")).toBeInTheDocument();
  });
});
