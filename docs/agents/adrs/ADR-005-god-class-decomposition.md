# ADR-005: Decompose `postgres_runtime.py` and `engine/simulation.py`

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 5 of 6
**Tier**: T1 + T2
**Estimated effort**: 5 days
**Risk**: Medium

## Context

Two files concentrate critical-path responsibility into single classes:

| File                                          | Lines | Class             | Methods | Notes                                                                         |
| --------------------------------------------- | ----: | ----------------- | ------: | ----------------------------------------------------------------------------- |
| `src/babylon/persistence/postgres_runtime.py` |  1955 | `PostgresRuntime` |      53 | Satisfies BOTH `RuntimePersistence` AND `PostgresRuntimeExtensions` protocols |
| `src/babylon/engine/simulation.py`            |  1048 | `Simulation`      |      35 | Owns `tick()`, observer dispatch, history, error recovery, lifecycle          |

Both are textbook god classes. They aggregate cleanly separable responsibilities behind single-class facades, which:

- Makes `mypy --strict` slow (large `Mapped[...]` SQLAlchemy columns + nested generics).
- Makes targeted unit testing painful (instantiating either requires significant setup).
- Concentrates merge conflicts in one file when multiple branches touch persistence or orchestration.

Both have strong existing test coverage (`PostgresRuntime`: 150 unit + 10 contract per project memory; `Simulation`: covered by integration tests in `tests/integration/`). That coverage is the safety net that makes decomposition tractable.

## Decision

Apply **composition over monolith** to both files. Each public class becomes a thin facade that delegates to focused sub-components, each in its own file (~300–400 LOC).

### Part A — `PostgresRuntime` decomposition

```python
# src/babylon/persistence/postgres_runtime/
# ├── __init__.py            # PostgresRuntime facade (thin, ~150 LOC)
# ├── _pool.py               # connection-pool ownership + retry logic
# ├── tick_io.py             # PostgresTickIO — read/write per-tick state (~300 LOC)
# ├── archival_io.py         # PostgresArchivalIO — Parquet export, R2 upload (~300 LOC)
# ├── spatial_io.py          # PostgresSpatialIO — PostGIS hex queries (~300 LOC)
# ├── community_io.py        # PostgresCommunityIO — XGI hyperedge state (~300 LOC)
# └── trace_io.py            # PostgresTraceIO — TraceCollector impl (~200 LOC)

class PostgresRuntime:
    """Facade composing focused IO classes. Satisfies RuntimePersistence + PostgresRuntimeExtensions."""
    def __init__(self, pool: AsyncConnectionPool):
        self._tick = PostgresTickIO(pool)
        self._archival = PostgresArchivalIO(pool)
        self._spatial = PostgresSpatialIO(pool)
        self._community = PostgresCommunityIO(pool)
        self._trace = PostgresTraceIO(pool)

    # ~15 thin pass-through methods covering the public Protocol surface:
    async def write_tick(self, *args, **kwargs): return await self._tick.write(*args, **kwargs)
    async def read_tick(self, *args, **kwargs): return await self._tick.read(*args, **kwargs)
    async def query_hex(self, *args, **kwargs): return await self._spatial.query(*args, **kwargs)
    # ...
```

`PgVectorStore` already lives in its own file (`pgvector_store.py`) — leave it. Optionally move it under `postgres_runtime/vector_io.py` for symmetry; not strictly required.

### Part B — `Simulation` decomposition

```python
# src/babylon/engine/simulation/
# ├── __init__.py            # Simulation facade (thin, ~150 LOC)
# ├── orchestrator.py        # SimulationOrchestrator — runs tick() pipeline (~300 LOC)
# ├── observer_dispatch.py   # ObserverDispatcher — fanout to SimulationObserver impls (~200 LOC)
# ├── lifecycle.py           # SimulationLifecycle — start/pause/stop/reset state (~200 LOC)
# └── error_recovery.py      # SimulationRecovery — invariant rollback (~150 LOC)

class Simulation:
    """Facade. Public API stable for embedders (UI, web backend, tests)."""
    def __init__(self, ...):
        self._lifecycle = SimulationLifecycle(...)
        self._orchestrator = SimulationOrchestrator(...)
        self._observers = ObserverDispatcher(...)
        self._recovery = SimulationRecovery(...)

    def tick(self, n: int = 1) -> WorldState:
        with self._recovery.guard():
            for _ in range(n):
                state = self._orchestrator.run_tick()
                self._observers.notify(state)
        return self._lifecycle.current_state()
```

Each component is independently testable: `tests/unit/engine/simulation/test_orchestrator.py`, etc.

## Consequences

### Positive

- Each new module ≤400 LOC. mypy + ruff per-file analysis becomes faster.
- Targeted unit tests: stub `PostgresTickIO` without instantiating the whole runtime.
- Public API (`PostgresRuntime`, `Simulation`) preserved — embedders unchanged.
- Future feature work (e.g., archival pipeline completion, listed in project memory as "Phase 8 stub") localizes to `archival_io.py` instead of one 1955-line file.

### Negative / tradeoffs

- **Critical path.** Persistence and orchestration are core. Any test gap during decomposition risks production bugs.
- Adds 8–10 new files. The `__init__.py` facade in each subpackage carries non-trivial pass-through code.
- Composition introduces a small runtime overhead per call (one extra method dispatch). Negligible at simulation tick frequency (≪ kHz).

## Acceptance criteria

### Part A — postgres_runtime

- [ ] `src/babylon/persistence/postgres_runtime/` package replaces the 1955-line file.
- [ ] No file in the new package exceeds 400 LOC.
- [ ] `PostgresRuntime` facade is ≤200 LOC.
- [ ] `from babylon.persistence import PostgresRuntime` keeps working without change.
- [ ] All 150 unit + 10 contract persistence tests pass unchanged.
- [ ] Both `RuntimePersistence` and `PostgresRuntimeExtensions` Protocols still satisfied (verified via `runtime_checkable` `isinstance`).
- [ ] PersistenceObserver tests skip count unchanged (the unrelated `ShadowLaborConfig` import chain issue noted in project memory is not regressed).

### Part B — simulation

- [ ] `src/babylon/engine/simulation/` package replaces the 1048-line file.
- [ ] No file in the new package exceeds 400 LOC.
- [ ] `Simulation` facade is ≤200 LOC.
- [ ] `from babylon.engine import Simulation` keeps working.
- [ ] All integration tests in `tests/integration/` pass unchanged.
- [ ] `mise run sim:run` and `mise run sim:trace` both succeed end-to-end.

## Rollout

Strict ordering: **Part A first**, then **Part B**. Persistence churn affects fewer call sites than orchestrator churn.

### Part A — postgres_runtime (3 days)

1. **`refactor(persistence): create postgres_runtime package skeleton`**

   - Add `persistence/postgres_runtime/__init__.py` re-exporting current `PostgresRuntime`.
   - Add empty IO module files.
   - Verify `from babylon.persistence import PostgresRuntime` still works.

1. **`refactor(persistence): extract PostgresTickIO`**

   - Move tick read/write methods to `tick_io.py`.
   - `PostgresRuntime` delegates.
   - Run all persistence tests.

1. **`refactor(persistence): extract PostgresArchivalIO + PostgresSpatialIO`**

   - Same playbook for archival + spatial concerns.
   - Continue running tests after each.

1. **`refactor(persistence): extract PostgresCommunityIO + PostgresTraceIO`**

   - Final IO classes.
   - Delete the original `postgres_runtime.py`.

### Part B — simulation (2 days)

5. **`refactor(engine): create simulation package skeleton`**

   - Same shape as step 1.

1. **`refactor(engine): extract SimulationOrchestrator + ObserverDispatcher`**

   - Move tick pipeline + observer fanout.
   - Run unit + integration tests.

1. **`refactor(engine): extract SimulationLifecycle + SimulationRecovery`**

   - Final extraction.
   - Delete the original `simulation.py`.

## Test strategy

- **Pre-flight**: tag the current commit as `pre-adr-005-baseline`. Snapshot baseline metrics: `mise run qa:regression-generate`.
- **After every commit in Part A**: `pytest tests/unit/persistence/ tests/contract/persistence/`.
- **After every commit in Part B**: `pytest tests/unit/engine/ tests/integration/`.
- **Before merge**: `mise run check` + `mise run test:all` + `mise run qa:regression` (compares against `pre-adr-005-baseline`).
- **Specific contract tests**: `isinstance(PostgresRuntime(...), RuntimePersistence)` and `isinstance(..., PostgresRuntimeExtensions)` both still return `True`.
- **Smoke test**: full simulation run at small scale (`mise run sim:trace 100`). Compare CSV output byte-for-byte to baseline (deterministic seeds).

## References

- Knowledge graph nodes:
  - `file:src/babylon/persistence/postgres_runtime.py` (1955 LOC, 1 class with 53 methods)
  - `class:src/babylon/persistence/postgres_runtime.py:PostgresRuntime` (implements `RuntimePersistence` + `PostgresRuntimeExtensions`)
  - `file:src/babylon/engine/simulation.py` (1048 LOC, 1 class with 35 methods)
  - `class:src/babylon/engine/simulation.py:Simulation`
- Project memory: "Feature 037 - PostgreSQL Runtime Database: 7 commits, 10 phases complete, 150 unit + 10 contract tests passing"
- Project memory: "PersistenceObserver tests skip due to unrelated ShadowLaborConfig import chain issue"
- Project memory: "Archival pipeline (Phase 8) is stub-only — `NotImplementedError` for all 4 functions"
- Related ADRs: ADR-003 (`SystemBase` helpers will be used by `SimulationOrchestrator`), ADR-001 (precedent for facade-package shape).
- CLAUDE.md sections: "Coding Standards" (no function over ~100 lines), "Common Gotchas" (Dependency Injection Over Discovery).
