# Release Gate Checklist: Data Preflight & Loader Unification

**Purpose**: Validate requirement quality, completeness, and consistency for release readiness
**Created**: 2026-01-31
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Depth**: Formal release gate (maximum rigor)
**Focus**: Comprehensive (all FRs, SCs, edge cases, gaps)

## Requirement Completeness

- [ ] CHK001 - Is the `VerificationProtocol` interface fully specified with method signature, parameters, and return type? [Completeness, Spec §FR-001]
- [ ] CHK002 - Are all three target loaders (CensusLoader, LodesCrosswalkLoader, TIGERCountyLoader) explicitly listed for protocol implementation? [Completeness, Spec §FR-002]
- [ ] CHK003 - Is the loader registration mechanism fully specified (explicit whitelist pattern)? [Completeness, Spec §FR-003, Clarifications]
- [ ] CHK004 - Are all four Detroit data sources (QCEW, LODES, ACS, TIGER) explicitly enumerated with file paths? [Completeness, Spec §FR-004]
- [ ] CHK005 - Is the year range (2010-2025) explicitly specified for Detroit scenario validation? [Completeness, Spec §FR-004]
- [ ] CHK006 - Are all three Detroit county FIPS codes documented (Wayne, Oakland, Macomb)? [Completeness, Assumptions]
- [ ] CHK007 - Is the simulation entry point integration location specified (`__main__.py`)? [Completeness, Spec §FR-005]
- [ ] CHK008 - Are the required report fields (file paths, hints, download URLs) explicitly defined? [Completeness, Spec §FR-006]

## Requirement Clarity

- [ ] CHK009 - Is the distinction between "hard failures" and "warnings" precisely defined with examples? [Clarity, Spec §FR-007]
- [ ] CHK010 - Is "offline mode" behavior clearly specified (skip network checks, report warnings)? [Clarity, Spec §FR-008]
- [ ] CHK011 - Is "online mode" behavior clearly specified (validate API reachability)? [Clarity, Spec §FR-008]
- [ ] CHK012 - Are Git LFS pointer detection criteria explicitly defined (byte signature pattern)? [Clarity, Spec §FR-009]
- [ ] CHK013 - Is the exit code value specified for preflight failures (non-zero, but which code)? [Ambiguity, Spec §FR-010]
- [ ] CHK014 - Is "structured report" format specified (console output format, JSON option)? [Ambiguity, Spec §FR-006]
- [ ] CHK015 - Is the protocol method name (`check_source_files`) and signature explicitly documented? [Clarity, Plan §VerificationProtocol]

## Requirement Consistency

- [ ] CHK016 - Do edge case behaviors align with FR-007 (failures vs warnings)? [Consistency, Edge Cases vs FR-007]
- [ ] CHK017 - Is empty file handling consistent between Edge Cases and Clarifications? [Consistency, Edge Cases vs Clarifications]
- [ ] CHK018 - Does the plan's loader list match the spec's FR-002 target loaders? [Consistency, Plan vs Spec §FR-002]
- [ ] CHK019 - Are Detroit scenario requirements consistent between spec §FR-004 and Assumptions? [Consistency]
- [ ] CHK020 - Is the QCEW loader included in protocol implementation (listed in scenario but not in FR-002)? [Conflict, Spec §FR-002 vs §FR-004]

## Acceptance Criteria Quality

- [ ] CHK021 - Is the 5-second performance target (SC-001) measurable with defined test conditions? [Measurability, Spec §SC-001]
- [ ] CHK022 - Is "100% of required files" (SC-002) enumerable and testable? [Measurability, Spec §SC-002]
- [ ] CHK023 - Is "single-method protocol" (SC-003) objectively verifiable? [Measurability, Spec §SC-003]
- [ ] CHK024 - Is "zero simulation crashes" (SC-004) testable with defined crash scenarios? [Measurability, Spec §SC-004]
- [ ] CHK025 - Are "actionable hints with download URLs" (SC-005) defined for each data source? [Measurability, Spec §SC-005]
- [ ] CHK026 - Is "zero regressions" (SC-006) defined with baseline test count or coverage? [Measurability, Spec §SC-006]

## Scenario Coverage

- [ ] CHK027 - Are all three user stories testable independently as specified? [Coverage, Spec §User Stories]
- [ ] CHK028 - Are acceptance scenarios for Story 1 (missing data) comprehensive for all data sources? [Coverage, Spec §Story 1]
- [ ] CHK029 - Are acceptance scenarios for Story 2 (developer interface) testable with mock loaders? [Coverage, Spec §Story 2]
- [ ] CHK030 - Are acceptance scenarios for Story 3 (Detroit validation) covering partial data states? [Coverage, Spec §Story 3]
- [ ] CHK031 - Is the "preflight passes silently" behavior (Story 1, Scenario 3) specified with output requirements? [Coverage, Spec §Story 1]

## Edge Case Coverage

- [ ] CHK032 - Is empty file (0 bytes) detection criteria and message format specified? [Edge Case, Spec §Edge Cases]
- [ ] CHK033 - Is Git LFS pointer detection and error message format specified? [Edge Case, Spec §Edge Cases]
- [ ] CHK034 - Is unset API key handling specified for each loader type (which are optional)? [Edge Case, Spec §Edge Cases]
- [ ] CHK035 - Is incompatible version/format detection criteria defined (how to detect)? [Ambiguity, Spec §Edge Cases]
- [ ] CHK036 - Is year range coverage gap behavior defined with specific thresholds? [Edge Case, Spec §Edge Cases]
- [ ] CHK037 - Is the behavior for corrupted (non-empty but invalid) files specified? [Gap, Edge Cases]
- [ ] CHK038 - Is the behavior for read permission errors on data files specified? [Gap, Edge Cases]

## Recovery & Rollback Paths

- [ ] CHK039 - Are partial preflight failure scenarios defined (some loaders pass, some fail)? [Gap, Recovery]
- [ ] CHK040 - Is the behavior specified when preflight is interrupted (Ctrl+C)? [Gap, Recovery]
- [ ] CHK041 - Is retry behavior defined for transient network errors in online mode? [Gap, Recovery]
- [ ] CHK042 - Is the behavior specified when download hints point to unavailable URLs? [Gap, Recovery]
- [ ] CHK043 - Is cleanup behavior defined if preflight creates temporary files? [Gap, Recovery]

## Non-Functional Requirements

- [ ] CHK044 - Is the 5-second performance target specified with test methodology? [NFR, Spec §SC-001]
- [ ] CHK045 - Are logging/observability requirements defined for preflight execution? [Gap, NFR]
- [ ] CHK046 - Are error message localization/i18n requirements specified or explicitly excluded? [Gap, NFR]
- [ ] CHK047 - Is thread safety / concurrent execution behavior specified? [Gap, NFR]

## Dependencies & Assumptions

- [ ] CHK048 - Is the assumption of explicit whitelist registration validated against spec clarifications? [Assumption, Clarifications]
- [ ] CHK049 - Is the dependency on existing `_is_lfs_pointer()` function documented? [Dependency, Plan]
- [ ] CHK050 - Is the dependency on existing preflight infrastructure (`PreflightCheck`, `PreflightResult`) documented? [Dependency, Plan]
- [ ] CHK051 - Are TIGER shapefile naming conventions explicitly specified (year in filename)? [Assumption, Assumptions]
- [ ] CHK052 - Is the assumption about `python -m babylon` as entry point validated? [Assumption, Assumptions]

## Traceability

- [ ] CHK053 - Do all functional requirements (FR-001 to FR-010) have corresponding acceptance scenarios? [Traceability]
- [ ] CHK054 - Do all success criteria (SC-001 to SC-006) have corresponding functional requirements? [Traceability]
- [ ] CHK055 - Are all edge cases traceable to specific functional requirements? [Traceability]
- [ ] CHK056 - Does the implementation plan cover all functional requirements? [Traceability, Plan vs Spec]

## Notes

- **CHK020**: Potential conflict - QCEW is in Detroit scenario (FR-004) but not listed in FR-002 target loaders. Needs clarification.
- **CHK035**: "Incompatible version/format" detection is specified as an edge case but detection criteria are not defined.
- **CHK037-CHK043**: Recovery path gaps identified per Q3 selection - these scenarios should be evaluated for explicit requirements or explicit exclusion.
- Items marked `[Gap]` indicate potential missing requirements that should be addressed or explicitly excluded.
- Items marked `[Ambiguity]` indicate requirements that may need clarification before implementation.
- Items marked `[Conflict]` indicate potential inconsistencies between spec sections.
