/**
 * Contract tests for `useActionPreview` — fires the live `/actions/preview/`
 * fetch once gameId+orgId+verb are set and the verb is composable (a target
 * is selected, or the config's `targetRequired` is false). Mirrors
 * `useNarration.test.ts`'s `renderHook` + MSW pattern.
 */

import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { DEFAULT_GAME_ID } from "@/test/handlers";
import type { ActionPreviewResult } from "@/types/game";
import type { VerbConfig, VerbTarget } from "@/lib/verbs";
import { useActionPreview } from "./useActionPreview";

function makeConfig(overrides?: Partial<VerbConfig>): VerbConfig {
  return {
    verb: "educate",
    label: "Educate",
    description: "Fixture verb config.",
    parseTargets: (): VerbTarget[] => [],
    paramFields: [],
    buildPayload: (orgId, targetId, params) => ({
      org_id: orgId,
      target_id: targetId ?? "",
      params,
    }),
    ...overrides,
  };
}

function stubPreview(overrides?: Partial<ActionPreviewResult>): void {
  server.use(
    http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, () =>
      HttpResponse.json({
        status: "ok",
        data: {
          estimated_consciousness_delta: 0,
          estimated_heat_delta: 0,
          action_point_cost: 1,
          success_probability: 0.5,
          affected_territory_ids: [],
          warnings: [],
          ...overrides,
        },
      }),
    ),
  );
}

describe("useActionPreview", () => {
  it("does not fetch when the verb requires a target and none is selected", () => {
    stubPreview();
    const { result } = renderHook(() =>
      useActionPreview(DEFAULT_GAME_ID, "org-1", "educate", makeConfig(), null),
    );

    expect(result.current).toEqual({ preview: null, loading: false });
  });

  it("fetches once a target is selected on a target-required verb", async () => {
    stubPreview({ estimated_consciousness_delta: 0.05 });
    const { result } = renderHook(() =>
      useActionPreview(DEFAULT_GAME_ID, "org-1", "educate", makeConfig(), "comm-1"),
    );

    await waitFor(() => expect(result.current.preview).not.toBeNull());
    expect(result.current.preview?.estimated_consciousness_delta).toBe(0.05);
    expect(result.current.loading).toBe(false);
  });

  it("fetches immediately for a targetRequired:false verb with no target selected", async () => {
    stubPreview();
    const config = makeConfig({ verb: "reproduce", targetRequired: false });

    const { result } = renderHook(() =>
      useActionPreview(DEFAULT_GAME_ID, "org-1", "reproduce", config, null),
    );

    await waitFor(() => expect(result.current.preview).not.toBeNull());
  });

  it("does not fetch when orgId is empty", () => {
    stubPreview();
    const { result } = renderHook(() =>
      useActionPreview(DEFAULT_GAME_ID, "", "educate", makeConfig(), "comm-1"),
    );

    expect(result.current).toEqual({ preview: null, loading: false });
  });

  it("re-fetches when the target changes (selection-driven, no debounce)", async () => {
    let requestCount = 0;
    server.use(
      http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, () => {
        requestCount += 1;
        return HttpResponse.json({
          status: "ok",
          data: {
            estimated_consciousness_delta: requestCount,
            estimated_heat_delta: 0,
            action_point_cost: 1,
            success_probability: 0.5,
            affected_territory_ids: [],
            warnings: [],
          },
        });
      }),
    );

    const { result, rerender } = renderHook(
      ({ targetId }: { targetId: string | null }) =>
        useActionPreview(DEFAULT_GAME_ID, "org-1", "educate", makeConfig(), targetId),
      { initialProps: { targetId: "comm-1" } },
    );

    await waitFor(() => expect(result.current.preview?.estimated_consciousness_delta).toBe(1));

    rerender({ targetId: "comm-2" });

    await waitFor(() => expect(result.current.preview?.estimated_consciousness_delta).toBe(2));
  });

  it("returns preview:null on a server error (honest null, never throws)", async () => {
    server.use(
      http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, () =>
        HttpResponse.json({ status: "error", data: null, message: "boom" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() =>
      useActionPreview(DEFAULT_GAME_ID, "org-1", "educate", makeConfig(), "comm-1"),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.preview).toBeNull();
  });
});
