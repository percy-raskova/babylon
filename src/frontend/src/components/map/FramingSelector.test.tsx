/**
 * Unit tests for FramingSelector — the spec-112 C5 admin-level LOD control,
 * a controlled component (props: framing, onFramingChange) mirroring
 * MapModeSelector's B2 convention (no store reads). Ported from the OLD
 * app's FramingSelector (web/frontend/src/components/map/FramingSelector.tsx),
 * which read/wrote mapStore directly — stores are B3 territory here.
 */

import { useState } from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FramingSelector } from "./FramingSelector";
import type { AdminLevel } from "@/types/game";

const ALL_LEVELS: AdminLevel[] = ["hex", "county", "cz", "msa", "bea_ea", "state"];

/** Wraps FramingSelector with local state so click handlers are exercised. */
function ControlledSelector({ initial = "hex" as AdminLevel }: { initial?: AdminLevel }) {
  const [framing, setFraming] = useState<AdminLevel>(initial);
  return <FramingSelector framing={framing} onFramingChange={setFraming} />;
}

describe("FramingSelector", () => {
  it("renders a button for each of the 6 admin levels", () => {
    render(<ControlledSelector />);
    for (const level of ALL_LEVELS) {
      expect(screen.getByTestId(`framing-${level}`)).toBeInTheDocument();
    }
  });

  it("marks the active framing button as pressed, others not", () => {
    render(<ControlledSelector initial="county" />);
    expect(screen.getByTestId("framing-county")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("framing-hex")).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking a framing button calls onFramingChange with the new level", () => {
    render(<ControlledSelector />);
    fireEvent.click(screen.getByTestId("framing-county"));
    expect(screen.getByTestId("framing-county")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("framing-hex")).toHaveAttribute("aria-pressed", "false");
  });

  it("cycles through all 6 levels via clicks", () => {
    render(<ControlledSelector />);
    for (const level of ALL_LEVELS) {
      fireEvent.click(screen.getByTestId(`framing-${level}`));
      expect(screen.getByTestId(`framing-${level}`)).toHaveAttribute("aria-pressed", "true");
    }
  });

  it("labels match the old app's FRAMING_OPTIONS (web/frontend's FramingSelector)", () => {
    render(<ControlledSelector />);
    expect(screen.getByTestId("framing-state")).toHaveTextContent("ST");
    expect(screen.getByTestId("framing-bea_ea")).toHaveTextContent("EA");
    expect(screen.getByTestId("framing-msa")).toHaveTextContent("MSA");
    expect(screen.getByTestId("framing-cz")).toHaveTextContent("CZ");
    expect(screen.getByTestId("framing-county")).toHaveTextContent("CTY");
    expect(screen.getByTestId("framing-hex")).toHaveTextContent("HEX");
  });

  it("does not throw when clicked with no onFramingChange handler (uncontrolled-safe)", () => {
    render(<FramingSelector framing="hex" />);
    expect(() => fireEvent.click(screen.getByTestId("framing-county"))).not.toThrow();
  });

  it("county/state are primary (rendered before hex) — DESIGN_BIBLE.md §9.2's cartography inversion", () => {
    render(<ControlledSelector />);
    const buttons = screen.getAllByRole("button").map((b) => b.getAttribute("data-testid"));
    expect(buttons.indexOf("framing-county")).toBeLessThan(buttons.indexOf("framing-hex"));
    expect(buttons.indexOf("framing-state")).toBeLessThan(buttons.indexOf("framing-hex"));
    expect(buttons[buttons.length - 1]).toBe("framing-hex");
  });
});
