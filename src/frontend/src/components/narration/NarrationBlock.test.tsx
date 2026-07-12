import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NarrationBlock } from "./NarrationBlock";
import type { NarrationBeat } from "@/types/narration";

const WIRE_BEAT: NarrationBeat = {
  id: "beat-1",
  tick: 104,
  scope: "event",
  subjectRef: "evt-1",
  headline: "Federal agents raided the WCLF hall, tick 104.",
  body: "Federal agents breached the WCLF hall on Schaefer before dawn, detaining fourteen.",
  register: "wire",
};

const ANALYSIS_BEAT: NarrationBeat = {
  id: "beat-2",
  tick: 104,
  scope: "county",
  subjectRef: "26163",
  headline: "Wayne County's contradiction sharpens.",
  body: "The wage floor beneath the county's organized core continues to erode against rising imperial rent extraction.",
  register: "analysis",
};

describe("NarrationBlock", () => {
  it("renders a wire-register beat's headline and body", () => {
    render(<NarrationBlock beat={WIRE_BEAT} state="ready" />);
    expect(screen.getByTestId("narration-headline")).toHaveTextContent(
      "Federal agents raided the WCLF hall, tick 104.",
    );
    expect(screen.getByTestId("narration-body")).toHaveTextContent(
      "Federal agents breached the WCLF hall on Schaefer before dawn, detaining fourteen.",
    );
    expect(screen.getByTestId("narration-block")).toHaveAttribute("data-register", "wire");
  });

  it("renders an analysis-register beat with its own register attribute", () => {
    render(<NarrationBlock beat={ANALYSIS_BEAT} state="ready" />);
    expect(screen.getByTestId("narration-block")).toHaveAttribute("data-register", "analysis");
  });

  it("a beat takes precedence over state — a beat still renders even if state is offline/pending", () => {
    render(<NarrationBlock beat={WIRE_BEAT} state="offline" />);
    expect(screen.getByTestId("narration-headline")).toBeInTheDocument();
    expect(screen.queryByTestId("narration-empty")).not.toBeInTheDocument();
  });

  it("shows the honest offline copy when narration is disabled, in-register (never blank, never the admin voice)", () => {
    render(<NarrationBlock beat={null} state="offline" />);
    expect(screen.getByTestId("narration-empty")).toHaveTextContent(/narrator is silent/i);
    expect(screen.getByTestId("narration-block")).toHaveAttribute(
      "data-narration-state",
      "offline",
    );
  });

  it("shows the subtle pending copy when generation is scheduled but not yet materialized", () => {
    render(<NarrationBlock beat={null} state="pending" />);
    expect(screen.getByTestId("narration-empty")).toHaveTextContent(/pending/i);
    expect(screen.getByTestId("narration-block")).toHaveAttribute(
      "data-narration-state",
      "pending",
    );
  });

  it("shows a distinct ready-but-nothing-filed copy from offline/pending", () => {
    render(<NarrationBlock beat={null} state="ready" />);
    const emptyText = screen.getByTestId("narration-empty").textContent ?? "";
    expect(emptyText).not.toMatch(/narrator is silent/i);
    expect(emptyText).not.toMatch(/pending/i);
    expect(screen.getByTestId("narration-block")).toHaveAttribute("data-narration-state", "ready");
  });

  it("never renders ALL-CAPS shouting text in a beat (Design Bible §6)", () => {
    render(<NarrationBlock beat={WIRE_BEAT} state="ready" />);
    const headline = screen.getByTestId("narration-headline").textContent ?? "";
    // The source headline itself is mixed-case; assert the component doesn't
    // transform it to uppercase (no text-transform:uppercase-style class churn).
    expect(headline).not.toEqual(headline.toUpperCase());
  });
});
