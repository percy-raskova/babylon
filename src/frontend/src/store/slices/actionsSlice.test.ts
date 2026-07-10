/**
 * Contract tests for the actions slice (spec-110 B3 stage 2) — the Action
 * Composer's submit path and the pending-actions list.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("actions slice — submit", () => {
  it("starts with an empty pending list, not submitting, no error", () => {
    const { actions } = useStore.getState();
    expect(actions.pending).toEqual([]);
    expect(actions.submitting).toBe(false);
    expect(actions.error).toBeNull();
  });

  it("POSTs to /actions/{verb}/ with the body unchanged (verb rides in the URL, Spec 040)", async () => {
    let capturedBody: unknown;
    server.use(
      http.post("/api/games/:id/actions/:verb/", async ({ request, params }) => {
        capturedBody = await request.json();
        expect(params.verb).toBe("educate");
        return HttpResponse.json({ status: "ok", data: null });
      }),
    );

    const ok = await useStore.getState().actions.submit(DEFAULT_GAME_ID, "educate", {
      org_id: "org-1",
      target_community_id: "community-1",
      params: {},
    });

    expect(ok).toBe(true);
    expect(capturedBody).toEqual({
      org_id: "org-1",
      target_community_id: "community-1",
      params: {},
    });
  });

  it("on success, appends a pending entry and refetches world state", async () => {
    await useStore.getState().actions.submit(DEFAULT_GAME_ID, "educate", {
      org_id: "org-1",
      target_community_id: "community-1",
      params: {},
    });

    expect(useStore.getState().actions.pending).toHaveLength(1);
    expect(useStore.getState().actions.pending[0]).toMatchObject({
      verb: "educate",
      orgId: "org-1",
      targetId: "community-1",
    });
    expect(requestLog.filter((r) => r === "GET state")).toHaveLength(1);
  });

  it("on failure, sets a loud error and does not queue a pending entry", async () => {
    server.use(
      http.post("/api/games/:id/actions/:verb/", () =>
        HttpResponse.json(
          { status: "error", message: "Insufficient cadre labor" },
          { status: 400 },
        ),
      ),
    );

    const ok = await useStore.getState().actions.submit(DEFAULT_GAME_ID, "mobilize", {
      org_id: "org-1",
      target_id: "community-1",
      params: { sl_committed: 5 },
    });

    expect(ok).toBe(false);
    expect(useStore.getState().actions.pending).toEqual([]);
    expect(useStore.getState().actions.error).toBe("Insufficient cadre labor");
  });

  it("clearPending empties the list", async () => {
    await useStore.getState().actions.submit(DEFAULT_GAME_ID, "educate", {
      org_id: "org-1",
      target_community_id: "community-1",
      params: {},
    });
    expect(useStore.getState().actions.pending).toHaveLength(1);

    useStore.getState().actions.clearPending();
    expect(useStore.getState().actions.pending).toEqual([]);
  });
});

describe("actions slice — world slice clears pending on tick advance", () => {
  it("submitting an action then resolving the tick clears the pending list", async () => {
    await useStore.getState().actions.submit(DEFAULT_GAME_ID, "educate", {
      org_id: "org-1",
      target_community_id: "community-1",
      params: {},
    });
    expect(useStore.getState().actions.pending).toHaveLength(1);

    await useStore.getState().world.fetchState(DEFAULT_GAME_ID); // same tick — no clear yet
    expect(useStore.getState().actions.pending).toHaveLength(1);

    await useStore.getState().time.step(DEFAULT_GAME_ID); // resolves -> tick advances
    expect(useStore.getState().actions.pending).toEqual([]);
  });
});
