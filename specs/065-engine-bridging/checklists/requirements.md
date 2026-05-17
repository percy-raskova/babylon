# Specification Quality Checklist: Engine-Bridging

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-15
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

## Notes

- The user description explicitly anchored scope to **Michigan + Canada
  (83 counties, not tri-county)** and to **real reference data from the
  SQLite database**. Both are reflected in US1's acceptance scenarios
  (Wayne County's tick-0 `v` within ±50% of BLS QCEW) and in FR-002,
  FR-005, FR-022, and SC-005.
- Five user stories with priorities P1 → P3, each independently testable.
- Twelve measurable success criteria. SC-001 (zero empty cells) and
  SC-004 (≥5% tick-over-tick change) directly close the empirical gaps
  surfaced by the user's audit of
  `reports/sim-runs/2026-05-15T03-47-07Z/`.
- The 2026-05-15 `/speckit.clarify` session resolved five high-impact
  ambiguities (recorded in `spec.md` under `## Clarifications`):
  - **Q1**: Reference-data window mismatch → rescope canonical run to
    520 ticks / 2010-2020 (full real-data coverage).
  - **Q2**: Hex hydrator scope → upgrade in this spec (FR-002a + FR-002b).
  - **Q3**: CI gate strictness → `qa:e2e-regression` uses `--strict` by
    default (FR-012a).
  - **Q4**: Events array ordering → engine emission order (FR-018
    tightened).
  - **Q5**: `tools/shared.run_simulation` terminal surface → return the
    terminal-tick `WorldState` instance (SC-011 updated).
- Implementation details that COULD leak (Postgres tables, migration
  numbers, view definitions, Python class names) are restricted to the
  Functional Requirements section as anchors against existing code
  surfaces (II.11 compliance). The User Scenarios and Success Criteria
  sections remain technology-agnostic.
- **2026-05-15 post-foundation reconciliation**: During Phase 1+2
  review, the original `contracts/subsystem_state_tables.yaml` and
  `tasks.md` T037–T039 were found to reference WorldState fields that
  do not exist on the current model
  (`world.consciousness_simplex`, `world.demographics_per_county`,
  `world.employment_per_county`). The user-facing spec.md
  requirements were unaffected — they remain technology-agnostic. The
  implementation surface was reconciled in research.md §R10,
  data-model.md §1.6/§1.7, the two affected contract YAMLs, and
  tasks.md (T036a, T037a added; T037–T041 rewritten). The fix is a
  derivation/aggregation adapter pattern in
  `babylon.persistence.county_aggregation` + a single optional
  `SocialClass.county_fips` field. No FRs, SCs, or user stories
  changed. Spec quality checklist re-validated; all items still pass.
