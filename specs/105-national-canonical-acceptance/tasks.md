# tasks-105 — National canonical acceptance

## Part 1: Liveness gate (TDD)

- [x] T01 — RED: `test_liveness_gate.py` — gate fails when
      `counties_alive < N_scope`; gate passes when equal; gate is
      no-op when flag is False
- [x] T02 — GREEN: `SimulationRunConfig.liveness_gate` field +
      `--liveness-gate` CLI flag + runner assertion
      (`_assert_liveness_or_raise` helper)
- [x] T03 — REFACTOR: assertion logic in testable helper, 6 unit tests
      all passing
- [x] T04 — Commit: `feat(gate): spec-105 --liveness-gate runtime assertion`

## Part 2: National validation run

- [x] T05a — Discovered national-scale bug: SocialClass ID pattern
      `^C[0-9]{3}$` rejects 4-digit IDs (C1000+) when county count > 999;
      bourgeoisie offset 500 causes ID collisions when N > 500
- [x] T05b — Fix: pattern `^C[0-9]{3,}$` (3+ digits) + dynamic
      bourgeoisie offset `max(500, N+1)` (preserves small-scope baselines)
- [ ] T06 — Run 5-tick national validation
      (`--scope=national --ticks 5 --liveness-gate`)
- [ ] T07 — Verify liveness: `counties_alive > 0`,
      `counties_with_population > 0`, `total_v > 0`, STEP-0 guard
      did not fire
- [ ] T08 — Verify `qa:storage-budget` against national run footprint
- [ ] T09 — Verify Observatory renders the national session
- [ ] T10 — Commit national baseline bundle (short-run validation)

## Part 3: Gates

- [ ] T11 — `mise run qa:e2e-regression` Δ=0.000% (tri-county hash
      unchanged)
- [ ] T12 — `mise run check` green (or targeted unit tests)
- [ ] T13 — Final commit + update ai-docs/state.yaml
