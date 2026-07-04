/**
 * Consolidation guard (spec-091): one codebase, no legacy siblings.
 *
 * These are source-scan invariants — they fail while the old god-page
 * cluster or the retired react map library remain in the tree, and pin the
 * consolidated state so a future regression re-introducing either fails CI.
 *
 * NOTE: the retired map library's literal name is assembled at runtime
 * (see LIB below) so this guard file itself stays clear of the exact token
 * the `rg` gate scans for.
 */

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Vitest runs with cwd at the Vite root (web/frontend); resolve the src tree
// from there rather than import.meta.url (non-file scheme under Vite).
const SRC = join(process.cwd(), "src");

// The retired library token, assembled so it does not appear verbatim here.
const LIB = "leaf" + "let";

function walk(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walk(full, acc);
    } else if (/\.(ts|tsx)$/.test(entry)) {
      acc.push(full);
    }
  }
  return acc;
}

const ALL_SOURCE = walk(SRC);

const LEGACY_SIBLINGS = [
  "components/ActionPage.tsx",
  "components/GameView.tsx",
  "components/HexMap.tsx",
  "components/IntelPage.tsx",
  "components/OrganizationsPage.tsx",
  "components/OrgDashboard.tsx",
  "components/TimeSeriesPanel.tsx",
  // Legacy panel-Inspector cluster (superseded by IntelPageV2)
  "components/inspector/Inspector.tsx",
];

describe("frontend consolidation (spec-091)", () => {
  it(`no source file imports the retired ${LIB} map library`, () => {
    const importRe = new RegExp(`from\\s+["'](react-)?${LIB}`);
    const assetRe = new RegExp(`["']${LIB}/`);
    const offenders = ALL_SOURCE.filter((f) => {
      const text = readFileSync(f, "utf8");
      return importRe.test(text) || assetRe.test(text);
    });
    expect(offenders).toEqual([]);
  });

  it.each(LEGACY_SIBLINGS)("legacy sibling %s is deleted", (rel) => {
    expect(existsSync(join(SRC, rel))).toBe(false);
  });

  it("the retired /dev/hexmap DevHarness is removed", () => {
    // The harness existed solely to render the retired map component; the
    // live deck.gl map now ships first-class on Briefing (spec-091 US2).
    expect(existsSync(join(SRC, "DevHarness.tsx"))).toBe(false);
  });
});
