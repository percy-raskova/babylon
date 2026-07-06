/**
 * Token-contract test — spec-090 Cold Collapse design-system migration.
 *
 * The executable contract between the shipped design layer and the ratified
 * canon (`design/mockups/colors_and_type.css` + `preview/colors-data.html`).
 * Written RED-first (TDD): before the migration this fails on gold/Inter tokens
 * and on the missing `DATA_RAMPS` / `getLensRampStops` exports.
 *
 * See specs/090-cold-collapse/contracts/token-contract.md (C1..C6).
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";

import { DATA_RAMPS, getColorScale } from "./colors";
import { getLensRampStops, LENS_RAMP_STOPS, LENS_DEFINITIONS } from "@/lib/lensDefinitions";
import type { LensId, MapLayer } from "@/types/game";

// Vitest runs with cwd = web/frontend (see vitest.config.ts / package.json).
const cssPath = path.resolve(process.cwd(), "src/index.css");
const css = readFileSync(cssPath, "utf-8");
const cssLower = css.toLowerCase();

/** Canon palette tokens (design/mockups/colors_and_type.css). */
const CANON_TOKENS: Record<string, string> = {
  "--babylon-void": "#06070b",
  "--babylon-tar": "#0d1016",
  "--babylon-concrete": "#11141c",
  "--babylon-rebar": "#1a1f2a",
  "--babylon-wet-steel": "#28303d",
  "--babylon-rust": "#3a3530",
  "--babylon-bone": "#d8dce0",
  "--babylon-fog": "#8a93a0",
  "--babylon-ash": "#5e6470",
  "--babylon-shroud": "#3d4250",
  "--babylon-spire": "#4dd9e6",
  "--babylon-spire-dim": "#2a8a93",
  "--babylon-laser": "#ff3344",
  "--babylon-thermal": "#b8321f",
  "--babylon-rupture": "#d4a02c",
  "--babylon-cadre": "#6b8fb5",
  "--babylon-solidarity": "#5fbf7a",
  "--babylon-rent": "#8b4d9e",
  "--babylon-heat": "#d97a2c",
  "--babylon-population": "#7a6db8",
};

/** Canon luminance-monotonic ramps (design/mockups/preview/colors-data.html). */
const CANON_RAMPS: Record<string, string[]> = {
  heat: ["#0d1016", "#3a3530", "#7a4720", "#b8581f", "#d97a2c", "#ff3344"],
  consciousness: ["#0d1016", "#1f2c3d", "#345670", "#4a86a0", "#6bbcc8", "#4dd9e6"],
  rent: ["#0d1016", "#2e2236", "#56356b", "#8b4d9e", "#a83a78", "#b8321f"],
  biocapacity: ["#b8321f", "#7a3525", "#3d4250", "#3a6b48", "#5fbf7a"],
  wealth: ["#0d1016", "#2a251f", "#4d3f28", "#8a6a2a", "#d4a02c"],
  population: ["#0d1016", "#23223a", "#3d3868", "#5a4f95", "#7a6db8", "#a89dd0"],
};

describe("C1 — Cold Collapse palette tokens present in index.css", () => {
  for (const [name, value] of Object.entries(CANON_TOKENS)) {
    it(`${name} = ${value}`, () => {
      const re = new RegExp(`${name}\\s*:\\s*${value}`, "i");
      expect(cssLower).toMatch(re);
    });
  }
});

describe("C2 — type-stack tokens name the canon primaries", () => {
  it("--font-mono is JetBrains Mono", () => {
    expect(cssLower).toMatch(/--font-mono\s*:[^;]*jetbrains mono/i);
  });
  it("--font-sans is Space Grotesk", () => {
    expect(cssLower).toMatch(/--font-sans\s*:[^;]*space grotesk/i);
  });
  it("--font-display is Redaction", () => {
    expect(cssLower).toMatch(/--font-display\s*:[^;]*redaction/i);
  });
  it("--font-pixel is Departure Mono", () => {
    expect(cssLower).toMatch(/--font-pixel\s*:[^;]*departure mono/i);
  });
});

describe("C3 — banned fonts absent", () => {
  it("does not mention Inter", () => {
    expect(cssLower).not.toMatch(/\binter\b/);
  });
  it("does not mention Roboto Mono", () => {
    expect(cssLower).not.toMatch(/roboto mono/);
  });
});

describe("C4 — self-hosted @font-face, no Google Fonts at runtime", () => {
  it("declares @font-face rules", () => {
    expect(cssLower).toMatch(/@font-face/);
  });
  it("font sources are local /fonts/*.woff2", () => {
    expect(cssLower).toMatch(/url\(["']?\/fonts\/[^)]*\.woff2/i);
  });
  it("no request to Google Fonts hosts", () => {
    expect(cssLower).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com/);
  });
});

describe("C5 — DATA_RAMPS match canon stops", () => {
  for (const [layer, stops] of Object.entries(CANON_RAMPS)) {
    it(`${layer} ramp equals canon`, () => {
      expect(DATA_RAMPS[layer as keyof typeof DATA_RAMPS].map((s) => s.toLowerCase())).toEqual(
        stops,
      );
    });
  }

  it("sequential ramps start at the darkest substrate #0d1016", () => {
    for (const layer of ["heat", "consciousness", "rent", "wealth", "population"] as const) {
      expect((DATA_RAMPS[layer][0] ?? "").toLowerCase()).toBe("#0d1016");
    }
  });

  it("no ramp carries the retired gold rainbow interior (#c8a860)", () => {
    for (const stops of Object.values(DATA_RAMPS)) {
      expect(stops.map((s) => s.toLowerCase())).not.toContain("#c8a860");
    }
  });

  it("getColorScale returns a function for every MapLayer", () => {
    const layers: MapLayer[] = [
      "heat",
      "consciousness",
      "wealth",
      "rent",
      "biocapacity",
      "population",
      "profit_rate",
      "exploitation_rate",
      "occ",
      "imperial_rent",
      "org_presence",
    ];
    for (const l of layers) {
      expect(typeof getColorScale(l)).toBe("function");
    }
  });
});

describe("C6 — each lens resolves to its canon ramp", () => {
  // Independently-stated expectation (NOT read back from LENS_DEFINITIONS): the
  // canonical lens→layer binding. Pinning this here means a regression that
  // repoints a lens's primaryLayer fails C6 instead of silently passing a
  // read-back tautology (spec-090 residual e).
  const EXPECTED_PRIMARY_LAYER: Record<LensId, keyof typeof DATA_RAMPS> = {
    economic: "rent",
    political: "consciousness",
    social: "heat",
    strategic: "consciousness",
  };

  const lenses: LensId[] = ["economic", "political", "social", "strategic"];
  for (const id of lenses) {
    it(`${id} lens is bound to the ${EXPECTED_PRIMARY_LAYER[id]} layer + ramp`, () => {
      const expected = EXPECTED_PRIMARY_LAYER[id];
      // 1) the mapping itself is pinned to the independent expectation
      expect(LENS_DEFINITIONS[id].primaryLayer).toBe(expected);
      // 2) the resolved ramp matches that layer's canon ramp
      expect(getLensRampStops(id)).toEqual(DATA_RAMPS[expected]);
      expect(LENS_RAMP_STOPS[id]).toEqual(DATA_RAMPS[expected]);
    });
  }
});
