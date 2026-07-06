# research-105 — National canonical acceptance

## Pre-implementation findings (2026-07-06)

### National scope resolution

`resolve_scope('national')` returns 3,156 county FIPS codes from the
SQLite reference DB (`scopes.py:_load_national_fips`). Excludes Pacific
territories (`state_fips >= 60`) and synthetic rest-of-state
placeholders (`\d{2}999`). External nodes: `{'canada', 'china'}`.

```
National scope counties: 3156
External nodes: frozenset({'canada', 'china'})
First 5: ['01001', '01003', '01005', '01007', '01009']
Last 5:  ['56037', '56039', '56041', '56043', '56045']
```

### hex_spatial_map state

The `hex_spatial_map` table currently has 1,884,347 rows across 3,128
distinct counties. This is 28 fewer than the 3,156 national scope —
these are counties with no hydrated hex cells (likely very small
territories or missing TIGER data). The liveness gate must account for
this: it should assert `counties_alive > 0` (not necessarily == 3156
at the hex level), while the terminal aggregate (which joins through
`view_runtime_trace_emission`) resolves to the county level.

### Existing liveness infrastructure

1. **STEP-0 guard** (`_assert_county_resolution_or_raise`, runner.py:556):
   Catches the silent-zero bug where hex rows exist but county
   resolution yields zero counties. Does NOT assert a specific count.

2. **Population liveness** (regression_test.py:553-568): Asserts
   `counties_with_population == counties_alive` (every econ-alive
   county has a living population). Post-hoc, baseline-dependent.

3. **`counties_alive` exact match** (regression_test.py:543-551):
   Compares `actual["terminal_state"]["counties_alive"]` against
   `expected["terminal_state"]["counties_alive"]` from the baseline
   JSON. Already scope-agnostic (reads N from baseline), but requires a
   pre-existing baseline.

### What needs generalizing

The regression_test.py comparison is already general (reads expected
N from baseline). What's missing is a **runtime** liveness gate that:
- Does NOT require a pre-existing baseline (national baseline would be
  gigabytes)
- Derives N_scope from the resolved scope (`len(config.scope_fips)`)
- Asserts `counties_alive == N_scope` AND
  `counties_with_population == N_scope` at the terminal tick
- Sets exit_reason=ERRORED on failure (like --strict does for alarms)

This is the `--liveness-gate` flag.

### National run runtime projection

From spec-104 measurements:
- Michigan statewide (83 counties): 2.05s/tick, 24.9s hex hydration
- National (3,156 counties = 38× Michigan): projected ~78s/tick,
  >10min hex hydration
- 200-tick national: ~4.3 hours (hydration + tick loop)
- 5-tick national: ~17min (hydration + 5 ticks)

The 5-tick national validation is feasible in-session. The 200-tick
run is operator-side.

### Observatory readiness

The Observatory (`/observatory` route group, built by O:096+099) reads
from the same Postgres tables the runner writes to. It should render
any session with trace data. No E-lane changes needed — just
verification.

### Pre-existing LSP errors

The worktree has pre-existing LSP errors in `gamma_hydration.py`
(FactBilateralTradeAnnual import), `manifest.py` (shock_schedule
attribute), and `test_runner_fail_fast.py` (TerminalAggregateResolutionError).
These are from other lanes' in-progress work and are NOT related to
spec-105. Verified: `TerminalAggregateResolutionError` is defined at
`runner.py:556` — the LSP is confused by the worktree state.
