import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MockBadge } from "./MockBadge";

describe("MockBadge", () => {
  it("renders a visible MOCK indicator (owner's mock doctrine, Program 17 Wave 1 / W1.4)", () => {
    render(<MockBadge />);
    expect(screen.getByTestId("mock-badge")).toBeInTheDocument();
    expect(screen.getByText("Mock")).toBeInTheDocument();
  });
});
