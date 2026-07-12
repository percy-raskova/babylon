/**
 * Contract tests for `useNarration` (spec-113 Lane G — "the hook shipped
 * without a test"). Mirrors `store/orchestrator.test.ts`'s
 * `useHeartbeat`/`useSpacebarShortcut` `renderHook` pattern.
 *
 * Uses the MSW narration handlers (`src/mocks/narration/handlers.ts`) per
 * that file's own documented opt-in pattern (`server.use(...narrationHandlers)`)
 * — the real `GET /api/games/:id/narration/` endpoint doesn't exist on the
 * backend yet (`lib/narration/client.ts`'s docstring), so these handlers
 * are the only fixture-backed way to exercise `useNarration`'s "ready"
 * path; the global `src/test/handlers.ts` deliberately doesn't register
 * them.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { server } from "@/test/server";
import {
  narrationHandlers,
  resetSimulatedNarrationStatus,
  setSimulatedNarrationStatus,
} from "@/mocks/narration/handlers";
import { useNarration } from "./useNarration";

beforeEach(() => {
  resetStore();
  resetMockGameState();
  resetSimulatedNarrationStatus();
  server.use(...narrationHandlers);
});

afterEach(() => {
  resetSimulatedNarrationStatus();
});

describe("useNarration", () => {
  it("mounting marks the narration panel mounted and fires the first fetch", async () => {
    renderHook(() => useNarration(DEFAULT_GAME_ID));

    expect(useStore.getState().panels.narration.mounted).toBe(true);
    await waitFor(() => {
      expect(useStore.getState().panels.narration.status).toBe("ready");
    });
    expect(useStore.getState().panels.narration.beats.length).toBeGreaterThan(0);
  });

  it("unmounting marks the narration panel unmounted", async () => {
    const { unmount } = renderHook(() => useNarration(DEFAULT_GAME_ID));
    await waitFor(() => {
      expect(useStore.getState().panels.narration.status).toBe("ready");
    });

    unmount();
    expect(useStore.getState().panels.narration.mounted).toBe(false);
  });

  it("does nothing when gameId is null (no mount, no fetch)", () => {
    renderHook(() => useNarration(null));
    expect(useStore.getState().panels.narration.mounted).toBe(false);
    expect(useStore.getState().panels.narration.status).toBe("offline");
  });

  it("latest returns the newest beat by tick once beats arrive", async () => {
    const { result } = renderHook(() => useNarration(DEFAULT_GAME_ID));

    expect(result.current.latest).toBeNull();
    await waitFor(() => {
      expect(result.current.status).toBe("ready");
    });

    // NARRATION_FIXTURE_BEATS' highest tick is 312, shared by two endgame
    // beats — mergeBeats' stable sort keeps "beat-endgame-analysis" last
    // (it follows "beat-endgame-dual-power" in the fixture's own order).
    expect(result.current.latest?.tick).toBe(312);
    expect(result.current.latest?.id).toBe("beat-endgame-analysis");
  });

  it("reports the offline status honestly when the narrator is off (Constitution III.11)", async () => {
    setSimulatedNarrationStatus("offline");
    const { result } = renderHook(() => useNarration(DEFAULT_GAME_ID));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.status).toBe("offline");
    expect(result.current.beats).toEqual([]);
    expect(result.current.latest).toBeNull();
  });
});
