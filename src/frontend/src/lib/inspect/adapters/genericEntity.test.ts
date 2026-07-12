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
});
