/**
 * Unit tests for the HexInspector component.
 *
 * Updated for Spec 052: edges use mode, host/occupant lookup against orgs,
 * classification uses new territory fields.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HexInspector } from "./HexInspector";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";

describe("HexInspector", () => {
  const snapshot = makeSnapshot();

  it("renders territory name and profile badge", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    expect(screen.getByText("Downtown")).toBeInTheDocument();
    expect(screen.getByText("HIGH_PROFILE")).toBeInTheDocument();
  });

  it("shows heat and rent level", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    expect(screen.getByText("Heat")).toBeInTheDocument();
    expect(screen.getByText("Rent Level")).toBeInTheDocument();
  });

  it("shows eviction alert when under_eviction is true", () => {
    const snap = makeSnapshot({
      territories: [makeTerritory({ under_eviction: true })],
    });
    render(<HexInspector snapshot={snap} hexId="territory-downtown" />);
    expect(screen.getByText("UNDER EVICTION")).toBeInTheDocument();
  });

  it("does not show eviction alert normally", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    expect(screen.queryByText("UNDER EVICTION")).not.toBeInTheDocument();
  });

  it("shows connected edges with mode", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    // edge-02 connects org-workers-union -> territory-downtown with mode SOLIDARISTIC
    expect(screen.getByText(/Edges/)).toBeInTheDocument();
    expect(screen.getByText("SOLIDARISTIC")).toBeInTheDocument();
  });

  it("shows unknown territory message for invalid ID", () => {
    render(<HexInspector snapshot={snapshot} hexId="nonexistent" />);
    expect(screen.getByText(/Unknown territory/)).toBeInTheDocument();
  });

  it("shows host and occupant when present", () => {
    const snap = makeSnapshot({
      territories: [
        makeTerritory({
          host_id: "org-workers-union",
          occupant_id: "org-finance-bloc",
        }),
      ],
      organizations: [
        {
          id: "org-workers-union",
          name: "Workers Union",
          org_type: "civil_society_org",
          class_character: "proletarian",
          cohesion: 0.75,
          cadre_level: 0.35,
          budget: 15.0,
          heat: 0.3,
          territory_ids: ["territory-downtown"],
          hyperedge_memberships: [],
          consciousness: { liberal: 0.15, fascist: 0.05, revolutionary: 0.8 },
          ooda: { observe: 0.6, orient: 0.5, decide: 0.7, act: 0.8, cycle_ticks: 1 },
        },
        {
          id: "org-finance-bloc",
          name: "Finance Bloc",
          org_type: "business",
          class_character: "bourgeois",
          cohesion: 0.9,
          cadre_level: 0.8,
          budget: 500.0,
          heat: 0.0,
          territory_ids: [],
          hyperedge_memberships: [],
          consciousness: { liberal: 0.7, fascist: 0.2, revolutionary: 0.1 },
          ooda: { observe: 0.8, orient: 0.7, decide: 0.9, act: 0.9, cycle_ticks: 1 },
        },
      ],
    });
    render(<HexInspector snapshot={snap} hexId="territory-downtown" />);
    expect(screen.getByText("Host")).toBeInTheDocument();
    expect(screen.getAllByText("Workers Union").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Occupant")).toBeInTheDocument();
    expect(screen.getAllByText("Finance Bloc").length).toBeGreaterThanOrEqual(1);
  });
});
