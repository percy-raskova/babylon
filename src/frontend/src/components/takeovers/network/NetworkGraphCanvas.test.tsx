/**
 * NetworkGraphCanvas tests (AW4-R2) — the thin imperative sigma.js wrapper.
 * `sigma` is globally mocked in `test/setup.ts` (jsdom has no WebGL/canvas,
 * mirroring the deck.gl mocks already there) so these tests assert the
 * mount/unmount contract (construct on mount with the given graph and
 * container, `kill()` on unmount) rather than any actual pixel output.
 *
 * The mock's call history is NOT cleared between `it()` blocks (this repo's
 * vitest config sets no `clearMocks`/`restoreMocks` — `DeckGLMap.test.tsx`
 * hits the same thing and reads `.mock.calls.at(-1)` rather than an absolute
 * index/count), so every assertion here reads the LAST call/result, never a
 * fixed index or `toHaveBeenCalledTimes`.
 */

import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import Graph from "graphology";
import Sigma from "sigma";
import { NetworkGraphCanvas } from "./NetworkGraphCanvas";

describe("NetworkGraphCanvas", () => {
  it("renders a container element", () => {
    const graph = new Graph();
    const { getByTestId } = render(<NetworkGraphCanvas graph={graph} />);
    expect(getByTestId("network-graph-canvas")).toBeInTheDocument();
  });

  it("constructs a Sigma renderer with the given graph and the container on mount", () => {
    const graph = new Graph();
    graph.addNode("a");
    const { getByTestId } = render(<NetworkGraphCanvas graph={graph} />);

    const [passedGraph, passedContainer] = vi.mocked(Sigma).mock.calls.at(-1)!;
    expect(passedGraph).toBe(graph);
    expect(passedContainer).toBe(getByTestId("network-graph-canvas"));
  });

  it("kills the renderer on unmount", () => {
    const graph = new Graph();
    const { unmount } = render(<NetworkGraphCanvas graph={graph} />);
    const instance = vi.mocked(Sigma).mock.results.at(-1)!.value as { kill: () => void };

    unmount();

    expect(instance.kill).toHaveBeenCalledTimes(1);
  });

  it("rebuilds the renderer when the graph instance changes", () => {
    const graphA = new Graph();
    const graphB = new Graph();
    const { rerender } = render(<NetworkGraphCanvas graph={graphA} />);
    const callsBefore = vi.mocked(Sigma).mock.calls.length;

    rerender(<NetworkGraphCanvas graph={graphB} />);

    expect(vi.mocked(Sigma).mock.calls.length).toBeGreaterThan(callsBefore);
    const lastCallGraph = vi.mocked(Sigma).mock.calls.at(-1)![0];
    expect(lastCallGraph).toBe(graphB);
  });
});
