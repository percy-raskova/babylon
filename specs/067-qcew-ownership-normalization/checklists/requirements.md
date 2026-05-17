# Specification Quality Checklist: QCEW Ownership Filter Normalization

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-16
**Feature**: [spec.md](../spec.md)

## Content Quality

- [X] No implementation details (languages, frameworks, APIs)
- [X] Focused on user value and business needs
- [X] Written for non-technical stakeholders
- [X] All mandatory sections completed

## Requirement Completeness

- [X] No [NEEDS CLARIFICATION] markers remain
- [X] Requirements are testable and unambiguous
- [X] Success criteria are measurable
- [X] Success criteria are technology-agnostic (no implementation details)
- [X] All acceptance scenarios are defined
- [X] Edge cases are identified
- [X] Scope is clearly bounded
- [X] Dependencies and assumptions identified

## Feature Readiness

- [X] All functional requirements have clear acceptance criteria
- [X] User scenarios cover primary flows
- [X] Feature meets measurable outcomes defined in Success Criteria
- [X] No implementation details leak into specification

## Validation Notes

**Pass — spec is ready for `/speckit.plan` after 2026-05-16 clarification.**

Notes on judgment calls made during drafting:

1. **"Implementation details" carved out**: The spec names two specific files (`hex_hydrator.py`, `county_aggregation.py`) and one ingestion tool (`tools/ingest_qcew_full.py`) by path. These are retained because spec-066 explicitly added the per-query filters in those exact files; "remove the filter from where spec-066 added it" is the load-bearing scope statement, not an implementation detail. SQL column names (`area_fips`, `industry_code`, `ownership_id`) likewise appear in the spec because the *external interface contract* with the table is what spec-067 reshapes; downstream consumers see those column names as part of the public contract. The line is held at "no Python classes, no internal function signatures, no specific ingestion implementation strategy."

2. **BLS publication as ground truth**: SC-006 / SC-007 / FR-006 use "BLS publication" without specifying which BLS dataset/page. The convention is well-established (QCEW Statewide and County publication PDFs/CSVs); calling it out further would be implementation detail.

3. **No [NEEDS CLARIFICATION] markers used**: every potentially-ambiguous decision has a reasonable default that follows from spec-066's design and the BLS source format. Specifically:
   - Whether to drop or mark rollup rows → spec FR-001 settles on "exclude from persisted table" with an audit log. Marking-with-discriminator was considered and rejected as more complex than the use case requires.
   - Whether to keep public-sector data → FR-005 keeps it; this matches spec-066's "private-sector only" consumer pattern and leaves the door open for future specs.
   - Whether to make ingestion re-runnable → FR-010 + SC-005 require idempotency; this matches all prior ingest specs (037, 062, 066).

4. **Clarification 2026-05-16 — NAICS scope expanded**: Q1 of the `/speckit.clarify` session resolved with Option A (expand spec-067 to cover NAICS-hierarchy rollups in addition to ownership rollups). Sections touched: title, Input, new `## Clarifications` section, User Story 1, User Story 3, Edge Cases (+2 new bullets for NAICS vintages and BLS-suppressed county-years), Functional Requirements (FR-001 / FR-003 / FR-004 / FR-005 / FR-007 expanded; new FR-011 for NAICS vintage detection), Key Entities (+2 new entities for NAICS dimension and vintage), Success Criteria (SC-001 / SC-002 / SC-004 expanded; new SC-008 for audit-report rollup-class accounting), Assumptions (paragraph 4 inverted from "out of scope" to "in scope"; new paragraph for NAICS vintage range).

5. **Analyze pass 2026-05-16 — 7 findings resolved**: cross-artifact `/speckit.analyze` surfaced 7 findings (1 HIGH, 2 MEDIUM, 4 LOW). All resolved without changing semantic scope. Spec sections touched: FR-002 (tightened), FR-009 + SC-003 (test name pinned), FR-011 (reframed), Assumptions ¶3 (factual correction). Plan touched: Technical Context Scale/Scope (estimate cleaned up), project structure (test file location + new audit-validation test). Tasks touched: T001 (extended for column-name verification), T049 / T050 / T054 (test name pinned), new T054b (reproducibility verification for SC-006). Research touched: R3 amendment note, new "Post-/speckit.analyze amendments" section. Total task count grew 69 → 70.

## Sign-off

Specification validated against quality criteria on 2026-05-16 (initial draft), re-validated 2026-05-16 (post-clarification NAICS scope expansion), and re-validated 2026-05-16 (post-analyze 7-finding resolution). Ready to proceed to `/speckit.implement`.
