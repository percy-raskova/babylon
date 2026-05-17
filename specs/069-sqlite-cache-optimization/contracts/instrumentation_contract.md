# Contract: Bridge-level read-counter instrumentation

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data Model**: [../data-model.md](../data-model.md)

This document defines the **read-only observability surface** that
the bridge re-exposes from `ReferenceDataCache` so that operators
and tests can verify SC-002 (exactly `2 × N × Y` reads) and FR-003
(persist_tick performs zero reads against the underlying database).

---

## Exposed properties

The bridge gains three read-only properties:

```python
class WorldStateBridge:
    @property
    def population_db_reads(self) -> int: ...

    @property
    def employment_db_reads(self) -> int: ...

    @property
    def total_db_reads(self) -> int: ...
```

Each property delegates directly to the underlying
`ReferenceDataCache` properties. If the bridge has not yet been
hydrated, all three properties return `0`.

---

## Semantic unit of "read"

One read = one `(county_fips, year)` tuple's worth of either
population or employment-proxy data resolved against the underlying
database. The unit is **per-tuple**, not per-SQL-execution.

Concretely:

```text
population_db_reads  = number of (fips, year) tuples in (scope × year_set)
                       for which a population value (or its absence)
                       was determined at hydrate time
employment_db_reads  = same for employment proxy
total_db_reads       = population_db_reads + employment_db_reads
```

For the canonical Michigan-Canada run (`N=83 counties, Y=11 years`),
after `hydrate_initial(total_ticks=520, start_year=2010, ...)`:

```text
population_db_reads  == 913
employment_db_reads  == 913
total_db_reads       == 1826
```

---

## Behavioral invariants

### I1 — Initial state

Before `hydrate_initial` is called:

```python
bridge.population_db_reads == 0
bridge.employment_db_reads == 0
bridge.total_db_reads == 0
```

### I2 — Post-hydrate stability

After `hydrate_initial(total_ticks=T, start_year=Y0,
scope_fips=F, ...)`:

```python
N = len(F)
Y = len(derive_year_set(Y0, T))
bridge.population_db_reads == N * Y
bridge.employment_db_reads == N * Y
bridge.total_db_reads == 2 * N * Y
```

Where `derive_year_set(Y0, T) = {Y0 + t // 52 for t in range(T)}`.

### I3 — Persist-tick invariance (FR-003)

For all valid tick `t ∈ [0, T)`:

```python
counts_before = (bridge.population_db_reads,
                 bridge.employment_db_reads,
                 bridge.total_db_reads)
bridge.persist_tick(t, world)
counts_after = (bridge.population_db_reads,
                bridge.employment_db_reads,
                bridge.total_db_reads)
assert counts_before == counts_after
```

The counter never increments after hydrate. Any divergence is a
correctness regression of FR-003.

### I4 — Single-instance scope (FR-008)

Two `WorldStateBridge` instances in the same process do not share
counters:

```python
a = WorldStateBridge(...); a.hydrate_initial(...)
b = WorldStateBridge(...); b.hydrate_initial(...)
# a.total_db_reads and b.total_db_reads reflect their own runs only.
```

---

## Usage from the slow-gate test

```python
# tests/integration/engine/headless_runner/test_cache_canonical_wallclock.py

def test_sc_002_canonical_read_count(canonical_bridge_post_hydrate):
    """SC-002 — exactly 2 × N × Y reference-data reads."""
    N = 83  # MI + Canada-adjacent counties
    Y = 11  # 2010-2020 inclusive

    bridge = canonical_bridge_post_hydrate
    assert bridge.population_db_reads == N * Y, (
        f"expected {N * Y}, got {bridge.population_db_reads}"
    )
    assert bridge.employment_db_reads == N * Y
    assert bridge.total_db_reads == 2 * N * Y
```

```python
def test_fr_003_persist_tick_does_not_increment_counter(
    canonical_bridge_post_hydrate, sample_world
):
    """FR-003 — persist_tick is forbidden from touching the DB."""
    before = canonical_bridge_post_hydrate.total_db_reads
    for tick in range(0, 520):
        canonical_bridge_post_hydrate.persist_tick(tick, sample_world)
        assert canonical_bridge_post_hydrate.total_db_reads == before
```

---

## What this contract does NOT promise

- **No SQL-execution count**. The properties count *logical* reads
  (per-tuple resolutions), not `cursor.execute()` calls. The actual
  number of SQL executions is 2 or 3 (per R4) regardless of
  `(scope × year_set)` size.
- **No timing data**. The counters are structural (count of reads),
  not temporal. Wallclock gates (SC-001) are observed via the
  runner's existing `manifest.json.wallclock_seconds` field, not
  via this surface.
- **No per-tuple miss visibility**. The counters do not distinguish
  "(fips, year) resolved to a value" from "(fips, year) resolved to
  None." The `mark_*_miss_logged` API on the cache is the surface
  for inspecting missing-data state, not the counter.

---

## Compatibility

This contract introduces three new properties on `WorldStateBridge`
that did not exist pre-spec. No existing property is renamed,
removed, or changed. Code that does not reference the new
properties is unaffected.
