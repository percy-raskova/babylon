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

  describe("Vanguard Resources section (W1.3)", () => {
    const vanguardData = {
      vanguard: {
        cadre_labor: 1.0,
        sympathizer_labor: 4.0,
        reputation: null,
        budget: 100.0,
        heat: 0.0,
        max_cadre_labor: 1.0,
        max_sympathizer_labor: 5.0,
      },
    };

    it("renders Cadre Labor and Sympathizer Labor as [current, headroom] composition bars", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, vanguardData);
      const section = node.sections.find((s) => s.label === "Vanguard Resources");
      expect(section).toBeDefined();

      const cadre = section?.rows.find((r) => r.label === "Cadre Labor");
      expect(cadre?.composition).toEqual([
        { key: "Current", value: 1.0, color: "text-spire" },
        { key: "Headroom", value: 0.0, color: "text-ash" },
      ]);

      const sympathizer = section?.rows.find((r) => r.label === "Sympathizer Labor");
      expect(sympathizer?.composition).toEqual([
        { key: "Current", value: 4.0, color: "text-spire" },
        { key: "Headroom", value: 1.0, color: "text-ash" },
      ]);
    });

    it("renders Reputation as null (existing no-data state), never a fabricated 0", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, vanguardData);
      const section = node.sections.find((s) => s.label === "Vanguard Resources");
      const reputation = section?.rows.find((r) => r.label === "Reputation");
      expect(reputation?.value).toBeNull();
      expect(reputation?.composition).toBeUndefined();
    });

    it("omits the Vanguard Resources section entirely for a non-player org", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, { vanguard: null });
      expect(node.sections.find((s) => s.label === "Vanguard Resources")).toBeUndefined();
    });
  });

  describe("Trap Detection section (W1.3)", () => {
    const trapsData = {
      traps: {
        liberal: {
          trap_type: "liberal",
          severity: "mild",
          score: 0.35,
          indicators: [],
          ticks_at_moderate: 0,
        },
        ultra_left: {
          trap_type: "ultra_left",
          severity: "none",
          score: 0.1,
          indicators: [],
          ticks_at_moderate: 0,
        },
        rightist: {
          trap_type: "rightist",
          severity: "none",
          score: 0.05,
          indicators: [],
          ticks_at_moderate: 0,
        },
        active_trap: "liberal",
        game_over_trap: null,
      },
    };

    it("renders an Active Trap status row naming the trap and severity", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, trapsData);
      const section = node.sections.find((s) => s.label === "Trap Detection");
      expect(section).toBeDefined();
      expect(section?.rows.find((r) => r.label === "Active Trap")?.value).toBe("Liberal (mild)");
    });

    it("renders 'none' for the Active Trap row when no trap is active", () => {
      const node = adaptOrg(
        { kind: "org", id: "org-1" },
        { traps: { ...trapsData.traps, active_trap: null } },
      );
      const section = node.sections.find((s) => s.label === "Trap Detection");
      expect(section?.rows.find((r) => r.label === "Active Trap")?.value).toBe("none");
    });

    it("renders Liberal/Ultra-Left/Rightist score rows as percent-formatted", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, trapsData);
      const section = node.sections.find((s) => s.label === "Trap Detection");
      expect(section?.rows.find((r) => r.label === "Liberal")).toMatchObject({
        value: 0.35,
        format: "percent",
      });
      expect(section?.rows.find((r) => r.label === "Ultra-Left")).toMatchObject({
        value: 0.1,
        format: "percent",
      });
      expect(section?.rows.find((r) => r.label === "Rightist")).toMatchObject({
        value: 0.05,
        format: "percent",
      });
    });

    it("omits the Game-Over Trap row when no trap has gone severe", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, trapsData);
      const section = node.sections.find((s) => s.label === "Trap Detection");
      expect(section?.rows.find((r) => r.label === "Game-Over Trap")).toBeUndefined();
    });

    it("shows a Game-Over Trap warning row only when a trap has gone severe", () => {
      const node = adaptOrg(
        { kind: "org", id: "org-1" },
        { traps: { ...trapsData.traps, game_over_trap: "ultra_left" } },
      );
      const section = node.sections.find((s) => s.label === "Trap Detection");
      expect(section?.rows.find((r) => r.label === "Game-Over Trap")?.value).toBe("Ultra-Left");
    });

    it("omits the Trap Detection section entirely for a non-player org", () => {
      const node = adaptOrg({ kind: "org", id: "org-1" }, { traps: null });
      expect(node.sections.find((s) => s.label === "Trap Detection")).toBeUndefined();
    });
  });
});
