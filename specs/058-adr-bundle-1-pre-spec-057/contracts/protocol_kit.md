# Contract: `protocol_kit` — `DataSource` and `CachedSource[T]`

**Module**: `src/babylon/core/protocol_kit.py`
**Introduced by**: Spec 058 / FR-004 (US1, Bundle 1)
**Status**: Draft (this is the contract; implementation lands in commit 4)

This contract specifies the public surface of `DataSource` (Protocol marker) and `CachedSource[T]` (Generic ABC mixin) with their semantic guarantees. The `SourceRegistry` contract is in [`source_registry.md`](source_registry.md).

---

## 1. `DataSource`

### Public surface

```python
@runtime_checkable
class DataSource(Protocol):
    name: str
```

### Semantic guarantees

| Guarantee | Detail |
|-----------|--------|
| **Marker only** | `DataSource` defines no methods. Existing source Protocols (`BEADataSource`, `QCEWDataSource`, etc.) gain `DataSource` as a base class so they can be detected via `isinstance(impl, DataSource)`. |
| **Runtime-checkable** | `isinstance(some_impl, DataSource)` works at runtime. The check verifies *only* that `some_impl` has a `name` attribute of type `str`. |
| **Convention: `name` is human-readable** | The `name` attribute is for diagnostics (registry error messages, logs). Not used as a registry key. |

### Caller contract

- A new source Protocol SHOULD inherit from `DataSource`: `class FooSource(DataSource, Protocol): ...`
- A `Default*` class SHOULD set `name: str = "DefaultFooSource"` (typically the class name) at class level
- `isinstance(impl, DataSource)` is allowed but rare; prefer typing against the specific Protocol (`isinstance(impl, FooSource)`)

---

## 2. `CachedSource[T]`

### Public surface

```python
class CachedSource(Generic[T]):
    cache_negative_results: bool = True

    def __init__(self, *, max_entries: int = 1024) -> None: ...
    def _resolve(self, key: Hashable, fetch: Callable[[], T | None]) -> T | NoDataSentinel: ...
    def invalidate(self, key: Hashable) -> None: ...
    def clear(self) -> None: ...
```

### Semantic guarantees

#### Cache key derivation

| Guarantee | Detail |
|-----------|--------|
| **Caller-controlled** | The cache key is supplied by the subclass at `_resolve` call time. `CachedSource` does not derive keys from `_fetch` arguments — the subclass MUST construct an appropriate `Hashable` key. |
| **Hashable required** | The key MUST be `Hashable` (Python's dict requirement). If not, `TypeError` is raised by Python's dict implementation, not by `CachedSource`. |
| **Recommended pattern** | `tuple` of the `_fetch` arguments: `key = (year, fips_code)` then `self._resolve(key, lambda: self._fetch(year, fips_code))`. |
| **Equality semantics** | Two keys are the same cache slot iff `key1 == key2 and hash(key1) == hash(key2)` (Python dict semantics). Tuples of hashable types satisfy this; lists do not (lists are not hashable). |

#### `cache_negative_results` policy

| Guarantee | Detail |
|-----------|--------|
| **Default: `True`** | `NoDataSentinel` results are cached. Repeated calls with the same key return the same `NoDataSentinel` instance without re-invoking `_fetch`. Correct for stable-within-session sources (FRED, BEA Use Tables, county FIPS). |
| **Opt-out: `False`** | Subclasses set `cache_negative_results = False` at class level. With this setting, `NoDataSentinel` results are returned but NOT cached; the next `_resolve` call with the same key re-invokes `_fetch`. Correct for transient-derivation sources (DPD lifecycle, MELT recomputation, sources whose `_fetch` consumes still-pending output from another derivation pass). |
| **No mid-instance switching** | `cache_negative_results` is a class-level attribute. Mutating it on an instance after construction is allowed but discouraged; the cache state at the time of mutation is not retroactively updated. |
| **Real values always cached** | `cache_negative_results` controls only `NoDataSentinel` caching. Real values (`T` from `_fetch`) are always cached regardless of this flag. |

#### Eviction

| Guarantee | Detail |
|-----------|--------|
| **FIFO eviction at `max_entries`** | When the cache reaches `max_entries`, the oldest insertion is evicted on the next insert. NOT LRU — a hit on an old entry does NOT bump it to the front. The simpler FIFO is acceptable for Babylon's data-shape (most sources have <100 distinct keys per session; `max_entries=1024` is rarely hit). |
| **Non-monotonic memory** | After `invalidate(key)` or `clear()`, cache size shrinks. After `_resolve`, cache size grows up to `max_entries`. |
| **`max_entries` lower bound** | `max_entries=1` is permitted (every cache miss evicts the previous entry). `max_entries=0` is undefined behavior (loop guard not enforced); subclasses MUST NOT pass 0. |

#### `invalidate(key)` and `clear()`

| Guarantee | Detail |
|-----------|--------|
| **`invalidate(key)`** | Removes one cache entry. No-op if `key` is not present. Returns `None`. |
| **`clear()`** | Removes all cache entries. Returns `None`. Equivalent to `for k in list(cache): cache.pop(k)`. |
| **Test contract** | Both methods exist primarily for tests that need to swap mock return values mid-test. `SourceRegistry`'s `variant="test"` substitution does NOT call `clear()` automatically; tests that mutate cache state through `invalidate`/`clear` are responsible for cleanup. |
| **Thread safety** | NONE. `CachedSource` is single-threaded. Babylon's tick computation is single-threaded by Constitution II.6 (pure-transformation engine), so this is consistent with the project's concurrency model. |

#### `_resolve(key, fetch)` return type

| Guarantee | Detail |
|-----------|--------|
| **Return is `T \| NoDataSentinel`** | Never `None`. If `fetch()` returns `None`, `_resolve` wraps it in a `NoDataSentinel` with a generated `reason` string. |
| **`NoDataSentinel.reason` format** | `f"no data for {key}"` — caller-readable but not parsed by any consumer. Subclasses that need a more specific reason MUST construct their own `NoDataSentinel` and return it directly from `_fetch` (return-type allows it because `T | None` is interpreted permissively for falsy sentinels). |
| **Stable instance on cache hit** | A cache hit returns *the same instance* that was stored, not a copy. This means `is` checks across calls are sufficient to detect cache reuse: `r1 is r2` iff both calls hit the same cache slot. |

### Caller contract

- A `Default*` class SHOULD inherit from `CachedSource[T]` where `T` is the concrete return type of its `_fetch` method
- A subclass MUST implement `_fetch(*args, **kwargs) -> T | None`
- Each public lookup method MUST construct a `Hashable` key and delegate to `_resolve`:
  ```python
  def get_value(self, year: int, fips: str) -> float | NoDataSentinel:
      return self._resolve((year, fips), lambda: self._fetch(year, fips))
  ```
- A subclass MAY override `cache_negative_results = False` if its `NoDataSentinel` represents transient missing data
- A subclass MAY pass `max_entries=N` to the parent's `__init__` to size the cache; default `1024` is appropriate for most cases

### Test contract

`tests/unit/core/test_protocol_kit.py` MUST cover:

1. **Cache hit returns same instance**: `r1 = src._resolve(k, fetch); r2 = src._resolve(k, fetch); assert r1 is r2; assert fetch_call_count == 1`
2. **`None` from `_fetch` becomes `NoDataSentinel`**: `assert isinstance(src._resolve(k, lambda: None), NoDataSentinel)`
3. **`cache_negative_results=True` (default)**: `NoDataSentinel` is cached: second call does not re-invoke `_fetch`
4. **`cache_negative_results=False`**: `NoDataSentinel` is NOT cached: second call re-invokes `_fetch`
5. **`invalidate(key)` removes the entry**: `src._resolve(k, fetch); src.invalidate(k); src._resolve(k, fetch); assert fetch_call_count == 2`
6. **`clear()` removes all entries**: same as #5 but with `clear()` instead of `invalidate(k)`
7. **FIFO eviction at `max_entries`**: with `max_entries=2`, three inserts evict the first; the first key is no longer cached
8. **`_resolve` return type is `T | NoDataSentinel`, never `None`**: even if `_fetch` returns `None`, the result is wrapped

---

## 3. Backward-compatibility commitments

Per Spec 058 Clarifications 2026-05-08 (Q2): Babylon has no external downstream consumers, so the contract is solely internal.

- `protocol_kit.py` is a NEW module — there are no historical imports to preserve
- The 10 `Default*` classes that migrate to `CachedSource[T]` retain their existing public method signatures (the `get_*` methods that callers use); only the private `__init__` boilerplate changes
- After migration, `isinstance(impl, OldProtocolType)` continues to work (Protocols are structural, not nominal)

---

## 4. Out-of-scope for Bundle 1

- Performance benchmarking the new `CachedSource` cache vs the previous hand-rolled implementations (per spec "Out of Scope")
- Migrating the 51 non-`melt/`/`gamma/` `Default*` classes to `CachedSource[T]` (per spec "Out of Scope"; deferred to ADR-002 follow-up rollout)
- Multi-process or async cache semantics (single-threaded by Constitution II.6)
- Persistent caches (cache is in-memory, lost on process restart)
