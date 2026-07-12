/**
 * Contract tests for the events slice (spec-113 §4.2, DESIGN_BIBLE §5.2):
 * the two-stream toast/tray model.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { makeEvent } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
});

describe("events slice — ingest", () => {
  it("dedupes by tick — a second ingest of the same tick is a no-op", () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1 })]);
    expect(useStore.getState().events.toasts).toHaveLength(1);

    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1 })]);
    expect(useStore.getState().events.toasts).toHaveLength(1);
    expect(useStore.getState().events.ingestedTicks).toEqual([1]);
  });

  it("pops one persistent toast per critical event", () => {
    useStore
      .getState()
      .events.ingest(1, [
        makeEvent({ type: "rupture", tick: 1, id: "e1" }),
        makeEvent({ type: "sovereign_collapse", tick: 1, id: "e2" }),
      ]);

    const { toasts } = useStore.getState().events;
    expect(toasts).toHaveLength(2);
    expect(toasts.every((t) => t.severity === "critical" && t.lifetime === "persistent")).toBe(
      true,
    );
    expect(toasts.every((t) => t.events.length === 1)).toBe(true);
  });

  it("batches same-tick notable events into one expandable ephemeral toast", () => {
    useStore
      .getState()
      .events.ingest(2, [
        makeEvent({ type: "uprising", tick: 2, id: "e1" }),
        makeEvent({ type: "excessive_force", tick: 2, id: "e2" }),
      ]);

    const { toasts } = useStore.getState().events;
    expect(toasts).toHaveLength(1);
    expect(toasts[0]!.severity).toBe("notable");
    expect(toasts[0]!.lifetime).toBe("ephemeral");
    expect(toasts[0]!.events).toHaveLength(2);
  });

  it("never toasts the ambient stream (informational-derived events)", () => {
    useStore.getState().events.ingest(3, [makeEvent({ type: "value_transfer", tick: 3 })]);
    expect(useStore.getState().events.toasts).toHaveLength(0);
    // Still recorded as ingested — the dedup guard doesn't depend on toasting.
    expect(useStore.getState().events.ingestedTicks).toEqual([3]);
  });

  it("skips muted categories entirely — no toast, no tray entry", () => {
    useStore.getState().events.toggleMuteCategory("struggle");
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1 })]);

    expect(useStore.getState().events.toasts).toHaveLength(0);
    expect(useStore.getState().events.tray).toHaveLength(0);
  });
});

describe("events slice — dismiss/restore (recoverable tray)", () => {
  it("dismissToast moves a toast into the tray, not away entirely", () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    const id = useStore.getState().events.toasts[0]!.id;

    useStore.getState().events.dismissToast(id);

    expect(useStore.getState().events.toasts).toHaveLength(0);
    expect(useStore.getState().events.tray).toHaveLength(1);
    expect(useStore.getState().events.tray[0]!.id).toBe(id);
  });

  it("restoreToast pulls a tray entry back into the active queue", () => {
    useStore.getState().events.ingest(1, [makeEvent({ type: "rupture", tick: 1, id: "e1" })]);
    const id = useStore.getState().events.toasts[0]!.id;
    useStore.getState().events.dismissToast(id);

    useStore.getState().events.restoreToast(id);

    expect(useStore.getState().events.tray).toHaveLength(0);
    expect(useStore.getState().events.toasts).toHaveLength(1);
    expect(useStore.getState().events.toasts[0]!.id).toBe(id);
  });

  it("dismissing an unknown id is a safe no-op", () => {
    useStore.getState().events.dismissToast("does-not-exist");
    expect(useStore.getState().events.toasts).toHaveLength(0);
    expect(useStore.getState().events.tray).toHaveLength(0);
  });
});

describe("events slice — per-category mute", () => {
  it("toggleMuteCategory adds then removes a category", () => {
    useStore.getState().events.toggleMuteCategory("economy");
    expect(useStore.getState().events.mutedCategories).toEqual(["economy"]);

    useStore.getState().events.toggleMuteCategory("economy");
    expect(useStore.getState().events.mutedCategories).toEqual([]);
  });
});
