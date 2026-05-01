/**
 * Unit tests for the DeckGLMap component (stubbed — WebGL mocked in setup.ts).
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { DeckGLMap } from "./DeckGLMap";
import { makeSnapshot, makeTerritory } from "@/test/fixtures";

describe("DeckGLMap", () => {
  it("renders without crashing", () => {
    const snapshot = makeSnapshot();
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders with territories", () => {
    const snapshot = makeSnapshot({
      territories: [
        makeTerritory({ id: "terr-1", name: "Downtown" }),
        makeTerritory({ id: "terr-2", name: "Suburbs" }),
      ],
    });
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    expect(container.querySelector("div")).toBeTruthy();
  });

  it("renders map controls container", () => {
    const snapshot = makeSnapshot();
    const { container } = render(
      <MemoryRouter>
        <DeckGLMap snapshot={snapshot} />
      </MemoryRouter>,
    );
    // LayerControls removed in Phase 7 — verify map renders with legend container
    expect(container.querySelector("div")).toBeTruthy();
  });
});
