import { describe, it, expect } from "vitest";
import { readNumberField, readStringField, readConsciousness } from "./inspectorFields";

describe("readNumberField", () => {
  it("returns the number when present with the right type", () => {
    expect(readNumberField({ heat: 0.4 }, "heat")).toBe(0.4);
  });
  it("returns null when missing", () => {
    expect(readNumberField({}, "heat")).toBeNull();
  });
  it("returns null when data itself is null", () => {
    expect(readNumberField(null, "heat")).toBeNull();
  });
  it("returns null when the field has the wrong type", () => {
    expect(readNumberField({ heat: "0.4" }, "heat")).toBeNull();
  });
});

describe("readStringField", () => {
  it("returns the string when present", () => {
    expect(readStringField({ name: "Wayne County" }, "name")).toBe("Wayne County");
  });
  it("returns null when missing or wrong type", () => {
    expect(readStringField({}, "name")).toBeNull();
    expect(readStringField({ name: 5 }, "name")).toBeNull();
  });
});

describe("readConsciousness", () => {
  it("returns the vector when all three components are numbers", () => {
    expect(
      readConsciousness({ consciousness: { liberal: 0.1, fascist: 0.05, revolutionary: 0.85 } }),
    ).toEqual({ liberal: 0.1, fascist: 0.05, revolutionary: 0.85 });
  });
  it("returns null when consciousness is null (engine has not computed it)", () => {
    expect(readConsciousness({ consciousness: null })).toBeNull();
  });
  it("returns null when consciousness is absent entirely", () => {
    expect(readConsciousness({})).toBeNull();
  });
  it("returns null when a component is missing/malformed", () => {
    expect(readConsciousness({ consciousness: { liberal: 0.1 } })).toBeNull();
  });
});
