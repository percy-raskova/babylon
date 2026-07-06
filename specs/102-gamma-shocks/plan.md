# Plan — spec-102 Gamma Hydration + Scheduled Bloc Shocks

## Approach (data flow)

```
SLICE A — Gamma hydration
economics/factory.py::create_economics_services()
  └─ SQLiteGammaHydrationSource(session_factory)          (new adapter, SQLAlchemy)
       ├─ get_alpha(year)         -> Σimports_usd_millions / Σtotal_final_uses_millions
       └─ get_gamma_import(year)  -> 1 / fact_hickel_erdi_annual.erdi (scale_type=Intensive)
  └─ DefaultBasketVisibilityCalculator(hydration_source=...)   (was: registry.get(), parameterless)
       get_gamma_basket(year, alpha=None, gamma_import=None):
         if alpha/gamma_import explicitly passed -> unchanged (existing formula path)
         elif hydration_source is not None:
             hydrated = hydration_source.hydrate(year)
             if hydrated is not None -> compute formula, estimated=False
             else -> MVP fallback, estimated=True   (unchanged behavior)
         else -> MVP fallback, estimated=True         (unchanged behavior — no source injected)

  NOT reachable from headless_runner today (D1) — ServiceContainer.create(defines=defines)
  never sets melt_calculator/basket_calculator, so TickDynamicsSystem.step()
  early-returns every tick regardless of this spec. Verified baseline-neutral.

SLICE B — Scheduled bloc shocks
headless_runner/models.py::SimulationRunConfig
  └─ shock_schedule: tuple[ScheduledBlocShock, ...] = ()      (new field, empty default)

headless_runner/runner.py::run() (setup, once)
  └─ base_external_nodes_phi = _query_external_nodes_phi(...)      (unchanged, spec-101)
  └─ shock_timeline = _build_shock_timeline(config.shock_schedule)  (sorted by tick)
  └─ active_multipliers: dict[str, float] = {}                     (mutable closure state)

_tick_loop (every tick)
  └─ _apply_due_shocks(tick, shock_timeline, active_multipliers)   (pure, deterministic)
  └─ effective_phi = {node: base_phi[node] * active_multipliers.get(node, 1.0)
                      for node in base_phi}
  └─ _advance_tick(..., external_nodes_phi=effective_phi)           (was: static base_phi)
```

## File changes (Lane E owns `src/babylon/**`, `tests/`, baselines)

| File | Change |
|------|--------|
| `src/babylon/engine/headless_runner/runner.py` | STEP 0 guard (done, commit `6b7a1fd4`); SLICE B: shock-timeline build + per-tick effective-phi computation threaded into `_tick_loop`/`_advance_tick`. |
| `src/babylon/economics/melt/gamma_hydration.py` (new) | `GammaHydrationSource` Protocol + `SQLiteGammaHydrationSource` (SQLAlchemy adapter, matches `melt/adapters.py` pattern): `get_alpha(year)`, `get_gamma_import(year, scale_type="Intensive")`, both `-> float \| None`. |
| `src/babylon/economics/melt/basket_visibility.py` | `DefaultBasketVisibilityCalculator.__init__(self, hydration_source: GammaHydrationSource \| None = None)`; `get_gamma_basket` hydrates when alpha/gamma_import not explicitly passed and a source is injected. |
| `src/babylon/economics/factory.py` | `create_economics_services()` constructs `SQLiteGammaHydrationSource(session_factory)` + wires it into `DefaultBasketVisibilityCalculator`, replacing the parameterless registry pull. |
| `src/babylon/engine/headless_runner/models.py` | `ScheduledBlocShock` frozen model; `SimulationRunConfig.shock_schedule` field (default `()`). |
| `tests/unit/economics/melt/test_gamma_hydration.py` (new) | Adapter unit tests: hydrated year, out-of-coverage year → `None`, scale_type selection. |
| `tests/unit/economics/melt/test_basket_visibility.py` | New tests: hydration-source-injected path returns `estimated=False` with real value; falls back to MVP when hydration source returns `None`; all EXISTING tests (parameterless construction) stay green unmodified. |
| `tests/unit/economics/test_factory.py` | Extend: `basket_calculator` is `DefaultBasketVisibilityCalculator` with a non-`None` `_hydration_source` after `create_economics_services()`. |
| `tests/unit/engine/headless_runner/test_shock_schedule.py` (new) | `ScheduledBlocShock` validation; shock-timeline build (sorted, level-set semantics). |
| `tests/integration/engine/headless_runner/test_shock_determinism.py` (new) | RED→GREEN: same shock config run twice (different session ids) → byte-identical hex state (`v_hex_state_asof`) + `DRAIN_EDGE` magnitudes (D5 — corrected from an original `tick_commit.determinism_hash` diff plan after empirical testing found both on-disk hash tables embed `session_id`). |
| `tests/integration/engine/headless_runner/test_shock_bends_phi.py` (new) | Shock scenario: bloc's `external_nodes_phi` / `DRAIN_EDGE` sum step-changes at the scheduled tick by the configured multiplier; ticks before the schedule are unaffected. |

## Constitution v2.7.0 gate checklist (per §4)

- **III.1 no-magic-numbers** — PASS. Kills the exact seam
  (`MVP_ALPHA`/`MVP_GAMMA_IMPORT` as the *only* code path) by hydrating both
  coefficients from grounded reference tables per year; MVP constants remain
  only as the documented, disclosed degrade path for years outside data
  coverage (unchanged contract).
- **III.7 determinism / frozen models** — PASS. `ScheduledBlocShock` is a
  frozen Pydantic model; shock application is a pure dict transform over
  sorted bloc keys, no RNG, no wall-clock. D5 discloses (empirically
  verified) that neither on-disk "determinism hash" table is directly
  comparable across two session ids — the shipped test compares raw
  persisted hex state + DRAIN_EDGE values instead, which is what a hash
  chain would be a proxy for.
- **III.8 data-grounding** — PASS w/ DISCLOSURE. α from BEA final-demand +
  bilateral trade (spec-068 + spec-100); γ_import from Hickel ERDI
  (spec-057's existing ingestion). Data-coverage: Hickel 1980–2017 (37 rows incl. 2017 erdi=7.20)
  disclosed in spec.md FR-102-2, not silently ignored or fabricated past.
  Hickel's own `alpha` column is explicitly NOT reused for α (D2) to avoid a
  false-cognate fabrication.
- **III.10 earn-its-keep** — PASS. Hydration replaces a hardcoded constant
  with a real per-year computation; shocks are a real scenario-authoring
  primitive (used by the Observatory-facing shock scenario), not decorative.
- **R-AMEND** — PASS. Shocks are declarative exogenous schedule data, never
  bloc-initiated action; blocs stay Layer-0 register machinery.
- **R-PROOF** — one shared 101+102 proof window. D1's two-part
  verification (consumption path + wiring path) is the written proof that no
  re-baseline is required; see `proof.md`.

## Task-execution order

1. Speckit docs (this file + spec.md + tasks.md + research.md) — commit.
2. STEP 0 fail-loud guard — **done**, commit `6b7a1fd4` (ships first per the
   task brief, protects the re-baseline path even though D1 concludes no
   re-baseline is needed).
3. SLICE A gamma hydration, TDD: adapter unit tests (RED) → adapter
   implementation (GREEN) → basket_visibility hydration-source wiring, TDD →
   factory.py wiring → `mise run check`.
4. SLICE B scheduled shocks, TDD: `ScheduledBlocShock` model + timeline-build
   unit tests (RED) → implementation (GREEN) → runner wiring → determinism
   integration test (RED→GREEN) → "bends the Φ trajectory" integration test
   (RED→GREEN).
5. Verify: `mise run check`; `mise run qa:e2e-regression` against the
   existing baseline (D1 — expected green, no regen).
6. Proof + close-out: write `proof.md` (D1 empirical confirmation +
   determinism-gate disclosure), update `ai-docs/state.yaml` /
   `project/09-program-full-game.md` spec-102 status.
