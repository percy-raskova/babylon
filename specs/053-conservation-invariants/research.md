# Phase 0 Research: Property-Based Tests for Conservation Invariants

**Date**: 2026-05-05
**Branch**: `053-conservation-invariants`

## Open Questions Carried into Phase 0

| # | Question | Resolution Path |
|---|----------|----------------|
| R1 | Which **engine systems** (vs substrate computers) actually touch `HexEconomicState.{constant_capital, variable_capital, surplus_value}`? | Audit each `step()` implementation in `src/babylon/engine/systems/`. |
| R2 | What is the correct `creates_value: ClassVar[bool]` value for each system? | Derived from R1 audit + scope analysis. |
| R3 | Hypothesis strategy: how to generate a valid `HexGrid` with consistent res-6 / res-5 parent pointers when we are not actually computing real H3 hierarchies? | Pick between (a) drawing real H3 IDs via the `h3` library and computing `h3.cell_to_parent()`, or (b) drawing synthetic IDs and constructing a consistent fake hierarchy. |
| R4 | Hypothesis strategy: how to generate a sparse OD matrix that exercises edge cases (empty rows, identity, dense, normalized)? | Use `hypothesis-numpy` patterns — generate dense matrix shapes, pick cells, normalize. |
| R5 | Where does the `DPDState` cohort count live, and how are births/deaths bookkept tick-to-tick? | Read `src/babylon/economics/lifecycle/types.py` and `src/babylon/engine/systems/{lifecycle,vitality}.py`. |
| R6 | Capital-stock perpetual-inventory: which function or class realizes `K_{t+1} = (1-δ)K_t + I_t` in the codebase? | Read `src/babylon/economics/capital_stock.py`. |
| R7 | Hypothesis profile: how to keep the property-test suite under 60 s while still drawing ≥100 examples per `@given`? | Configure `hypothesis.settings` profiles (default vs slow), use `derandomize=True` for CI. |
| R8 | Should the failure message for the c+v+s invariant point at a specific system on a per-system failure, vs the whole pipeline on a full-pipeline failure? | Use `pytest.fail(msg)` with the system name in the per-system parametrize id; rely on Hypothesis shrinking for the pipeline case. |

---

## R1 / R2 — System audit and `creates_value` marker

Audit performed via `grep` over each `src/babylon/engine/systems/*.py`. Two distinct mutation classes matter for c+v+s:

**Class A — touches `HexEconomicState.{c, v, s}` directly.** None of the engine systems do this; only the substrate computers in `src/babylon/economics/substrate/{production, circulation, aggregation, equalization, ground_rent}.py` do.

**Class B — touches a graph-node attribute named `wealth` (which is not the same field as `c+v+s` but is the engine-side proxy for capital mass).** The audit produced:

| System | Touches `wealth`? | Behaviour | Proposed `creates_value` |
|--------|-------------------|-----------|--------------------------|
| `economic.ImperialRentSystem` | Yes | Subtracts cost: `graph.update_node(node.id, wealth=max(0.0, wealth - cost))` | **True** (cost is removed from the system, not redistributed in this step) |
| `solidarity.SolidaritySystem` | No | Mutates SOLIDARITY edges and consciousness only | **False** |
| `ideology.ConsciousnessSystem` | No | Drifts ideology floats only | **False** |
| `survival.SurvivalSystem` | No | Computes `P(S\|A)`, `P(S\|R)` (read-only writes) | **False** |
| `struggle.StruggleSystem` | Yes | Multiplies wealth by `(1 - destruction_rate)` during uprisings | **True** (destroys wealth) |
| `contradiction.ContradictionSystem` | No (read-only) | Reads wealth to compute tension; does not mutate | **False** |
| `territory.TerritorySystem` | No directly; eviction events may | Heat dynamics + eviction pipeline. Eviction-emitted events may transfer wealth elsewhere — handled by `dispossession_events`. | **False** for the system itself; events handled separately |
| `production.HexProductionComputer` | Yes (substrate, observes c/v/s) | Per spec, observes already-hydrated value-in-hours from capital stocks; does not generate fresh value | **False** |
| `lifecycle.LifecycleSystem` | Reads `wealth_d_prime` | Cohort transitions; doesn't directly touch wealth | **False** for c+v+s; but produces births/deaths counted in invariant 4 |
| `metabolism.MetabolismSystem` | No `wealth` mutation | Tracks biocapacity rift; ecological deltas | **False** for c+v+s |
| `dispossession_events.DispossessionEvents` | Yes | `territory_wealth - transfer_amount` then transfers elsewhere | **True** when transfer is partial / lossy; `False` if fully sum-preserving. Audit at implementation time; default to `True` to be safe. |
| `decomposition.DecompositionSystem` | Yes | "Transfers wealth proportionally" (LA → reserve army)  | **False** if internally redistributing (sum-preserving); `True` if some is destroyed. Audit at implementation time. |
| `reserve_army.ReserveArmySystem` | Indirect | Cohort accounting | **False** for c+v+s |
| `community.CommunitySystem`, `ooda.OODA*`, `edge_transition.*`, `field_derivative.*`, `event_template.*`, `contradiction_field.*`, `control_ratio.*`, `vitality.VitalitySystem` | No `wealth` mutation found | Mostly metadata, edges, derived quantities | **False** |

**Decision (R1/R2)**: Adopt the table above as the seed `creates_value` policy. The audit is encoded as a single-line `creates_value: ClassVar[bool] = <T/F>` on each system class. Where the audit was inconclusive (`dispossession_events`, `decomposition`), default to `True` and let the substrate-level test prove conservation if the maintainer believes the redistribution is exact — this enforces the default-deny policy from FR-004a without optimistically green-lighting a system whose conservation behaviour is not yet proven.

**Rationale**: Default-deny means "if you're not sure, set the marker `True` and the test will skip you; later, a maintainer who proves conservation can flip it to `False` and the test will catch any regression." This biases toward false-skip rather than false-pass.

**Alternatives considered**:
- Inferring the marker dynamically by introspecting whether `step()` writes to a `wealth`-typed key — rejected because dynamic inference encodes the audit itself in test code, defeating the purpose of an explicit declaration.
- Maintaining a curated test-side allowlist — rejected because the marker on the class is the single source of truth and survives renames.

---

## R3 — Hex-grid Hypothesis strategy

**Decision**: Use the real `h3` library to generate H3 cell IDs. Draw 1–25 000 res-7 cells per grid (the upper bound matches the Article IV statewide-Michigan scale; Michigan has ~50 000 res-7 cells statewide), then derive their res-6 and res-5 parents via `h3.cell_to_parent(cell, parent_resolution)`. This guarantees the parent-child pointer maps satisfy the structural invariants of `HexGrid` without us having to hand-build them.

**Source**: `tests/property/strategies/hex_grid.py` (NEW). Default seed pool is `MICHIGAN_RES7_SEED_CELLS`, populated once at module-import time via `h3.polygon_to_cells(MICHIGAN_BOUNDARY_GEOJSON, res=7)` (Michigan boundary already available via the Natural Earth SQLite dependency from spec 036). Falls back to a smaller `WAYNE_OAKLAND_MACOMB_SEED_CELLS` pool (used by `MockCommuterFlowSource` and `WAYNE_HEX_IDS`) if Natural Earth is unavailable in the test environment.

**Rationale**: The 25 000 upper bound matches the constitution's Article IV canonical test case (state of Michigan, all 83 counties, 2010–2025) and the Article IV.2 tri-county backward-compat criterion. Generating arbitrary H3 IDs out of nowhere risks producing cells from disparate parts of the world that share no parent; drawing from a pool of real Michigan res-7 cells lets us cover both the statewide and tri-county acceptance criteria with a single strategy. Hypothesis's default size-biased shrinking ensures most generated examples are small (1–10 hexes), so the upper bound is reached only occasionally on the default profile and exhaustively on the `slow` profile — keeping the SC-002 60 s budget achievable while still stressing the scaled-tolerance bound at realistic statewide scale.

**Alternatives considered**:
- Synthetic string IDs and a fake hierarchy — rejected; would diverge from the production `HexGrid` validators and from the real `h3` library's parent computation.
- Drawing from the full continental US — rejected; too many parents (~10 M res-7 cells nationally), slow generation, low test value beyond the constitutional Michigan scope.
- Smaller upper bound (e.g., 500) — rejected; would not stress the scaled tolerance at the Article IV statewide scale and would leave the largest realistic input regime untested.

---

## R4 — OD matrix Hypothesis strategy

**Decision**: Use `hypothesis.strategies.composite` to draw `(N, density)` pairs (`N ∈ [1, 25 000]` matching `hex_grid_strategy`; `density ∈ [0.0, 1.0]` for small N, capped at `density ≤ 0.01` for large N to match empirical LODES sparsity and keep matrix construction tractable), then build an `N × N` `scipy.sparse.csr_matrix` by drawing a Bernoulli mask + non-negative weights, normalizing each non-zero row to sum to 1.0 (matching `circulate_wages`'s row-stochastic precondition). Special generators:

- `identity_od_strategy(N)` — guarantees the identity case (no redistribution).
- `empty_row_od_strategy(N)` — at least one zero-row hex.
- `full_redistribution_od_strategy(N)` — every row has multiple non-zero entries.

These specials are explicitly drawn via `hypothesis.strategies.one_of` to ensure Hypothesis exercises the edge cases on most runs.

**Rationale**: The example-based test in `test_circulation.py` already documents that the identity matrix and empty-row matrix are the two interesting edge cases. Promoting them to explicit generators ensures they are not lost when Hypothesis randomly samples mostly-dense matrices.

**Alternatives considered**:
- `hypothesis-numpy` array strategies — works but adds a dependency edge for sparse matrices that scipy's own constructors handle better. Rejected for clarity.

---

## R5 — Population bookkeeping

**Decision**: `population_t = sum(DPDState.cohort_total for hex in WorldState.hexes)`. Births and deaths are read from the per-tick event log (`WorldState.events`) filtered by event type. The lifecycle and vitality systems already publish `BIRTH` / `DEATH` (or equivalent) events; the test reads the event count for the tick and asserts the accounting equation against the change in `population`.

**Source**: `src/babylon/economics/lifecycle/types.py` defines `DPDState`. `src/babylon/engine/systems/lifecycle.py` mutates D-P-D′ transitions. `src/babylon/engine/systems/vitality.py` applies mortality. No new persistence is needed; the test reads existing fields.

**Rationale**: Per the user's framing in `/speckit.specify`, the population invariant requires explicit accounting bookkeeping. Reading from `WorldState.events` is consistent with the existing per-tick event semantics (CLAUDE.md "Common Gotchas: WorldState.events is Per-Tick, NOT Cumulative"); the test therefore accumulates births/deaths across ticks itself, never trusting a cumulative state.

**Alternatives considered**:
- Adding a dedicated `births_this_tick` / `deaths_this_tick` field to `WorldState` — rejected; events already carry this.
- Computing population only at simulation end — rejected; we want per-tick conservation, not just terminal conservation.

---

## R6 — Capital-stock perpetual inventory

**Decision**: `src/babylon/economics/capital_stock.py:65 class CapitalStockCalculator` realises the perpetual-inventory recurrence. The property test extracts the recurrence as a pure function (or uses the calculator directly) and asserts `|K_{t+1} − ((1 − δ) K_t + I_t)| < 1e-10`. Inputs are drawn from `K ∈ [0, 1e9]`, `δ ∈ [0, 1]`, `I ∈ [0, 1e9]` to cover both small and economically realistic magnitudes.

**Rationale**: The recurrence is a closed-form formula; testing it against the calculator exercises both the formula and any rounding behaviour the calculator introduces (e.g., via Pydantic constrained types). Using the calculator (rather than reimplementing the formula in the test) ensures the test catches calculator bugs, not just formula bugs.

**Alternatives considered**:
- Testing the formula in isolation as a pure function — rejected; would fail to catch wrapper bugs in the calculator.
- Drawing K from a Pareto distribution to stress numerical stability — deferred; can be added later as a slow-profile variant.

---

## R7 — Hypothesis profiles for the 60 s budget

**Decision**: Define two profiles in `tests/property/conftest.py`:

```python
from hypothesis import settings, HealthCheck, Phase

settings.register_profile(
    "default",
    max_examples=100,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "slow",
    max_examples=500,
    derandomize=False,
    deadline=None,
)
settings.load_profile("default")
```

CI runs `default`. Local `mise run test:slow` (or `pytest -k slow`) loads `slow`. `derandomize=True` in default makes CI runs reproducible without re-shrinking; `derandomize=False` in slow lets the example database grow.

**Rationale**: The 60 s budget (SC-002) requires bounded example counts. 100 examples × 5 invariants × ~120 ms per generation+execution = ~60 s upper bound. The slow profile pays the cost of exploration but is run out-of-band.

**Alternatives considered**:
- Pytest-hypothesis `--hypothesis-seed` — supplements but does not replace `derandomize`; both are used.
- Single profile with `max_examples=200` — rejected; doubles CI cost without doubling coverage value.

---

## R8 — Failure messaging

**Decision**: For per-system tests, use `pytest.parametrize` with the system class as the id (`test_value_conservation_per_system[ImperialRentSystem]`). When the assertion fails, the test id alone identifies the system; the Hypothesis counterexample identifies the input. For full-pipeline tests, use a single test name (`test_value_conservation_full_pipeline`); when it fails, the failure message lists per-system pre/post sums to localize where in the pipeline the drift entered.

**Rationale**: This satisfies FR-013 (failure output identifies the invariant, the input, and the responsible system) without introducing a custom failure-formatting layer.

**Alternatives considered**:
- Custom Hypothesis `note()` calls in every test — rejected; verbose and brittle.
- Pytest plugins for per-system reporting — rejected; existing parametrize already does this for free.

---

## Summary of resolved unknowns

| # | Resolution |
|---|------------|
| R1 | Engine systems mostly do not touch HexEconomicState c+v+s; only substrate computers do. The full-pipeline test catches engine-side wealth mutations that bleed into hex aggregates. |
| R2 | `creates_value` defaults to `True` for systems that audit-prove they mutate wealth (`ImperialRent`, `Struggle`, `Dispossession`, possibly `Decomposition`); `False` for the rest. Default-deny is enforced by audit-time decision, not test-time inference. |
| R3 | HexGrid strategy uses real `h3` library and a fixed pool of Wayne/Oakland/Macomb seed cells. |
| R4 | OD matrix strategy uses scipy sparse + explicit edge-case generators (identity, empty-row, dense). |
| R5 | Population = sum of `DPDState.cohort_total`; births/deaths from per-tick events. |
| R6 | `CapitalStockCalculator` is the calculator-under-test; recurrence asserted to 1e-10. |
| R7 | Two Hypothesis profiles: `default` (CI, 100 ex, derandomized), `slow` (out-of-band, 500 ex). |
| R8 | Per-system tests use parametrize for failure id; full-pipeline test enumerates per-system pre/post in the failure message. |

All `NEEDS CLARIFICATION` markers from the Technical Context are resolved. Ready for Phase 1.
