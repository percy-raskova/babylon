# Feature Specification: SQLite per-tick read cache for the bridged headless runner

**Feature Branch**: `069-sqlite-cache-optimization`
**Created**: 2026-05-17
**Status**: Draft
**Input**: User description: "069" (expand spec-066 R8 deferred placeholder into a full specification)

## Context

Spec-066's engine-bridged headless runner persists three subsystem rows per
(county × tick): a consciousness row derived from engine state, a demographics
row, and an employment row. The demographics and employment rows each require
a per-county reference-data lookup that today opens a fresh SQLite connection
and runs a JOIN query against `marxist-data-3NF.sqlite` on every call.

For the canonical 520-tick Michigan-Canada run (83 counties × 520 ticks × 2
fetches = **86,320 SQLite reads**), this dominates wallclock: post-spec-066
the per-tick bridge overhead is ~3.5 s/tick, and the full run takes ~60-90
minutes against an SC-011 budget of 90 min. The reference data being read
is *invariant within a calendar year* — for a weekly cadence the same value
is returned for 52 consecutive ticks before the year rolls over — so the
per-tick work is structurally redundant.

Spec-069 lifts the reference-data reads OUT of the per-tick path and serves
them from a hydrate-once, year-keyed cache resident on the bridge instance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical run finishes within the tightened time budget (Priority: P1)

A simulation operator launches `mise run sim:headless` for the canonical
520-tick Michigan-Canada scenario and walks away. When they return, the
run has completed in under sixty minutes of wallclock — a substantial
margin under the existing 90-minute SC-011 budget and well within the
working session of a single human operator.

**Why this priority**: This is the only user-visible deliverable of the
spec. Every other story exists in service of this one. Without it the
spec does not need to ship.

**Independent Test**: Run the canonical scenario at the published seed,
measure wall-clock from CLI invocation to terminal exit, confirm it is
at or under sixty minutes.

**Acceptance Scenarios**:

1. **Given** the canonical 520-tick Michigan-Canada scenario at the
   published seed, **When** the operator runs the headless simulation
   end-to-end, **Then** wall-clock completion time is at or below sixty
   minutes.
2. **Given** the same scenario at the same seed before and after this
   change, **When** the two runs are compared, **Then** the post-change
   run is at least thirty minutes faster than the pre-change run.

---

### User Story 2 - Operator can verify the cache is doing its job (Priority: P2)

A simulation operator (or CI gatekeeper) wants confidence that the
performance win comes from the structural change rather than from
incidental caching by the operating system, the SQLite page cache, or
filesystem warm-up effects. They need a way to confirm the bridge is
actually reading reference data once per (county × year) tuple — not
once per (county × tick).

**Why this priority**: Without instrumentation the SC-1 wallclock gate
is non-falsifiable. A run could come in under sixty minutes for the
wrong reason (faster disk, warmer page cache, different machine) and
mask a regression that quietly reverts to per-tick reads. This story
makes the structural property of the cache directly observable.

**Independent Test**: Run a short scenario (e.g., 60 ticks across 4
counties at two distinct calendar years), record the number of
reference-data fetches actually executed against the underlying
reference database, and confirm it equals exactly the number of
distinct (county × year) tuples covered — not the number of
(county × tick) cells.

**Acceptance Scenarios**:

1. **Given** a scenario spanning N counties and Y distinct calendar
   years, **When** the operator runs the simulation, **Then** the
   reference-data fetch counter records exactly N × Y × 2 reference-
   data reads across the whole run (two reads per (county × year)
   tuple: one population, one employment proxy).
2. **Given** a scenario in which all ticks fall within a single
   calendar year, **When** the simulation runs, **Then** each
   reference-data fetch function is called at most once per county
   over the entire run.

---

### User Story 3 - Trace output stays byte-identical (Priority: P3)

A regression auditor compares the canonical trace.csv produced before
and after this change at the same seed. Because the cache is a pure
latency optimization with no semantic change, the per-tick numeric
output must be unchanged at the file level.

**Why this priority**: This story is the gate that distinguishes a
correct optimization from a quiet regression. It is lower priority
than the wallclock gate because it is a derived invariant — if SC-1
and SC-2 both pass, the value returned by each cache lookup is by
construction the same value the underlying fetch would have returned.
But putting the contract in writing prevents silently introducing
quantization, type coercion, or rounding drift in the cache layer.

**Independent Test**: Capture the trace.csv from a pre-change canonical
run and a post-change canonical run at the same seed, then diff them
at the byte level.

**Acceptance Scenarios**:

1. **Given** the canonical scenario at the published seed, **When**
   the operator runs it before and after this change, **Then** the
   two trace.csv files are byte-identical.
2. **Given** any scenario at any fixed seed, **When** the operator
   runs it twice on the same machine, **Then** the two post-change
   trace.csv files are byte-identical to each other.

---

### Edge Cases

- **County / year missing from reference data**. The current per-tick
  fetch functions raise a "reference data missing" error for
  (county, year) tuples that have no row in the underlying tables; the
  bridge logs a warning and emits an audit entry without writing the
  demographics or employment row for that tick. The cache MUST preserve
  this semantic gate — a missing-data condition must still surface
  exactly once per (county, year) tuple, not be silently swallowed.
- **Year-in-scope wider than the data window**. A scenario may request
  a calendar year for which the reference DB has no rows at all (e.g.,
  a future year beyond the published data window). The cache MUST treat
  this as a normal "missing data" condition rather than a fatal
  hydrate-time failure that aborts the run.
- **Year rollover at tick boundary**. Under the weekly cadence the
  calendar year increments every 52 ticks. The cache MUST return the
  reference value associated with the *correct* year on either side of
  that boundary — a tick that resolves to year Y+1 must not return the
  cached value for year Y.
- **Hydrate-time data revision**. The reference SQLite database is
  read-only relative to a single simulation run; values fetched at
  hydrate time will be the values served for the duration of that run,
  even if the underlying file is modified mid-run. This matches the
  pre-cache behavior (each per-tick fetch opens its own connection) for
  any read that hits the OS page cache, and is a deliberate property,
  not a defect.
- **Multiple concurrent runs**. The cache is scoped to a single bridge
  instance and is not shared across runs. Two runs in the same process
  or two runs on the same host must not see each other's cached values.
- **Empty year-in-scope**. If the scenario's year-in-scope set is empty
  (a degenerate zero-tick run), hydrate is a no-op and the run
  proceeds without performing any reference-data reads.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bridge MUST compute the full set of (county FIPS,
  calendar year) tuples covered by the scenario before the first tick
  is persisted, and use that set to drive a single bulk hydration of
  reference data.
- **FR-002**: For each (county, year) tuple in the in-scope set, the
  bridge MUST perform at most one population read and at most one
  employment-proxy read against the underlying reference data over the
  lifetime of a single run.
- **FR-003**: When the bridge persists a tick, every per-county
  reference-data value it writes MUST come from the cache populated at
  hydrate time. The per-tick path MUST NOT open a new connection to the
  reference database.
- **FR-004**: A missing-data condition for a (county, year) tuple MUST
  surface to the bridge's existing "missing reference data" logging and
  audit pathway exactly once, when that tuple is first encountered.
  Subsequent ticks for the same (county, year) MUST NOT re-log the
  same condition.
- **FR-005**: The numeric value the bridge writes to the demographics
  row and the employment row at tick T MUST equal the value that the
  pre-cache implementation would have written for tick T, with no
  rounding, quantization, or type coercion introduced by the cache
  layer.
- **FR-006**: The cache MUST distinguish "value not yet fetched" from
  "value fetched and confirmed missing" so that a missing (county,
  year) tuple is not repeatedly re-queried over the 51 subsequent
  ticks of the same calendar year.
- **FR-007**: The system MUST expose, for any single run, an
  instrumentation signal sufficient for an operator or automated test
  to determine the total count of reference-data reads that actually
  occurred against the underlying database during that run.
- **FR-008**: The cache MUST be scoped to a single bridge instance and
  MUST NOT persist across runs, sessions, or processes.

### Key Entities

- **In-scope year set**: The minimal collection of calendar years
  spanned by the scenario, derived from the scenario's start year and
  total tick count under the weekly cadence. Drives the hydrate-time
  enumeration of which (county × year) tuples need to be fetched.
- **Reference-data cache entry**: For each (county FIPS, calendar
  year) tuple, holds the resolved population value, the resolved
  employment-proxy value, and a "fetched and missing" indicator for
  the tuples whose underlying data is absent. Lifetime is bounded by
  the bridge instance.
- **Instrumentation counter**: A per-run accumulator of the number of
  reference-data reads actually issued against the underlying database,
  exposed for verification by SC-2 and any future regression test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The canonical 520-tick Michigan-Canada simulation run
  completes within sixty minutes of wallclock at the published seed.
- **SC-002**: For any scenario spanning N counties and Y distinct
  calendar years, the total number of reference-data reads against the
  underlying database is exactly 2 × N × Y over the entire run
  (verified by the instrumentation counter from FR-007).
- **SC-003**: The trace.csv output of the canonical scenario at the
  published seed is byte-identical before and after this change.
- **SC-004**: The "missing reference data" warning is emitted at most
  once per (county, year) tuple per run, never per (county, tick) cell.

## Assumptions

- The reference SQLite database is read-only for the lifetime of a
  single simulation run. No simulation subsystem mutates the reference
  tables during run.
- The scenario's calendar-year span is knowable before tick 0 — i.e.,
  the operator supplies (or the runner derives) a start year and total
  tick count, and the in-scope year set follows mechanically from
  those two values under the weekly cadence.
- Pre-cache wallclock dominance of the per-tick SQLite reads has
  already been measured. The ~3.5 s/tick bridge-overhead figure cited
  in the spec-066 R8 deferral is the operational basis for expecting
  SC-001 to hold; the directional ~30× reduction in per-tick fetch
  overhead is a derived consequence of the structural change (52×
  fewer reads per (county × year), amortized batch-query setup), not
  an independent acceptance gate.
- Per-bridge-instance scoping is sufficient. There is no current or
  planned need to share cached reference data across runs, sessions,
  or hosts.
- The deterministic-by-seed property of the pre-cache simulation is
  load-bearing for SC-003. Any environmental nondeterminism that
  already exists is unchanged by this spec.

## Dependencies

- The bridged headless runner from spec-065 must be the active entry
  point for the canonical scenario; the cache binds to its
  hydrate-time and persist-tick lifecycle.
- The reference-data fetch functions targeted by this cache must
  already be in their post-spec-066 / post-spec-067 form (single-source-
  of-truth aggregations over canonical-leaf rows).

## Out of Scope

- Cross-run, cross-session, or cross-host caching. The cache is a
  per-bridge-instance optimization only.
- Schema changes, migration changes, or any modification to the
  underlying reference tables.
- Adding new reference-data sources, new per-county metrics, or new
  subsystem rows. The cache covers the existing population and
  employment-proxy reads only.
- Changing the bridge's persistence semantics. The number, shape, and
  content of the rows written per tick must remain identical to
  pre-cache behavior.
- Tightening SC-011 (the wallclock budget) from 90 minutes to a new
  number. SC-001 here is an internal acceptance gate for spec-069; any
  amendment to the spec-066 SC-011 budget is a separate, follow-up
  decision.

## References

- spec-066 Phase 0 R8 — the deferred research item that names spec-069
  as the home for this optimization.
- spec-066 SC-011 — the 90-minute wallclock budget that this spec
  creates headroom under.
- ADR044 (engine integration into bridged runner) — cites spec-069 as
  the planned reclaim of ~30 min wallclock if needed.
- ADR045 (spec-067 QCEW normalization) — cites spec-069 as a TBD
  follow-up in the perf-optimization queue.
