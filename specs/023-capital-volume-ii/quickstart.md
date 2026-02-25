# Quickstart: Capital Volume II Integration

**Feature**: 023-capital-volume-ii
**Branch**: `023-capital-volume-ii`
**Date**: 2026-02-25

## What This Feature Adds

Capital Volume II adds **circulation dynamics** to the simulation. Where Volume I (existing) captures how much surplus value is extracted per production cycle, Volume II captures:

1. **How fast** capital completes the M-C-P-C'-M' circuit (turnover time)
2. **What form** capital currently occupies (money, productive, commodity)
3. **Whether departments exchange proportionally** for reproduction (I(v+s) = IIc)
4. **Whether produced commodities can actually be sold** (realization crisis)

## Module Structure

```
src/babylon/economics/circulation/
├── __init__.py              # Package exports with __all__
├── types.py                 # All frozen Pydantic models (CircuitState, TurnoverProfile, etc.)
├── circuit.py               # Circuit state transitions (M→C→P→C'→M')
├── turnover.py              # Turnover time computation, annual surplus value
├── fixed_circulating.py     # Fixed/circulating capital decomposition, depreciation fund
├── reproduction.py          # Reproduction schema balance conditions
├── inventory.py             # Inventory tracking, realization crisis detection
├── costs.py                 # Circulation costs classification (productive/unproductive)
├── crisis.py                # Integrated circulation crisis assessment
└── defaults.py              # Default turnover profiles by NAICS sector

tests/unit/economics/circulation/
├── conftest.py              # Test fixtures and factories
├── test_types.py            # Model validation and computed fields
├── test_circuit.py          # Circuit state transition tests
├── test_turnover.py         # Turnover time and annual surplus value
├── test_fixed_circulating.py # Depreciation and decomposition
├── test_reproduction.py     # Reproduction schema checks
├── test_inventory.py        # Inventory diagnosis and realization crisis
├── test_costs.py            # Circulation cost classification
└── test_crisis.py           # Integrated crisis assessment
```

## Key Patterns

### Creating a CircuitState

```python
from babylon.economics.circulation.types import CircuitState, CapitalForm
from babylon.models.types import Currency

state = CircuitState(
    fips_code="26163",
    year=2022,
    money_capital=Currency(30.0),
    productive_capital=Currency(50.0),
    commodity_capital=Currency(20.0),
    fixed_capital=Currency(35.0),
    circulating_capital=Currency(15.0),
)

# Diagnostics (computed fields)
state.total_capital      # Currency(100.0)
state.liquidity_ratio    # 0.3
state.commodity_overhang # 0.2
```

### Computing Annual Surplus Value

```python
from babylon.economics.circulation.turnover import compute_annual_surplus_value
from babylon.models.types import Currency

result = compute_annual_surplus_value(
    variable_capital=Currency(50.0),
    surplus_per_cycle=Currency(50.0),  # s/v = 100%
    turnover_time_days=60,            # ~6 turnovers/year
)

result.rate_of_surplus_value          # 1.0 (100%)
result.turnovers_per_year             # 6.083
result.annual_rate_of_surplus_value   # 6.083 (608.3%)
```

### Checking Reproduction Conditions

```python
from babylon.economics.circulation.reproduction import (
    check_simple_reproduction,
    check_extended_reproduction,
)
from babylon.economics.tensor import DepartmentRow
from babylon.models.types import LaborHours

dept_i = DepartmentRow(c=LaborHours(50), v=LaborHours(30), s=LaborHours(20))
dept_ii = DepartmentRow(c=LaborHours(50), v=LaborHours(40), s=LaborHours(10))

balance = check_simple_reproduction(dept_i, dept_ii)
balance.condition_met   # True — I(v+s)=50 = IIc=50
balance.gap             # 0.0
```

### Detecting Realization Crisis

```python
from babylon.economics.circulation.inventory import detect_realization_crisis

crisis = detect_realization_crisis(
    inventory_trend=last_4_quarters,   # list[InventoryState]
    production_trend=last_4_outputs,   # list[Currency]
)
# Returns True if finished goods rising + production flat/falling
```

## Integration Points

### With Existing TickDynamicsSystem

The circulation module integrates as a new step in the annual pipeline:

1. After step 4 (imperial rent computation)
2. Before step 5 (crisis triggers)

The circulation step:
- Reads `ValueTensor4x3` from `TensorRegistry` for department data
- Reads `CapitalStockCalculator.get_K()` for capital stock
- Computes `CircuitState`, `InventoryState`, `DepreciationFundState`
- Runs reproduction schema checks and crisis assessment
- Writes results to `CountyEconomicState.circulation_state`
- Graph bridge serializes to `tick_` prefixed territory node attributes

### With Existing Crisis System (Feature 018)

Volume II crisis runs **alongside** TRPF crisis, not replacing it:

```
CountyEconomicState
├── crisis_state: CrisisState              # TRPF (Feature 018)
├── bifurcation_risk: BifurcationRiskMetric # Political trajectory
└── circulation_state: CirculationCrisisState  # Volume II (NEW)
```

Both signals are available to downstream consumers (narrative, UI, endgame detection).

## Running Tests

```bash
# All circulation tests
poetry run pytest tests/unit/economics/circulation/ -v

# Type checking
poetry run mypy src/babylon/economics/circulation/ --strict

# Specific module
poetry run pytest tests/unit/economics/circulation/test_turnover.py -v
```

## Dependencies

- **Existing**: ValueTensor4x3, DepartmentRow, CapitalStockCalculator, DepreciationConfig, CountyEconomicState, CrisisState
- **New external**: None (pure Python + Pydantic)
- **Data sources**: BEA Fixed Asset Tables (ratios), Census M3 (inventory-to-sales) — hardcoded defaults initially, data loader Protocol for future injection
