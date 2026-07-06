# plan-104 — National tick-compute profile + budget

## Pre-implementation findings (2026-07-05)

Three of the five master-plan items were already done by prior specs:

| Item | Master plan said | Actual state | Done by |
|------|-----------------|--------------|---------|
| `per_system_ms` wiring | "exists but is empty — wire it" | Fully wired: `SimulationEngine.run_tick` wraps every `system.step()` with `time.perf_counter()`, accumulates into `_per_system_ms`; runner reads it into `PerformanceBreakdown` | spec-065 T074 |
| DecompositionSystem no-op | "Close the carceral-enforcer no-op" | Closed: `decomposition.py:298-313` creates CARCERAL_ENFORCER / INTERNAL_PROLETARIAT on demand via `_create_target_entity` | spec-071 |
| `--scope=national` | implied | Works: `scopes.py:_load_national_fips` reads all US counties from SQLite | spec-064 |

Remaining work:
1. `sim:profile` doesn't accept `--scope` (hardcodes detroit-tri-county)
2. No ratified budget / `qa:tick-budget` gate
3. National profile not yet measured

## Implementation steps

### Step 1 — `sim:profile` scope support
Add `--scope` arg to `tools/profiler.py` and `tools/shared.run_simulation`.
Default: `detroit-tri-county` (backward compat).

### Step 2 — National 20-tick profile
Run `--scope=national --ticks=20`, collect `summary.json.performance.per_system_ms`.

### Step 3 — Ratify budget
Set budget numbers in `qa:tick-budget` task (per master plan §6: "number
set AFTER first measurement").

### Step 4 — `qa:tick-budget` gate
Add mise task that runs a short national profile and checks against the
ratified budget.

### Step 5 — Verify
`mise run qa:e2e-regression` Δ=0.000%.

## Determinism preservation

All changes are pure-perf (profiler tooling, mise tasks). No engine math
reordering. No baseline changes expected.
