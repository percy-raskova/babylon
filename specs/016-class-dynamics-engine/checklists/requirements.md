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
- [ ] Requirements are testable and unambiguous
  - FR-001 uses "approximately" for savings rates (LA ~12%, proletariat ~3%) rather than exact values
  - FR-003 states "weighted by class-transition relevance" without specifying actual weights
  - FR-009 says "non-linearly" without quantifying the amplification model
  - Precaritization and stabilization rate computation formulas are not specified in any FR
- [ ] Success criteria are measurable
  - SC-002: "transition magnitude" is not defined (sum of rates? max single rate? total share movement?)
  - SC-003: "positive correlation across counties" is untestable with MVP hardcoded national averages (all counties get same rate)
  - SC-004: "gradual upward mobility" is not quantified (what rate of change qualifies as "gradual"?)
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
  - FR-003: composite risk weighting methodology not specified
  - FR-009: crisis amplification factors not quantified in spec (only in research.md: 2.5x/0.3x)
  - FR-002: precaritization and stabilization rate computation inputs/formulas not defined in any FR
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **3 items unchecked** after post-planning review (2026-02-05). Key issues:
  1. Several FRs contain ambiguous language ("approximately", "non-linearly", "weighted by relevance") without precise values
  2. SC-002/SC-004 use vague metrics; SC-003 is untestable with MVP data strategy
  3. Precaritization and stabilization formulas are described as pathways but never specified
- **Mitigation**: research.md Section 4-5 and Section 7 provide the missing precision (exact savings rates, crisis amplifier values, validation ranges). These should be promoted into the spec or explicitly referenced as normative.
- Bourgeoisie/petit-bourgeoisie dynamics are explicitly scoped out (FE-001, FE-002) to keep the feature focused.
- Data source availability (Eviction Lab, US Courts) is documented in Assumptions with fallback to hardcoded values for initial implementation.
- The accumulation formula in US1 acceptance scenario 1 uses $60k wage - $50k consumption = $10k surplus x 0.15 savings rate = $1,500 annually. This is intentionally simplified to demonstrate the concept; the actual formula integrates imperial rent subsidy on the consumption side.
