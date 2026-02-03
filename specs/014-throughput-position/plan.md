# Implementation Plan: Throughput Position and Domestic Value Geography

**Branch**: `014-throughput-position` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/014-throughput-position/spec.md`

## Summary

Implement the throughput position (π) and domestic value geography analysis system for understanding within-US value flows. Unlike international value transfer (which operates through visibility γ and ERDI differentials), domestic geography operates through **throughput position** - the relative flow of accumulated value through a location. The core insight: within a single currency zone, wages track THROUGHPUT, not value creation. A retail worker in Manhattan handles enormous throughput but captures little (low λ), while an extraction worker in Appalachia creates value but sees little flow through (low π).

Key formulas:
- τ_through[fips] = GDP[fips] / (employment[fips] × 2080) - county throughput intensity
- π[fips] = τ_through[fips] / τ_national - throughput position (coordination vs extraction)
- D[fips] = Σ(employment × depth) / Σ employment - supply chain depth
- W = λ × τ_through - wage formula (throughput × institutional capture)

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Feature 013 (MELTCalculator for national τ); BEA county GDP data (✅ exists in FactBEACountyGDP); QCEW county employment (✅ exists in FactQcewAnnual)
**Storage**: Queries existing 3NF database (marxist-data-3NF.sqlite); no new tables needed
**Testing**: pytest with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.math`
**Target Platform**: Linux server (simulation engine context)
**Project Type**: Single Python package extension to existing `babylon.economics` module
**Performance Goals**: <100ms per county throughput computation; batch computation for all counties <30s
**Constraints**: Must integrate with Feature 013 MELTCalculator for national MELT; thread-safe
**Scale/Scope**: 3,143 US counties for throughput position; 20+ 2-digit NAICS sectors for depth mapping

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.2 Imperial Rent (Φ) | ✅ PASS | Spec models domestic value geography as complement to international Φ; π identifies coordination chokepoints where throughput accumulates |
| I.5 Department III | ⚠️ N/A | Domestic throughput analysis does not directly model reproductive labor; future enhancement FE-003 could add union density for λ estimation |
| II.2 Primitives vs Derived | ✅ PASS | τ_through derived from county GDP/L primitives; π derived from τ_through/τ_national; D derived from NAICS employment × depth mapping |
| II.4 Quantities vs Coefficients | ✅ PASS | π and D are coefficients (slow-evolving, annual); NAICS depth mapping is fixed structural constant |
| III.1 No Magic Constants | ✅ PASS | τ_through from BEA CAGDP1 GDP and QCEW employment; NAICS depth mapping derived from supply chain position (0=extraction to 5=finance) per economic structure |
| III.2 Falsifiability Required | ✅ PASS | SC-001-SC-007 provide testable predictions: 3000+ counties computed, Detroit validation (Oakland π > Wayne π), finance D > manufacturing D > extraction D, π × λ correlates with LA share |
| III.4 Data Source Traceability | ✅ PASS | BEA CAGDP1 county GDP (D-002), QCEW county employment by NAICS (D-003, D-004), Feature 013 national MELT (D-001), LODES commuter flows (D-005, optional) |
| IV. Metro Detroit Validation | ✅ PASS | Spec includes Wayne (26163) vs Oakland (26125) validation case: π[Oakland] > π[Wayne], D[Oakland] > D[Wayne] |
| VII.3 Determinism from Material | ✅ PASS | Throughput position is derived from material data flows, but class position still depends on institutional factors (λ) not determined purely by π |

**All gates pass. Proceeding to Phase 0 research.**

## Project Structure

### Documentation (this feature)

```text
specs/014-throughput-position/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── throughput_calculator.py
│   ├── supply_chain_analyzer.py
│   └── naics_depth_mapping.py
├── checklists/          # Validation checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/economics/
├── melt/                            # EXISTING (Feature 013)
│   ├── melt_calculator.py           # EXISTING: National MELT (τ)
│   ├── class_position.py            # EXISTING: ClassPositionClassifier
│   ├── wealth_proxy.py              # EXISTING: WealthProxyCalculator
│   └── data_sources.py              # EXISTING: BEADataSource, QCEWDataSource
├── throughput/                      # NEW: Throughput analysis module
│   ├── __init__.py                  # NEW: Module exports
│   ├── types.py                     # NEW: ThroughputMetrics, WageShareEstimate types
│   ├── calculator.py                # NEW: ThroughputCalculator service
│   ├── supply_chain.py              # NEW: SupplyChainAnalyzer, NAICS depth mapping
│   └── data_sources.py              # NEW: BEACountyGDPSource, QCEWCountyNAICSSource
└── __init__.py                      # EXTEND: Export new throughput module

src/babylon/economics/throughput/
└── adapters.py                      # NEW: SQLite adapters for BEA/QCEW data

tests/unit/economics/throughput/
├── __init__.py
├── test_calculator.py               # NEW: Unit tests for ThroughputCalculator
├── test_supply_chain.py             # NEW: Unit tests for SupplyChainAnalyzer
└── test_types.py                    # NEW: Unit tests for throughput types

tests/integration/economics/
└── test_throughput_validation.py    # NEW: Detroit validation, literature tests
```

**Structure Decision**: Single project (extends existing `babylon.economics` module). Creates new `throughput/` subpackage parallel to existing `melt/` subpackage. SQLite adapters query existing `FactBEACountyGDP` and `FactQcewAnnual` tables loaded via `mise run data:bea-county` and `mise run data:qcew`.

## Complexity Tracking

> **No violations to justify** - This feature adheres to all Constitution constraints.

## Design Decisions

### D1: Throughput vs Local MELT Distinction

**Decision**: Explicitly name and document that τ_through measures THROUGHPUT (accumulated value flow), not local value creation.

**Rationale**:
- Prevents confusion with national MELT (τ) which measures value creation rate
- τ_through for Manhattan >> τ_national because Manhattan is a coordination chokepoint, not because Manhattan workers create more value per hour
- Clear naming prevents theoretical misunderstanding

### D2: NAICS Depth Mapping as Frozen Constant

**Decision**: Implement NAICS-to-depth mapping as a frozen dictionary constant, not a configurable file.

**Rationale**:
- Depth values are theoretically derived from supply chain position, not empirically calibrated
- 20+ 2-digit NAICS sectors with fixed structural positions (extraction=0, finance=5)
- Future enhancement FE-001 can add 3-digit granularity
- Frozen constant aligns with Constitution principle that constants must be grounded

### D3: Separate throughput/ Subpackage vs Extending melt/

**Decision**: Create new `throughput/` subpackage rather than adding files to `melt/`.

**Rationale**:
- Throughput analysis is conceptually distinct from MELT/visibility/imperial rent
- Domestic geography vs international value transfer are different theoretical domains
- Clean separation enables independent testing and future development
- Follows established pattern of subpackages for distinct feature sets

### D4: County GDP via Existing FactBEACountyGDP Table

**Decision**: Create SQLite adapter that queries existing `FactBEACountyGDP` table.

**Rationale**:
- Data loader already exists: `mise run data:bea-county` (BEACountyGDPLoader)
- Data stored in `FactBEACountyGDP` with 1.99M records, 3,091 counties, 2001-2023
- Only need adapter implementing `BEACountyGDPSource` protocol
- **CRITICAL**: Must filter to `line_number=1` (All industries) to avoid 4.5x overcounting

**Validated Values (2022)**:
- National GDP: $25.56T (correct, matches actual US GDP)
- Wayne County: $113.8B
- Oakland County: $127.7B

### D5: Wage Share as Proxy (λ_proxy)

**Decision**: Implement wage share as a proxy (λ_proxy = avg_wage / τ_through) rather than true institutional λ.

**Rationale**:
- True λ requires union density, bargaining power data not in scope
- Proxy captures the wage capture rate implicitly
- Clearly marked as "proxy" with confidence levels
- Future enhancement FE-003 can incorporate BLS union density data

## Implementation Phases

### Phase 0: Research
- Analyze BEA CAGDP1 data format and API access
- Verify QCEW county-by-NAICS employment data availability
- Validate NAICS depth mapping against economic theory
- Research LODES commuter flow data for future enhancement

### Phase 1: Data Model & Contracts
- Define ThroughputMetrics container (fips, year, tau_through, pi, D, is_estimated)
- Define WageShareEstimate container (fips, naics, year, lambda_proxy, confidence)
- Define NAICSDepthMapping constant
- Define ThroughputCalculator protocol/interface
- Define SupplyChainAnalyzer protocol/interface
- Define BEACountyGDPSource protocol/interface
- Define QCEWCountyNAICSSource protocol/interface
- Document contracts in `contracts/` directory

### Phase 2: Task Generation
- Run `/speckit.tasks` to generate detailed tasks

### Phase 3: Core Implementation
- Implement NAICSDepthMapping constant (FR-003) ✅ DONE
- Implement ThroughputMetrics and WageShareEstimate types ✅ DONE
- Implement ThroughputCalculator protocol ✅ DONE
- Implement SupplyChainAnalyzer protocol ✅ DONE
- **NEW**: Implement SQLiteBEACountyGDPSource adapter (queries FactBEACountyGDP)
- **NEW**: Implement SQLiteQCEWCountyNAICSSource adapter (queries FactQcewAnnual)
- Wire adapters into DefaultThroughputCalculator and DefaultSupplyChainAnalyzer
- Implement wage share proxy calculation (FR-005)

### Phase 4: Integration
- Integrate with Feature 013 MELTCalculator for national τ (FR-006)
- Add sanity range validation per FR-008
- Implement data unavailable indicators with reasons (FR-007)
- Add batch county computation support

### Phase 5: Validation
- Implement Detroit validation case - Oakland > Wayne (SC-002)
- Implement 3000+ county coverage test (SC-001)
- Implement supply chain depth ranking tests (SC-003)
- Implement high-π wage correlation test (SC-004)
- Implement π × λ vs LA share correlation test (SC-005)
- Implement edge case coverage tests (SC-006)
- Implement retail λ < 0.15 validation (SC-007)

### Phase 6: Documentation
- Write quickstart.md with usage examples
- Update data-model.md with final implementation
- Document integration patterns with Feature 013 (MELT and Basket Visibility)
- Document Detroit validation results
