/**
 * Unit tests for the VerbSelector component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VerbSelector } from "./VerbSelector";

describe("VerbSelector", () => {
  it("renders all 9 verb buttons", () => {
    render(<VerbSelector selectedVerb={null} onSelect={vi.fn()} />);
    expect(screen.getByText("Educate")).toBeInTheDocument();
    expect(screen.getByText("Reproduce")).toBeInTheDocument();
    expect(screen.getByText("Investigate")).toBeInTheDocument();
    expect(screen.getByText("Attack")).toBeInTheDocument();
    expect(screen.getByText("Mobilize")).toBeInTheDocument();
    expect(screen.getByText("Campaign")).toBeInTheDocument();
    expect(screen.getByText("Aid")).toBeInTheDocument();
    expect(screen.getByText("Move")).toBeInTheDocument();
    expect(screen.getByText("Negotiate")).toBeInTheDocument();
  });

  it("renders column headers", () => {
    render(<VerbSelector selectedVerb={null} onSelect={vi.fn()} />);
    expect(screen.getByText("Build Org")).toBeInTheDocument();
    expect(screen.getByText("Project Pwr")).toBeInTheDocument();
    expect(screen.getByText("Manage Res")).toBeInTheDocument();
  });

  it("fires onSelect when verb button is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<VerbSelector selectedVerb={null} onSelect={onSelect} />);

    await user.click(screen.getByText("Educate"));
    expect(onSelect).toHaveBeenCalledWith("educate");
  });

  it("highlights selected verb", () => {
    render(<VerbSelector selectedVerb="attack" onSelect={vi.fn()} />);
    const attackButton = screen.getByText("Attack").closest("button");
    expect(attackButton?.className).toContain("bg-dark-metal");
  });

  it("dims over-budget verbs", () => {
    render(
      <VerbSelector
        selectedVerb={null}
        onSelect={vi.fn()}
        verbCosts={{ educate: 10, attack: 5 }}
        availableAP={7}
      />,
    );
    // educate costs 10, AP=7 -> over budget -> opacity-50
    const educateButton = screen.getByText("Educate").closest("button");
    expect(educateButton?.className).toContain("opacity-50");

    // attack costs 5, AP=7 -> affordable -> no opacity
    const attackButton = screen.getByText("Attack").closest("button");
    expect(attackButton?.className).not.toContain("opacity-50");
  });

  it("shows AP cost when verbCosts provided", () => {
    render(<VerbSelector selectedVerb={null} onSelect={vi.fn()} verbCosts={{ educate: 3 }} />);
    expect(screen.getByText("3 AP")).toBeInTheDocument();
  });

  it("shows verb descriptions", () => {
    render(<VerbSelector selectedVerb={null} onSelect={vi.fn()} />);
    expect(screen.getByText("Raise consciousness")).toBeInTheDocument();
    expect(screen.getByText("Direct action")).toBeInTheDocument();
    expect(screen.getByText("Transfer resources")).toBeInTheDocument();
  });
});
