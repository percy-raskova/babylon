---
description: "Task list for spec-090 Cold Collapse design-system migration"
---

# Tasks: Cold Collapse Design-System Migration

**Input**: Design documents from `specs/090-cold-collapse/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/token-contract.md
**Tests**: TDD is mandatory (Program 09 §4; project constitution). The red token-contract test is T004.

**Path base**: `web/frontend/` (Lane W owned). Never touch `src/babylon/**` or `web/observatory/**`.
Never run `npm install` / `poetry install` (shared symlinks).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete-task deps)
- **[Story]**: US1 (palette+fonts), US2 (ramps), US3 (amendment)

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create `web/frontend/public/fonts/` with a subdir per family (`jetbrains-mono/`, `space-grotesk/`, `redaction-35/`, `departure-mono/`).
- [ ] T002 Read the canon source of truth into working memory: `design/mockups/colors_and_type.css` (tokens) + `design/mockups/preview/colors-data.html` (six ramps). These are read-only inputs.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ The red test must exist and fail before any migration code lands.**

- [ ] T003 [P] Download + commit self-hosted fonts under `web/frontend/public/fonts/`: JetBrains Mono (400/500/600/700 + OFL), Space Grotesk (400/500/600/700 + OFL), Redaction 35 (400 + OFL/LGPL), Departure Mono (400 + OFL). Verify each `.woff2` is valid (`file` reports WOFF2). Commit `--no-verify` if formatter hooks choke on binaries.
- [ ] T004 [US1] Write the **red-first** token-contract test `web/frontend/src/theme/tokens.contract.test.ts` per `contracts/token-contract.md` (C1 palette tokens, C2 type stack, C3 banned fonts absent, C4 self-hosted `@font-face`, C5 `DATA_RAMPS` stops, C6 lens ramp wiring). Run it and **observe RED** (`npx vitest run src/theme/tokens.contract.test.ts`). Commit the failing test with `@pytest.mark.red_phase` equivalent note in the commit message.

---

## Phase 3: User Story 1 — Cold Collapse identity (Priority: P1) 🎯 MVP

**Goal**: The frontend renders the Cold Collapse palette + self-hosted type stack; no Inter/Roboto Mono.
**Independent test**: token-contract test C1–C4 GREEN; `rg -i 'roboto mono|inter' web/frontend/src/index.css` empty; fonts render offline.

- [ ] T005 [US1] Rewrite `web/frontend/src/index.css`: port the full Cold Collapse token set from `colors_and_type.css` into Tailwind v4 `@theme` (colors + font stacks) + `:root` (semantic aliases, urgency tints, CRT constants, spacing/radius/elevation/glows). Values byte-identical to canon.
- [ ] T006 [US1] Add `@font-face` rules in `index.css` for the four families referencing `/fonts/<family>/<file>.woff2` (local only). No `fonts.googleapis.com` / `fonts.gstatic.com`. Wire `--font-mono/sans/display/pixel` to the self-hosted primaries with canon fallbacks.
- [ ] T007 [US1] Add backward-compat `@theme` aliases (old canon names → Cold Collapse values) for token names still referenced by ROUTED components (`void`, `bone`, `wet-concrete`→wet-steel, `gold`→rupture, `crimson`→laser, `data-green`→solidarity, etc.) so the build stays green. Do NOT alias `Inter`/`Roboto Mono` (removed outright).
- [ ] T008 [US1] Author CRT/bloom utility classes as **chrome-only** (`.crt-scanlines`, `.crt-vignette`, `.bbl-flicker`, `.bloom-*`) per canon `colors_and_type.css`; document R-CRT (forbidden on data surfaces) in a comment. Apply to nothing here.
- [ ] T009 [US1] Clean `web/frontend/index.html`: remove the Inter `font-family` in the inline `<style>` and any Google-Fonts reference; use a neutral system fallback + the void background token value. No banned font names remain.

---

## Phase 4: User Story 2 — Luminance-monotonic data ramps (Priority: P1)

**Goal**: The six map layers use the canon ramps; lenses resolve to their canon ramp.
**Independent test**: token-contract test C5–C6 GREEN; `colors.test.ts` still green; ramps equal canon stops.

- [ ] T010 [US2] Rewrite `web/frontend/src/theme/colors.ts`: add exported `DATA_RAMPS` (six canon ramp stop-arrays from `colors-data.html`); rebuild the six scale functions to interpolate over them via the existing `lerp`/hex path; preserve the public API (`getColorScale` for all 11 `MapLayer`s, `rgbaToCss`, `RGBAColor`). Biocapacity stays diverging.
- [ ] T011 [US2] Extend `web/frontend/src/theme/colors.test.ts` with canon-anchored assertions: each ramp's stops equal canon; sequential ramps start at `#0d1016`; single-hue discipline (no old rainbow signature). Keep existing boundary/`rgbaToCss` tests passing.
- [ ] T012 [US2] Wire ramps into `web/frontend/src/lib/lensDefinitions.ts`: add additive `LENS_RAMP_STOPS: Record<LensId, string[]>` + `getLensRampStops(id)` mapping each lens to `DATA_RAMPS[lens.primaryLayer]` (imported from `theme/colors.ts`). No `LensDefinition` interface change.

---

## Phase 5: User Story 3 — Constitutional reconciliation (Priority: P2)

**Goal**: The Article VII amendment is drafted and referenced; constitution.md untouched.
**Independent test**: `article-vii-amendment.md` exists + referenced by `plan.md`; `git diff constitution.md` empty.

- [ ] T013 [P] [US3] (DONE in plan phase) Verify `specs/090-cold-collapse/article-vii-amendment.md` covers the three conflicts (VII.2 palette, VII.9 typography, VII.10/VIII.8 R-CRT) with current-text quotes + reconciling clauses; confirm `plan.md` references it and `.specify/memory/constitution.md` is unchanged on the branch.

---

## Phase 6: Polish & Gate Verification

- [ ] T014 Run the GREEN gate: `mise run web:check` (tsc + eslint + prettier + vitest ≥310) — all pass. Fix any lint/format fallout in the migrated files.
- [ ] T015 Run the CLI gates: `rg -i 'roboto mono|inter' web/frontend/src/index.css` (empty) + `rg -i 'googleapis|gstatic' web/frontend/src/index.css web/frontend/index.html` (empty).
- [ ] T016 Visual-baseline review: compare the token/ramp/type/CRT surfaces against `design/mockups/preview/{colors-cold-collapse,colors-data,type-specimens,effects-crt}.html`; record notes (chrome faithful; no CRT texture inside any data surface). Regenerate Playwright baselines if a visual-snapshot spec is added; otherwise confirm the 8 behavioural suites are unaffected by the token swap.
- [ ] T017 Close-out: update `project/01-state-of-the-world.md` (Web layer facts: index.css migrated), `project/09-program-full-game.md` §2 spec-090 status → DONE, and `ai-docs/state.yaml`.

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T004)**: T004 (red test) MUST fail before Phase 3.
- **US1 (T005–T009)** depends on T003 (fonts) + T004 (red test). MVP boundary is end of US1 + US2.
- **US2 (T010–T012)** depends on T004; independent of US1's CSS (different files) — T010/T011/T012 can run right after the red test, in parallel with US1 CSS work (T005 index.css vs T010 colors.ts vs T012 lensDefinitions.ts are different files → [P]-eligible), but both must be GREEN for the token-contract test to pass fully.
- **US3 (T013)** is independent (docs; already drafted) — [P] anytime.
- **Polish (T014–T017)** after US1 + US2 land.

## Parallel opportunities

- T003 (fonts) ∥ T004 (red test) — different surfaces.
- After T004: T005 (index.css) ∥ T010 (colors.ts) ∥ T012 (lensDefinitions.ts) ∥ T013 (amendment verify) — all different files.

## Implementation strategy

MVP = US1 + US2 (the token/font/ramp swap that gates every later Lane-W spec). US3 is a review
artifact (already drafted). Commit after each unit via `mise run commit`; fonts/binaries via
`--no-verify` per artifact precedent. Do NOT merge to `dev` (BD's call, gated on amendment ratification).
