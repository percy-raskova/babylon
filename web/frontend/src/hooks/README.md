# Frontend Hooks — Polling Cadence

## Spec 061 FR-028: 2-second polling interval

All polling hooks in this directory use **`POLL_INTERVAL_MS = 2000`** as the
default interval between fetches against the Django backend. The constant is
declared at the top of each hook (currently `useGameState.ts` and
`useTimeseries.ts`).

### Why 2 seconds?

The v1 pages have been running on this cadence stably since before spec 061;
the v2 pages adopt the same value for two reasons:

1. **Tick-alignment**: a typical resolved tick changes engine state in
   under one second. Polling every 2 s means the displayed tick number
   updates within at most 2× the interval (4 s), which the Playwright
   `polling-tick-aligned.spec.ts` test enforces.
1. **Backend load**: the snapshot endpoint and the new
   `/timeseries/` endpoint are both cheap reads against indexed tables.
   Multiple concurrent v2 pages × 2 s polling produces well under
   1 RPS per session, comfortably under the alpha-tier load budget per
   the spec 061 plan.md.

### Don't deviate per-hook without good reason

Different intervals per hook create timing drift between sibling panels
on the same page (e.g., the tick badge updating before the sparkline
strip). If a future hook genuinely needs a different cadence (e.g., a
real-time vote tally panel that needs sub-second updates), introduce a
separate constant and document the rationale here.

### Tests

- `web/frontend/e2e/polling-tick-aligned.spec.ts` asserts the
  Briefing-page subtitle's tick number advances within 4 s of a
  `/resolve/` call.
- `useGameState.ts` and `useTimeseries.ts` declare `POLL_INTERVAL_MS`
  at module scope so a future test can monkeypatch a faster cadence
  without rewriting the hook.
