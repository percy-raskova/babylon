import { describe, it, expect } from "vitest";
import { adaptFog } from "./fog";

describe("adaptFog", () => {
  it("names WHAT is unknown using the player-legible label, not the raw field name", () => {
    const node = adaptFog(
      { kind: "fog", id: "territory:t1:solidarity_index", label: "Class Solidarity" },
      { field: "solidarity_index", nodeType: "territory", nodeId: "t1", nodeName: "Wayne County" },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "What")?.value).toBe("Class Solidarity");
    expect(node.title).toBe("Unknown: Class Solidarity");
  });

  it("names WHY using the invariant reach reason, naming the node type", () => {
    const node = adaptFog(
      { kind: "fog", id: "organization:org-2:heat" },
      { field: "heat", nodeType: "organization", nodeId: "org-2", nodeName: "Rival Union" },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Why")?.value).toBe(
      "This organization is outside your organization's reach, and you hold no intelligence on it.",
    );
  });

  it("falls back to a generic subject phrase for an unmapped node type", () => {
    const node = adaptFog(
      { kind: "fog", id: "faction:f1:colonial_stance" },
      { field: "colonial_stance", nodeType: "faction", nodeId: "f1", nodeName: null },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Why")?.value).toContain("This faction is outside");
  });

  it("degrades honestly when inline is malformed/empty, never crashing", () => {
    const node = adaptFog({ kind: "fog", id: "x" }, {});
    expect(node.sections[0]?.rows.length).toBeGreaterThan(0);
    expect(node.title).toContain("Unknown:");
  });

  it("names the subject node so the card is legible without the breadcrumb", () => {
    const node = adaptFog(
      { kind: "fog", id: "territory:t1:heat" },
      { field: "heat", nodeType: "territory", nodeId: "t1", nodeName: "Wayne County" },
    );
    const rows = node.sections[0]?.rows ?? [];
    expect(rows.find((r) => r.label === "Subject")?.value).toBe("Wayne County");
  });
});
