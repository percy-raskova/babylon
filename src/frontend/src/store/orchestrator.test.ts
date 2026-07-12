/**
 * Contract tests for the fetch orchestrator (spec-110 B3) — the single
 * visibility-gated heartbeat that replaces 13 independent pollers, the
 * spacebar shortcut hook, and the Q/E lens-cycling shortcut hook (spec-112
 * C5-1).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { DEFAULT_LENS, lensKey } from "@/lib/lens";
import { LENS_REGISTRY } from "@/lib/lenses/registry";
import {
  startHeartbeat,
  HEARTBEAT_MS,
  useSpacebarShortcut,
  useHeartbeat,
  useLensCycleShortcut,
} from "./orchestrator";

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

describe("useLensCycleShortcut", () => {
  it("KeyE advances through LENS_REGISTRY with wrap-around (last entry -> first)", () => {
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    let expectedIdx = 0; // default lens is LENS_REGISTRY[0] (imperial_rent)
    LENS_REGISTRY.forEach(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE" }));
      expectedIdx = (expectedIdx + 1) % LENS_REGISTRY.length;
      expect(lensKey(useStore.getState().map.lens)).toEqual(
        lensKey(LENS_REGISTRY[expectedIdx]!.toLens()),
      );
    });
  });

  it("KeyQ goes backward through LENS_REGISTRY with wrap-around (first entry -> last)", () => {
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    let expectedIdx = 0; // default lens is LENS_REGISTRY[0] (imperial_rent)
    LENS_REGISTRY.forEach(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyQ" }));
      expectedIdx = (expectedIdx - 1 + LENS_REGISTRY.length) % LENS_REGISTRY.length;
      expect(lensKey(useStore.getState().map.lens)).toEqual(
        lensKey(LENS_REGISTRY[expectedIdx]!.toLens()),
      );
    });
  });

  it("KeyE from an unregistered metric lens lands on LENS_REGISTRY[0]", () => {
    useStore.getState().map.setLens({ kind: "metric", metric: "occ" });
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE" }));

    expect(lensKey(useStore.getState().map.lens)).toEqual(lensKey(LENS_REGISTRY[0]!.toLens()));
  });

  it("KeyQ from an unregistered metric lens lands on the last registry entry", () => {
    useStore.getState().map.setLens({ kind: "metric", metric: "occ" });
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyQ" }));

    expect(lensKey(useStore.getState().map.lens)).toEqual(
      lensKey(LENS_REGISTRY[LENS_REGISTRY.length - 1]!.toLens()),
    );
  });

  it("ignores KeyE/KeyQ when focus is in a text input", () => {
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE", bubbles: true }));
    input.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyQ", bubbles: true }));
    expect(useStore.getState().map.lens).toEqual(DEFAULT_LENS);
    document.body.removeChild(input);
  });

  it("ignores KeyE/KeyQ when a modifier key is held", () => {
    renderHook(() => useLensCycleShortcut(DEFAULT_GAME_ID));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE", ctrlKey: true }));
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE", metaKey: true }));
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE", altKey: true }));

    expect(useStore.getState().map.lens).toEqual(DEFAULT_LENS);
  });

  it("does nothing when gameId is null", () => {
    renderHook(() => useLensCycleShortcut(null));

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyE" }));

    expect(useStore.getState().map.lens).toEqual(DEFAULT_LENS);
  });
});
