/**
 * Unit tests for the NodeInspector component.
 *
 * Updated for Spec 052: entity views removed. Orgs have consciousness
 * 3-vectors and OODA profiles. Institutions have factional_composition.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NodeInspector } from "./NodeInspector";
import { makeSnapshot } from "@/test/fixtures";

describe("NodeInspector", () => {
  const snapshot = makeSnapshot();

  describe("organization view", () => {
    it("shows org name and type", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("Workers Union")).toBeInTheDocument();
      expect(screen.getByText("civil_society_org")).toBeInTheDocument();
    });

    it("shows capacity metrics", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("Budget")).toBeInTheDocument();
      expect(screen.getByText("Cohesion")).toBeInTheDocument();
      expect(screen.getByText("Cadre Level")).toBeInTheDocument();
    });

    it("shows consciousness 3-vector", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("Revolutionary")).toBeInTheDocument();
      expect(screen.getByText("Liberal")).toBeInTheDocument();
      expect(screen.getByText("Fascist")).toBeInTheDocument();
    });

    it("shows territories as clickable rows with resolved names", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      // Territories now show resolved name instead of raw ID
      expect(screen.getByText("Downtown")).toBeInTheDocument();
    });
  });

  describe("institution view", () => {
    it("shows institution name and apparatus type", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      expect(screen.getByText("City Hall")).toBeInTheDocument();
      expect(screen.getByText("executive")).toBeInTheDocument();
    });

    it("shows internal balance faction bars", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      expect(screen.getByText("Liberal-Technocratic")).toBeInTheDocument();
      expect(screen.getByText("Revanchist-Fascist")).toBeInTheDocument();
      expect(screen.getByText("Institutionalist-Bonapartist")).toBeInTheDocument();
    });

    it("shows housed organizations by name", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      // Housed orgs now display resolved name instead of raw ID
      expect(screen.getByText("Workers Union")).toBeInTheDocument();
    });
  });

  it("shows unknown node message for nonexistent node", () => {
    render(<NodeInspector snapshot={snapshot} nodeId="nonexistent" />);
    expect(screen.getByText(/Unknown node/)).toBeInTheDocument();
  });
});
