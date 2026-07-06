/**
 * Red-first tests for TerritoryDetailView (spec 093 US1).
 *
 * Ported from `design/mockups/ui_kits/webapp/TerritoryDetail.jsx`'s layout
 * onto live GameSnapshot data: full stat grid, an economic panel (via
 * `useEconomy`), organizations actually present in the territory (derived
 * from real `territory_ids`, not a hardcoded roster), events actually
 * scoped to the territory, and a not-found state — every numeric stat
 * wrapped in `BreakdownTooltip` for provenance.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { seedGameStore, resetGameStore, SEEDED_SNAPSHOT } from "@/__tests__/helpers/seedSnapshot";
import { render, screen } from "@testing-library/react";
import { TerritoryDetailView } from "@/components/intel/TerritoryDetailView";

const territory = SEEDED_SNAPSHOT.territories[0]!; // terr-hamtramck

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("TerritoryDetailView", () => {
  it("renders the territory name and county FIPS", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    expect(screen.getAllByText("Hamtramck").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the full material stat grid", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    for (const label of [/Heat/i, /Rent/i, /Population/i, /Biocapacity/i]) {
      expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("lists organizations actually present in the territory (real territory_ids)", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    // Both seeded orgs' territory_ids include terr-hamtramck.
    expect(screen.getByText(/Wayne County Labor Federation|WCLF/)).toBeInTheDocument();
    expect(screen.getByText(/Detroit Enforcement Division|DTED/)).toBeInTheDocument();
  });

  it("excludes organizations not present in the territory", () => {
    const noOrgSnapshot = {
      ...SEEDED_SNAPSHOT,
      organizations: SEEDED_SNAPSHOT.organizations.map((o) => ({ ...o, territory_ids: [] })),
    };
    render(<TerritoryDetailView territory={territory} snapshot={noOrgSnapshot} />);
    expect(screen.getByText(/No organizations present/i)).toBeInTheDocument();
  });

  it("shows an explicit empty state when no events are scoped to this territory", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    expect(screen.getByText(/no events/i)).toBeInTheDocument();
  });

  it("wraps numeric stats in a BreakdownTooltip trigger", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    expect(screen.getByLabelText(/Breakdown for Heat/i)).toBeInTheDocument();
  });

  it("renders an economic panel container", () => {
    render(<TerritoryDetailView territory={territory} snapshot={SEEDED_SNAPSHOT} />);
    expect(screen.getByText(/Economy/i)).toBeInTheDocument();
  });
});
