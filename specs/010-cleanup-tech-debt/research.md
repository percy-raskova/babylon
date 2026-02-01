# Research: Technical Debt Cleanup & Infrastructure Hardening

**Branch**: `010-cleanup-tech-debt`
**Date**: 2026-02-01
**Purpose**: Document findings from Phase 0 research to inform implementation

## R1: Import Dependency Analysis

### babylon.systems Import Locations

Total: **51 occurrences** across **25 files**

#### Source Code (21 occurrences in 10 files)

| File | Import Statement | Count |
|------|------------------|-------|
| `src/babylon/systems/__init__.py` | `from babylon.systems.formulas import ...` | 1 |
| `src/babylon/systems/formulas/__init__.py` | `from babylon.systems.formulas.X import ...` | 11 |
| `src/babylon/systems/formulas/fundamental_theorem.py` | `from babylon.systems.formulas.constants import ...` | 1 |
| `src/babylon/systems/formulas/survival_calculus.py` | `from babylon.systems.formulas.constants import ...` | 1 |
| `src/babylon/systems/formulas/ideological_routing.py` | `from babylon.systems.formulas.constants import ...` | 1 |
| `src/babylon/engine/formula_registry.py` | `from babylon.systems import formulas` | 2 |
| `src/babylon/engine/systems/economic.py` | `from babylon.systems.formulas import ...` | 1 |
| `src/babylon/engine/systems/vitality.py` | `from babylon.systems.formulas import ...` | 1 |
| `src/babylon/engine/systems/ideology.py` | `from babylon.systems.formulas import ...` | 1 |
| `src/babylon/engine/systems/metabolism.py` | `from babylon.systems.formulas import ...` | 1 |

#### Test Code (30 occurrences in 15 files)

| File | Count |
|------|-------|
| `tests/unit/formulas/test_bourgeoisie_decision.py` | 15 |
| `tests/unit/formulas/test_survival_calculus_properties.py` | 2 |
| `tests/unit/formulas/test_fundamental_theorem.py` | 1 |
| `tests/unit/formulas/test_fundamental_theorem_properties.py` | 1 |
| `tests/unit/formulas/test_survival_calculus.py` | 1 |
| `tests/unit/formulas/test_ideological_routing.py` | 1 |
| `tests/unit/formulas/test_solidarity.py` | 1 |
| `tests/unit/formulas/test_unequal_exchange.py` | 1 |
| `tests/unit/formulas/test_metabolic_rift.py` | 1 |
| `tests/unit/formulas/test_trpf.py` | 1 |
| `tests/unit/formulas/test_vitality.py` | 1 |
| `tests/unit/formulas/test_class_dynamics.py` | 1 |
| `tests/unit/engine/test_formula_registry.py` | 1 |
| `tests/unit/config/test_constants_sync.py` | 1 |
| `tests/integration/system/test_phase1_blueprint.py` | 1 |

### Decision: Package Rename Strategy

**Decision**: Use `git mv` to preserve history, then find-and-replace imports.

**Rationale**:
- `git mv` preserves file history for blame/log operations
- Single atomic operation reduces risk of partial rename
- Find-and-replace can be validated with grep before commit

**Alternatives Considered**:
- Manual rename + import updates (rejected: higher risk of missing files)
- Create new package + deprecation period (rejected: overkill for internal refactor)

---

## R2: DPGColors Usage Analysis

### Locations and Actions

| Location | Occurrences | Action | Reason |
|----------|-------------|--------|--------|
| `src/babylon/ui/dpg_runner.py` | 85 | DELETE FILE | Entire file is legacy DPG code |
| `tests/unit/ui/test_dpg_runner.py` | 34 | DELETE FILE | Tests for deleted code |
| `src/babylon/ui/__init__.py` | 2 | UPDATE | Remove from exports |
| `src/babylon/ui/design_system.py` | 4 | REMOVE CLASS | Keep BunkerPalette only |
| `docs/how-to/gui-development.rst` | 3 | UPDATE | Replace with BunkerPalette examples |
| `ai-docs/epochs/epoch1/dpg-patterns.yaml` | 7 | UPDATE | Historical reference, note deprecation |
| `ai-docs/epochs/epoch1/ui-wireframes.yaml` | 1 | UPDATE | Historical reference |
| `ai-docs/archive/epochs-overview.md` | 1 | UPDATE | Note removal |
| `thoughts/shared/research/*.md` | 2 | NO CHANGE | Historical research notes |

### Decision: DPGColors Removal Scope

**Decision**: Remove DPGColors class entirely from design_system.py.

**Rationale**:
- DPGColors provides RGBA tuples specifically for DearPyGui's color format
- BunkerPalette provides hex strings for CSS/ECharts (PyQt6 dashboard uses this)
- No active code outside legacy DPG needs RGBA tuples
- The PyQt6 dashboard (God Mode) uses BunkerPalette exclusively

**Alternatives Considered**:
- Keep DPGColors but mark deprecated (rejected: dead code with no consumers)
- Convert DPGColors methods to BunkerPalette (rejected: BunkerPalette already has equivalent)

---

## R3: Documentation Cross-References

### Sphinx Documentation Updates Required

| File | babylon.systems References | Action |
|------|---------------------------|--------|
| `docs/reference/formulas.rst` | 22 (autodoc modules) | Update module paths to babylon.formulas |
| `docs/reference/class-dynamics.rst` | 4 | Update cross-references |
| `docs/reference/topology.rst` | 1 | Update cross-reference |
| `docs/concepts/survival-calculus.rst` | 4 | Update cross-references |
| `docs/concepts/imperial-rent.rst` | 1 | Update cross-reference |
| `docs/concepts/percolation-theory.rst` | 1 | Update cross-reference |
| `docs/api/systems.rst` | 1 | RENAME to formulas.rst |
| `docs/api/index.rst` | 1 | Update toctree entry |

### Decision: Documentation Update Strategy

**Decision**: Update all references and rename systems.rst → formulas.rst.

**Rationale**:
- Sphinx autodoc requires correct module paths to generate API docs
- Broken cross-references cause build warnings/errors
- Consistent naming (formulas everywhere) reduces confusion

**Alternatives Considered**:
- Leave docs referencing old path with redirect (rejected: Sphinx doesn't support redirects)
- Create alias module (rejected: adds complexity, doesn't solve doc problem)

---

## R4: Conflict Analysis

### Current State

- **Branch**: `010-cleanup-tech-debt` (created from `dev`)
- **Parent Branch**: `dev` (clean status as of 2026-02-01)
- **Open PRs**: None touching affected files

### Files at Risk of Merge Conflicts

| File | Risk Level | Mitigation |
|------|------------|------------|
| `src/babylon/ui/__init__.py` | Low | Small file, simple changes |
| `src/babylon/engine/formula_registry.py` | Low | Import statement only |
| `docs/reference/formulas.rst` | Medium | Autodoc sections may be edited |

### Decision: Merge Strategy

**Decision**: Complete cleanup in single branch, merge to dev promptly.

**Rationale**:
- Refactoring branches should be short-lived
- Rename affects many files; long-lived branch increases conflict risk
- All changes are mechanical (find-and-replace), easy to resolve

---

## R5: Logging Context Verification

### Current State (src/babylon/utils/log.py)

The logging infrastructure already supports contextvars:
- `_log_context: ContextVar[dict[str, Any] | None]` - Thread-local context storage
- `log_context_scope(**kwargs)` - Context manager for scoped logging
- `ContextAwareFilter` - Injects context into LogRecords

### SessionRecorder Analysis (src/babylon/utils/recorder.py)

Current implementation:
- Constructor accepts `metrics_collector: TickStateRecorder` (injected)
- Does NOT instantiate its own MetricsCollector
- Uses injected collector reference stored in `self._metrics`

**Status**: FR-008 already satisfied - SessionRecorder uses DI pattern.

### Decision: Logging Integration

**Decision**: Add integration test to verify tick context propagation.

**Rationale**:
- Infrastructure exists but lacks explicit integration test
- Test documents expected behavior for future maintainers
- Validates Spec 008 compliance

---

## R6: TRPF Documentation Review

### Current Docstrings (src/babylon/systems/formulas/trpf.py)

| Function | Current Documentation | Enhancement Needed |
|----------|----------------------|-------------------|
| `calculate_trpf_multiplier` | Complete with examples | None |
| `calculate_rent_pool_decay` | Complete with examples | None |
| `calculate_rate_of_profit` | Marked as "Epoch 2 placeholder" | Add data requirements |
| `calculate_organic_composition` | Marked as "Epoch 2 placeholder" | Add data requirements |

### Decision: TRPF Documentation Enhancement

**Decision**: Enhance Epoch 2 placeholder docstrings with explicit data requirements.

**Rationale**:
- Current docstrings mention "Epoch 2" but don't specify data sources
- Developers need to know what QCEW fields map to constant_capital/variable_capital
- Clear data requirements enable future implementation

**Enhancement Plan**:
```python
# calculate_rate_of_profit docstring addition:
"""
Epoch 2 Data Requirements:
    - constant_capital: QCEW annual payroll × capital_labor_ratio (from BEA I-O tables)
    - variable_capital: QCEW annual payroll (direct)
    - surplus_value: QCEW total wages - variable_capital (simplified)

See: ai-docs/epoch2-trpf.yaml for full specification
"""
```

---

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Package Rename | `git mv` + find-and-replace | Preserves history, single atomic operation |
| DPGColors | Remove entirely | No active consumers, BunkerPalette suffices |
| Documentation | Update all refs + rename systems.rst | Sphinx requires correct paths |
| Merge Strategy | Short-lived branch, prompt merge | Minimize conflict risk |
| Logging | Add integration test | Validate Spec 008 compliance |
| TRPF | Enhance docstrings | Document Epoch 2 data requirements |
