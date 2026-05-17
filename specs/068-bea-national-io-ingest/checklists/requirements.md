# Specification Quality Checklist: BEA National Industry I-O Ingest

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-17
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

**Pass — spec is ready for `/speckit.clarify` or `/speckit.plan`.**

Notes on judgment calls made during drafting:

1. **Implementation details retained as scope anchors**: The spec names
   specific file paths (`src/babylon/persistence/hex_hydrator.py:107`,
   `data/input-output/`, `data/bea/loader_concordance.py`) and the
   load-bearing constant (`_INTERMEDIATE_INPUTS_FRACTION = 0.5`). These
   are retained because spec-066 explicitly placed the deferral marker
   at that exact code site; "replace the 0.5 with BEA-derived per-
   industry shares at this file" IS the load-bearing scope statement,
   not an implementation detail. Schema-level entity names (`fact_bea_*`,
   `dim_naics_bea_*`) likewise appear because the external interface
   contract with those tables is what spec-068 reshapes.

2. **No [NEEDS CLARIFICATION] markers used**: every potentially-ambiguous
   decision has a reasonable default that follows from BEA's published
   methodology and the existing spec-066/067 design:
   - BEA aggregation level → spec ships at Summary (~70 industries)
     per the Shaikh-tractability rationale carried forward from
     spec-066 R7.
   - Multi-vintage reconciliation → "use most recent vintage covering
     simulation year" matches BEA's own recommended practice.
   - NAICS→BEA concordance gaps → falls back to 2-digit sector
     aggregation; this matches BLS's own fallback pattern when 6-digit
     industries are too granular for downstream consumers.
   - Idempotency → matches all prior ingest specs (037, 062, 066, 067).

3. **Shaikh empirical band documented**: SC-006 cites Shaikh (2016)
   *Capitalism: Competition, Conflict, Crises* as the canonical
   modern-Marxian calibration source. The specific per-industry bands
   (manufacturing [1.5, 3.0], services [0.3, 1.0], retail [0.5, 1.2],
   agriculture [2.0, 5.0]) are illustrative; a validation script
   (FR-included as part of US4) will codify the actual reference
   values when implemented.

4. **Spec-068 is independent of spec-070**: explicit assumption that
   the per-industry intermediate-inputs share is orthogonal to the BLS-
   suppression issue (which affects `v`, not the composition of `c`).
   This means spec-068 can ship before spec-070's BLS amendment is
   resolved.

## Sign-off

Specification validated against quality criteria on 2026-05-17.
Ready to proceed to `/speckit.clarify` or `/speckit.plan`.
