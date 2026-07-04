# Implementation Plan: Event Log + Tick Resolution Surfaces

**Branch**: `092-event-log` (stacks on `091-frontend-consolidation`) | **Spec**:
`specs/092-event-log/spec.md`
**Program**: 09 Full-Game Build — Lane W. Kit refs: `project/09-program-full-game.md` §1 (R-CONS),
§2 (spec-092), §3 (Lane W file ownership).

## Summary

Implement the two empty `{}` bridge dashboard stubs (`get_journal_dashboard`,
`get_alerts_dashboard`) together with their real frontend consumers (R-CONS), plus the "End Turn"
caller that was missing entirely. Backend: wire `tick_event` persistence into `resolve_tick`, add
a session-wide event query, implement both dashboard methods over real data. Frontend: two new
routed pages (Event Log, Tick Resolution), two new polling hooks, one new button.

## Technical Context

**Language**: Python 3.12 (backend), TypeScript 5.7 (frontend).
**Stack**: Django 5.x + psycopg3 (`PostgresRuntime`), React 19 + Zustand 5 + Vite 6 + Vitest 4 +
Playwright 1.58 — all already installed (shared `node_modules`/`.venv` symlinks, no
install/`poetry install`).
**Constraints**: `mise run web:check` green; `poetry run pytest tests/unit/web/` green (255/255);
Vitest 378/378 (was 364); no engine dynamics changed (presentation + persistence-plumbing only).
**Scope of ownership (Lane W)**: `web/**` (product), including the shared hot file
`web/game/engine_bridge.py` (owned this spec per the 09 kickoff prompt; next W spec, 093, stacks
after and must not conflict). MUST NOT touch `src/babylon/engine/**` — the ONE exception is
`src/babylon/persistence/postgres_runtime/_legacy.py` (adding `query_session_events`), which is
persistence plumbing the bridge already depends on, not engine dynamics; no `WorldState`/formula/
System changes anywhere.

## Constitution Check

*GATE: Must pass before implementation. Constitution v2.7.0 (Amendments K + L ratified).* UI work
is bound by Article VII + VIII.9.

| Gate | Requirement | This feature | Status |
|------|-------------|--------------|--------|
| **III.1 No Magic Numbers** | Constants trace to a grounded source | `_JOURNAL_LIMIT=200`/`_ALERT_SEVERITIES` are named module constants with docstrings explaining the choice (payload-size cap; matches spec-061's 3-bucket severity taxonomy) — no bare literals in dashboard logic. | PASS |
| **III.7 Determinism / Frozen models** | No engine/state changes | Zero `WorldState`/formula/System changes. `resolve_tick`'s new write is a side-effecting persistence call *after* the deterministic step completes — it cannot affect `new_state` or the returned snapshot's content, only adds a row for later read-back. | PASS |
| **III.8 Data-Grounding** | Claims trace to data/code | The event-type-casing mismatch (spec.md "Known Gap") is verified against `src/babylon/models/enums/events.py` and `lib/eventClassifier.ts` directly, not asserted from memory. | PASS |
| **II.11 / II.12 authoring API** | Engine authoring untouched | No engine authoring API touched; `query_session_events` is a read-only SQL helper alongside the existing `query_tick_events`/`query_tick_summary_series` siblings. | PASS |
| **I.20 / IV** | Layering respected | `engine_bridge.py` remains the sole `web/` importer of `babylon.*`; Django views only call bridge methods (unchanged pattern, `web/game/api.py`'s `game_journal`/`game_alerts` predate this spec). | PASS |
| **VII** | Color=meaning; no decorative glow | `EventLogPage`/`TickResolutionPage` reuse existing `bbl` components and `theme/colors.ts`-derived Tailwind tokens (`text-crimson`→`--babylon-laser`, etc.) — no new hex literals, no decorative glow. | PASS |
| **VIII.9 Community as Pairwise Edge** | Hyperedges never pairwise / spatial hulls | Neither page renders community/hyperedge data. | N/A |
| **R-CONS** | Build endpoints WITH consumers | `get_journal_dashboard` → EventLogPage (via `useJournal`); `get_alerts_dashboard` → TickResolutionPage's state-response step (via `useAlerts`). Both wired in this spec, same commit series. | PASS |

**Gate resolution**: No conflicts. This is presentation + read/write persistence plumbing over
already-committed engine output; no dynamics, no new constants beyond a documented payload cap and
a severity allowlist.

## Project Structure — touched files

```
web/game/engine_bridge.py                          # tick_event persist + journal/alerts dashboards (shared hot file)
src/babylon/persistence/postgres_runtime/_legacy.py # + query_session_events
tests/unit/web/test_engine_bridge.py                # red-first: TestTickEventPersistence, TestJournalDashboard, TestAlertsDashboard

web/frontend/src/types/game.ts                      # + JournalPayload, AlertsPayload
web/frontend/src/hooks/useJournal.ts                # NEW
web/frontend/src/hooks/useAlerts.ts                  # NEW
web/frontend/src/components/pages/EventLogPage.tsx   # NEW — replaces the /log stub
web/frontend/src/components/pages/TickResolutionPage.tsx  # NEW
web/frontend/src/components/pages/OrgsPage.tsx       # + End Turn button
web/frontend/src/App.tsx                             # route /log → EventLogPage; + /resolution route
web/frontend/src/test/handlers.ts                    # + /journal/, /alerts/ MSW fixtures
web/frontend/src/__tests__/integration/journal-alerts-contract.test.tsx  # NEW, red-first
web/frontend/src/components/pages/__tests__/event-log-page.test.tsx     # NEW
web/frontend/src/components/pages/__tests__/tick-resolution-page.test.tsx  # NEW
web/frontend/src/components/pages/__tests__/pages-v2.test.tsx           # + End Turn test
web/frontend/e2e/end-turn-flow.spec.ts               # NEW, owner-run (SPEC061_TEST_SESSION_ID gated)

specs/092-event-log/contracts/journal.yaml           # NEW
specs/092-event-log/contracts/alerts.yaml            # NEW
```

## Phased Approach (each phase = one commit, TDD red-first)

1. **Backend RED** → 6 failing tests in `test_engine_bridge.py` (tick_event persistence,
   journal dashboard, alerts dashboard) against the `{}` stubs. Confirmed RED (6 failed, 1 passed
   no-op).
2. **Backend GREEN** → `_tick_event_row`/`_game_event_from_tick_event_row`/
   `_persist_tick_events_safe` helpers; `query_session_events` on `PostgresRuntime`; implement
   both dashboard methods; wire persistence into `resolve_tick`. 31/31 `test_engine_bridge.py`,
   255/255 `tests/unit/web/`, ruff+mypy strict clean.
3. **Frontend contract RED** → `journal-alerts-contract.test.tsx` against unmocked routes
   (confirmed RED: `ECONNREFUSED`, no MSW handler).
4. **Frontend contract GREEN** → add MSW handlers + fixture; 2/2 green.
5. **EventLogPage** → hook + page + tests (6 tests): heading, live rendering, 3 severity filters,
   empty state.
6. **TickResolutionPage** → hook + page + tests (5 tests): header tick math, staged reveal,
   auto-advance to state-response step, Continue navigation, no-changes empty state.
7. **End Turn wiring** → OrgsPage button + `pages-v2.test.tsx` navigation test.
8. **Quality gate** → `mise run web:check` (fixed 2 real lint errors surfaced by new code: a
   `react-hooks/set-state-in-effect` false-positive-vs-pattern-mismatch in the two new hooks,
   resolved by matching the sibling `useTimeseries`/`useCommunities` try/catch/fetch shape instead
   of the `api/client.ts` helper; a `setStep(0)` tick-reset effect in TickResolutionPage, resolved
   via React's endorsed "adjust state during render" pattern instead of `useEffect(fn, [tick])`;
   and one `sonarjs/no-nested-conditional` in EventLogPage's subtitle, resolved by extracting a
   `subtitleFor()` helper matching OrgsPage's existing precedent). 378/378 Vitest, 0 lint errors.
9. **Playwright owner-run flow** → `e2e/end-turn-flow.spec.ts`, gated on
   `SPEC061_TEST_SESSION_ID` (same precedent as spec-091's behavioural suites); confirmed it skips
   cleanly without the env var.
10. **Close-out** → `project/01-state-of-the-world.md`, `09` §2 spec-092 status,
    `ai-docs/state.yaml`, this plan + tasks.md + contracts.

## Complexity Tracking

| Divergence from the mockup | Why unavoidable | Resolution |
|---|---|---|
| `TickResolution.jsx`'s 5 fixed phases (OBSERVE/ORIENT/DECIDE/ACT/RESPOND) with hardcoded narration | The engine has no phase-tagged per-tick narration; fabricating it would violate III.8/data-grounding | Steps are real classified-event groups (informational→important→critical) plus a real alerts-sourced "STATE RESPONSE" step; chrome (progress bar, header, Skip/Continue) ported, content grounded |
| `EventLog.jsx`'s 5-tier filter (`all/info/warning/critical/rupture`) | "rupture" isn't a `GameEvent.severity` value; "warning" isn't either (frontend's is `critical/important/informational`) | Filter chips use the REAL `EventSeverity` union so filtering is truthful, not decorative |
| Mock journal fixture uses UPPERCASE event types (`RUPTURE`, `UPRISING`) | Matches `eventClassifier.ts`'s existing map + `test/fixtures.ts` precedent; using the real lowercase engine casing would make every fixture event classify as "informational" (see spec.md Known Gap) | Documented as a pre-existing mismatch, not silently patched — out of this spec's scope |
