# Quickstart: MELT and Basket Visibility Computation

**Feature**: 013-melt-basket-visibility | **Date**: 2026-02-01

## Overview

This module provides tools to determine **Labor Aristocracy thresholds** based on Topological Value Theory (TVT). The key concepts:

| Symbol | Name | Meaning |
|--------|------|---------|
| τ | MELT | Monetary Expression of Labor Time ($/labor-hour) |
| γ_basket | Basket Visibility | Imperial subsidy coefficient (0 < γ ≤ 1) |
| τ_effective | LA Threshold | Wage above which workers extract imperial rent |
| V_reproduction | Subsistence Floor | Minimum wage for labor-power reproduction |
| Φ_hour | Imperial Rent | Labor-hours extracted per hour worked |

## Quick Start

### 1. Get National Parameters

```python
from babylon.economics import (
    MELTCalculator,
    BasketVisibilityCalculator,
    NationalParameters,
    ClassPosition,
    ClassPositionClassifier,
)

# Create calculators (use dependency injection in production)
melt_calc = DefaultMELTCalculator(bea_source, qcew_source)
basket_calc = DefaultBasketVisibilityCalculator()

# Compute MELT for 2022
tau = melt_calc.get_melt(2022)
if not tau:  # NoDataSentinel
    print(f"No data: {tau.reason}")
    raise ValueError("Cannot proceed without MELT")

# Compute basket visibility (MVP mode if no trade data)
gamma_basket, estimated = basket_calc.get_gamma_basket(2022)

# Create national parameters
params = NationalParameters(
    year=2022,
    tau=tau,
    alpha=basket_calc.mvp_alpha,  # 0.25
    gamma_import=basket_calc.mvp_gamma_import,  # 0.35
    gamma_basket=gamma_basket,  # 0.68
    tau_effective=tau * gamma_basket,  # ~$44/hr
    v_reproduction=12.0,  # $12/hr (2024 dollars)
    estimated=estimated,
)

print(f"MELT τ = ${params.tau:.2f}/labor-hour")
print(f"Basket visibility γ = {params.gamma_basket:.3f}")
print(f"LA threshold τ_effective = ${params.tau_effective:.2f}/hour")
```

### 2. Classify Wages

```python
classifier = DefaultClassPositionClassifier()

# Classify individual wage
wage = 50.0  # $50/hour
position = classifier.classify(wage, params)
print(f"${wage}/hr → {position.name}")
# Output: $50.0/hr → LABOR_ARISTOCRACY

# Classify multiple wages
wages = [75.0, 50.0, 35.0, 25.0, 18.0, 10.0, 8.0]
for w in wages:
    pos = classifier.classify(w, params)
    print(f"${w:5.2f}/hr → {pos.name}")

# Output:
# $75.00/hr → LABOR_ARISTOCRACY
# $50.00/hr → LABOR_ARISTOCRACY
# $35.00/hr → PROLETARIAT
# $25.00/hr → PROLETARIAT
# $18.00/hr → PROLETARIAT
# $10.00/hr → SUBPROLETARIAT
# $ 8.00/hr → SUBPROLETARIAT
```

### 3. Compute Class Distribution

```python
# Get wage distribution (from QCEW or mock data)
county_wages = [75, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10]

# Get class shares
shares = classifier.classify_distribution(county_wages, params)
print(f"Labor Aristocracy: {shares[ClassPosition.LABOR_ARISTOCRACY]:.1%}")
print(f"Proletariat:       {shares[ClassPosition.PROLETARIAT]:.1%}")
print(f"Subproletariat:    {shares[ClassPosition.SUBPROLETARIAT]:.1%}")

# Output:
# Labor Aristocracy: 41.7%
# Proletariat:       41.7%
# Subproletariat:    16.7%
```

### 4. Calculate Imperial Rent

```python
from babylon.economics import ImperialRentCalculator

calculator = DefaultImperialRentCalculator()

# High-wage worker (Labor Aristocracy)
wage_high = 85.0
phi = calculator.compute_phi_hour(wage_high, params)
l_cmd = calculator.compute_labor_commanded(wage_high, params)
print(f"${wage_high}/hr worker:")
print(f"  Extracts Φ = {phi:.2f} hours of peripheral labor per hour worked")
print(f"  Commands L = {l_cmd:.2f} hours of labor per hour worked")
# Output:
# $85.0/hr worker:
#   Extracts Φ = 0.92 hours of peripheral labor per hour worked
#   Commands L = 1.92 hours of labor per hour worked

# Low-wage worker (Proletariat)
wage_low = 20.0
phi = calculator.compute_phi_hour(wage_low, params)
l_cmd = calculator.compute_labor_commanded(wage_low, params)
print(f"\n${wage_low}/hr worker:")
print(f"  Imperial rent Φ = {phi:.2f} (negative = net exploited)")
print(f"  Commands L = {l_cmd:.2f} hours per hour worked")
# Output:
# $20.0/hr worker:
#   Imperial rent Φ = -0.55 (negative = net exploited)
#   Commands L = 0.45 hours per hour worked
```

## Key Formulas

### MELT (τ)
```
τ = GDP / L
  = GDP / (employment × 2080)
```
where 2080 = 40 hours/week × 52 weeks/year

### Basket Visibility (γ_basket)
```
γ_basket = 1 / (α/γ_import + (1-α))
```
where α = import share, γ_import = peripheral visibility

### Effective MELT (τ_effective)
```
τ_effective = τ × γ_basket
```
This is the Labor Aristocracy threshold wage.

### Imperial Rent (Φ_hour)
```
Φ_hour = (W/τ) × (1/γ_basket) - 1
       = L_commanded - 1
```
Positive = extracts labor. Negative = net exploited.

### Class Position Rules
```
if W > τ_effective:     LABOR_ARISTOCRACY (Φ > 0)
elif W > V_reproduction: PROLETARIAT (Φ ≤ 0)
else:                    SUBPROLETARIAT (W ≤ subsistence)
```

## Validation Case: Detroit Metro

Test the core-periphery hypothesis:

```python
# Wayne County (Detroit proper) - domestic periphery
# Oakland County (suburbs) - domestic core

wayne_wages = get_county_wages("26163")  # Wayne FIPS
oakland_wages = get_county_wages("26125")  # Oakland FIPS

wayne_shares = classifier.classify_distribution(wayne_wages, params)
oakland_shares = classifier.classify_distribution(oakland_wages, params)

wayne_la = wayne_shares[ClassPosition.LABOR_ARISTOCRACY]
oakland_la = oakland_shares[ClassPosition.LABOR_ARISTOCRACY]

# Should validate: Oakland LA share > Wayne LA share
assert oakland_la > wayne_la, "Expected Oakland to have higher LA share than Wayne"
print(f"Oakland LA share: {oakland_la:.1%}")
print(f"Wayne LA share:   {wayne_la:.1%}")
print("✓ Core-periphery hypothesis validated")
```

## MVP vs Full Implementation

| Aspect | MVP | Full |
|--------|-----|------|
| τ (MELT) | Computed from BEA/QCEW | Same |
| γ_basket | Hardcoded 0.68 | Computed from Penn World Tables + Census trade |
| α (import share) | Hardcoded 0.25 | Computed from Census trade data |
| γ_import | Hardcoded 0.35 | Computed from country-weighted ERDI |
| V_reproduction | $12/hr (2024$), CPI-adjusted | Same |
| `estimated` flag | True | False |

## Error Handling

```python
# All calculators return NoDataSentinel for missing data
tau = melt_calc.get_melt(2005)  # Before data range
if not tau:  # NoDataSentinel is falsy
    print(f"Cannot compute: {tau.reason}")
    # Output: Cannot compute: Year 2005 outside data range [2010, 2024]

# Sanity validation
is_valid, warning = melt_calc.validate_melt(tau)
if not is_valid:
    raise ValueError(warning)
elif warning:
    logging.warning(warning)
```
