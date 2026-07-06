# plan-105 — National canonical acceptance

## Architecture

The liveness gate is a **runtime assertion** in the headless runner,
not a post-hoc comparison. It fires after the terminal aggregate is
queried (same point where STEP-0 guard runs) and before the run result
is returned. This makes it scope-agnostic: `N_scope =
len(config.scope_fips)` is derived from the resolved scope, so the
same flag works for tri-county (3), Michigan (83), and national (3156).

### Design: `--liveness-gate` flag

**Model**: `SimulationRunConfig.liveness_gate: bool` (default False).

**CLI**: `--liveness-gate` argparse flag → mapped to RunConfig.

**Assertion** (runner.py, after `_query_terminal_aggregates`):
```
if config.liveness_gate:
    n_scope = len(config.scope_fips)
    alive = terminal_state["counties_alive"]
    pop = terminal_state["counties_with_population"]
    if alive != n_scope or pop != n_scope:
        exit_reason = ExitReason.ERRORED
        error_payload = {"name": "LivenessGateFailure", ...}
```

This is **not** a `--strict`-style early-exit (it runs after the loop).
It's a terminal assertion: the run completes, artifacts are emitted,
then the gate validates and sets exit code.

### National run strategy

The national hex hydration takes >10 minutes (spec-104 measured this).
A 200-tick national run projects to multiple hours. The plan:

1. Implement + unit-test the liveness gate (tri-county fixture).
2. Run a **5-tick national validation** (`--scope=national --ticks 5
   --liveness-gate`) to prove the full stack works end-to-end at
   national scale.
3. If time permits, start the full 200-tick run in the background.
4. Verify `qa:storage-budget` against the national run's footprint.
5. Verify Observatory renders the national session.

## Parts

### Part 1: Liveness gate (TDD)
- RED: `test_liveness_gate.py` — gate fails when counties_alive < N_scope
- GREEN: `--liveness-gate` flag + RunConfig field + runner assertion
- REFACTOR: extract `_assert_liveness_or_raise` helper

### Part 2: National validation run
- 5-tick national run with `--liveness-gate`
- Verify liveness, storage, Observatory
- Commit baseline bundle (short-run) or document runtime

### Part 3: Gates
- `qa:e2e-regression` Δ=0.000%
- `mise run check` green
- Commit

## Risk

- **National run too slow**: If the 5-tick national run exceeds the
  session budget, fall back to documenting the infrastructure and
  expected runtime. The liveness gate + Observatory verification are
  the durable deliverables.
- **hex_spatial_map contention**: The #18 fix (spec-104) should prevent
  the zeroing that hit E:101. The STEP-0 guard (spec-102) is the
  backstop.
