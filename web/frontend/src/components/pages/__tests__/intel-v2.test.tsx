/**
 * Tests for IntelPage — 4-variant inspector.
 *
 * RED-first: defines expected behavior for org, territory, edge, community variants.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { IntelPageV2 } from "@/components/pages/IntelPageV2";

function renderIntel(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/games/:id/intel" element={<IntelPageV2 />} />
        <Route path="/games/:id/intel/:targetType/:targetId" element={<IntelPageV2 />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("IntelPageV2", () => {
  // --- Index view ---
  it("renders the Intel page heading", () => {
    renderIntel("/games/g1/intel");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Intel");
  });

  it("renders category tabs", () => {
    renderIntel("/games/g1/intel");
    expect(screen.getByText(/Territories/)).toBeInTheDocument();
    expect(screen.getByText(/Orgs/)).toBeInTheDocument();
    expect(screen.getByText(/Edges/)).toBeInTheDocument();
    expect(screen.getByText(/Communities/)).toBeInTheDocument();
  });

  it("shows entity list in the surveillance index", () => {
    renderIntel("/games/g1/intel");
    // Default tab should show some entity names
    expect(screen.getAllByRole("button").length).toBeGreaterThan(4);
  });

  // --- Org variant ---
  it("renders org detail when org target selected", () => {
    renderIntel("/games/g1/intel/org/org-dted");
    expect(screen.getByText("DTED")).toBeInTheDocument();
  });

  it("shows org stats grid for enemy org", () => {
    renderIntel("/games/g1/intel/org/org-dted");
    expect(screen.getAllByText(/Cohesion/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Opacity/i).length).toBeGreaterThanOrEqual(1);
  });

  // --- Territory variant ---
  it("renders territory detail when territory target selected", () => {
    renderIntel("/games/g1/intel/territory/terr-hamtramck");
    expect(screen.getAllByText("Hamtramck").length).toBeGreaterThanOrEqual(1);
  });

  it("shows territory stats grid", () => {
    renderIntel("/games/g1/intel/territory/terr-hamtramck");
    expect(screen.getAllByText(/Heat/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Rent/i).length).toBeGreaterThanOrEqual(1);
  });

  // --- Edge variant ---
  it("renders edge detail when edge target selected", () => {
    renderIntel("/games/g1/intel/edge/edge-1");
    expect(screen.getAllByText("ANTAGONISTIC").length).toBeGreaterThanOrEqual(1);
  });

  // --- Community variant ---
  it("renders community detail when community target selected", () => {
    renderIntel("/games/g1/intel/community/hx-tenants");
    expect(screen.getAllByText("Hamtramck Tenants Union").length).toBeGreaterThanOrEqual(1);
  });

  it("shows community composition badges", () => {
    renderIntel("/games/g1/intel/community/hx-tenants");
    expect(screen.getByText("rent_burden")).toBeInTheDocument();
  });
});
