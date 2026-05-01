import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { renderWithProviders } from "../../test/render";
import { ActionPage } from "@/components/ActionPage";
import { resetMockState } from "../../test/handlers";
import { server } from "../../test/server";
import { http, HttpResponse } from "msw";

describe("ActionPage contract parity", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("renders form, loads targets, and submits payload matching schema", async () => {
    const user = userEvent.setup();
    let submittedPayload: Record<string, unknown> | null = null;

    // Intercept the POST request to verify the payload
    server.use(
      http.post("/api/games/:id/actions/educate/", async ({ request }) => {
        submittedPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ status: "ok" });
      }),
    );

    renderWithProviders(
      <MemoryRouter initialEntries={["/games/wayne-county-001/actions/educate"]}>
        <Routes>
          <Route
            path="/games/:id/actions/:verb"
            element={<ActionPage username="testuser" onLogout={() => {}} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    // Wait for the form to load orgs and targets
    expect(await screen.findByText(/Action: educate/i)).toBeInTheDocument();

    // Check if player orgs loaded
    const orgSelect = await screen.findByRole("combobox", { name: /select organization/i });
    expect(orgSelect).toBeInTheDocument();

    // Check if targets loaded
    await waitFor(() => {
      expect(
        screen.getByRole("combobox", { name: /select target territory/i }),
      ).toBeInTheDocument();
    });

    // The fixture contains 'Downtown Detroit' and 'Dearborn Assembly'
    await waitFor(() => {
      expect(screen.getByText(/Downtown Detroit/)).toBeInTheDocument();
    });

    // Submit form with auto-selected first target (comm-1)
    const submitButton = screen.getByRole("button", { name: /submit action/i });
    await user.click(submitButton);

    // Verify payload contract structure
    await waitFor(() => {
      expect(submittedPayload).not.toBeNull();
    });

    // Payload must contain org_id, target_id, target_community_id
    expect(submittedPayload).toHaveProperty("org_id", "org-player-1");
    expect(submittedPayload).toHaveProperty("target_id");
    expect(submittedPayload).toHaveProperty("target_community_id");
    expect(submittedPayload).toHaveProperty("params");
    // Auto-selected first target (comm-1)
    expect(submittedPayload!.target_community_id).toBe(submittedPayload!.target_id);
  });
});
