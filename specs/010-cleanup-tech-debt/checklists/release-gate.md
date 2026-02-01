# Release Gate Checklist: Technical Debt Cleanup & Infrastructure Hardening

**Purpose**: Validate specification completeness, clarity, and consistency before implementation begins
**Created**: 2026-02-01
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)
**Depth**: Release Gate (formal sign-off)
**Focus**: All priority areas equally (P1-P4)

---

## Requirement Completeness

- [x] CHK001 - Are all files targeted for deletion explicitly listed with full paths? [Completeness, Spec §FR-001, FR-002]
- [x] CHK002 - Are all classes targeted for removal explicitly named with their containing files? [Completeness, Spec §FR-003]
- [x] CHK003 - Are all export changes specified for affected `__init__.py` files? [Completeness, Spec §FR-004]
- [x] CHK004 - Is the complete list of files requiring import updates documented? [Completeness, Plan §R1]
- [x] CHK005 - Are all documentation files requiring updates enumerated? [Completeness, Plan §R3]
- [x] CHK006 - Is the scope of TRPF documentation enhancement specified (which functions, what content)? [Completeness, Spec §FR-009, Research §R6]
- [x] CHK007 - Are all affected test files for the package rename listed? [Completeness, Plan §R1]
- [x] CHK008 - Is the complete DPGColors usage inventory documented across all file types? [Completeness, Plan §R2]

## Requirement Clarity

- [x] CHK009 - Is "package rename" specified with exact source and destination paths? [Clarity, Spec §FR-005]
- [x] CHK010 - Are the import patterns to be updated explicitly defined (e.g., `babylon.systems` vs `babylon.systems.formulas`)? [Clarity, Spec §FR-006, Plan §Quickstart]
- [x] CHK011 - Is "contextvars-based tick injection" defined with specific expected behavior? [Clarity, Spec §FR-007] — *Accepted: SC-011 defines integration test for tick context propagation*
- [x] CHK012 - Is "constructor injection" for SessionRecorder specified with expected parameter signature? [Clarity, Spec §FR-008] — *Accepted: SC-012 defines grep pattern for metrics_collector parameter*
- [x] CHK013 - Are "clear data requirements" for TRPF docstrings defined with specific content expectations? [Clarity, Research §R6]
- [x] CHK014 - Is "documentation files" scoped to specific file types (RST, MD, YAML)? [Clarity, Plan §R2, §R3]
- [x] CHK015 - Is "PyQt6 dashboard launches successfully" defined with specific validation criteria? [Clarity, Spec §SC-008] — *Accepted: Command exit code 0 is standard success criterion; --demo flag provides deterministic test*

## Requirement Consistency

- [x] CHK016 - Do FR-001 through FR-004 align with User Story 1 acceptance scenarios? [Consistency, Spec §US1]
- [x] CHK017 - Do FR-005 and FR-006 align with User Story 2 acceptance scenarios? [Consistency, Spec §US2]
- [x] CHK018 - Do FR-007 and FR-008 align with User Story 3 acceptance scenarios? [Consistency, Spec §US3]
- [x] CHK019 - Does FR-009 align with User Story 4 acceptance scenarios? [Consistency, Spec §US4] — *Resolved: US4 rescoped to documentation; FR-011/FR-012 added for QCEW field mappings*
- [x] CHK020 - Are success criteria (SC-001 to SC-010) traceable 1:1 to functional requirements? [Consistency]

## Acceptance Criteria Quality

- [x] CHK021 - Can SC-001 and SC-002 (file deletion) be objectively verified via filesystem check? [Measurability, Plan §Success Criteria Mapping]
- [x] CHK022 - Can SC-003 (class removal) be objectively verified via grep? [Measurability, Plan §Success Criteria Mapping]
- [x] CHK023 - Can SC-004 (package rename) be objectively verified via directory existence? [Measurability, Plan §Success Criteria Mapping]
- [x] CHK024 - Can SC-005 and SC-006 (import cleanup) be objectively verified via grep? [Measurability, Plan §Success Criteria Mapping]
- [x] CHK025 - Is SC-010 (TRPF docstrings) measurable or does it rely on subjective "manual review"? [Measurability, Spec §SC-010] — *Resolved: SC-010 now specifies grep verification for "QCEW" in docstrings*
- [x] CHK026 - Are validation commands specified for each success criterion? [Measurability, Plan §Success Criteria Mapping]

## Scenario Coverage

- [x] CHK027 - Are acceptance scenarios defined for the happy path of each user story? [Coverage, Spec §US1-US4]
- [x] CHK028 - Are scenarios defined for partial completion states (e.g., rename done but imports not updated)? [Coverage, Gap] — *Accepted risk: Git history allows rollback; grep validation catches incomplete renames*
- [x] CHK029 - Are scenarios defined for verifying no regression in existing functionality? [Coverage, Spec §SC-007]
- [x] CHK030 - Are scenarios defined for documentation build validation? [Coverage, Spec §SC-009]
- [x] CHK031 - Are scenarios defined for the QCEW data unavailability case mentioned in edge cases? [Coverage, Spec §Edge Cases] — *Accepted risk: P4 is documentation-only; data unavailability handled in Epoch 2 implementation*

## Edge Case Coverage

- [x] CHK032 - Are circular import prevention requirements specified for the package rename? [Edge Case, Spec §Edge Cases, Plan §Risk Assessment]
- [x] CHK033 - Are broken Sphinx cross-reference detection requirements specified? [Edge Case, Spec §SC-009]
- [x] CHK034 - Are orphaned import detection requirements specified for test fixtures? [Edge Case, Spec §SC-005, SC-006]
- [x] CHK035 - Is the TRPF fallback behavior (Epoch 1 surrogate) specified with trigger conditions? [Edge Case, Spec §Edge Cases] — *Accepted risk: P4 is documentation-only; fallback behavior deferred to Epoch 2 implementation*
- [x] CHK036 - Are requirements specified for handling ai-docs/thoughts historical references? [Edge Case, Research §R2]
- [x] CHK037 - Is the behavior specified if PyQt6 dashboard fails to launch after DPG removal? [Edge Case, Gap] — *Accepted risk: SC-008 verifies dashboard launches; failure would block merge*
- [x] CHK038 - Are requirements specified for handling partial test failures during rename? [Edge Case, Gap] — *Accepted risk: SC-007 requires all tests pass; partial failure blocks merge*

## Recovery & Rollback Paths

- [x] CHK039 - Are rollback requirements defined if package rename breaks imports? [Recovery, Gap] — *Accepted risk: git mv preserves history; git revert provides rollback*
- [x] CHK040 - Are recovery steps specified if doc build fails after updates? [Recovery, Gap] — *Accepted risk: SC-009 catches failures before merge; git history enables recovery*
- [x] CHK041 - Is git history preservation specified for the package rename operation? [Recovery, Research §R1]
- [x] CHK042 - Are requirements defined for reverting individual phases independently? [Recovery, Gap] — *Accepted risk: Each phase has distinct commit; git revert per-commit enables independent rollback*
- [x] CHK043 - Is the merge conflict risk mitigation strategy documented as a requirement? [Recovery, Research §R4]

## Non-Functional Requirements

- [x] CHK044 - Are any performance requirements specified for the cleanup (e.g., test suite runtime)? [NFR, Gap] — *Accepted: Cleanup spec; performance N/A by design*
- [x] CHK045 - Are maintainability goals for the architecture clarification quantified? [NFR, Gap] — *Accepted: Maintainability IS the goal; clear separation of formulas vs engine.systems is the metric*
- [x] CHK046 - Are documentation quality standards specified beyond "builds without warnings"? [NFR, Spec §SC-009] — *Accepted: Sphinx -W flag is industry standard; no additional quality gates needed for cleanup*
- [x] CHK047 - Is the expected reduction in codebase size/complexity documented? [NFR, Gap] — *Accepted: Plan notes ~2000 LOC deletion; not a hard requirement for cleanup*

## Dependencies & Assumptions

- [x] CHK048 - Is the assumption "PyQt6 dashboard is unaffected" validated against the codebase? [Assumption, Spec §Assumptions] — *Accepted: SC-008 validates dashboard launches; grep confirms no DPG imports in dashboard/*
- [x] CHK049 - Is the assumption "no external consumers" validated for babylon.systems imports? [Assumption, Spec §Assumptions] — *Accepted: Internal codebase only; grep covers all import validation*
- [x] CHK050 - Is the assumption "BunkerPalette provides all needed colors" validated? [Assumption, Research §R2]
- [x] CHK051 - Is the QCEW Loader dependency scoped correctly (P4 only, documentation)? [Dependency, Spec §Dependencies]
- [x] CHK052 - Are all pre-existing tests that must continue passing enumerated? [Dependency, Spec §SC-007] — *Accepted: "mise run test:all" covers entire suite; enumeration unnecessary for cleanup*

## Traceability

- [x] CHK053 - Does each functional requirement (FR-001 to FR-012) map to at least one success criterion? [Traceability] — *Resolved: SC-011 added for FR-007, SC-012 added for FR-008; FR-011/FR-012 map to SC-010*
- [x] CHK054 - Does each success criterion (SC-001 to SC-010) map to at least one functional requirement? [Traceability]
- [x] CHK055 - Are implementation phases (A-D) traceable to their corresponding user stories (P1-P4)? [Traceability, Plan §Implementation Phases]
- [x] CHK056 - Is each edge case traceable to a specific mitigation or acceptance scenario? [Traceability, Spec §Edge Cases] — *Accepted: TRPF null data deferred to Epoch 2; P4 is documentation-only*

---

## Summary

| Category | Passed | Total | Notes |
|----------|--------|-------|-------|
| Requirement Completeness | 8 | 8 | All files, classes, imports enumerated |
| Requirement Clarity | 7 | 7 | SC-011/SC-012 provide verification criteria |
| Requirement Consistency | 5 | 5 | US4 rescoped; FR-011/FR-012 added |
| Acceptance Criteria Quality | 6 | 6 | SC-010 now measurable via grep |
| Scenario Coverage | 5 | 5 | Partial completion/TRPF risks accepted |
| Edge Case Coverage | 7 | 7 | All edge cases addressed or risk accepted |
| Recovery & Rollback Paths | 5 | 5 | Git history preservation accepted as mitigation |
| Non-Functional Requirements | 4 | 4 | All NFRs accepted as N/A for cleanup spec |
| Dependencies & Assumptions | 5 | 5 | Assumptions validated or risk accepted |
| Traceability | 4 | 4 | SC-011/SC-012 added; edge cases deferred to Epoch 2 |

**Total Items**: 56
**Passed**: 56 (100%)

### Resolved Critical Gaps

1. ~~**CHK019**~~: ✅ US4 rescoped to documentation; FR-011/FR-012 added for QCEW field mappings.

2. ~~**CHK053**~~: ✅ SC-011 added for FR-007 (logging context), SC-012 added for FR-008 (SessionRecorder DI).

3. ~~**CHK025**~~: ✅ SC-010 now specifies grep verification for "QCEW" in docstrings.

### Accepted Risks (Low Impact)

All items below have been checked off with explicit risk acceptance and mitigations:

- **CHK011, CHK012, CHK015**: Clarity items now covered by SC-011, SC-012, and SC-008 validation commands
- **CHK044-CHK047**: NFRs intentionally omitted for cleanup spec
- **CHK028, CHK031, CHK035**: Scenario gaps accepted with git history as rollback
- **CHK037, CHK038**: Edge cases covered by SC-007/SC-008 blocking merge on failure
- **CHK039-CHK042**: Rollback via git history preservation
- **CHK048-CHK049, CHK052**: Assumptions validated via grep or accepted for internal codebase
- **CHK056**: TRPF edge cases deferred to Epoch 2

**Pass Threshold**: 56/56 items pass (100%). All critical gaps resolved. Ready for `/speckit.tasks`.
