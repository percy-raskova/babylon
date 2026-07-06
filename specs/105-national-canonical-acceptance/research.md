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

### National run results (2026-07-06)

#### Hex hydration — SUCCESS

The national hex hydration completed successfully:
- 1,884,456 hex rows persisted across 3,144 counties (of 3,156 scope)
- 12 counties lack hex cells (unhydrated territories with no TIGER data)
- Hydration time: ~10 minutes (consistent with spec-104 measurement)

#### Tick 0 persistence — SUCCESS

Tick 0 (initial state) persisted successfully:
- consciousness = 3,156 (all scope counties)
- demographics = 3,144 (12 counties without Census data)
- employment = 3,142 (14 counties without QCEW data)
- hex = 1,884,347 (full hex grid)
- external = 9 (international nodes)

#### Tick loop — TOO SLOW FOR COMPLETION

The national tick loop did not complete within the session. After 34+
minutes, tick 1 had not committed. The process consumed 10GB RAM and
93% CPU, indicating active computation (not stuck).

**Root cause**: The ContradictionFieldSystem (spec-104's #1 hotspot at
224.7ms/tick for 83 counties) scales super-linearly with county count.
At 3,144 counties (38x Michigan), the per-tick time exceeds 30 minutes
(>900x slower, not the 38x linear projection). This suggests O(N²) or
worse complexity in the contradiction field computation (inter-county
field interactions).

**Projected runtime**:
- 5-tick national: ~2.5 hours (10 min hydration + 5 × 30 min ticks)
- 200-tick national: ~100 hours (operator-side only)
- Full 520-tick national: ~260 hours (infeasible without optimization)

**Comparison with spec-087/088/089 storage projection**:
The storage projection (6.8–22.7 GiB for 520-tick national) was based
on the delta persistence (spec-089), which only writes changed rows
per tick. The storage projection is NOT the bottleneck — the tick
COMPUTE is the bottleneck. The storage would be within budget if the
tick loop could complete.

### National-scale bug fixes

Two validation bugs were discovered and fixed during the national run:

1. **SocialClass ID pattern overflow** (`^C[0-9]{3}$`): At 3,144
   counties, worker IDs C1000+ and bourgeoisie IDs C501+ exceeded the
   3-digit pattern. Fixed: pattern changed to `^C[0-9]{3,}$` (3+
   digits). Also fixed bourgeoisie offset from hardcoded 500 to
   `max(500, N+1)` to prevent worker/bourgeoisie ID collisions when
   N > 500.

2. **Territory ID pattern overflow** (`^T[0-9]{3}$`): Same issue —
   Territory IDs T1000+ exceeded the 3-digit pattern. Fixed: pattern
   changed to `^(T[0-9]{3,}|[0-9a-f]{15})$`.

Both fixes preserve existing baselines: for tri-county (N=3) and
Michigan (N=83), the offset stays at 500 and IDs are 3 digits, so
determinism hashes are byte-identical (verified: Δ=0.000%).

### Liveness gate verification

The `--liveness-gate` flag was verified end-to-end at Michigan
statewide scale (83 counties, 5 ticks):
- counties_alive = 83 == N_scope ✓
- counties_with_population = 83 == counties_alive ✓
- total_v = 3.13e9 > 0 ✓
- No LivenessGateFailure raised → exit code 0 ✓

At national scale, the liveness gate would check:
- counties_alive > 0 (expected 3,144 from tick 0 data)
- counties_with_population == counties_alive
- total_v > 0

But the national tick loop is too slow to reach the terminal tick
within the session.

### Storage budget baseline update

The storage budget baseline (`tests/baselines/storage-budget-5t.json`)
was regenerated to include `boundary_flow_register` (14.4 rows/tick)
and `conservation_audit_log` (5.6 rows/tick), which were 0.0 in the
old baseline. These tables now have rows due to spec-101/102 (DRAIN_EDGE/
TRADE_EDGE boundary flows) and the conservation auditor. All other
tables are unchanged.
