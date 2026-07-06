# Implementation Plan: Cold Collapse Design-System Migration

**Branch**: `090-cold-collapse` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/090-cold-collapse/spec.md`
**Program**: 09 Full-Game Build — Lane W. Kit refs: `project/09-program-full-game.md` §1 (R-VII, R-CRT), §2 (spec-090), §5 (canon).

## Summary

Migrate the React frontend from the pre-ratification gold/Inter token set to the ratified
**Constitution VIII — Cold Collapse** canon. Three surfaces: (1) the CSS token layer + Tailwind v4
`@theme` (`index.css`), (2) self-hosted typography (four OFL/free families, Inter + Roboto Mono
removed), (3) the six luminance-monotonic data ramps in `theme/colors.ts` wired through
`lensDefinitions.ts`. Driven red-first by a Vitest token-contract test. Ships the **drafted** Article
VII amendment (R-VII) — reviewed/ratified by the BD before merge; the constitution file is not edited
here.

**Technical approach**: The canon files under `design/mockups/` are the byte-level source of truth.
`index.css` is rewritten to mirror `colors_and_type.css` under Tailwind v4's `@theme` + `:root`
conventions. Fonts are committed as `.woff2` + license files under `web/frontend/public/fonts/` and
declared via `@font-face` in `index.css` (Vite serves `public/` at web root; no bundler/npm change).
`theme/colors.ts` keeps its `getColorScale`/`rgbaToCss` public API but rebuilds the six scales as
multi-stop interpolations over the canon ramp arrays (a single exported `DATA_RAMPS` constant);
`lensDefinitions.ts` re-exports each lens's canon ramp via its `primaryLayer` so map fill and legend
share one source. TDD: `src/theme/tokens.contract.test.ts` asserts canon token values + banned-font
absence and is observed RED before the CSS lands.

## Technical Context

**Language/Version**: TypeScript 5.7, CSS (Tailwind v4 `@theme`)
**Primary Dependencies**: React 19, Vite 6, Tailwind CSS v4 (`@tailwindcss/vite`), Vitest 4, Playwright 1.58 — **all already installed** (`web/frontend/node_modules` is a shared symlink; no `npm install`)
**Storage**: N/A (presentation-layer only; no engine/DB/endpoint change)
**Testing**: Vitest (jsdom) for the token contract + ramp/lens units; existing 8 Playwright behavioural suites as regression; visual review against `design/mockups/preview/*.html`
**Target Platform**: Modern browsers (deck.gl 9 / MapLibre 5 client); offline font rendering required
**Project Type**: Web frontend (Lane W owns `web/**` product code; never touches `src/babylon/**` or `web/observatory/**`)
**Performance Goals**: Zero runtime font network requests; subset `.woff2` (~13–39 KiB/face) keeps first paint light
**Constraints**: Byte-fidelity to canon values; `mise run web:check` green with Vitest ≥310; `rg -i 'roboto mono|inter' web/frontend/src/index.css` empty; no mutation of shared `node_modules`/`.venv`
**Scale/Scope**: 4 product files + font assets + 1 new test + 1 amendment draft; the token foundation every later Lane-W spec (091–095, 103) consumes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitution v2.7.0
(Amendments K + L ratified). UI work is bound by Article VII and Anti-Pattern VIII.9.

| Gate | Requirement | This feature | Status |
|------|-------------|--------------|--------|
| **VII.2 Color as Data** | Palette encodes meaning; luminosity = magnitude; all via tokens | Cold Collapse token set; each accent = a verb; ramps luminance-monotonic. **Conflicts with the current VII.2 letter** ("GOLD (action/solidarity)") → reconciled by the drafted Article VII amendment (R-VII). | Amendment-gated |
| **VII.9 Typography** | "Monospace dominant. Max two typeface families." | Four functional families (mono=data dominant, sans=chrome, display, pixel). **Conflicts** → amendment revises the two-family cap to a functional-role stack. | Amendment-gated |
| **VII.10 Prohibitions / VIII.8** | No decorative glow, hardcoded colors, chartjunk | CRT/bloom texture is diegetic canon. **Conflicts** → amendment adds the R-CRT carve-out: texture on chrome only, forbidden in data-encoding surfaces. Colors are all tokens (no hardcoding in components). | Amendment-gated |
| **VII.3 Data-Ink / VII.7 Smallest Effective Difference** | Every pixel encodes data; single-hue ramps | Six luminance-monotonic ramps retire the rainbow scales. | advanced |
| **VIII.9 Community as Pairwise Edge** | Hyperedges never rendered pairwise / as spatial hulls | Out of scope for tokens; not regressed (no rendering changes). Binds 093, not 090. | N/A |
| **III.1 No Magic Numbers** | Constants trace to a grounded source | Every token/ramp value traces to `design/mockups/colors_and_type.css` + `colors-data.html` (the ratified canon). The token-contract test pins them. | grounded |
| **III.8 Data-Grounding** | Claims trace to data | Canon is the design "data"; provenance = `design/mockups/PROVENANCE.md`. | grounded |
| **AI Observes (III)** | AI never controls mechanics | No AI, no engine, no determinism surface touched. | N/A |

**Gate resolution**: The three amendment-gated conflicts are **expected and intended** — they are
exactly why R-VII requires an Article VII amendment. Per R-VII the amendment is **drafted with this
spec** ([article-vii-amendment.md](./article-vii-amendment.md)) and Percy ratifies it **before** the
token swap merges to `dev`. The branch carries the full swap (build it all — merging is the BD's
call); `.specify/memory/constitution.md` is **not** edited by this feature. No unjustified violation
remains: each conflict has a drafted reconciling clause. Complexity Tracking below records them.

## Project Structure

### Documentation (this feature)

```text
specs/090-cold-collapse/
├── spec.md                    # /speckit.specify output
├── plan.md                    # This file
├── research.md                # Phase 0: font sourcing, Tailwind v4 @theme, ramp derivation, test strategy
├── data-model.md              # Phase 1: token / ramp / font-asset schemas
├── quickstart.md              # Phase 1: how to verify the migration locally
├── article-vii-amendment.md   # R-VII design artifact (draft; ratified by BD at PR)
├── contracts/
│   └── token-contract.md      # The token-contract test contract (canon values + banned fonts)
├── checklists/
│   └── requirements.md        # /speckit.specify quality checklist
└── tasks.md                   # /speckit.tasks output (not created by /speckit.plan)
```

### Source Code (repository root) — Lane W owned surface only

```text
web/frontend/
├── index.html                       # remove Inter <style>/Google-Fonts; neutral system fallback
├── public/
│   └── fonts/                        # NEW — self-hosted woff2 + licenses
│       ├── jetbrains-mono/  (400/500/600/700 + OFL)
│       ├── space-grotesk/   (400/500/600/700 + OFL)
│       ├── redaction-35/    (400 + OFL/LGPL)
│       └── departure-mono/  (400 + OFL)
└── src/
    ├── index.css                    # REWRITE — Cold Collapse @theme + :root + @font-face + CRT utils
    ├── theme/
    │   ├── colors.ts                # REWRITE scales → canon DATA_RAMPS (public API preserved)
    │   ├── colors.test.ts           # extend: ramp-stop + canon assertions
    │   └── tokens.contract.test.ts  # NEW — red-first token-contract test
    └── lib/
        └── lensDefinitions.ts       # ADD lens→canon-ramp wiring (LENS_RAMP_STOPS / getLensRampStops)
```

**Structure Decision**: Web frontend. All writes land under `web/frontend/**` (Lane W's owned
surface). Fonts go in `public/fonts/` because Vite copies `public/` to the site root verbatim — the
simplest self-hosting path that also works in `vite build` / Django-served production and needs no
bundler config. `src/utils/colorScale.ts` and the legacy sibling components are **not** touched here
(spec-091 deletion territory); the migration only preserves build-green (token aliases if a *routed*
component needs a renamed token).

## Complexity Tracking

| Violation (vs. current constitution letter) | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| VII.2 palette remap (gold→scarce rupture; spire cyan primary; solidarity green) | Percy ratified Cold Collapse as "official babylon canon" (2026-05-17); the cover-art chromatics demand cold cyan agency + laser threat | Keeping gold-as-solidarity would contradict the ratified canon and every staged mockup; not a real option |
| VII.9 four typeface families | Each family does one job (mono=data, sans=chrome, display=epigraph, pixel=readout); the canon is explicit ("Three families. Each does one job." + system DIN for Synopticon) | Two families cannot carry the data/chrome/display/pixel distinction the canon encodes |
| VII.10/VIII.8 CRT + phosphor bloom | Diegetic "concrete bunker" texture is core to the ratified identity; R-CRT confines it to chrome | Banning all texture would strip the ratified aesthetic; R-CRT is the disciplined middle path (texture is not chartjunk when kept off data surfaces) |

All three are reconciled by [article-vii-amendment.md](./article-vii-amendment.md); none is an
unjustified breach — each is a canon-vs-current-letter delta that the amendment resolves before merge.

## Phase 0 — Research

See [research.md](./research.md). Resolves: font sourcing + licenses (all OFL, verified downloads),
Tailwind v4 `@theme` token conventions, the canonical ramp stop lists (from `colors-data.html`,
including the deliberate diverging biocapacity ramp and the semantic alarm terminals that are *not*
strictly luminance-monotonic), the token-contract test strategy (jsdom cannot resolve cascaded custom
properties reliably → parse `index.css` text + import the ramp module), and the R-CRT chrome/data line.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — token / ramp / font-asset schemas + validation rules.
- [contracts/token-contract.md](./contracts/token-contract.md) — the exact canon values the
  token-contract test pins, and the banned-font assertions.
- [quickstart.md](./quickstart.md) — local verification steps (`mise run web:check`, the `rg` gate,
  offline-font check, visual review against previews).
- Agent context: no new runtime tech introduced (all deps pre-installed); agent-file update is a no-op
  beyond noting the design-system migration.

## Phase 2 — Task planning (handed to /speckit.tasks)

Tasks are ordered TDD-first: write the red token-contract test → observe RED → add fonts →
rewrite `index.css` → rewrite `theme/colors.ts` ramps → wire `lensDefinitions.ts` → update
`index.html` → make GREEN (`web:check`) → draft amendment (parallel) → close-out docs. Commit after
each unit via `mise run commit`.
