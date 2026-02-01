# Quickstart: Fundamental Tensor Primitive

**Feature**: 011-fundamental-tensor-primitive
**Date**: 2026-02-01

## Overview

The Fundamental Tensor Primitive establishes `ValueTensor4x3` as the single source of truth for all economic data in Babylon. This guide shows how to use the tensor layer.

## Key Concepts

1. **TensorRegistry**: Cached container for all tensor data
2. **ValueTensor4x3**: 4×3 tensor (4 departments × 3 value components)
3. **LaborHours**: All values measured in labor-time, not currency
4. **NoDataSentinel**: Explicit marker for missing data

## Basic Usage

### Initialize the Registry

```python
from babylon.economics.tensor_registry import TensorRegistry
from babylon.economics.snlt import SNLTConfig

# Create registry with default SNLT (wage-proportional proxy)
registry = TensorRegistry()

# Or with custom SNLT factors
snlt = SNLTConfig(factors={2020: 0.95, 2021: 0.93}, default_factor=1.0)
registry = TensorRegistry(snlt_config=snlt)
```

### Load Data via Simulation (Recommended)

```python
from babylon.engine.simulation import Simulation

# Let simulation handle hydration internally
sim = Simulation.from_sqlite(
    fips_codes=["26163", "26125"],  # Wayne, Oakland counties
    year=2022,
)

# Access registry from simulation
registry = sim.tensor_registry
```

### Load Data Directly (Advanced)

```python
from babylon.economics.hydrator import MarxianHydrator
from babylon.economics.adapters import SQLAlchemyQCEWSource, InterpolatingBEASource
from babylon.economics.department_mapper import IndustryDepartmentMapper

# Set up data sources
qcew_source = SQLAlchemyQCEWSource(session)
bea_source = InterpolatingBEASource(session, max_delta=5)
dept_mapper = IndustryDepartmentMapper.from_yaml("config/department_mapping.yaml")

# Create hydrator and registry
hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)
registry = TensorRegistry()

# Load specific counties and years
registry.hydrate_counties(
    hydrator,
    fips_codes=["26163", "26125"],  # Wayne, Oakland counties
    years=[2020, 2021, 2022],
)

# Or load all counties in a state
registry.hydrate_state(hydrator, "26", years=[2020, 2021, 2022])  # Michigan
```

### Access Tensor Data

```python
# Get single county tensor (NO database query)
if tensor := registry.get("26163", 2022):
    print(f"Profit rate: {tensor.profit_rate}")
    print(f"Total value: {tensor.total_value} labor-hours")
    print(f"Exploitation rate: {tensor.exploitation_rate}")
else:
    print(f"No data: {tensor.reason}")
```

### Access Aggregates

```python
from babylon.economics.tensor_registry import GeoLevel

# State aggregate (computed lazily, cached)
if michigan := registry.get_aggregate(GeoLevel.STATE, "26", 2022):
    print(f"Michigan total value: {michigan.total_value}")

# National aggregate
if usa := registry.get_aggregate(GeoLevel.NATION, "US", 2022):
    print(f"US total value: {usa.total_value}")
```

## The 4×3 Structure

```
                c (constant)    v (variable)    s (surplus)
              ┌───────────────┬───────────────┬───────────────┐
Dept I       │ dead labor    │ wages         │ profit        │
(Means of    │ transferred   │ (living labor)│ (unpaid labor)│
Production)  │               │               │               │
              ├───────────────┼───────────────┼───────────────┤
Dept IIa     │               │               │               │
(Wage Goods) │               │               │               │
              ├───────────────┼───────────────┼───────────────┤
Dept IIb     │               │               │               │
(Luxuries)   │               │               │               │
              ├───────────────┼───────────────┼───────────────┤
Dept III     │               │               │               │
(Reproductive│               │               │               │
Labor)       │               │               │               │
              └───────────────┴───────────────┴───────────────┘
```

Access department data:

```python
tensor = registry.get("26163", 2022)
if tensor:
    # Access specific department
    print(f"Dept I constant capital: {tensor.dept_I.c}")
    print(f"Dept IIa wages: {tensor.dept_IIa.v}")
    print(f"Dept III surplus: {tensor.dept_III.s}")

    # Department-level ratios
    print(f"Dept I OCC: {tensor.dept_I.organic_composition}")
    print(f"Dept IIa exploitation: {tensor.dept_IIa.exploitation_rate}")
```

## Derived Values

Derived values are computed from the primitive tensor:

```python
tensor = registry.get("26163", 2022)
if tensor:
    # Aggregate ratios (from all departments)
    r = tensor.profit_rate          # s / (c + v)
    e = tensor.exploitation_rate    # s / v
    occ = tensor.organic_composition  # c / v

    # Shadow labor analysis (Dept III)
    shadow = tensor.shadow_subsidy   # Unmonetized reproductive labor
    g33 = tensor.visibility_g33      # Visibility metric

    # Imperial rent (can be negative)
    phi = tensor.imperial_rent       # v - total_value
    # Positive = core (receiving rent)
    # Negative = periphery (donating rent)
```

## Integration with Simulation

The simulation engine uses the tensor registry internally for all economic data access:

```python
from babylon.engine.simulation import Simulation

# Create simulation (initializes registry internally)
sim = Simulation.from_sqlite(
    fips_codes=["26163", "26125"],
    year=2022,
)

# Access registry for direct queries
registry = sim.tensor_registry

# Engine systems access registry for economic data
# (this happens automatically within simulation ticks)
tensor = registry.get(territory.fips, 2022)
if tensor:
    print(f"Profit rate: {tensor.profit_rate}")
```

## Integration with Visualization

```python
class HexagonRenderer:
    def __init__(self, registry: TensorRegistry):
        self._registry = registry

    def render(self, territory: TerritoryState) -> None:
        # Get tensor for territory (NO database query)
        tensor = self._registry.get(territory.fips, territory.year)

        if tensor:
            # Use tensor data for visualization
            color = profit_rate_to_color(tensor.profit_rate)
            tooltip = format_tensor(tensor)
        else:
            # Handle missing data
            color = NO_DATA_COLOR
            tooltip = f"No data: {tensor.reason}"
```

## Handling Missing Data

The `NoDataSentinel` pattern ensures clean handling:

```python
# Pattern 1: Walrus operator
if tensor := registry.get(fips, year):
    use(tensor)
else:
    handle_missing(tensor.reason)

# Pattern 2: Explicit check
result = registry.get(fips, year)
if result:
    tensor = result
    use(tensor)
else:
    sentinel = result
    log(f"Missing: {sentinel.reason}")

# Pattern 3: Guard clause
tensor = registry.get(fips, year)
if not tensor:
    return NoDataSentinel(fips, year, "Propagated from source")
# Continue with tensor...
```

## SNLT Conversion

By default, tensor values are **wage-proportional labor-time proxies**:

- Derived ratios (r, e, OCC) are **exact** (units cancel)
- Absolute magnitudes require SNLT calibration

To configure year-specific SNLT:

```python
from babylon.economics.snlt import SNLTConfig

# Productivity improved 5% from 2015 to 2020
snlt = SNLTConfig(
    factors={
        2015: 1.0,    # Base year
        2020: 0.95,   # 5% more productive
    },
    default_factor=1.0,
)

registry = TensorRegistry(snlt_config=snlt)
```

## Performance Notes

- **No database queries after hydration**: `get()` reads from cache only
- **Lazy aggregation**: State/nation totals computed on first request
- **LRU caching**: Aggregates evicted when memory limit reached
- **Target**: 100 counties × 10 years loads in <5 seconds

## Common Patterns

### Batch Processing

```python
# Efficient: Load once, query many
registry.hydrate(fips_codes, years)
for fips in fips_codes:
    for year in years:
        tensor = registry.get(fips, year)
        process(tensor)
```

### State Comparison

```python
# Compare two states
mi = registry.get_aggregate(GeoLevel.STATE, "26", 2022)
oh = registry.get_aggregate(GeoLevel.STATE, "39", 2022)

if mi and oh:
    print(f"MI exploitation rate: {mi.exploitation_rate}")
    print(f"OH exploitation rate: {oh.exploitation_rate}")
```

### Time Series

```python
# Track profit rate over time
years = registry.available_years("26163")
for year in sorted(years):
    if tensor := registry.get("26163", year):
        print(f"{year}: r = {tensor.profit_rate:.4f}")
```

## Testing & Debugging

### Manual Tensor Creation (For Tests)

```python
from babylon.economics.tensor import ValueTensor4x3, DepartmentRow

# Create tensor manually for testing
tensor = ValueTensor4x3(
    fips_code="26163",
    year=2022,
    dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
    dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
    dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
    dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
    naics_granularity=0.9,
    excluded_wages=0.0,
)

# Add to registry manually (bypasses hydrator)
registry = TensorRegistry()
registry.put("26163", 2022, tensor)
```

### Cache Diagnostics

```python
# Check cache status
info = registry.cache_info()
print(f"Counties loaded: {info['county_count']}")
print(f"Aggregate hits: {info['aggregate_hits']}")
print(f"Aggregate misses: {info['aggregate_misses']}")

# Clear caches (useful for testing)
registry.clear()
```
