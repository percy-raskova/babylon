import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BreakdownBar } from "./BreakdownBar";

describe("BreakdownBar", () => {
  it("renders 'no data' honestly when entries is undefined (ported from ConsciousnessBreakdown's null-honesty test)", () => {
    render(<BreakdownBar entries={undefined} />);
    expect(screen.getByTestId("breakdown-no-data")).toBeInTheDocument();
    expect(screen.getByText("no data")).toBeInTheDocument();
  });

  it("renders 'no data' honestly for an empty array too", () => {
    render(<BreakdownBar entries={[]} />);
    expect(screen.getByTestId("breakdown-no-data")).toBeInTheDocument();
  });

  it("renders the proportional bar + legend when entries are present (ported)", () => {
    render(
      <BreakdownBar
        entries={[
          { key: "Revolutionary", value: 0.85, color: "text-laser" },
          { key: "Liberal", value: 0.1, color: "text-cadre" },
          { key: "Fascist", value: 0.05, color: "text-rupture" },
        ]}
      />,
    );
    expect(screen.getByTestId("breakdown-bar")).toBeInTheDocument();
    expect(screen.getByText("Revolutionary")).toBeInTheDocument();
    expect(screen.getByText("0.850")).toBeInTheDocument();
  });
});
