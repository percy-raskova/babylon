# Research — spec-102

## R1 — Hickel ERDI data coverage (direct CSV inspection)

`/media/user/data/babylon-data/babylon_hickel_final.csv` (source for
`fact_hickel_erdi_annual`, ingested by `tools/ingest/hickel_erdi.py`):

```
scale_type                    row count   year range
Extensive                     20          1960–1979
Intensive                     37          1980–2016
Intensive_China_Inflection    1           2005 (variant, not a series)
```

2010–2017 `Intensive` rows (year, erdi, alpha, scale_type):

```
2010 7.60 0.894 Intensive
2011 7.73 0.912 Intensive
2012 7.86 0.930 Intensive
2013 7.99 0.947 Intensive
2014 8.12 0.965 Intensive
2015 8.25 0.982 Intensive
2016 8.38 1.000 Intensive
2017 7.20 0.840 Intensive
```

**Finding**: no row exists for 2018+. The canonical `michigan-canada` run
(`start_year=2010`, 520 weekly ticks ≈ 10 calendar years) spans into years
without Hickel coverage. `alpha` in this table climbs to *exactly* 1.000 in
2016 — implausible as "import share of US consumption" (imports have never
approached 100% of US consumption) — confirming this is a distinct
Hickel-methodology parameter, not reusable as spec-102's α (D2 in spec.md).

## R2 — γ_import dimensional analysis

`basket_visibility.py`'s formula `γ_basket = 1/(α/γ_import + (1-α))` requires
`γ_import ∈ (0, 1]` (validated by `GammaBasket.gamma_import: Field(gt=0, le=1)`
in the sibling `economics/gamma/types.py`). ERDI (market/PPP exchange-rate
ratio) is `>1` for undervalued-currency partners — the 2010–2017 values above
range 7.2–8.38, far outside `(0,1]`. The sibling module
`economics/gamma/gamma_import.py` documents the correct relationship:
`gamma_import = Σ import_share[origin] × 1/ERDI[origin]` — i.e. γ_import is a
weighted average of the *inverse* of ERDI. `1/7.86 ≈ 0.127` (2012) is in
range and in the right ballpark relative to `MVP_GAMMA_IMPORT=0.35`.

## R3 — `services.basket_calculator` / `services.melt_calculator` wiring audit

Grepped every construction site of `ServiceContainer`:

- `src/babylon/engine/headless_runner/runner.py:692` —
  `services = ServiceContainer.create(defines=defines)`. No
  `melt_calculator`/`basket_calculator` kwarg. This is the **only**
  `ServiceContainer` construction in the headless-runner module, used by
  every `--scope` (canonical `michigan-canada`, `detroit-tri-county` /
  `qa:e2e-regression`, etc.) — confirmed via `rg -n "ServiceContainer"
  src/babylon/engine/headless_runner/`.
- `src/babylon/economics/tick/system/__init__.py:132` —
  `if services.melt_calculator is None: ... return` — the very first line of
  `TickDynamicsSystem.step()`. Since `melt_calculator` is always `None` from
  the runner's construction, this is an **unconditional early return every
  tick** in every headless-runner execution.
- The only place `create_economics_services()` (which *does* wire
  `basket_calculator` via the registry, and after this spec, via
  `SQLiteGammaHydrationSource`) is called is
  `src/babylon/engine/simulation/_legacy.py:272`
  (`Simulation.from_sqlite()`) — a different, `_legacy`-suffixed module the
  headless runner does not import or call.

**Conclusion**: gamma hydration cannot affect the headless-runner canonical
baseline because the consuming system never executes in that runner. This is
independent of (and stronger than) the hex-state-isolation argument in
spec.md D1 §1 — even if `TickDynamicsSystem` wrote to hex state, it would
still never run in the canonical path today.

## R4 — `tick_commit` determinism-hash inputs

`src/babylon/persistence/conservation_audit.py::compute_determinism_hash`:
`sha256(json({"tick", "rng_seed", "hex_state": sorted(hex_rows, key=h3_index),
"actions"}))`. No reference to `external_nodes_phi`, `boundary_flow_register`,
or `conservation_audit_log`. Confirmed by direct source read, not inferred —
this bounds what the shock-determinism gate (spec.md D5) can and cannot prove.

## R5 — Existing test surface that must stay green

`tests/unit/economics/melt/test_basket_visibility.py` (28 tests) exercises
`DefaultBasketVisibilityCalculator()` constructed with **zero** arguments
throughout (parameterless), including explicit MVP-mode assertions for
`get_gamma_basket(year)` with no `alpha`/`gamma_import`. The
`hydration_source` constructor parameter must default to `None` and every
existing call path must be byte-behavior-identical when it is `None` (no
hydration attempted, straight MVP fallback) — this is the load-bearing
backward-compatibility constraint for SLICE A's design.
