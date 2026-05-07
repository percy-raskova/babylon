# Specification Quality Checklist: Causal/Temporal Invariants

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-07
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

- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
- The spec references concrete file paths and class names for traceability — these are
  not implementation prescriptions but markers for the predicates the test suite must
  observe (e.g., `_DEFAULT_SYSTEMS`, `OODASystem`, `ServiceContainer.database`,
  `RuntimePersistence`). They reflect the *current* surface; if the engine is
  refactored, the test harness moves with the surface but the invariants remain.
- Both pre-clarify ambiguities and the post-verification surprises were resolved
  in dedicated `/speckit.clarify` and post-`/speckit.analyze` rounds. The
  authoritative resolutions live in `spec.md`'s `## Clarifications` section:
  1. **Q1 (clarify)**: Material Base / Action Phase / Consequences partition →
     ADR032 13-System Material Base + OODA + 7-System Consequence (Option A).
  2. **Q2 (clarify, revised post-verification)**: US4 monotonicity contract →
     **monotonic-idempotent** (F7=B): same-payload re-persist succeeds (preserves
     existing UPSERT-retry callers in `persistence_observer.py:146` and
     `session_recorder.py:168`), different-payload re-persist raises
     `MonotonicityViolationError`.
  3. **Q3 (clarify)**: US3 patch scope → `SimulationEngine.run_tick` call boundary.
  4. **F6 (post-analyze, α)**: Reorder `_DEFAULT_SYSTEMS` so `OODASystem` runs at
     position 14 (between `MetabolismSystem` and `SurvivalSystem`), matching
     ADR032's documented partition. Required for US1+US2 to be meaningful;
     part of T004 production work.
  5. **F7 (post-analyze, B)**: Method names corrected from placeholder
     `write_state` / `read_tick` to actual API `persist_tick` / `hydrate_graph`
     across spec.md, data-model.md, contracts/, tasks.md.

- Additional `/speckit.analyze` HIGH/MEDIUM/LOW remediations applied 2026-05-07:
  - C1 (HIGH): Dropped `CausalInvariantHarness` runner class; `causal_harness.py`
    now bundles only shared event dataclasses (matches Spec 055's light-touch
    `TopologyInvariantHarness` pattern).
  - C2 (MEDIUM): Removed unused helper methods on `TickTrace`; tests use inline
    comprehensions over `spy.events`.
  - F1 (HIGH): T011 now begins with extracting
    `OODASystem._resolve_for_organization` helper method (behavior-preserving
    refactor) to give `unittest.mock.patch.object` a clean named seam.
  - F2 (MEDIUM): T020's order-independence patch target is now the
    `_collect_org_nodes` module-level helper at `ooda.py:198` (named seam).
  - F4 (MEDIUM): T019's interleaving recipe now patches the new
    `_resolve_for_organization` method to invoke `ContradictionSystem.step()`
    after the FIRST per-org call.
  - F5 (MEDIUM): Verified — `_DEFAULT_SYSTEMS` contains exactly 21 Systems
    matching the partition (resolved by inspection during F6 audit).
  - D1 (LOW): FR-007 now defers to FR-009 for the gate declaration (single
    source of truth).
  - D2 (LOW): Added AS↔Predicate cross-reference table to
    `contracts/tick_persistence_monotonic.md` and Phase 6 header in `tasks.md`.
  - B1 (LOW): T030 now includes a diagnostic-format sanity assertion per
    invariant (machine-checkable per FR-010).
  - E1 (LOW): Closed as non-issue — pytest auto-discovers profile registration
    from conftest.py without per-test-file action.
