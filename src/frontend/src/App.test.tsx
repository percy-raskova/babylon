import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App shell", () => {
  it("renders the five named cockpit regions", () => {
    render(<App />);

    expect(screen.getByTestId("region-statusbar")).toBeInTheDocument();
    expect(screen.getByTestId("region-outliner")).toBeInTheDocument();
    expect(screen.getByTestId("region-map")).toBeInTheDocument();
    expect(screen.getByTestId("region-dock")).toBeInTheDocument();
    expect(screen.getByTestId("region-bottomstrip")).toBeInTheDocument();
  });

  it("shows a health indicator", () => {
    render(<App />);

    expect(screen.getByTestId("health-indicator")).toBeInTheDocument();
  });
});
