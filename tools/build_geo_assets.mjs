#!/usr/bin/env node
/**
 * build_geo_assets.mjs — TIGER shapefile -> TopoJSON cartographic substrate pipeline.
 *
 * Owned by Lane Carto (spec-113 architecture.md §7; DESIGN_BIBLE.md §2). Regenerate with:
 *
 *   node tools/build_geo_assets.mjs
 *
 * Reads (READ-ONLY source data, never mutated):
 *   /media/user/data/babylon-data/tiger/county/tl_2024_us_county.shp   (3,235 records, NAD83)
 *   /media/user/data/babylon-data/tiger/aiannh/tl_2025_us_aiannh.shp   (867 records, NAD83)
 *
 * Writes:
 *   src/frontend/public/geo/counties.topojson  — de jure county mesh (immutable substrate)
 *   src/frontend/public/geo/states.topojson    — state dissolve (heavier "colonial" borders)
 *   src/frontend/public/geo/nation.topojson    — single CONUS+territories outline (backdrop glow)
 *   src/frontend/public/geo/aiannh.topojson    — AIANNH tribal areas (future sovereignty lens,
 *                                                  best-effort: skipped with a warning if the
 *                                                  source shapefile is unavailable)
 *   src/frontend/public/geo/README.md          — provenance (source, vintage, sizes, regen cmd)
 *
 * DECISION (recorded, Lane Carto, 2026-07-11): natural geography, no AK/HI/PR insets. deck.gl
 * overlays (H3 hexes, flow arcs, org pins) use real lon/lat coordinates; repositioning Alaska
 * or Hawaii into inset boxes would desynchronize every overlay layer from the basemap under it.
 * Default camera framing handles CONUS at scenario start; players can pan/zoom to AK/HI/PR like
 * any other territory. This supersedes DESIGN_BIBLE.md §2.2's inset note for this program.
 *
 * Uses `npx --yes mapshaper` (no GDAL on this box); each stage runs -clean before AND after
 * -simplify so simplification-introduced self-intersections/slivers never reach the shipped
 * asset. Percentages below were tuned empirically against the size budgets in BUDGETS.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.join(REPO_ROOT, "src/frontend/public/geo");

const COUNTY_SHP =
  "/media/user/data/babylon-data/tiger/county/tl_2024_us_county.shp";
const AIANNH_SHP =
  "/media/user/data/babylon-data/tiger/aiannh/tl_2025_us_aiannh.shp";

const COUNTY_VINTAGE = "TIGER/Line 2024 (tl_2024_us_county)";
const AIANNH_VINTAGE = "TIGER/Line 2025 (tl_2025_us_aiannh)";

/** Size budgets from spec-113 §7 / architecture.md task list. */
const BUDGETS = {
  "counties.topojson": 2.5 * 1024 * 1024,
  "states.topojson": 400 * 1024,
  "nation.topojson": 200 * 1024,
  "aiannh.topojson": 600 * 1024,
};

/** Simplification percentages (mapshaper `weighted keep-shapes` interval, tuned to budget). */
const SIMPLIFY_PCT = {
  counties: "6%",
  states: "8%",
  nation: "8%",
  aiannh: "5%",
};

function runMapshaper(args, label) {
  console.log(`\n[build_geo_assets] ${label}`);
  execFileSync("npx", ["--yes", "mapshaper", ...args], { stdio: "inherit" });
}

function checkBudget(file) {
  const full = path.join(OUT_DIR, file);
  if (!existsSync(full)) {
    throw new Error(`Expected output missing: ${file}`);
  }
  const size = statSync(full).size;
  const budget = BUDGETS[file];
  const status = size <= budget ? "OK" : "OVER BUDGET";
  console.log(
    `  ${file}: ${(size / 1024).toFixed(1)} KiB (budget ${(budget / 1024).toFixed(0)} KiB) — ${status}`,
  );
  if (size > budget) {
    throw new Error(
      `${file} exceeds size budget: ${size} bytes > ${budget} bytes`,
    );
  }
  return size;
}

function buildCounties() {
  runMapshaper(
    [
      "-i",
      COUNTY_SHP,
      "encoding=utf8",
      "-filter-fields",
      "fields=GEOID,NAME,STATEFP",
      "-clean",
      "-simplify",
      "weighted",
      "keep-shapes",
      SIMPLIFY_PCT.counties,
      "-clean",
      "-rename-layers",
      "counties",
      "-o",
      path.join(OUT_DIR, "counties.topojson"),
      "format=topojson",
      "quantization=1e5",
      "id-field=GEOID",
      "force",
    ],
    "counties.topojson — de jure county mesh (all 3,235 records)",
  );
}

function buildStates() {
  runMapshaper(
    [
      "-i",
      COUNTY_SHP,
      "encoding=utf8",
      "-dissolve",
      "STATEFP",
      "copy-fields=STATEFP",
      "-clean",
      "-simplify",
      "weighted",
      "keep-shapes",
      SIMPLIFY_PCT.states,
      "-clean",
      "-rename-layers",
      "states",
      "-o",
      path.join(OUT_DIR, "states.topojson"),
      "format=topojson",
      "quantization=1e5",
      "id-field=STATEFP",
      "force",
    ],
    "states.topojson — state dissolve of the county mesh",
  );
}

function buildNation() {
  runMapshaper(
    [
      "-i",
      COUNTY_SHP,
      "encoding=utf8",
      "-dissolve",
      "-clean",
      "-simplify",
      "weighted",
      "keep-shapes",
      SIMPLIFY_PCT.nation,
      "-clean",
      "-rename-layers",
      "nation",
      "-o",
      path.join(OUT_DIR, "nation.topojson"),
      "format=topojson",
      "quantization=1e5",
      "force",
    ],
    "nation.topojson — single dissolved outline (backdrop glow)",
  );
}

function buildAiannh() {
  if (!existsSync(AIANNH_SHP)) {
    console.warn(
      `\n[build_geo_assets] AIANNH shapefile not found at ${AIANNH_SHP} — skipping aiannh.topojson.`,
    );
    return null;
  }
  try {
    runMapshaper(
      [
        "-i",
        AIANNH_SHP,
        "encoding=utf8",
        "-filter-fields",
        "fields=GEOID,NAME",
        "-clean",
        "-simplify",
        "weighted",
        "keep-shapes",
        SIMPLIFY_PCT.aiannh,
        "-clean",
        "-rename-layers",
        "aiannh",
        "-o",
        path.join(OUT_DIR, "aiannh.topojson"),
        "format=topojson",
        "quantization=1e5",
        "id-field=GEOID",
        "force",
      ],
      "aiannh.topojson — AIANNH tribal statistical areas (future sovereignty overlay)",
    );
    return checkBudget("aiannh.topojson");
  } catch (err) {
    console.warn(
      `\n[build_geo_assets] aiannh.topojson generation failed, skipping (bible §9.4 escape hatch): ${err.message}`,
    );
    return null;
  }
}

function writeReadme(sizes, aiannhSize) {
  const fmtKiB = (n) => `${(n / 1024).toFixed(1)} KiB`;
  const lines = [
    "# public/geo — cartographic substrate provenance",
    "",
    "Generated by `tools/build_geo_assets.mjs` (Lane Carto, spec-113 §7). Do not hand-edit",
    "these files — regenerate from source with:",
    "",
    "```",
    "node tools/build_geo_assets.mjs",
    "```",
    "",
    "## Sources (read-only)",
    "",
    `- Counties/states/nation: **${COUNTY_VINTAGE}**, \`/media/user/data/babylon-data/tiger/county/tl_2024_us_county.shp\`.`,
    "  3,235 county-equivalent records, NAD83 lon/lat (unprojected), `GEOID` = 5-digit FIPS.",
    `- AIANNH: **${AIANNH_VINTAGE}**, \`/media/user/data/babylon-data/tiger/aiannh/tl_2025_us_aiannh.shp\`.`,
    "  867 American Indian/Alaska Native/Native Hawaiian area records, NAD83 lon/lat.",
    "",
    "## Decision: natural geography, no AK/HI/PR insets",
    "",
    "deck.gl overlays (H3 hexes, flow arcs, org/event pins) use real lon/lat coordinates.",
    "Repositioning Alaska or Hawaii into a cartographic inset box would desynchronize every",
    "overlay layer from the basemap beneath it. Default camera framing handles CONUS at",
    "scenario start; Alaska/Hawaii/Puerto Rico/territories are reachable by pan/zoom like any",
    "other territory. This supersedes DESIGN_BIBLE.md §2.2's inset note for this program.",
    "",
    "## Pipeline",
    "",
    "`npx --yes mapshaper` (v0.7.44 at time of generation), per output:",
    "",
    "1. `-filter-fields` / `-dissolve` to the minimal property set (GEOID/NAME/STATEFP only —",
    "   no attribute bloat carried into the client bundle).",
    "2. `-clean` (repairs input topology) → `-simplify weighted keep-shapes <pct>` → `-clean`",
    "   again (repairs any self-intersections/slivers the simplification pass introduced).",
    "   `keep-shapes` guarantees no county/state disappears entirely at the simplification",
    "   budget used here.",
    "3. `-o format=topojson quantization=1e5` — shared-arc TopoJSON, so county and state",
    "   borders that coincide share one arc (this is what `topojson-client`'s `merge`/`mesh`",
    "   rely on for clean polity dissolves with no seams).",
    "",
    "## Outputs",
    "",
    "| File | Properties | Records | Simplify | Size | Budget |",
    "|---|---|---|---|---|---|",
    `| \`counties.topojson\` | GEOID, NAME, STATEFP | 3,235 | ${SIMPLIFY_PCT.counties} | ${fmtKiB(sizes["counties.topojson"])} | ≤ 2.5 MiB |`,
    `| \`states.topojson\` | STATEFP | 56 | ${SIMPLIFY_PCT.states} | ${fmtKiB(sizes["states.topojson"])} | ≤ 400 KiB |`,
    `| \`nation.topojson\` | (none) | 1 | ${SIMPLIFY_PCT.nation} | ${fmtKiB(sizes["nation.topojson"])} | ≤ 200 KiB |`,
    aiannhSize != null
      ? `| \`aiannh.topojson\` | GEOID, NAME | 867 | ${SIMPLIFY_PCT.aiannh} | ${fmtKiB(aiannhSize)} | ≤ 600 KiB |`
      : "| `aiannh.topojson` | — | — | — | **not generated** (see warning in build log) | ≤ 600 KiB |",
    "",
    "`states.topojson` carries **56** STATEFP values: the 50 states, DC, and the inhabited",
    "territories present in TIGER (PR, VI, GU, AS, MP).",
    "",
    "## Basemap",
    "",
    "`basemap-style.json` in this directory is a minimal self-contained MapLibre style (no",
    "external tile/glyph/sprite URLs) — it replaces the Carto Dark Matter dependency. The",
    "political layer (this data) IS the map; the basemap is only a background color pulled",
    "from the app's `--babylon-void` token.",
    "",
  ];
  writeFileSync(path.join(OUT_DIR, "README.md"), lines.join("\n"));
  console.log(`\n[build_geo_assets] wrote ${path.join(OUT_DIR, "README.md")}`);
}

function main() {
  if (!existsSync(COUNTY_SHP)) {
    throw new Error(`County shapefile not found at ${COUNTY_SHP}`);
  }
  mkdirSync(OUT_DIR, { recursive: true });

  buildCounties();
  buildStates();
  buildNation();

  const sizes = {};
  for (const file of [
    "counties.topojson",
    "states.topojson",
    "nation.topojson",
  ]) {
    sizes[file] = checkBudget(file);
  }

  const aiannhSize = buildAiannh();

  writeReadme(sizes, aiannhSize);
  console.log("\n[build_geo_assets] done.");
}

main();
