/**
 * Component/flow tests for the Observatory dashboard (spec-096).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import ObservatoryPage from "../ObservatoryPage";
import { SessionPicker } from "../SessionPicker";
import { ObservatoryChart } from "../ObservatoryChart";
import type { ObservatorySession, ValueAggregatePoint } from "../types";

const SID = "bc680a68-0000-4000-8000-000000000000";

function makeSession(overrides: Partial<ObservatorySession> = {}): ObservatorySession {
  return {
    session_id: SID,
    min_tick: 0,
    max_tick: 3,
    tick_count: 4,
    checkpoint_count: 1,
    latest_hash: "a".repeat(64),
    scenario: "wayne_county",
    status: "active",
    created_at: null,
    ...overrides,
  };
}

const POINTS: ValueAggregatePoint[] = [
  { tick: 0, c_sum: 10, v_sum: 5, s_sum: 3, k_sum: 100, biocapacity_sum: 20, hex_count: 2 },
  { tick: 1, c_sum: 11, v_sum: 6, s_sum: 4, k_sum: 110, biocapacity_sum: 21, hex_count: 2 },
];

describe("ObservatoryPage gating", () => {
  it("shows the disabled state when status 404s", async () => {
    server.use(
      http.get("/api/observatory/status/", () => new HttpResponse("Not Found", { status: 404 })),
    );
    render(<ObservatoryPage />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/disabled or unavailable/i),
    );
  });

  it("lists sessions when enabled", async () => {
    server.use(
      http.get("/api/observatory/status/", () =>
        HttpResponse.json({ status: "ok", data: { enabled: true, sim_alias: "sim" } }),
      ),
      http.get("/api/observatory/sessions/", () =>
        HttpResponse.json({ status: "ok", data: [makeSession()] }),
      ),
    );
    render(<ObservatoryPage />);
    await waitFor(() => expect(screen.getByTestId("session-list")).toBeInTheDocument());
    expect(screen.getByText(SID)).toBeInTheDocument();
  });

  it("selecting a session opens the series browser and plots a chart", async () => {
    server.use(
      http.get("/api/observatory/status/", () =>
        HttpResponse.json({ status: "ok", data: { enabled: true, sim_alias: "sim" } }),
      ),
      http.get("/api/observatory/sessions/", () =>
        HttpResponse.json({ status: "ok", data: [makeSession()] }),
      ),
      http.get(`/api/observatory/sessions/${SID}/series/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            scope: "national",
            scope_id: "USA",
            from_tick: 0,
            to_tick: 1,
            points: POINTS,
          },
        }),
      ),
    );
    render(<ObservatoryPage />);
    await waitFor(() => expect(screen.getByText(SID)).toBeInTheDocument());
    await userEvent.click(screen.getByText(SID));
    await waitFor(() => expect(screen.getByTestId("observatory-chart")).toBeInTheDocument());
    // Back navigation returns to the picker.
    await userEvent.click(screen.getByText(/sessions/i));
    await waitFor(() => expect(screen.getByTestId("session-list")).toBeInTheDocument());
  });
});

describe("SessionPicker", () => {
  it("renders an empty state with no sessions", () => {
    render(<SessionPicker sessions={[]} onSelect={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent(/no simulation sessions/i);
  });

  it("invokes onSelect when a session is clicked", async () => {
    const onSelect = vi.fn();
    render(<SessionPicker sessions={[makeSession()]} onSelect={onSelect} />);
    await userEvent.click(screen.getByText(SID));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});

describe("ObservatoryChart", () => {
  it("renders an empty state when there are no points", () => {
    render(<ObservatoryChart points={[]} metrics={["v_sum"]} />);
    expect(screen.getByRole("status")).toHaveTextContent(/no data/i);
  });

  it("renders a chart container when points are present", () => {
    render(<ObservatoryChart points={POINTS} metrics={["v_sum", "s_sum"]} />);
    expect(screen.getByTestId("observatory-chart")).toBeInTheDocument();
  });
});
