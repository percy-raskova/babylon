# Quickstart: Capital Stock Dynamics

**Feature**: 012-capital-stock-dynamics
**Date**: 2026-02-01
**Phase**: 1 - Documentation

## Overview

This guide demonstrates how to compute capital stock (K) from constant capital flows (c) and calculate stock-based profit rates for TRPF analysis.

## Prerequisites

```python
from babylon.economics.tensor_registry import TensorRegistry, GeoLevel
from babylon.economics.capital_stock import CapitalStockCalculator
from babylon.economics.depreciation import DepreciationConfig
```

## Basic Usage

### 1. Initialize Components

```python
# Create tensor registry and hydrate with data
registry = TensorRegistry()
# ... hydrate registry via TensorHydrator or simulation startup ...

# Create capital stock calculator with default depreciation (δ = 0.07)
calculator = CapitalStockCalculator(registry)

# Or with custom depreciation rate
config = DepreciationConfig(rate=0.05)  # 5% depreciation
calculator = CapitalStockCalculator(registry, depreciation=config)
```

### 2. Compute Capital Stock for a County-Year

```python
# Get capital stock for Wayne County, 2022
K = calculator.get_K("26163", 2022)

if K:
    print(f"Capital stock K = {K:,.0f} labor-hours")
else:
    print(f"No data: {K.reason}")
```

### 3. Compute Time Series

```python
# Compute K for all available years
time_series = calculator.compute_time_series("26163", 2010, 2024)

for year, K in time_series.items():
    print(f"{year}: K = {K:,.0f}")
```

### 4. Get Derived Metrics

```python
# Get comprehensive metrics including stock-based profit rate
metrics = calculator.get_metrics("26163", 2022)

if metrics:
    print(f"Capital stock: K = {metrics.capital_stock:,.0f}")
    print(f"Stock-based profit rate: r = {metrics.profit_rate_stock:.4f}")
    print(f"Flow-based profit rate: r = {metrics.profit_rate_flow:.4f}")
    print(f"OCC: {metrics.organic_composition:.2f}")
    print(f"Exploitation rate: e = {metrics.exploitation_rate:.2f}")
```

## TRPF Analysis

### Validate Falling Profit Rate Trend

```python
import scipy.stats as stats

# Compute profit rate time series
fips = "26163"
time_series = calculator.compute_time_series(fips, 2010, 2024)
years = sorted(time_series.keys())
profit_rates = []

for year in years:
    metrics = calculator.get_metrics(fips, year)
    if metrics:
        profit_rates.append(metrics.profit_rate_stock)

# Test for secular decline (TRPF)
slope, intercept, r_value, p_value, std_err = stats.linregress(
    list(range(len(profit_rates))), profit_rates
)

print(f"Slope: {slope:.6f}")
print(f"p-value: {p_value:.4f}")

if slope < 0 and p_value < 0.05:
    print("TRPF validated: statistically significant declining trend")
else:
    print("TRPF not validated at p < 0.05")
```

### Sensitivity Analysis

```python
# Test TRPF robustness across depreciation rates
for rate in [0.05, 0.07, 0.10]:
    config = DepreciationConfig(rate=rate)
    calc = CapitalStockCalculator(registry, depreciation=config)

    time_series = calc.compute_time_series(fips, 2010, 2024)
    years = sorted(time_series.keys())
    rates = [calc.get_metrics(fips, y).profit_rate_stock for y in years]

    slope, _, _, p_value, _ = stats.linregress(range(len(rates)), rates)

    print(f"δ = {rate}: slope = {slope:.6f}, p = {p_value:.4f}")
```

## Geographic Aggregation

```python
# State-level capital stock
michigan_K = calculator.get_K_aggregate(GeoLevel.STATE, "26", 2022)
if michigan_K:
    print(f"Michigan capital stock: {michigan_K:,.0f}")

# National capital stock
us_K = calculator.get_K_aggregate(GeoLevel.NATION, "US", 2022)
if us_K:
    print(f"US capital stock: {us_K:,.0f}")
```

## Detroit Validation Case

Per TVT political-theoretical exposition, compare Wayne (peripheral) vs Oakland (core):

```python
# Wayne County - domestic periphery
wayne_metrics = calculator.get_metrics("26163", 2022)

# Oakland County - domestic core
oakland_metrics = calculator.get_metrics("26125", 2022)

if wayne_metrics and oakland_metrics:
    print(f"Wayne OCC: {wayne_metrics.organic_composition:.2f}")
    print(f"Oakland OCC: {oakland_metrics.organic_composition:.2f}")

    # Validate: core should have higher OCC
    if oakland_metrics.organic_composition > wayne_metrics.organic_composition:
        print("✓ Core-periphery OCC differential validated")
    else:
        print("✗ Unexpected: periphery has higher OCC than core")
```

## Integration with Simulation Engine

```python
from babylon.engine.simulation_engine import SimulationEngine

# Recommended: Hydrate tensors before simulation
registry = TensorRegistry()
registry.hydrate_counties(hydrator, fips_codes, years)

# Create calculator
calculator = CapitalStockCalculator(registry)

# Pass to simulation engine (optional, for TRPF tracking)
engine = SimulationEngine(
    registry=registry,
    capital_stock_calculator=calculator,
)
```

## Export for Analysis

```python
import pandas as pd

# Export metrics to DataFrame
fips_codes = ["26163", "26125"]  # Wayne, Oakland
years = range(2010, 2025)

data = []
for fips in fips_codes:
    for year in years:
        metrics = calculator.get_metrics(fips, year)
        if metrics:
            data.append(metrics.to_dict())

df = pd.DataFrame(data)
df.to_csv("trpf_analysis.csv", index=False)
```

## Formulas Reference

| Metric | Formula | Notes |
|--------|---------|-------|
| Initial K | K_0 = c_0 / δ | Steady-state assumption |
| K evolution | K[t] = K[t-1] × (1-δ) + c[t-1] | Perpetual inventory method |
| Stock profit rate | r = s / (K + v) | TVT Section 3.6 |
| Flow profit rate | r = s / (c + v) | Existing tensor property |
| OCC | c / v | Organic composition |
| Exploitation rate | e = s / v | Rate of surplus extraction |

## Common Issues

### "Year outside data range"

Capital stock requires continuous time series from 2010. Years before 2010 or after 2024 return NoDataSentinel.

### Missing intermediate years

If years are missing in the time series, they are skipped. K continues from the last available year. This is logged as a warning.

### Negative K values

Theoretically impossible but can occur with extreme depreciation. Values are clamped to 0.0.

### Division by zero

If (K + v) = 0, profit_rate_stock returns `float('inf')`. This matches existing tensor behavior.
