/**
 * Unit tests for the HexInspector component.
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

  it("shows classification section", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    expect(screen.getByText("Sector")).toBeInTheDocument();
    expect(screen.getByText("INDUSTRIAL")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("URBAN")).toBeInTheDocument();
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

  it("shows connected edges", () => {
    render(<HexInspector snapshot={snapshot} hexId="territory-downtown" />);
    // The TENANCY edge connects to territory-downtown
    expect(screen.getByText(/Edges/)).toBeInTheDocument();
    expect(screen.getByText("TENANCY")).toBeInTheDocument();
  });

  it("shows unknown territory message for invalid ID", () => {
    render(<HexInspector snapshot={snapshot} hexId="nonexistent" />);
    expect(screen.getByText(/Unknown territory/)).toBeInTheDocument();
  });

  it("shows occupant when present", () => {
    const snap = makeSnapshot({
      territories: [
        makeTerritory({
          host_id: "entity-proletariat",
          occupant_id: "entity-bourgeoisie",
        }),
      ],
    });
    render(<HexInspector snapshot={snap} hexId="territory-downtown" />);
    expect(screen.getByText("Host")).toBeInTheDocument();
    expect(screen.getByText("Proletariat")).toBeInTheDocument();
    expect(screen.getByText("Occupant")).toBeInTheDocument();
    expect(screen.getByText("Bourgeoisie")).toBeInTheDocument();
  });
});
