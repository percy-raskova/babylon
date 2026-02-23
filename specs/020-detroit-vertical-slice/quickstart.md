# Quickstart: 020-detroit-vertical-slice

**Date**: 2026-02-23

## Prerequisites

- Poetry environment set up (`poetry install`)
- marxist-data-3NF.sqlite populated with QCEW data (`mise run data:db-init`)
- All existing tests passing (`mise run check`)

## After Implementation

### Run Single-Year Wired Simulation

```python
from babylon.engine.simulation import Simulation

sim = Simulation.from_sqlite(["26163", "26125"], year=2022, years=[2022])
sim.step()  # One tick — TickDynamicsSystem now executes full pipeline

# Verify calculators are wired
assert sim._services is not None  # ServiceContainer exists
# Verify time series extraction
ts = sim.get_time_series()
print(ts)  # Should show year=2022 records for Wayne and Oakland
```

### Run Multi-Year Detroit Time Series

```python
from babylon.engine.simulation import Simulation

# Create simulation spanning available QCEW years
sim = Simulation.from_sqlite(
    ["26163", "26125"],
    year=2015,
    years=list(range(2015, 2024)),  # 9 years of QCEW data
)

# Run 468 ticks (9 years x 52 weeks)
for _ in range(468):
    sim.step()

# Extract time series
results = sim.get_time_series()
for r in results:
    print(f"{r['year']} {r['fips']} r={r['profit_rate']:.4f} phi={r['phi_hour']:.2f}")
```

### Run Validation Harness

```bash
# After US4 is implemented:
mise run sim:validate-detroit
# Outputs comparison table: model vs Census 2023 class distributions
```

## Key Files Modified

| File | Change |
|------|--------|
| `src/babylon/engine/services.py` | Add `tensor_registry` field |
| `src/babylon/engine/simulation_engine.py` | Add `calculator_overrides` param to `step()` |
| `src/babylon/engine/simulation.py` | Wire factory in `from_sqlite()`, add `get_time_series()` |
| `src/babylon/engine/systems/production.py` | Read tensor data instead of `base_labor_power` |
| `src/babylon/economics/factory.py` | NEW: Calculator factory function |
| `src/babylon/economics/melt/adapters.py` | NEW: BEA/QCEW national adapters |
| `src/babylon/economics/gamma/adapters.py` | Add MVPUnpaidCareHoursSource |

## Verification

```bash
# Unit tests
mise run test:unit

# Integration test for wiring
poetry run pytest tests/integration/economics/ -k "detroit" -v

# Full CI gate
mise run check
```
