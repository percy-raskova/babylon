/**
 * Red-first tests for OrgDetailView (spec 093 US2).
 *
 * Ported from `design/mockups/ui_kits/webapp/OrgDetail.jsx`'s layout onto
 * live GameSnapshot data: vanguard economy stats, OODA phase, a relations
 * list derived from real edge `mode` (not a random label), org-scoped
 * events — every numeric stat wrapped in `BreakdownTooltip`.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { seedGameStore, resetGameStore, SEEDED_SNAPSHOT } from "@/__tests__/helpers/seedSnapshot";
import { render, screen } from "@testing-library/react";
import { OrgDetailView } from "@/components/intel/OrgDetailView";
import type { EdgeState } from "@/types/game";

const org = SEEDED_SNAPSHOT.organizations[0]!;
const otherOrg = SEEDED_SNAPSHOT.organizations[1]!;

const edges: EdgeState[] = [
  {
    id: "edge-1",
    source_id: org.id,
    target_id: otherOrg.id,
    mode: "ANTAGONISTIC",
    value_flow: 0,
    tension: 0.6,
    repression_flow: 0.1,
  },
];

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("OrgDetailView", () => {
  it("renders the org name and type", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={edges} />);
    expect(
      screen.getAllByText(new RegExp(org.short_name ?? org.name)).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("renders vanguard economy stats (cadre labor, sympathizer labor, reputation, heat)", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={edges} />);
    for (const label of [/Cadre Labor/i, /Sympathizer Labor/i, /Reputation/i, /Heat/i]) {
      expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("renders the OODA phase", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={edges} />);
    expect(screen.getByText(new RegExp(org.ooda.phase ?? "observe", "i"))).toBeInTheDocument();
  });

  it("lists relations derived from real edge mode, not a hardcoded label", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={edges} />);
    expect(screen.getByText(/antagonistic/i)).toBeInTheDocument();
  });

  it("shows an explicit empty relations state when no edges reference this org", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={[]} />);
    expect(screen.getByText(/no known relations/i)).toBeInTheDocument();
  });

  it("wraps numeric stats in a BreakdownTooltip trigger", () => {
    render(<OrgDetailView org={org} snapshot={SEEDED_SNAPSHOT} edges={edges} />);
    expect(screen.getByLabelText(/Breakdown for Cadre Labor/i)).toBeInTheDocument();
  });
});
