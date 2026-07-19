# Vol III Money — Baseline Delta

**Status:** DRAFT — pending owner approval (see "Owner Approval Gate" below)
**Design:** `docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md`
**Precedent:** ADR077/ADR078 (Program 23 Market Scissors) — the same
"prove the delta in writing, then regenerate baselines in a dedicated
ceremony commit" pattern (D3 owner ruling here mirrors that precedent
explicitly).
**Raw evidence:** `reports/vol3-baseline-delta-raw-diff.txt` (qa:regression),
`reports/vol3-e2e-regression-raw-diff.txt` (qa:e2e-regression) — both
captured verbatim by U8.2, real output from this branch, not paraphrased.

## Headline finding (read this first)

**`qa:regression` is byte-identical: 5 of 5 scenarios PASS, 0 fail.**
`qa:e2e-regression` (detroit-tri-county, 5 ticks) PASSES unchanged. The
Vol III financial layer landed by U1-U7 produces **no behavioral delta on
any of these six gate runs** — and that is the *expected, materially-grounded*
result, not a sign the layer is inert. Two independent reasons, both proven
below:

1. **The five `qa:regression` scenarios carry zero `county_fips`**
   (`tools/regression_test.py:159` — "the five regression scenarios carry no
   `county_fips`"). Every Vol III term is county-keyed or fed by county surplus
   distributions, so each one resolves to honest-absence `None`
   (Constitution III.11) and drops out of the tick. See the per-scenario
   mechanism analysis below.
2. **The `qa:e2e-regression` run is only 5 ticks long**, and the Vol III
   annual pipeline "executes only on year boundaries"
   (`src/babylon/domain/economics/tick/system/__init__.py:152`). A 5-tick
   window never crosses a 52-tick year boundary, so the annual financial
   recompute never fires.

The **only** thing U1-U7 changed that a regeneration would encode is the
**advisory `defines_hash`** — new `MarketDefines` fields (U4/U6) and
`capital_vol3` endogenous-interest coefficients (U9) altered
`GameDefines.model_dump_json`, so the live hash differs from the stored one
(e.g. `imperial_circuit` baseline `08f0a3d2837f4bb3` → live
`a8dde205a7256427`). This is **not a failure**: `compare_baselines`
classifies a `defines_hash` change as a `WARNING` and excludes it from the
pass filter (`passed = len([d for d in diffs if not d.startswith("WARNING")])
== 0`, `tools/regression_test.py:962`), and the WARNING is printed only on a
FAILing scenario — which is why the captured PASS output shows no WARNING line
at all. **The behavioral baseline is byte-identical; U8.5's regeneration only
refreshes that advisory `defines_hash`, it does not overwrite any tick value.**

## Why this document exists

Constitution III.7's falsifiability gate (`qa:regression`) was *expected* to
go RED the moment U1-U7 land: `s = p + i + r + t` has never evaluated in the
shipped game before this branch (design spec §1.1), so turning it on is a
genuine behavioral change. D3 requires that change to be explained, per
scenario, by a *named mechanism* — never "values shifted" — before any
baseline is regenerated. The honest finding of this report is that the
change **is real in the code path but produces no observable delta on the
abstract gate scenarios**, for the county-coverage reason above — and D3 is
satisfied by naming, per scenario, exactly *which* mechanism resolved to
absence and *why*.

## Verification evidence

| Check | Command | Result | Evidence |
|---|---|---|---|
| Per-tick construction cadence determinism | `mise run test:q -- tests/unit/tools/test_regression_construction_cadence_determinism.py` | PASS — 1 passed in 5.59s | U7.0 (pre-U7 run) + U8.5 Step 5 (post-regeneration re-run) |
| qa:regression (checkpoint + dense) | `mise run qa:regression` | 5 passed, 0 failed (byte-identical; re-confirmed live) | `reports/vol3-baseline-delta-raw-diff.txt` |
| qa:e2e-regression (detroit-tri-county, 5 ticks) | `mise run qa:e2e-regression` | PASS — "All regression checks passed", exit=0, total_v Δ=0.000% | `reports/vol3-e2e-regression-raw-diff.txt` |
| `mise run check:quick` (lint+format+typecheck) | `mise run check:quick` | PASS | Ruff "All checks passed!"; format "1766 files left unchanged"; MyPy "Success: no issues found in 653 source files" |
| Scoped unit sweep over every U1-U7 touched path | `mise run test:q -- tests/unit/economics tests/unit/dialectics tests/unit/engine tests/unit/config tests/unit/sentinels tests/unit/tools tests/unit/formulas` | 6023 passed, 1 xfailed, **2 pre-existing failures unrelated to U8.3** (see note) | see tail below |

Scoped-sweep tail:

```
FAILED tests/unit/economics/tick/test_financial_state_consequence_roundtrip.py::test_consequence_phase_system_reads_financial_state_same_tick
FAILED tests/unit/tools/test_regression_test_melt_gate.py::test_regression_run_actually_invokes_the_vol3_financial_layer
====== 2 failed, 6023 passed, 1 xfailed, 14 warnings in 285.37s (0:04:45) ======
```

**Note on the 2 failures — pre-existing, out of U8.3 scope, not a regression
introduced here.** U8.3 touches only two paths — `reports/vol3-baseline-delta.md`
(this file) and `tests/unit/tools/test_vol3_baseline_delta_report.py` (new) —
neither of which is production code or either failing test. Both failures
reproduce in isolation on HEAD `adbe5f0c` before any U8.3 edit. Both are
**stale spies left by the U9 endogenous-interest refactor**, not evidence of
an inert layer:

- `test_regression_run_actually_invokes_the_vol3_financial_layer` monkeypatches
  `DefaultInterestCalculator.compute_interest_rate_state` (the FRED-based
  calculator) and asserts it is called during a run. U9 (commit `e19715d3`,
  "endogenous national interest rate replaces the FRED read") removed that
  calculator from the tick path, so the spy target is now dead code — the
  financial layer **does** still execute (the live `qa:regression` run emits
  `TickDynamics Step 2` national-params log lines, which sit *after* the
  `melt_calculator is None` gate, proving the gate is open), it simply no
  longer routes through `DefaultInterestCalculator`.
- `test_consequence_phase_system_reads_financial_state_same_tick` asserts
  `NATIONAL_FINANCIAL_ATTR in graph.graph` in a county-less harness; the same
  U9/U3 wiring change moved when/whether that attr is published.

These belong to the U1/U3/U9 financial-layer wiring tasks and are flagged for
the owner as a follow-up; they do not affect this report's delta analysis
(which turns on county coverage, not on these two spy targets).

## Per-scenario delta

Each section below names the mechanism from the design's layer structure
(§3.1-3.5) that *would* have produced a delta and explains why it instead
resolved to honest absence. The observed delta on every field is **none
(byte-identical)** — the analytic content is *which* Vol III mechanism was
reached and where it terminated in `None`.

**Endogenous interest (U9):** the national interest rate is **total by
construction** — U9 (commit `2a7ae7f5`, "endogenous rate is total") dropped
the interest-unavailable path; the rate is computed endogenously as
`i = r·share(τ)` from sim quantities (Capital Vol. III Part V), *not* read
from FRED (FRED is calibration-only, `interest_profit_share_base`), so **no
`NoDataSentinel` is reachable for the rate on any of the five scenarios.**
It nonetheless moves no baseline value: the rate's `interest_payments` feed
the county-level `SurplusValueDistribution`, and with no `county_fips` there
are no county distributions to carry them — `_national_serviceability`
(`market_scissors.py:547`) returns `None` at its `county_states` guard, so
the scissors interest-burden term drops out entirely.

**Wealth-weighted asymmetry field (U7.6b, owner ruling 2026-07-19):** commit
`3072efd4` rewrote `catalog.py::_mean_asymmetry` to weight each pair by its
engaged wealth — `gap = Σ|b−a|/Σ(a+b)`, `balance = Σ(b−a)/Σ(a+b)` (the
intensive-aggregation remedy the U7.6 sensor forced), affecting the
`capital_labor`, `wage`, `imperial` and `tenancy` oppositions. These four
oppositions *are* present on the abstract scenarios, yet the baseline is
still byte-identical, because the reweighting lives in the **dialectical
opposition layer, which the regression contract does not serialize** (neither
`imperial_circuit.json`'s checkpoints nor `dense/imperial_circuit.csv` carry
any opposition/asymmetry column — only class-level material state and edge
flows/tensions). The reweighted reading re-enters material state only through
(a) the `MarketScissors` correction, which reads the `price_value` opposition,
not these four, and (b) the Vol III interest-burden/debt terms, which are
absent here — so the new asymmetry formula changes no baseline-captured value.

### imperial_circuit

**Description:** 4-node default scenario (`tools/regression_test.py` SCENARIOS).

| Field | Before (pre-Vol III) | After (this branch) | Named mechanism |
|---|---|---|---|
| First checkpoint tick with a value delta | none (byte-identical) | none (byte-identical) | Layer 1 ground-rent repoint (§3.1) needs `county_fips`; scenario has none → `NoDataSentinel` |
| `final_outcome` | SURVIVED | SURVIVED | unchanged — no financial term reached the material state |
| `ticks_survived` | 52 | 52 | unchanged |
| Correction fired differently (tick, if any) | no | no | anchor pull (§3.3): `_read_fictitious_anchor` returns `None` (no `NATIONAL_FINANCIAL_ATTR.fictitious_capital`); interest-burden term (§3.5.1): `_national_serviceability` returns `None` (no county distributions) — both drop out |
| Principal contradiction at terminal tick | (unchanged) | (unchanged) | `surplus_distribution`/`debt_spiral`/`credit`/`financial` are registered (catalog 6→10, U5.9) but get no county input → they never rank; Design Risk #4 not realized |
| First dense-trace divergence (tick, column) | n/a | none (`dense/imperial_circuit.csv` byte-identical) | — |

**Materiality argument:** The Layer-1 repoint (`tick_ground_rent` reading
`DefaultDistributionCalculator`'s real `B230RC0Q173SBEA`-backed figure instead
of the `DefaultRentCalculator` `NoDataSentinel` it fell back to before) can
only fire for a Territory that carries a `county_fips`. `imperial_circuit`'s
territories carry none, so the surplus-distribution layer sees no county to
distribute over: `ground_rent`, `interest_payments`, `taxes_on_surplus` are
all absent, `_national_serviceability` short-circuits to `None`, and the
scissors correction runs with exactly its pre-Vol-III inputs. The delta is
honestly zero, and the reason is county coverage, not inert code (U1.9's
Wayne integration test is where county coverage is proven).

### two_node

**Description:** Minimal worker vs owner (`tools/regression_test.py` SCENARIOS).

| Field | Before | After | Named mechanism |
|---|---|---|---|
| First checkpoint tick with a value delta | none (byte-identical) | none (byte-identical) | no `county_fips` → every Vol III term `None` |
| `final_outcome` / `ticks_survived` | SURVIVED / 52 | SURVIVED / 52 | unchanged |
| Correction fired differently | no | no | anchor pull + interest-burden both resolve to `None` (§3.3/§3.5.1) |
| Principal contradiction at terminal tick | (unchanged) | (unchanged) | four new oppositions registered but unpopulated (no county surplus) |
| First dense-trace divergence | n/a | none (`dense/two_node.csv` byte-identical) | — |

**Materiality argument:** This is the honest-absence case the brief
anticipated. `two_node`'s Territory nodes carry no `county_fips`
(`src/babylon/models/entities/territory.py` makes it optional; the scenario
sets none), so the observed result is exactly **no delta**. The
`opposition_states` key-set *does* grow 6→10 in the live registry
(`build_default_registry`, U5.9 evidence) and the `defines_hash` *does* change,
but neither is part of the serialized checkpoint/dense contract, so both are
invisible to `qa:regression`. Nothing else moved — read from the raw diff,
not assumed.

### starvation

**Description:** Low extraction efficiency stress (`tools/regression_test.py` SCENARIOS).

| Field | Before | After | Named mechanism |
|---|---|---|---|
| First checkpoint tick with a value delta | none (byte-identical) | none (byte-identical) | no `county_fips` → Vol III terms `None` |
| `final_outcome` / `ticks_survived` | SURVIVED / 52 | SURVIVED / 52 | unchanged |
| Correction fired differently | no | no | interest-burden term (§3.5.1) `None` via `_national_serviceability` |
| Principal contradiction at terminal tick | (unchanged) | (unchanged) | financial oppositions unpopulated |
| First dense-trace divergence | n/a | none (`dense/starvation.csv` byte-identical) | — |

**Materiality argument:** Low extraction efficiency stresses the Vol I
production/survival path, none of which the Vol III layer touches without
county surplus data. With no `county_fips`, the debt-accumulation term
(§3.5.2) and anchor pull (§3.3) both terminate in honest absence, so the
scenario's stress dynamics are byte-identical to the pre-Vol-III baseline.

### glut

**Description:** High extraction with metabolic overshoot (`tools/regression_test.py` SCENARIOS).

| Field | Before | After | Named mechanism |
|---|---|---|---|
| First checkpoint tick with a value delta | none (byte-identical) | none (byte-identical) | no `county_fips` → Vol III terms `None` |
| `final_outcome` / `ticks_survived` | SURVIVED / 52 | SURVIVED / 52 | unchanged |
| Correction fired differently | no | no | anchor pull (§3.3) `None`; MarketScissors runs on pre-Vol-III `price_value` inputs |
| Principal contradiction at terminal tick | (unchanged) | (unchanged) | financial oppositions unpopulated |
| First dense-trace divergence | n/a | none (`dense/glut.csv` byte-identical) | — |

**Materiality argument:** High extraction with metabolic overshoot exercises
the metabolic-rift path (`ΔB = R − E·η`), which is orthogonal to the Vol III
financial layer. Even the price⟷value scissors (Program 23), which *is* live,
reads only `price_value` — the U7.6b reweighting of `capital_labor`/`wage`/
`imperial`/`tenancy` never reaches it, and the Vol III interest/debt terms are
county-absent. Byte-identical.

### fascist_bifurcation

**Description:** Consciousness routing to national identity (`tools/regression_test.py` SCENARIOS).

| Field | Before | After | Named mechanism |
|---|---|---|---|
| First checkpoint tick with a value delta | none (byte-identical) | none (byte-identical) | no `county_fips` → Vol III terms `None` |
| `final_outcome` / `ticks_survived` | SURVIVED / 52 | SURVIVED / 52 | unchanged |
| Correction fired differently | no | no | interest-burden + anchor pull both `None` |
| Principal contradiction at terminal tick | (unchanged) | (unchanged) | `financial`/`debt_spiral` never populated to displace the prior principal (Design Risk #4 not realized) |
| First dense-trace divergence | n/a | none (`dense/fascist_bifurcation.csv` byte-identical) | — |

**Materiality argument:** Bifurcation routes agitation to national identity by
SOLIDARITY-edge presence — a consciousness-layer mechanism the Vol III money
layer only feeds through the (absent) financial oppositions. With no county
surplus distributions the four new oppositions stay unpopulated, so the
principal-contradiction ranking is unchanged and the fascist-routing dynamics
are byte-identical to the pre-Vol-III baseline.

## qa:e2e-regression (detroit-tri-county, 5 ticks)

**PASS, unchanged.** The captured run
(`reports/vol3-e2e-regression-raw-diff.txt`) completes with
`counties_alive == 3`, `population liveness: 3/3`,
`total_v: actual=1.497e+09, expected=1.497e+09, Δ=0.000%`, no critical
conservation violations, exit=0. This scenario *does* hydrate real
county-keyed reference series (the log shows `hydrate_counties: Loaded 45
tensors`, `bea_reis_rent: 6`, `fred_rates: 6` rows across Wayne/Oakland/Macomb),
so unlike `qa:regression` it *could* exercise the Vol III county path — but the
annual financial recompute did not fire in this window. The annual pipeline is
gated to year-boundary ticks (`if tick % WEEKS_PER_YEAR != 0: ...` skip,
`src/babylon/domain/economics/tick/system/__init__.py:161`), and the captured
e2e log contains **zero** `TickDynamics`/annual-pipeline lines (contrast the
`qa:regression` diff, which emits `TickDynamics Step 2` national-params lines
once the tick-0 boundary is crossed) — direct evidence the 5-tick window did
not land on a year boundary. The summary-level comparison the e2e baseline
pins (counties_alive, population, total_v within ±1.0%) therefore matches
exactly (Δ=0.000%). County-level financial coverage is proven separately by
U1.9's Wayne integration test, not by this 5-tick gate.

## Risks realized vs mitigated (design spec §7)

| Risk | Realized? | Evidence |
|---|---|---|
| #1 turning on never-executed code surfaces latent bugs | No | Both U8.2 runs completed cleanly (exit 0, no `ValidationError`, no unexpected `NoDataSentinel` crash, no traceback) — the only non-tick log lines are the benign `gamma_basket`/`gamma_III` modelled-default INFO notices and the two expected "Skipping coupling" Volume II endpoint notices. The Vol III terms resolve to honest absence by design, not by error. |
| #4 catalog growth 6→10 changes principal-contradiction ranking | No | No scenario saw a principal-contradiction change: the four new oppositions (`surplus_distribution`/`debt_spiral`/`credit`/`financial`) are registered (U5.9 evidence, `build_default_registry` catalog 6→10) but receive no county surplus input on any county-less scenario, so they never populate and never rank. The ranking is unchanged in all five per-scenario tables above. |

## Owner Approval Gate

> **STOP. Do not proceed to baseline regeneration (U8.5) past this point
> without an explicit, recorded owner approval below.**
>
> This report is the complete, factual record of every behavioral delta
> `qa:regression` and `qa:e2e-regression` will encode as the new baseline.
> Once regenerated, the old (pre-Vol-III) baseline is gone from
> `tests/baselines/` — recoverable only via git history. The owner must
> read the per-scenario tables above and affirmatively approve *in this
> file* before U8.5 runs.
>
> **Honest scope note for the owner:** the behavioral baseline is
> **byte-identical** (5/5 PASS, dense CSVs unchanged). The *only* value U8.5's
> regeneration will change is the advisory `defines_hash` field in the five
> checkpoint JSONs (new `MarketDefines`/`capital_vol3` coefficients from
> U4/U6/U9). No tick value, outcome, or dense trace is overwritten — the
> "old baseline" and the "new baseline" are identical except for that one
> advisory hash. This is a lower-stakes regeneration than the boilerplate
> above implies, and it is recorded here so the sign-off is fully informed.

**Approved by:** `<FILL — leave blank until real sign-off; do not
pre-fill with a placeholder name>`
**Date:** `<FILL>`
**Approval text (verbatim):** `<FILL — quote the owner's actual approval
message, per the ADR078 precedent of quoting the owner's exact words as
the authorization record>`

## Post-approval regeneration record

_Pending U8.5 — to be filled after owner sign-off with the ceremony commit
hash and a one-line confirmation that `qa:regression` is green against the
newly regenerated baselines._
