import { describe, it, expect } from "vitest";
import { adaptOrg } from "./org";

describe("adaptOrg", () => {
  it("renders org fields with consciousness null-honesty when the org has no computed distribution (ported from InspectorPanel.test.tsx)", () => {
    const node = adaptOrg(
      { kind: "org", id: "org-1" },
      {
        class_character: "proletarian",
        budget: 42.5,
        cohesion: 0.6,
        heat: 0.3,
        consciousness: null,
      },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Class Character")?.value).toBe("proletarian");
    const consciousnessRow = rows.find((r) => r.label === "Consciousness");
    expect(consciousnessRow?.value).toBeNull();
    expect(consciousnessRow?.composition).toBeUndefined();
  });

  it("renders the real consciousness breakdown as a composition row when present (ported)", () => {
    const node = adaptOrg(
      { kind: "org", id: "org-1" },
      { consciousness: { liberal: 0.1, fascist: 0.05, revolutionary: 0.85 } },
    );
    const rows = node.sections[0]?.rows ?? [];
    const consciousnessRow = rows.find((r) => r.label === "Consciousness");
    expect(consciousnessRow?.composition).toEqual([
      { key: "Revolutionary", value: 0.85, color: "text-laser" },
      { key: "Liberal", value: 0.1, color: "text-cadre" },
      { key: "Fascist", value: 0.05, color: "text-rupture" },
    ]);
  });

  it("attaches explain refs for the four org-scoped provenance-mirror metrics regardless of raw-field presence", () => {
    const node = adaptOrg({ kind: "org", id: "org-1" }, {});
    const rows = node.sections[0]?.rows ?? [];
    for (const label of [
      "Labor Aristocracy Ratio",
      "Revolution Probability",
      "Acquiescence Probability",
      "Consciousness Drift",
    ]) {
      const row = rows.find((r) => r.label === label);
      expect(row?.ref?.kind).toBe("metric");
      expect(row?.ref?.scope).toBe("org:org-1");
      expect(row?.value).toBeNull(); // honest: this endpoint carries no live copy of it
    }
  });

  it("titles from the org's own name, falling back to id", () => {
    expect(adaptOrg({ kind: "org", id: "o1" }, { name: "Wayne County Committee" }).title).toBe(
      "Wayne County Committee",
    );
    expect(adaptOrg({ kind: "org", id: "o1" }, {}).title).toBe("o1");
  });

  it("falls back budget to funds (StubEngineBridge's canned field name)", () => {
    const node = adaptOrg({ kind: "org", id: "org-1" }, { funds: 100.0 });
    expect(node.sections[0]?.rows.find((r) => r.label === "Budget")?.value).toBe(100.0);
  });
});
