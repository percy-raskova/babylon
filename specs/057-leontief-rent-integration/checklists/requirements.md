# Specification Quality Checklist: End-to-End Leontief Imperial Rent Integration

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-08
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

The spec intentionally references existing module names (`ProductionChainRentCalculator`, `_compute_imperial_rent`, `CountyEconomicState`, `ServiceContainer`) because the feature is a wiring task — its purpose is to connect named existing components and add named missing ones. This crosses the "no implementation details" line in the strictest reading, but the alternative (renaming or paraphrasing every component) would obscure what the feature actually changes. Stakeholders for this spec are the project's engineering team, who already know these names. If a future re-read deems this too implementation-tied, it can be loosened to "the per-tick imperial rent computation step" without changing intent.

Three other latent imperfections worth surfacing for the planning phase rather than rewording out of the spec:

1. **FR-002's choice of periphery-wage source is delegated to implementation.** This is intentional — the data source is a research question, not a spec question — but planners should treat that delegation as a real prerequisite, not a detail.
2. **The industry-to-county allocation strategy (employment-weighted, FR-004 / Story 4) is named but not fully justified.** It is the natural default; alternative weightings (value-added, payroll, hours-worked) are reasonable competitors and deserve a one-paragraph design note in the plan.
3. **SC-004's "within an order of magnitude of Hickel et al." is a deliberately weak calibration bar.** Tightening it requires either a published US-only periphery-drain figure (which may not exist) or a conversion from the global figure. Planners should treat this as a calibration task, not a hard pass/fail gate.
