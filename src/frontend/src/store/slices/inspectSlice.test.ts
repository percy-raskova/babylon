/**
 * Contract tests for the fleshed-out InspectionStack slice (spec-113 Lane
 * C, architecture.md §2.3). Uses the default MSW catch-all
 * (`GET /api/games/:id/:kind/:entityId/` -> `{status:"ok", data:{kind,id}}`,
 * logged as `GET inspector:<kind>`) from `src/test/handlers.ts` unless a
 * test overrides it.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, requestLog, DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";
import { MAX_INSPECTION_DEPTH } from "./inspectSlice";

const tick = (n: number): void => {
  useStore.setState((s) => ({ world: { ...s.world, snapshot: makeSnapshot({ tick: n }) } }));
};

const settle = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  resetStore();
  resetMockGameState();
  useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);
});

describe("inspect.push", () => {
  it("adds a frame and resolves it against the entity endpoint", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();

    const [frame] = useStore.getState().inspect.stack;
    expect(frame?.ref).toEqual({ kind: "hex", id: "h1" });
    expect(frame?.loading).toBe(false);
    expect(frame?.error).toBeNull();
    expect(frame?.data).not.toBeNull();
    expect(requestLog.filter((r) => r === "GET inspector:hex")).toHaveLength(1);
  });

  it("marks the frame with a loud error when no active game is set", async () => {
    useStore.getState().session.setActiveGame(null);
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();

    const [frame] = useStore.getState().inspect.stack;
    expect(frame?.error).toBe("No active game");
    expect(frame?.data).toBeNull();
    expect(frame?.loading).toBe(false);
  });

  it(`refuses to push past MAX_INSPECTION_DEPTH (${MAX_INSPECTION_DEPTH})`, async () => {
    for (let i = 0; i < MAX_INSPECTION_DEPTH + 2; i += 1) {
      useStore.getState().inspect.push({ kind: "hex", id: `h${i}` });
    }
    await settle();

    expect(useStore.getState().inspect.stack).toHaveLength(MAX_INSPECTION_DEPTH);
    expect(useStore.getState().inspect.stack.at(-1)?.ref.id).toBe(`h${MAX_INSPECTION_DEPTH - 1}`);
  });
});

describe("inspect.pop / popTo / clear", () => {
  it("pop removes the top frame", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    useStore.getState().inspect.push({ kind: "org", id: "o1" });
    await settle();

    useStore.getState().inspect.pop();
    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.ref).toEqual({ kind: "hex", id: "h1" });
  });

  it("pop no-ops when the top frame is pinned (DESIGN_BIBLE.md §4)", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();
    useStore.getState().inspect.togglePin(0);

    useStore.getState().inspect.pop();
    expect(useStore.getState().inspect.stack).toHaveLength(1);
  });

  it("popTo(i) truncates to frames 0..i regardless of pin", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    useStore.getState().inspect.push({ kind: "org", id: "o1" });
    useStore.getState().inspect.push({ kind: "node", id: "n1" });
    await settle();
    useStore.getState().inspect.togglePin(2);

    useStore.getState().inspect.popTo(0);
    expect(useStore.getState().inspect.stack).toHaveLength(1);
  });

  it("clear empties the stack", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();
    useStore.getState().inspect.clear();
    expect(useStore.getState().inspect.stack).toHaveLength(0);
  });

  it("togglePin flips the pinned flag on the frame at index", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();
    expect(useStore.getState().inspect.stack[0]?.pinned).toBe(false);
    useStore.getState().inspect.togglePin(0);
    expect(useStore.getState().inspect.stack[0]?.pinned).toBe(true);
    useStore.getState().inspect.togglePin(0);
    expect(useStore.getState().inspect.stack[0]?.pinned).toBe(false);
  });
});

describe("tick fan-out (architecture.md §2.3)", () => {
  it("refetches only the top frame on tick change; a lower frame refetches lazily when popTo re-focuses it", async () => {
    tick(1);
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();
    expect(requestLog.filter((r) => r === "GET inspector:hex")).toHaveLength(1);

    tick(2);
    await settle();
    expect(requestLog.filter((r) => r === "GET inspector:hex")).toHaveLength(2);
    expect(useStore.getState().inspect.stack[0]?.fetchedAtTick).toBe(2);

    useStore.getState().inspect.push({ kind: "org", id: "o1" });
    await settle();
    expect(requestLog.filter((r) => r === "GET inspector:org")).toHaveLength(1);

    tick(3);
    await settle();
    // Only the top (org) frame refetches on the tick bump...
    expect(requestLog.filter((r) => r === "GET inspector:org")).toHaveLength(2);
    expect(requestLog.filter((r) => r === "GET inspector:hex")).toHaveLength(2);
    expect(useStore.getState().inspect.stack[0]?.fetchedAtTick).toBe(2); // still stale

    // ...but popping back to the hex frame re-focuses it, and its cached
    // tick (2) is stale against the current tick (3), so it refetches lazily.
    useStore.getState().inspect.popTo(0);
    await settle();
    expect(requestLog.filter((r) => r === "GET inspector:hex")).toHaveLength(3);
    expect(useStore.getState().inspect.stack[0]?.fetchedAtTick).toBe(3);
  });
});

describe("stale-response guard", () => {
  it("a superseded push's slow response never lands on the frame that replaced it", async () => {
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await settle();
    useStore.getState().inspect.clear();
    useStore.getState().inspect.push({ kind: "org", id: "o2" });
    await settle();

    expect(useStore.getState().inspect.stack).toHaveLength(1);
    expect(useStore.getState().inspect.stack[0]?.ref).toEqual({ kind: "org", id: "o2" });
    expect(useStore.getState().inspect.stack[0]?.data).not.toBeNull();
  });
});
