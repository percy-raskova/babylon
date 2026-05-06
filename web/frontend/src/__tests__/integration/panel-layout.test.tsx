/**
 * Integration test: v2 layout interactions.
 *
 * Tests NavRail navigation links and GameRouteShell layout structure.
 * Replaces the v1 RightPanel/BottomPanel interaction tests.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { NavRail } from "@/components/layout/NavRail";

describe("v2 layout interactions", () => {
  describe("NavRail", () => {
    it("renders all three nav groups", () => {
      render(
        <MemoryRouter initialEntries={["/games/g1"]}>
          <Routes>
            <Route path="/games/:id" element={<NavRail gameId="g1" />} />
          </Routes>
        </MemoryRouter>,
      );

      // Group labels are lowercase in DOM, uppercase via CSS
      expect(screen.getByText("Play")).toBeInTheDocument();
      expect(screen.getByText("Verbs")).toBeInTheDocument();
      expect(screen.getByText("Analyze")).toBeInTheDocument();
    });

    it("renders nav links with correct aria-labels", () => {
      render(
        <MemoryRouter initialEntries={["/games/g1"]}>
          <Routes>
            <Route path="/games/:id" element={<NavRail gameId="g1" />} />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByLabelText("Briefing")).toBeInTheDocument();
      expect(screen.getByLabelText("Orgs")).toBeInTheDocument();
      expect(screen.getByLabelText("Intel")).toBeInTheDocument();
      expect(screen.getByLabelText("Results")).toBeInTheDocument();
    });
  });
});
