# Data Model: 020-detroit-vertical-slice

**Date**: 2026-02-23

## Entities

### Modified Entities

#### ServiceContainer (existing, modified)

**File**: `src/babylon/engine/services.py`

New field added:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tensor_registry` | `Any` | `None` | TensorRegistry instance for tensor data lookup |

The `create()` classmethod gains a `tensor_registry: Any = None` keyword argument.

#### Simulation (existing, modified)

**File**: `src/babylon/engine/simulation.py`

New instance attribute:

| Attribute | Type | Description |
|-----------|------|-------------|
| `_calculator_overrides` | `dict[str, Any]` | Pre-built calculator instances + tensor_registry for injection into step() |

`from_sqlite()` gains `years: Sequence[int] | None = None` parameter. When provided, hydrates TensorRegistry for all specified years.

### New Entities

#### CalculatorFactory (new module)

**File**: `src/babylon/economics/factory.py`

A factory function (not a class) that wires all calculator dependencies:

```
create_economics_services(
    session_factory: Callable[[], Session],
    tensor_registry: TensorRegistry,
) -> dict[str, Any]
```

Returns a dict with keys matching ServiceContainer field names:
- `melt_calculator`
- `basket_calculator`
- `gamma_calculator`
- `capital_calculator`
- `throughput_calculator`
- `transition_engine`
- `imperial_rent_calculator`
- `tensor_registry`

#### SQLiteBEANationalGDPSource (new adapter)

**File**: `src/babylon/economics/melt/adapters.py`

Implements `BEADataSource` protocol. Aggregates `fact_bea_national_industry.value_added_millions` by year.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_gdp` | `(year: int) -> float \| None` | SUM(value_added_millions) * 1e6 for given year |

Constructor: `(session_factory: Callable[[], Session])`

#### SQLiteQCEWNationalEmploymentSource (new adapter)

**File**: `src/babylon/economics/melt/adapters.py`

Implements `QCEWDataSource` protocol. Aggregates `fact_qcew_annual.employment` nationally.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_national_employment` | `(year: int) -> int \| None` | SUM(employment) across all counties for annual records |

Constructor: `(session_factory: Callable[[], Session])`

#### MVPUnpaidCareHoursSource (new adapter)

**File**: `src/babylon/economics/gamma/adapters.py`

Implements `UnpaidCareHoursSource` protocol. Hardcoded ATUS estimates (same pattern as `HardcodedNationalDispossessionSource`).

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_unpaid_care_hours` | `(year: int) -> float \| None` | Returns hardcoded ATUS estimates by year |

Constructor: no parameters.

### Time Series Record (new data structure)

Emitted by `Simulation.get_time_series()`. One record per county per year.

| Field | Type | Description |
|-------|------|-------------|
| `year` | `int` | Simulation year |
| `fips` | `str` | 5-digit FIPS code |
| `class_distribution` | `dict[str, float]` | Class shares (LA, proletariat, lumpen, bourgeoisie) |
| `profit_rate` | `float` | r for this county-year |
| `phi_hour` | `float` | Imperial rent per hour |
| `throughput_position` | `float \| None` | pi, if computable |
| `tau` | `float` | National MELT for this year |
| `data_source` | `str` | "tensor" or "carry-forward" or "fallback" |

## Relationships

```
Simulation --creates--> CalculatorFactory --instantiates--> 7 Calculators
Simulation --stores---> TensorRegistry --cached-by--> (fips, year)
step() --creates--> ServiceContainer --injects--> calculators + tensor_registry
ServiceContainer --passed-to--> TickDynamicsSystem, ProductionSystem, etc.
ProductionSystem --reads--> ServiceContainer.tensor_registry --lookups--> ValueTensor4x3
TickDynamicsSystem --reads--> ServiceContainer.melt_calculator --computes--> tau, gamma, etc.
```

## State Transitions

No new state machines. The wiring is stateless — calculators are instantiated once at simulation creation and reused across all ticks.

The TensorRegistry year lookup transitions implicitly:
- `tick 0..51` → year 2015 tensor data
- `tick 52..103` → year 2016 tensor data (or carry-forward if missing)
- etc.
