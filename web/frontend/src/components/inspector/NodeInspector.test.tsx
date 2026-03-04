/**
 * Unit tests for the NodeInspector component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NodeInspector } from "./NodeInspector";
import { makeSnapshot } from "@/test/fixtures";

describe("NodeInspector", () => {
  const snapshot = makeSnapshot();

  describe("entity view", () => {
    it("shows entity name and role badge", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="entity-proletariat" />);
      expect(screen.getByText("Proletariat")).toBeInTheDocument();
      expect(screen.getByText("proletariat")).toBeInTheDocument();
    });

    it("shows survival probabilities", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="entity-proletariat" />);
      expect(screen.getByText("P(Acquiescence)")).toBeInTheDocument();
      expect(screen.getByText("P(Revolution)")).toBeInTheDocument();
    });

    it("shows economics section", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="entity-proletariat" />);
      expect(screen.getByText("Wealth")).toBeInTheDocument();
      expect(screen.getByText("Subsistence")).toBeInTheDocument();
      expect(screen.getByText("Population")).toBeInTheDocument();
    });

    it("shows consciousness section", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="entity-proletariat" />);
      // "Consciousness" appears twice: section header + stat label
      const matches = screen.getAllByText("Consciousness");
      expect(matches).toHaveLength(2);
      expect(screen.getByText("Organization")).toBeInTheDocument();
      expect(screen.getByText("Agitation")).toBeInTheDocument();
    });
  });

  describe("organization view", () => {
    it("shows org name and type", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("Workers Union")).toBeInTheDocument();
      expect(screen.getByText("POLITICAL_FACTION")).toBeInTheDocument();
    });

    it("shows capacity metrics", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("Budget")).toBeInTheDocument();
      expect(screen.getByText("Cohesion")).toBeInTheDocument();
      expect(screen.getByText("Cadre Level")).toBeInTheDocument();
    });

    it("shows territory IDs", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="org-workers-union" />);
      expect(screen.getByText("territory-downtown")).toBeInTheDocument();
    });
  });

  describe("institution view", () => {
    it("shows institution name and apparatus type", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      expect(screen.getByText("City Hall")).toBeInTheDocument();
      expect(screen.getByText("RSA")).toBeInTheDocument();
    });

    it("shows internal balance faction bars", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      expect(screen.getByText("Liberal-Technocratic")).toBeInTheDocument();
      expect(screen.getByText("Revanchist-Fascist")).toBeInTheDocument();
      expect(screen.getByText("Institutionalist-Bonapartist")).toBeInTheDocument();
    });

    it("shows housed organizations", () => {
      render(<NodeInspector snapshot={snapshot} nodeId="inst-city-hall" />);
      expect(screen.getByText("org-workers-union")).toBeInTheDocument();
    });
  });

  it("shows unknown node message for nonexistent node", () => {
    render(<NodeInspector snapshot={snapshot} nodeId="nonexistent" />);
    expect(screen.getByText(/Unknown node/)).toBeInTheDocument();
  });
});
