# Feature Specification: Frontend Consolidation + Django Debt

**Feature Branch**: `091-frontend-consolidation`
**Created**: 2026-07-03
**Status**: Draft
**Program**: 09 Full-Game Build — Lane W (web product). Advisory audit number: n/a (first-come 091). Stacks on `090-cold-collapse`.
**Input**: One codebase, one data path, no legacy siblings. Audit spec-042, verify the frontend course-correction, delete the superseded god-page cluster, promote the map to a first-class in-game surface, and clear the Django migration debt.

## Overview

The frontend carries two generations of code side by side. The current, routed app is the
spec-061 **16-route architecture** (`web/frontend/src/components/pages/` on the `bbl` component
kit, wired to the live engine via `gameStore` + `useGameState`). Alongside it, the repository
still contains the **old god-page cluster** — `ActionPage`, `GameView`, `HexMap` (react-leaflet),
`IntelPage`, `OrganizationsPage`, `OrgDashboard`, `TimeSeriesPanel`, and the panel-based
`Inspector` — none of which the router mounts. This dead cluster confuses navigation, ships a
second map library (leaflet) the design canon rejects, and keeps two verb/inspector abstractions
alive.

This feature consolidates to one codebase. It (1) audits spec-042 (the Vic3 UI overhaul, formally
0/49) against shipped evidence and closes it as superseded per program ruling R-042; (2) verifies
the frontend course-correction (`docs/agents/babylon-frontend-paradox-course-correction.md`)
phases 4/6/7 against the live code and records the divergences; (3) deletes the god-page cluster
plus the react-leaflet dependency; (4) promotes the deck.gl map from the `/dev/hexmap` harness to
a persistent first-class presence on the Briefing route; and (5) clears the Django debt — the
`accounts` app has no migrations (its `PlayerProfile` table is never created), the `game` app has
pending model changes, and `django.contrib.gis` is absent from `INSTALLED_APPS` despite a PostGIS
engine.

It also lands the six spec-090 residuals assigned at review (prettier hook alignment, a Playwright
visual-baseline suite pinning the Cold Collapse canon, Space Grotesk italic resolution, the 35
semantic type-role tokens, a tightened lens→layer contract test, and amendment-aligned ramp
docstrings).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — One codebase, no legacy siblings (Priority: P1)

A developer opening `web/frontend/src/components/` finds exactly one implementation of each screen.
The god-page cluster is gone; `rg leaflet web/frontend/src` is empty; the router mounts only the
16-route `pages/` components.

**Independent Test**: `rg leaflet web/frontend/src` empty; none of the seven named legacy files
exist; Vitest suite green; a consolidation guard test asserts the invariants in CI.

**Acceptance**:
1. `ActionPage.tsx`, `GameView.tsx`, `HexMap.tsx`, `IntelPage.tsx`, `OrganizationsPage.tsx`,
   `OrgDashboard.tsx`, `TimeSeriesPanel.tsx` are deleted (each verified unrouted first).
2. `react-leaflet`, `leaflet`, `@types/leaflet` removed from `package.json`; lockfile updated
   without mutating shared `node_modules`.
3. No live route or component imports a deleted file; the suite stays green.

### User Story 2 — The map is a first-class in-game surface (Priority: P1)

A player on the Briefing route sees the real deck.gl/MapLibre situation map (not an SVG
placeholder), color-encoded by the active layer, with a legend — the same map that previously
rendered only in the `/dev/hexmap` harness.

**Independent Test**: Load a seeded game; the Briefing map panel renders `DeckGLMap` fed by the
live snapshot; a Vitest test asserts the map (not the placeholder) mounts.

**Acceptance**:
1. `BriefingPage` renders `DeckGLMap` in its Situation-Map panel, fed by the `useGameState`
   snapshot.
2. The SVG `HexMapPlaceholder` no longer renders on Briefing.
3. The `/dev/hexmap` harness no longer depends on the deleted leaflet `HexMap`.

### User Story 3 — Django state is materialized (Priority: P1)

An operator runs migrations on a fresh database and the `PlayerProfile` table is created; the
`game` app has no pending model changes; PostGIS ORM features are available because
`django.contrib.gis` is installed.

**Independent Test**: `mise run web:migrate` semantics on a fresh/test DB create the `accounts`
tables; `makemigrations --check` reports no pending changes; a smoke test asserts the migration
graph is complete.

**Acceptance**:
1. `web/accounts/migrations/` exists with an initial migration materializing `PlayerProfile`.
2. `web/game/migrations/` captures pending model changes (`makemigrations` clean afterward).
3. `django.contrib.gis` is in `INSTALLED_APPS` (`web/babylon_web/settings/base.py`).

### User Story 4 — spec-042 is audited and closed (Priority: P2)

A reviewer reads the 042 evidence audit: all 49 tasks classified done-with-evidence / superseded /
residual, residuals assigned to 092/093/095, and spec-042 marked superseded.

**Acceptance**:
1. An audit table covering T001–T049 is committed with file citations.
2. spec-042's status is marked **superseded by 051/061 + spec-091**.
3. Residual tasks are assigned to 092/093/095.

### User Story 5 — spec-090 residuals closed (Priority: P2)

The Cold Collapse canon is protected against regression and its loose ends are closed: the
pre-commit prettier hook matches the gate's prettier, a Playwright visual-baseline suite pins the
canon, no faux-italic is used, the semantic type-role tokens are ported (or deferral documented),
the lens→layer contract test is tightened, and the ramp docstrings match the Article VII amendment.

## Requirements *(mandatory)*

- **FR-001**: Delete the seven named legacy sibling components after verifying each is unrouted.
- **FR-002**: Remove the react-leaflet/leaflet dependency from `package.json` and the lockfile
  without mutating shared `node_modules`; `rg leaflet web/frontend/src` MUST be empty.
- **FR-003**: Any orphan created solely by these deletions is either removed (own-mess cleanup) or
  reported; the entangled legacy `Inspector` cluster is removed as a unit with its dead tests.
- **FR-004**: `BriefingPage` MUST render the live `DeckGLMap` fed by the current snapshot.
- **FR-005**: `web/accounts` MUST have an initial migration; `web/game` MUST have no pending
  model changes; `django.contrib.gis` MUST be in `INSTALLED_APPS`.
- **FR-006**: A committed 042 evidence audit MUST classify all 49 tasks and mark 042 superseded.
- **FR-007**: A course-correction verification record MUST assess phases 4/6/7 against live code.
- **FR-008**: The Vitest suite MUST remain ≥357 green; all Playwright suites (8 existing + the new
  visual suite) MUST be green; `poetry run pytest tests/unit/web/` MUST be green.
- **FR-009 (090 residuals)**: prettier hook bumped to 3.x matching the gate; a Playwright visual
  suite pinning the canon (fixed viewport, animations off); no faux-italic (Space Grotesk has no
  italic face); the 35 semantic type-role tokens ported or deferral documented; the C6 lens→layer
  contract test pinned against independently-stated expectations; `theme/colors.ts` docstrings
  aligned to the amendment (monotonic EXCEPT named alarm terminals/diverging).

## Constraints & Non-Goals

- **Server-authoritative**: no engine/DB/endpoint logic added; `src/babylon/**` and
  `web/observatory/**` are off-limits (other lanes own them).
- **Shared env**: never `npm install` / `poetry install`; lockfile-only for dependency removal.
- **No provenance re-wire here**: wiring `BreakdownTooltip` into the live intel/verb screens is
  spec-093's scope (program §2). The selector/verb infra is preserved but not re-plumbed in 091.
- **No new endpoints.**

## Success Criteria

- SC-001: `rg leaflet web/frontend/src` empty; the seven legacy files absent.
- SC-002: Vitest ≥357 green; all Playwright suites (incl. the new visual suite) green.
- SC-003: `poetry run pytest tests/unit/web/` green; fresh-DB migration materializes
  `PlayerProfile`; `makemigrations --check` clean.
- SC-004: 042 audit table committed; 042 marked superseded; residuals assigned.
