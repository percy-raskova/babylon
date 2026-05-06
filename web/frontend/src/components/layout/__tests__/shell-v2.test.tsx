/**
 * Tests for the v2 shell components — NavRail, PageHeader, GameRouteShell.
 *
 * Written RED-first: these define the expected behavior of the shell
 * before implementation.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

// Components under test
import { NavRail } from "@/components/layout/NavRail";
import { PageHeader } from "@/components/layout/PageHeader";

// ---------------------------------------------------------------------------
// NavRail
// ---------------------------------------------------------------------------
describe("NavRail", () => {
  function renderInRouter(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="*" element={<NavRail gameId="g1" />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("renders the PLAY group navigation items", () => {
    renderInRouter("/games/g1");
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    // Core nav items should be present
    expect(screen.getByLabelText("Briefing")).toBeInTheDocument();
    expect(screen.getByLabelText("Orgs")).toBeInTheDocument();
    expect(screen.getByLabelText("Intel")).toBeInTheDocument();
    expect(screen.getByLabelText("Results")).toBeInTheDocument();
  });

  it("renders all 9 verb shortcuts", () => {
    renderInRouter("/games/g1");
    expect(screen.getByLabelText("Educate")).toBeInTheDocument();
    expect(screen.getByLabelText("Mobilize")).toBeInTheDocument();
    expect(screen.getByLabelText("Campaign")).toBeInTheDocument();
    expect(screen.getByLabelText("Aid")).toBeInTheDocument();
    expect(screen.getByLabelText("Attack")).toBeInTheDocument();
    expect(screen.getByLabelText("Move")).toBeInTheDocument();
    expect(screen.getByLabelText("Investigate")).toBeInTheDocument();
    expect(screen.getByLabelText("Reproduce")).toBeInTheDocument();
    expect(screen.getByLabelText("Negotiate")).toBeInTheDocument();
  });

  it("highlights the active route", () => {
    renderInRouter("/games/g1/orgs");
    const orgsLink = screen.getByLabelText("Orgs");
    // Active item should have active styling (gold border or text)
    expect(orgsLink.closest("a")?.getAttribute("aria-current")).toBe("page");
  });
});

// ---------------------------------------------------------------------------
// PageHeader
// ---------------------------------------------------------------------------
describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Briefing" />);
    expect(screen.getByText("Briefing")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<PageHeader title="Test" subtitle="Subtitle text" />);
    expect(screen.getByText("Subtitle text")).toBeInTheDocument();
  });

  it("renders breadcrumbs", () => {
    render(<PageHeader title="Test" breadcrumbs={["Operation", "Actions", "Educate"]} />);
    expect(screen.getByText("Operation")).toBeInTheDocument();
    expect(screen.getByText("Educate")).toBeInTheDocument();
  });

  it("renders right slot content", () => {
    render(<PageHeader title="Test" right={<span data-testid="right">Badge</span>} />);
    expect(screen.getByTestId("right")).toBeInTheDocument();
  });
});
