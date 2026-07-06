# Tasks: Frontend Consolidation + Django Debt

**Input**: `specs/091-frontend-consolidation/{spec,plan}.md`
**Prerequisites**: stacks on `090-cold-collapse` (`42232a15`).
**Tests**: TDD red-first per unit. Vitest ≥357 green; Playwright green; `tests/unit/web/` green.

## Format: `[ID] [Story] Description`

## Phase 1 — 042 audit + course-correction verification (US4, docs)

- [ ] T001 [US4] Write the 042 evidence audit (T001–T049 classified done-with-evidence /
  superseded / residual→092/093/095) to `specs/042-game-ui-overhaul/AUDIT-091.md`; mark
  `specs/042-game-ui-overhaul/spec.md` **superseded**. Commit.
- [ ] T002 Write `specs/091-frontend-consolidation/course-correction-verification.md`: phases
  1–7 assessed against live code with file citations; record the unrouted Phase-4/5 infra
  divergence. Commit.

## Phase 2 — Consolidation (US1, red-first)

- [ ] T003 [US1] RED: add `web/frontend/src/__tests__/integration/consolidation.test.ts` — asserts
  no `leaflet` import anywhere under `src/`, each of the 7 legacy files absent, `Inspector.tsx`
  absent, `DevHarness` free of leaflet. (Fails at HEAD.)
- [ ] T004 [US1] Delete the 7 siblings (`ActionPage`, `GameView`, `HexMap`, `IntelPage`,
  `OrganizationsPage`, `OrgDashboard`, `TimeSeriesPanel`) + the legacy `Inspector` cluster
  (`Inspector.tsx`, `Breadcrumbs.tsx`) + their dead tests (`ActionPage.contract`,
  `OrganizationsPage.contract`, `store-sync`, `inspector-selection`, `Inspector.test`). Repoint
  `DevHarness` off leaflet. Remove `react-leaflet`/`leaflet`/`@types/leaflet` from `package.json`;
  `npm install --package-lock-only`.
- [ ] T005 [US1] GREEN: consolidation test + full Vitest green; `rg leaflet web/frontend/src`
  empty. Commit.

## Phase 3 — Map promotion (US2, red-first)

- [ ] T006 [US2] RED: `web/frontend/src/components/pages/__tests__/briefing-map.test.tsx` — asserts
  `BriefingPage` mounts the map (DeckGL container) and not `HexMapPlaceholder`.
- [ ] T007 [US2] Wire `DeckGLMap` into `BriefingPage`'s Situation-Map panel (snapshot-fed);
  guard WebGL for jsdom. GREEN. Commit.

## Phase 4 — Django debt (US3, red-first)

- [ ] T008 [US3] RED: `tests/unit/web/test_migration_graph.py` — asserts `accounts` has migrations
  and `makemigrations --check --dry-run` is clean.
- [ ] T009 [US3] Add `django.contrib.gis` to `INSTALLED_APPS`; `makemigrations accounts game`;
  GREEN; `poetry run pytest tests/unit/web/` green. Commit.

## Phase 5 — 090 residuals (US5)

- [ ] T010 [US5-a] Bump the pre-commit prettier hook to match the gate's prettier 3.x. Commit.
- [ ] T011 [US5-b] NEW Playwright visual-baseline suite pinning the Cold Collapse canon
  (fixed viewport, animations off; token sheet + representative chrome; R-CRT line). Commit.
- [ ] T012 [US5-c] Resolve Space Grotesk italic: remove faux-italic usage (BreakdownTooltip) or
  self-host the italic face. Commit.
- [ ] T013 [US5-d] Port the 35 semantic type-role tokens or document deferral with rationale. Commit.
- [ ] T014 [US5-e] Tighten `tokens.contract.test.ts` C6: pin lens→layer against independent
  expectations. Commit.
- [ ] T015 [US5-f] Align `theme/colors.ts` docstrings to the amendment wording (monotonic EXCEPT
  named alarm terminals/diverging). Commit.

## Phase 6 — Close-out

- [ ] T016 Update `project/01-state-of-the-world.md`, `project/09-program-full-game.md` §2 spec-091
  status, `ai-docs/state.yaml`. Commit.

## Notes

- Commit after each unit via `mise run commit -- "type(scope): msg"`; verify HEAD moved.
- Preserve `lib/selectors`, `lib/verbs`, `VerbShell`, `HexInspector`, `NodeInspector`,
  `BreakdownTooltip` (tested infra; provenance wiring is spec-093).
