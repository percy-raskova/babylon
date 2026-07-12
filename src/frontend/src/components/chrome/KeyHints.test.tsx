/**
 * KeyHints tests — the keyboard-hint footer primitive (DESIGN_BIBLE.md
 * §9b). Presentational only: renders hint text, binds no keys itself.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KeyHints, DEFAULT_KEY_HINTS } from "./KeyHints";

describe("KeyHints", () => {
  it("renders its testid", () => {
    render(<KeyHints />);
    expect(screen.getByTestId("key-hints")).toBeInTheDocument();
  });

  it("renders the default global hint set (space/1-2-3/Q-E/Esc) when no hints prop is given", () => {
    render(<KeyHints />);
    for (const hint of DEFAULT_KEY_HINTS) {
      expect(screen.getByText(hint.keys)).toBeInTheDocument();
      expect(screen.getByText(hint.label)).toBeInTheDocument();
    }
  });

  it("renders only the hosted-supplied subset when hints is given", () => {
    render(<KeyHints hints={[{ keys: "Esc", label: "close" }]} />);
    expect(screen.getByText("Esc")).toBeInTheDocument();
    expect(screen.queryByText("Space")).not.toBeInTheDocument();
  });
});
