/**
 * Unit tests for the lens registry (spec-113 Lane B) — availability
 * degradation, group ordering, legend metadata, and the DEFAULT_LENS sync
 * guard.
 */

import { describe, it, expect } from "vitest";
import {
  LENS_REGISTRY,
  DEFAULT_LENS_ID,
  lensDefForLens,
  availableLensRegistry,
  lensRegistryByGroup,
} from "./registry";
import { LENS_GROUPS } from "./groups";
import { DEFAULT_LENS, lensKey } from "@/lib/lens";

describe("LENS_REGISTRY", () => {
  it("every id is unique", () => {
    const ids = LENS_REGISTRY.map((d) => d.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every entry's group is a registered LensGroupId", () => {
    const groupIds = new Set(LENS_GROUPS.map((g) => g.id));
    for (const def of LENS_REGISTRY) {
      expect(groupIds.has(def.group)).toBe(true);
    }
  });

  it("LENS_REGISTRY[0] is the imperial_rent lens, matching DEFAULT_LENS_ID and lib/lens.ts's DEFAULT_LENS", () => {
    expect(LENS_REGISTRY[0]?.id).toBe(DEFAULT_LENS_ID);
    expect(lensKey(LENS_REGISTRY[0]!.toLens())).toBe(lensKey(DEFAULT_LENS));
  });

  it("includes the class_composition and solidarity_index additions (spec-113 Lane B/D)", () => {
    expect(LENS_REGISTRY.some((d) => d.id === "class_composition")).toBe(true);
    expect(LENS_REGISTRY.some((d) => d.id === "solidarity_index")).toBe(true);
  });
});

describe("lensDefForLens", () => {
  it("resolves a mode lens back to its registry entry", () => {
    expect(lensDefForLens({ kind: "heat" })?.id).toBe("heat");
  });

  it("resolves a metric lens back to its registry entry", () => {
    expect(lensDefForLens({ kind: "metric", metric: "imperial_rent" })?.id).toBe("imperial_rent");
  });

  it("resolves class_composition back to its registry entry", () => {
    expect(lensDefForLens({ kind: "class_composition" })?.id).toBe("class_composition");
  });

  it("returns undefined for a lens with no registry entry (e.g. an unregistered metric)", () => {
    expect(lensDefForLens({ kind: "metric", metric: "occ" })).toBeUndefined();
  });
});

describe("availableWhen degradation (existing balkanization pattern)", () => {
  // Political lenses (stance/faction/collapse) are ALWAYS available — like
  // the old MapModeSelector, the registry never hides them; the "no
  // balkanization data yet" degradation stays fill-level (NO_DATA gray + a
  // "— no data" legend suffix — see mapLensLayers.test.ts), matching prior
  // behavior exactly.
  it("political lenses are available with no balkanization data at all", () => {
    const emptyCtx = { balkanization: { factions: [], sovereigns: [], territory_influence: [] } };
    const available = availableLensRegistry(emptyCtx).map((d) => d.id);
    expect(available).toContain("stance");
    expect(available).toContain("faction");
    expect(available).toContain("collapse");
  });

  it("political lenses are available before any mapData has loaded (no context)", () => {
    const available = availableLensRegistry({}).map((d) => d.id);
    expect(available).toContain("stance");
  });

  it("class_composition degrades honestly when dominant_class isn't in available_metrics", () => {
    const ctx = { availableMetrics: ["heat", "population"] };
    expect(availableLensRegistry(ctx).map((d) => d.id)).not.toContain("class_composition");
  });

  it("solidarity_index degrades honestly when solidarity_index isn't in available_metrics", () => {
    const ctx = { availableMetrics: ["heat", "population"] };
    expect(availableLensRegistry(ctx).map((d) => d.id)).not.toContain("solidarity_index");
  });

  it("heat and habitability are always available (no backend gate)", () => {
    const ctx = { availableMetrics: [] };
    const available = availableLensRegistry(ctx).map((d) => d.id);
    expect(available).toContain("heat");
    expect(available).toContain("habitability");
  });
});

describe("lensRegistryByGroup", () => {
  it("preserves LENS_REGISTRY order within each group", () => {
    const byGroup = lensRegistryByGroup();
    for (const [, defs] of byGroup) {
      const registryIndices = defs.map((d) => LENS_REGISTRY.indexOf(d));
      expect(registryIndices).toEqual([...registryIndices].sort((a, b) => a - b));
    }
  });

  it("every group referenced by a lens has at least one entry", () => {
    const byGroup = lensRegistryByGroup();
    for (const def of LENS_REGISTRY) {
      expect(byGroup.get(def.group)).toContain(def);
    }
  });

  it("filters by availability when a context is passed", () => {
    const ctx = { availableMetrics: ["heat"] }; // dominant_class not advertised
    const byGroup = lensRegistryByGroup(ctx);
    const political = byGroup.get("political") ?? [];
    expect(political.map((d) => d.id)).not.toContain("class_composition");
    expect(political.map((d) => d.id)).toContain("stance");
  });
});

describe("legend metadata", () => {
  it("every ramp-legend lens carries a non-empty stop list", () => {
    for (const def of LENS_REGISTRY) {
      if (def.legend.kind === "ramp") {
        expect(def.legend.stops.length).toBeGreaterThan(1);
      }
    }
  });

  it("every categorical-legend lens carries at least one entry", () => {
    for (const def of LENS_REGISTRY) {
      if (def.legend.kind === "categorical") {
        expect(def.legend.entries.length).toBeGreaterThan(0);
      }
    }
  });

  it("stance/faction share the identical 3-entry categorical legend", () => {
    const stance = LENS_REGISTRY.find((d) => d.id === "stance");
    const faction = LENS_REGISTRY.find((d) => d.id === "faction");
    expect(stance?.legend).toEqual(faction?.legend);
  });

  it("collapse's legend extends stance's with a Contested entry", () => {
    const stance = LENS_REGISTRY.find((d) => d.id === "stance");
    const collapse = LENS_REGISTRY.find((d) => d.id === "collapse");
    if (stance?.legend.kind !== "categorical" || collapse?.legend.kind !== "categorical") {
      throw new Error("expected categorical legends");
    }
    expect(collapse.legend.entries).toHaveLength(stance.legend.entries.length + 1);
    expect(collapse.legend.entries.map((e) => e.label)).toContain("Contested");
  });

  it("class_composition's legend has one entry per SOCIAL_ROLE_COLOR key", () => {
    const def = LENS_REGISTRY.find((d) => d.id === "class_composition");
    if (def?.legend.kind !== "categorical") throw new Error("expected categorical legend");
    expect(def.legend.entries).toHaveLength(8);
  });
});
