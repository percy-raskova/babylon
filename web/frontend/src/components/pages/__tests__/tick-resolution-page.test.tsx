/**
 * Tests for TickResolutionPage (spec 092).
 *
 * Snapshot events come from the seeded Zustand gameStore (useGameState);
 * the "STATE RESPONSE" step comes from useAlerts, MSW-backed by the
 * fixture in test/handlers.ts (2 non-informational alerts, always present
 * regardless of :id — see `journal-alerts-contract.test.tsx`). Real timers
 * throughout — the component's 1100ms auto-advance is real `setTimeout`,
 * and mixing that with fake timers deadlocks testing-library's `waitFor`
 * polling (which also runs on the timer clock).
 */

import { describe, it, expect, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { TickResolutionPage } from "@/components/pages/TickResolutionPage";
import { makeSnapshot, makeEvent } from "@/test/fixtures";
import { server } from "@/test/server";

const STEP_DELAY_MS = 1100;

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/games/g1/resolution"]}>
      <Routes>
        <Route path="/games/:id/resolution" element={<TickResolutionPage />} />
        <Route path="/games/:id" element={<div>Briefing landing</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  resetGameStore();
});

describe("TickResolutionPage", () => {
  it("shows the resolving-tick header with prev → current tick", () => {
    seedGameStore(makeSnapshot({ tick: 42, events: [makeEvent({ type: "RUPTURE", tick: 42 })] }));
    renderPage();

    expect(screen.getByText(/Resolving Tick 0041 → 0042/)).toBeInTheDocument();
  });

  it("reveals the first severity step immediately, not the state-response step", async () => {
    seedGameStore(
      makeSnapshot({
        tick: 5,
        events: [makeEvent({ type: "RUPTURE", tick: 5, body: "Critical rupture line" })],
      }),
    );
    renderPage();

    expect(await screen.findByText(/Critical rupture line/)).toBeInTheDocument();
    expect(screen.queryByText("STATE RESPONSE")).not.toBeInTheDocument();
    // Not done yet — Continue button withheld until the last step reveals.
    expect(screen.queryByText(/Continue/)).not.toBeInTheDocument();
  }, 10000);

  it("auto-advances to the state-response step and shows Continue", async () => {
    seedGameStore(
      makeSnapshot({
        tick: 5,
        events: [makeEvent({ type: "RUPTURE", tick: 5, body: "Critical rupture line" })],
      }),
    );
    renderPage();
    await screen.findByText(/Critical rupture line/);

    expect(
      await screen.findByText("STATE RESPONSE", {}, { timeout: STEP_DELAY_MS + 2000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Continue/)).toBeInTheDocument();
  }, 10000);

  it("Continue navigates back to the Briefing route", async () => {
    seedGameStore(
      makeSnapshot({
        tick: 5,
        events: [makeEvent({ type: "RUPTURE", tick: 5, body: "Critical rupture line" })],
      }),
    );
    renderPage();
    await screen.findByText(/Critical rupture line/);

    const continueBtn = await screen.findByText(/Continue/, {}, { timeout: STEP_DELAY_MS + 2000 });
    fireEvent.click(continueBtn);

    expect(await screen.findByText("Briefing landing")).toBeInTheDocument();
  }, 10000);

  it("shows 'no changes' state when the tick had no events and no alerts", async () => {
    server.use(
      http.get("/api/games/:id/alerts/", () =>
        HttpResponse.json({ status: "ok", data: { alerts: [] } }),
      ),
    );
    seedGameStore(makeSnapshot({ tick: 5, events: [] }));
    renderPage();

    expect(await screen.findByText(/No changes recorded this tick/)).toBeInTheDocument();
    expect(screen.getByText(/Continue/)).toBeInTheDocument();
  });
});
