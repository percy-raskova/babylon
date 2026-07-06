# Implementation Plan: Frontend Consolidation + Django Debt

**Branch**: `091-frontend-consolidation` (stacks on `090-cold-collapse`) | **Spec**: `specs/091-frontend-consolidation/spec.md`
**Program**: 09 Full-Game Build — Lane W. Kit refs: `project/09-program-full-game.md` §1 (R-042, R-CRT, R-CONS), §2 (spec-091), §3 (Lane W file ownership).

## Summary

Consolidate the frontend to one codebase and clear the Django migration debt. Five workstreams:
(1) audit + close spec-042 (R-042); (2) verify the course-correction phases 4/6/7 against live
code; (3) delete the god-page cluster + react-leaflet; (4) promote the deck.gl map to Briefing;
(5) clear Django debt (accounts migration, game makemigrations, `django.contrib.gis`). Plus the six
spec-090 residuals. TDD throughout: red guard/behaviour tests before each destructive or additive
change.

## Technical Context

**Language**: TypeScript 5.7 (frontend), Python 3.12 (Django backend).
**Stack**: React 19, Vite 6, Tailwind v4, Zustand 5, deck.gl 9 + MapLibre, Vitest 4,
Playwright 1.58; Django 5.x on PostGIS. All already installed — shared `node_modules`/`.venv`
symlinks; **no `npm install` / `poetry install`**. Dependency removal is lockfile-only
(`npm install --package-lock-only`).
**Constraints**: Vitest ≥357 green; all Playwright suites green; `rg leaflet web/frontend/src`
empty; `poetry run pytest tests/unit/web/` green; fresh-DB migration materializes `PlayerProfile`.
**Scope of ownership (Lane W)**: `web/**` (product) + `design/mockups` READ-ONLY. MUST NOT touch
`src/babylon/**` or `web/observatory/**`.

## Constitution Check

*GATE: Must pass before implementation. Constitution v2.7.0 (Amendments K + L ratified).* UI work
is bound by Article VII (+ the drafted Cold Collapse amendment shipping with 090) and Anti-Pattern
VIII.9.

| Gate | Requirement | This feature | Status |
|------|-------------|--------------|--------|
| **III.1 No Magic Numbers** | Constants trace to a grounded source | Consolidation/deletion adds no game constants; the map reuses `theme/colors.ts` ramps (grounded in the canon). No inline hex in touched components. | PASS |
| **III.7 Determinism / Frozen models** | No engine/state changes | Presentation + Django-migration only; zero engine dynamics, zero baseline churn. | PASS |
| **III.8 Data-Grounding** | Claims trace to data/code | The 042 audit cites files/commits per row; the course-correction verification cites live code. | PASS |
| **II.11 / II.12 authoring API** | Engine authoring untouched | No engine work. | N/A |
| **I.20 / IV** | Layering respected | React stays a presentation layer; no client-side simulation; migrations are Django-native. | PASS |
| **VII (Cold Collapse amendment)** | Color=meaning; tokens only; texture off data surfaces (R-CRT) | The promoted map uses the luminance-monotonic ramps from `theme/colors.ts`; the visual-baseline suite pins R-CRT (texture on chrome, none inside data-encoding surfaces). | PASS |
| **VII.9 Typography** | Functional type-role stack | 090 residual (d) ports the 35 semantic type-role tokens or documents deferral; residual (c) forbids faux-italic. | PASS |
| **VIII.9 Community as Pairwise Edge** | Hyperedges never pairwise / spatial hulls | No hyperedge rendering changes; binds 093, not 091. | N/A |
| **R-042** | 042 audited then closed superseded | US4: full T001–T049 audit table; 042 marked superseded. | PASS |
| **R-CONS** | Build endpoints WITH consumers | No new endpoints; the map consumes the existing snapshot contract. | PASS |

**Gate resolution**: No conflicts. This feature changes no dynamics and adds no constants; it
removes dead code, wires an existing map component to an existing snapshot, and materializes Django
schema that the models already declare. The provenance-tooltip re-wire that the course-correction
Phase 5 envisioned for the live screens is explicitly **deferred to spec-093** (program §2), so no
Article VII data-surface work is undertaken here beyond the map ramp reuse.

## Project Structure — Lane W owned surface only

```
web/frontend/src/
├── components/            # DELETE 7 siblings + legacy Inspector cluster; wire DeckGLMap into BriefingPage
├── DevHarness.tsx         # repoint off leaflet HexMap
├── __tests__/…            # delete dead-cluster tests; add consolidation + briefing-map tests
├── theme/colors.ts        # residual (f): amendment-aligned docstrings
├── index.css              # residual (d): semantic type-role tokens
└── e2e/visual.spec.ts     # residual (b): NEW Playwright visual-baseline suite
web/accounts/migrations/   # NEW initial migration (PlayerProfile)
web/game/migrations/       # makemigrations for pending model changes
web/babylon_web/settings/base.py  # add django.contrib.gis
.pre-commit-config.yaml    # residual (a): bump prettier hook
tests/unit/web/            # migration smoke test (red-first)
specs/042-game-ui-overhaul/AUDIT-091.md  # R-042 evidence audit
specs/091-frontend-consolidation/course-correction-verification.md
```

## Phased Approach (each phase = one commit, TDD red-first)

1. **042 evidence audit** → `specs/042-game-ui-overhaul/AUDIT-091.md`; mark 042 superseded.
2. **Course-correction verification** → `course-correction-verification.md` (phases 4/6/7 vs code).
3. **Consolidation** → red consolidation guard test; delete 7 siblings + legacy Inspector cluster
   + leaflet dep; repoint DevHarness; green.
4. **Map promotion** → red briefing-map test (Briefing renders DeckGLMap, not the placeholder);
   wire; green.
5. **Django debt** → red migration smoke test (`tests/unit/web/`); add `django.contrib.gis`,
   `accounts` initial migration, `game` makemigrations; green.
6. **090 residuals** (a–f) → prettier hook, visual suite, italic, type-role tokens, C6 test,
   ramp docstrings.
7. **Close-out** → update `project/01-state-of-the-world.md`, `09` §2 spec-091 status,
   `ai-docs/state.yaml`.

## Complexity Tracking

| Divergence from the course-correction letter | Why unavoidable | Resolution |
|---|---|---|
| Phase 4 registry (`lib/verbs`/`VerbShell`/`ActionPage`) is unrouted; the live `VerbPage` uses the spec-061 `verb-config.ts` | spec-061 rebuilt the verb surface as a 16-route page after the course-correction ActionPage was written | Delete the unrouted `ActionPage`; **preserve** the `lib/verbs`/`VerbShell`/selector infra (cited as "already exist"); document the unwired state; registry wiring is a later concern, provenance wiring is 093 |
| Phase 5 `BreakdownTooltip` lives in `HexInspector`, reachable only through the dead `IntelPage`/`Inspector` | IntelPageV2 (live) uses `bbl.Stat` panels without provenance | Preserve `HexInspector`/`NodeInspector`/`BreakdownTooltip`/`lib/selectors` as tested infra; **provenance-on-every-number is spec-093** (program §2) |
| Deleting `OrgDashboard` forces removing the entire legacy `Inspector` cluster (16 dead tests) | `OrgDashboard` is imported by the dead `Inspector`, itself exercised only by dead-cluster tests | Remove the cluster as a unit; add live-behaviour tests (map-on-briefing, consolidation guard) to hold Vitest ≥357 |
