# Tasks — spec-101 Trade Activation (dependency-ordered)

Legend: [x] done · [ ] todo. Each numbered task = one commit unit.

- [ ] **T1 — Speckit artifacts.** spec.md, plan.md, tasks.md, research.md.
  Commit: `docs(spec-101): specify + plan + tasks + research (trade activation)`.
- [ ] **T2 — Pre-change baseline confirm.** `mise run qa:e2e-regression` green on
  HEAD (no commit; env prep incl. `immutable_reference_tiger_county` populate).
- [ ] **T3 — RED integration test.** `tests/integration/test_trade_circuit.py`
  (`@pytest.mark.red_phase`, gated on PG+SQLite like `test_bridge_income_circuit`):
  run ~3-tick tri-county bridged harness; assert per-tick DRAIN_EDGE rows for each
  Φ>0 bloc + `Σ DRAIN == Φ_week` per bloc. Observe RED (no rows). Commit:
  `test(spec-101): red trade-circuit integration (DRAIN_EDGE + conservation)`.
- [ ] **T4 — Exposure loader.** `economics/county_exposure.py` +
  `tests/unit/economics/test_county_exposure.py` (bloc-invariant read, scope
  renorm→1.0, empty→raise, sorted determinism). Commit:
  `feat(spec-101): county-exposure map loader (bloc-invariant, scope-renormalised)`.
- [ ] **T5 — Φ attribution + bilateral trade value.** `postgres_initialization.py`
  `_NODE_TO_BLOC` + `_attribute_national_phi_and_trade` + `_bootstrap_external_nodes`
  wiring; `tests/unit/persistence/test_phi_attribution.py` (crosswalk injective,
  shares sum 1.0, Φ=0 for unmapped nodes, trade value USD). Commit:
  `feat(spec-101): attribute national Φ + bilateral trade to blocs (trade-share crosswalk)`.
- [ ] **T6 — Conservation evaluator.** `conservation_audit.py`
  `phi_week_conservation_evaluator` (relative residual) + unit test. Commit:
  `feat(spec-101): conservation invariant Σ DRAIN_EDGE ≡ Φ_week per bloc`.
- [ ] **T7 — Wire context + register evaluator.** `runner.py` (exposure map +
  external_nodes_phi at setup; register evaluator; thread 4 keys through
  `_tick_loop`→`_advance_tick`→`TickContext`) + `bridge.py` (pass context to
  auditor). Flip T3 GREEN; drop `red_phase`. Commit:
  `feat(spec-101): wire TickContext keys — Φ distribution live every tick`.
- [ ] **T8 — Verify loop.** `mise run check` → `test_bridge_income_circuit.py` →
  `test_trade_circuit.py` → `qa:e2e-regression`.
- [ ] **T9 — Proof + re-baseline.** Write proof (in spec dir); regenerate
  `tests/baselines/detroit-tri-county-5t.json`; commit proof + baseline together.
  Commit: `test(spec-101): re-baseline 5-tick + written proof (boundary flows populate)`.
  **Review correction (spec-101 review, cheap minor)**: the historical commit
  for this task used `--no-verify`, citing 635d234e ("chore(spec-069): commit
  canonical headless-runner sim-run artifacts") as precedent. That precedent
  doesn't actually apply: 635d234e bypassed the `check-added-large-files`
  500KB gate for `summary.json` files OUTSIDE `tests/baselines/`, but
  `.pre-commit-config.yaml`'s `check-added-large-files` hook already
  `exclude`s `^tests/baselines/.*\.json$` — baseline JSON commits never
  needed `--no-verify` on size grounds. Left uncorrected in the historical
  commit message (git history is immutable); noted here so the justification
  isn't repeated for future baseline commits.
- [ ] **T10 — Close-out.** Update `project/01-state-of-the-world.md`, `09 §2`
  spec-101 status, `ai-docs/state.yaml`; add ADR (Φ attribution model). Commit:
  `docs(spec-101): close-out + ADR (Φ attribution + trade activation)`.
- [ ] **T11 — Canonical re-baseline.** `mise run sim:e2e-bg`; confirm alive via
  `mise run sim:status`; RETURN PARTIAL with run in flight (orchestrator verifies
  83/83 + archives).
