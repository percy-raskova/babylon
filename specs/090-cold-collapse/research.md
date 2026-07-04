# Phase 0 Research: Cold Collapse Design-System Migration

All decisions below resolve the NEEDS-CLARIFICATION space from Technical Context. Verified in-repo /
against live font sources 2026-07-03.

## R1 — Font sourcing & licensing (self-hosted, no Google Fonts)

**Decision**: Ship subset `.woff2` for four families under `web/frontend/public/fonts/<family>/`, each
with its license file. Weights: 400/500/600/700 for the two workhorses; 400 only for display/pixel.

| Family | Role | Weights | Source (verified 200 OK) | License |
|--------|------|---------|--------------------------|---------|
| JetBrains Mono | mono / data | 400,500,600,700 | `github.com/JetBrains/JetBrainsMono` webfonts + fontsource `jetbrains-mono` latin subset | OFL 1.1 |
| Space Grotesk | sans / chrome | 400,500,600,700 | fontsource `space-grotesk` latin subset (`cdn.jsdelivr.net/fontsource/...`) | OFL 1.1 |
| Redaction 35 | display / epigraph | 400 | fontsource `redaction-35` latin subset | OFL 1.1 + LGPL 2.1 (MCKL Inc.) |
| Departure Mono | pixel / readout | 400 | `github.com/rektdeckard/departure-mono` `public/assets/` | OFL 1.1 (Helena Zhang) |

**Rationale**: fontsource provides clean per-weight latin `.woff2` subsets (13–39 KiB/face) with
LICENSE files; all four are OFL (Redaction dual OFL/LGPL) → free to embed and redistribute with the
app. Self-hosting satisfies the "no Google Fonts at runtime" requirement and the strict-CSP-friendly,
offline-capable constraint.

**Alternatives considered**: (a) Google Fonts `<link>` — rejected (runtime network dependency, the
exact thing the canon forbids). (b) Variable fonts — rejected for now (per-weight static keeps
`@font-face` explicit and the bundle predictable; the canon uses discrete 400/500/600/700). (c) npm
`@fontsource/*` packages — rejected: `node_modules` is a shared symlink and `npm install` is banned;
committed static assets are the correct path (fonts are files, not deps).

**Note**: The canon `_tokens.css` preview uses Google-hosted *substitutes* (Major Mono Display, VT323)
for display/pixel; the canon `colors_and_type.css` names **Redaction 35** and **Departure Mono** as the
primaries, with those substitutes as *fallbacks* in the stack. We self-host the primaries and keep the
substitutes as unfetched fallbacks.

## R2 — Tailwind v4 `@theme` conventions

**Decision**: Put the palette + font stacks in `@theme { --color-*: …; --font-*: … }` so Tailwind
generates `bg-*`/`text-*`/`border-*`/`font-*` utilities; put semantic aliases, urgency tints, CRT
constants, spacing/radius/elevation, and `@font-face` in a plain `:root` / top-level block. Keep a set
of **backward-compatible `--color-*` aliases** (old names → new canon values) so still-routed
components that reference old Tailwind classes keep building until spec-091 deletes them.

**Rationale**: `@theme` is Tailwind v4's token entry point (already used by the current `index.css` via
`@import "tailwindcss"`). Custom properties not needed as utilities live in `:root`, matching the
canon file's structure. `@font-face` must be top-level CSS (not inside `@theme`).

**Alternatives considered**: A separate `theme.css` imported by `index.css` — rejected as unnecessary
indirection for one file; the spec names `index.css` as the single token surface.

## R3 — The six luminance-monotonic data ramps

**Decision**: Encode the six canon ramps from `design/mockups/preview/colors-data.html` as an exported
`DATA_RAMPS` constant in `theme/colors.ts`; rebuild `getColorScale` to interpolate over them. Canon
stops:

- **heat**: `#0d1016 #3a3530 #7a4720 #b8581f #d97a2c #ff3344` (ember → laser terminal alarm)
- **consciousness**: `#0d1016 #1f2c3d #345670 #4a86a0 #6bbcc8 #4dd9e6` (dark → spire glow)
- **rent**: `#0d1016 #2e2236 #56356b #8b4d9e #a83a78 #b8321f` (extraction → violence)
- **biocapacity**: `#b8321f #7a3525 #3d4250 #3a6b48 #5fbf7a` (**diverging**: collapse ↔ regenerate)
- **wealth**: `#0d1016 #2a251f #4d3f28 #8a6a2a #d4a02c` (destitute → scarcity-gold)
- **population**: `#0d1016 #23223a #3d3868 #5a4f95 #7a6db8 #a89dd0` (single hue, lightness only)

**Key finding — "luminance-monotonic" is a design principle, not a strict per-stop invariant.** Two
deliberate exceptions the test MUST respect:
1. **Alarm terminals** — heat ends in laser `#ff3344` and rent ends in thermal `#b8321f`, whose
   relative luminance is *below* the preceding stop. This is intentional (threat = semantic alarm,
   Article VII "smallest effective difference" traded for danger signalling). So a naive "strictly
   increasing luminance across all stops" assertion is WRONG and would fight the canon.
2. **Biocapacity is diverging** — darkest at the neutral centre (`#3d4250`), brightening toward both
   collapse-red and regenerate-green ends. Two monotonic arms, not one ramp.

**Test consequence**: assert exact stop equality against canon + single-hue-family discipline (no old
`crimson→gold` rainbow signature) + body-brightening for the sequential ramps' non-alarm span. Do NOT
assert global strict monotonicity.

**Alternatives considered**: Deriving ramps programmatically (HSL lightness sweep) — rejected: the
canon hand-tuned the stops; byte-fidelity to canon (III.1 grounding) beats a re-derivation that would
drift from the ratified swatches.

## R4 — Wiring ramps through `lensDefinitions.ts`

**Decision**: Add an additive `LENS_RAMP_STOPS: Record<LensId, string[]>` (+ `getLensRampStops(id)`)
that maps each lens to `DATA_RAMPS[lens.primaryLayer]` imported from `theme/colors.ts`. No change to
the `LensDefinition` interface (avoids churn to its consumers/tests). This gives the LensBar/MapLegend
a direct canon-ramp handle sharing one source of truth with the map fill.

**Rationale**: Single source of truth (`DATA_RAMPS`), minimal surface, no interface break, satisfies
"wire the ramps into lensDefinitions.ts + theme/colors.ts" literally.

**Alternatives considered**: Adding a `ramp` field to `LensDefinition` — rejected (interface churn;
the existing `primaryLayer` already keys the ramp).

## R5 — Token-contract test strategy (TDD, red-first)

**Decision**: `src/theme/tokens.contract.test.ts` reads `web/frontend/src/index.css` **as text**
(Node `fs`) and asserts each canon token value is present (e.g. `--babylon-spire: #4dd9e6`), the font
stacks name the canon families, and the banned strings `Inter` / `Roboto Mono` are absent. Ramp
assertions import `DATA_RAMPS` from `theme/colors.ts`. The test is committed and observed **RED**
(current `index.css` still has gold/Inter) before the migration.

**Rationale**: jsdom does not reliably resolve cascaded CSS custom properties from an imported
stylesheet (`getComputedStyle` returns empty for `var()`-defined tokens under `css:false` in
`vitest.config.ts`). Parsing the authored CSS text is deterministic, fast, and is the truest
"token contract" — it pins the source of truth the browser then consumes. This matches the spec's
"computed custom properties match canon values; banned fonts absent" intent at the layer we can
assert deterministically.

**Alternatives considered**: (a) Render a component in jsdom and read `getComputedStyle` — rejected
(unreliable var resolution, `css:false`). (b) Playwright computed-style probe — kept as an optional
review aid, not the unit gate (needs the live server; heavier; the text contract is sufficient and CI-safe).

## R6 — R-CRT chrome-vs-data discipline

**Decision**: CRT utilities (`.crt-scanlines`, `.crt-vignette`, `.bbl-flicker`, `.bloom-*`, grain) are
authored as **chrome-only** classes and documented as forbidden inside data-encoding surfaces (chart
plot areas, map fills, ramps, sparklines). The migration does not apply them to any data surface; the
amendment codifies the rule. No component wiring of CRT to data is introduced.

**Rationale**: R-CRT (program §1) + Article VII.10/VIII.8. Keeping texture off data surfaces preserves
"color = meaning / luminosity = magnitude" on the ramps absolutely.

## R7 — Backward-compatibility for legacy token names

**Decision**: Provide `@theme` aliases mapping the old canon names still referenced by *routed*
components (`void`, `bone`, `wet-concrete`, `gold`, `crimson`, `data-green`, etc.) to Cold Collapse
values, so `mise run web:check` stays green without touching spec-091's deletion set. Old `--font-*`
names (`Inter`, `Roboto Mono`) are NOT aliased — they are removed outright (that is the point).

**Rationale**: The migration must keep 310 Vitest + tsc/eslint/prettier green while replacing the
palette. Un-routed legacy siblings (`HexMap`, `GameView`, `utils/colorScale.ts`) are spec-091's to
delete; aliasing bridges the gap without scope creep. Verified consumers of old classes: base layer
`@apply bg-void text-bone`, scrollbar `bg-wet-concrete`/`bg-gold` — all aliased to canon.
