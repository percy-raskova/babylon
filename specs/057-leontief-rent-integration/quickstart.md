# Quickstart: End-to-End Leontief Imperial Rent Integration

**Spec**: 057
**Audience**: Contributor (Claude or human) implementing or verifying Spec 057 locally.
**Prerequisites**: `dev` branch up to and including the merge of Spec 058 and the test-reports infrastructure (commit `f852f46a` or later on `057-leontief-rent-integration`).

This is the verification recipe that runs after each commit on this branch and at the end of `/speckit.implement`. Every block is a copy-pastable command.

---

## Phase 0 — Baseline before any code change

```bash
# 1. Confirm we're on the right branch
git branch --show-current
# Expected: 057-leontief-rent-integration

# 2. Confirm Spec 058 infrastructure is in place
test -f src/babylon/core/protocol_kit.py && echo "✓ protocol_kit present"
test -f src/babylon/economics/tensor_hierarchy/mappings/_models.py && echo "✓ BEAMappings present"
test -d src/babylon/economics/tick/system && echo "✓ tick/system package present"
test -d src/babylon/config/defines && echo "✓ defines/ package present"
test -d src/babylon/models/enums && echo "✓ enums/ package present"

# 3. Confirm Spec 057 quarantine markers ARE still in place (we will UNSKIP them as part of FR-009)
grep -rln "Blocked on spec 057-leontief" src/ tests/ | wc -l
# Expected: ≥9

# 4. Establish baseline test counts
mise run test:unit
mise run test:summary
# Expected: ~9000+ passed / 186 skipped / 1 xfailed / 0 failures
# Capture as the "before" tally.
```

---

## Phase 1 — Implement the new entities (TDD red → green per user-story phase)

The order below matches the user-story priority and minimizes inter-commit dependency. Each block is one or two commits.

### Commit 1 — `LeontiefRentDefines` + `CalibrationWarning` event family (foundational)

```bash
# Add LeontiefRentDefines to src/babylon/config/defines/economy_basic.py
# Add 3 new EconomicEvent subclasses to src/babylon/models/events.py
# Add 3 new EventType enum entries to src/babylon/models/events.py

# Verify with focused tests
poetry run pytest tests/unit/models/test_events.py -v -k calibration
# Expected: 5+ new tests pass (per contracts/calibration_warning.md AC1-AC5)

# Commit
git add src/babylon/config/defines/economy_basic.py src/babylon/models/events.py tests/unit/models/test_events.py
git commit -m "feat(spec-057): LeontiefRentDefines + CalibrationWarning event family"
```

### Commit 2 — `DefaultPeripheryLaborCoefficientsSource` (US2 / P1)

```bash
# Create src/babylon/economics/tensor_hierarchy/leontief_rent/{__init__,periphery_labor_coefficients}.py
# Tests: tests/unit/economics/tensor_hierarchy/leontief_rent/test_periphery_labor_coefficients_source.py

poetry run pytest tests/unit/economics/tensor_hierarchy/leontief_rent/test_periphery_labor_coefficients_source.py -v
# Expected: AC1-AC5 from contracts/periphery_labor_coefficients_source.md pass

git commit -m "feat(spec-057): DefaultPeripheryLaborCoefficientsSource (US2 — PWT v10.x)"
```

### Commit 3 — `DefaultFinalDemandSource` (US3 / P1)

```bash
# Create src/babylon/economics/tensor_hierarchy/leontief_rent/final_demand.py
# Tests: tests/unit/economics/tensor_hierarchy/leontief_rent/test_final_demand_source.py

poetry run pytest tests/unit/economics/tensor_hierarchy/leontief_rent/test_final_demand_source.py -v
# Expected: AC1-AC6 from contracts/final_demand_source.md pass

git commit -m "feat(spec-057): DefaultFinalDemandSource (US3 — BEA Use Table)"
```

### Commit 4 — `IndustryToCountyAllocator` (US4 / P2)

```bash
# Create src/babylon/economics/tensor_hierarchy/leontief_rent/industry_to_county_allocator.py
# Tests: tests/unit/economics/tensor_hierarchy/leontief_rent/test_industry_to_county_allocator.py

poetry run pytest tests/unit/economics/tensor_hierarchy/leontief_rent/test_industry_to_county_allocator.py -v
# Expected: AC1-AC7 from contracts/industry_to_county_allocator.md pass (7 tests including carry-forward)

git commit -m "feat(spec-057): IndustryToCountyAllocator with 5-year carry-forward (US4)"
```

### Commit 5 — `imperial_rent.compute()` pipeline + `TickDynamicsSystem` delegation (US1 / P1)

```bash
# Create src/babylon/economics/tick/system/imperial_rent.py (≤400 LOC)
# Edit src/babylon/economics/tick/system/__init__.py — _compute_imperial_rent becomes 3-line delegation
# Edit src/babylon/economics/factory.py — register 4 new sources via SourceRegistry.builtin_economics()
# Edit src/babylon/engine/services.py — add 4 new optional fields
# Tests: tests/integration/economics/tick/test_imperial_rent_pipeline.py

poetry run pytest tests/integration/economics/tick/test_imperial_rent_pipeline.py -v
poetry run pytest tests/integration/economics/tick/test_facade_behavioral_fence.py -v
# Expected: AC1-AC10 from contracts/imperial_rent_pipeline.md pass; behavioral fence intact

git commit -m "feat(spec-057): imperial_rent.compute() pipeline + ServiceContainer wiring (US1)"
```

### Commit 6 — Performance smoke test (R3)

```bash
# Tests: tests/integration/economics/tick/test_imperial_rent_perf.py

poetry run pytest tests/integration/economics/tick/test_imperial_rent_perf.py -v
# Expected: AC11 (warm cache ≤100ms mean over 100 ticks) + AC12 (cold cache ≤250ms) pass

git commit -m "test(spec-057): performance smoke test for imperial-rent pipeline (R3)"
```

### Commit 7 — Orphan-test cleanup (US5 / P3, FR-009)

```bash
# UNSKIP the spec-057 quarantine markers (per FR-009)
# Files affected (per spec.md "Out of Scope" cross-reference):
#   tests/unit/engine/test_services.py
#   tests/unit/engine/test_formula_registry.py (3 markers)
#   tests/unit/economics/test_factory.py (2 markers)
#   tests/unit/economics/test_hydrator_mutants.py
#   tests/unit/economics/melt/test_class_position.py
#   tests/integration/economics/conftest.py
#   tests/integration/system/test_phase1_blueprint.py

# For each: review the test, either UNSKIP (if behavior is now correct) or DELETE (if it tested the removed per-worker calculator API)
# Updates ServiceContainer assertions to include 4 new fields

# Verify nothing else regresses
mise run test:unit && mise run test:int
mise run test:summary
# Expected: tally is now 9000+ passed / ~177 skipped (9 quarantines lifted) / 1 xfailed / 0 failures

git commit -m "test(spec-057): unquarantine spec-057 markers + delete orphan per-worker tests (FR-009)"
```

---

## Phase 2 — End-to-end verification

### Wayne County baseline integration

```bash
# Run a single tick of the Wayne County baseline scenario
poetry run python -c "
from babylon.scenarios.wayne_baseline import build_scenario  # exact import path TBD at impl time
from babylon.engine.simulation import Simulation
sim = Simulation(build_scenario())
sim.run(num_ticks=1)
phi_hours = {fips: county.phi_hour for fips, county in sim.county_states.items()}
nonzero = [(fips, p) for fips, p in phi_hours.items() if p > 1e-6]
print(f'Counties with non-zero phi_hour: {len(nonzero)} / {len(phi_hours)}')
print(f'Max phi_hour: {max(phi_hours.values()):.4f}')
print(f'Min phi_hour: {min(phi_hours.values()):.4f}')
print(f'Mean (non-zero): {sum(p for _, p in nonzero) / len(nonzero):.4f}' if nonzero else 'N/A')
"
# Expected (per SC-002): at least one county has phi_hour > 1e-6
```

### Reproducibility check

```bash
# Run two consecutive single-tick simulations, diff phi_hour distributions
poetry run python -c "
from babylon.scenarios.wayne_baseline import build_scenario
from babylon.engine.simulation import Simulation

def run():
    sim = Simulation(build_scenario(seed=42))
    sim.run(num_ticks=1)
    return tuple(sorted((fips, c.phi_hour) for fips, c in sim.county_states.items()))

a, b = run(), run()
assert a == b, 'Reproducibility failure!'
print('✓ Reproducibility verified across two consecutive runs (SC-002)')
"
```

### Calibration order-of-magnitude check (SC-004)

```bash
# Compute national-total phi_hour for tick year 2015, compare against Hickel 2022 ($2.8T)
poetry run python -c "
from babylon.scenarios.wayne_baseline import build_scenario
from babylon.engine.simulation import Simulation

sim = Simulation(build_scenario(year=2015))
sim.run(num_ticks=1)

HOURS_PER_YEAR = 2080
total_drain = sum(
    county.phi_hour * county.employment_total * HOURS_PER_YEAR
    for county in sim.county_states.values()
    if county.phi_hour > 0
)
hickel_2015 = 2.8e12  # \$2.8T
ratio = total_drain / hickel_2015
print(f'Computed national drain (2015): \${total_drain / 1e9:.1f}B')
print(f'Hickel 2022 estimate:           \${hickel_2015 / 1e9:.1f}B')
print(f'Ratio: {ratio:.3f} (acceptable: 0.1 to 10 = order-of-magnitude per SC-004)')
assert 0.1 < ratio < 10, f'OOM check failed: ratio={ratio:.3f}'
print('✓ Order-of-magnitude check passed (SC-004)')
"
```

### Calibration warning observability

```bash
# Confirm CalibrationWarning events flow through the EventBus during a real tick
poetry run python -c "
from babylon.scenarios.wayne_baseline import build_scenario
from babylon.engine.simulation import Simulation

sim = Simulation(build_scenario(year=2015))
sim.run(num_ticks=1)
history = sim.services.event_bus.get_history()
calib = [e for e in history if e.type.startswith('calibration_warning.')]
print(f'Calibration warnings emitted in 1 tick: {len(calib)}')
for e in calib[:5]:
    print(f'  {e.type}: {e.payload}')
"
# Expected: small number of QcewCarryForward events (counties with mid-year QCEW gaps)
# May see PhiHourOutlier events if phi_hour exceeds defaults (±\$1000/hr)
# AxiomViolation events should be rare with PWT v10.x
```

---

## Phase 3 — Constitution gate verification

```bash
# III.4 Data Catalog — confirm PWT is the only periphery-wage source referenced (no new constitutional addition)
grep -inE "periphery|hickel|sullivan|zoomka" .specify/memory/data-catalog.yaml
# Expected: no matches — PWT itself is listed (id: PWT) and serves as the periphery-wage source via aggregation

# III.7 Determinism Hash — behavioral fence test passes
poetry run pytest tests/integration/economics/tick/test_facade_behavioral_fence.py -v
# Expected: 0 failures (Spec 058 / FR-007 invariant preserved)

# III.1 No Magic Constants — verify the only tunable lifted to defines
grep -nE "qcew_carry_forward_max_years|phi_hour_outlier_threshold" src/babylon/config/defines/
# Expected: definitions in economy_basic.py
grep -nE "= 5\b|= 1000\b|= -1000\b" src/babylon/economics/tick/system/imperial_rent.py
# Expected: no magic constants in the pipeline body — all read from services.defines.economy.leontief_rent.*
```

---

## Phase 4 — Final regression + reports

```bash
# Run the full non-AI suite
mise run test:all
mise run test:summary

# Compare against the Phase 0 baseline (captured before any code change)
# Expected:
#   - passed count: +N (where N = new tests added in commits 1-7)
#   - skipped count: ~177 (down from 186 — 9 spec-057 quarantines lifted)
#   - failures: 0
#   - xfailed: 1 (the pre-existing test_per_system_coverage_complete from spec 054)

# Coverage check
mise run test:cov
mise run test:show
# Browse to the generated HTML report; confirm new modules have ≥90% line coverage
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ValidationError: phi_hour must be ≥ 0` | Calculator clamp removed or negative value reached `CountyEconomicState` | Re-verify `production_chain_rent.py:181` clamp is in place; check the source layer is NOT clamping (per research.md §R5) |
| `ValueError: BEA industry list mismatch for year 2015...` | One source's industry list out of sync with another for that year | Re-run Spec 025 ingestion for the misaligned year; confirm the BEA Summary vintage matches across all 3 source tables |
| Test `test_wayne_baseline_nonzero_phi_hour` fails (all phi_hour zero) | One of the 4 sources returned `NoDataSentinel` for the tick year — `imperial_rent.compute()` fell back to stub | Check `event_bus.get_history()` for `QcewCarryForwardEvent(county_fips="*", look_back_distance=-1)` — the event payload identifies which source had no data |
| `test_imperial_rent_perf_warm_cache` fails (>100ms) | Cache miss happening every tick; check `CachedSource[T]` is wired correctly and `cache_negative_results=True` | Verify `super().__init__()` is called in `Default*` constructors; verify `_resolve(year)` is the entry point, not `_fetch(year)` directly |
| Calibration check fails — OOM ratio > 10 | Periphery-wage source returning unrealistic ratios; check PWT extraction | Inspect `metadata.calibration_anchor`; if `industry_disaggregation == "None"`, the v1 uniform-broadcast assumption may be inflating drain — see research.md §R1 v1 simplification caveats |
| Calibration check fails — OOM ratio < 0.1 | Periphery wages too close to core wages; check PWT data was loaded for the right year | Re-run PWT ingestion; verify `wage_ratios` mean is in expected range (~3-10 for periphery vs core) |
