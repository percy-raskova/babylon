# Research: MELT and Basket Visibility Computation

**Feature**: 013-melt-basket-visibility | **Date**: 2026-02-01

## R1: TVT Formula Precision

### Decision
Use exact TVT axiom formulas as specified in `ai-docs/brainstorms/tensor/tvt_mathematical_formalization.md`.

### Rationale
- Axiom B3 defines τ = GDP / L (MELT as ratio of national output to labor hours)
- Axiom D3 defines γ_basket = 1 / (α/γ_import + (1-α)) (weighted harmonic mean)
- Axiom D4 defines τ_effective = τ × γ_basket (effective MELT threshold)
- Axiom E3 defines Φ_hour = (W/τ) × (1/γ_basket) - 1 (imperial rent per hour)
- Axiom E4 defines L_commanded = (W/τ) × (1/γ_basket) (labor hours commanded)

### Alternatives Considered
- Simplified linear formula for γ_basket (rejected: doesn't match TVT derivation)
- Alternative MELT definitions using GNP or NDP (rejected: GDP is standard)

## R2: BEA GDP Data Availability

### Decision
Use BEA Annual GDP data from existing data pipeline (NIPA Table 1.1.5).

### Rationale
- BEA provides annual GDP in current dollars (required for τ calculation)
- National GDP aggregation is available directly (no need to sum counties)
- Historical data available 2010-2024 (matches spec data range)
- Existing `BEADataSource` protocol in `babylon.economics.adapters` provides pattern

### Data Format
- GDP is reported in billions of dollars
- Convert to raw dollars: GDP_dollars = GDP_billions × 1e9
- Use current-year dollars (not inflation-adjusted) per TSSI

### Alternatives Considered
- Sum county-level GDP from BEA Regional (rejected: unnecessary when national available)
- Use GNP instead of GDP (rejected: GDP is TVT standard)

## R3: QCEW National Employment Aggregation

### Decision
Use QCEW national-level employment totals from existing data pipeline.

### Rationale
- QCEW provides total employment counts at national level
- Existing `QCEWDataSource` protocol supports national queries
- Convert employment to labor hours: L = employment × 2080 hours/year (per A-001)
- Historical data available 2010-2024

### Data Format
- Employment is integer count of workers
- L = employment × 2080 (standard work-year)
- τ = GDP / L gives $/labor-hour

### Alternatives Considered
- Sum county employment to national (rejected: QCEW already provides national)
- Use BLS employment instead of QCEW (rejected: QCEW is more detailed)

## R4: CPI Data for V_reproduction Adjustment

### Decision
Use BLS CPI-U (Consumer Price Index for All Urban Consumers) for inflation adjustment.

### Rationale
- V_reproduction = $12/hour is specified in 2024 dollars (A-003)
- For years before 2024, adjust: V_reproduction[year] = 12 × (CPI[year] / CPI[2024])
- CPI-U is the standard inflation measure used by Census and BLS
- Data available from FRED or direct BLS API

### Implementation
```python
def adjust_v_reproduction(year: int, cpi_data: dict[int, float]) -> float:
    """Adjust V_reproduction for inflation.

    Base value is $12/hour in 2024 dollars.
    """
    base_value = 12.0
    base_year = 2024
    return base_value * (cpi_data[year] / cpi_data[base_year])
```

### Alternatives Considered
- PCE deflator instead of CPI (rejected: CPI is more common for wage analysis)
- Regional CPI (rejected: national CPI sufficient for MVP)
- No adjustment, use constant $12 (rejected: would distort historical comparisons)

## R5: MVP γ_basket Derivation

### Decision
Use hardcoded γ_basket = 0.68 for MVP, derived from Hickel et al. methodology.

### Rationale
- Per A-004: α ≈ 0.25 (25% import share), γ_import ≈ 0.35 (peripheral visibility)
- γ_basket = 1 / (0.25/0.35 + 0.75) = 1 / 1.464 ≈ 0.683
- Rounding to 0.68 provides clean MVP value
- Empirically reasonable: implies ~32% consumption subsidy from imperial extraction

### Validation
- Expected range: 0.60-0.80 (spec FR-010)
- 0.68 is comfortably within expected range
- Sensitivity: varying α ± 0.10 yields γ_basket in [0.60, 0.78]

### Alternatives Considered
- Use 0.70 for cleaner number (rejected: 0.68 is more accurate)
- Compute dynamically from Penn World Tables (deferred: requires new loader)

## R6: Existing TensorRegistry Caching Pattern

### Decision
Follow existing `TensorRegistry` caching pattern for `NationalParameters`.

### Rationale
- TensorRegistry uses dict-based cache with (fips, year) keys
- NationalParameters uses (year,) key only (national, not county-level)
- Thread safety via simple dict operations (GIL provides atomicity for dict[key])
- Cache invalidation: clear entire cache on configuration change

### Pattern Reference
From `babylon.economics.tensor_registry.py`:
```python
class TensorRegistry:
    def __init__(self):
        self._cache: dict[tuple[str, int], ValueTensor4x3 | NoDataSentinel] = {}

    def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
        key = (fips, year)
        if key not in self._cache:
            self._cache[key] = self._compute(fips, year)
        return self._cache[key]
```

### Alternatives Considered
- LRU cache with size limit (rejected: annual params are small, cache all years)
- External cache (Redis) (rejected: overkill for single-process simulation)

## R7: ClassPosition Enum Design

### Decision
Implement `ClassPosition` as `enum.Enum` with three wage-based values.

### Rationale
- Per Constitution I.7: qualities are discrete, not continuous
- Three positions: LABOR_ARISTOCRACY, PROLETARIAT, SUBPROLETARIAT
- Enum provides type safety and exhaustive matching
- Scope limitation: wage-based only (cannot identify bourgeoisie/lumpen)

### Implementation
```python
from enum import Enum, auto

class ClassPosition(Enum):
    """Wage-based class position for imperial rent analysis.

    Scope limitation: This classification is wage-based only.
    It cannot identify bourgeoisie (non-wage income) or lumpen
    (excluded from production).
    """
    LABOR_ARISTOCRACY = auto()  # W > τ_effective, Φ_hour > 0
    PROLETARIAT = auto()         # τ_effective ≥ W > V_reproduction
    SUBPROLETARIAT = auto()      # W ≤ V_reproduction
```

### Alternatives Considered
- String literals (rejected: no type safety)
- Integer codes (rejected: less readable)
- Include BOURGEOISIE/LUMPEN (rejected: out of scope per spec)

## R8: Feature 012 Integration Points

### Decision
This feature depends on Feature 012 (Capital Stock Dynamics) being complete.

### Integration Points
1. **Shared NoDataSentinel pattern**: Use same sentinel for missing data
2. **TensorRegistry access**: Both features read from same registry
3. **Economics module exports**: Both export from `babylon.economics`
4. **Test patterns**: Follow same pytest marker conventions

### Rationale
- Feature 012 established patterns that Feature 013 should follow
- No direct data dependency (MELT doesn't need capital stock K)
- Shared infrastructure patterns ensure consistency

### Alternatives Considered
- Duplicate NoDataSentinel in new module (rejected: DRY violation)
- Independent module outside babylon.economics (rejected: breaks coherence)

## R9: Edge Case Handling

### Decision
Document and handle all edge cases per spec Edge Cases section.

| Edge Case | Handling | Return |
|-----------|----------|--------|
| GDP data missing | Log warning | NoDataSentinel("National GDP unavailable for year") |
| Employment = 0 | Log error | NoDataSentinel("Zero employment (division by zero)") |
| γ_basket > 1.0 | Cap at 1.0 | 1.0 (cannot have negative subsidy) |
| γ_basket ≤ 0 | Log error | NoDataSentinel("Invalid γ_basket ≤ 0") |
| V_reproduction > τ_effective | Log warning | Return values (theoretically impossible but data error) |
| Year < 2010 | Reject | NoDataSentinel("Year outside data range") |
| α = 0 | Normal compute | γ_basket = 1.0 (no imports, no subsidy) |
| α = 1 | Normal compute | γ_basket = γ_import (100% imports) |

### Rationale
- Graceful degradation via NoDataSentinel matches existing patterns
- Logging ensures visibility of edge cases
- Capping γ_basket at 1.0 prevents mathematical nonsense

## R10: Sanity Range Validation

### Decision
Implement sanity range validation per FR-010 with warning/fail thresholds.

| Parameter | Expected | Warning | Fail |
|-----------|----------|---------|------|
| τ ($/hour) | 55-75 | 40-100 | <20 or >200 |
| γ_basket | 0.60-0.80 | 0.4-0.95 | <0.1 or >1.0 |
| τ_effective ($/hour) | 35-55 | 25-70 | N/A |
| LA share | 30-50% | 15-70% | N/A |

### Implementation
```python
def validate_melt(tau: float) -> tuple[bool, str | None]:
    """Validate MELT against sanity ranges."""
    if tau < 20 or tau > 200:
        return False, f"MELT τ={tau} outside valid range [20, 200]"
    if tau < 40 or tau > 100:
        return True, f"WARNING: MELT τ={tau} outside expected range [40, 100]"
    return True, None
```

### Rationale
- Two-tier validation (warning vs fail) allows flexibility
- Fail conditions indicate data or calculation errors
- Warning conditions flag unusual but valid values
