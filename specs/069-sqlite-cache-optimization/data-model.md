# Phase 1 Data Model: SQLite per-tick read cache

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

This document defines the in-memory data structures introduced by
spec-069. No SQL schema changes are required (FR / spec Out-of-Scope).
All entities are runtime-only, bound to the lifetime of a single
`WorldStateBridge` instance (FR-008).

---

## Entity inventory

| Entity                  | Kind                  | Lifetime          | Persisted? |
|------------------------|------------------------|-------------------|------------|
| `ReferenceCacheEntry`   | Frozen Pydantic model | Bridge instance   | No         |
| `ReferenceDataCache`    | Plain class           | Bridge instance   | No         |
| In-scope year set       | `frozenset[int]`      | Bridge instance   | No         |
| Read counter            | `int` (×2 fields)     | Bridge instance   | No         |
| Miss-logged tracker     | `set[tuple[str, int]]` (×2) | Bridge instance | No   |

---

## 1. `ReferenceCacheEntry`

The atomic cache value. One instance per `(county_fips, year)` tuple
in scope.

**Module**: `src/babylon/engine/headless_runner/reference_data_cache.py`

**Definition** (shape; non-normative example for Phase 1):

```python
class ReferenceCacheEntry(BaseModel):
    """One (county, year) tuple's cached reference data.

    population and employment_proxy are independently nullable:
    Census/QCEW data coverage is asymmetric (see R2 in research.md).
    """
    model_config = ConfigDict(frozen=True)

    population: int | None
    employment_proxy: float | None
```

**Fields**:

| Field              | Type             | Meaning                                                          |
|-------------------|------------------|------------------------------------------------------------------|
| `population`      | `int \| None`    | Resolved population for `(county, year)`; `None` ⇒ underlying data absent (Census missing AND QCEW fallback missing) |
| `employment_proxy`| `float \| None`  | Resolved annual-average employment for `(county, year)`; `None` ⇒ QCEW absent for this tuple |

**Validation rules**:

- `population >= 0` if not None.
- `employment_proxy >= 0.0` if not None.
- Both fields independently nullable. The four combinations
  `{(present, present), (present, None), (None, present), (None,
  None)}` are all legitimate empirical states given the asymmetric
  Census/QCEW fallback path.

**Frozen**: `ConfigDict(frozen=True)`. Once constructed at hydrate
time, never mutated.

---

## 2. `ReferenceDataCache`

The container that holds all `ReferenceCacheEntry` values for a run,
plus the instrumentation counters and miss-logging state.

**Module**: same as above.

**Internal state**:

| Attribute                  | Type                                        | Initial    |
|---------------------------|---------------------------------------------|------------|
| `_sqlite_path`            | `Path`                                      | (ctor)     |
| `_entries`                | `dict[tuple[str, int], ReferenceCacheEntry]` | `{}`       |
| `_population_db_reads`    | `int`                                       | `0`        |
| `_employment_db_reads`    | `int`                                       | `0`        |
| `_population_miss_logged` | `set[tuple[str, int]]`                      | `set()`    |
| `_employment_miss_logged` | `set[tuple[str, int]]`                      | `set()`    |
| `_hydrated`               | `bool`                                      | `False`    |

**Lifecycle states**:

```text
                hydrate(scope_fips, year_set)
   ┌──────────┐──────────────────────────────────────────────►┌─────────┐
   │ INITIAL  │                                                │ HYDRATED│
   └──────────┘                                                └─────────┘
   _hydrated == False                                           _hydrated == True
   _entries == {}                                              _entries fully populated
   Lookups: raise RuntimeError                                  Lookups: O(1) dict access
```

**Public API (cache-internal — see contracts/ for the bridge-facing contract):**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `hydrate` | `(scope_fips: frozenset[str], year_set: frozenset[int]) -> None` | Issue batched SQL, populate `_entries`, increment counters. Idempotent only via the `_hydrated` guard (calling twice → RuntimeError, mirroring bridge.hydrate_initial). |
| `lookup_population` | `(county_fips: str, year: int) -> int \| None` | Return cached value or `None` if missing. Does NOT increment any counter (counter is hydrate-time only per R6). |
| `lookup_employment_proxy` | `(county_fips: str, year: int) -> float \| None` | Same. |
| `mark_population_miss_logged` | `(county_fips: str, year: int) -> bool` | Return `True` on first call for this tuple, `False` thereafter. Drives SC-004. |
| `mark_employment_miss_logged` | `(county_fips: str, year: int) -> bool` | Same for employment. |
| `population_db_reads` | `@property -> int` | Number of `(county, year)` tuples whose population was resolved at hydrate (whether to a value or to `None`). |
| `employment_db_reads` | `@property -> int` | Same for employment. |
| `total_db_reads` | `@property -> int` | Sum of the above. |

**Hydrate algorithm (informal, see research R4 for SQL)**:

```text
1. Validate inputs: scope_fips non-empty, year_set non-empty.
   (Empty year_set is the degenerate zero-tick case; permit silent no-op.)
2. Open ONE sqlite3.Connection(self._sqlite_path).
3. Query A: SELECT (fips, year, SUM(Census household_count))
            FROM fact_census_income JOIN dim_county JOIN dim_time
            WHERE fips IN ? AND year IN ? GROUP BY fips, year.
   For each row: pop_by_tuple[(fips, year)] = household_count (int).
4. Determine the (fips, year) tuples NOT covered by Query A.
5. Query B (fallback): SELECT (fips, year, SUM(QCEW employment))
            FROM fact_qcew_annual JOIN dim_county JOIN dim_time
            WHERE (fips, year) IN <set from step 4> GROUP BY fips, year.
   For each row: pop_by_tuple[(fips, year)] = int(qcew_emp * 0.33).
6. Query C: SELECT (fips, year, SUM(QCEW employment))
            FROM fact_qcew_annual JOIN dim_county JOIN dim_time
            WHERE fips IN ? AND year IN ? GROUP BY fips, year.
   For each row: emp_by_tuple[(fips, year)] = float(employment).
7. For every (fips, year) in (scope_fips × year_set):
      pop = pop_by_tuple.get((fips, year))           # may be None
      emp = emp_by_tuple.get((fips, year))           # may be None
      self._entries[(fips, year)] = ReferenceCacheEntry(
          population=pop, employment_proxy=emp
      )
      self._population_db_reads += 1
      self._employment_db_reads += 1
8. Close the connection. Set self._hydrated = True.
```

After hydrate:
- `len(self._entries) == len(scope_fips) * len(year_set)`.
- `self._population_db_reads == self._employment_db_reads ==
  len(scope_fips) * len(year_set)`.
- `self._total_db_reads == 2 × N × Y` (SC-002).

---

## 3. In-scope year set

A `frozenset[int]` derived by the pure function
`derive_year_set(start_year, total_ticks)` (research R3). Owned by
the bridge in transit between `hydrate_initial` parameter parsing
and `ReferenceDataCache.hydrate`. Not persisted as a separate entity
on the bridge — after hydrate, the cache's `_entries` is the
authoritative carrier.

**Validation rules**:

- `total_ticks >= 0`. (`< 0` → `ValueError` raised at bridge.)
- For canonical Michigan-Canada (`start_year=2010, total_ticks=520`):
  the year-set is `{2010, 2011, ..., 2020}` (11 distinct years).

---

## 4. Read counters

Two `int` fields on `ReferenceDataCache` (R6). Lifecycle:

```text
0 → +len(scope_fips × year_set) at hydrate → frozen for the lifetime of the bridge
```

The counters are **incremented only during `hydrate`**. `persist_tick`
must not increment them. The post-hydrate value is the testable
invariant for SC-002:

```python
assert bridge.population_db_reads == N * Y
assert bridge.employment_db_reads == N * Y
assert bridge.total_db_reads == 2 * N * Y
```

---

## 5. Miss-logged tracker

Two `set[tuple[str, int]]` fields on `ReferenceDataCache` (R7).
Lifecycle:

```text
∅ at construction
  → grows by exactly one (fips, year) tuple the FIRST time the bridge
    invokes mark_*_miss_logged(fips, year) AND the corresponding cache
    entry has the field as None
  → stable thereafter for the lifetime of the bridge.
```

The tracker is the operational form of SC-004. Verification:

```python
# Run a scenario with K missing (county, year) tuples spanning T ticks each.
# Trigger persist_tick T*K times.
# Assert: warning logged exactly K times, not T*K times.
```

---

## Relationships

```text
WorldStateBridge
  │
  │ 1 owns
  ▼
ReferenceDataCache
  │
  │ 1..N
  ▼
ReferenceCacheEntry  (one per (county_fips, year) tuple in scope)
```

A bridge instance has **at most one** cache (FR-008). A cache has
exactly `len(scope_fips) × len(year_set)` entries after hydrate. Each
entry is keyed by a `(county_fips, year)` tuple in the underlying dict.

---

## Constraints

- **No persistence**: Cache state lives in process memory only. The
  underlying SQLite DB is unmodified.
- **No mutation post-hydrate**: `_entries` is treated as effectively
  immutable after `hydrate` returns. (The dict object is mutable in
  Python, but the cache exposes no method to alter it.)
- **No cross-bridge sharing**: Each bridge constructs its own
  `ReferenceDataCache`. Two concurrent runs cannot see each other's
  cached values.

---

## Test surface (forward reference for `tasks.md`)

The data model is exercised by these test files (one assertion
focus per file, per the project's testing convention):

| Test file | Focus | Maps to |
|-----------|-------|---------|
| `test_reference_data_cache_year_set.py` | `derive_year_set` pure-function correctness | R3 |
| `test_reference_data_cache_three_state.py` | Per-field nullability semantics | R2 |
| `test_reference_data_cache_miss_logging.py` | `mark_*_miss_logged` returns True exactly once per tuple | R7 / SC-004 |
| `test_reference_data_cache_counter.py` | Counter increments at hydrate, not at lookup | R6 / SC-002 |
| `test_cache_byte_identical_trace.py` | (slow gate) Empirical SC-003 verification | R8 |
| `test_cache_canonical_wallclock.py` | (slow gate) SC-001 + SC-002 on canonical scenario | R1 |
