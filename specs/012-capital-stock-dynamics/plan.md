# Implementation Plan: Capital Stock Dynamics

**Branch**: `012-capital-stock-dynamics` | **Date**: 2026-02-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/012-capital-stock-dynamics/spec.md`

## Summary

Derive capital STOCK (K) from capital FLOWS (c) using the perpetual inventory method with TSSI historical cost valuation. This enables profit rate calculation using stock-based formula `r = s / (K + v)` for testing the Tendency of the Rate of Profit to Fall (TRPF). Implements TVT Axiom A3 (Stock-Flow Consistency) and Section 5.2 (Capital Stock Evolution).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: TensorRegistry, ValueTensor4x3 from spec 011 (fundamental-tensor-primitive); numpy for optional vectorized operations
**Storage**: In-memory cache (follows TensorRegistry pattern); no new database tables
**Testing**: pytest with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.math`
**Target Platform**: Linux server (simulation engine context)
**Project Type**: Single Python package extension to existing `babylon.economics` module
**Performance Goals**: <100ms per county time series (2010-2024), per SC-001
**Constraints**: Must integrate with existing TensorRegistry without breaking consumers; thread-safe
**Scale/Scope**: 3,143 US counties × 15 years = ~47,145 county-year combinations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.3 TRPF with Counter-Tendencies | ✅ PASS | Spec explicitly models TRPF (FR-004, SC-002) and counter-tendencies are handled by δ sensitivity (FR-011) |
| II.2 Primitives vs Derived | ✅ PASS | K is derived from primitive c (constant capital flows), never stored directly |
| II.4 Quantities vs Coefficients | ✅ PASS | K is a quantity (accumulated stock); δ is a coefficient (slow-evolving parameter) |
| III.1 No Magic Constants | ✅ PASS | δ = 0.07 traces to BEA fixed asset depreciation tables (A-001) |
| III.2 Falsifiability Required | ✅ PASS | SC-002 (TRPF: dr/dt < 0, p < 0.05) and SC-003 (OCC-Core correlation > 0.3) provide testable predictions |
| III.4 Data Source Traceability | ✅ PASS | K derives from QCEW (via ValueTensor4x3), δ from BEA |

**All gates pass. Proceeding to Phase 0 research.**

## Project Structure

### Documentation (this feature)

```text
specs/012-capital-stock-dynamics/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── capital_stock_calculator.py
│   └── derived_tensor_metrics.py
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/economics/
├── tensor.py               # EXTEND: Add stock-based profit rate option
├── tensor_registry.py      # EXTEND: Add capital stock caching
├── capital_stock.py        # NEW: CapitalStockCalculator service
├── depreciation.py         # NEW: DepreciationConfig dataclass
└── derived_metrics.py      # NEW: DerivedTensorMetrics container

tests/unit/economics/
├── test_capital_stock.py   # NEW: Unit tests for CapitalStockCalculator
├── test_depreciation.py    # NEW: Unit tests for DepreciationConfig
└── test_derived_metrics.py # NEW: Unit tests for DerivedTensorMetrics

tests/integration/economics/
└── test_trpf_validation.py # NEW: TRPF statistical validation tests
```

**Structure Decision**: Single project (Option 1). Extends existing `babylon.economics` module with new files for capital stock computation. Follows established patterns from TensorRegistry (caching, thread safety, NoDataSentinel).

## Complexity Tracking

> **No violations to justify** - This feature adheres to all Constitution constraints.

## Design Decisions

### D1: Capital Stock as Separate Service vs Tensor Property

**Decision**: Implement as separate `CapitalStockCalculator` service, not as `ValueTensor4x3` computed_field.

**Rationale**:
- K[t] depends on K[t-1], requiring time-series computation across multiple tensor instances
- computed_field cannot access data from other years
- Service pattern matches existing `MarxianHydrator` architecture
- Enables caching of computed K values independently from primitive tensors

### D2: Stock-Based vs Flow-Based Profit Rate

**Decision**: Add stock-based profit rate `r = s / (K + v)` as new method, preserve existing flow-based `profit_rate` computed_field.

**Rationale**:
- Backward compatibility: existing consumers use flow-based rate
- TRPF validation requires stock-based formula (TVT Section 3.6)
- Both rates are theoretically valid for different purposes
- DerivedTensorMetrics will expose stock-based rate via `profit_rate_stock`

### D3: Initial Capital Stock (K_0)

**Decision**: Use steady-state assumption K_0 = c_0 / δ for 2010 baseline.

**Rationale**:
- Follows TVT Section 5.2 recommendation
- Error from this assumption decays with time constant ~14 years (1/δ)
- By 2024 (14 years), initial error is significantly dampened
- Alternative (extrapolating backward) would require data we don't have

### D4: Missing Year Handling

**Decision**: Skip missing years and continue accumulation from last available year.

**Rationale**:
- Interpolation would introduce speculative values
- Skipping is conservative and transparent
- Logged warning ensures user awareness
- Consistent with existing TensorRegistry NoDataSentinel pattern

## Implementation Phases

### Phase 0: Research
- Review TVT mathematical formalization for formula precision
- Analyze existing TensorRegistry caching patterns
- Identify test data requirements for validation

### Phase 1: Data Model & Contracts
- Define DepreciationConfig dataclass
- Define DerivedTensorMetrics container
- Define CapitalStockCalculator protocol/interface
- Document contracts in `contracts/` directory

### Phase 2: Task Generation
- Run `/speckit.tasks` to generate detailed tasks

### Phase 3: Core Implementation
- Implement DepreciationConfig with validation
- Implement CapitalStockCalculator with perpetual inventory method
- Implement DerivedTensorMetrics container
- Add stock-based profit rate calculation

### Phase 4: Integration
- Integrate CapitalStockCalculator with TensorRegistry
- Add capital stock caching with invalidation
- Implement geographic aggregation for K

### Phase 5: Validation
- Implement TRPF statistical tests (SC-002)
- Implement OCC-CoreIndex correlation tests (SC-003)
- Implement Detroit validation case (Wayne vs Oakland)
- Sensitivity analysis with δ ∈ {0.05, 0.07, 0.10}

### Phase 6: Documentation
- Write quickstart.md with usage examples
- Update data-model.md with final implementation
- Document integration patterns
