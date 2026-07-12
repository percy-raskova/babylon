/**
 * installerKit tests — the shared button-as-key/selection-grammar class
 * builders every chrome surface composes (DESIGN_BIBLE.md §9b).
 */

import { describe, it, expect } from "vitest";
import {
  keyButtonClass,
  keyButtonMutedClass,
  keyButtonUrgentClass,
  INSTALLER_WELL,
  TITLE_TAB,
} from "./installerKit";

describe("keyButtonClass", () => {
  it("applies the gold inverse-video grammar when selected", () => {
    const cls = keyButtonClass(true);
    expect(cls).toContain("border-accent-gold");
    expect(cls).toContain("bg-accent-gold");
    expect(cls).toContain("text-selection-ink");
  });

  it("applies the idle plate grammar when not selected", () => {
    const cls = keyButtonClass(false);
    expect(cls).not.toContain("bg-accent-gold");
    expect(cls).toContain("bg-plate");
  });

  it("always includes the shared key-button primitive (square + hard shadow)", () => {
    expect(keyButtonClass(true)).toContain("key-button");
    expect(keyButtonClass(false)).toContain("key-button");
  });

  it("appends extra classes verbatim", () => {
    expect(keyButtonClass(false, "px-4 text-xs")).toContain("px-4 text-xs");
  });
});

describe("keyButtonMutedClass", () => {
  it("never carries the selection grammar", () => {
    const cls = keyButtonMutedClass();
    expect(cls).not.toContain("bg-accent-gold");
    expect(cls).toContain("key-button");
  });
});

describe("keyButtonUrgentClass", () => {
  it("carries the crimson urgency grammar, never gold selection", () => {
    const cls = keyButtonUrgentClass();
    expect(cls).toContain("border-accent-crimson");
    expect(cls).toContain("text-accent-crimson");
    expect(cls).not.toContain("bg-accent-gold");
    expect(cls).toContain("key-button");
  });

  it("appends extra classes verbatim", () => {
    expect(keyButtonUrgentClass("px-2")).toContain("px-2");
  });
});

describe("installer anatomy constants", () => {
  it("INSTALLER_WELL references the double-line well utility class", () => {
    expect(INSTALLER_WELL).toBe("installer-well");
  });

  it("TITLE_TAB carries the crimson breaking-border label grammar", () => {
    expect(TITLE_TAB).toContain("text-accent-crimson");
    expect(TITLE_TAB).toContain("uppercase");
  });
});
