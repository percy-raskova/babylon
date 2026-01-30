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

### entity-id-proliferation

- **What**: Hardcoded entity ID strings (`"C001"`, `"C002"`, etc.) are scattered across 91 files
  with 2038 total occurrences instead of using the new `entity_registry` module constants
- **Where**: Widespread across codebase:
  - 9 source files in `src/` (excluding `entity_registry.py` which is the canonical source):
    - `src/babylon/engine/scenarios.py` (34 occurrences)
    - `src/babylon/engine/factories.py`
    - `src/babylon/engine/systems/decomposition.py`
    - `src/babylon/engine/adapters/inmemory_adapter.py`
    - `src/babylon/engine/adapters/subgraph_view.py`
    - `src/babylon/engine/adapters/subgraph_filter.py`
    - `src/babylon/models/graph.py`
    - `src/babylon/models/events.py`
    - `src/babylon/models/types.py`
  - 78 test files in `tests/` (heaviest: `test_inmemory_adapter.py` with 122 occurrences)
  - 3 tools files in `tools/`
- **Why it exists**: Entity IDs were introduced ad-hoc before a registry pattern was established.
  The `entity_registry` module was created to address the DRY violation between `metrics.py`
  and `tools/shared.py`, but the broader proliferation was not addressed.
- **Fix looks like**:
  1. **Phase 1 (Source)**: Update 9 source files to import constants like
     `PERIPHERY_WORKER_ID`, `COMPRADOR_ID` from `babylon.models.entity_registry`
  1. **Phase 2 (Tests)**: Update test files to use `TestConstants` or import from registry
  1. **Phase 3 (Tools)**: Remaining tools files
- **Blocked by**: None (entity_registry module now exists as canonical source)
- **Priority**: High (prevents consistent entity ID management, risk of typos, makes
  adding new entities error-prone, violates DRY across 91 files)

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
