# Data Requirements Quality Checklist: Throughput Position

**Purpose**: Validate completeness of data source requirements, suppression handling, and missing data edge cases
**Created**: 2026-02-02
**Feature**: [spec.md](../spec.md)
**Focus**: Data Requirements Quality
**Depth**: Standard (~25-35 items)
**Priority**: Completeness (gap detection)
**Evaluation Date**: 2026-02-02

## BEA CAGDP1 County GDP Requirements

- [ ] CHK001 - Are BEA API authentication requirements documented (API key handling)? [Gap, D-002]
- [ ] CHK002 - Are BEA FIPS code mapping requirements specified for Virginia independent cities? [Gap, Research §BEA Notes]
- [x] CHK003 - Is the GDP unit specification clear (nominal vs real/chained dollars)? [Clarity, FR-001] ✓ RESOLVED: "chained 2017 dollars" specified, mixing prohibited
- [x] CHK004 - Are requirements defined for handling counties with suppressed GDP data? [Completeness, Edge Cases] ✓ "Return data unavailable indicator with reason"
- [ ] CHK005 - Is the year range for supported BEA data explicitly specified (2001-2023)? [Gap, D-002]
- [ ] CHK006 - Are requirements defined for BEA API rate limiting or failure handling? [Gap]
- [ ] CHK007 - Is the data freshness requirement documented (latest available year)? [Gap]
- [ ] CHK008 - Are requirements specified for handling BEA's combined county FIPS codes (e.g., 51919)? [Gap, Research §FIPS Notes]

## QCEW County Employment Requirements

- [ ] CHK009 - Are QCEW aggregation level code requirements documented (agglvl_code = 74)? [Gap, Research §QCEW]
- [ ] CHK010 - Are ownership code filtering requirements specified (own_code = 5 for private)? [Gap, Research §QCEW]
- [ ] CHK011 - Is the ~60% suppression rate impact on completeness addressed in requirements? [Gap, Research §Data Quality]
- [x] CHK012 - Are requirements defined for handling suppressed county-NAICS combinations? [Completeness, Edge Cases] ✓ "Use available sectors, flag as partial estimate"
- [ ] CHK013 - Is the disclosure_code field handling requirement specified? [Gap]
- [x] CHK014 - Are requirements defined for quarterly vs annual data aggregation? [Completeness, D-003] ✓ Data Sources table specifies "annual" resolution
- [ ] CHK015 - Is the 5-6 month publication lag impact documented in requirements? [Gap, Research §QCEW]
- [x] CHK016 - Are requirements specified for handling missing NAICS sectors in a county? [Completeness, FR-004] ✓ Edge Cases: "Use available sectors, flag as partial estimate"

## Data Quality and Validation Requirements

- [ ] CHK017 - Are sanity range thresholds for τ_through explicitly justified with data sources? [Gap, FR-008]
- [x] CHK018 - Is the warning vs fail threshold distinction clearly defined for all metrics? [Clarity, FR-008] ✓ "expected range" vs "flag outliers/extreme values for review" distinction clear
- [x] CHK019 - Are requirements defined for flagging vs rejecting outlier values? [Completeness, FR-008] ✓ Edge Cases: "Flag as outlier for review but do not cap"
- [ ] CHK020 - Is the data quality confidence level (high/medium/low) criteria specified? [Gap, Data-Model §ThroughputMetrics]
- [x] CHK021 - Are requirements defined for λ_proxy > 1.0 detection and handling? [Completeness, Edge Cases] ✓ FR-008 + Edge Cases: "flag if > 1.0 indicating data quality issue"
- [x] CHK022 - Is the small county threshold defined for "low-confidence estimate" flagging? [Completeness, Edge Cases] ✓ RESOLVED: SUPPRESSED (<3 establishments) vs INSUFFICIENT_DATA (<1,000 employment)

## NoDataSentinel and Error Handling Requirements

- [x] CHK023 - Are distinct error messages required for GDP vs employment unavailability? [Completeness, FR-007] ✓ "descriptive reasons" requirement implies distinct messages
- [ ] CHK024 - Is the NoDataSentinel reason field content specified for each failure mode? [Gap, FR-007]
- [ ] CHK025 - Are requirements defined for partial data availability (GDP available, employment not)? [Gap, Edge Cases]
- [x] CHK026 - Is the behavior specified when national MELT (Feature 013) returns NoDataSentinel? [Completeness, FR-006] ✓ RESOLVED: Return NoDataSentinel for π only; τ_through, D, λ_proxy remain valid
- [ ] CHK027 - Are requirements defined for propagating data quality flags through computations? [Gap]

## NAICS Depth Mapping Requirements

- [x] CHK028 - Is the theoretical basis for each NAICS depth value documented? [Completeness, FR-003] ✓ Theoretical Foundation section + FR-003 table
- [ ] CHK029 - Are requirements defined for handling unknown NAICS codes (not in mapping)? [Gap, FR-004]
- [x] CHK030 - Is the manufacturing depth=1.5 averaging rationale documented? [Clarity, FR-003, A-006] ✓ A-006 explicitly documents rationale
- [ ] CHK031 - Are requirements specified for NAICS code format validation (2-digit)? [Gap]

## Integration Requirements (Feature 013)

- [x] CHK032 - Are requirements defined for MELTCalculator unavailability scenarios? [Completeness, D-001] ✓ RESOLVED: MELT is optional; graceful degradation documented in FR-006
- [x] CHK033 - Is the year alignment requirement between county data and national MELT specified? [Completeness, FR-006] ✓ FR-002 formula uses same year parameter: π[fips, year] = τ_through[fips, year] / τ[year]
- [ ] CHK034 - Are requirements defined for handling MELTCalculator validation warnings? [Gap]

## Batch Processing Requirements

- [x] CHK035 - Are requirements specified for batch computation of all ~3,143 counties? [Completeness, SC-001] ✓ "target: 3,000+ counties"
- [ ] CHK036 - Is the performance target (<30s for all counties) traceable to a requirement? [Gap, Plan §Performance]
- [ ] CHK037 - Are requirements defined for partial batch failure handling? [Gap]

## Evaluation Summary

| Category | Pass | Fail | Total |
|----------|------|------|-------|
| BEA CAGDP1 County GDP | 2 | 6 | 8 |
| QCEW County Employment | 3 | 5 | 8 |
| Data Quality and Validation | 5 | 1 | 6 |
| NoDataSentinel and Error Handling | 2 | 3 | 5 |
| NAICS Depth Mapping | 2 | 2 | 4 |
| Integration (Feature 013) | 2 | 1 | 3 |
| Batch Processing | 1 | 2 | 3 |
| **TOTAL** | **17** | **20** | **37** |

**Pass Rate**: 46% (17/37) ← Updated after resolving CHK003, CHK022, CHK026, CHK032

## Critical Gaps Requiring Spec Updates

### High Priority (blocks implementation) - ALL RESOLVED ✓
- ~~CHK003: GDP unit specification (nominal vs chained)~~ ✓ RESOLVED
- ~~CHK022: Small county threshold~~ ✓ RESOLVED
- ~~CHK026: Feature 013 failure handling~~ ✓ RESOLVED
- ~~CHK032: MELTCalculator unavailability~~ ✓ RESOLVED

### Medium Priority (affects data quality)
- CHK001, CHK006: BEA API handling - needed for data loader
- CHK002, CHK008: Virginia FIPS mapping - affects county coverage
- CHK011: Suppression rate impact on SC-001 target
- CHK020: Confidence level criteria - affects quality flagging

### Low Priority (implementation details)
- CHK009, CHK010, CHK013: QCEW field-level requirements
- CHK015: Publication lag (informational)
- CHK036: Performance target (non-functional)

## Notes

- 20 gaps remain, 17 items pass (46% pass rate)
- **All 4 high-priority gaps resolved** on 2026-02-02
- BEA/QCEW API-level details not in spec (may belong in data-model or implementation)
- Spec adequately covers edge case handling for missing data
- Theoretical foundation well-documented
- Remaining gaps are medium/low priority and can be addressed during implementation
