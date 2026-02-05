# Implementation Plan: Gamma (Visibility) Tensor

**Branch**: `015-gamma-visibility-tensor` | **Date**: 2026-02-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-gamma-visibility-tensor/spec.md`

## Summary

Implement the Gamma (γ) Visibility Tensor for measuring the fraction of labor-time that survives transformation to price-space. Two distinct mechanisms:

1. **γ_III (Reproductive)**: Fraction of care labor that is commodified vs naturalized as unpaid household work
2. **γ_import (International)**: ERDI-based compression of peripheral labor at currency zone borders

**Critical constraint**: γ does NOT apply to domestic core/periphery geography (use π from Feature 014).

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x, SQLAlchemy 2.x (existing), ATUS infrastructure (Feature 005)
**Storage**: In-memory computation; reads from existing ATUS/QCEW data sources
**Testing**: pytest with existing markers (@pytest.mark.unit, @pytest.mark.integration)
**Target Platform**: Linux (research/simulation backend)
**Project Type**: Single (extends existing `babylon.economics` package)
**Performance Goals**: N/A (batch calculation, not latency-sensitive)
**Constraints**: NoDataSentinel pattern for unavailable data; MVP hardcoded ERDI values initially
**Scale/Scope**: National-level γ_III; county-level out of scope for MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I.2 Imperial Rent (Φ)** | ✅ PASS | γ measures visibility of labor transfer mechanisms |
| **I.5 Department III** | ✅ PASS | γ_III directly implements Fortunati visibility coefficient |
| **II.2 Primitives vs Derived** | ✅ PASS | γ is derived from labor-hour primitives (ATUS, QCEW) |
| **II.3 NetworkX as Manifold** | ✅ N/A | No graph topology changes; pure calculation |
| **II.5 AI Observes, Never Controls** | ✅ PASS | Calculation module, no AI interaction |
| **II.6 State is Data, Engine is Transformation** | ✅ PASS | γ types are frozen Pydantic models |
| **III.1 No Magic Constants** | ✅ PASS | ERDI values trace to Penn World Tables; γ_III from ATUS data |
| **III.4 Data Source Traceability** | ✅ PASS | ATUS, QCEW, Penn World Tables all documented |
| **VII.6 Constants Without Data Sources** | ✅ PASS | MVP ERDI hardcoded with explicit data source reference |

**Gate Status**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/015-gamma-visibility-tensor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - internal calculation)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/gamma/
├── __init__.py          # Package exports
├── types.py             # GammaComponents, GammaIII, ShadowSubsidy types
├── gamma_iii.py         # GammaIIICalculator (reproductive visibility)
├── gamma_import.py      # GammaImportCalculator (international visibility)
├── gamma_basket.py      # GammaBasketCalculator (composite basket)
├── shadow_subsidy.py    # ShadowSubsidyCalculator (Φ_III, Φ_imperial)
├── data_sources.py      # Protocols for data access
└── adapters.py          # SQLite adapters for QCEW care sectors

tests/
├── unit/economics/gamma/
│   ├── test_types.py
│   ├── test_gamma_iii.py
│   ├── test_gamma_import.py
│   ├── test_gamma_basket.py
│   └── test_shadow_subsidy.py
└── integration/economics/
    └── test_gamma_validation.py  # National magnitude validation
```

**Structure Decision**: New `gamma/` subpackage under `babylon.economics` following the pattern established by `melt/` and `throughput/` packages. Separates visibility tensor from existing basket visibility (which is for class position, not shadow subsidy).

## Phase 0: Research

### Research Tasks

1. **Existing Infrastructure Survey**
   - ATUS visibility decomposition (Feature 005): `VisibilityComputer.get_national_g33()`
   - MELT basket visibility (Feature 013): `DefaultBasketVisibilityCalculator`
   - QCEW care sector access: Feature 014 adapters

2. **NAICS Care Sector Aggregation**
   - Which QCEW NAICS codes map to paid care labor?
   - How to convert employment → labor hours?

3. **ERDI Data Strategy**
   - Penn World Tables ERDI structure
   - MVP hardcoded values for top US trading partners

4. **Integration Points**
   - How does γ_III relate to existing g₃₃ in ATUS visibility?
   - How does γ_basket relate to existing basket_visibility module?

### Research Findings

**R1: ATUS Infrastructure (Feature 005)**

The existing `VisibilityComputer` in `babylon.data.atus.visibility` computes g₃₃ from seed data weights. Key insight:

- **g₃₃ (existing)**: Visibility decomposition by structural category (domestic_unpaid=0, state_socialized=1.0)
- **γ_III (this spec)**: Visibility as ratio of paid/total care hours

These are **different formulations** of the same concept. g₃₃ uses qualitative category weights; γ_III uses quantitative hour ratios. We implement γ_III as the new canonical formula while preserving g₃₃ for backward compatibility.

**R2: QCEW Care Sector NAICS Codes**

Per FR-002, aggregate hours from:
- **61**: Educational Services
- **62**: Health Care and Social Assistance
- **624**: Social Assistance (subset of 62, more specific)
- **814**: Private Households (nannies, housekeepers)

The QCEW provides employment counts. Convert to hours: `hours = employment × 2080` (annual FTE).

**R3: ERDI MVP Values**

Top US import partners and Penn World Tables ERDI (2019 baseline):

| Country | Import Share | ERDI | γ_origin |
|---------|--------------|------|----------|
| China | 18% | 1.8 | 0.56 |
| Mexico | 14% | 1.5 | 0.67 |
| Canada | 13% | 1.1 | 0.91 |
| Vietnam | 5% | 2.5 | 0.40 |
| Germany | 5% | 1.0 | 1.00 |
| Japan | 5% | 1.0 | 1.00 |

Computed γ_import ≈ 0.65 (weighted average)

**R4: Integration with Existing Modules**

- **Do NOT modify** `melt/basket_visibility.py` - that serves class position calculation
- **Create new** `gamma/` package for shadow subsidy calculations
- **Reuse** ATUS infrastructure for unpaid hours data
- **Reuse** QCEW adapters for paid care hours

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md) for entity definitions.

**Key Types:**

```python
class GammaIII(BaseModel, frozen=True):
    """Reproductive labor visibility coefficient."""
    year: int
    paid_care_hours: float        # L_paid (annual, national)
    unpaid_care_hours: float      # L_unpaid (annual, national)
    gamma_iii: float              # L_paid / (L_paid + L_unpaid)
    fortunati_exploitation: float # (1 - γ_III) / γ_III

class GammaImport(BaseModel, frozen=True):
    """International import visibility coefficient."""
    year: int
    import_shares: dict[str, float]  # country -> share
    erdi_values: dict[str, float]    # country -> ERDI
    gamma_import: float              # Σ(share × 1/ERDI)

class GammaBasket(BaseModel, frozen=True):
    """Composite basket visibility."""
    year: int
    alpha: float         # Import share [0, 1]
    gamma_import: float  # From GammaImport
    gamma_basket: float  # 1 / (α/γ_import + (1-α))

class ShadowSubsidy(BaseModel, frozen=True):
    """Shadow subsidy calculations."""
    year: int
    phi_iii: float              # Reproductive shadow subsidy
    phi_iii_labor_hours: float  # Same in labor-hours (if MELT unavailable)
    phi_imperial: float         # Imperial shadow subsidy
    total_shadow: float         # Combined subsidies
```

### Service Protocols

```python
class GammaIIICalculator(Protocol):
    """Compute reproductive visibility γ_III."""
    def compute(self, year: int) -> GammaIII | NoDataSentinel: ...
    def get_paid_care_hours(self, year: int) -> float | NoDataSentinel: ...
    def get_unpaid_care_hours(self, year: int) -> float | NoDataSentinel: ...

class GammaImportCalculator(Protocol):
    """Compute import visibility γ_import."""
    def compute(self, year: int) -> GammaImport | NoDataSentinel: ...
    def get_erdi(self, country: str) -> float: ...

class GammaBasketCalculator(Protocol):
    """Compute composite basket visibility."""
    def compute(self, year: int, alpha: float, gamma_import: float) -> GammaBasket | NoDataSentinel: ...

class ShadowSubsidyCalculator(Protocol):
    """Compute shadow subsidies Φ_III and Φ_imperial."""
    def compute_phi_iii(self, gamma_iii: GammaIII, melt: float | None) -> ShadowSubsidy: ...
    def compute_phi_imperial(self, gamma_basket: GammaBasket, consumption: float) -> float: ...
```

### Contracts

N/A - This is an internal calculation module, not an API.

### Quickstart

See [quickstart.md](./quickstart.md) for usage examples.

## Complexity Tracking

No constitution violations requiring justification.
