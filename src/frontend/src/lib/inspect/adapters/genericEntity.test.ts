import { describe, it, expect } from "vitest";
import { adaptNode } from "./node";
import { adaptEdge } from "./edge";
import { adaptCommunity } from "./community";

describe("generic entity adapters (node/edge/community)", () => {
  it("adaptNode dumps whatever fields the payload carries", () => {
    const node = adaptNode({ kind: "node", id: "n1" }, { type: "node", details: "Stub details." });
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "type")?.value).toBe("node");
    expect(rows.find((r) => r.label === "details")?.value).toBe("Stub details.");
  });

  it("adaptEdge honestly reports an empty payload rather than fabricating rows", () => {
    const node = adaptEdge({ kind: "edge", id: "e1" }, {});
    expect(node.sections[0]?.rows).toEqual([{ label: "Detail", value: null, format: "raw" }]);
  });

  it("adaptCommunity renders numeric fields with decimal2 format", () => {
    const node = adaptCommunity({ kind: "community", id: "c1" }, { member_count: 12 });
    expect(node.sections[0]?.rows.find((r) => r.label === "member_count")).toEqual({
      label: "member_count",
      value: 12,
      format: "decimal2",
    });
  });

  it("titles from ref.label when set (same-name discipline)", () => {
    const node = adaptNode({ kind: "node", id: "n1", label: "Linked Institution" }, { id: "n1" });
    expect(node.title).toBe("Linked Institution");
  });

  describe("Track 1 Task 7 — no fogged dead ends", () => {
    it("attaches a fog ref to a masked (vision_masked) field's row", () => {
      const node = adaptNode(
        { kind: "node", id: "org-2" },
        {
          type: "organization",
          name: "Rival Union",
          heat: null,
          vision_masked: ["heat"],
          vision_approx: [],
        },
      );
      const rows = node.sections[0]?.rows ?? [];
      const heatRow = rows.find((r) => r.label === "heat");
      expect(heatRow?.value).toBeNull();
      expect(heatRow?.ref).toEqual({
        kind: "fog",
        id: "organization:org-2:heat",
        label: "Repression Heat",
        inline: {
          field: "heat",
          nodeType: "organization",
          nodeId: "org-2",
          nodeName: "Rival Union",
        },
      });
    });

    it("does not attach a fog ref to a field that is null but NOT masked (honest absence, not fog)", () => {
      const node = adaptNode(
        { kind: "node", id: "n1" },
        { type: "territory", some_unrelated_field: null, vision_masked: [], vision_approx: [] },
      );
      const rows = node.sections[0]?.rows ?? [];
      const row = rows.find((r) => r.label === "some_unrelated_field");
      expect(row?.value).toBeNull();
      expect(row?.ref).toBeUndefined();
    });

    it("never renders vision_masked/vision_approx themselves as raw dump rows", () => {
      const node = adaptNode(
        { kind: "node", id: "t1" },
        { type: "territory", heat: null, vision_masked: ["heat"], vision_approx: [] },
      );
      const rows = node.sections[0]?.rows ?? [];
      expect(rows.find((r) => r.label === "vision_masked")).toBeUndefined();
      expect(rows.find((r) => r.label === "vision_approx")).toBeUndefined();
    });
  });
});
