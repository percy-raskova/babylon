# Quickstart: Gamma (Visibility) Tensor

**Feature**: 015-gamma-visibility-tensor
**Date**: 2026-02-04

## Overview

The Gamma (γ) Visibility Tensor measures the fraction of labor-time that survives transformation to price-space. This module computes:

1. **γ_III (Reproductive visibility)**: Fraction of care labor that is commodified
2. **γ_import (Import visibility)**: ERDI-weighted visibility of imports
3. **γ_basket (Basket visibility)**: Composite consumption basket visibility
4. **Shadow subsidies (Φ_III, Φ_imperial)**: Dollar value of hidden value transfers

## Installation

The gamma module is part of the `babylon.economics` package. No additional installation required.

## Basic Usage

### Compute Reproductive Visibility (γ_III)

```python
from babylon.economics.gamma import (
    DefaultGammaIIICalculator,
    GammaIII,
)

# Create calculator with default ATUS/QCEW data sources
calculator = DefaultGammaIIICalculator()

# Compute γ_III for a given year
result = calculator.compute(year=2022)

if isinstance(result, GammaIII):
    print(f"γ_III = {result.gamma_iii:.3f}")
    print(f"Fortunati exploitation rate = {result.fortunati_exploitation:.2f}")
    print(f"Paid care hours: {result.paid_care_hours:.1f}B")
    print(f"Unpaid care hours: {result.unpaid_care_hours:.1f}B")
else:
    print(f"Data unavailable: {result.reason}")
```

**Expected Output**:
```
γ_III = 0.333
Fortunati exploitation rate = 2.01
Paid care hours: 25.0B
Unpaid care hours: 50.0B
```

### Compute Import Visibility (γ_import)

```python
from babylon.economics.gamma import (
    DefaultGammaImportCalculator,
    GammaImport,
)

# Create calculator (uses MVP hardcoded ERDI values)
calculator = DefaultGammaImportCalculator()

# Compute γ_import for a given year
result = calculator.compute(year=2022)

print(f"γ_import = {result.gamma_import:.3f}")
print(f"Using MVP values: {result.is_mvp}")

# Inspect per-country visibility
for country, erdi in result.erdi_values.items():
    share = result.import_shares.get(country, 0)
    gamma = 1 / erdi
    print(f"  {country}: share={share:.1%}, ERDI={erdi:.1f}, γ={gamma:.2f}")
```

**Expected Output**:
```
γ_import = 0.650
Using MVP values: True
  CHN: share=18.0%, ERDI=1.8, γ=0.56
  MEX: share=14.0%, ERDI=1.5, γ=0.67
  CAN: share=13.0%, ERDI=1.1, γ=0.91
  ...
```

### Compute Basket Visibility (γ_basket)

```python
from babylon.economics.gamma import (
    DefaultGammaBasketCalculator,
    GammaBasket,
)

# Create calculator
basket_calc = DefaultGammaBasketCalculator()

# Option 1: Compute from components
result = basket_calc.compute(
    year=2022,
    alpha=0.35,        # Import share
    gamma_import=0.65, # From GammaImport
)

print(f"γ_basket = {result.gamma_basket:.3f}")
print(f"Import share α = {result.alpha:.1%}")

# Option 2: Direct formula
gamma_basket = 1 / (0.35/0.65 + 0.65)  # = 0.74
```

**Expected Output**:
```
γ_basket = 0.739
Import share α = 35.0%
```

### Compute Shadow Subsidies

```python
from babylon.economics.gamma import (
    DefaultGammaIIICalculator,
    DefaultShadowSubsidyCalculator,
    ShadowSubsidy,
)
from babylon.economics.melt import DefaultMELTCalculator
from babylon.economics.tensor import NoDataSentinel

# Create calculators
subsidy_calc = DefaultShadowSubsidyCalculator()
melt_calc = DefaultMELTCalculator()

# Get MELT for dollar conversion
melt_result = melt_calc.compute_melt(year=2022)
tau = melt_result.melt if not isinstance(melt_result, NoDataSentinel) else None

# First compute γ_III (or use a pre-computed result)
gamma_calc = DefaultGammaIIICalculator()
gamma_result = gamma_calc.compute(year=2022)

# Compute reproductive shadow subsidy (Φ_III)
phi_iii = subsidy_calc.compute_phi_iii(
    gamma_iii=gamma_result,  # GammaIII model with paid/unpaid hours
    melt=tau,                # $65/hour (or None for labor-hours only)
)

print(f"Φ_III = ${phi_iii.phi_iii_dollars/1e12:.2f}T")
print(f"Φ_III (labor-hours) = {phi_iii.phi_iii_labor_hours/1e9:.1f}B hours")

# Compute imperial shadow subsidy (Φ_imperial)
phi_imperial = subsidy_calc.compute_phi_imperial(
    gamma_basket=0.74,
    consumption=15e12,  # $15 trillion
)

print(f"Φ_imperial = ${phi_imperial/1e12:.2f}T")
```

**Expected Output**:
```
Φ_III = $2.18T
Φ_III (labor-hours) = 33.5B hours
Φ_imperial = $3.90T
```

## Validation

### Check Value Ranges

```python
from babylon.economics.gamma import (
    validate_gamma_iii,
    validate_gamma_import,
    validate_gamma_basket,
)

# Validate γ_III
valid, message = validate_gamma_iii(0.33)
if not valid:
    print(f"ERROR: {message}")
elif message:
    print(f"WARNING: {message}")
else:
    print("γ_III within expected range")

# Expected ranges:
# - γ_III: [0.20, 0.40]
# - γ_import: [0.40, 0.70]
# - γ_basket: [0.60, 0.85]
```

### Detroit Metro Validation

```python
# Validation scenario: Detroit Metro comparison
# This validates the "two subsidies" framework produces expected magnitudes

detroit_test = {
    "gamma_iii": 0.30,           # Within [0.20, 0.40] ✓
    "gamma_import": 0.65,        # Within [0.40, 0.70] ✓
    "gamma_basket": 0.74,        # Within [0.60, 0.85] ✓
    "phi_iii": 2.2e12,           # $2.2T - within $1.5-3.5T ✓
    "phi_imperial": 3.9e12,      # $3.9T - within $1.0-4.0T ✓
    "fortunati_e": 2.33,         # Within [2.0, 3.0] ✓
}

for metric, value in detroit_test.items():
    print(f"{metric}: {value:.2g}")
```

## Integration with Existing Modules

### Using ATUS Data

```python
from babylon.data.atus import create_atus_loader

# Get unpaid care hours from ATUS
atus_loader = create_atus_loader()
summary = atus_loader.load_county_summary("26163", 2022)  # Wayne County
unpaid_weekly = summary.unpaid_care_hours_weekly

# Scale to national annual estimate
unpaid_annual = unpaid_weekly * 52 * 130_000_000  # ~130M US households
```

### Using QCEW Data

```python
from babylon.economics.throughput import SQLiteQCEWCountyNAICSSource

# Get paid care employment from QCEW
qcew_source = SQLiteQCEWCountyNAICSSource(session)

# Care sector NAICS codes
care_naics = ["61", "62", "624", "814"]
total_employment = sum(
    qcew_source.get_employment(fips="00000", naics=code, year=2022) or 0
    for code in care_naics
)

# Convert to hours (with care fraction adjustment)
paid_care_hours = total_employment * 2080 * 0.40  # 40% care fraction
```

### Using MELT for Dollar Conversion

```python
from babylon.economics.melt import DefaultMELTCalculator

melt_calc = DefaultMELTCalculator()
result = melt_calc.compute_melt(year=2022)

if not isinstance(result, NoDataSentinel):
    tau = result.melt  # ~$65/hour
    # Convert labor-hours to dollars
    phi_iii_dollars = phi_iii_hours * tau
```

## Key Constraints

1. **γ does NOT apply to domestic core/periphery geography**
   - For domestic value geography, use π (throughput position) from Feature 014
   - γ only applies to: international borders (ERDI) and reproductive naturalization

2. **Intensive aggregation only**
   - γ values are weighted-averages, not sums
   - When aggregating: use `Σ(weight × γ) / Σ(weight)`

3. **NoDataSentinel pattern**
   - All calculators return `NoDataSentinel` when data unavailable
   - Always check: `if isinstance(result, NoDataSentinel): ...`

## Next Steps

1. Run validation tests: `pytest tests/unit/economics/gamma/ -v`
2. Check national magnitude: `pytest tests/integration/economics/test_gamma_validation.py -v`
3. Review shadow subsidy calculations match expected $2-4T magnitudes
