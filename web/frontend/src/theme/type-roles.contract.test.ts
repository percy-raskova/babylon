/**
 * Type-role token contract (spec-090 residual d).
 *
 * The 35 canon "SEMANTIC TYPE ROLES" from design/mockups/colors_and_type.css
 * (h1/h2/h3/body/label/data/code × their font/size/weight/color/tracking…)
 * must be defined in index.css so components bind to a role rather than raw
 * sizes. This source-scan pins their presence and the canon accents
 * (h3/data → spire, code → solidarity).
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const INDEX_CSS = readFileSync(join(process.cwd(), "src/index.css"), "utf8");

// The exact 35 role tokens ported from the canon.
const ROLE_TOKENS = [
  "--h1-font",
  "--h1-size",
  "--h1-weight",
  "--h1-color",
  "--h1-tracking",
  "--h2-font",
  "--h2-size",
  "--h2-weight",
  "--h2-color",
  "--h2-tracking",
  "--h3-font",
  "--h3-size",
  "--h3-weight",
  "--h3-color",
  "--h3-tracking",
  "--body-font",
  "--body-size",
  "--body-weight",
  "--body-color",
  "--body-leading",
  "--label-font",
  "--label-size",
  "--label-weight",
  "--label-color",
  "--label-tracking",
  "--label-transform",
  "--data-font",
  "--data-size",
  "--data-weight",
  "--data-color",
  "--code-font",
  "--code-size",
  "--code-bg",
  "--code-color",
  "--code-border",
];

describe("semantic type-role tokens (Constitution VIII)", () => {
  it("defines all 35 canon type-role tokens", () => {
    expect(ROLE_TOKENS).toHaveLength(35);
    const missing = ROLE_TOKENS.filter((t) => !INDEX_CSS.includes(`${t}:`));
    expect(missing).toEqual([]);
  });

  it("binds heading/data accents to spire and code to solidarity (Cold Collapse)", () => {
    expect(INDEX_CSS).toMatch(/--h3-color:\s*var\(--babylon-spire\)/);
    expect(INDEX_CSS).toMatch(/--data-color:\s*var\(--babylon-spire\)/);
    expect(INDEX_CSS).toMatch(/--code-color:\s*var\(--babylon-solidarity\)/);
  });
});
