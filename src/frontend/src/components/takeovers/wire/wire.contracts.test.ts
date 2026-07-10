/**
 * Wire-family contracts (spec-111 design-sync findings, 2026-07-10).
 *
 * jsdom cannot compute styles from imported stylesheets, so these pin the
 * two defects at their source-of-truth files:
 *  1. The triptych columns must claim equal flex space — without
 *     `flex: 1 1 0` on `.col-wrap`, columns shrink to natural content
 *     width (IntelColumn wraps mid-word when populated; the row collapses
 *     to bare void when story is null).
 *  2. `EMPTY_WIRE_FEED` filter colors must reference *defined* tokens —
 *     the palette ships only `--babylon-*`-prefixed custom properties, so
 *     an unprefixed `var(--rent)` silently resolves to nothing.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { EMPTY_WIRE_FEED } from "@/types/wire";

// vitest cwd is src/frontend (the config home); import.meta.url is not a
// file: URL under vitest's module runner, so anchor on cwd instead.
const wireCss = readFileSync(
  resolve(process.cwd(), "src/components/takeovers/wire/wire.css"),
  "utf8",
);

describe("wire.css .col-wrap", () => {
  it("distributes triptych space equally (flex: 1 1 0)", () => {
    const colWrap = /\.col-wrap\s*\{([^}]*)\}/.exec(wireCss)?.[1] ?? "";
    expect(colWrap).toMatch(/flex:\s*1 1 0/);
  });
});

describe("EMPTY_WIRE_FEED filter colors", () => {
  it("reference only defined --babylon-* tokens", () => {
    for (const filter of EMPTY_WIRE_FEED.filters) {
      expect(filter.color, `${filter.id} color`).toMatch(/^var\(--babylon-[a-z-]+\)$/);
    }
  });
});
