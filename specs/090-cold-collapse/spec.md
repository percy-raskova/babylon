# Feature Specification: Cold Collapse Design-System Migration

**Feature Branch**: `090-cold-collapse`
**Created**: 2026-07-03
**Status**: Draft
**Program**: 09 Full-Game Build — Lane W (web product). Advisory audit number: n/a (first-come 090).
**Input**: Port the ratified "Constitution VIII — Cold Collapse" design canon into the React frontend, replacing the pre-ratification gold/Inter token set.

## Overview

The shipped frontend still carries the pre-ratification visual identity: a gold-and-crimson
palette on Inter + Roboto Mono, wired through `web/frontend/src/index.css`. In May 2026 Percy
ratified a new canon — **Cold Collapse** ("official babylon canon", `design/mockups/colors_and_type.css`):
a cold-cyan/concrete/laser-red identity where each accent encodes a *verb, not a vibe*, on a
four-family self-hosted type stack, with luminance-monotonic cartographic ramps that retire the
old rainbow scales.

This feature migrates the frontend to that canon. It is the **foundation spec of Lane W** — every
subsequent UI spec (091–095, 103) consumes these tokens, so the migration must land first and
completely. Because the canon conflicts with the letter of Constitution Article VII
("GOLD (action/solidarity)", "Max two typeface families", "No decorative glow"), this feature also
**drafts** the Article VII amendment that reconciles them; ratification is the BD's, queued at PR
review. The token binaries land on this branch; the constitution file is not touched.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player sees the Cold Collapse identity (Priority: P1)

A player opens the web app. Instead of the gold-on-Inter chrome, they see the cold-bunker
identity: void-black surfaces, cyan "spire" as the primary/agency accent, laser-red reserved for
threat, bronze-gold ("rupture") reserved for the scarce revolutionary breakthrough. Text renders in
the self-hosted type stack (Space Grotesk chrome, JetBrains Mono data) with no network font
requests. Nothing on screen still reads Inter or Roboto Mono.

**Why this priority**: This is the whole point of the feature and the gate for all downstream UI
work. Without the token layer migrated, every later screen would be built on the wrong identity and
would have to be reworked.

**Independent Test**: Load the app (or any component) and confirm the computed CSS custom
properties resolve to the canon values (e.g. the primary accent is `#4dd9e6`, not `#c8a860`) and
the document requests only self-hosted fonts. A token-contract test asserts each token equals its
canon value and that the banned font families are absent from the stylesheet.

**Acceptance Scenarios**:

1. **Given** the migrated stylesheet, **When** a test reads the resolved `@theme`/`:root` token
   values, **Then** every Cold Collapse token (substrate, emissions, semantic accents, type stack)
   matches `design/mockups/colors_and_type.css` exactly.
2. **Given** the migrated stylesheet, **When** searched for the strings "Inter" or "Roboto Mono",
   **Then** neither appears.
3. **Given** the running dev server, **When** the page loads, **Then** all font faces resolve from
   local `.woff2` assets and no request is made to `fonts.googleapis.com` or `fonts.gstatic.com`.

---

### User Story 2 - Map & charts read magnitude by lightness (Priority: P1)

An analyst switches map lenses (economic/political/social/strategic). Each lens colours hexes with a
single-hue-family ramp whose lightness encodes magnitude — heat runs dark→ember→laser, consciousness
dark→cyan-glow, wealth dark→scarcity-gold, population a single violet lightness ramp, biocapacity a
diverging depleted↔healthy ramp. No ramp is a `dark-purple → crimson → gold` rainbow.

**Why this priority**: Article VII ("Luminosity = magnitude") and the R-CRT ruling bind data-encoding
surfaces absolutely. Getting the ramps right is a correctness requirement, not a cosmetic one, and
the lens legend and deck.gl fills both consume them.

**Independent Test**: For each of the six data layers, the ramp's stop list equals the canon ramp
from `design/mockups/preview/colors-data.html`; each lens resolves to its layer's canon ramp; the
sequential ramps trend brighter through their body.

**Acceptance Scenarios**:

1. **Given** the six map layers, **When** the colour scale for each is sampled, **Then** the stops
   match the canon luminance-monotonic ramps.
2. **Given** a lens, **When** the legend renders, **Then** it shows the canon ramp for that lens's
   primary layer.
3. **Given** the biocapacity layer, **When** sampled at 0.0 / 0.5 / 1.0, **Then** it reads
   collapse-red → neutral-grey → regenerate-green (a diverging ramp), not a monotone gradient.

---

### User Story 3 - The token swap is constitutionally reconciled (Priority: P2)

The BD reviews the migration. Alongside the code sits a drafted Article VII amendment that names the
exact conflicts (palette remap, four-family typography, CRT/glow prohibition vs. the ratified diegetic
texture) and proposes reconciling clause text, so ratification is a yes/no decision rather than a
research task.

**Why this priority**: R-VII requires the amendment to be drafted *with* the spec and ratified before
the tokens merge. The draft is a hard deliverable; the ratification is Percy's and out of this
feature's control, so it is P2 (blocks merge, not implementation).

**Independent Test**: `specs/090-cold-collapse/article-vii-amendment.md` exists, cites the three
conflicts against the current constitution text, and proposes clause-level replacements; `plan.md`
references it. `.specify/memory/constitution.md` is unchanged.

**Acceptance Scenarios**:

1. **Given** the amendment draft, **When** read, **Then** it quotes the current VII.2 / VII.9 / VII.10
   text and gives replacement clauses for the Cold Collapse token set, the four-family stack, and the
   R-CRT texture carve-out.
2. **Given** the branch diff, **When** inspected, **Then** `constitution.md` shows no changes.

### Edge Cases

- **Legacy siblings still import old token names.** Components slated for deletion in spec-091
  (`HexMap.tsx`, `GameView.tsx`, `utils/colorScale.ts`, etc.) may reference removed Tailwind utility
  classes. The migration MUST keep the frontend building and the test suite green; where a still-routed
  component depends on a renamed token, provide a backward-compatible alias rather than breaking it.
  Un-routed legacy files that spec-091 deletes are not rehabilitated here.
- **CRT texture bleeding into data.** Scanlines/vignette/grain/bloom are chrome-only. If any texture
  utility is applied to a chart plot area, map fill, ramp, or sparkline, that is an R-CRT violation.
- **Missing font weight.** If a self-hosted weight is unavailable, the `@font-face` stack falls back to
  the next family in the canon stack (never to Inter/Roboto Mono, which are removed).
- **Offline / air-gapped load.** With no network, all fonts must still render (self-hosted requirement).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The frontend token layer (`web/frontend/src/index.css`) MUST define the full Cold Collapse
  token set — substrate (void…rust), emissions (bone…shroud), semantic accents (spire, spire-dim, laser,
  thermal, rupture, cadre, solidarity, rent, heat, population), semantic aliases (bg/border/text/interactive),
  urgency tints, CRT constants, and the type/spacing/radius/elevation scales — with values byte-identical to
  `design/mockups/colors_and_type.css`.
- **FR-002**: The Tailwind v4 `@theme` block MUST expose the canon colours and font stacks as Tailwind
  utilities so components can use `bg-*`, `text-*`, `border-*`, `font-*` classes bound to the canon.
- **FR-003**: The primary accent (agency/"infrastructure online") MUST be spire cyan `#4dd9e6`; gold
  (`#d4a02c`) MUST appear only as the scarce `rupture` accent; laser `#ff3344` MUST be reserved for threat.
- **FR-004**: The type stack MUST be self-hosted JetBrains Mono (data/mono), Space Grotesk (chrome/sans),
  Redaction 35 (display), Departure Mono (pixel). `@font-face` rules MUST reference only local `.woff2`
  assets committed in-repo. No runtime request to any Google Fonts host.
- **FR-005**: The strings "Inter" and "Roboto Mono" MUST NOT appear in `web/frontend/src/index.css`.
  `web/frontend/index.html` MUST NOT reference Inter (or any removed font) or a Google Fonts link.
- **FR-006**: Each self-hosted font family MUST ship its license file (OFL, plus LGPL for Redaction)
  alongside the binaries.
- **FR-007**: `web/frontend/src/theme/colors.ts` MUST define the six data-layer colour scales (heat,
  consciousness, wealth, rent, biocapacity, population) as the canon luminance-monotonic ramps from
  `design/mockups/preview/colors-data.html`, replacing the old rainbow interpolations, while preserving the
  existing public API (`getColorScale`, `rgbaToCss`, `RGBAColor`).
- **FR-008**: `web/frontend/src/lib/lensDefinitions.ts` MUST expose each lens's canon data ramp (via its
  `primaryLayer`) so the lens legend renders the same canon ramp used by the map fill — a single source of
  truth shared with `theme/colors.ts`.
- **FR-009**: A token-contract test MUST assert (a) the resolved custom properties match the canon values and
  (b) the banned font families are absent. It MUST be written and observed failing (RED) before the migration
  lands (TDD).
- **FR-010**: The migration MUST keep `mise run web:check` green — TypeScript, ESLint, Prettier, and the full
  Vitest suite (≥310 cases) all pass.
- **FR-011**: The Article VII amendment MUST be drafted at `specs/090-cold-collapse/article-vii-amendment.md`
  reconciling the palette remap, the four-family typography, and the R-CRT texture carve-out; it MUST be
  referenced from `plan.md`. `.specify/memory/constitution.md` MUST NOT be edited (ratification is the BD's).
- **FR-012**: CRT/glow texture (scanlines, vignette, grain, phosphor bloom, flicker) MUST be available as
  chrome-only utility classes and MUST NOT be applied inside any data-encoding surface (chart plot area, map
  fill, ramp, sparkline). [R-CRT]
- **FR-013**: The migration MUST NOT change simulation behaviour, backend endpoints, or persistence — it is a
  presentation-layer change confined to Lane W's owned files plus static font assets.

### Key Entities

- **Design Token**: A named CSS custom property (colour, font stack, spacing, radius, elevation, CRT constant)
  with a canon-defined value. Source of truth: `design/mockups/colors_and_type.css`.
- **Data Ramp**: An ordered list of hex stops for a map layer; lightness encodes magnitude, hue carries
  semantic flavour. Six ramps (heat, consciousness, rent, biocapacity, wealth, population). Source of truth:
  `design/mockups/preview/colors-data.html`.
- **Font Asset**: A self-hosted `.woff2` binary + its license, referenced by an `@font-face` rule.
- **Article VII Amendment (draft)**: The proposed constitutional clause changes reconciling the canon with
  the current Article VII; a review artifact, not executable code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Cold Collapse tokens in `index.css` match the canon values (verified by the token-contract
  test).
- **SC-002**: `rg -i 'roboto mono|inter' web/frontend/src/index.css` returns zero matches.
- **SC-003**: Zero runtime font requests leave the machine — all four families render offline from local assets.
- **SC-004**: All six data-layer ramps equal their canon stop lists; every lens resolves to its canon ramp.
- **SC-005**: `mise run web:check` passes with the Vitest count at or above the pre-migration 310.
- **SC-006**: The Article VII amendment draft exists and is referenced by `plan.md`; the constitution file is
  unchanged on the branch.
- **SC-007**: A reviewer comparing the running UI (or the token/type/ramp/CRT surfaces) against
  `design/mockups/preview/*.html` finds the chrome faithful to canon and no CRT texture inside any
  data-encoding surface.

## Assumptions

- The ratified canon files under `design/mockups/` are authoritative and byte-stable (committed `--no-verify`
  as verbatim artifacts); they are read-only inputs to this feature.
- Font binaries are fetched from official OFL sources (JetBrains Mono repo; fontsource CDN for Space Grotesk,
  Redaction 35; the Departure Mono repo) and committed as static assets. This is not an npm dependency change —
  no `npm install` is run; `node_modules` is a shared symlink and must not be mutated.
- The four self-hosted weights for the two workhorse families are 400/500/600/700; display and pixel families
  ship their single regular weight. The canon fallback fonts (IBM Plex Mono, system-ui, Major Mono Display,
  VT323) remain in the stacks as graceful degradation but are never fetched.
- Weights beyond 400/500/600/700 are out of scope; italic faces are out of scope (the canon specimens use
  upright only).
- Playwright's existing behavioural suites do not assert on specific colours/fonts, so the token swap should not
  regress them; a visual-baseline pass against the canon previews is a review aid, not a blocking gate. The
  blocking gate is `mise run web:check`.
- Ratification of the Article VII amendment is Percy's and happens at PR review; this feature delivers the draft
  and the full token swap on the branch but does not merge.
- Legacy sibling components and `utils/colorScale.ts` are spec-091's deletion territory; this feature only keeps
  the build green (aliases where a routed component needs a renamed token), it does not migrate or delete them.
