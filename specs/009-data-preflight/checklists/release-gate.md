# Release Gate Checklist: Data Preflight & Loader Unification

**Purpose**: Validate requirement quality, completeness, and consistency for release readiness
**Created**: 2026-01-31
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Depth**: Formal release gate (maximum rigor)
**Focus**: Comprehensive (all FRs, SCs, edge cases, gaps)

## Requirement Completeness

- [x] CHK001 - Is the `VerificationProtocol` interface fully specified with method signature, parameters, and return type? [Completeness, Spec §FR-001]
  - ✓ contracts/verification_protocol.py: `check_source_files(self, data_dir: Path, online: bool = False) -> list[PreflightCheck]`
- [x] CHK002 - Are all three target loaders (CensusLoader, LodesCrosswalkLoader, TIGERCountyLoader) explicitly listed for protocol implementation? [Completeness, Spec §FR-002]
  - ✓ spec.md FR-002 lists all three; plan.md Steps 2a/2b/2c implement each
- [x] CHK003 - Is the loader registration mechanism fully specified (explicit whitelist pattern)? [Completeness, Spec §FR-003, Clarifications]
  - ✓ Clarifications session 2026-01-31; plan.md shows VERIFICATION_LOADERS dict
- [x] CHK004 - Are all four Detroit data sources (QCEW, LODES, ACS, TIGER) explicitly enumerated with file paths? [Completeness, Spec §FR-004]
  - ✓ research.md §3 table; quickstart.md Data File Locations
- [x] CHK005 - Is the year range (2010-2025) explicitly specified for Detroit scenario validation? [Completeness, Spec §FR-004]
  - ✓ spec.md FR-004; data-model.md year_range=(2010, 2025)
- [x] CHK006 - Are all three Detroit county FIPS codes documented (Wayne, Oakland, Macomb)? [Completeness, Assumptions]
  - ✓ spec.md Assumptions: Wayne=26163, Oakland=26125, Macomb=26099
- [x] CHK007 - Is the simulation entry point integration location specified (`__main__.py`)? [Completeness, Spec §FR-005]
  - ✓ spec.md Assumptions; plan.md Step 5 targets src/babylon/__main__.py
- [x] CHK008 - Are the required report fields (file paths, hints, download URLs) explicitly defined? [Completeness, Spec §FR-006]
  - ✓ quickstart.md example output; plan.md _print_preflight_report() code

## Requirement Clarity

- [x] CHK009 - Is the distinction between "hard failures" and "warnings" precisely defined with examples? [Clarity, Spec §FR-007]
  - ✓ Edge Cases: empty files → fail; unset API keys → warn
- [x] CHK010 - Is "offline mode" behavior clearly specified (skip network checks, report warnings)? [Clarity, Spec §FR-008]
  - ✓ FR-008 + Story 2 Scenario 3: offline reports warning instead of failure
- [x] CHK011 - Is "online mode" behavior clearly specified (validate API reachability)? [Clarity, Spec §FR-008]
  - ✓ FR-008 "validate API reachability"; quickstart.md --online flag
- [x] CHK012 - Are Git LFS pointer detection criteria explicitly defined (byte signature pattern)? [Clarity, Spec §FR-009]
  - ✓ research.md §4: "version https://git-lfs.github.com/spec/v1" header
- [x] CHK013 - Is the exit code value specified for preflight failures (non-zero, but which code)? [Ambiguity, Spec §FR-010]
  - ✓ spec.md says "non-zero"; plan.md Step 5 specifies sys.exit(1)
- [ ] CHK014 - Is "structured report" format specified (console output format, JSON option)? [Ambiguity, Spec §FR-006]
  - ⚠️ Console format shown in quickstart.md; JSON option NOT specified
- [x] CHK015 - Is the protocol method name (`check_source_files`) and signature explicitly documented? [Clarity, Plan §VerificationProtocol]
  - ✓ contracts/verification_protocol.py with full docstring; plan.md Step 1

## Requirement Consistency

- [x] CHK016 - Do edge case behaviors align with FR-007 (failures vs warnings)? [Consistency, Edge Cases vs FR-007]
  - ✓ Edge Cases align: empty=fail (hard), API keys=warn (optional)
- [x] CHK017 - Is empty file handling consistent between Edge Cases and Clarifications? [Consistency, Edge Cases vs Clarifications]
  - ✓ Both say "treated as failures" / "same as missing - block simulation"
- [x] CHK018 - Does the plan's loader list match the spec's FR-002 target loaders? [Consistency, Plan vs Spec §FR-002]
  - ✓ Both list: CensusLoader, LodesCrosswalkLoader, TIGERCountyLoader
- [x] CHK019 - Are Detroit scenario requirements consistent between spec §FR-004 and Assumptions? [Consistency]
  - ✓ FR-004 lists data sources; Assumptions adds county FIPS and paths
- [ ] CHK020 - Is the QCEW loader included in protocol implementation (listed in scenario but not in FR-002)? [Conflict, Spec §FR-002 vs §FR-004]
  - ❌ CONFLICT: FR-002 lists 3 loaders but FR-004 Detroit needs 4 sources (including QCEW). Plan Step 4 mitigates by calling existing _check_qcew().

## Acceptance Criteria Quality

- [ ] CHK021 - Is the 5-second performance target (SC-001) measurable with defined test conditions? [Measurability, Spec §SC-001]
  - ⚠️ Target stated but no test methodology (machine specs, cold/warm start)
- [x] CHK022 - Is "100% of required files" (SC-002) enumerable and testable? [Measurability, Spec §SC-002]
  - ✓ Files enumerated in research.md §3 table and quickstart.md
- [x] CHK023 - Is "single-method protocol" (SC-003) objectively verifiable? [Measurability, Spec §SC-003]
  - ✓ contracts/verification_protocol.py shows exactly one method
- [ ] CHK024 - Is "zero simulation crashes" (SC-004) testable with defined crash scenarios? [Measurability, Spec §SC-004]
  - ⚠️ Outcome clear but specific crash test scenarios not defined
- [x] CHK025 - Are "actionable hints with download URLs" (SC-005) defined for each data source? [Measurability, Spec §SC-005]
  - ✓ quickstart.md shows URLs; plan.md Steps 2a/2b/2c include URLs in hints
- [ ] CHK026 - Is "zero regressions" (SC-006) defined with baseline test count or coverage? [Measurability, Spec §SC-006]
  - ⚠️ "All existing tests pass" stated but no baseline count specified

## Scenario Coverage

- [x] CHK027 - Are all three user stories testable independently as specified? [Coverage, Spec §User Stories]
  - ✓ Each story has "Independent Test" section explaining how to test
- [ ] CHK028 - Are acceptance scenarios for Story 1 (missing data) comprehensive for all data sources? [Coverage, Spec §Story 1]
  - ⚠️ Only LODES and TIGER shown in examples; QCEW and ACS not explicit
- [x] CHK029 - Are acceptance scenarios for Story 2 (developer interface) testable with mock loaders? [Coverage, Spec §Story 2]
  - ✓ "testable with mock loaders" stated; scenarios describe protocol behavior
- [x] CHK030 - Are acceptance scenarios for Story 3 (Detroit validation) covering partial data states? [Coverage, Spec §Story 3]
  - ✓ Scenario 3: "partial Detroit data (e.g., QCEW present but LODES missing)"
- [ ] CHK031 - Is the "preflight passes silently" behavior (Story 1, Scenario 3) specified with output requirements? [Coverage, Spec §Story 1]
  - ⚠️ "Silently" is ambiguous - no stdout? info log? needs clarification

## Edge Case Coverage

- [x] CHK032 - Is empty file (0 bytes) detection criteria and message format specified? [Edge Case, Spec §Edge Cases]
  - ✓ "0 bytes" criteria; message: "File exists but is empty" in quickstart.md
- [x] CHK033 - Is Git LFS pointer detection and error message format specified? [Edge Case, Spec §Edge Cases]
  - ✓ research.md §4 pattern; quickstart.md shows "Git LFS pointer" message
- [x] CHK034 - Is unset API key handling specified for each loader type (which are optional)? [Edge Case, Spec §Edge Cases]
  - ✓ CENSUS_API_KEY → warn (optional); plan.md Step 2c shows status="warn"
- [ ] CHK035 - Is incompatible version/format detection criteria defined (how to detect)? [Ambiguity, Spec §Edge Cases]
  - ❌ Listed as edge case but detection method not defined
- [x] CHK036 - Is year range coverage gap behavior defined with specific thresholds? [Edge Case, Spec §Edge Cases]
  - ✓ "fail only if zero years available"; partial = warning
- [ ] CHK037 - Is the behavior for corrupted (non-empty but invalid) files specified? [Gap, Edge Cases]
  - ❌ GAP: Only empty (0 bytes) handled; corrupt content not addressed
- [ ] CHK038 - Is the behavior for read permission errors on data files specified? [Gap, Edge Cases]
  - ❌ GAP: Permission errors not addressed

## Recovery & Rollback Paths

- [x] CHK039 - Are partial preflight failure scenarios defined (some loaders pass, some fail)? [Gap, Recovery]
  - ✓ Story 3 Scenario 3 covers partial data; PreflightResult.failures handles mixed results
- [ ] CHK040 - Is the behavior specified when preflight is interrupted (Ctrl+C)? [Gap, Recovery]
  - ❌ GAP: Not addressed
- [ ] CHK041 - Is retry behavior defined for transient network errors in online mode? [Gap, Recovery]
  - ❌ GAP: Not addressed
- [ ] CHK042 - Is the behavior specified when download hints point to unavailable URLs? [Gap, Recovery]
  - ❌ GAP: Not addressed (hints are static, not validated)
- [x] CHK043 - Is cleanup behavior defined if preflight creates temporary files? [Gap, Recovery]
  - ✓ N/A - data-model.md: "Preflight is stateless. No persistent state changes."

## Non-Functional Requirements

- [ ] CHK044 - Is the 5-second performance target specified with test methodology? [NFR, Spec §SC-001]
  - ⚠️ Target stated; plan.md notes "I/O bound on file existence checks" but no methodology
- [ ] CHK045 - Are logging/observability requirements defined for preflight execution? [Gap, NFR]
  - ❌ GAP: Not addressed
- [ ] CHK046 - Are error message localization/i18n requirements specified or explicitly excluded? [Gap, NFR]
  - ❌ GAP: Not addressed (assume English-only for MVP)
- [ ] CHK047 - Is thread safety / concurrent execution behavior specified? [Gap, NFR]
  - ❌ GAP: Not addressed (preflight is sequential)

## Dependencies & Assumptions

- [x] CHK048 - Is the assumption of explicit whitelist registration validated against spec clarifications? [Assumption, Clarifications]
  - ✓ Clarifications: "Explicit registration (whitelist)"; plan.md VERIFICATION_LOADERS
- [x] CHK049 - Is the dependency on existing `_is_lfs_pointer()` function documented? [Dependency, Plan]
  - ✓ research.md §4 references cbsa_parser._is_lfs_pointer()
- [x] CHK050 - Is the dependency on existing preflight infrastructure (`PreflightCheck`, `PreflightResult`) documented? [Dependency, Plan]
  - ✓ data-model.md: "PreflightCheck (existing)" and "PreflightResult (existing)"
- [x] CHK051 - Are TIGER shapefile naming conventions explicitly specified (year in filename)? [Assumption, Assumptions]
  - ✓ research.md §3: tl_2024_us_county.shp; plan.md notes "hardcoded for now"
- [x] CHK052 - Is the assumption about `python -m babylon` as entry point validated? [Assumption, Assumptions]
  - ✓ Verified: src/babylon/__main__.py exists and is the entry point

## Traceability

- [x] CHK053 - Do all functional requirements (FR-001 to FR-010) have corresponding acceptance scenarios? [Traceability]
  - ✓ FR-001→Story2, FR-002→Story2, FR-003→Clarifications, FR-004→Story3, FR-005→Story1, FR-006→Story1, FR-007→EdgeCases, FR-008→Story2.3, FR-009→EdgeCases, FR-010→Story1
- [ ] CHK054 - Do all success criteria (SC-001 to SC-006) have corresponding functional requirements? [Traceability]
  - ⚠️ SC-001 (5s) and SC-006 (regressions) are NFRs without explicit FRs
- [x] CHK055 - Are all edge cases traceable to specific functional requirements? [Traceability]
  - ✓ Empty→FR-006/FR-007, LFS→FR-009, API keys→FR-007, Year range→FR-004
- [x] CHK056 - Does the implementation plan cover all functional requirements? [Traceability, Plan vs Spec]
  - ✓ Steps 1-6 map to all 10 FRs (see plan.md Implementation Details)

## Notes

### Summary

**Passed**: 40/56 items (71%)
**Failed/Gaps**: 16/56 items (29%)

### Critical Issues

- **CHK020**: CONFLICT - QCEW is in Detroit scenario (FR-004) but not listed in FR-002 target loaders. Plan mitigates by calling existing `_check_qcew()` in run_scenario_preflight().
- **CHK035**: "Incompatible version/format" detection is specified as an edge case but detection criteria are not defined.

### Gaps to Address Before Implementation

| Item | Gap | Recommended Resolution |
|------|-----|------------------------|
| CHK014 | JSON output format not specified | Add optional --json flag or explicitly exclude |
| CHK021/CHK044 | 5-second performance: no test methodology | Define: "cold start, spinning disk, 4 data sources" |
| CHK024 | Crash scenarios not defined | Add integration test: "run Detroit with all data present" |
| CHK026 | No baseline test count | Run `pytest tests/unit/data/test_preflight.py -v --collect-only` to establish baseline |
| CHK028 | Story 1 only shows LODES/TIGER examples | Add QCEW and ACS examples |
| CHK031 | "Silently" behavior ambiguous | Clarify: "no stdout output when ok=True" |
| CHK037 | Corrupted files not handled | Add: "Defer format validation to loader; preflight only checks existence/size/LFS" |
| CHK038 | Permission errors not handled | Add: "Report as fail with hint: check file permissions" |
| CHK040-CHK042 | Interrupt/retry/URL validation gaps | Explicitly exclude from MVP scope |
| CHK045-CHK047 | Logging/i18n/threading gaps | Explicitly exclude from MVP scope |

### Items Correctly Left Unchecked

Items marked `[Gap]` indicate requirements intentionally deferred or explicitly excluded.
Items marked `[Ambiguity]` need clarification before implementation proceeds.
Items marked `[Conflict]` indicate inconsistencies requiring spec update.
