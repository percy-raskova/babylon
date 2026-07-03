# 06b — Phase D design (economy as adjunction)

Fable's binding design for `project/06` §6 + §9.3, written 2026-07-03
after a full kernel recon. Delegate: read `project/06` §8 + §9.1 first,
then this file. The prime directive of this phase is **reuse**: every
arithmetic quantity below already has a tested kernel (cited by file);
the adjunction instances are the STRUCTURE that binds them plus the NEW
laws. If a kernel's actual formula contradicts an identity stated here,
STOP and report — do not bend the law test to fit.

## D0. Ground truth corrections (recon findings, binding)

- The contract's shorthand "γ_basket = τa/τb" is a gloss. The tested
  code formula is the harmonic mean `γ_basket = 1/(α/γ_import + (1−α))`
  (`economics/melt/basket_visibility.py` and `economics/gamma/gamma_basket.py`
  agree). Cite and use the code formula everywhere.
- π (throughput) lives in `economics/throughput/calculator.py`
  (`π = τ_through/τ_national`) and is NOT a visibility mechanism — it
  never enters τ_eff. One law test pins this: rescaling π must not
  change τ_eff or any Φ component.
- Meillassoux externalized reproduction has NO kernel (zero repo hits).
  Its honest computable proxy is `formulas/lifecycle.py::compute_shadow_subsidy`
  (intergenerational: value of next-generation labor-power minus wages
  paid for its rearing). Phase D adopts that proxy as Φ_repro and says
  so in the docstring — no invented economics.
- `economics/shadow_labor.py` (config-lens Fortunati duplicate) is NOT
  touched — the data-driven `economics/gamma/` package is the kernel of
  record for Φ_domestic. Flag the duplication in the module docstring of
  value_form.py; reconciling it is out of scope.

## D1. `instances/value_form.py` — the labor-time ⇄ money adjunction

Typed poles REUSE the C1.7-orphaned `babylon.economics.value` models:
`AbstractLabor` (pole A, hours) ⇄ `ExchangeValue` (pole B, dollars).
This re-consumes the orphan — record that in the module docstring.

```python
class ValueFormAdjunction(BaseModel):   # frozen
    tau: float                # τ from MELTCalculator (DI — protocol, not Default hardwired)
    gamma_basket: float       # from BasketVisibilityCalculator
    # tau_effective = tau * gamma_basket   (computed_field; must equal
    # NationalParameters.tau_effective semantics — parameters.py:232-236)

    def to_labor_hours(self, dollars: float) -> float   # dollars / tau
    def to_money(self, hours: float) -> float           # hours * tau
```

- **τ round-trip law**: `to_money(to_labor_hours(x)) == x` and the
  reverse, Hypothesis over x ∈ [1e-6, 1e12], rel tol 1e-12. The pure
  numeraire map has ZERO defect — Φ is not conversion error.
- **Φ is the wage-form counit defect** — the gap between what the wage
  commands and what the labor produced:
  - `phi_class(w_c: float, v_c: float) -> float` = `(w_c − v_c)/v_c`,
    per-class, signed, dimensionless (the §6 contract form; ValueError
    on v_c \<= 0 — logic fails loud).
  - `phi_hour(wage_hourly: float, tau_effective: float) -> float` =
    `wage_hourly − tau_effective` (dollars/hour; the §9.3 sorting form).
- **Class sorting** (§9.3):
  `class_position_by_phi_hour(wage_hourly, tau_effective, v_reproduction)`
  returns `ClassPosition` — Φ_hour ≥ 0 →
  LABOR_ARISTOCRACY; Φ_hour < 0 ∧ W ≥ V_repro → PROLETARIAT; W < V_repro
  → LUMPENPROLETARIAT (use the existing enum + SUBPROLETARIAT alias,
  `economics/melt/types.py`). This is the FLOW axis; do NOT touch the
  canonical wealth-percentile classifier (stock axis — the two are
  deliberately decoupled, melt/types.py:9-18). Docstring must say both
  axes exist and why.
- **Numeraire invariance laws** (extend the spec-060 suite's style, new
  module `tests/property/dialectics/test_value_form_invariance.py`):
  `phi_class` invariant under uniform currency rescale k (w,v both
  scale); `class_position_by_phi_hour` invariant when wage, τ_eff, and
  V_repro all rescale by k. Hypothesis k ∈ [1e-3, 1e6].

## D2. Φ tri-decomposition (§9.3 — mandatory)

```python
class PhiDecomposition(BaseModel):      # frozen
    phi_unequal_exchange: float   # Emmanuel/Amin — kernel: gamma package
    phi_reproduction: float       # Meillassoux — kernel: lifecycle.compute_shadow_subsidy
    phi_domestic: float           # Fortunati — kernel: gamma_iii + shadow_subsidy
    # total: computed_field = sum of the three. NEVER a stored primitive.
```

Component kernels (reuse, cite in docstrings):

- Φ_UE := `DefaultShadowSubsidyCalculator.compute_phi_imperial`
  (`(1−γ_basket) × Consumption`, gamma/shadow_subsidy.py). The
  `formulas/unequal_exchange.py` four (exchange_ratio → value_transfer)
  are the flow-level cross-check: one law test computes a two-zone
  fixture both ways and asserts the same sign and order of magnitude.
- Φ_repro := aggregated `compute_shadow_subsidy` (per D0).
- Φ_domestic := the value of unpaid care hours, `τ × L_unpaid`.
  **Verify the kernel first**: if `compute_phi_iii` returns
  `(1−γ_III) × L_total × τ` it algebraically equals `τ × L_unpaid`
  (since 1−γ_III = L_unpaid/L_total) — use it directly. If it actually
  returns `(1−γ_III) × L_unpaid × τ` (quadratic in L_unpaid), that is a
  narrower "invisible-fraction" quantity: then Φ_domestic is computed as
  `τ × L_unpaid` in the instance and Φ_III is carried as a separate
  derived report field, NOT the conservation term. Determine which by
  reading the code; record the finding in the docstring.
- **THE conservation law** (§9.3): over a closed fixture,
  `Σ L_performed × τ = Σ V_visible + Σ Φ_shadow` where
  `L_performed = L_paid + L_unpaid`, `V_visible = τ × L_paid`,
  `Φ_shadow = Φ_domestic (+ Φ_repro where the fixture models generations)`. Exact within float tolerance; each component
  independently asserted (kill the "one big sum hides a broken term"
  failure mode). Name: `test_conservation_labor_equals_visible_plus_shadow`.

## D3. `instances/scale.py` — allocate ⊣ aggregate

The recon confirmed the two cited kernels operate on unrelated domains
today (industry-rent→county vs CFS-flow-matrix). The adjunction is the
GENERIC structure both instantiate:

```python
class ScaleAdjunction(BaseModel):       # frozen
    mapping: Mapping[str, str]          # child -> parent (total function)
    shares: Mapping[str, float]         # child -> share of its parent (per-parent sum == 1, validated)

    def allocate(self, by_parent: Mapping[str, float]) -> dict[str, float]
    def aggregate(self, by_child: Mapping[str, float]) -> dict[str, float]
```

- **Adjunction laws** (Hypothesis over random partitions + values):
  `aggregate(allocate(x)) == x` exactly (unit is identity — shares sum
  to 1); `allocate(aggregate(y))` is idempotent (the closure — applying
  it twice equals once). Extensive quantities SUM on aggregate;
  intensive quantities take the share-weighted mean (`aggregate_intensive`
  helper; one law test each).
- **H3 sheaf laws** (§9.1 — name the sheaf condition in the tests):
  `test_sheaf_gluing_conservation` (gluing = conservation: child sums
  equal parent totals) and `test_sheaf_functoriality_h3`
  (`A_{6→5} ∘ A_{7→6} == A_{7→5}` using real `h3` lib parentage over a
  small res-7 cell set — build the two mappings from `h3.cell_to_parent`;
  the composite of the two aggregations equals the direct one). NO
  cohomology, no sheaf class — the tests ARE the sheaf condition.
- **Naturality squares**: docstrings map the audit invariant names
  (`persistence/conservation_audit.py:158-180`) onto squares —
  hex→county, county→state, state→national sums for c/v/s/k are three
  square FAMILIES; one parametrized law test per family using
  ScaleAdjunction over fixture data. (The auditor's 21 names are a
  contract with no-op evaluators today — Phase D does NOT wire
  register_invariant; that is spec-062's program. Say so in the
  docstring.)
- Bind, don't rewrite: a thin test demonstrates
  `DefaultGeographicAggregator.aggregate` (geographic_flow.py:225)
  agrees with `ScaleAdjunction.aggregate` on a shared fixture (the
  existing kernel keeps its API; the instance names its law).

## D4. Accounting becomes categorical — ImperialRentSystem exposure

Computation UNCHANGED. The wages phase of
`engine/systems/economic.py::ImperialRentSystem` (whose per-edge
`value_flow` already exists) additionally writes per-tick node attrs on
each worker class it pays: `w_paid` (total wages incl. super-wage
bonus) and `v_produced` (productivity_value). Extraction phase already
records `value_flow` — leave it. That is the WHOLE change to economic.py;
its tests extend, none change.

`ContradictionSystem._build_graph_inputs` gains
`wage_value_pairs: tuple[tuple[float, float], ...] = ()` on
`GraphInputs` — one `(w_paid, v_produced)` pair per class node carrying
both attrs (skip nodes missing either; inactive-node guard as the other
extractors).

## D5. Catalog rebind — `wage` and `imperial` get true measures

Per the catalog's own docstrings ("Phase D replaces it" / "Phase D
rebinds this"):

- `wage` measure: from WAGES-edge endpoint wealth-asymmetry → the true
  defect over `wage_value_pairs`: gap = mean |w−v|/(w+v), balance =
  mean signed (w−v)/(w+v) (REUSE
  `formulas/contradiction.calculate_wealth_asymmetry_gap/_balance` on
  (v, w) ordered so positive balance = wage exceeds value = the bribe).
  Empty pairs → (0,0) with the old endpoint proxy as documented
  fallback REMOVED (no silent dual path — empty means no data). Update
  the spec poles to the true names: pole_a="value-produced",
  pole_b="price-of-labor-power"; keep key="wage".
- `imperial` measure: from NULL → per-class signed counit defect over
  the same pairs: gap = mean |phi_class| clamped [0,1] via the
  asymmetry form |w−v|/(w+v); balance = mean signed form (positive =
  wages exceed value = imperial-rent inflow = core pole dominant).
  Poles stay core/periphery; unity string updated to cite value_form.
  (wage reads the RELATION per class; imperial reads the same defect as
  the core↔periphery frame — document that they share inputs but carry
  different poles/levels, which C2's coupling graph already encodes as
  `wage feeds capital_labor`; add `wage feeds imperial` to the default
  coupling graph.)
- Consumers to re-verify (do not change semantics): consciousness reads
  wage's rate (crisis-gating — flat during a growing bribe stays
  CORRECT); `ImperialRentSystem._calculate_aggregate_tension` reads
  capital_labor (untouched).
- **Bridged integration test** (new, gated like
  test_bridge_income_circuit.py): 30-tick bridged run — assert the
  imperial opposition's gap becomes NON-ZERO once Φ flows (the
  income-circuit world pays super-wages every tick), its balance sign
  is stable-positive (pacification), and `wage`'s state matches the
  (w, v) accounting rather than endpoint wealth.

## D6. Out of scope (fence — do not wander)

- The four dormant spec-060 "arm" integration tests
  (`test_aggregate_equalities.py` etc.) stay gated: they await a
  transformation-weight instance (Volume III equalization), which is
  NOT Phase D (contract §6/§9.3 silence). Record in value_form.py's
  docstring that the transformation problem lands in a later phase.
- `economics/tick/system/imperial_rent.py` (county Leontief pipeline)
  and its `phi_hour` (production-chain rent per hour — a DIFFERENT
  quantity from D1's wage-defect Φ_hour): read-only. Name the collision
  in the value_form docstring so nobody conflates them.
- `economics/shadow_labor.py` duplication: flag only (D0).
- No GameDefines changes; no new tunables (all inputs are data or DI).

## File plan

| File                                                      | Change                                                                      |
| --------------------------------------------------------- | --------------------------------------------------------------------------- |
| `src/babylon/dialectics/instances/value_form.py`          | NEW — adjunction, phi_class/phi_hour, sorting, PhiDecomposition             |
| `src/babylon/dialectics/instances/scale.py`               | NEW — ScaleAdjunction + intensive/extensive helpers                         |
| `src/babylon/engine/systems/economic.py`                  | wages phase writes w_paid/v_produced node attrs                             |
| `src/babylon/engine/systems/contradiction.py`             | GraphInputs extraction: wage_value_pairs                                    |
| `src/babylon/dialectics/instances/catalog.py`             | wage + imperial measure rebind; `wage feeds imperial` coupling              |
| `tests/unit/dialectics/test_value_form.py`                | NEW — round-trip, phi laws, sorting, tri-decomposition, conservation        |
| `tests/unit/dialectics/test_scale.py`                     | NEW — adjunction laws, sheaf gluing/functoriality (h3), naturality families |
| `tests/property/dialectics/test_value_form_invariance.py` | NEW — numeraire invariance (Hypothesis)                                     |
| `tests/unit/engine/systems/test_economic_accounting.py`   | NEW — w_paid/v_produced exposure                                            |
| `tests/unit/engine/systems/test_contradiction_system.py`  | EXTEND — wage_value_pairs extraction                                        |
| `tests/integration/test_value_form_bridged.py`            | NEW — imperial gap live in the income-circuit world                         |

Commit units: (1) value_form + laws, (2) scale + sheaf laws,
(3) accounting exposure, (4) catalog rebind + bridged test, (5) docs +
margins. TDD each. Mutation probes required on: the tri-decomposition
sum (drop a component), the conservation identity (swap L_paid for
L_total), and aggregate∘allocate identity (skip share normalization).

## Gate

Standing loop (§8) + economics suites
(`poetry run pytest tests/unit/economics tests/integration/economics -q`)

- the new law tests + property suite. All-green bar. Then STOP for
  Fable review before Phase E.
