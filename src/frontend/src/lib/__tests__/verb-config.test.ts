/**
 * Tests for verb-config — Article V verb catalog invariants.
 *
 * Target resolution and parameter schemas moved to `@/lib/verbs`
 * (VERB_REGISTRY, live-endpoint driven) — see verbs.test.ts and
 * payloads.test.ts. This file pins the static metadata invariants.
 */

import { describe, it, expect } from "vitest";
import { DISABLED_VERBS, SUPPORTED_VERBS, VERBS } from "@/lib/verb-config";
import { VERB_NAMES } from "@/lib/verbs";

const VALID_TARGET_TYPES = [
  "community",
  "territory",
  "org",
  "any",
  "org_or_territory",
  "territory_or_community",
];

describe("VERBS catalog", () => {
  it("contains all 9 constitutional verbs with unique keys", () => {
    expect(VERBS).toHaveLength(9);
    expect(new Set(VERBS.map((v) => v.verb)).size).toBe(9);
  });

  it("matches the VERB_REGISTRY key set exactly", () => {
    expect([...VERBS.map((v) => v.verb)].sort()).toEqual(VERB_NAMES);
  });

  it("every verb has a valid target_type", () => {
    for (const v of VERBS) {
      expect(VALID_TARGET_TYPES).toContain(v.target_type);
    }
  });

  it("every verb has label, glyph, cost_label, and desc", () => {
    for (const v of VERBS) {
      expect(v.label).toBeTruthy();
      expect(v.glyph).toBeTruthy();
      expect(v.cost_label).toBeTruthy();
      expect(v.desc).toBeTruthy();
    }
  });
});

describe("SUPPORTED_VERBS / DISABLED_VERBS", () => {
  // AW3-R1 (2026-07-15): all 9 canonical verbs now have real, registered
  // engine resolvers (babylon.engine.actions.VERB_RESOLVERS, pinned by
  // tests/contract/verbs/test_registry.py) dispatched end-to-end from
  // POST /api/games/{id}/actions/{verb}/. Spec 061 FR-025's disabled set
  // is resolved — DISABLED_VERBS is empty, kept only as a mechanism for a
  // future verb that ships without a resolver.
  it("is currently empty — every canonical verb has a real engine handler", () => {
    expect(DISABLED_VERBS.size).toBe(0);
  });

  it("SUPPORTED_VERBS equals the full VERBS catalog while DISABLED_VERBS is empty", () => {
    expect(SUPPORTED_VERBS).toHaveLength(VERBS.length);
    expect(SUPPORTED_VERBS).toEqual(VERBS);
  });

  it("excludes exactly the disabled set, whatever it is", () => {
    expect(SUPPORTED_VERBS).toHaveLength(VERBS.length - DISABLED_VERBS.size);
    for (const v of SUPPORTED_VERBS) {
      expect(DISABLED_VERBS.has(v.verb)).toBe(false);
    }
  });

  it("every disabled verb is a real catalog verb", () => {
    const keys = new Set(VERBS.map((v) => v.verb));
    for (const d of DISABLED_VERBS) {
      expect(keys.has(d as (typeof VERBS)[number]["verb"])).toBe(true);
    }
  });
});
