import { describe, it, expect } from "vitest";
import { adaptHex, territoryToHexInline } from "./hex";
import type { TerritoryState } from "@/types/game";

/** A fully-populated per-hex TerritoryState (the object a map click carries). */
function territoryFixture(overrides: Partial<TerritoryState> = {}): TerritoryState {
  return {
    id: "t1",
    name: "Wayne County",
    h3_index: "87283472bffffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.4,
    sector_type: "urban",
    territory_type: "core",
    profile: "industrial",
    rent_level: 1.2,
    population: 8000,
    under_eviction: false,
    biocapacity: 3.3,
    host_id: null,
    occupant_id: null,
    habitability: 0.8,
    ...overrides,
  };
}

describe("adaptHex", () => {
  it("renders territory fields including habitability (ported from InspectorPanel.test.tsx)", () => {
    const node = adaptHex(
      { kind: "hex", id: "territory-1" },
      { habitability: 0.62, biocapacity: 0.3, heat: 0.4 },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Habitability")?.value).toBe(0.62);
    expect(rows.find((r) => r.label === "Biocapacity")?.value).toBe(0.3);
    expect(rows.find((r) => r.label === "Heat")?.value).toBe(0.4);
  });

  it("titles the frame from county_name when no ref.label was set", () => {
    const node = adaptHex({ kind: "hex", id: "87283..." }, { county_name: "Wayne County" });
    expect(node.title).toBe("Wayne County");
  });

  it("falls back to the ref id when the payload has no county_name", () => {
    const node = adaptHex({ kind: "hex", id: "87283..." }, {});
    expect(node.title).toBe("87283...");
  });

  it("honors ref.label for same-name discipline over the payload's own name", () => {
    const node = adaptHex(
      { kind: "hex", id: "87283...", label: "Profit Rate" },
      { county_name: "Wayne County" },
    );
    expect(node.title).toBe("Profit Rate");
  });

  it("attaches an explain ref to profit_rate (hex is a supported scope)", () => {
    const node = adaptHex({ kind: "hex", id: "87283..." }, { profit_rate: 0.08 });
    const row = node.sections[0]?.rows.find((r) => r.label === "Profit Rate");
    expect(row?.ref).toEqual({
      kind: "metric",
      id: "profit_rate",
      scope: "hex:87283...",
      label: "Profit Rate",
    });
  });

  it("renders 'no data' honestly when the real bridge returns an empty payload", () => {
    const node = adaptHex({ kind: "hex", id: "87283..." }, {});
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Habitability")?.value).toBeNull();
    expect(rows.find((r) => r.label === "Population")?.value).toBeNull();
  });
});

describe("territoryToHexInline", () => {
  it("maps a clicked TerritoryState into the adaptHex RawEntity key shape", () => {
    const raw = territoryToHexInline(territoryFixture());
    expect(raw.county_name).toBe("Wayne County"); // TerritoryState.name -> county_name
    expect(raw.population).toBe(8000);
    expect(raw.heat).toBe(0.4);
    expect(raw.rent_level).toBe(1.2);
    expect(raw.biocapacity).toBe(3.3);
    expect(raw.habitability).toBe(0.8);
  });

  it("omits fields a TerritoryState does not carry, so adaptHex renders them as honest nulls (III.11)", () => {
    const raw = territoryToHexInline(territoryFixture());
    // dominant_class + profit_rate are engine-side enrichments the click has no
    // access to — they must be ABSENT (undefined), never a fabricated value.
    expect("dominant_class" in raw).toBe(false);
    expect("profit_rate" in raw).toBe(false);

    const node = adaptHex({ kind: "hex", id: "t1" }, raw);
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Dominant Class")?.value).toBeNull();
    expect(rows.find((r) => r.label === "Profit Rate")?.value).toBeNull();
    // …while the fields the click DID carry render real values, not "no data".
    expect(rows.find((r) => r.label === "Population")?.value).toBe(8000);
    expect(rows.find((r) => r.label === "Rent Level")?.value).toBe(1.2);
  });

  it("passes a null habitability through as null (never a fabricated 0)", () => {
    const raw = territoryToHexInline(territoryFixture({ habitability: null }));
    const node = adaptHex({ kind: "hex", id: "t1" }, raw);
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Habitability")?.value).toBeNull();
  });
});
