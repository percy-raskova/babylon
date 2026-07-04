# Feature Specification: Event Log + Tick Resolution Surfaces

**Feature Branch**: `092-event-log`
**Created**: 2026-07-04
**Status**: Implemented
**Program**: 09 Full-Game Build — Lane W (web product). Advisory audit number: n/a (first-come
092). Stacks on `091-frontend-consolidation` (`c1d1a834`).
**Input**: Replace the `/games/:id/log` "coming soon" stub with a real Event Log page over the
classified event stream; build the Tick Resolution end-of-turn screen; implement
`EngineBridge.get_journal_dashboard`/`get_alerts_dashboard` (today `{}`) WITH these two consumers
(program ruling R-CONS).

## Overview

Two bridge dashboard methods — `get_journal_dashboard` and `get_alerts_dashboard` — have returned
`{}` since spec-061 scaffolded the dashboard surface. Their Django views (`game_journal`,
`game_alerts` in `web/game/api.py`) already exist and already route to them; only the bridge
implementation and a frontend consumer were missing. Separately, `/games/:id/log` has rendered a
literal "coming soon" placeholder, and there is no end-of-turn resolution screen — `resolveTick()`
existed on the game store but nothing in the UI ever called it.

This spec closes all three gaps as one unit (R-CONS: "build endpoints WITH the consumer"):

1. **`tick_event` persistence.** `resolve_tick()` now writes every tick's classified events into
   the `tick_event` table (`PostgresRuntime.persist_tick_events`, existing since spec-037/061 but
   never called in the resolve path) via a best-effort, non-fatal helper. SQLite-backed
   `RuntimeDatabase` (dev/test) has no such method and silently no-ops, matching the established
   `get_game_timeseries` fallback pattern.
2. **`get_journal_dashboard`.** Reads back the full cross-tick history via a new
   `PostgresRuntime.query_session_events` method, returning `{"events": GameEvent[]}` in the exact
   shape the frontend already understands (`id/type/tick/severity/title/body/data`, spec-061
   FR-012).
3. **`get_alerts_dashboard`.** Reads the *latest resolved tick's* events via the existing
   `query_tick_events(session_id, tick)`, filtered to `{critical, warning}` severities, returning
   `{"alerts": GameEvent[]}` — the "threshold crossings" surfaced right after a tick resolves.
4. **Event Log page** (`/games/:id/log`) — a filterable (all/critical/important/informational),
   scrollable history view fed by `useJournal` → `GET /journal/`, classified with the existing
   `lib/eventClassifier.ts` (previously used only by the notification tray).
5. **Tick Resolution page** (`/games/:id/resolution`) — an animated step-through of the tick that
   was just resolved: `snapshot.events` grouped by severity (ascending drama), followed by a
   "STATE RESPONSE" step sourced from `useAlerts` → `GET /alerts/`.
6. **End Turn button** (Organizations page) — the only caller of `resolveTick()`; navigates to the
   Tick Resolution screen on success.

The design canon mockups `design/mockups/ui_kits/webapp/EventLog.jsx` and `TickResolution.jsx` are
reference only (standalone JSX, not project code — §4.4). `EventLog.jsx`'s design is ported
directly (severity-filter chips over a scrolling row list); `TickResolution.jsx`'s fabricated
OBSERVE/ORIENT/DECIDE/ACT/RESPOND phase narration does not exist in the engine, so its chrome
(progress bar, "Resolving Tick N → M" header, Skip/Continue) is ported but its *content* is
grounded in real classified events instead of invented phase copy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Event Log renders real history (Priority: P1)

A player opens `/games/:id/log` after several ticks have passed. They see every recorded event
across the game's history (not just the current tick), each row showing tick number, event type,
and a plain-language summary. They can filter to just critical, just important, or just
informational events, or view everything.

**Independent test**: seed MSW/backend fixtures with events across ticks 3–5 spanning all three
severities; render the page; assert all three appear; click each filter chip; assert only the
matching-severity rows remain.

### User Story 2 — Tick Resolution shows what just happened (Priority: P1)

After clicking "End Turn," the player is shown a short animated summary of the tick that just
resolved — grouped by how alarming the changes were, ending with a "state response" section for
any critical/warning threshold crossings — before landing back on the Briefing.

**Independent test**: seed a snapshot with one critical-severity event and a non-empty alerts
fixture; render the page; assert the header shows the correct tick transition; assert the reveal
starts on step 0 (Continue withheld); after the auto-advance delay, assert the state-response step
and the Continue button appear; clicking Continue navigates to `/games/:id`.

### User Story 3 — End Turn → resolution → log entry (Priority: P1, gate)

From the Organizations page, the player clicks "End Turn." The tick resolves, the Tick Resolution
screen appears, they click Continue, and the Event Log (visited afterward) reflects the resolved
tick's history.

**Independent test**: Playwright, gated on a live seeded session (`SPEC061_TEST_SESSION_ID`) —
see `e2e/end-turn-flow.spec.ts`. Owner-run per the spec-091 precedent (this agent does not stand up
`mise run web:dev` + a seeded Postgres session unattended).

## Requirements *(mandatory)*

- **FR-J1**: `get_journal_dashboard(session_id)` MUST return `{"events": [...]}, up to 200 rows,
  newest-tick-first, degrading to `[]` when the persistence layer lacks `query_session_events`
  (never raises).
- **FR-A1**: `get_alerts_dashboard(session_id)` MUST return `{"alerts": [...]}` scoped to the
  latest hydrated tick, filtered to `severity in {critical, warning}`, degrading to `[]` when the
  persistence layer lacks `query_tick_events` (never raises).
- **FR-P1**: `resolve_tick()` MUST persist the resolved tick's events into `tick_event` via
  `persist_tick_events` when the persistence layer supports it; a persistence failure MUST NOT
  fail tick resolution (logged, swallowed).
- **FR-UI1**: `/games/:id/log` MUST render classified history from `GET /journal/`, with working
  severity filters, and an explicit empty state.
- **FR-UI2**: `/games/:id/resolution` MUST render the just-resolved tick's classified events plus
  the alerts feed, gated behind an animated reveal that ends in a "Continue" action returning to
  Briefing.
- **FR-UI3**: exactly one UI surface calls `resolveTick()` (End Turn, Organizations page) and
  navigates to `/games/:id/resolution` on success.

## Success Criteria *(mandatory)*

- **SC-001**: `mise run web:check` green (tsc + eslint + prettier + Vitest).
- **SC-002**: `poetry run pytest tests/unit/web/test_engine_bridge.py` green, including red-first
  journal/alerts/tick-event-persistence tests.
- **SC-003**: journal/alerts response schemas pinned by an MSW contract test
  (`journal-alerts-contract.test.tsx`).
- **SC-004**: the end-turn → resolution → log Playwright flow exists and is documented as an
  owner-run check (not required to pass unattended).

## Known Gap (documented, not fixed here)

`lib/eventClassifier.ts`'s `EVENT_SEVERITY_MAP` keys are UPPERCASE (`"UPRISING"`, `"RUPTURE"`,
...), matching the pre-existing test-fixture convention (`test/fixtures.ts`'s `makeEvent()`). The
real engine's `EventType` enum values are lowercase snake_case (`"uprising"`, `"rupture"`, ...,
verified in `src/babylon/models/enums/events.py`), so on real production data every event
classified as the default `"informational"` bucket via that classifier. This mismatch
**predates this spec**.

**Update (spec-092 review fix, 2026-07-04)**: the original framing above overstated the fix
cost — "re-casing 70+ `EventType` enum values" was never the realistic option; the actual
smaller fix is re-casing (or adding lowercase aliases to) the classifier's own ~15-entry
`EVENT_SEVERITY_MAP`, a small, localized change. More importantly, `EventLogPage` and
`TickResolutionPage` (this spec's two pages) no longer depend on the classifier at all — the
review fix (Defect B) changed both to read the backend's already-correct `GameEvent.severity`
(spec-061 FR-012: `critical`/`warning`/`informational`, derived server-side in
`engine_bridge.py`'s `_classify_event`) directly, making the classifier's casing irrelevant to
these two consumers. The gap is now scoped down to its one remaining real consumer: the live
notification tray (`gameStore.ts`'s `accumulateEvents` → `uiStore.ts`'s
`groupEventsBySeverity`, still keyed on the classifier's `"critical"/"important"/
"informational"` vocabulary) and the legacy `components/events/EventLog.tsx` panel. Recasing
those is still out of this spec's scope, but is a smaller lift than originally stated — a call
for the owner.
