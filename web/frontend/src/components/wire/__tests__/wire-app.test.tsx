/**
 * Wire component tests (spec 094).
 *
 * Renders WireApp against the MSW fixture and verifies the triptych,
 * tab switching, and euphemism sync-highlight.
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { WireApp } from "@/components/wire/WireApp";

function renderWire() {
  return render(
    <MemoryRouter>
      <WireApp gameId="wayne-county-001" />
    </MemoryRouter>,
  );
}

describe("WireApp (spec 094)", () => {
  it("renders the title bar with THE WIRE", async () => {
    renderWire();
    expect(await screen.findByText("THE WIRE")).toBeInTheDocument();
  });

  it("renders the tick badge from the feed", async () => {
    renderWire();
    expect(await screen.findByText("0005")).toBeInTheDocument();
  });

  it("renders all 4 tab labels", async () => {
    renderWire();
    expect(await screen.findByText("The Wire")).toBeInTheDocument();
    expect(screen.getByText("Wire Index")).toBeInTheDocument();
    expect(screen.getByText("Patterns")).toBeInTheDocument();
    expect(screen.getByText("Corpus")).toBeInTheDocument();
  });

  it("renders the triptych columns on the WIRE tab", async () => {
    renderWire();
    expect(await screen.findByText(/CHANNEL - CORPORATE/)).toBeInTheDocument();
    expect(screen.getByText(/CHANNEL - LIBERATED/)).toBeInTheDocument();
    expect(screen.getByText(/CHANNEL - INTEL/)).toBeInTheDocument();
  });

  it("renders the active story headline in the continental column", async () => {
    renderWire();
    expect(await screen.findByText(/Authorities Report Civil Disturbance/)).toBeInTheDocument();
  });

  it("switches to the INDEX tab when clicked", async () => {
    renderWire();
    const tabButton = await screen.findByText("Wire Index");
    fireEvent.click(tabButton);
    expect(await screen.findByText("Recent dispatches")).toBeInTheDocument();
  });

  it("switches to the PATTERNS tab and shows filter cards", async () => {
    renderWire();
    await screen.findByText("Patterns");
    fireEvent.click(screen.getByText("Patterns"));
    expect(await screen.findByText("Manufacturing Consent - live audit")).toBeInTheDocument();
    expect(screen.getByText("Ownership")).toBeInTheDocument();
    expect(screen.getByText("Sourcing")).toBeInTheDocument();
  });

  it("switches to the CORPUS tab", async () => {
    renderWire();
    await screen.findByText("Corpus");
    fireEvent.click(screen.getByText("Corpus"));
    expect(await screen.findByText("The Archive")).toBeInTheDocument();
  });

  it("shows the translation footer with euphemism count", async () => {
    renderWire();
    expect(await screen.findByText(/EUPHEMISMS/)).toBeInTheDocument();
  });
});
