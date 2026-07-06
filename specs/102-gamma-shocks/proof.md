# spec-102 R-PROOF — Written proof (baseline-neutrality + shock determinism)

**Proof window**: shared 101+102 (R-PROOF, one open window, opened by spec-101).
Closed by spec-102.

## Part 1 — Gamma hydration is baseline-neutral (no re-baseline required)

### WHAT changed

`src/babylon/economics/melt/basket_visibility.py`'s `DefaultBasketVisibilityCalculator`
now accepts an optional `hydration_source` (spec-102's `SQLiteGammaHydrationSource`,
`src/babylon/economics/melt/gamma_hydration.py`). When injected and the caller
doesn't pass explicit `alpha`/`gamma_import`, it hydrates real per-year values
from `fact_bilateral_trade_annual` + `fact_bea_final_demand_annual` (α) and
`fact_hickel_erdi_annual` (γ_import = 1/ERDI) instead of always returning the
hardcoded MVP tuple `(0.68, True)`. `economics/factory.py`'s
`create_economics_services()` wires this hydration source in.

### WHY it does not require a canonical re-baseline

Two independent findings, both verified directly against the source (not
inferred):

1. **Consumption-path isolation.** `TickDynamicsSystem` (position 4/26 in
   `_DEFAULT_SYSTEMS`) is the *only* caller of `get_gamma_basket`. Its output
   (`tau_effective`, `phi_hour`, county-level crisis/bifurcation state) is
   written *only* to territory-node graph attributes (`tick_`-prefixed) and a
   separate `persist_graph_metadata()` Postgres sink — never into
   `dynamic_hex_state`, the sole source (via `v_hex_state_asof` →
   `view_runtime_trace_emission`) of the canonical baseline's gated
   `terminal_state` fields (`total_v`, `total_c`, `total_s`, `total_k`,
   `counties_alive`).

2. **Wiring-path isolation (decisive).** The headless runner
   (`runner.py:692`, `services = ServiceContainer.create(defines=defines)`)
   never passes `melt_calculator` or `basket_calculator` — both are `None`
   for **every** headless-runner scope, canonical `michigan-canada` included.
   `TickDynamicsSystem.step()`'s first line
   (`if services.melt_calculator is None: ... return`) makes the **entire
   system a no-op** in every headless-runner execution today.
   `get_gamma_basket` — hydrated or not — is never even called. This is the
   same class of gap the task brief itself flagged ("like MELT/n_calculator").
   `create_economics_services()` (where the hydration source is wired) is
   reachable only via the separate `Simulation.from_sqlite()` path in
   `engine/simulation/_legacy.py`, which the headless runner does not use.

Given (1) and (2) — either one alone would suffice, but both hold —
`tests/baselines/michigan-e2e.json` (spec-101's committed session
`a8202ed0` at `8210db17`) and `tests/baselines/detroit-tri-county-5t.json`
remain valid, unmodified baselines. **No re-baseline was generated or
committed for spec-102.**

### Verification

- 34 unit tests in `tests/unit/economics/melt/test_basket_visibility.py`
  (28 pre-existing + 6 new) — all green, including the byte-identical
  parameterless-construction path (`test_no_hydration_source_is_byte_identical_to_pre_spec_102`).
  7 unit tests in `test_gamma_hydration.py`. `test_factory.py` extended
  (basket_calculator now data-adapter-injected) — green.
- `mise run qa:e2e-regression` run against the **existing**
  `detroit-tri-county-5t.json` baseline post-implementation (2026-07-04):
  **PASS** — `counties_alive == 3`, `population liveness: 3/3`,
  `total_v: actual=1.497e+09, expected=1.497e+09, Δ=0.000%` (tolerance
  ±1.0%), no critical conservation violations. Empirically confirms D1:
  gamma hydration required zero baseline changes.

## Part 2 — Scheduled bloc shocks: determinism + observable effect

### WHAT shipped

`ScheduledBlocShock` (frozen Pydantic model: `tick`, `bloc`, `phi_multiplier`)
+ `SimulationRunConfig.shock_schedule` (default `()`). The tick loop
(`_tick_loop` in `runner.py`) applies due shocks each tick via
`_apply_due_shocks` (level-set semantics — a bloc's multiplier persists once
set) and recomputes the *effective* `external_nodes_phi` via
`_effective_external_nodes_phi` before calling `_advance_tick`. With an empty
schedule this is a value-identical no-op, so canonical scenarios are
unaffected by this feature's mere existence.

### Determinism — course-corrected during implementation (honest disclosure)

The original plan was to diff `tick_commit.determinism_hash` between two
runs of the identical shock config. Implementing the integration test
surfaced, empirically, that this does not work as assumed:

- `tick_commit.determinism_hash` is `sha256(f"{session_id}:{tick}:{random_seed}")`
  (`_tick_loop`) — it embeds `session_id` directly, so it can *never* match
  across two independent runs, by construction, regardless of determinism.
- `conservation_audit_log.determinism_hash` is computed by
  `compute_determinism_hash(tick, rng_seed, hex_rows, action_list)`, which
  looks state-pure on its signature — but the `hex_rows` it hashes are
  `DynamicHexState`-shaped Pydantic models that themselves carry a
  `session_id` field, and the function hashes each row's full
  `model_dump(mode="json")`. `session_id` leaks into this "state hash" too.
  **Verified by running the unmodified spec-101 baseline (empty
  `shock_schedule`) twice**: its `conservation_audit_log.determinism_hash`
  sequence *also* diverges between the two runs — proving this is a
  pre-existing latent gap in the determinism-hash instrumentation, unrelated
  to spec-102's scheduling code (out of scope to remediate here — flagged,
  not fixed, matching the STEP-0 guard's deferred session-scoping half).

Given that, `tests/integration/engine/headless_runner/test_shock_determinism.py`
instead compares the **actual persisted values** between two runs of the
identical shock config (`detroit-tri-county`, `start_year=2010`, 6 ticks,
`china` shocked ×2.5 at tick 2):

- hex-level `(tick, h3_index, c, v, s, k)` from `v_hex_state_asof` —
  **byte-identical** across both runs (verified GREEN).
- per-bloc `DRAIN_EDGE` magnitude sums per tick from `boundary_flow_register`
  — **byte-identical within Postgres `SUM()`-order float noise (rel 1e-8)**
  across both runs (verified GREEN).

This is exactly what a hash chain would have been a *proxy* for, had the
session-id leak not existed — it directly demonstrates the new
shock-scheduling code introduces no accidental nondeterminism (unsorted
iteration, RNG, wall-clock reads).

### Observable effect — the shock visibly bends the Φ trajectory

`tests/integration/engine/headless_runner/test_shock_bends_phi.py` (`china`
shocked ×2.5 at tick 3, `detroit-tri-county`, 6 ticks): verified GREEN —

- pre-shock ticks (1, 2) carry `china`'s constant unshocked weekly DRAIN_EDGE
  sum (within float-summation noise).
- at and after the scheduled tick (3, 4, 5), `china`'s DRAIN_EDGE sum equals
  the pre-shock baseline × 2.5, within `rel=1e-6`.
- every *other* bloc's DRAIN_EDGE sum is unaffected across all ticks (within
  float noise) — the shock does not leak outside its declared bloc.

## Verification chain

- Unit: `test_gamma_hydration.py` (7), `test_basket_visibility.py` (34, 6
  new), `test_factory.py` (6, 1 new), `test_shock_schedule.py` (16),
  `test_terminal_aggregate_guard.py` (6, STEP 0) — all green.
- Integration (Postgres-gated, `@pytest.mark.integration`):
  `test_shock_determinism.py` (2 — hex-state + DRAIN_EDGE reproduction),
  `test_shock_bends_phi.py` (3 — pre-shock baseline, post-shock scaling,
  unshocked-bloc isolation) — all green.
- `mise run check` (lint + format + typecheck + full unit suite, 2026-07-04):
  **GREEN** — 8995 passed, 17 skipped, 4 xfailed (all pre-existing, unrelated
  to spec-102), 0 failed, in 515.55s.
- `mise run qa:e2e-regression` (2026-07-04): **GREEN** against the existing,
  unmodified `detroit-tri-county-5t.json` baseline — `counties_alive == 3`,
  `population liveness: 3/3`, `total_v Δ=0.000%`, no critical conservation
  violations. No re-baseline generated or committed.
