/**
 * Contract tests for the fetch orchestrator (spec-110 B3) — the single
 * visibility-gated heartbeat that replaces 13 independent pollers, and the
 * spacebar shortcut hook.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { startHeartbeat, HEARTBEAT_MS, useSpacebarShortcut, useHeartbeat } from "./orchestrator";

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

beforeEach(() => {
  resetStore();
  resetMockGameState();
  setVisibility("visible");
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("startHeartbeat", () => {
  it("fetches state once per HEARTBEAT_MS while the tab is visible", async () => {
    const stop = startHeartbeat(DEFAULT_GAME_ID);

    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(2);

    stop();
  });

  it("skips the fetch entirely while the tab is hidden", async () => {
    setVisibility("hidden");
    const stop = startHeartbeat(DEFAULT_GAME_ID);

    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 3);

    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(0);
    stop();
  });

  it("resumes fetching once the tab becomes visible again (next tick, no catch-up burst)", async () => {
    setVisibility("hidden");
    const stop = startHeartbeat(DEFAULT_GAME_ID);
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 2);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(0);

    setVisibility("visible");
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);

    stop();
  });

  it("stop() halts further fetches", async () => {
    const stop = startHeartbeat(DEFAULT_GAME_ID);
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);

    stop();
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 3);

    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);
  });
});

describe("useHeartbeat", () => {
  it("starts on mount and stops on unmount", async () => {
    const { unmount } = renderHook(() => useHeartbeat(DEFAULT_GAME_ID));

    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);

    unmount();
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 3);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);
  });

  it("does nothing when gameId is null", async () => {
    renderHook(() => useHeartbeat(null));
    await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 3);
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(0);
  });
});

describe("useSpacebarShortcut", () => {
  it("toggles play/pause on Space, ignoring the event when focus is in a text input", () => {
    const toggleSpy = vi.fn();
    useStore.setState((s) => ({ time: { ...s.time, toggleSpacebar: toggleSpy } }));
    renderHook(() => useSpacebarShortcut(DEFAULT_GAME_ID));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));
    expect(toggleSpy).toHaveBeenCalledTimes(1);
    expect(toggleSpy).toHaveBeenCalledWith(DEFAULT_GAME_ID);

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.dispatchEvent(new KeyboardEvent("keydown", { code: "Space", bubbles: true }));
    expect(toggleSpy).toHaveBeenCalledTimes(1); // still 1 — ignored while typing
    document.body.removeChild(input);
  });

  it("removes the listener on unmount", () => {
    const toggleSpy = vi.fn();
    useStore.setState((s) => ({ time: { ...s.time, toggleSpacebar: toggleSpy } }));
    const { unmount } = renderHook(() => useSpacebarShortcut(DEFAULT_GAME_ID));

    unmount();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));

    expect(toggleSpy).not.toHaveBeenCalled();
  });

  it("does nothing when gameId is null", () => {
    const toggleSpy = vi.fn();
    useStore.setState((s) => ({ time: { ...s.time, toggleSpacebar: toggleSpy } }));
    renderHook(() => useSpacebarShortcut(null));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));

    expect(toggleSpy).not.toHaveBeenCalled();
  });
});
