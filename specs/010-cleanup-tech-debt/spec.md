# Feature Specification: Technical Debt Cleanup & Infrastructure Hardening

**Feature Branch**: `010-cleanup-tech-debt`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "Cleanup and refactoring plan to purge technical debt and harden the nervous system (logging/utilities) infrastructure before advancing to the next epoch."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Legacy DPG Code Removal (Priority: P1)

As a developer, I want the deprecated DearPyGui dashboard code removed from the codebase, so that I don't confuse legacy components with the new God Mode (PyQt6) dashboard architecture.

**Why this priority**: Dead code creates confusion and maintenance burden. The DearPyGui runner is fully superseded by the PyQt6 dashboard, and removing it first prevents developers from accidentally working on deprecated code.

**Independent Test**: Can be fully tested by verifying the deleted files no longer exist, imports are updated, and all tests still pass.

**Acceptance Scenarios**:

1. **Given** the file `src/babylon/ui/dpg_runner.py`, **When** the cleanup is complete, **Then** the file no longer exists in the repository.
2. **Given** the test file `tests/unit/ui/test_dpg_runner.py`, **When** the cleanup is complete, **Then** the file no longer exists.
3. **Given** the class `DPGColors` in `src/babylon/ui/design_system.py`, **When** the cleanup is complete, **Then** the class no longer exists (only `BunkerPalette` remains).
4. **Given** the UI package exports in `src/babylon/ui/__init__.py`, **When** the cleanup is complete, **Then** `dpg_runner` and `DPGColors` are no longer exported.
5. **Given** the cleaned codebase, **When** I run `python -m babylon.ui.dashboard --demo`, **Then** the PyQt6 dashboard launches successfully.

______________________________________________________________________

### User Story 2 - Systems Architecture Clarification (Priority: P2)

As a developer, I want a clear separation between pure math formulas and stateful simulation systems, so that I know where to put new code and don't accidentally mix concerns.

**Why this priority**: The current `src/babylon/systems` package is confusingly named since it only re-exports formulas, while actual ECS-style systems live in `src/babylon/engine/systems`. Renaming prevents architectural drift and improves code discoverability.

**Independent Test**: Can be fully tested by verifying the old package is renamed, all imports are updated, and tests pass.

**Acceptance Scenarios**:

1. **Given** the package `src/babylon/systems`, **When** the refactoring is complete, **Then** it is renamed to `src/babylon/formulas`.
2. **Given** existing imports like `from babylon.systems import calculate_imperial_rent`, **When** the refactoring is complete, **Then** they are updated to `from babylon.formulas import calculate_imperial_rent`.
3. **Given** imports in `src/babylon/engine/systems/*.py`, **When** the refactoring is complete, **Then** they import from `babylon.formulas` instead of `babylon.systems`.
4. **Given** documentation references to `babylon.systems`, **When** the refactoring is complete, **Then** they are updated to reference `babylon.formulas`.
5. **Given** the cleaned codebase, **When** I run the full test suite, **Then** all tests pass with the updated import paths.

______________________________________________________________________

### User Story 3 - Logging Context Integration (Priority: P3)

As a debugger, I want every log message generated during a simulation tick to automatically include the tick number, so that I can trace issues without manually correlating timestamps.

**Why this priority**: This extends Spec 008 by ensuring the logging infrastructure in `src/babylon/utils/log.py` supports automatic tick correlation. Lower priority because the infrastructure already exists; this validates it works with recorder.

**Independent Test**: Can be fully tested by running a simulation and verifying log output contains tick context.

**Acceptance Scenarios**:

1. **Given** the `log_context_scope` in `src/babylon/utils/log.py`, **When** I wrap simulation tick execution, **Then** all log messages within the scope include `[Tick: N]`.
2. **Given** the `SessionRecorder` in `src/babylon/utils/recorder.py`, **When** it records metrics during a tick, **Then** it uses the metrics collector passed via ServiceContainer, not a global singleton.
3. **Given** a simulation running 10 ticks, **When** I filter logs by `tick=5`, **Then** I see only events from tick 5.

______________________________________________________________________

### User Story 4 - TRPF Data Requirements Documentation (Priority: P4)

As a simulation developer, I want the TRPF formulas to clearly document their Epoch 2 data requirements, so that I know exactly which QCEW fields map to constant_capital, variable_capital, and surplus_value when implementing the full OCC-based calculations.

**Why this priority**: This is Epoch 2 preparation. The TRPF placeholder formulas (`calculate_rate_of_profit`, `calculate_organic_composition`) exist but need clear documentation of how QCEW data will map to their parameters. Lower priority because it's documentation rather than implementation.

**Independent Test**: Can be fully tested by verifying TRPF docstrings contain explicit QCEW field mappings.

**Acceptance Scenarios**:

1. **Given** the `calculate_rate_of_profit` function, **When** I read its docstring, **Then** I find an "Epoch 2 Data Requirements" section specifying QCEW field mappings for constant_capital, variable_capital, and surplus_value.
2. **Given** the `calculate_organic_composition` function, **When** I read its docstring, **Then** I find documentation linking OCC to occupation/industry classification data.
3. **Given** a developer implementing Epoch 2 TRPF, **When** they read the docstrings, **Then** they have a clear roadmap of required data sources and transformations.

______________________________________________________________________

### Edge Cases

- **Import cycles**: Renaming `babylon.systems` to `babylon.formulas` must not create circular import issues with `babylon.engine.systems`.
- **Documentation references**: Any RST/Sphinx docs referencing `babylon.systems` must be updated to prevent broken cross-references.
- **Test fixtures**: Tests importing from `babylon.systems` must be updated; a grep for orphaned imports should find zero matches after refactoring.
- **DPG design system references**: Documentation mentioning DPGColors should be updated to reference BunkerPalette only.
- **TRPF null data**: If QCEW data is unavailable, TRPF calculations should gracefully fall back to Epoch 1 surrogate multiplier rather than failing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The file `src/babylon/ui/dpg_runner.py` MUST be deleted from the repository.
- **FR-002**: The file `tests/unit/ui/test_dpg_runner.py` MUST be deleted from the repository.
- **FR-003**: The class `DPGColors` MUST be removed from `src/babylon/ui/design_system.py`.
- **FR-004**: The file `src/babylon/ui/__init__.py` MUST be updated to remove `dpg_runner` and `DPGColors` from exports.
- **FR-005**: The package `src/babylon/systems/` MUST be renamed to `src/babylon/formulas/`.
- **FR-006**: All imports of `babylon.systems` (including submodules like `babylon.systems.formulas`) MUST be updated to `babylon.formulas`.
- **FR-007**: The `src/babylon/utils/log.py` module MUST already support `contextvars`-based tick injection (verify Spec 008 compliance).
- **FR-008**: The `src/babylon/utils/recorder.py` SessionRecorder MUST accept a metrics collector via constructor injection, not instantiate its own.
- **FR-009**: The `src/babylon/formulas/trpf.py` (post-rename) `calculate_rate_of_profit` function MUST be documented as Epoch 2 preparation with clear data requirements.
- **FR-010**: Documentation files referencing `DPGColors` or `babylon.systems` MUST be updated to reflect the new structure.
- **FR-011**: The `calculate_rate_of_profit` docstring MUST specify QCEW field mappings for constant_capital, variable_capital, and surplus_value parameters.
- **FR-012**: The `calculate_organic_composition` docstring MUST specify the relationship between OCC and QCEW occupation/industry data.

### Key Entities

- **BunkerPalette**: The canonical design system color palette (hex strings for CSS/ECharts), replacing DPGColors.
- **babylon.formulas**: The renamed package containing pure math formulas (stateless calculations).
- **babylon.engine.systems**: The existing package containing stateful ECS-style simulation systems (unaffected by this spec).
- **SessionRecorder**: The black box recorder that must use injected dependencies rather than global state.
- **TRPF formulas**: Rate of profit calculations that will connect to QCEW data in Epoch 2.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: File `src/babylon/ui/dpg_runner.py` does not exist after cleanup (verified via filesystem check).
- **SC-002**: File `tests/unit/ui/test_dpg_runner.py` does not exist after cleanup (verified via filesystem check).
- **SC-003**: Class `DPGColors` does not exist in `src/babylon/ui/design_system.py` (verified via grep).
- **SC-004**: Package `src/babylon/systems/` is renamed to `src/babylon/formulas/` (directory exists at new location, not old).
- **SC-005**: Zero occurrences of `from babylon.systems` or `import babylon.systems` in source code (verified via grep across `src/`).
- **SC-006**: Zero occurrences of `from babylon.systems` in test code (verified via grep across `tests/`).
- **SC-007**: All existing tests pass after refactoring (verified via `mise run test:all`).
- **SC-008**: The PyQt6 dashboard launches successfully via `python -m babylon.ui.dashboard --demo`.
- **SC-009**: Documentation builds without warnings for broken cross-references (verified via `mise run docs:strict`).
- **SC-010**: TRPF docstrings contain "Epoch 2 Data Requirements" section with explicit QCEW field mappings (verified via grep for "QCEW" in trpf.py docstrings).
- **SC-011**: The `log_context_scope` context manager exists in `src/babylon/utils/log.py` and an integration test verifies tick context propagation (verified via `pytest tests/integration -k log_context`).
- **SC-012**: `SessionRecorder.__init__` accepts `metrics_collector` parameter (verified via grep for `def __init__.*metrics_collector` in recorder.py).

## Assumptions

- The PyQt6 dashboard (`src/babylon/ui/dashboard/`) is the current active UI and is unaffected by DPG removal.
- Spec 008 (Infrastructure Hardening) has already implemented or will implement the logging context infrastructure; this spec validates integration.
- The 4x3 fundamental tensor structure for QCEW data is defined but may not yet be populated; TRPF connectivity is documented as forward preparation.
- No external consumers depend on `babylon.systems` import paths (internal codebase only).
- The `BunkerPalette` class provides all needed color constants; no DPG-specific RGBA tuples are required by the new dashboard.

## Dependencies

- **Spec 008**: Infrastructure Hardening must be complete or compatible for logging context validation (P3 story).
- **QCEW Loader**: Must define the data schema that TRPF formulas will consume in Epoch 2 (P4 story).
