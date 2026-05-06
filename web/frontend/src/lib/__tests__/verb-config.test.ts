/**
 * Tests for verb-config — target resolution gating and parameter schemas.
 *
 * These validate Constitution Article IV/V invariants:
 * - hyperedges and dyadic nodes never conflated
 * - each verb returns only its declared target_type
 * - parameter schemas are well-formed
 */

import { describe, it, expect } from "vitest";
import { resolveTargets, getVerbParams, VERBS } from "@/lib/verb-config";

describe("resolveTargets", () => {
  it("returns only community targets for 'community' type", () => {
    const targets = resolveTargets("community");
    expect(targets.length).toBeGreaterThan(0);
    for (const t of targets) {
      expect(t.type).toBe("community");
    }
  });

  it("returns only territory targets for 'territory' type", () => {
    const targets = resolveTargets("territory");
    expect(targets.length).toBeGreaterThan(0);
    for (const t of targets) {
      expect(t.type).toBe("territory");
    }
  });

  it("returns only org targets for 'org' type", () => {
    const targets = resolveTargets("org");
    expect(targets.length).toBeGreaterThan(0);
    for (const t of targets) {
      expect(t.type).toBe("org");
    }
  });

  it("returns orgs (enemy only) and territories for 'org_or_territory'", () => {
    const targets = resolveTargets("org_or_territory");
    const types = new Set(targets.map((t) => t.type));
    expect(types.has("org")).toBe(true);
    expect(types.has("territory")).toBe(true);
    expect(types.has("community")).toBe(false);
    // Enemy orgs only — no player-controlled orgs
    for (const t of targets.filter((t) => t.type === "org")) {
      expect(t.sub).toContain("ENEMY");
    }
  });

  it("returns territories and communities for 'territory_or_community'", () => {
    const targets = resolveTargets("territory_or_community");
    const types = new Set(targets.map((t) => t.type));
    expect(types.has("territory")).toBe(true);
    expect(types.has("community")).toBe(true);
    expect(types.has("org")).toBe(false);
  });

  it("returns all entity types for 'any'", () => {
    const targets = resolveTargets("any");
    const types = new Set(targets.map((t) => t.type));
    expect(types.has("org")).toBe(true);
    expect(types.has("territory")).toBe(true);
    expect(types.has("community")).toBe(true);
    expect(types.has("edge")).toBe(true);
  });

  it("returns empty array for unknown target type", () => {
    const targets = resolveTargets("nonexistent");
    expect(targets).toEqual([]);
  });

  it("every target has required fields", () => {
    for (const verb of VERBS) {
      const targets = resolveTargets(verb.target_type);
      for (const t of targets) {
        expect(t.id).toBeTruthy();
        expect(t.label).toBeTruthy();
        expect(t.sub).toBeTruthy();
        expect(t.color).toBeTruthy();
        expect(t.telemetry).toBeDefined();
      }
    }
  });
});

describe("getVerbParams", () => {
  it("returns non-empty params for every verb", () => {
    for (const verb of VERBS) {
      const params = getVerbParams(verb.verb);
      expect(params.length).toBeGreaterThan(0);
    }
  });

  it("every param has key, label, and kind", () => {
    for (const verb of VERBS) {
      const params = getVerbParams(verb.verb);
      for (const p of params) {
        expect(p.key).toBeTruthy();
        expect(p.label).toBeTruthy();
        expect(["radio", "slider", "toggle"]).toContain(p.kind);
      }
    }
  });

  it("radio params have options array", () => {
    for (const verb of VERBS) {
      const params = getVerbParams(verb.verb);
      for (const p of params.filter((p) => p.kind === "radio")) {
        expect(Array.isArray(p.options)).toBe(true);
        expect(p.options!.length).toBeGreaterThan(0);
      }
    }
  });

  it("slider params have min, max, unit", () => {
    for (const verb of VERBS) {
      const params = getVerbParams(verb.verb);
      for (const p of params.filter((p) => p.kind === "slider")) {
        expect(p.min).toBeDefined();
        expect(p.max).toBeDefined();
        expect(p.unit).toBeTruthy();
        expect(p.max!).toBeGreaterThan(p.min!);
      }
    }
  });
});
