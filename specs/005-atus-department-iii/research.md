# Research: ATUS Department III - Visibility Decomposition

**Feature**: 005-atus-department-iii
**Date**: 2026-01-31
**Status**: Complete

## Overview

This document consolidates research findings for implementing g₃₃ visibility decomposition. The scope is narrow: compute visibility from data instead of using the default 1.0.

**Already Exists** (NOT researched here):

- `dept_III` field in `ValueTensor4x3`
- `visibility_g33` field (defaults to 1.0)
- `shadow_subsidy` computed property
- ATUS activity code mappings
- ATUS seed data with occupation multipliers

**Research Focus**: How to compute g₃₃ from the four-category decomposition.

______________________________________________________________________

## 1. Existing Infrastructure Assessment

### Decision: Leverage Existing ATUS Module

**Rationale**: The `src/babylon/data/atus/` module already provides substantial infrastructure:

| Component        | Status            | Action Required                                        |
| ---------------- | ----------------- | ------------------------------------------------------ |
| `mappings.py`    | Complete          | ATUS activity codes → Babylon categories (22 mappings) |
| `models.py`      | Complete          | `ATUSActivityRecord`, `ATUSHouseholdSummary` models    |
| `protocol.py`    | Complete          | `ReproductionLoaderProtocol` for dependency injection  |
| `loader.py`      | Complete          | `ATUSReferenceLoader` loads seed YAML into 3NF schema  |
| `seed_data.yaml` | Needs Enhancement | Add visibility decomposition weights                   |
| `mock_loader.py` | Complete          | Testing infrastructure in place                        |

**Alternatives Considered**:

- Build from scratch: Rejected (would duplicate existing work)
- Fork IPUMS ATUS package: Rejected (adds external dependency, overkill for national averages)

______________________________________________________________________

## 2. Visibility Decomposition (g₃₃) Formula

### Decision: Four-Component Weighted Average

**Formula**:

```
g₃₃ = w_domestic × g_domestic + w_migrant × g_migrant + w_peripheral × g_peripheral + w_state × g_state
```

Where:

- `g_domestic` = 0.0 (domestic unpaid is invisible by definition)
- `g_migrant` = 0.3 (migrant care work partially visible via cash economy)
- `g_peripheral` = 0.0 (peripheral subsistence invisible to core price system)
- `g_state` = 1.0 (state-socialized care fully visible via taxation/spending)

**Weight Derivation** (national-level estimates):

| Component              | Weight | Source         | Calculation                                       |
| ---------------------- | ------ | -------------- | ------------------------------------------------- |
| domestic_unpaid        | 0.70   | ATUS Table A-1 | % of reproductive hours done by household members |
| migrant_care           | 0.10   | ACS + OEWS     | Estimated noncitizen share of care sector         |
| peripheral_subsistence | 0.05   | Theoretical    | Remittance-based reproduction estimate            |
| state_socialized       | 0.15   | QCEW + BEA     | Public sector care employment / total care        |

**Result**: g₃₃ ≈ 0.70×0.0 + 0.10×0.3 + 0.05×0.0 + 0.15×1.0 = **0.18**

This falls within SC-004 range (0.2-0.5) with conservative domestic_unpaid weighting.

**Alternatives Considered**:

- Single-factor model (gender differential only): Rejected (misses structural sources of invisibility)
- County-level variation: Rejected (ATUS sample too small; deferred to future work)

______________________________________________________________________

## 3. CEX Data Integration Strategy

> **OUT OF SCOPE**: CEX integration is deferred. The existing hydrator already populates `dept_III.c` from QCEW. This feature focuses only on visibility decomposition (g₃₃), not T³_c computation.

See [spec.md](./spec.md) "Scope Clarification" section for details on what's in/out of scope.

______________________________________________________________________

## 4. Occupation → Class Position Mapping

### Decision: Use Existing SOC-Based Mapping

**Rationale**: `mappings.py` already defines `OccupationGroupMapping` with class character:

| Babylon Group           | SOC Range | Class Character             |
| ----------------------- | --------- | --------------------------- |
| professional_managerial | 11-13     | bourgeois/petit_bourgeois   |
| professional_technical  | 15-29     | labor_aristocracy           |
| sales_clerical          | 41-43     | proletariat/petit_bourgeois |
| service                 | 31-39     | proletariat                 |
| trades                  | 45-49     | proletariat                 |
| production_transport    | 51-53     | proletariat                 |

**Refinement for Babylon SocialRole**:

| Class Character             | Babylon SocialRole                  |
| --------------------------- | ----------------------------------- |
| bourgeois/petit_bourgeois   | BOURGEOISIE                         |
| labor_aristocracy           | PROLETARIAT (with aristocracy flag) |
| proletariat/petit_bourgeois | PROLETARIAT                         |
| proletariat                 | PROLETARIAT                         |

**Alternatives Considered**:

- Income-based classification: Rejected (income varies within occupation; occupation is structural)
- Education-based classification: Rejected (education is effect, not cause of class position)

______________________________________________________________________

## 5. Regression Validation Approach

### Decision: scipy.stats.linregress for Simplicity

**Rationale**: The validation regression is diagnostic, not predictive. scipy.stats provides sufficient functionality:

```python
from scipy.stats import linregress

# Transform: 1/income (inverse income as predictor)
x = 1 / income_array
y = domestic_hours_array

result = linregress(x, y)
# SC-002: Check result.slope > 0 (positive coefficient)
```

**Test Data Source**: ATUS + CEX linked at occupation group level (synthetic dataset for validation)

**Alternatives Considered**:

- statsmodels OLS: Rejected (heavier dependency for simple univariate regression)
- sklearn LinearRegression: Rejected (overkill; scipy.stats is sufficient)

______________________________________________________________________

## 6. Shadow Subsidy Computation

### Decision: Extend Existing ShadowLaborService

**Current Implementation** (`shadow_labor.py`):

```python
class ShadowLaborResult:
    v_market: float   # T³_v × g₃₃
    v_shadow: float   # T³_v × (1 - g₃₃)
```

**Enhancement**: Add visibility decomposition breakdown:

```python
class VisibilityDecomposition(BaseModel):
    domestic_unpaid: float     # Fraction in domestic_unpaid bucket
    migrant_care: float        # Fraction in migrant_care bucket
    peripheral_subsistence: float  # Fraction in peripheral bucket
    state_socialized: float    # Fraction in state bucket
    total_g33: float           # Weighted visibility coefficient
```

**Integration Point**: `ShadowLaborService.calculate_shadow_decomposition()` returns enhanced result including `VisibilityDecomposition`.

______________________________________________________________________

## 7. Performance Considerations

### Decision: Batch Processing with Lazy Loading

**Approach**:

1. Load ATUS seed data once at service initialization
1. Cache occupation multipliers in memory
1. Compute T³_v and g₃₃ on demand (lazy evaluation)
1. Full pipeline benchmark: Load seed → compute all 30 occupation×category combinations

**Target**: ≤5 minutes for full survey year (SC-008)

**Estimated Performance**:

- Seed data load: \<1 second (small YAML file)
- T³_v computation: O(1) per occupation-category (simple multiplication)
- g₃₃ computation: O(1) (weighted sum)
- Total: \<<5 minutes (performance target easily met with current approach)

______________________________________________________________________

## 8. Error Handling Strategy

### Decision: Fail Fast with Clear Messages

Per clarification session:

- **BLS Unavailable**: Raise `DataSourceUnavailableError` with source name
- **Missing Occupation Mapping**: Default to "proletariat" with WARNING log
- **g₃₃ Out of Bounds**: Clamp to [0, 1] with WARNING log
- **Small Sample Size**: Return result with `confidence_flag=LOW`

**Exception Hierarchy**:

```
DataError (base)
├── DataSourceUnavailableError
├── MappingNotFoundError
└── InsufficientSampleError
```

______________________________________________________________________

## Summary

| Unknown                 | Resolution                                            | Confidence                     |
| ----------------------- | ----------------------------------------------------- | ------------------------------ |
| Existing infrastructure | Leverage existing ATUS module (already complete)      | High                           |
| g₃₃ formula             | Four-component weighted average                       | Medium (weights are estimates) |
| CEX integration         | OUT OF SCOPE (existing hydrator suffices)             | N/A                            |
| Occupation mapping      | Use existing SOC-based mapping                        | High                           |
| Validation regression   | scipy.stats.linregress                                | High                           |
| Shadow subsidy          | Integrate visibility into existing ShadowLaborService | High                           |
| Performance             | Seed data already loaded; O(1) computation            | High                           |
| Error handling          | Fail fast pattern                                     | High                           |

**All NEEDS CLARIFICATION items resolved. Ready for implementation.**
