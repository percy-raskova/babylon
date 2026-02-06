# Specification Quality Checklist: Class Dynamics Engine

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-02-05
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
  - ~~FR-001 "approximately"~~ → replaced with exact defaults + cross-ref to research.md §4
  - ~~FR-003 unspecified weights~~ → cross-ref to research.md §3 for component weights
  - ~~FR-009 "non-linearly"~~ → replaced with "multiplicative amplifier" + default values (2.5/0.3)
  - ~~Missing precaritization/stabilization~~ → added FR-015 (precaritization) and FR-016 (stabilization)
- [x] Success criteria are measurable
  - ~~SC-002 "transition magnitude"~~ → defined as "sum of absolute share changes across LA, proletariat, and lumpen"
  - ~~SC-003 "across counties"~~ → rewritten to "across years (2007-2020)" — testable with MVP national data
  - ~~SC-004 "gradual"~~ → replaced with "monotonically decreasing lumpen, within validation Warning bounds"
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
  - ~~FR-003 weights~~ → cross-ref to research.md §3 added
  - ~~FR-009 unquantified~~ → concrete multiplier model with defaults in spec
  - ~~FR-002 missing formulas~~ → FR-015 (precaritization) and FR-016 (stabilization) added
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **All 16 items now pass** after hybrid remediation (2026-02-05).
- **Remediation applied**: Strategy C (Hybrid) — direct fixes for behavioral ambiguities (FR-009 amplifier model, SC-002/SC-003/SC-004 metrics, FR-015/FR-016 new requirements) + cross-references to research.md for calibration values (FR-001 savings rates, FR-003 weights).
- **Prior issues** (3 items unchecked) resolved by: removing "approximately" language, defining "transition magnitude", rewriting SC-003 for year-based correlation, quantifying SC-004 with monotonicity + validation bounds, and adding FR-015/FR-016 for precaritization and stabilization.
- Bourgeoisie/petit-bourgeoisie dynamics are explicitly scoped out (FE-001, FE-002) to keep the feature focused.
- Data source availability (Eviction Lab, US Courts) is documented in Assumptions with fallback to hardcoded values for initial implementation.
- The accumulation formula in US1 acceptance scenario 1 uses $60k wage - $50k consumption = $10k surplus x 0.15 savings rate = $1,500 annually. This is intentionally simplified to demonstrate the concept; the actual formula integrates imperial rent subsidy on the consumption side.
