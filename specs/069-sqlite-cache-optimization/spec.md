# Spec-069: SQLite per-tick read cache (placeholder)

**Status**: PLACEHOLDER (deferred from spec-066 Phase 0 R8)
**Created**: 2026-05-16
**Owner**: TBD

## Scope (one-paragraph stub)

The spec-065 bridged runner calls `fetch_population_for_county_at_tick()`
and `fetch_employment_proxy_for_county_at_tick()` from
`babylon.persistence.county_aggregation` once per (county × tick). Each
call opens a `sqlite3.connect()` and runs a JOIN query against
`marxist-data-3NF.sqlite`. For the 520-tick canonical Michigan run
(83 counties × 520 ticks × 2 fetches = 86,320 SQLite reads), this
adds ~3.5 s/tick of bridge overhead — the dominant cost of the e2e
pipeline post spec-066.

Spec-069 will move these reads OUT of the per-tick path into a
hydrate-once cache:

  - At `bridge.hydrate_initial`, batch-fetch population AND employment_proxy
    for every (county × year-in-scope) tuple ONCE and store as a
    `dict[(fips, year), float]` cache on the bridge instance.
  - `persist_tick` reads from the cache instead of re-querying SQLite.
  - The cache invalidates on year-rollover (every 52 ticks for the
    weekly cadence).

## Expected wallclock reduction

~3.5 s/tick → ~0.1 s/tick (35× reduction in subsystem-fetch latency).
For the 520-tick Michigan run this reclaims ~30 minutes, taking the
e2e budget from ~90 min back toward ~60 min and creating headroom for
SC-011 tightening to ≤ 60 min in a follow-up.

## Out of scope

- Changing the SQLite schema or migration order.
- Adding new reference-data sources (deferred to spec-070 data-driven
  ideology seeding + spec-067 QCEW refinement).
- Cross-session caching (the cache is per-bridge-instance only).

## Acceptance criteria

- SC-1: The 520-tick canonical Michigan-Canada run completes in
  ≤ 60 minutes wallclock (current spec-066 budget: 90 min).
- SC-2: `fetch_population_for_county_at_tick` and
  `fetch_employment_proxy_for_county_at_tick` are called exactly once
  per `(county × year)` tuple over a full run (verified via SQL
  query-counter instrumentation in a slow-gate test).
- SC-3: The trace.csv values are byte-identical between pre-spec-069
  and post-spec-069 runs at the same seed (cache is a pure latency
  optimization — no semantic change).

## References

- spec-066 Phase 0 R8 — wallclock dominance of per-tick SQLite reads
- spec-066 SC-011 — the relaxed-from-45-to-90-min wallclock budget
- spec-066 ADR044 — companion architectural decision
