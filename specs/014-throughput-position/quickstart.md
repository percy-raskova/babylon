# Quickstart: Throughput Position and Domestic Value Geography

**Feature**: 014-throughput-position
**Date**: 2026-02-02
**Status**: Phase 1 (Planning Complete)

## Overview

The throughput position module analyzes domestic value geography within the US - understanding how wages relate to **throughput** (accumulated value flow) rather than local value creation.

**Key Insight**: Within a single currency zone, wages track THROUGHPUT, not value creation. A retail worker in Manhattan handles enormous throughput but captures little (low λ), while an extraction worker in Appalachia creates value but sees little flow through (low π).

## Core Concepts

### Throughput Intensity (τ_through)

The amount of accumulated value flowing through a location per hour of local labor.

```python
τ_through[fips] = GDP[fips] / (employment[fips] × 2080)
```

**This is NOT a local MELT** - it measures throughput, not value creation.

### Throughput Position (π)

A county's throughput intensity relative to the national average.

```python
π[fips] = τ_through[fips] / τ_national
```

- **π > 1.0**: Coordination chokepoint (value flows through)
- **π < 1.0**: Value creation/export node (value flows out)

### Supply Chain Depth (D)

Employment-weighted average position in the supply chain funnel.

```python
D[fips] = Σ(employment[naics] × depth[naics]) / Σ employment[fips]
```

Scale: 0 (extraction) to 5 (finance)

### Wage Share (λ)

The fraction of throughput captured as wages (institutional variable).

```python
W = λ × τ_through
```

Retail workers have high τ_through but λ ≈ 0.05. Longshoremen have high τ_through AND high λ (union power).

## Usage Example

```python
from babylon.economics.throughput import (
    DefaultThroughputCalculator,
    DefaultSupplyChainAnalyzer,
    NAICS_DEPTH_MAPPING,
)
from babylon.economics.melt import DefaultMELTCalculator

# Initialize with data sources
melt_calculator = DefaultMELTCalculator(bea_source, qcew_source)
supply_chain_analyzer = DefaultSupplyChainAnalyzer(county_qcew_source)
throughput_calculator = DefaultThroughputCalculator(
    county_gdp_source, county_qcew_source, supply_chain_analyzer, melt_calculator
)

# Compute throughput position for Wayne County (Detroit)
wayne_fips = "26163"
year = 2022

metrics = throughput_calculator.compute_metrics(wayne_fips, year)
print(f"Wayne County τ_through: ${metrics.tau_through:.2f}/hour")
print(f"Wayne County π: {metrics.pi:.2f}")
print(f"Wayne County D: {metrics.supply_chain_depth:.1f}")

# Compare with Oakland County (suburban Detroit)
oakland_fips = "26125"
oakland_metrics = throughput_calculator.compute_metrics(oakland_fips, year)
print(f"\nOakland County τ_through: ${oakland_metrics.tau_through:.2f}/hour")
print(f"Oakland County π: {oakland_metrics.pi:.2f}")
print(f"Oakland County D: {oakland_metrics.supply_chain_depth:.1f}")

# Expected: Oakland π > Wayne π (suburban coordination > urban manufacturing)
```

## NAICS Depth Mapping

The supply chain depth mapping is a frozen constant:

```python
from babylon.economics.throughput import NAICS_DEPTH_MAPPING

# Extraction sectors (depth 0)
print(NAICS_DEPTH_MAPPING["21"])  # Mining: 0.0
print(NAICS_DEPTH_MAPPING["11"])  # Agriculture: 0.0

# Transformation (depth 1-2)
print(NAICS_DEPTH_MAPPING["31"])  # Manufacturing: 1.5

# Coordination (depth 3-5)
print(NAICS_DEPTH_MAPPING["52"])  # Finance: 5.0
print(NAICS_DEPTH_MAPPING["55"])  # Management: 5.0
```

## Wage Share Proxy

Compute the wage share proxy for specific industries:

```python
# Retail wage share (the "Walmart effect")
# Note: QCEW uses combined NAICS codes (e.g., "44-45" for retail/wholesale)
retail_lambda = supply_chain_analyzer.compute_wage_share_proxy(
    fips="26163", naics="44-45", year=2022
)
print(f"Retail λ_proxy: {retail_lambda.lambda_proxy:.2f}")  # ~0.08

# Finance wage share
finance_lambda = supply_chain_analyzer.compute_wage_share_proxy(
    fips="26163", naics="52", year=2022
)
print(f"Finance λ_proxy: {finance_lambda.lambda_proxy:.2f}")  # ~0.35
```

## Integration with Feature 013

This feature extends Feature 013 (MELT and Basket Visibility) with domestic geography:

```python
from babylon.economics.melt import (
    DefaultMELTCalculator,
    DefaultClassPositionClassifier,
)
from babylon.economics.throughput import DefaultThroughputCalculator

# Feature 013: International value transfer
melt_calc = DefaultMELTCalculator(bea_source, qcew_source)
tau_national = melt_calc.get_melt(2022)  # National MELT ~$65/hour

# Feature 014: Domestic geography
supply_chain = DefaultSupplyChainAnalyzer(county_qcew_source)
throughput_calc = DefaultThroughputCalculator(
    county_gdp_source, county_qcew_source, supply_chain, melt_calc
)
pi = throughput_calc.compute_throughput_position("36061", 2022)  # Manhattan
# π ~= 2.8 (major coordination chokepoint)
```

## Validation: Detroit Metro

The Detroit metro provides a key validation case:

| Metric | Oakland (26125) | Wayne (26163) | Expected |
|--------|-----------------|---------------|----------|
| π | Higher | Lower | Oakland > Wayne |
| D | Higher | Lower | Oakland > Wayne |
| Industry | Finance/HQ | Manufacturing | Coordination vs Creation |

```python
# Validate Detroit metro relationship
assert oakland_metrics.pi > wayne_metrics.pi, "Oakland should have higher throughput"
assert oakland_metrics.supply_chain_depth > wayne_metrics.supply_chain_depth, (
    "Oakland should have higher supply chain depth"
)
```

## Data Unavailable Handling

The module uses `NoDataSentinel` for missing data:

```python
from babylon.economics.tensor import NoDataSentinel

result = throughput_calculator.compute_metrics("99999", 2022)
if isinstance(result, NoDataSentinel):
    print(f"Data unavailable: {result.reason}")
else:
    print(f"Metrics computed: π={result.pi:.2f}")
```

## Next Steps

After implementation, this module enables:

1. **Throughput-Class Correlation**: Correlate (π × λ) with LA share from Feature 013
2. **Walmart Effect Validation**: Verify retail λ < 0.15 nationally
3. **Commuter Flow Analysis**: Future enhancement with LODES data
4. **Temporal Analysis**: Track how π changes during deindustrialization
