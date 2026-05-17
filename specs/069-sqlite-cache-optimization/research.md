# Phase 0 Research: SQLite per-tick read cache

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-05-17

This document records the design-time decisions that resolve the
ambiguities not pinned by the spec or by the spec-066 R8 placeholder.
Each decision is presented in **Decision / Rationale / Alternatives**
form so that future readers can reconstruct the reasoning.

---

## R1 — When to populate the cache (hydrate-time bulk vs first-encounter batch)

**Decision**: Bulk hydration at `bridge.hydrate_initial()` time. The bridge's
`hydrate_initial` signature gains a new mandatory `total_ticks: int`
parameter. The runner passes `config.ticks` at the existing call site
(`runner.py:603`). The bridge derives the in-scope year-set
(`{start_year + t // 52 for t in range(total_ticks)}`) and issues a
small fixed number of batched SQL queries to populate the cache for
every `(scope_fips × year_set)` tuple before returning.

**Rationale**:

- FR-001 reads literally: "before the first tick is persisted." Bulk
  hydration matches the literal wording; lazy hydration would defer
  reads to "the first tick that needs them," which technically obeys
  FR-001 only if you redefine "is persisted" loosely.
- A single hydration point gives an unambiguous home for the
  instrumentation counter (R6); lazy hydration scatters the increment
  across whichever tick happens to be first-in-year.
- Year-set enumeration becomes a pure function, trivially unit-testable
  on its own without spinning up a bridge.
- For the canonical 520-tick Michigan-Canada run, year-set enumeration
  is deterministic from `(start_year=2010, total_ticks=520)` →
  `{2010, 2011, ..., 2019, 2020}` (11 years). No per-run discovery
  needed.

**Alternatives considered**:

- *Lazy / first-encounter batch*: On the first `persist_tick` that
  resolves to a new year Y, batch-fetch all `(county × Y)` tuples.
  Rejected because it (a) puts a wallclock spike on the first tick of
  each new year, (b) complicates SC-002's read-count proof (the
  counter must be checked at end of run, not at end of hydrate), and
  (c) doesn't match FR-001's literal wording.
- *Per-tick fetch with simple memoization*: Wrap the existing
  `fetch_*_at_tick` calls in `@functools.cache`. Rejected because the
  per-call connection-open overhead still dominates: with 913 distinct
  `(county, year)` tuples and `sqlite3.connect()` taking ~1-3 ms each,
  this is ~1-3 s of connection overhead even at the structurally
  optimal read count — a substantial improvement, but missing the
  batch amortization that takes the per-tick path down to the
  ~0.1 s/tick range spec-066 R8 measured for cache-served lookups.

---

## R2 — Cache value shape and missing-data representation

**Decision**: One frozen Pydantic model per `(county, year)` tuple,
with per-field nullability:

```python
class ReferenceCacheEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    population: int | None
    employment_proxy: float | None
```

`None` means "fetched at hydrate time, not present in the underlying
data." Post-hydrate, every `(county, year)` tuple in scope is a key
in the cache dict — absence of the key is reserved for "scope bug,
this tuple was not enumerated" (assertion-raising state, not a normal
case).

**Rationale**:

- Per-field nullability matches the existing fetcher contract.
  Inspection of `fetch_population_for_county_at_tick` and
  `fetch_employment_proxy_for_county_at_tick` reveals an asymmetric
  fallback path: `population` derives from Census primary + QCEW×0.33
  fallback, but `employment_proxy` reads only QCEW. A `(county, year)`
  tuple where Census is missing but QCEW is present will have
  `(population=int, employment_proxy=float)`; if QCEW is missing
  both fields are `None`. A single `MISSING` enum value can't capture
  this asymmetric structure.
- Frozen Pydantic matches the project's existing model-shape convention
  (per [[feedback_full_vision_no_mvps]] and the universal
  `ConfigDict(frozen=True)` pattern across the codebase).
- "Not yet fetched" is encoded by **absence from the dict**, which is
  a one-shot post-hydrate property: hydrate either succeeds (every
  in-scope key is present) or fails loud (assertion on a missing key
  is a bridge-correctness bug, not a runtime concern for callers).

**Alternatives considered**:

- *Status enum (`VALUE | MISSING`)*: Rejected because the asymmetric
  fetcher fallback above makes per-field state the natural shape.
- *Tuple value (`(int | None, float | None)`)*: Rejected because a
  named field with a docstring is more self-documenting than tuple
  positions for a long-lived in-memory structure.
- *Two separate caches (one per fetch function)*: Rejected because
  every `persist_tick` invokes both fetchers for the same `(county,
  year)` tuple; co-locating them in one entry means one dict lookup
  per tick instead of two.

---

## R3 — Year-set derivation

**Decision**: Pure function on the bridge module:

```python
def derive_year_set(start_year: int, total_ticks: int) -> frozenset[int]:
    """Year-set covered by a run of ``total_ticks`` weekly ticks starting at ``start_year``."""
    if total_ticks <= 0:
        return frozenset()
    return frozenset({start_year + t // 52 for t in range(total_ticks)})
```

The weekly cadence (52 ticks/year) is inherited unchanged from
spec-065/066. `total_ticks` is the new `hydrate_initial` parameter
threaded from `runner.RunnerConfig.ticks`.

**Rationale**:

- Matches the existing `_tick_to_year(tick, start_year) = start_year +
  tick // 52` convention in `county_aggregation.py:263`.
- `frozenset[int]` reads as an immutable, deduplicated set — the
  natural type for "which years does this run touch." Order doesn't
  matter (cache is dict-keyed).
- Degenerate cases: `total_ticks=0` → empty set (no-op hydrate);
  `total_ticks=1` → `{start_year}`; `total_ticks=52` → `{start_year}`;
  `total_ticks=53` → `{start_year, start_year+1}`.

**Alternatives considered**:

- *`(start_year, end_year)` parameterization*: Rejected because the
  runner thinks in `total_ticks`, not in `end_year`. Conversion would
  duplicate the cadence convention.
- *Cadence as a configurable parameter*: Rejected as YAGNI. The weekly
  cadence is constitutional for the project (per spec-062
  Cross-Scale-Integration) and is not in flux.

---

## R4 — Hydrate query strategy

**Decision**: Three batched SQL queries per hydrate, all issued
through a single `sqlite3.connect()`:

1. **Population — Census primary**: one `SELECT … GROUP BY (county,
   year)` returning `(fips, year, population)` for all
   `(scope_fips × year_set)` tuples where Census has data.
2. **Population — QCEW fallback**: a second query for the `(county,
   year)` tuples NOT returned by query 1, multiplying QCEW employment
   by 0.33 (the existing Wayne-calibrated ratio in
   `fetch_population_for_county_at_tick:332`).
3. **Employment proxy**: one `SELECT … GROUP BY (county, year)`
   returning `(fips, year, SUM(qcew.employment))` for all
   `(scope_fips × year_set)` tuples.

All three queries use `WHERE fips IN (?, ...)` and
`WHERE year IN (?, ...)` placeholder lists. SQLite's parameter limit
defaults to 999, which is comfortably above the canonical run's
83 + 11 = 94 placeholders.

**Rationale**:

- Three SQL executions (with `?`-bound placeholders) collapse 86,320
  per-tick round-trips into 3 hydrate-time round-trips. The
  per-execution connection-open overhead amortizes over thousands of
  rows.
- Reusing the existing aggregation logic (`SUM(household_count)`,
  `SUM(employment)`) keeps the cached values byte-equal to what the
  pre-cache fetchers would have returned (FR-005, SC-003).
- The Census-primary + QCEW-fallback two-query pattern for population
  matches the existing fetcher's behavior exactly; we are NOT changing
  the semantic, only the access pattern.

**Alternatives considered**:

- *One mega-query with LEFT JOINs across Census, QCEW, dim_county,
  dim_time*: Rejected as unnecessarily complex. Three legible queries
  beat one inscrutable one.
- *Reuse the existing per-tick fetchers in a loop*: Rejected. Even at
  the structurally optimal 913 calls (one per `(county, year)` tuple),
  the connection-open overhead is ~1-3 s of pure connect/close work
  — non-trivial against the SC-001 wallclock budget and entirely
  wasted given that all reads can share one connection.

---

## R5 — Cache structure on the bridge

**Decision**: The bridge gains a private attribute
`_ref_cache: ReferenceDataCache | None = None` (set in `__init__`,
populated in `hydrate_initial`). `ReferenceDataCache` is a new class
in `src/babylon/engine/headless_runner/reference_data_cache.py` with:

- `__init__(self, sqlite_path: Path)` — record the read path.
- `hydrate(self, scope_fips: frozenset[str], year_set: frozenset[int])
  -> None` — issue the three batched queries, populate the internal
  `dict[tuple[str, int], ReferenceCacheEntry]`, increment the
  instrumentation counters.
- `lookup_population(self, county_fips: str, year: int) -> int | None`
  — return cached value (may be `None` for missing data).
- `lookup_employment_proxy(self, county_fips: str, year: int) -> float
  | None` — same.
- `mark_population_miss_logged(self, county_fips: str, year: int) ->
  bool` — return True on the first call for that tuple, False
  thereafter. Drives FR-004 / SC-004 once-per-tuple logging.
- `mark_employment_miss_logged(self, county_fips: str, year: int) ->
  bool` — same for employment.
- Read-only properties: `population_db_reads: int`,
  `employment_db_reads: int`, `total_db_reads: int`.

**Rationale**:

- One class, one responsibility (cache reference data, count reads,
  track miss-logging state). Easy to test in isolation.
- Per-bridge-instance scoping (FR-008) is enforced by lifetime: the
  cache is bound to the bridge constructor, not to module-level state.
- The miss-logging tracker lives on the cache (not on the bridge)
  because the cache already knows about (fips, year) tuples; pushing
  it elsewhere splits the state across two objects.

**Alternatives considered**:

- *Module-level singletons*: Rejected — explicit FR-008 prohibition
  on cross-instance state.
- *Two separate caches (`PopulationCache`, `EmploymentCache`)*:
  Rejected because every `persist_tick` invokes both fetchers
  back-to-back; one combined cache is the natural shape.

---

## R6 — Instrumentation counter (FR-007)

**Decision**: Two `int` counters on `ReferenceDataCache`:

- `_population_db_reads: int` — incremented once per `(county, year)`
  tuple resolved to a population value (or proven absent) during
  `hydrate`.
- `_employment_db_reads: int` — same for employment.

Exposed via read-only properties on the cache, and re-exposed via
read-only properties on the bridge (`bridge.population_db_reads`,
`bridge.employment_db_reads`, `bridge.total_db_reads`). The counter
is incremented at hydrate time, **not** in `persist_tick` (FR-003 and
SC-002 require persist_tick to do zero reads against the underlying
database).

The semantic unit of count is **one (county, year) tuple's worth of
data**, not one SQL query execution. This matches SC-002's wording
("exactly 2 × N × Y reference-data reads") and makes the metric
directly testable.

**Rationale**:

- Per-bridge-instance state matches FR-008 cleanly.
- Counting `(county, year)` resolutions (not SQL executions) is the
  user-visible semantic the spec actually constrains.
- Read-only property exposure is observable without contaminating
  production code with state-mutation hooks for tests.

**Alternatives considered**:

- *Count SQL `cursor.execute()` calls*: Rejected — that count is
  always 3 (per R4) regardless of scope, which is a weaker
  verification.
- *Expose via `event_bus.publish()`*: Rejected as overkill — the
  counter is observability for tests/operators, not a domain event.

---

## R7 — SC-004 once-per-tuple miss logging

**Decision**: The bridge's per-tick `_derive_subsystem_rows_for_county`
flow changes from:

```python
try:
    population = fetch_population_for_county_at_tick(...)
    demographics_row = DynamicDemographicsState(...)
except ReferenceDataMissingError as exc:
    logger.warning("persist_tick: population missing ...", ...)
```

to:

```python
population = self._ref_cache.lookup_population(county_fips, year)
if population is None:
    if self._ref_cache.mark_population_miss_logged(county_fips, year):
        logger.warning("persist_tick: population missing for county=%s year=%d ...", ...)
else:
    demographics_row = DynamicDemographicsState(...)
```

The `mark_*_miss_logged` boolean returns True only on the first
invocation for a given `(county, year)` tuple. Subsequent ticks in
the same calendar year invoke the marker, get False, and skip the
log call.

**Rationale**:

- Encodes "log at most once per tuple per run" as a property of the
  cache's state, not of the logger or of the bridge's tick counter.
- Testable in isolation: instantiate cache → call
  `mark_population_miss_logged("26163", 2010)` 100 times → verify
  exactly one True and 99 False.
- The bridge's logger-call site remains the place that emits the
  human-readable warning; the cache only owns the "is this the first
  time?" predicate.

**Alternatives considered**:

- *Compute `tick % 52 == 0` and log only at year boundaries*: Rejected.
  Misses the first-tick-of-year for a missing (county, year+1)
  tuple, since the "first time we see this tuple" is the first tick
  where `tick // 52` equals the new year, not a multiple of 52.
- *De-duplicate at the logger level via a `logging.Filter`*: Rejected.
  Coupling the spec's correctness to logger configuration is fragile;
  a logger change in unrelated code could re-introduce per-tick
  warnings without breaking any test.

---

## R8 — Determinism preservation (SC-003)

**Decision**: The cache introduces no new source of nondeterminism.
The same `(county, year)` lookup over the lifetime of a run returns
the same value. The underlying SUM aggregates in the batched queries
are order-independent on integer columns and (per the post-spec-067
canonical-leaf schema) byte-stable across re-runs. Dict iteration
order is not consulted by `persist_tick` (it looks up by key).

The SC-003 byte-identical contract is **verified empirically** by a
slow-gate integration test that runs the canonical scenario twice
(pre-cache and post-cache, or two post-cache runs) at the same seed
and diffs the resulting `trace.csv` at the byte level.

**Rationale**:

- The cache is a memoization. Memoization of a deterministic function
  produces a deterministic result (textbook).
- The pre-spec fetchers themselves are deterministic given the same
  reference DB state.
- Empirical verification is the constitutional III.7 standard
  ("determinism is the mechanism by which falsifiability is
  enforced"), so we lift it from a theoretical argument to a slow-gate
  CI test.

**Alternatives considered**:

- *Hypothesis property test over random shuffled access orders*:
  Bonus, not required. Useful follow-up but the byte-identical-trace
  slow-gate is the canonical proof.
- *Cryptographic determinism hash on the cache contents*: Out of
  scope for this spec; the spec-066 trace-hash already covers the
  user-visible run output.

---

## R9 — Cache eviction policy

**Decision**: No eviction. Bridge-instance lifetime is one canonical
run. Max cache size = 83 counties × 11 years × 1 entry per tuple ≈
913 entries × ~64 bytes (Pydantic frozen model with two scalar fields)
≈ 60 KB. Not memory-bound.

**Rationale**:

- Cache exists to eliminate redundant reads. Eviction re-introduces
  them.
- 60 KB is rounding error against the bridge's other in-memory state
  (hex template tuple, external template tuple, EventBus subscribers,
  etc.).

**Alternatives considered**:

- *LRU eviction*: Rejected — see above.
- *Spill-to-disk for very-long runs*: Rejected as YAGNI. A 10× scale
  bump (831 counties × 11 years × 8 bytes/entry ≈ 73 KB) is still
  trivial.

---

## R10 — Backward compatibility with non-bridged callers

**Decision**: The fetcher functions
`fetch_population_for_county_at_tick` and
`fetch_employment_proxy_for_county_at_tick` in
`src/babylon/persistence/county_aggregation.py` remain **unchanged**.
They retain their per-call `sqlite3.connect()` semantics for callers
that do not own a `ReferenceDataCache` (legacy tests, ad-hoc scripts,
the operator-side `tools/inspect_qcew_audit.py` helper, etc.).

The cache is opt-in for the bridge subsystem. Outside the bridge,
nothing changes.

**Rationale**:

- II.11 (subsystem table ownership) — the bridge owns its read path;
  other subsystems are free to read through the declared fetcher
  interface as they always have.
- Minimizes blast radius. The spec is a localized perf optimization;
  changing the public fetcher signatures would propagate edits
  through code we are not testing here.

**Alternatives considered**:

- *Deprecate the per-call fetchers in favor of cache-only access*:
  Rejected. The fetchers are the constitutional read interface (II.11)
  and have non-bridge callers (legacy tools).
- *Promote the cache to a module-level singleton consumed by both
  the bridge and ad-hoc callers*: Rejected. FR-008 explicitly forbids
  cross-run sharing, and the operator tools don't have a "run"
  lifetime to scope a cache to.

---

## R11 — New `hydrate_initial` signature

**Decision**: Extend `WorldStateBridge.hydrate_initial` to accept a
new keyword-only required parameter:

```python
def hydrate_initial(
    self,
    session_id: UUID,
    scope_fips: frozenset[str],
    event_capture: EventCapture | None = None,
    *,
    total_ticks: int,                # NEW — required, drives year-set
    start_year: int = 2010,
    sqlite_path: Path | None = None,
) -> WorldState:
```

`total_ticks` is required (no default), so any existing caller that
forgets to pass it surfaces at call site as a `TypeError`. The
runner's existing call site (`runner.py:603`) passes `config.ticks`,
which is already in scope.

**Rationale**:

- Required argument forces explicit thread-through. A default would
  hide a latent bug (running a 1000-tick scenario with a
  20-tick-implied cache).
- Keyword-only placement keeps positional ordering stable for any
  third-party callers (none known) and matches the existing
  `start_year=2010, sqlite_path=None` keyword-only pattern.

**Alternatives considered**:

- *Optional parameter with default 1 or 0*: Rejected — silent
  misuse. A 0-tick cache miss-fires on the first persist_tick.
- *Read `total_ticks` from `RunnerConfig` injected at bridge
  construction time*: Rejected — bridge construction predates run
  configuration parsing in the existing init order, and inverting
  that is out of scope.

---

## Open items / non-decisions

None. All FRs and SCs in spec.md have a concrete design path through
the above decisions.
