---
name: specification-validate
description: Create tests, checklists, and acceptance criteria. Validates against Michigan test case and tri-county backward-compat criterion. Ensures falsifiability criteria are met and determinism is preserved.
---

# Specification Validate Phase

## Purpose

Verify that implementation matches spec and satisfies constitutional test requirements. This phase answers: **Does it work and can we prove it?**

## Prerequisites

You MUST have implemented code from `specification-build`. Load the ratified spec and implementation to compare.

## Constitutional Constraints (P1)

- **III.2 Falsifiability Required** — Every formula has: prediction, null hypothesis, distinguishing observable, falsifying data. Validation MUST verify all four exist and are testable.
- **III.7 Determinism Hash** — Validation MUST include replay tests: same inputs produce same outputs. Non-determinism is a bug.
- **IV Michigan Test Case** — The model MUST reproduce observed class transitions using QCEW/Census data + theoretical mechanisms. Failure = theory or implementation wrong.
- **IV.2 Tri-County Backward-Compat** — Any statewide model MUST reproduce tri-county results when coarse-grained. Regression = implementation wrong.
- **II.6 State is Data, Engine is Transformation** — `tick()` must be pure. Validation MUST verify no side effects.

## Procedure

1. **Read Ratified Spec** — Load `.specify/specs/{NNN}-{topic}/spec.md`. Extract all testable requirements.

1. **Read Implementation** — Load the implemented code. Compare against spec contracts.

1. **Write Acceptance Criteria** — For each spec requirement, write a binary pass/fail criterion:

   - **Functional**: Given X input, produces Y output
   - **Performance**: Completes within Z milliseconds
   - **Determinism**: Same seed → same hash across 100 runs
   - **Falsifiability**: Has prediction, null hypothesis, observable, and falsifying data defined

1. **Create Test Suite** — Organize tests by marker:

   - `@pytest.mark.math` — Deterministic formulas (pure functions)
   - `@pytest.mark.ledger` — Economic/political state tests
   - `@pytest.mark.topology` — Graph/network operations
   - `@pytest.mark.integration` — Database/ChromaDB tests
   - `@pytest.mark.unit` — Default unit tests
   - `@pytest.mark.red_phase` — Intentionally failing (TDD RED)

1. **Run Full Test Suite** — Execute:

   ```bash
   mise run test:unit    # Fast gate
   mise run test:int     # Integration
   mise run test:scenario # Slow, full arcs
   ```

   Fix all failures.

1. **Run Michigan Validation** — If the change affects simulation mechanics:

   - Execute Michigan statewide scenario (83 counties)
   - Verify tri-county backward-compat when coarse-grained
   - Document any deviations with analysis: theory wrong, implementation wrong, or data wrong?

1. **Run Determinism Audit** — Execute:

   ```bash
   mise run qa:verify    # Formula correctness
   mise run qa:audit     # Health check (3 scenarios)
   ```

   Verify deterministic hashes match across runs.

1. **Create Checklist** — Write `.specify/checklists/{YYYYMMDD}-{topic}.md` with:

   - All acceptance criteria (PASS/FAIL/PENDING)
   - Test coverage summary by marker
   - Michigan validation results
   - Determinism audit results
   - Open issues / blockers

1. **Validate Falsifiability** — For every new formula:

   - Prediction stated? ✓/✗
   - Null hypothesis stated? ✓/✗
   - Distinguishing observable defined? ✓/✗
   - Falsifying data identified? ✓/✗
     If any missing, flag as spec defect and load `specification-specify`.

## Prohibitions

- Do NOT mark tests as passing if they have non-deterministic outputs.
- Do NOT skip Michigan validation for mechanics-affecting changes.
- Do NOT ignore determinism hash mismatches.
- Do NOT falsify falsifiability criteria (predictions without observables).

## Next Phase

After validation passes, proceed to `specification-govern` for constitutional compliance review. The user may iterate between `validate` and `build` if tests fail.
