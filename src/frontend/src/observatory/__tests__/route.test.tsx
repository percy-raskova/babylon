/**
 * Smoke test for the standalone `ObservatoryRoute` module (spec-111 port).
 *
 * Verifies the route mounts and lazily renders `ObservatoryPage` without
 * any App.tsx/routes registration — the orchestrator wires the one-line
 * `<Route>` separately (route-registration discipline for this wave).
 */

import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { ObservatoryRoute } from "../ObservatoryRoute";

describe("ObservatoryRoute", () => {
  it("lazily mounts ObservatoryPage and shows the disabled state when the flag is off", async () => {
    server.use(
      http.get("/api/observatory/status/", () => new HttpResponse("Not Found", { status: 404 })),
    );
    render(
      <MemoryRouter initialEntries={["/observatory"]}>
        <Routes>
          <Route path="/observatory/*" element={<ObservatoryRoute />} />
        </Routes>
      </MemoryRouter>,
    );
    // Generous timeout: this exercises the real `React.lazy()` chunk import
    // (ObservatoryRoute -> ObservatoryPage) on top of the status fetch, which
    // can be slow under parallel CI/agent load — the default 1s waitFor
    // window flaked here while other observatory tests (which mount
    // ObservatoryPage directly, skipping the lazy import) did not.
    await waitFor(
      () => expect(screen.getByRole("alert")).toHaveTextContent(/disabled or unavailable/i),
      { timeout: 5000 },
    );
  });

  it("renders the session list once the backend reports the flag enabled", async () => {
    server.use(
      http.get("/api/observatory/status/", () =>
        HttpResponse.json({ status: "ok", data: { enabled: true, sim_alias: "sim" } }),
      ),
      http.get("/api/observatory/sessions/", () =>
        HttpResponse.json({
          status: "ok",
          data: [
            {
              session_id: "bc680a68-0000-4000-8000-000000000000",
              min_tick: 0,
              max_tick: 3,
              tick_count: 4,
              checkpoint_count: 1,
              latest_hash: "a".repeat(64),
              scenario: "wayne_county",
              status: "active",
              created_at: null,
            },
          ],
        }),
      ),
    );
    render(
      <MemoryRouter initialEntries={["/observatory"]}>
        <Routes>
          <Route path="/observatory/*" element={<ObservatoryRoute />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("session-list")).toBeInTheDocument(), {
      timeout: 5000,
    });
  });
});
