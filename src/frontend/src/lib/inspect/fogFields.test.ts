import { describe, it, expect } from "vitest";
import { fogFieldLabel, fogRefFor } from "./fogFields";

describe("fogFieldLabel", () => {
  it("translates a known gated field to its player-legible label", () => {
    expect(fogFieldLabel("solidarity_index")).toBe("Class Solidarity");
    expect(fogFieldLabel("heat")).toBe("Repression Heat");
  });

  it("falls back to the raw field name for an unmapped field (never throws)", () => {
    expect(fogFieldLabel("some_future_field")).toBe("some_future_field");
  });
});

describe("fogRefFor", () => {
  it("returns undefined when the field is not in the masked list", () => {
    expect(fogRefFor("heat", [], "territory", "t1", "Wayne County")).toBeUndefined();
    expect(fogRefFor("heat", ["consciousness"], "territory", "t1", "Wayne County")).toBeUndefined();
  });

  it("builds a fog-kind ref with an inline payload when the field IS masked", () => {
    const ref = fogRefFor(
      "solidarity_index",
      ["solidarity_index"],
      "territory",
      "t1",
      "Wayne County",
    );
    expect(ref).toEqual({
      kind: "fog",
      id: "territory:t1:solidarity_index",
      label: "Class Solidarity",
      inline: {
        field: "solidarity_index",
        nodeType: "territory",
        nodeId: "t1",
        nodeName: "Wayne County",
      },
    });
  });

  it("carries a null nodeName through honestly rather than fabricating one", () => {
    const ref = fogRefFor("heat", ["heat"], "organization", "org-1", null);
    expect(ref?.inline?.nodeName).toBeNull();
  });
});
