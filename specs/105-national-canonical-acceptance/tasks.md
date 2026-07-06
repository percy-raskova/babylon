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

- [ ] T05 — Run 5-tick national validation
      (`--scope=national --ticks 5 --liveness-gate`)
- [ ] T06 — Verify liveness: `counties_alive > 0`,
      `counties_with_population > 0`, `total_v > 0`, STEP-0 guard
      did not fire
- [ ] T07 — Verify `qa:storage-budget` against national run footprint
- [ ] T08 — Verify Observatory renders the national session
- [ ] T09 — Commit national baseline bundle (short-run validation)

## Part 3: Gates

- [ ] T10 — `mise run qa:e2e-regression` Δ=0.000% (tri-county hash
      unchanged)
- [ ] T11 — `mise run check` green (or targeted unit tests)
- [ ] T12 — Final commit + update ai-docs/state.yaml
