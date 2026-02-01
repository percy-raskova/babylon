# Implementation Plan: Technical Debt Cleanup & Infrastructure Hardening

**Branch**: `010-cleanup-tech-debt` | **Date**: 2026-02-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-cleanup-tech-debt/spec.md`

## Summary

Remove deprecated DearPyGui dashboard code (dpg_runner.py, DPGColors), rename `babylon.systems` to `babylon.formulas` for architectural clarity, validate logging context integration with SessionRecorder, and document TRPF Epoch 2 data requirements. This is a refactoring/cleanup spec with no new features—all changes are deletions, renames, or documentation updates.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: NetworkX 3.x, Pydantic 2.x (no new dependencies)
**Storage**: N/A (no storage changes)
**Testing**: pytest with mise run test:all
**Target Platform**: Linux/macOS development environment
**Project Type**: Single project (simulation engine)
**Performance Goals**: N/A (cleanup does not affect performance)
**Constraints**: All tests must pass; docs must build without warnings
**Scale/Scope**: ~51 import updates (21 src + 30 tests), 2 file deletions, 1 class removal, 35+ doc references

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This spec is **cleanup/refactoring** focused. Constitution compliance assessment:

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| II.5 | AI Observes, Never Controls | PASS | SessionRecorder remains read-only observer |
| II.6 | State is Data, Engine is Transformation | PASS | No changes to state/engine separation |
| VI.1 | UI Observes, Never Controls | PASS | Removing legacy UI, not adding new behavior |
| VI.2 | Color as Data | PASS | BunkerPalette retained; DPGColors (RGBA tuples for legacy DPG) removed |
| VI.6 | Semantic Invariance | PASS | BunkerPalette maintains same semantic bindings |
| III.1 | No Magic Constants | N/A | No new constants introduced |
| III.2 | Falsifiability Required | N/A | No new formulas or predictions |
| VII.8 | Decorative Visualization | PASS | Removing decorative legacy code |

**Gate Result**: PASS - No constitution violations. This is pure cleanup.

## Project Structure

### Documentation (this feature)

```text
specs/010-cleanup-tech-debt/
├── plan.md              # This file
├── research.md          # Phase 0: Import analysis, dependency mapping
├── checklists/
│   └── requirements.md  # Spec quality checklist (created during specify)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code Impact

```text
# Files to DELETE
src/babylon/ui/dpg_runner.py           # ~1500 LOC legacy DPG dashboard
tests/unit/ui/test_dpg_runner.py       # ~500 LOC legacy tests

# Files to MODIFY (class removal)
src/babylon/ui/design_system.py        # Remove DPGColors class (~60 LOC)
src/babylon/ui/__init__.py             # Update exports

# Package to RENAME
src/babylon/systems/                   # Rename to src/babylon/formulas/
├── __init__.py
└── formulas/
    ├── __init__.py
    ├── constants.py
    ├── fundamental_theorem.py
    ├── survival_calculus.py
    ├── solidarity.py
    ├── ideological_routing.py
    ├── unequal_exchange.py
    ├── dynamic_balance.py
    ├── metabolic_rift.py
    ├── trpf.py
    ├── vitality.py
    └── class_dynamics.py

# Import updates required
src/babylon/engine/systems/*.py        # 4 files
src/babylon/engine/formula_registry.py # 1 file
src/babylon/systems/formulas/*.py      # Internal imports (11 occurrences)
tests/unit/formulas/*.py               # 13 files
tests/unit/engine/*.py                 # 1 file
tests/unit/config/*.py                 # 1 file
tests/integration/system/*.py          # 1 file

# Documentation updates
docs/reference/*.rst                   # 4 files (27 occurrences)
docs/api/*.rst                         # 2 files
docs/concepts/*.rst                    # 3 files (6 occurrences)
docs/how-to/gui-development.rst        # 1 file (DPGColors refs)
```

**Structure Decision**: Existing project structure preserved. The rename `systems/` → `formulas/` clarifies the distinction between:
- `babylon.formulas` - Pure math, stateless calculations
- `babylon.engine.systems` - ECS-style Systems with state transformation

## Complexity Tracking

> No violations requiring justification. This is pure cleanup/refactoring.

---

## Phase 0: Outline & Research

### Research Questions

1. **Import Dependency Graph**: Map all files importing from `babylon.systems` to ensure complete coverage
2. **DPGColors Usage**: Verify no new dashboard code depends on DPGColors RGBA tuples
3. **Documentation Cross-References**: Identify all Sphinx cross-refs to `babylon.systems` modules
4. **Git History Considerations**: Check for pending PRs that might conflict with the rename

### Findings

**R1: Import Dependency Analysis**

| Source | Import Count | Files Affected |
|--------|--------------|----------------|
| src/babylon/systems/ (internal) | 11 | 4 formula files + __init__.py |
| src/babylon/engine/ | 5 | formula_registry.py, 4 system files |
| tests/unit/formulas/ | 26 | 13 test files |
| tests/unit/engine/ | 1 | test_formula_registry.py |
| tests/unit/config/ | 1 | test_constants_sync.py |
| tests/integration/ | 1 | test_phase1_blueprint.py |
| **Total** | **51** | **25 files** |

**R2: DPGColors Usage Analysis**

| Location | Usage | Action |
|----------|-------|--------|
| src/babylon/ui/dpg_runner.py | 85 occurrences | File deleted |
| tests/unit/ui/test_dpg_runner.py | 34 occurrences | File deleted |
| src/babylon/ui/__init__.py | 2 occurrences | Update exports |
| src/babylon/ui/design_system.py | 4 occurrences | Class definition removed |
| docs/how-to/gui-development.rst | 3 occurrences | Update to BunkerPalette |
| ai-docs/ (YAML files) | 9 occurrences | Update references |
| thoughts/ (research MD) | 2 occurrences | Historical, no update needed |

**Conclusion**: No active code outside legacy DPG uses DPGColors. Safe to remove.

**R3: Documentation Cross-References**

| Doc File | babylon.systems Refs | Action |
|----------|---------------------|--------|
| docs/reference/formulas.rst | 22 | Update module paths |
| docs/reference/topology.rst | 1 | Update cross-ref |
| docs/reference/class-dynamics.rst | 4 | Update module paths |
| docs/concepts/survival-calculus.rst | 4 | Update cross-refs |
| docs/concepts/imperial-rent.rst | 1 | Update cross-ref |
| docs/concepts/percolation-theory.rst | 1 | Update cross-ref |
| docs/api/systems.rst | 1 | Rename to formulas.rst |
| docs/api/index.rst | 1 | Update toctree |

**R4: Conflict Check**

- Current branch: `010-cleanup-tech-debt`
- No open PRs touching affected files
- Clean git status on `dev` branch

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed import during rename | Low | Medium | grep validation in SC-005, SC-006 |
| Circular import after rename | Low | High | Test import before pushing |
| Doc build failure | Medium | Low | mise run docs:strict validation |
| Breaking ai-docs references | Low | Low | Historical context, non-blocking |

---

## Phase 1: Design & Contracts

### Data Model Changes

**None** - This spec does not modify any data models. The entities remain:
- BunkerPalette (unchanged, now sole design system class)
- SessionRecorder (unchanged, validates DI compliance)
- TRPF formulas (unchanged, docstring enhancement only)

### API Contract Changes

**None** - This spec does not modify any APIs. All changes are internal restructuring:
- Package rename: `babylon.systems` → `babylon.formulas`
- Export changes: UI package no longer exports `dpg_runner`, `DPGColors`

### Quickstart

After this cleanup:

```python
# Before (deprecated)
from babylon.systems import calculate_imperial_rent
from babylon.ui import dpg_runner, DPGColors

# After (correct)
from babylon.formulas import calculate_imperial_rent
from babylon.ui import dashboard, BunkerPalette
```

### Agent Context Update

Technologies in use (no changes):
- Python 3.12+
- Pydantic 2.x (frozen models)
- NetworkX 3.x (graph)
- pytest (testing)

---

## Implementation Phases

### Phase A: Legacy DPG Removal (P1)

**Objective**: Remove all DearPyGui dashboard code

| Step | Action | Validation |
|------|--------|------------|
| A1 | Delete `src/babylon/ui/dpg_runner.py` | File not found |
| A2 | Delete `tests/unit/ui/test_dpg_runner.py` | File not found |
| A3 | Remove `DPGColors` class from `design_system.py` | grep returns 0 matches |
| A4 | Update `src/babylon/ui/__init__.py` exports | Import works |
| A5 | Update `docs/how-to/gui-development.rst` | Doc builds |
| A6 | Verify PyQt6 dashboard launches | `python -m babylon.ui.dashboard --demo` |

**Commit**: `refactor(ui): remove legacy DPG dashboard code`

### Phase B: Systems Architecture Rename (P2)

**Objective**: Rename `babylon.systems` → `babylon.formulas`

| Step | Action | Validation |
|------|--------|------------|
| B1 | git mv `src/babylon/systems` to `src/babylon/formulas` | Directory exists |
| B2 | Update internal imports in formulas/*.py (11 occurrences) | No import errors |
| B3 | Update engine imports (5 files) | No import errors |
| B4 | Update test imports (15 files, 30 occurrences) | Tests pass |
| B5 | Update Sphinx docs (8 files, 35 occurrences) | Docs build |
| B6 | Rename `docs/api/systems.rst` → `docs/api/formulas.rst` | Doc builds |
| B7 | Update `docs/api/index.rst` toctree | Doc builds |
| B8 | Update ai-docs YAML references | Grep validation |

**Commit**: `refactor(formulas): rename babylon.systems to babylon.formulas`

### Phase C: Logging Context Validation (P3)

**Objective**: Validate Spec 008 logging infrastructure integration

| Step | Action | Validation |
|------|--------|------------|
| C1 | Verify `log_context_scope` exists in `src/babylon/utils/log.py` | Function exists |
| C2 | Verify SessionRecorder uses injected metrics collector | Code review |
| C3 | Add integration test for tick context logging | Test passes |

**Commit**: `test(logging): add integration test for tick context`

### Phase D: TRPF Documentation (P4)

**Objective**: Document Epoch 2 data requirements with QCEW field mappings

| Step | Action | Validation |
|------|--------|------------|
| D1 | Add "Epoch 2 Data Requirements" section to `calculate_rate_of_profit` docstring | `grep "QCEW" src/babylon/formulas/trpf.py` |
| D2 | Document QCEW field mappings: constant_capital, variable_capital, surplus_value | Docstring contains field mappings |
| D3 | Add OCC-to-occupation relationship in `calculate_organic_composition` docstring | Docstring contains occupation reference |
| D4 | Add reference to ai-docs/epoch2-trpf.yaml specification | Cross-reference present |

**Commit**: `docs(trpf): document Epoch 2 data requirements with QCEW mappings`

---

## Success Criteria Mapping

| SC | Requirement | Validation Command |
|----|-------------|-------------------|
| SC-001 | dpg_runner.py deleted | `! test -f src/babylon/ui/dpg_runner.py` |
| SC-002 | test_dpg_runner.py deleted | `! test -f tests/unit/ui/test_dpg_runner.py` |
| SC-003 | DPGColors removed | `grep -r "class DPGColors" src/` returns empty |
| SC-004 | Package renamed | `test -d src/babylon/formulas && ! test -d src/babylon/systems` |
| SC-005 | No src imports of babylon.systems | `grep -r "from babylon.systems\|import babylon.systems" src/` returns empty |
| SC-006 | No test imports of babylon.systems | `grep -r "from babylon.systems" tests/` returns empty |
| SC-007 | All tests pass | `mise run test:all` exits 0 |
| SC-008 | Dashboard launches | `python -m babylon.ui.dashboard --demo` exits 0 |
| SC-009 | Docs build clean | `mise run docs:strict` exits 0 |
| SC-010 | TRPF docstrings have QCEW mappings | `grep -A5 "Epoch 2 Data Requirements" src/babylon/formulas/trpf.py` returns QCEW |
| SC-011 | Logging context integration | `pytest tests/integration -k log_context` exits 0 |
| SC-012 | SessionRecorder DI | `grep "def __init__.*metrics_collector" src/babylon/utils/recorder.py` returns match |

---

## Post-Phase 1 Constitution Re-check

| Article | Status | Notes |
|---------|--------|-------|
| II.5 AI Observes, Never Controls | PASS | No changes to AI/observer pattern |
| II.6 State is Data, Engine is Transformation | PASS | No changes to state/engine separation |
| VI Visual Design Principles | PASS | BunkerPalette retained with semantic bindings |
| VII.8 Decorative Visualization | PASS | Removed decorative legacy code |

**Final Gate**: PASS - Ready for task generation via `/speckit.tasks`
