import { describe, it, expect } from "vitest";
import { adaptHex } from "./hex";

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
