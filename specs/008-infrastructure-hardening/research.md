# Research: Infrastructure Hardening & Metrics Convergence

**Feature**: 008-infrastructure-hardening
**Date**: 2026-01-31

## R-001: Singleton Removal Strategy

### Question
How should the singleton pattern be removed from MetricsCollector?

### Research Conducted
- Examined current implementation in `src/babylon/metrics/collector.py`
- Identified singleton components: `_instance`, `_lock`, `__new__` override
- Found 5 legacy call sites in RAG module using `MetricsCollector()` directly
- Verified `_verify_protocol_conformance()` is type-checking helper only

### Decision
Remove `__new__` override and `_instance`/`_lock` class variables entirely. No deprecation period.

### Rationale
- User clarification explicitly requested hard removal (no deprecation)
- All 5 RAG call sites must be refactored as part of this spec
- Clean break is simpler than maintaining dual-mode behavior

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| DeprecationWarning fallback | User explicitly requested hard removal |
| Gradual migration over releases | Scope creep, adds complexity |
| Keep singleton for backward compat | Violates DI architecture |

---

## R-002: ServiceContainer Integration Pattern

### Question
How should MetricsCollector be integrated into ServiceContainer?

### Research Conducted
- Examined existing ServiceContainer pattern in `src/babylon/engine/services.py`
- Noted existing fields: `config`, `database`, `event_bus`, `formulas`, `defines`
- Verified `create()` factory method handles default instantiation

### Decision
Add `metrics: MetricsCollectorProtocol` field to ServiceContainer dataclass. Factory method `create()` instantiates real collector by default, accepts optional injection.

### Rationale
- Matches established pattern for other services
- Protocol type enables mock injection for tests
- Factory encapsulates construction, allowing customization

### Implementation Detail
```python
from babylon.metrics.interfaces import MetricsCollectorProtocol

@dataclass
class ServiceContainer:
    # ... existing fields ...
    metrics: MetricsCollectorProtocol

    @classmethod
    def create(cls, ..., metrics: MetricsCollectorProtocol | None = None):
        from babylon.metrics.collector import MetricsCollector
        return cls(
            ...,
            metrics=metrics if metrics is not None else MetricsCollector(),
        )
```

---

## R-003: Log Context Scope Integration

### Question
How should tick-context logging be integrated into SimulationEngine.run_tick()?

### Research Conducted
- Examined `src/babylon/utils/log.py` - confirmed `log_context_scope` exists
- Verified ContextVar-based implementation (thread-safe, async-safe)
- Confirmed `ContextAwareFilter` injects context into LogRecords
- Examined `run_tick()` signature - receives `context: ContextType`

### Decision
Wrap `run_tick()` body with `log_context_scope(tick=N, correlation_id=uuid)`. Generate UUID per-tick per clarification.

### Rationale
- Infrastructure already exists - just needs integration
- ContextVar propagates to nested function calls automatically
- UUID per-tick enables precise event correlation

### Challenge Identified
`run_tick()` context parameter can be `TickContext` object or dict. Need to extract tick number safely:
```python
tick = context.tick if hasattr(context, 'tick') else context.get('tick', 0)
```

---

## R-004: RAG Module Refactoring

### Question
How should the 5 RAG classes be refactored for DI compliance?

### Research Conducted
- Identified all call sites via grep:
  1. `embeddings.py:114` - EmbeddingsManager
  2. `pre_embeddings/manager.py:67` - PreEmbeddingsManager
  3. `pre_embeddings/cache_manager.py:51` - CacheManager
  4. `pre_embeddings/preprocessor.py:52` - Preprocessor
  5. `pre_embeddings/chunking.py:51` - ChunkingManager

### Decision
Add `metrics: MetricsCollectorProtocol | None = None` parameter to each constructor. If None, instantiate MetricsCollector() internally.

### Rationale
- Optional parameter preserves backward compatibility during migration
- Enables test injection of mocks
- Follows standard DI pattern

### Pattern
```python
def __init__(self, ..., metrics: MetricsCollectorProtocol | None = None):
    from babylon.metrics.collector import MetricsCollector
    self.metrics = metrics if metrics is not None else MetricsCollector()
```

---

## R-005: Dead Code Verification

### Question
Is `src/babylon/metrics/models.py` truly dead code?

### Research Conducted
- Examined file contents: SQLAlchemy models `MetricsBase`, `Metric`, `Counter`, `TimeSeries`
- Grep for imports: `from babylon.metrics.models` - NO RESULTS anywhere
- Grep for class names: Only found in the file itself
- Checked test files: No tests reference these models

### Decision
Delete `src/babylon/metrics/models.py` entirely.

### Rationale
- Models were designed for planned database persistence
- Persistence was never implemented
- Zero usage across entire codebase
- Removing reduces confusion for new contributors

### Risk Assessment
**Risk**: None. File is completely unused.

---

## R-006: Getter Method Usage Analysis

### Question
Are `get_counter`, `get_gauge`, `get_timer_stats`, `get_metrics` methods used?

### Research Conducted
- Grep for each method name across codebase
- Check test files for usage

### Preliminary Findings
These methods exist in the protocol interface but usage needs verification during implementation. Decision deferred to Phase D.

---

## Summary

| Research ID | Decision | Confidence |
|-------------|----------|------------|
| R-001 | Hard removal of singleton | High |
| R-002 | Add metrics field to ServiceContainer | High |
| R-003 | Wrap run_tick with log_context_scope | High |
| R-004 | DI pattern for RAG classes | High |
| R-005 | Delete models.py | High |
| R-006 | Defer getter analysis to implementation | Medium |
