# Tasks: Event Log + Tick Resolution Surfaces

**Input**: `specs/092-event-log/{spec,plan}.md`
**Prerequisites**: stacks on `091-frontend-consolidation` (`c1d1a834`).
**Tests**: TDD red-first per unit. `tests/unit/web/` 255/255 green; Vitest 378/378 green;
Playwright owner-run flow documented (not required to pass unattended).

## Format: `[ID] [Story] Description`

## Phase 1 — Backend: tick_event persistence + journal/alerts dashboards (US-backend, red-first)

- [x] T001 RED: add `TestTickEventPersistence`, `TestJournalDashboard`, `TestAlertsDashboard` to
  `tests/unit/web/test_engine_bridge.py` against the `{}` stubs. Confirmed RED (6 failed).
- [x] T002 Add `_tick_event_row`, `_game_event_from_tick_event_row`,
  `_persist_tick_events_safe` helpers to `web/game/engine_bridge.py`.
- [x] T003 Wire `_persist_tick_events_safe` into `resolve_tick()` right after
  `_state_to_snapshot`; best-effort, never fails tick resolution.
- [x] T004 Add `PostgresRuntime.query_session_events(game_id, *, limit=200)` to
  `src/babylon/persistence/postgres_runtime/_legacy.py` (session-wide history; sibling to the
  existing single-tick `query_tick_events`).
- [x] T005 Implement `get_journal_dashboard` (via `query_session_events`, optional-capability
  `getattr` pattern matching `get_game_timeseries`'s established SQLite-fallback precedent) and
  `get_alerts_dashboard` (via `query_tick_events` on the latest hydrated tick, filtered to
  `{critical, warning}`).
- [x] T006 GREEN: `poetry run pytest tests/unit/web/test_engine_bridge.py` 31/31;
  `poetry run pytest tests/unit/web/` 255/255; `ruff check`/`ruff format`/`mypy --strict` clean.
  Commit (`eabaed54`).

## Phase 2 — Frontend contract: journal/alerts MSW fixtures (US1/US2, red-first)

- [x] T007 RED: add `journal-alerts-contract.test.tsx` asserting the `{events: GameEvent[]}` /
  `{alerts: GameEvent[]}` shapes over `fetch()` — no MSW handler yet. Confirmed RED
  (`ECONNREFUSED`).
- [x] T008 Add `/api/games/:id/journal/` and `/api/games/:id/alerts/` handlers + a 3-event mixed-
  severity fixture to `web/frontend/src/test/handlers.ts`.
- [x] T009 GREEN: contract test 2/2. Add `JournalPayload`/`AlertsPayload` to `types/game.ts`.

## Phase 3 — Event Log page (US1)

- [x] T010 Add `useJournal` hook (`web/frontend/src/hooks/useJournal.ts`) — polling GET wrapper
  matching the `useTimeseries`/`useCommunities` sibling pattern (raw `fetch` + try/catch/finally;
  the `api/client.ts` `get<T>()` helper trips a `react-hooks/set-state-in-effect` lint rule this
  shape doesn't).
- [x] T011 Add `EventLogPage.tsx` — severity-filter chips (all/critical/important/informational,
  the REAL `EventSeverity` union) over a scrolling row list, classified via the existing
  `lib/eventClassifier.ts`. Wire into `App.tsx` replacing the `/log` "coming soon" stub.
- [x] T012 Add `event-log-page.test.tsx` — heading, live-fetched rows, all 3 filter tiers, empty
  state (via `server.use()` override). 6/6 green.

## Phase 4 — Tick Resolution page (US2)

- [x] T013 Add `useAlerts` hook (`web/frontend/src/hooks/useAlerts.ts`) — same pattern as
  `useJournal`.
- [x] T014 Add `TickResolutionPage.tsx` — animated step-through: `snapshot.events` (current tick)
  grouped by `classifyEvents` severity (informational→important→critical), plus a real
  alerts-sourced "STATE RESPONSE" final step. Tick-reset uses React's "adjust state during render"
  pattern, not a `useEffect(fn, [tick])` (lint-clean). Wire `/games/:id/resolution` route in
  `App.tsx`.
- [x] T015 Add `tick-resolution-page.test.tsx` — header tick math, staged reveal (Continue
  withheld before the last step), auto-advance to state-response + Continue, Continue navigation,
  no-changes empty state (MSW override to empty alerts). 5/5 green, real timers throughout (fake
  timers deadlock testing-library's `waitFor` polling, which shares the same clock).

## Phase 5 — End Turn wiring (US3 / gate)

- [x] T016 Add "End Turn" button to `OrgsPage.tsx` (`PageHeader` right slot) — the only caller of
  `useGameState().resolveTick()`; navigates to `/games/:id/resolution` on success.
- [x] T017 Add End Turn navigation test to `pages-v2.test.tsx`'s OrgsPage suite. 16/16 green.

## Phase 6 — Quality gate + Playwright owner-run flow

- [x] T018 `mise run web:check` — fix 2 real errors surfaced by new code (hooks lint pattern
  mismatch; TickResolutionPage's tick-reset effect) + 2 prettier formatting fixes. 378/378 Vitest,
  0 eslint errors (67 pre-existing non-null-assertion warnings untouched, all in files this spec
  didn't modify).
- [x] T019 Add `e2e/end-turn-flow.spec.ts` — gated on `SPEC061_TEST_SESSION_ID` (spec-091
  precedent); confirmed it skips cleanly without the env var. Owner-run checklist recorded in the
  close-out report.

## Phase 7 — Close-out

- [x] T020 Update `project/01-state-of-the-world.md` stub inventory (journal/alerts no longer
  `{}`; `/log` no longer "coming soon").
- [x] T021 Update `project/09-program-full-game.md` §2 spec-092 entry: status DONE.
- [x] T022 Update `ai-docs/state.yaml`.
- [x] T023 Write contracts `journal.yaml`/`alerts.yaml`; write close-out report
  `.superpowers/sdd/reports/092.md`.
