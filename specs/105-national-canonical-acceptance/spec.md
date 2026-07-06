# spec-105 — National canonical acceptance

**Program**: 09 Full-Game Build, Lane E (engine). **Spec number**: 105.
**Depends on**: 098-LODES ✅, 068-completion ✅, 104 ✅, 101/102 ✅, 096 ✅.
**Branch**: `105-national-canonical-acceptance` (off `cce596db` = 104's HEAD).
**Status**: implemented.

## Why

The P4 nationwide milestone. Every storage, compute, and observability
investment from Program 09 converges here: a detached `--scope=national`
run across all 3,156 US counties on the full stack (delta persistence,
partitioning, budget gate). This is the canonical acceptance gate that
proves the engine scales from tri-county (3) through Michigan statewide
(83) to the full nation (3,156) without silent-zero failure.

Before this spec, the liveness gate was Michigan-constant (`83`) —
hardcoded in the Michigan baseline with no generalization path. The
STEP-0 guard (spec-102) catches silent-zero at the terminal aggregate,
but no runtime gate asserted `counties_alive == N_scope` for arbitrary
N. A national run could silently drop counties without detection.

## What ships (functional requirements)

- **FR-105-1** — `--liveness-gate` CLI flag: when set, the runner
  asserts `terminal_state.counties_alive == len(config.scope_fips)` and
  `counties_with_population == len(config.scope_fips)` at the terminal
  tick. Failure sets `exit_reason=ERRORED` with a descriptive error
  payload. Works for any scope (tri-county N=3, Michigan N=83, national
  N=3156).
- **FR-105-2** — A national canonical run executes to completion (or
  documents the runtime profile if the full 200-tick run is infeasible
  in-session). Liveness verified: `counties_alive > 0`,
  `counties_with_population > 0`, `total_v > 0`, STEP-0 guard did not
  fire.
- **FR-105-3** — `qa:storage-budget` passes against the national run's
  storage footprint (rows/tick within the 6.8–22.7 GiB projection from
  spec-087/088/089).
- **FR-105-4** — The Observatory (`/observatory`) renders the national
  session: session picker, series browser, boundary flow explorer.
- **FR-105-5** — National baseline bundle committed (if the full run
  completes) or a short-run validation bundle committed (if the full run
  is deferred to operator-side).

## Constraints

- `mise run qa:e2e-regression` must stay Δ=0.000% (tri-county hash
  unchanged).
- `mise run check` green.
- No new primitives — this is acceptance/validation work only.
- National hex hydration is SLOW (>10 min for 3,156 counties). This is
  the dominant cost and is expected.

## Gate

- Liveness gate generalized (works for any N_scope).
- National run executed (full or short validation).
- `qa:storage-budget` green.
- Observatory renders the national session.
- Tri-county hash unchanged.

## Out of scope

- National hex hydration optimization (separate spec).
- UI/observatory changes (web/** not owned by E lane).
- Cold Collapse / endgame mechanics (separate program).
