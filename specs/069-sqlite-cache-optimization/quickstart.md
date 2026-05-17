# Quickstart: SQLite per-tick read cache (spec-069)

**Audience**: simulation operator running the canonical Michigan-Canada
scenario, or a developer verifying the SC-001 / SC-002 / SC-003 gates
before merging spec-069 into `dev`.

This is a **how-to** document, not a tutorial — it assumes you already
know how to run the headless simulation. It tells you what's new in
spec-069, where to look for the new instrumentation, and how to verify
each acceptance criterion in turn.

---

## TL;DR

```bash
# Run the canonical scenario (no flag changes; cache is automatic).
mise run sim:headless -- --scenario canonical --ticks 520 --start-year 2010

# Verify SC-001 (≤ 60 min wallclock).
# Look at the `wallclock_seconds` field in the run's manifest.json
# under reports/sim-runs/<timestamp>/ — must be ≤ 3600.

# Verify SC-002 (2 × N × Y reads).
# Look at the new `bridge_db_reads` block in the manifest:
#   population_db_reads:  830   # 83 counties × 10 years (2010..2019)
#   employment_db_reads:  830
#   total_db_reads:      1660

# Verify SC-003 (byte-identical trace.csv).
# Run twice at the same seed, diff the trace.csv files:
diff -q reports/sim-runs/<run1>/trace.csv reports/sim-runs/<run2>/trace.csv
# Expected: no output (files identical).
```

If all three checks pass: spec-069 is operationally green for this run.

---

## What changed in spec-069

1. **`WorldStateBridge.hydrate_initial` has a new required parameter
   `total_ticks: int`.** The runner passes `config.ticks` at the
   existing call site (`runner.py:603`); no operator-facing CLI flag
   changes.
2. **The bridge instantiates a `ReferenceDataCache` at hydrate time**
   and routes every per-tick population / employment-proxy lookup
   through the cache. The cache reads the underlying SQLite
   reference DB once per `(county, year)` tuple at hydrate, never
   again during `persist_tick`.
3. **Three new read-only properties on the bridge**:
   `population_db_reads`, `employment_db_reads`, `total_db_reads`.
4. **A new `bridge_db_reads` block in `manifest.json`** records the
   final counter values for offline operator inspection.
5. **The legacy fetchers in `babylon.persistence.county_aggregation`
   are unchanged** — operator tools and ad-hoc scripts that import
   them directly continue to work.

---

## Verifying each success criterion

### SC-001 — wallclock ≤ 60 min

Run the canonical scenario:

```bash
mise run sim:headless -- --scenario canonical --ticks 520 --start-year 2010
```

Open the manifest:

```bash
cat reports/sim-runs/$(ls -t reports/sim-runs | head -1)/manifest.json | jq '.wallclock_seconds'
```

Expected output: a number ≤ 3600 (i.e., ≤ 60 minutes). For comparison,
the pre-spec-069 baseline on the same hardware was ~5400 s (~90 min).

### SC-002 — exactly `2 × N × Y` reference-data reads

```bash
cat reports/sim-runs/$(ls -t reports/sim-runs | head -1)/manifest.json | jq '.bridge_db_reads'
```

Expected output for canonical Michigan-Canada
(`N = 83 counties, Y = 10 years for 2010-2019` — see `research.md` R3
for the year-set derivation; the runner persists ticks 0..519, never
reaching tick 520 which would correspond to year 2020):

```json
{
  "population_db_reads": 830,
  "employment_db_reads": 830,
  "total_db_reads": 1660
}
```

Any deviation from `2 × N × Y` is a regression of FR-001 or FR-002.

### SC-003 — `trace.csv` byte-identical at same seed

Run the scenario twice with the same seed:

```bash
mise run sim:headless -- --scenario canonical --ticks 520 --start-year 2010 --seed 42
mise run sim:headless -- --scenario canonical --ticks 520 --start-year 2010 --seed 42

# Find the two most recent runs.
RUNS=$(ls -1t reports/sim-runs | head -2)
RUN1=$(echo "$RUNS" | head -1)
RUN2=$(echo "$RUNS" | tail -1)

diff -q "reports/sim-runs/$RUN1/trace.csv" "reports/sim-runs/$RUN2/trace.csv"
```

Expected: no output. The two `trace.csv` files are byte-identical.

### SC-004 — missing-data warning at most once per `(county, year)` tuple

Search the run log for `"persist_tick: population missing"` and
`"persist_tick: employment missing"`:

```bash
RUN=$(ls -t reports/sim-runs | head -1)
grep -c "persist_tick: population missing" "reports/sim-runs/$RUN/run.log"
grep -c "persist_tick: employment missing"  "reports/sim-runs/$RUN/run.log"
```

For the canonical scenario both counts should be `0` (no missing
tuples in 2010-2019 MI+Canada). For a stress-test scenario that
includes a known-missing county / year, the count should equal the
number of missing **tuples**, not the number of missing tuple-ticks
(52 × missing tuples).

---

## What to do if a gate fails

### SC-001 fails (run takes > 60 min)

- Confirm the cache hydrated by checking `total_db_reads > 0` in the
  manifest. If it's 0, the cache isn't being invoked → investigate
  the bridge `hydrate_initial` call site.
- Profile the run with `mise run sim:profile`; if reference-data
  fetches still dominate, the cache isn't reading from itself for
  some per-tick path.
- If reference-data fetches are no longer dominant but other
  bottlenecks emerge (e.g., engine systems), this is out of scope for
  spec-069 — open a follow-up spec.

### SC-002 fails (read count ≠ `2 × N × Y`)

- Check the manifest for the actual counts. If `>` the expected,
  some per-tick path is re-reading; FR-003 violated.
- If `<` the expected, scope was smaller than assumed; check
  `scope_fips` and `derive_year_set` outputs.

### SC-003 fails (`trace.csv` differs across runs)

- Diff the two files (`diff -u file1 file2 | head -50`) to see the
  first divergent line.
- If it's in a column derived from population or employment_proxy,
  the cache may be returning a different (but legitimate) value
  than the per-call fetcher would have — investigate the Census /
  QCEW fallback logic in `ReferenceDataCache.hydrate`.
- If it's in an unrelated column, the regression is elsewhere; not
  a spec-069 problem.

---

## Reverting spec-069

If the cache is suspected of causing a regression, the cleanest
revert is to flip a feature flag (NOT yet implemented; would be a
follow-up if needed). Until that flag exists, the revert is a `git
revert <merge-commit>` against `dev`.

The pre-spec-069 fetchers are still in
`src/babylon/persistence/county_aggregation.py` unchanged, so a
revert restores the original per-tick read path without further
surgery.

---

## Related docs

- `spec.md` — what the spec promises (functional + non-functional).
- `plan.md` — how the implementation maps to the codebase.
- `research.md` — design decisions and rejected alternatives.
- `data-model.md` — internal data structures.
- `contracts/reference_data_cache_contract.md` — cache class contract.
- `contracts/instrumentation_contract.md` — bridge read-counter contract.
- `tasks.md` (to be created by `/speckit.tasks`) — implementation
  task decomposition.
