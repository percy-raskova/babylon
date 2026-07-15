/**
 * RadarLoopPanel tests — the RADAR LOOP tick-scrubber HUD widget (Program
 * 17 Wave 3, Frontend-W3R3). TDD red phase written before the
 * implementation. Standard 4-test-suite shape (BifurcationGauge/
 * SurvivalDuelPanel) covering: non-replayable-lens hint, loading, capped
 * notice, reduced-motion disables autoplay — plus start/exit and the
 * mount-toggle test every FloatingPanel-hosted widget carries.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { RadarLoopPanel } from "./RadarLoopPanel";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeMapHistoryPayload, makeMapHistoryFrame } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RadarLoopPanel — availability", () => {
  it("shows an honest hint naming the 4 replayable lenses when the active lens has no persisted history", () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "metric", metric: "occ" } } }));
    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);

    const hint = screen.getByTestId("radar-loop-unavailable-hint");
    expect(hint).toHaveTextContent(/no persisted history/i);
    expect(hint).toHaveTextContent(/Heat/);
    expect(hint).toHaveTextContent(/Population/);
    expect(hint).toHaveTextContent(/Profit Rate/);
    expect(hint).toHaveTextContent(/Exploitation Rate/);
    expect(screen.queryByTestId("radar-loop-start")).not.toBeInTheDocument();
  });

  it("offers a Start Replay affordance when the active lens IS replayable", () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("radar-loop-start")).toBeInTheDocument();
    expect(screen.queryByTestId("radar-loop-unavailable-hint")).not.toBeInTheDocument();
  });
});

describe("RadarLoopPanel — entering replay", () => {
  it("shows a loading state immediately after Start Replay is clicked", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    let resolveFetch: (() => void) | undefined;
    server.use(
      http.get("/api/games/:id/map/history/", async () => {
        await new Promise<void>((r) => {
          resolveFetch = r;
        });
        return HttpResponse.json({ status: "ok", data: makeMapHistoryPayload() });
      }),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    expect(screen.getByTestId("radar-loop-loading")).toBeInTheDocument();
    resolveFetch?.();
    await waitFor(() => expect(screen.queryByTestId("radar-loop-loading")).not.toBeInTheDocument());
  });

  it("shows the REPLAY badge and scrubber once the window loads, with tick/window readout", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            from_tick: 10,
            to_tick: 12,
            frames: [
              makeMapHistoryFrame({ tick: 10 }),
              makeMapHistoryFrame({ tick: 11 }),
              makeMapHistoryFrame({ tick: 12 }),
            ],
          }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-replay-badge")).toBeInTheDocument());
    expect(screen.getByTestId("radar-loop-scrubber")).toBeInTheDocument();
    expect(screen.getByTestId("radar-loop-tick-readout")).toHaveTextContent("12");
  });

  it("an honest empty window (no frames yet) shows a no-history message, not a broken scrubber", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    // Default handler serves frames: [].
    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("radar-loop-scrubber")).not.toBeInTheDocument();
  });

  it("a failed fetch surfaces a loud error", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});

describe("RadarLoopPanel — capped notice", () => {
  it("shows an honest capped notice when the served window was narrower than the full history", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({ capped: true, frames: [makeMapHistoryFrame()] }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-capped")).toBeInTheDocument());
  });

  it("shows no capped notice when the window was not narrowed", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({ capped: false, frames: [makeMapHistoryFrame()] }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-scrubber")).toBeInTheDocument());
    expect(screen.queryByTestId("radar-loop-capped")).not.toBeInTheDocument();
  });
});

describe("RadarLoopPanel — reduced motion disables autoplay", () => {
  it("the play/pause control is disabled (scrub-only) when prefers-reduced-motion is set", async () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            frames: [makeMapHistoryFrame({ tick: 1 }), makeMapHistoryFrame({ tick: 2 })],
          }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-play-pause")).toBeInTheDocument());
    expect(screen.getByTestId("radar-loop-play-pause")).toBeDisabled();
  });

  it("the play/pause control is enabled by default (no reduced-motion preference)", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({
            frames: [makeMapHistoryFrame({ tick: 1 }), makeMapHistoryFrame({ tick: 2 })],
          }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));

    await waitFor(() => expect(screen.getByTestId("radar-loop-play-pause")).toBeInTheDocument());
    expect(screen.getByTestId("radar-loop-play-pause")).not.toBeDisabled();
  });
});

describe("RadarLoopPanel — exit", () => {
  it("Exit Replay returns to the Start Replay prompt with no residual scrubber state", async () => {
    useStore.setState((s) => ({ map: { ...s.map, lens: { kind: "heat" } } }));
    server.use(
      http.get("/api/games/:id/map/history/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeMapHistoryPayload({ frames: [makeMapHistoryFrame({ tick: 1 })] }),
        }),
      ),
    );

    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    await userEvent.click(screen.getByTestId("radar-loop-start"));
    await waitFor(() => expect(screen.getByTestId("radar-loop-scrubber")).toBeInTheDocument());

    await userEvent.click(screen.getByTestId("radar-loop-exit"));

    expect(screen.getByTestId("radar-loop-start")).toBeInTheDocument();
    expect(screen.queryByTestId("radar-loop-scrubber")).not.toBeInTheDocument();
    expect(screen.queryByTestId("radar-loop-replay-badge")).not.toBeInTheDocument();
    expect(useStore.getState().mapReplay.active).toBe(false);
  });
});

describe("RadarLoopPanel — mounts collapsed/expanded via ui.chrome.radarLoopOpen", () => {
  it("toggles via the panel header button", async () => {
    // DEFAULT_LENS (imperial_rent) is not replayable, so the panel body is
    // just the honest hint — the toggle is the only button on screen.
    render(<RadarLoopPanel gameId={DEFAULT_GAME_ID} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "true");

    await userEvent.click(button);
    expect(useStore.getState().ui.chrome.radarLoopOpen).toBe(false);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});
