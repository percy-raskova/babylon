# Contract: ReferenceDataCache

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data Model**: [../data-model.md](../data-model.md)

This document is the **normative** behavioral contract for the
`ReferenceDataCache` introduced by spec-069. Implementation details
are described in `data-model.md` and `research.md`; this file
enumerates the externally-observable guarantees a consumer (the
bridge) may rely on.

---

## Interface summary

The cache is **not** a Protocol-typed contract for cross-subsystem
consumption (unlike spec-068's `BEAShareLookupService`). It is a
single concrete class owned by the bridge subsystem (II.11 — the
bridge owns its read path; no other subsystem may construct or call
this cache). Documented here for the same reason: to make the
runtime behavior auditable.

Module: `src/babylon/engine/headless_runner/reference_data_cache.py`
Class: `ReferenceDataCache`

---

## Construction contract

```python
ReferenceDataCache(sqlite_path: Path) -> ReferenceDataCache
```

### Preconditions

- `sqlite_path` must be an absolute path to an existing SQLite file
  containing the post-spec-067 canonical-leaf `fact_qcew_annual`
  table and the `fact_census_income`, `dim_county`, `dim_time` tables.
- The constructor does NOT open a connection. It records the path and
  initializes empty internal state.

### Postconditions

- A new cache instance with:
  - `_hydrated == False`
  - `_entries == {}`
  - `_population_db_reads == 0`
  - `_employment_db_reads == 0`
  - Both miss-logged sets empty.
- All lookup methods raise `RuntimeError("not hydrated")` if called.

### Exceptions

- None. Construction must not raise. Path validity is checked at
  `hydrate` time.

---

## `hydrate` contract

```python
hydrate(scope_fips: frozenset[str], year_set: frozenset[int]) -> None
```

### Preconditions

- Cache is not yet hydrated (`_hydrated == False`). Calling `hydrate`
  twice on the same instance raises `RuntimeError`.
- `scope_fips` is non-empty.
- Every member of `scope_fips` is a syntactically valid 5-digit FIPS
  string (zero-padded).
- `year_set` may be empty (degenerate zero-tick case → no-op
  hydrate; `_hydrated` becomes `True` with zero entries).
- The SQLite file at `_sqlite_path` exists and is readable.

### Postconditions

- `_hydrated == True`.
- For every `(fips, year) ∈ scope_fips × year_set`, an entry exists
  in `_entries` with shape `ReferenceCacheEntry(population=...,
  employment_proxy=...)`. Each field is `None` iff the underlying
  data is absent for that tuple.
- `_population_db_reads == len(scope_fips) × len(year_set)`.
- `_employment_db_reads == len(scope_fips) × len(year_set)`.
- The numeric values stored in each entry are equal — to the bit
  pattern, for ints, and to within float-equality for floats —
  to what the legacy per-tick fetchers would have returned for the
  same `(fips, year)` tuple against the same DB state at the same
  point in time.
- Exactly one `sqlite3.Connection` was opened and closed during the
  call.

### Exceptions

| Condition | Exception |
|-----------|-----------|
| Called twice | `RuntimeError("ReferenceDataCache.hydrate called twice")` |
| `scope_fips` empty | `ValueError` |
| Malformed FIPS string | `ValueError` |
| `sqlite_path` does not exist | `FileNotFoundError` (deferred from ctor) |
| Any SQL execution fails | `sqlite3.Error` propagated unchanged |

### Side effects

- One `sqlite3.connect()` open/close round-trip.
- 2 or 3 `cursor.execute()` calls (2 if no Census-missing tuples need
  the QCEW fallback; 3 otherwise).
- No mutation of the SQLite file. All queries are `SELECT`.

---

## `lookup_population` contract

```python
lookup_population(county_fips: str, year: int) -> int | None
```

### Preconditions

- Cache has been hydrated (`_hydrated == True`); otherwise
  `RuntimeError("not hydrated")`.
- `(county_fips, year)` was in the `(scope_fips × year_set)` that
  was hydrated. Lookups outside that set raise `KeyError`.

### Postconditions

- Returns the cached population value for `(county_fips, year)`, or
  `None` if the underlying data was absent at hydrate time.
- The cache state is unchanged (no counter increment, no set
  mutation — see R6 for why).
- The same call against the same cache instance always returns the
  same value (idempotent).

### Exceptions

| Condition | Exception |
|-----------|-----------|
| Cache not hydrated | `RuntimeError` |
| `(county_fips, year)` not in scope | `KeyError` |

---

## `lookup_employment_proxy` contract

```python
lookup_employment_proxy(county_fips: str, year: int) -> float | None
```

Identical contract to `lookup_population` modulo field type
(`float` rather than `int`).

---

## `mark_population_miss_logged` contract

```python
mark_population_miss_logged(county_fips: str, year: int) -> bool
```

### Preconditions

- Cache has been hydrated.
- `(county_fips, year)` is in scope (else `KeyError`).
- Caller has already determined that the cached entry's
  `population` field is `None` (the marker is intended only for
  miss-logging coordination; calling it for a present-value tuple is
  not an error, but is a misuse signal — see "Side effects" below).

### Postconditions

- Returns `True` on the first invocation for this `(county_fips,
  year)` tuple, `False` thereafter.
- After the first invocation, `(county_fips, year)` is permanently
  in `_population_miss_logged`.

### Exceptions

| Condition | Exception |
|-----------|-----------|
| Cache not hydrated | `RuntimeError` |
| `(county_fips, year)` not in scope | `KeyError` |

### Side effects

- Mutates `_population_miss_logged` by adding `(county_fips, year)`
  if not already present.
- Does NOT log anything itself. The caller (bridge) is the logger.

---

## `mark_employment_miss_logged` contract

Identical contract to `mark_population_miss_logged` modulo target
set (`_employment_miss_logged`).

---

## Property contracts

```python
@property
population_db_reads -> int
```

- Returns the count of `(county, year)` tuples whose population
  field was resolved during hydrate, whether to a concrete value or
  to `None`.
- Stable for the lifetime of the cache after hydrate. No mutation
  pathway after `_hydrated == True`.

```python
@property
employment_db_reads -> int
```

- Same semantics, scoped to the employment proxy.

```python
@property
total_db_reads -> int
```

- Equals `population_db_reads + employment_db_reads`.

---

## Concurrency contract

**Not thread-safe.** The cache assumes single-threaded access by the
owning bridge instance. Multi-threaded run loops are out of scope
(spec-066 / spec-065 are single-threaded; no spec proposes otherwise).

---

## Determinism contract (mapping to constitution III.7)

- Given the same `sqlite_path` content at hydrate time, the same
  `scope_fips`, and the same `year_set`, `hydrate` produces a cache
  whose lookups return byte-identical values across runs.
- `hydrate` does not consume any external nondeterministic source
  (no random number generator, no wall-clock, no PID).
- `lookup_*` and `mark_*` are pure functions of cache state and
  arguments.

---

## Lifetime contract (mapping to spec FR-008)

- One `ReferenceDataCache` instance per `WorldStateBridge` instance.
- The cache must NOT be shared across bridges in the same process.
- The cache must NOT outlive its owning bridge. (Garbage collection
  occurs when the bridge is dropped.)
- No mechanism for serializing or persisting the cache to disk.

---

## Backward compatibility contract

- The existing functions `fetch_population_for_county_at_tick` and
  `fetch_employment_proxy_for_county_at_tick` in
  `src/babylon/persistence/county_aggregation.py` remain available
  with unchanged semantics. Non-bridge callers (legacy tests,
  operator tools) continue to work without modification.
- The cache is opt-in for the bridge. There is no global registry
  that redirects fetcher calls through the cache.
