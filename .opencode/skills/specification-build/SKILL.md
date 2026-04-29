---
name: specification-build
description: Implement code with TDD discipline. Enforces deterministic hashes, model pinning, and Aleksandrov Test compliance. Never implements transition-state dependencies. Follows RED/GREEN/REFACTOR for every change.
---

# Specification Build Phase

## Purpose

Implement the ratified spec with test-driven development. This phase answers: **What is the code?**

## Prerequisites

You MUST have a ratified spec at `.specify/specs/{NNN}-{topic}/spec.md` with status RATIFIED. If the spec is DRAFT or REVIEW, do not proceed — ask the user to ratify or load `specification-specify`.

## Constitutional Constraints (P0 + P1)

### P0 (Never Drop)

- **I.19 Dialectic Primitive** — `D = (A, Ā, w, T, σ)` is irreducible. All class partitions emerge from it. The engine enforces three invariants: weight ∈ [-1, 1], type stability, `step` returns declared type.
- **I.20 Spatial Substrate** — Immutable. Claims overlay; substrate never mutates.
- **II.9 Morphism Dyadic** — Strictly dyadic morphisms. Five canonical relations only.
- **III.7 Determinism Hash** — Every tick produces deterministic hash. Same inputs → same outputs. Non-determinism is a bug.
- **III.8 Aleksandrov Test** — Every formal construct traces to material relation.
- **V Verb Atomicity** — Every verb maps to graph operation. Atomic per target instance.

### P1 (Domain-Relevant)

- **II.2 Primitives vs Derived** — Store primitives; compute derived. No derived quantities in persistence.
- **II.6 State is Data, Engine is Transformation** — `World` is frozen Pydantic. `tick()` is pure. No DB I/O during tick.
- **II.11 Subsystem Table Ownership** — Only touch tables your subsystem owns.
- **III.1 No Magic Constants** — Every number traces to source.
- **III.6 Model Pinning** — AI parsing MUST pin model version. Parsed vectors stored with source.
- **I.21 Sparrow** — State repression and player resistance use three targeting modes (centrality, singletons, cutsets).

## TDD Discipline (Mandatory)

1. **RED**: Write a failing test first. Use `@pytest.mark.red_phase` if the test is intentionally failing.
1. **GREEN**: Implement minimal code to pass.
1. **REFACTOR**: Clean up while keeping tests green.

No exceptions unless user explicitly waives TDD.

## Procedure

1. **Read Ratified Spec** — Load `.specify/specs/{NNN}-{topic}/spec.md`. Understand all interface contracts.

1. **Read Test Constants** — Load `tests/constants.py`. Use `TestConstants` (TC) for all test values. Do not use magic numbers.

1. **Write Failing Tests (RED)** — Before any implementation:

   - Create/update test file in `tests/`
   - Use `@pytest.mark.red_phase` for intentionally failing tests
   - Import from `tests.constants import TestConstants as TC`
   - Test boundary cases: type boundaries (0.0, 1.0 for Probability), edge cases, error conditions
   - Test cross-subsystem integration if applicable

1. **Implement Minimal Code (GREEN)** — Write the smallest code that makes tests pass:

   - All game objects as Pydantic `BaseModel`
   - Use constrained types: `Probability`, `Currency`, `Intensity`, `Ideology`, `Coefficient`
   - Explicit return types on all functions
   - No raw dicts
   - `model_copy()` for immutable mutations

1. **Refactor** — Improve code quality while tests remain green:

   - Extract reusable functions
   - Improve naming
   - Add docstrings (Sphinx-compatible, RST format)
   - Update `__all__` exports

1. **Run Tests** — Execute relevant tests:

   ```bash
   poetry run pytest tests/unit/test_foo.py::test_specific
   poetry run pytest -k "test_name_pattern"
   ```

   Fix failures before proceeding.

1. **Run Pre-commit** — Execute `mise run check` or `pre-commit run --files <changed-files>`.

   - Fix lint/type errors even in files you didn't modify (CI hygiene).

1. **Commit** — Use conventional commits: `type(scope): description`

   - Commit after each logical unit (bug fix, feature, refactor)
   - Never accumulate multiple units without committing.

1. **Update ai-docs** — If the work is significant, update:

   - `ai-docs/state.yaml` (test counts, component status)
   - `ai-docs/roadmap.md` (milestones)
   - `ai-docs/decisions.yaml` (new ADRs)

## Prohibitions

- NEVER implement code depending on `[TRANSITION STATE]` principles.
- NEVER mutate spatial substrate.
- NEVER store derived quantities.
- NEVER skip RED phase.
- NEVER use `test_` prefix in production code.
- NEVER leave failing tests uncommitted in a "red phase" state — either make them pass or mark them `@pytest.mark.red_phase` and commit.

## Next Phase

After implementation, proceed to `specification-validate`. The user may iterate between `build` and `specify` if implementation reveals spec issues.
