/**
 * MeltGauge tests — T2-4 (spec-117): a real gauge instrument on
 * `latestMeltDrift`, previously only a line of ticker text. TDD red phase
 * written before the implementation.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MeltGauge } from "./MeltGauge";
import { makeTimeseriesPayload } from "@/test/fixtures";

describe("MeltGauge", () => {
  it("renders nothing when payload is null (no fetch has resolved yet)", () => {
    const { container } = render(<MeltGauge payload={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the MELT axis has never computed", () => {
    const payload = makeTimeseriesPayload({ price_index: [null, null] });
    const { container } = render(<MeltGauge payload={payload} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the axis + needle + copy line once price_index has a real reading", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.0, 1.08] });
    render(<MeltGauge payload={payload} />);

    expect(screen.getByTestId("melt-gauge")).toBeInTheDocument();
    expect(screen.getByTestId("melt-gauge-axis")).toBeInTheDocument();
    expect(screen.getByTestId("melt-gauge-needle")).toBeInTheDocument();
    expect(screen.getByTestId("melt-gauge-line")).toHaveTextContent(/\+8\.0%/);
    expect(screen.getByTestId("melt-gauge-line")).toHaveTextContent(/less labor/);
  });

  it("reads a negative drift as 'more labor'", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.0, 0.95] });
    render(<MeltGauge payload={payload} />);

    expect(screen.getByTestId("melt-gauge-line")).toHaveTextContent(/-5\.0%/);
    expect(screen.getByTestId("melt-gauge-line")).toHaveTextContent(/more labor/);
  });

  it("clamps the needle to the axis's drawable range for an extreme drift", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.0, 3.0] });
    render(<MeltGauge payload={payload} />);

    const needle = screen.getByTestId("melt-gauge-needle");
    const axis = screen.getByTestId("melt-gauge-axis");
    const axisWidth = Number(axis.getAttribute("width"));
    expect(Number(needle.getAttribute("cx"))).toBeLessThanOrEqual(axisWidth);
    expect(Number(needle.getAttribute("cx"))).toBeGreaterThanOrEqual(0);
  });

  it("omits the trajectory sparkline when fewer than two real points exist", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.08] });
    render(<MeltGauge payload={payload} />);

    expect(screen.queryByTestId("melt-gauge-sparkline")).not.toBeInTheDocument();
  });

  it("renders the trajectory sparkline once two+ real points exist", () => {
    const payload = makeTimeseriesPayload({ price_index: [1.0, 1.05, 1.08] });
    render(<MeltGauge payload={payload} />);

    expect(screen.getByTestId("melt-gauge-sparkline")).toBeInTheDocument();
  });
});
