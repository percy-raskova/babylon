import { describe, it, expect } from "vitest";
import { inspectorKindForEvent } from "./inspectorMapping";
import type { ClassifiedEvent } from "@/types/game";
import { makeEvent } from "@/test/fixtures";

function classified(overrides: Partial<ClassifiedEvent>): ClassifiedEvent {
  return {
    id: "1-0",
    event: makeEvent(),
    severity: "informational",
    tick: 1,
    read: false,
    linkedEntityId: null,
    linkedEntityType: null,
    ...overrides,
  };
}

describe("inspectorKindForEvent", () => {
  it("maps territory -> hex", () => {
    expect(
      inspectorKindForEvent(classified({ linkedEntityType: "territory", linkedEntityId: "t1" })),
    ).toBe("hex");
  });

  it("maps organization -> org", () => {
    expect(
      inspectorKindForEvent(classified({ linkedEntityType: "organization", linkedEntityId: "o1" })),
    ).toBe("org");
  });

  it("maps institution -> node (no dedicated inspector kind)", () => {
    expect(
      inspectorKindForEvent(classified({ linkedEntityType: "institution", linkedEntityId: "i1" })),
    ).toBe("node");
  });

  it("maps hyperedge -> community", () => {
    expect(
      inspectorKindForEvent(classified({ linkedEntityType: "hyperedge", linkedEntityId: "h1" })),
    ).toBe("community");
  });

  it("returns null when there is no linked entity", () => {
    expect(inspectorKindForEvent(classified({}))).toBeNull();
  });

  it("returns null when linkedEntityType is set but id is missing", () => {
    expect(
      inspectorKindForEvent(classified({ linkedEntityType: "territory", linkedEntityId: null })),
    ).toBeNull();
  });
});
