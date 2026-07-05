/**
 * Contract test: wire feed endpoint (spec 094).
 *
 * Pins the WireFeed response shape that `useWire` relies on:
 * `{status: "ok", data: WireFeed}` where WireFeed carries
 * meta/index/euphemisms/story/filters per the contract in
 * `specs/094-the-wire/contracts/wire.yaml`.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse } from "@/types/game";
import type { WireFeed } from "@/types/wire";

const GAME_ID = "wayne-county-001";

describe("wire contract (spec 094)", () => {
  it("GET /api/games/:id/wire/ returns WireFeed", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/wire/`, { credentials: "include" });
    const body = (await res.json()) as ApiResponse<WireFeed>;

    expect(body.status).toBe("ok");
    const feed = body.data;

    // meta
    expect(typeof feed.meta.tick).toBe("number");
    expect(typeof feed.meta.session).toBe("string");
    expect(typeof feed.meta.operator).toBe("string");

    // index
    expect(Array.isArray(feed.index)).toBe(true);
    for (const entry of feed.index) {
      expect(typeof entry.id).toBe("string");
      expect(typeof entry.tick).toBe("number");
      expect(typeof entry.slug).toBe("string");
      expect(typeof entry.hed.c).toBe("string");
      expect(typeof entry.hed.l).toBe("string");
      expect(typeof entry.hed.i).toBe("string");
      expect(["critical", "warning", "info"]).toContain(entry.severity);
    }

    // euphemisms
    expect(typeof feed.euphemisms).toBe("object");
    for (const [, entry] of Object.entries(feed.euphemisms)) {
      expect(typeof entry.c).toBe("string");
      expect(typeof entry.l).toBe("string");
      expect(["ownership", "advertising", "sourcing", "flak", "ideology"]).toContain(entry.filter);
      expect(typeof entry.note).toBe("string");
    }

    // filters — exactly 5
    expect(feed.filters).toHaveLength(5);
    const filterIds = new Set(feed.filters.map((f) => f.id));
    expect(filterIds.has("ownership")).toBe(true);
    expect(filterIds.has("advertising")).toBe(true);
    expect(filterIds.has("sourcing")).toBe(true);
    expect(filterIds.has("flak")).toBe(true);
    expect(filterIds.has("ideology")).toBe(true);

    // story (may be null for empty feeds, but the fixture has one)
    if (feed.story) {
      expect(typeof feed.story.id).toBe("string");
      expect(typeof feed.story.location).toBe("string");
      expect(feed.story.continental).toBeDefined();
      expect(feed.story.liberated).toBeDefined();
      expect(feed.story.intel).toBeDefined();
    }
  });
});
