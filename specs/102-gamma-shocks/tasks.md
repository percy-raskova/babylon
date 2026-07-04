# Tasks — spec-102 Gamma Hydration + Scheduled Bloc Shocks (dependency-ordered)

Legend: [x] done · [ ] todo. Each numbered task = one commit unit.

- [x] **T1 — Speckit artifacts.** spec.md, plan.md, tasks.md, research.md.
  Commit: `docs(spec-102): specify + plan + tasks + research (gamma hydration + shocks)`.
- [x] **T0 — STEP 0 fail-loud guard.** `_assert_county_resolution_or_raise` in
  `runner.py`, wired into `_query_terminal_aggregates` +
  `_county_terminal_snapshot`; unit tests (6). Commit:
  `fix(headless-runner): fail loud on hex-rows-exist-but-zero-counties-resolved (spec-102 STEP 0)`
  (`6b7a1fd4`).
- [ ] **T2 — RED: gamma hydration adapter.**
  `tests/unit/economics/melt/test_gamma_hydration.py` —
  `SQLiteGammaHydrationSource.get_alpha`/`get_gamma_import` don't exist yet
  (or return wrong values). Observe RED.
- [ ] **T3 — GREEN: gamma hydration adapter.**
  `src/babylon/economics/melt/gamma_hydration.py` —
  `GammaHydrationSource` Protocol + `SQLiteGammaHydrationSource`
  (SQLAlchemy, `melt/adapters.py` pattern): `get_alpha(year)`,
  `get_gamma_import(year, scale_type="Intensive")`, both `-> float | None`.
  Commit: `feat(spec-102): SQLite gamma-hydration adapter (alpha + gamma_import per year)`.
- [ ] **T4 — RED: basket_visibility hydration wiring.**
  `tests/unit/economics/melt/test_basket_visibility.py` new tests —
  hydrated year → `estimated=False`, real value; unhydratable year →
  `estimated=True` (MVP). Observe RED (constructor doesn't accept
  `hydration_source` yet).
- [ ] **T5 — GREEN: basket_visibility hydration wiring.**
  `DefaultBasketVisibilityCalculator.__init__(hydration_source=None)`;
  `get_gamma_basket` hydrates when alpha/gamma_import not explicit and a
  source is injected. All 28 pre-existing tests stay green unmodified.
  Commit: `feat(spec-102): kill basket_visibility MVP seam — hydrate alpha/gamma_import per year`.
- [ ] **T6 — Factory wiring.** `economics/factory.py`:
  `create_economics_services()` constructs `SQLiteGammaHydrationSource` +
  wires into `DefaultBasketVisibilityCalculator`; extend
  `tests/unit/economics/test_factory.py`. Commit:
  `feat(spec-102): wire gamma-hydration source into create_economics_services`.
- [ ] **T7 — RED: shock schedule model.**
  `tests/unit/engine/headless_runner/test_shock_schedule.py` —
  `ScheduledBlocShock` + timeline-build helper don't exist yet. Observe RED.
- [ ] **T8 — GREEN: shock schedule model + timeline.**
  `headless_runner/models.py`: `ScheduledBlocShock` frozen model,
  `SimulationRunConfig.shock_schedule: tuple[ScheduledBlocShock, ...] = ()`;
  `runner.py`: `_build_shock_timeline`, `_apply_due_shocks` (pure,
  deterministic, sorted). Commit:
  `feat(spec-102): scheduled bloc shocks — deterministic exogenous phi multiplier`.
- [x] **T9 — Wire into tick loop.** Thread effective (shocked)
  `external_nodes_phi` through `_tick_loop`/`_advance_tick`, recomputed each
  tick from base map + active multiplier state. Default empty schedule ⇒
  behavior-identical to spec-101 (base map, no shocks). Commit:
  `feat(spec-102): apply scheduled shocks to per-tick external_nodes_phi`.
- [x] **T10 — RED→GREEN: determinism integration test.**
  `tests/integration/engine/headless_runner/test_shock_determinism.py` — same
  shock config run twice (different session ids) → byte-identical hex state
  (`v_hex_state_asof`) + `DRAIN_EDGE` magnitudes. **Course-corrected during
  implementation** (D5): a direct `tick_commit.determinism_hash` diff was
  attempted first and found, empirically, to ALWAYS diverge across sessions
  (the hash embeds `session_id` by construction) — even for the unmodified
  spec-101 baseline with no shock schedule at all. Re-designed to compare
  raw persisted values instead (byte-identical, confirmed GREEN). Commit:
  `test(spec-102): shock-schedule determinism (hex state + DRAIN_EDGE reproduce byte-identically)`.
- [x] **T11 — RED→GREEN: shock bends the Φ trajectory.**
  `tests/integration/engine/headless_runner/test_shock_bends_phi.py` — a
  bloc's `external_nodes_phi` / per-tick `DRAIN_EDGE` sum steps at the
  scheduled tick by the configured multiplier; unaffected before. Commit:
  `test(spec-102): shock scenario bends bloc Φ trajectory at scheduled tick`.
- [ ] **T12 — Verify loop.** `mise run check` → full unit suite → integration
  tests (T10, T11) → `mise run qa:e2e-regression` (expected green against the
  EXISTING baseline per D1 — no regen).
- [ ] **T13 — Proof + close-out.** Write `proof.md` (D1 baseline-neutrality
  empirical confirmation via qa:e2e-regression; D5 determinism-gate scope
  disclosure). Update `project/09-program-full-game.md` spec-102 status,
  `ai-docs/state.yaml`. Commit:
  `docs(spec-102): proof + close-out (baseline-neutral gamma hydration + shock determinism)`.
- [ ] **T14 — Confirm canonical baseline untouched.** Per D1, no re-baseline
  is required. Confirm `mise run sim:status` shows no conflicting 5433
  activity, and that `tests/baselines/michigan-e2e.json` (spec-101's
  committed session `a8202ed0`) remains the checked-in canonical baseline —
  no new canonical run is launched by spec-102.
