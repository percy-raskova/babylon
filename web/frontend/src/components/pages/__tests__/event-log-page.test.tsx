/**
 * Tests for EventLogPage (spec 092).
 *
 * MSW-backed — useJournal fetches /api/games/:id/journal/ (mocked in
 * test/handlers.ts) rather than reading from the Zustand gameStore.
 *
 * Fixture types (RUPTURE/UPRISING/VALUE_TRANSFER) are chosen to hit all
 * three `lib/eventClassifier.ts` severity tiers (critical/important/
 * informational respectively) so the filter buttons have something real
 * to demonstrate against.
 */

import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { EventLogPage } from "@/components/pages/EventLogPage";
import { server } from "@/test/server";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/games/wayne-county-001/log"]}>
      <Routes>
        <Route path="/games/:id/log" element={<EventLogPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("EventLogPage", () => {
  it("renders the Event Log heading", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Event Log");
  });

  it("renders events fetched from the journal endpoint", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Contradiction rupture threshold crossed/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Workers rose up in Hamtramck/)).toBeInTheDocument();
    expect(screen.getByText(/Wages paid to proletariat/)).toBeInTheDocument();
  });

  it("filters events by critical severity", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Contradiction rupture threshold crossed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "critical" }));

    expect(screen.getByText(/Contradiction rupture threshold crossed/)).toBeInTheDocument();
    expect(screen.queryByText(/Workers rose up in Hamtramck/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Wages paid to proletariat/)).not.toBeInTheDocument();
  });

  it("filters events by important severity", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Workers rose up in Hamtramck/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "important" }));

    expect(screen.getByText(/Workers rose up in Hamtramck/)).toBeInTheDocument();
    expect(screen.queryByText(/Contradiction rupture threshold crossed/)).not.toBeInTheDocument();
  });

  it("filters events by informational severity", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Contradiction rupture threshold crossed/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "informational" }));
    expect(screen.getByText(/Wages paid to proletariat/)).toBeInTheDocument();
    expect(screen.queryByText(/Contradiction rupture threshold crossed/)).not.toBeInTheDocument();
  });

  it("shows empty state when the journal has no events", async () => {
    server.use(
      http.get("/api/games/:id/journal/", () =>
        HttpResponse.json({ status: "ok", data: { events: [] } }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No events recorded yet/)).toBeInTheDocument();
    });
  });
});
