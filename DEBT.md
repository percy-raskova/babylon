# Technical Debt Tracker

## About This Document

The purpose of this document is to manually track technical debt as it accumulates so it can be addressed.

### Definition of Technical Debt

Debt is the delta between how code is and how it should be given your current understanding.
Code that was appropriate when written becomes debt when your understanding evolves.

### Tracking Technical Debt

The standard format for a technical debt entry shall be:

```markdown
### [Short name]
- **What**: Description of the debt
- **Where**: File path to the specific file of the technical debt along with a line number
    *Example*: `src/babylon/widgets/gizmo.py:100-120`
- **Why it exists**: The historical reason (no shame)
- **Fix looks like**: What the solution would be
- **Blocked by**: Dependencies, if any
- **Priority**: Low/Medium/High
```

This prevents the "I know something's wrong somewhere" feeling and
lets you make rational prioritization decisions.

### Debt vs Aesthetic Preferences

Ask if this code prevent me from doing something I need to do, or does it just offend my taste?
The former is real debt. The latter is preference. Prioritize accordingly.

## Debts

### entity-id-proliferation ✅ RESOLVED

- **Status**: RESOLVED (2026-01-30)
- **What**: Hardcoded entity ID strings (`"C001"`, `"C002"`, etc.) proliferated across
  production code and test files before a registry pattern was established.
- **Resolution**: Created `babylon.models.entity_registry` module with canonical constants
  and migrated all production code and test files to use these constants.
- **Completed Phases**:
  - ✅ **Phase 0**: Bug fix in `decomposition.py`
  - ✅ **Phase 1**: Source file migration (`scenarios.py`, `factories.py`)
  - ✅ **Phase 2A**: Test DomainFactory (`tests/factories/domain.py`)
  - ✅ **Phase 2B**: Test file migration (78+ test files across 10 batches)
  - ✅ **Phase 3**: Tools (`tools/shared.py` already using registry)
- **Remaining legitimate occurrences** (~280 across 30 files, all intentional):
  - Docstrings/comments documenting entity ID mappings
  - Pattern validation tests (testing ID format `^C[0-9]{3}$`)
  - Error message assertions (testing output format)
  - Generic topology nodes (sequential test identifiers for graph algorithms)
  - Test-local constants for isolated mechanics tests
  - Territory IDs (`T001`-`T005`) which have no canonical registry
- **Key Files**:
  - `src/babylon/models/entity_registry.py` - Single source of truth
  - Exports: `PERIPHERY_WORKER_ID`, `COMPRADOR_ID`, `CORE_BOURGEOISIE_ID`,
    `LABOR_ARISTOCRACY_ID`, `CARCERAL_ENFORCER_ID`, `INTERNAL_PROLETARIAT_ID`

### metrics-singleton-vs-di

- **What**: `MetricsCollector` in `src/babylon/metrics/collector.py` uses the Singleton
  pattern, contradicting the project's dependency injection philosophy
- **Where**: `src/babylon/metrics/collector.py:56-66`
- **Why it exists**: Original RAG telemetry design predates the DI-first mandate
- **Fix looks like**: Either document as intentional exception OR refactor to ServiceContainer injection
- **Blocked by**: Requires tracing 20+ instantiation sites across RAG module
- **Priority**: Medium

### metrics-protocol-mismatch

- **What**: `MetricsCollectorProtocol` defines 6 methods, but RAG usage includes
  non-protocol methods (`record_metric()`, `record_cache_event()`, `record_token_usage()`, etc.)
- **Where**: `src/babylon/metrics/interfaces.py` vs actual usage in `src/babylon/rag/`
- **Why it exists**: Protocol was defined as minimal contract; implementation grew beyond it
- **Fix looks like**: Expand protocol to include all used methods OR delete the façade
- **Blocked by**: None
- **Priority**: Medium

### metrics-orphaned-orm-models

- **What**: ORM models `Metric`, `Counter`, `TimeSeries` in `models.py` are never instantiated anywhere in codebase
- **Where**: `src/babylon/metrics/models.py`
- **Why it exists**: Likely from early design that was never implemented
- **Fix looks like**: Delete dead code (after confirming no migration plan needs them)
- **Blocked by**: Confirm no planned SQLite metrics migration
- **Priority**: Low

### metrics-unused-methods

- **What**: Methods `get_counter()`, `get_gauge()`, `get_timer_stats()`, `get_metrics()` in MetricsCollector are never called
- **Where**: `src/babylon/metrics/collector.py:227-269`
- **Why it exists**: API completeness that was never utilized
- **Fix looks like**: Delete unused methods or document as future API
- **Blocked by**: None
- **Priority**: Low
