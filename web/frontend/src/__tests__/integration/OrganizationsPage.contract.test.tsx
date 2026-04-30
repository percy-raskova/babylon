import { describe, it, expect, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { renderWithProviders } from "../../test/render";
import { OrganizationsPage } from "@/components/OrganizationsPage";
import { resetMockState } from "../../test/handlers";

describe("OrganizationsPage contract parity", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("renders organizations from API mock properly", async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={["/games/wayne-county-001/orgs"]}>
        <Routes>
          <Route
            path="/games/:id/orgs"
            element={<OrganizationsPage username="testuser" onLogout={() => {}} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    // Wait for the organizations to load
    const title = await screen.findByText("Player Organizations");
    expect(title).toBeInTheDocument();

    // The fixture contains 'Wayne County Tenant Union', 'Detroit Workers Council', and 'Mutual Aid Detroit'
    expect(await screen.findByText("Wayne County Tenant Union")).toBeInTheDocument();
    expect(await screen.findByText("Detroit Workers Council")).toBeInTheDocument();
    expect(await screen.findByText("Mutual Aid Detroit")).toBeInTheDocument();

    // Verify some values to ensure schema parity is matched
    expect(screen.getAllByText("civil_society_org").length).toBeGreaterThan(0);
    expect(screen.getByText("political_faction")).toBeInTheDocument();
  });
});
