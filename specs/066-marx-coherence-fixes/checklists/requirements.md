# Specification Quality Checklist: Marx-Coherence Fixes

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

## Validation Notes

Each item passes with the following caveats and explicit reasoning:

### Content Quality

- **Implementation details**: The spec references file paths (`hex_hydrator.py:373`, `bridge._build_per_county_entities`) and class names (`ConsciousnessSystem`, `SimulationEngine`, `IdeologicalProfile`) inside Functional Requirements. These are not "implementation choices to be made" — they are *existing-project landmarks* that locate where the bugs live. The spec does not prescribe new implementation choices; it identifies bug sites in already-shipped code. This pattern is consistent with how spec-065 itself referenced existing bridge / runner modules.
- **Marxist terminology**: The spec uses heavy Marxist political-economy terminology (`c`, `v`, `s`, `organic composition`, `rate of profit`, `ternary simplex`, `imperial rent Φ`). This *is* the project's domain language per `CLAUDE.md` ("Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory"); the spec's stakeholders are political-economy researchers fluent in this vocabulary. Marx's canonical chapter citations (Vol I Ch 7/8/9, Vol III Ch 13) are provided so a stakeholder can verify identities against primary source.

### Requirement Completeness

- **Testability**: Every FR includes a measurable threshold:
  - FR-001 / FR-019: `c + v + s = W ± $1`
  - FR-005 / FR-006: employment `[3.5M, 4.8M]`
  - FR-009: `energy_stock != raw_material_stock` for ≥50% of counties
  - FR-010 / FR-012: `(0.05, 0.50, 0.45) ± 1e-9`, `r+l+f = 1.0 ± 1e-9`
  - FR-014: `≥5%` relative change tick 0 vs tick 519
  - FR-015: Pearson correlation `< 0.95`
  - FR-018: per-tick wallclock `≤ 10 seconds` (relaxed from `≤ 5 seconds` per /speckit.analyze C2 to match SC-011)
  - FR-021: state rate of profit `[0.20, 0.50]`
- **Tech-agnostic SC**: The Success Criteria reference `summary.json` and `trace.csv` as the user-facing observable contracts (these are documented in the spec-065 quickstart / summary.json contract — they are user-facing artifacts, not implementation choices). Test file paths in SC-013 / SC-015 are similarly user-facing CI deliverables, not new implementation choices.
- **Edge cases**: 5 distinct edge cases covered: negative residual surplus, missing reference data, engine-system exception, ideology drift outside simplex, zero-population county.

### Feature Readiness

- **Acceptance criteria mapping**: Every FR (FR-001 through FR-024) maps to either a User Story acceptance scenario, a Success Criterion, or both. For example:
  - FR-001 ↔ US1.1 + US1.3 + US1.4 ↔ SC-001 + SC-003 + SC-004
  - FR-014 ↔ US2.1 ↔ SC-005 + SC-013
  - FR-010 ↔ US3.1 ↔ SC-009
- **MVP path**: US1 (surplus value > 0) and US2 (consciousness evolves) are jointly the MVP. Either standalone delivers measurable progress. US3 / US4 / US5 are independent slices that each close one bug category.

## Conclusion

**All checklist items PASS.** No iteration needed. Spec is ready for `/speckit.clarify` (optional) or `/speckit.plan`.
