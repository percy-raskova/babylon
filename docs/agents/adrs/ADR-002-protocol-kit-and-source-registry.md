# ADR-002: `protocol_kit` + `SourceRegistry` for the Protocol+Default pattern

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 2 of 6
**Tier**: T1
**Estimated effort**: 2 days
**Risk**: Low

## Context

Babylon has 112 `Protocol` classes and 61 `Default*` implementations spread across 15+ economics submodules and `infrastructure/`. The pattern is essentially codegen-grade repetitive:

```python
# In every economics/*/data_sources.py:
class FooSource(Protocol):
    def get_foo(self, year: int) -> float | None: ...

# In every economics/*/calculator.py (or sibling):
class DefaultFooSource:
    def __init__(self, db_path: str): self._cache = {}; self._db = sqlite3.connect(db_path)
    def get_foo(self, year): return self._cache.setdefault(year, self._db.execute(...).fetchone())

# Stitched by economics/factory.py (662 lines, 7 hand-rolled create_* fns):
def create_economics_services(defines): return EconomicsServices(
    bea_source=DefaultBEASource(...),
    qcew_source=DefaultQCEWSource(...),
    ...
)
```

Default-class distribution by package (from `class:` nodes in the graph):

| Package                                               | Default\* classes |
| ----------------------------------------------------- | ----------------: |
| `economics/tensor_hierarchy/`                         |                11 |
| `infrastructure/`                                     |                 7 |
| `economics/substrate/`                                |                 6 |
| `economics/melt/`                                     |                 6 |
| `economics/lifecycle/`                                |                 5 |
| `economics/dynamics/`                                 |                 5 |
| `economics/gamma/`                                    |                 4 |
| `economics/credit/`                                   |                 3 |
| `economics/throughput/`, `economics/rent/`            |            2 each |
| `economics/{working_day,tick,reserve_army,monetary}/` |            1 each |

Per the project memory: "All calculators use `Protocol` for DI + `DefaultXxxCalculator` concrete class". The pattern works, but the repetition costs:

- Boilerplate `__init__(db_path: str)` and per-class LRU caches.
- `economics/factory.py` at 662 LOC manually wiring sources for every subdomain.
- Adding a new economic concept submodule requires ~5 files of repeated structure.

## Decision

Introduce a small core kit at `src/babylon/core/protocol_kit.py` and a `SourceRegistry` that replaces the manual `create_*_services` factory functions.

### `protocol_kit.py` — shared scaffolding

```python
from typing import Protocol, runtime_checkable, TypeVar, Generic, Callable
from babylon.domain.economics.tensor import NoDataSentinel  # falsy sentinel, already exists

T = TypeVar("T")

@runtime_checkable
class DataSource(Protocol):
    """Marker protocol: every source has a name for registry lookup."""
    name: str

class CachedSource(Generic[T]):
    """Mixin/ABC: LRU keyed by call args + NoDataSentinel handling.

    Subclasses implement `_fetch(*args, **kwargs) -> T | None` and call
    `self._resolve(key, lambda: self._fetch(...))` to get cached values.
    """
    def __init__(self, *, max_entries: int = 1024) -> None:
        self._cache: dict[tuple, T | NoDataSentinel] = {}
        self._max = max_entries
    def _resolve(self, key: tuple, fetch: Callable[[], T | None]) -> T | NoDataSentinel:
        if key in self._cache:
            return self._cache[key]
        value = fetch()
        result = value if value is not None else NoDataSentinel(reason=f"no data for {key}")
        if len(self._cache) >= self._max:
            self._cache.pop(next(iter(self._cache)))  # simple FIFO eviction
        self._cache[key] = result
        return result
```

### `SourceRegistry` — replace the factory functions

```python
from typing import Protocol
from collections.abc import Callable

class SourceRegistry:
    """Type-keyed registry for Protocol implementations.

    Replaces the 7 create_*_services() functions in economics/factory.py.
    Lookup by Protocol type + (optional) variant name.
    """
    def __init__(self) -> None:
        self._impls: dict[tuple[type, str], Callable[[], object]] = {}

    def register(self, protocol: type, factory: Callable[[], object], *, variant: str = "default") -> None:
        self._impls[(protocol, variant)] = factory

    def get(self, protocol: type, *, variant: str = "default") -> object:
        try:
            return self._impls[(protocol, variant)]()
        except KeyError as exc:
            raise LookupError(f"No {variant} impl registered for {protocol.__name__}") from exc

    def builtin_economics(self) -> "SourceRegistry":
        """Register all builtin Default* implementations. Mirrors current factory.py."""
        from babylon.domain.economics.melt.data_sources import BEADataSource, QCEWDataSource, CPIDataSource
        from babylon.domain.economics.melt.adapters import DefaultBEASource, DefaultQCEWSource, DefaultCPISource
        self.register(BEADataSource, DefaultBEASource)
        self.register(QCEWDataSource, DefaultQCEWSource)
        self.register(CPIDataSource, DefaultCPISource)
        # ... (one line per existing Default* class, ~61 entries)
        return self
```

### Migration shape per submodule

`economics/melt/data_sources.py` stays as-is (Protocol definitions are good).
`economics/melt/adapters.py` and similar files lose their `__init__` boilerplate by inheriting `CachedSource[float]` (or whatever their value type is).
`economics/factory.py` shrinks from 662 LOC of bespoke wiring to a single `SourceRegistry().builtin_economics()` call.

## Consequences

### Positive

- One canonical caching strategy across 61 Default\* implementations.
- Adding a new submodule: one `*Defines` class, one Protocol, one `Default*` class, one registry line. No factory edits.
- Tests can swap implementations cleanly: `registry.register(BEADataSource, MockBEASource, variant="test")`.
- `economics/factory.py` shrinks ~80%.

### Negative / tradeoffs

- Introduces a new `core/` package. Be vigilant that it doesn't grow into a junk drawer — keep it strictly to cross-cutting protocol/registry concerns. Each addition needs an ADR.
- `SourceRegistry` is a small DI container; teams wary of "factory of factories" patterns may push back. The win is replacing 7 hand-rolled factories with one explicit one.
- `CachedSource` is a mixin → `Default*` classes that already inherit from something else need careful MRO inspection. Acceptable: most `Default*` classes inherit only from `object` today.

## Acceptance criteria

- [ ] `src/babylon/core/protocol_kit.py` exists with `DataSource`, `CachedSource`, `SourceRegistry`.
- [ ] `economics/factory.py` reduced to \<150 LOC; old `create_*_services()` functions kept only as thin shims that call into `SourceRegistry`.
- [ ] At least 10 `Default*` classes (chosen from `melt/` + `gamma/`) migrated to inherit from `CachedSource[T]` and lose their hand-rolled `__init__`.
- [ ] `mise run check` passes with zero new findings.
- [ ] All 150+ persistence + economics unit tests pass unchanged.
- [ ] A migration guide in this ADR's "Rollout" section is followed; remaining 51 Default\* classes are listed as follow-up work in `ai/roadmap.md`.

## Rollout

1. **`feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry`**

   - Pure new module + unit tests for `CachedSource` and `SourceRegistry`.
   - No changes to existing code.

1. **`refactor(economics): migrate melt/ Default* classes to CachedSource`**

   - Update `melt/adapters.py` (`DefaultBEASource`, `DefaultQCEWSource`, `DefaultCPISource`).
   - Update `melt/melt_calculator.py`, etc.
   - Verify `tests/unit/economics/melt/` is green.

1. **`refactor(economics): migrate gamma/ Default* classes to CachedSource`**

   - Same playbook for `gamma/adapters.py`.

1. **`refactor(economics): replace factory.py wiring with SourceRegistry`**

   - Add `SourceRegistry.builtin_economics()`.
   - Convert each `create_*_services()` to a 3-line shim around the registry.
   - Update the engine call sites to consume `services.registry.get(Foo)` instead of `services.foo`.

1. **`refactor(infrastructure): migrate infrastructure/ Default* classes to CachedSource`** *(optional same-PR or follow-up)*

Steps 2–4 each commit independently. Step 5 is opportunistic.

## Test strategy

- `pytest tests/unit/economics/melt/` after each migration step.
- New unit tests in `tests/unit/core/test_protocol_kit.py`:
  - `CachedSource._resolve` returns same instance on repeat call.
  - `CachedSource._resolve` returns `NoDataSentinel` for missing data, never `None`.
  - `SourceRegistry.get` raises `LookupError` for unregistered protocol.
  - `SourceRegistry.register` with `variant="test"` does not shadow `default`.
- Add a contract test that each migrated `Default*` still satisfies its Protocol via `isinstance(impl, ProtocolClass)` (works because Protocols are `runtime_checkable`).

## References

- Knowledge graph nodes:
  - 112 `Protocol`-named class nodes (across all packages)
  - 61 `Default*` class nodes (concentrated in `economics/`)
  - `file:src/babylon/economics/factory.py` (662 LOC, 7 `create_*` functions, out-degree 28)
- Project memory: "Protocol + Default impl: All calculators use `Protocol` for DI + `DefaultXxxCalculator` concrete class".
- Related ADRs: ADR-001 (depends on `defines/` split for clean per-category registration).
- CLAUDE.md sections: "Coding Standards" (Pydantic First), "Common Gotchas" (Dependency Injection Over Discovery).
