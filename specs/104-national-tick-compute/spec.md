# spec-104 — National tick-compute profile + budget

**Program**: 09 Full-Game Build, Lane E (engine). **Spec number**: 104.
**Depends on**: 098-LODES (commute on), 101/102 (trade wired), 068 (BEA
national I-O). **Branch**: `104-national-tick-compute` (off `3dad3896`).
**Status**: implemented.

## Why

The first national-scale COMPUTE measurement. The persistence side is
known (3.17M-hex checkpoint frame = 629 MiB @ 54 s), but nothing measures
the tick loop at 3,156 counties. Before this spec, there was no ratified
per-system wallclock budget and no CI gate to catch regressions. A silent
2× slowdown in any system would ship unnoticed.

## What ships (functional requirements)

- **FR-104-1** — `PerformanceBreakdown.per_system_ms` is populated for
  every run. (Already wired by spec-065 T074; verified functional —
  `SimulationEngine.run_tick` wraps each `system.step()` with
  `time.perf_counter()` and accumulates into `_per_system_ms`.)
- **FR-104-2** — `--scope=national` resolves all ~3,156 US counties
  (excluding Pacific territories `state_fips >= 60` and synthetic
  rest-of-state placeholders `\\d{2}999`) from the SQLite reference DB.
  (Already implemented in `scopes.py:_load_national_fips`.)
- **FR-104-3** — `mise run sim:profile` accepts `--scope` so the
  cProfile wrapper can profile national-scale runs, not just
  detroit-tri-county.
- **FR-104-4** — A ratified per-system wallclock budget is documented in
  `research.md` and enforced by `mise run qa:tick-budget`.
- **FR-104-5** — `DecompositionSystem` carceral-enforcer no-op is closed:
  the system creates CARCERAL_ENFORCER / INTERNAL_PROLETARIAT entities on
  demand when decomposition fires and none exist. (Already closed by
  spec-071; verified at `decomposition.py:298-313`.)

## Constraints

- Pure-perf refactors keep determinism hashes byte-identical.
- Anything reordering float math takes the R-PROOF written-proof path.
- `mise run qa:e2e-regression` must stay Δ=0.000% after each fix.

## Gate

- National 20-tick run inside budget.
- Tri-county hash unchanged (or proven).
- `qa:tick-budget` task green.

## Out of scope

- National-scale data hydration optimization (separate spec).
- UI/observatory changes (web/** not owned by E lane).
