# Implementation Plan: SQLite per-tick read cache for the bridged headless runner

**Branch**: `069-sqlite-cache-optimization` | **Date**: 2026-05-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/home/user/projects/game/babylon/specs/069-sqlite-cache-optimization/spec.md`

## Summary

The spec-066-bridged headless runner's `persist_tick` step opens fresh
`sqlite3.Connection`s on the per-(county, tick) hot path for two
reference-data lookups (`fetch_population_for_county_at_tick`,
`fetch_employment_proxy_for_county_at_tick`). The value returned by
those lookups is invariant within a calendar year, so under the weekly
cadence the same fetch is re-executed 51 redundant times before the
year rolls over.

This spec lifts those reads out of the per-tick path into a hydrate-once,
year-keyed cache resident on the bridge instance. The cache is a
`dict[(county_fips, year), CacheEntry]` populated at
`bridge.hydrate_initial()` time via one batched SQL JOIN per fetch
function — issued **once for the union of (county × year) tuples covered
by the run** rather than once per (county, tick) cell. Every
`persist_tick` then reads from the dict, and the missing-data semantics
of the underlying fetchers (one-shot `ReferenceDataMissingError`
surfacing → warn-and-skip) are preserved by encoding "fetched and
missing" as an explicit cache-entry state distinct from "value present"
and "not yet fetched."

The cache is pure latency optimization: `trace.csv` must remain
byte-identical at the same seed (SC-003), the numeric values written
to demographics/employment rows must equal the pre-cache values
exactly (FR-005), and the canonical 520-tick Michigan-Canada run must
complete in ≤ 60 min (SC-001) — a ~30× reduction in bridge-fetch
wallclock from ~3.5 s/tick to ~0.1 s/tick (SC-004).

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard).
**Primary Dependencies**: `sqlite3` stdlib (existing); Pydantic 2.x for
the frozen cache-entry model (existing); no new third-party packages.
**Storage**: Reads from existing `marxist-data-3NF.sqlite` via the
unchanged `babylon.persistence.county_aggregation` fetcher functions.
Cache itself is an in-memory `dict[tuple[str, int], CacheEntry]` bound
to the bridge instance — no persistence layer, no cross-session
sharing (FR-008).
**Testing**: pytest 8.x; new fast-gate unit tests cover year-set
enumeration, three-state cache semantics, miss-handling once-per-tuple,
and instrumentation-counter correctness. A new slow-gate integration
test covers the SC-001 wallclock gate and the SC-002 read-count gate
against the canonical Michigan-Canada scenario.
**Target Platform**: Linux server (canonical-run host) — existing stack.
**Project Type**: Library + CLI extension (bridged headless runner
internals; no new top-level entry point).
**Performance Goals**: SC-001 (≤ 60 min wallclock for canonical 520-tick
run); SC-004 (≥ 30× wallclock reduction in bridge reference-data fetch
overhead); SC-002 (exactly 2 × N × Y reference-data reads against the
underlying database).
**Constraints**: SC-003 (`trace.csv` byte-identical at same seed);
FR-005 (no rounding/quantization/coercion); SC-005 (missing-data
warning at most once per (county, year) tuple).
**Scale/Scope**: 83 counties × 11 calendar years (2010–2020 for the
canonical run) = ≤ 1,826 cache entries; 86,320 → 1,826 reference-data
reads (a 47× structural reduction in read count; the 30× SC-004 number
is wallclock and accounts for connection-open overhead amortization).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v2.6.1 evaluated against this spec. Tier per III.9:

**P0 (Never Drop)**:

- **III.7 Determinism Hash and Replayability** — SC-003 (byte-identical
  `trace.csv` at same seed) is the operational form of III.7 for this
  spec. The cache reads invariant-within-year values; same lookup
  produces same value; nothing in the cache layer introduces
  nondeterminism. ✅ **PASS**.
- **III.8 Structural Provenance (Aleksandrov Test)** — The cache is
  not a new operator. It memoizes a lookup that already grounds in
  material relations (Census household counts → population; QCEW
  employment → employment proxy). No formalism added. ✅ **PASS**.

**P1 (Load-Bearing for this file domain)**:

- **II.6 State is Data, Engine is Transformation** — Includes the
  rule "No DB I/O during tick." Pre-spec, the bridged runner's
  `persist_tick` opens fresh SQLite connections per (county, tick),
  which is the prima facie violation of this principle that
  spec-069 closes. **Post-spec, the bridge becomes II.6-compliant**
  on the persist_tick path. ✅ **PASS (this is the motivation)**.
- **II.11 Subsystem Table Ownership** — The cache reads go through
  the existing `county_aggregation.fetch_*` functions, which are the
  declared interface for persistence reads from the bridge subsystem.
  No new direct table access. ✅ **PASS**.
- **III.1 No Magic Constants** — No new constants introduced. The
  cache configuration is structural (dict, set), not numeric. The
  weekly cadence and start-year mechanics are inherited unchanged
  from spec-065/spec-066. ✅ **PASS**.
- **III.4 Data Catalog** — No new data sources; no
  `.specify/memory/data-catalog.yaml` changes required. ✅ **PASS**.

**Result**: No violations. No `[TRANSITION STATE]` principles touched.
Complexity Tracking section below remains empty.

### Post-Phase-1 re-evaluation

After Phase 0 research and Phase 1 design artifacts (`research.md`,
`data-model.md`, `contracts/*.md`, `quickstart.md`):

- **III.7 Determinism**: R8 (research.md) and the contract's
  "Determinism contract" section together promise byte-identical
  trace at same seed. The cache is a memoization of deterministic
  inputs. Still ✅ **PASS**.
- **III.8 Aleksandrov**: No new operator. The cache memoizes
  values that already trace through Census `household_count` and
  QCEW `employment` to material relations. Still ✅ **PASS**.
- **II.6 No DB I/O during tick**: FR-003 hardens this to a testable
  invariant (`I3` in `contracts/instrumentation_contract.md`). The
  bridge's `persist_tick` becomes I/O-free by construction.
  ✅ **PASS post-design** (strengthened from pre-design "PASS").
- **II.11 Subsystem Ownership**: R10 explicitly preserves the
  existing fetcher functions unchanged for non-bridge callers; the
  cache wraps but does not replace them. Still ✅ **PASS**.
- **III.1 / III.4**: No new constants, no new data sources. Still
  ✅ **PASS**.

No gate change between pre- and post-design. Implementation may
proceed to `/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/069-sqlite-cache-optimization/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── reference_data_cache_contract.md     # Cache lookup Protocol
│   └── instrumentation_contract.md          # Read-counter signal
├── checklists/
│   └── requirements.md  # /speckit.specify validation output
├── spec.md              # /speckit.specify output
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code (repository root)

```text
src/babylon/engine/headless_runner/
├── bridge.py                              # MODIFIED — consume cache instead of per-tick fetches
└── reference_data_cache.py                # NEW — cache impl + instrumentation counter

src/babylon/persistence/
└── county_aggregation.py                  # UNCHANGED — fetcher functions remain authoritative

tests/unit/engine/headless_runner/
├── test_reference_data_cache_year_set.py     # NEW — year-set enumeration
├── test_reference_data_cache_three_state.py  # NEW — NOT_FETCHED/VALUE/MISSING semantics
├── test_reference_data_cache_miss_logging.py # NEW — SC-005 once-per-tuple warning
└── test_reference_data_cache_counter.py      # NEW — instrumentation counter

tests/integration/engine/headless_runner/
├── test_cache_byte_identical_trace.py        # NEW — SC-003 byte-identical gate
└── test_cache_canonical_wallclock.py         # NEW (slow gate) — SC-001 + SC-002
```

**Structure Decision**: Single-package extension within the existing
`src/babylon/engine/headless_runner/` package. The cache is bound to
the bridge instance and is not reused outside that subsystem, so it
co-locates with `bridge.py`. Fetcher functions in
`src/babylon/persistence/county_aggregation.py` remain the authoritative
read path for the underlying database and are unmodified (II.11
compliance: the cache wraps the declared interface, it does not
replace it).

## Complexity Tracking

> No violations identified; this section intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_  | _(n/a)_    | _(n/a)_                              |
