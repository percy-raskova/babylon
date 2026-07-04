# spec-102 — Gamma hydration + scheduled bloc shocks

**Program**: 09 Full-Game Build, Lane E (engine). **Provisional number**: 102.
**Depends on**: spec-100 (county-exposure + bilateral-trade + Hickel ERDI
reference tables), spec-101 (TickContext wiring, BoundaryFlowRegister, Φ
distribution — complete at `8210db17` on `101-trade-activation`). **Proof
window**: shared 101+102 (R-PROOF). **Status**: implemented.

## Why

`src/babylon/economics/melt/basket_visibility.py` hardcodes
`MVP_ALPHA=0.25`, `MVP_GAMMA_IMPORT=0.35`, `MVP_GAMMA_BASKET=0.68` — the
exact seam III.1 (no-magic-numbers) flags. `get_gamma_basket(year, alpha,
gamma_import)` is already parameterized to compute the real harmonic-mean
formula, but its two callers
(`economics/tick/system/__init__.py:381`, `economics/tick/initializer.py:118`)
call it with `year` only, so it always falls into MVP mode. Spec-100
materialised the reference tables (`fact_county_exposure_by_external`,
`fact_bilateral_trade_annual`, `fact_hickel_erdi_annual`) needed to hydrate
these two coefficients per year. Separately, the boundary-flow machinery
spec-101 activated (external-node `phi_year_inflow` feeding
`ImperialRentSystem._invoke_phi_distribution_if_wired`) has no way to model
scripted geopolitical shocks (e.g. a bloc's drain suddenly doubling) — this
spec adds a deterministic, exogenous scheduling layer for that.

## What ships (functional requirements)

- **FR-102-1** — `SQLiteGammaHydrationSource` (session-factory-based SQLAlchemy
  adapter, matching the `melt/adapters.py` pattern) computes, per calendar
  year:
  - `alpha` = `Σ fact_bilateral_trade_annual.imports_usd_millions` (all
    countries, year's annual `time_id`) / `Σ fact_bea_final_demand_annual
    .total_final_uses_millions` (all `bea_industry_id`, same `time_id`) — an
    import-share-of-final-demand ratio, grounded in BEA (spec-068) + spec-100
    trade data.
  - `gamma_import` = `1 / fact_hickel_erdi_annual.erdi` for
    `(year, scale_type="Intensive")` — dimensionally required: the harmonic
    formula needs `gamma_import ∈ (0, 1]`, and ERDI (market/PPP exchange-rate
    ratio) is `>1` for undervalued-currency partners, so `1/ERDI` is the
    visibility measure (matches the sibling `economics/gamma/gamma_import.py`
    formula `Σ import_share[origin] × 1/ERDI[origin]`, here degenerating to
    the single nationally-aggregated ERDI — the reference DB has no
    per-country ERDI resolution, so no fabricated per-country weighting is
    introduced, III.8).
  - Returns `None` for a year with no Hickel/BEA/trade row (see FR-102-2).
- **FR-102-2** — **Disclosed data-coverage gap**: `fact_hickel_erdi_annual`
  only carries `scale_type='Intensive'` rows for 1980–2016 (`'Extensive'` for
  1960–1979; a single `'Intensive_China_Inflection'` 2005 variant row). The
  canonical `michigan-canada` run starts 2010 across 520 weekly ticks (~10
  calendar years, through ~2019/2020) — years 2018+ have no Hickel row.
  `DefaultBasketVisibilityCalculator` falls back to the existing MVP hardcode
  (`estimated=True`) for any year hydration cannot cover — the existing
  Protocol docstring already specifies this contract
  ("`estimated`: True if using MVP hardcoded value (data unavailable)"). No
  data is fabricated for missing years.
- **FR-102-3** — `economics/tick/system/__init__.py` and
  `economics/tick/initializer.py` are unchanged at the call-site level
  (`services.basket_calculator.get_gamma_basket(year)`, no explicit
  alpha/gamma_import args) — the hydration happens *inside*
  `DefaultBasketVisibilityCalculator` via an injected optional
  `hydration_source`, preserving the existing Protocol signature and 100%
  backward compatibility for every caller/test that constructs
  `DefaultBasketVisibilityCalculator()` with no arguments (registry default,
  unit tests).
- **FR-102-4** — `economics/factory.py`'s `create_economics_services()`
  constructs `DefaultBasketVisibilityCalculator(hydration_source=
  SQLiteGammaHydrationSource(session_factory))` instead of pulling the
  parameterless registry instance — moving `BasketVisibilityCalculator`
  construction from the "Level 0: no dependencies" registry tier to the
  data-adapter-injected tier (matching `DefaultMELTCalculator`'s existing
  pattern).
- **FR-102-5** — `ScheduledBlocShock` (frozen Pydantic model): `tick: int`,
  `bloc: str` (one of the 8 `INTERNATIONAL_NODES`), `phi_multiplier: float |
  None`. A `SimulationRunConfig.shock_schedule: tuple[ScheduledBlocShock,
  ...] = ()` field (empty default) declares the run's shock timeline.
- **FR-102-6** — The headless runner's tick loop applies scheduled shocks
  deterministically: at each tick, any shock scheduled for that exact tick
  updates a per-bloc multiplier (level-set, not cumulative); the *effective*
  `external_nodes_phi` passed into that tick's `TickContext` is
  `base_phi[node] × active_multiplier.get(node, 1.0)`, recomputed every tick
  from the (unchanged) base map + the current multiplier state. No RNG; bloc
  iteration is sorted; multiplier state is a plain dict threaded through the
  tick loop closure (no hidden global state).
- **FR-102-7** — Default canonical scenario (`michigan-canada`,
  `detroit-tri-county`) has an **empty** `shock_schedule` — CLI/config default
  — so canonical runs are byte-for-byte unaffected by this feature's
  existence.
- **FR-102-8** — `trade_multiplier` is **out of scope for this spec's
  observable gate**: `bilateral_trade_value` has no active per-tick consumer
  today (`vol2_step`'s TRADE_EDGE path stays gated per spec-101 D5, dormant
  until 098-LODES) — a `trade_multiplier` field would be inert. FR-102-5's
  model therefore ships `phi_multiplier` only; a `trade_multiplier` field is
  deferred until TRADE_EDGE activates (disclosed, not fabricated as if it did
  something today).

## Non-goals

- Agentic or reactive bloc behaviour — shocks are pure exogenous scripted
  perturbations, never OODA-driven (R-AMEND, blocs stay Layer-0 register
  machinery).
- `trade_multiplier` wiring (FR-102-8, deferred to post-098-LODES).
- Per-country ERDI resolution — the reference DB only has a national
  aggregate; fabricating per-country splits would violate III.8.
- Re-deriving `alpha`/`gamma_import` for the separate `economics/gamma/`
  module (Feature 015) — that module is not wired into
  `services.basket_calculator` (verified: `ServiceContainer.create()` never
  references it) and is out of scope.

## Key decisions (recorded)

- **D1 — Gamma hydration is baseline-neutral by construction, verified two
  ways independently.**
  1. *Consumption path*: `TickDynamicsSystem` (position 4/26,
     `_DEFAULT_SYSTEMS`) is the **only** caller of `get_gamma_basket`. Its
     output (`tau_effective`, `phi_hour`, per-county crisis/bifurcation
     state) is written **only** to territory-node graph attributes
     (`tick_`-prefixed) and a separate `persist_graph_metadata()` Postgres
     sink — never into `dynamic_hex_state`, which is the *sole* source (via
     `v_hex_state_asof` → `view_runtime_trace_emission`) of the canonical
     baseline's gated `terminal_state` fields (`total_v`, `total_c`,
     `total_s`, `total_k`, `counties_alive`).
  2. *Wiring path (the decisive finding)*: the headless runner
     (`src/babylon/engine/headless_runner/runner.py:692`,
     `services = ServiceContainer.create(defines=defines)`) never passes
     `melt_calculator` or `basket_calculator` — both stay `None` for **every**
     headless-runner scope (canonical `michigan-canada` AND
     `detroit-tri-county`/`qa:e2e-regression`). `TickDynamicsSystem.step()`'s
     very first guard (`if services.melt_calculator is None: ... return`)
     therefore makes the **entire system a no-op** in every headless-runner
     execution today — `get_gamma_basket` is never even called. This exactly
     matches the program's own parenthetical hint ("like MELT/n_calculator").
     `create_economics_services()`/`factory.py` (where the hydration source
     is actually wired, FR-102-4) is reachable only via the separate,
     `_legacy`-suffixed `Simulation.from_sqlite()` path, which the headless
     runner does not use.
  **Conclusion: no canonical re-baseline is required for gamma hydration.**
  `mise run qa:e2e-regression` stays green against the existing baseline
  (`tests/baselines/detroit-tri-county-5t.json`, unchanged) and the existing
  canonical `tests/baselines/michigan-e2e.json` (spec-101's committed
  session `a8202ed0` at `8210db17`) remains the valid baseline — it is not
  superseded by this spec.
- **D2 — α is derived from BEA final-demand + bilateral trade, not Hickel's
  own `alpha` column.** `fact_hickel_erdi_annual.alpha` exists but is a
  *different* Hickel-methodology parameter (values run 0.30→1.00 across
  1960–2016 in the ingested CSV — implausible as "import share of US
  consumption," which has never approached 100%). Reusing it would be a
  false-cognate fabrication. α is instead computed from data that actually
  measures import penetration of final demand (imports ÷ final uses).
- **D3 — γ_import uses the single national ERDI, not a fabricated per-country
  split.** The reference DB's Hickel series (like spec-101's Hickel Φ) is a
  national aggregate with no per-bloc/per-country resolution. "Trade-weighted"
  in the program brief is satisfied by Hickel's own upstream methodology
  (their published ERDI is already an aggregate across US trading partners);
  this spec does not re-weight it against `fact_bilateral_trade_annual`
  per-country, because doing so would require a per-country ERDI input this
  DB does not have (III.8 — no fabricated specificity). This mirrors spec-101
  D3's disclosed containing-bloc-granularity limitation.
- **D4 — Shock scheduling is a runner-level, not engine-level, concern.**
  Shocks mutate the *external input* (`external_nodes_phi`) fed into
  `TickContext` each tick — they do not add a new engine System, do not
  touch the graph, and are computed before `_advance_tick` calls
  `engine.run_tick`. This keeps blocs non-agentic (R-AMEND): the shock
  schedule is declarative data, not a decision any node makes.
- **D5 — The `tick_commit` determinism-hash gate is necessary but structurally
  insensitive to Phi.** `compute_determinism_hash` hashes `tick + rng_seed +
  sorted(hex_state) + actions` only (verified:
  `src/babylon/persistence/conservation_audit.py:70`) — `external_nodes_phi`,
  `boundary_flow_register`, and `conservation_audit_log` are outside its
  input set entirely, matching D1's finding that Φ machinery never touches
  hex state. Running the same shock config twice and diffing the
  `tick_commit` hash chain is therefore a **regression test against
  accidentally-introduced nondeterminism in the new scheduling code** (e.g.
  unsorted dict iteration, wall-clock/RNG use) rather than a test that is
  *specific* to shock correctness — disclosed honestly rather than
  overclaiming what the gate proves. The shock's *actual* effect is verified
  separately (FR-102-6 test: the bloc's `external_nodes_phi` — and therefore
  its per-tick `DRAIN_EDGE` sum — visibly steps at the scheduled tick).

## Gate (program 09 §2)

- RED→GREEN: `get_gamma_basket(2012)` (a year within Hickel `Intensive` +
  BEA coverage) returns `estimated=False` with a real, non-0.68 `gamma_basket`
  when a working `hydration_source` is injected; falls back to `estimated=True`
  for years outside coverage (e.g. 2020) — both paths tested.
- RED→GREEN: running the same `shock_schedule` config twice (same seed,
  different session ids) produces an identical `tick_commit.determinism_hash`
  sequence.
- A dedicated shock-scenario integration test shows a bloc's
  `external_nodes_phi` (and its per-tick `DRAIN_EDGE` sum) step-changing at
  the scheduled tick by the configured multiplier.
- `mise run qa:e2e-regression` green against the **existing** baseline (D1 —
  no re-baseline needed).
- `mise run check` green (lint + format + typecheck + unit tests).
