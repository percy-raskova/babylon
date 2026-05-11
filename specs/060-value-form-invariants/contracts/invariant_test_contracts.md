# Invariant Test Contracts

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md)

Each contract states, in Given-When-Then form, the exact assertion the test
makes about engine behavior. These are the test-facing contracts — what
the bundle expects from the engine, not how the bundle implements the
checks. Each entry maps 1:1 to a Functional Requirement and at least
one Success Criterion.

---

## Value-Form Invariants

### Contract FR-001 / SC-001 — Numeraire Invariance (single-tick)

**Test**: `tests/property/test_numeraire_invariance.py::test_ratios_invariant_under_rescaling`

**Given**: A baseline `WorldState` from `TwoNodeScenario.build()` at tick T.
**When**:
1. Run one tick → produces `world_base`, `metrics_base = DerivedTensorMetrics.from_world(world_base)`.
2. Apply `rescale_currency_fields(world, k=100)`, run one tick → `world_k100`, `metrics_k100`.
3. Apply `rescale_currency_fields(world, k=0.01)`, run one tick → `world_k001`, `metrics_k001`.
**Then**:
- For each ratio in `{profit_rate_flow, profit_rate_stock, organic_composition, exploitation_rate}`:
  - `|metrics_k100.X - metrics_base.X| / |metrics_base.X| ≤ 1e-12`
  - `|metrics_k001.X - metrics_base.X| / |metrics_base.X| ≤ 1e-12`

### Contract FR-002 — Numeraire Invariance (property test)

**Test**: `tests/property/test_numeraire_invariance.py::test_ratios_invariant_hypothesis`

**Given**: Hypothesis generates 100 examples of `(scenario_seed: int, k: float ∈ [1e-3, 1e6])`.
**When**: For each example, build a `WorldState` with the seeded scenario, run one tick at base scale and at scale `k`, compute ratios.
**Then**: Every example satisfies the same per-ratio 1e-12 relative-tolerance assertion.

### Contract FR-003 / SC-002 — Per-Entity MELT Consistency

**Test**: `tests/integration/economics/test_melt_consistency.py::test_per_entity_money_equals_labor_times_tau`

**Given**: `WayneCountyScenario.build()` at tick T+1 after one tick has run.
**When**: For each productive entity (organization with non-zero `constant_capital` and `variable_capital`, county tensor with non-zero `total_v`):
- Read its money-form X (c, v, s, total_value).
- Read its labor-time X.
- Compute `expected_money = labor_time × τ` where τ = `MELTCalculator.get_melt(world.year)`.
**Then**:
- If `τ` is a `NoDataSentinel`: emit `pytest.skip("MELT NoDataSentinel for year={year}; cannot assert consistency")` per FR-004.
- Else: `|money_X - expected_money| / |money_X| ≤ 1e-9` for every entity and every X ∈ {c, v, s, total_value}.

### Contract FR-005 / SC-003 — TSSI/NI Aggregate Equalities

**Test**: `tests/integration/economics/test_aggregate_equalities.py::test_tssi_aggregate_equalities`

**Given**: `TwoNodeScenario.build()` at tick T+1 after one tick.
**When**:
- `Σπ = sum(entity.money_profit for entity in productive)`
- `Σs = sum(entity.labor_surplus for entity in productive)`
- `ΣP = sum(entity.money_price for entity in productive)`
- `ΣW = sum(entity.labor_value for entity in productive)`
- `τ = MELT for the tick`
**Then**:
- `|Σπ - Σs × τ| / |Σπ| ≤ 1e-6`
- `|ΣP - ΣW × τ| / |ΣP| ≤ 1e-6`

### Contract FR-006 / SC-004 — OCC-Conditional Wage Asymmetry

**Test**: `tests/integration/economics/test_wage_occ_asymmetry.py::test_high_occ_low_occ_diverge`

**Given**: A scenario with ≥ 5 hexes spanning OCC values; transformation engine in REDISTRIBUTION_ACTIVE mode.
**When**:
1. `skip_unless_active(world, "spec-060 FR-006")`.
2. Run tick A with baseline wages → `prices_A`, `values_A`.
3. Build `world_B` with all variable-capital fields × 1.10, run tick B → `prices_B`, `values_B`.
4. For each hex, compute `ratio = price / value` at A and B.
5. Classify hexes as high-OCC (above national-median OCC) or low-OCC (below).
**Then**:
- At least 80% of high-OCC hexes: `ratio_B < ratio_A` (decreased).
- At least 80% of low-OCC hexes: `ratio_B > ratio_A` (increased).
- Diagnostic on failure: name the hexes and their OCC + delta-ratio.

### Contract FR-007 / SC-005 — Productivity-Shock Decoupling

**Test**: `tests/integration/economics/test_productivity_shock_decoupling.py::test_value_drops_immediately_price_lags`

**Given**: A scenario with a designated productive sector S having stable c, v, s; transformation in REDISTRIBUTION_ACTIVE mode.
**When**:
1. `skip_unless_active(world, "spec-060 FR-007")`.
2. Run baseline tick T → record `value_S_old`, `price_S_old`.
3. Apply `halve_snlt_in_sector(world, S)` → `world'`.
4. Run tick T+1 from `world'` → record `value_S_new`, `price_S_new`.
5. Continue ticks T+2..T+5 from each successor.
**Then**:
- `|value_S_new - value_S_old / 2| / |value_S_old / 2| ≤ 1e-9` (value halved).
- `price_S_new / price_S_old > 0.5 + ε` for `ε = 1e-3` (price has NOT halved).
- Over T+1..T+5: the sequence `price_S_t / (value_S_t × τ_t)` is monotonically decreasing in absolute deviation from 1.0 (asymptotic convergence).

---

## Software Metamorphic Invariants

### Contract FR-013 / SC-009 — UUID Relabeling Invariance

**Test**: `tests/integration/economics/test_uuid_relabel_invariance.py::test_numeric_fields_identical_under_relabeling`

**Given**: `TwoNodeScenario.build()` at tick T.
**When**:
1. Run tick T → `world_base`.
2. `relabel_uuids(world)` → `world_aliased`, run tick → `world_aliased_base`.
**Then**:
- For every entity by-canonical-name in `world_base` and corresponding-by-alias in `world_aliased_base`:
  - Every numeric field (Currency, LaborHours, profit rates, ratios) is identical within 1e-15 relative tolerance.
- Only difference: IDs themselves.

### Contract FR-014 / SC-010 — Serialization Round-Trip Identity

**Test**: `tests/integration/economics/test_serialization_roundtrip.py::test_json_roundtrip_preserves_state`

**Given**: `WayneCountyScenario.build()` at tick T.
**When**:
1. `json_str = world.model_dump_json()`.
2. `world_rt = WorldState.model_validate_json(json_str)`.
3. `assert world == world_rt` (Pydantic structural equality).
4. Run one tick from `world` → `world_t1`.
5. Run one tick from `world_rt` → `world_rt_t1`.
6. `assert world_t1 == world_rt_t1`.
**Then**:
- Structural equality holds at every step.
- Diagnostic on failure: DeepDiff between `world` and `world_rt` showing field-level deltas.

### Contract FR-015 / SC-011 — Markovian Step Semantics

**Test**: `tests/integration/economics/test_markovian_step.py::test_step_depends_only_on_state_not_absolute_tick`

**Given**: A populated `WorldState`.
**When**:
1. Build `world_a` with `world.tick = 100`.
2. Build `world_b` with `world.tick = 10000`, every other field identical.
3. Run one tick on each → `world_a_t1`, `world_b_t1`.
**Then**:
- For every numeric field, every dict/list field, every relationship: `world_a_t1.field == world_b_t1.field` except for `tick` (which is `101` vs `10001`).
- Event payloads must be identical except for `tick` markers in the payload itself.

### Contract FR-016 / SC-012 — H3 Round-Trip Conservation

**Test**: `tests/integration/economics/test_h3_round_trip.py::test_rollup_disaggregate_conserves`

**Given**: A `HexEconomicState`-populated scenario at H3 resolution R=8.
**When**:
1. Collect `c[hex]` for every hex at R=8: `original = {h3: hex.constant_capital for hex in hexes}`.
2. Aggregate to R=7 via `h3.cell_to_parent(h3, 7)`, summing children: `parent_totals = {p: sum(...)}`.
3. Disaggregate parent_totals back to R=8 via `split_uniformly` using `h3.cell_to_children(p, 8)`.
**Then**:
- For each parent p: `parent_totals[p] == sum(children at R=8 in original)` exactly.
- For each child cell c at R=8: `round_tripped[c] == original[c]` within 1e-9 relative tolerance (allows for inequalities among original siblings to wash out under uniform-split round-trip).
- Note: per spec edge cases, if original siblings are unequal, the round-trip is **not** a per-cell identity (the parent total is preserved, the per-cell distribution is uniformized). The test asserts the parent identity is exact; the per-cell identity holds only when original siblings were uniform.

---

## Marxist Sign / Monotonicity Invariants

### Contract FR-017 / SC-013 — Proportional (c, v) Scaling

**Test**: `tests/property/test_proportional_scaling.py::test_total_value_scales_with_c_v`

**Given**: A scenario with productive entities having non-zero c, v, s.
**When**:
1. Baseline: read every entity's `(c, v, s)`.
2. Build `world'` with c → 2c, v → 2v, and s rescaled so that `s/v` is unchanged (so s also doubles, since v doubles).
3. Read `(c', v', s')`.
**Then**:
- For each entity:
  - `c' + v' + s' == 2 × (c + v + s)` within 1e-12 relative.
  - `s'/(c'+v') == s/(c+v)` within 1e-12 (profit rate unchanged).
  - `c'/v' == c/v` within 1e-12 (OCC unchanged).
  - `s'/v' == s/v` within 1e-12 (exploitation rate unchanged).

### Contract FR-018 / SC-014 — OCC Monotonicity

**Test**: `tests/integration/economics/test_occ_monotonicity.py::test_occ_monotone_in_c_and_in_v`

**Given**: A productive entity with baseline (c, v).
**When**:
1. Construct 11 evenly-spaced c values: `c_i = c * (0.5 + 0.1*i)` for i ∈ [0..10] (spans ±50%).
2. For each c_i, hold v fixed, compute OCC_i = c_i / v.
3. Construct 11 evenly-spaced v values: `v_j = v * (0.5 + 0.1*j)`.
4. For each v_j, hold c fixed, compute OCC_j = c / v_j.
**Then**:
- `OCC_i` is strictly monotonically non-decreasing in i.
- `OCC_j` is strictly monotonically non-increasing in j.

### Contract FR-019 / SC-015 — Volume III Equalization Tendency

**Test**: `tests/integration/economics/test_volume_iii_equalization.py::test_inter_sectoral_variance_decreases`

**Given**: A scenario with ≥ 2 productive sectors, `equalization_alpha > 0` (capital migration active).
**When**:
1. If capital migration disabled: SKIP with "spec-060 FR-019: capital migration inactive".
2. Run 50 ticks, at each tick record `(tick, {sector: profit_rate}, variance(profit_rates))` into `ProfitRateVarianceTrace`.
3. Compute `var_early = mean(variance[0..10])`, `var_late = mean(variance[40..50])`.
**Then**:
- `var_late < var_early` (strict).
- Diagnostic on failure: report both values and percent reduction.

---

## Cross-Cutting Contracts

### Contract FR-009 — Performance

Every test in this bundle MUST satisfy:
- Per-test wall-clock < 10 s (US7-c long-run: < 60 s).
- Bundle total < 120 s (SC-006).
- Verified via `--durations` in `reports/test-results/{unit,int}/`.

### Contract FR-010 — Diagnostics

Every failing assertion MUST emit:
- The offending entity / aggregate identifier.
- The numerical magnitude of the violation (Δ, relative error).
- A `spec-060` reference (e.g., `"see spec-060 FR-XYZ"`).

### Contract FR-011 — No Behavioral Change

The bundle MUST NOT change `src/babylon/` behavior. Only permitted
production-side change: `src/babylon/config/h3_splitter.py` (FR-011
exception, R1).

### Contract FR-012 — Byte-Equality Preservation

After landing the bundle, `mise run sim:trace 200` MUST produce a CSV
byte-identical to the pre-merge baseline.

### Contract FR-020 — Hypothesis Determinism

All Hypothesis-driven tests MUST set `derandomize=true` (or equivalent
profile setting) so CI runs are reproducible.

### Contract FR-021 — Single Transformation Probe

The four transformation-gated tests (FR-005-redistribution, FR-006,
FR-007, FR-019) MUST all import `probe_transformation_mode` from
`tests/_helpers/invariants/transformation_mode.py`. No test may
re-implement the probe.

### Contract FR-022 — Pytest Marker

Every test in this bundle MUST be decorated with
`@pytest.mark.invariant`. The marker MUST be registered in
`pyproject.toml` under `[tool.pytest.ini_options].markers`.

---

## Contract Summary

| FR | SC | Test File | Contract Type |
|---|---|---|---|
| FR-001 | SC-001 | `test_numeraire_invariance.py` | property/metamorphic |
| FR-002 | SC-001 | `test_numeraire_invariance.py` | property (Hypothesis) |
| FR-003 | SC-002 | `test_melt_consistency.py` | integration |
| FR-004 | SC-002 | `test_melt_consistency.py` | skip behavior |
| FR-005 | SC-003 | `test_aggregate_equalities.py` | integration |
| FR-006 | SC-004 | `test_wage_occ_asymmetry.py` | metamorphic, gated |
| FR-007 | SC-005 | `test_productivity_shock_decoupling.py` | metamorphic, gated |
| FR-008 | — | (cross-cut) | gate behavior |
| FR-013 | SC-009 | `test_uuid_relabel_invariance.py` | metamorphic |
| FR-014 | SC-010 | `test_serialization_roundtrip.py` | round-trip |
| FR-015 | SC-011 | `test_markovian_step.py` | metamorphic |
| FR-016 | SC-012 | `test_h3_round_trip.py` | metamorphic |
| FR-017 | SC-013 | `test_proportional_scaling.py` | metamorphic + property |
| FR-018 | SC-014 | `test_occ_monotonicity.py` | sign/monotonicity |
| FR-019 | SC-015 | `test_volume_iii_equalization.py` | long-run, gated |
| FR-009..FR-012, FR-020..FR-022 | SC-006..SC-008 | (cross-cut) | meta-properties |
