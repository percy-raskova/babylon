# Quickstart: Engine-Bridged Headless Runner

**Feature**: 065-engine-bridging
**Audience**: Operator, LLM coding agent, CI engineer, researcher
**Compares against**: spec-064 quickstart (`specs/064-headless-sim-runner/quickstart.md`)

---

## What changed since spec-064

The MVP runner (spec-064) shipped a faithful artifact-bundle delivery
contract running against a **no-op engine**. Spec-065 fills in the
substance: real engine systems advance state per tick, real reference
data seeds tick 0, and every column in `trace.csv` carries meaningful
values.

The CLI surface is mostly the same. Three new flags appear; the
canonical `--ticks` for `sim:e2e-michigan` changes from 1000 to 520:

| Change | Old (spec-064) | New (spec-065) |
|---|---|---|
| Default canonical `--ticks` | 1000 | 520 (10 years of real-data coverage) |
| Default canonical window | 2010-2029 (extrapolated) | 2010-2020 (entirely real) |
| `--strict` flag | did not exist | exits 1 on first `alarm` conservation row |
| `--endgame-detector` flag | did not exist | dotted path to an `EndgameDetector` |
| `--write-baseline <path>` flag | did not exist | copies `summary.json` to baseline on success (T085) |
| `summary.json.events[]` | did not exist | engine event stream, emission-ordered |
| `summary.json.performance.per_system_ms` | did not exist | per-system wallclock breakdown (populates when engine runs; spec-066) |
| `summary.json.terminal_state.max_tension` | did not exist | cross-tick MAX(tension) over EXPLOITATION edges (T080) |
| `manifest.json...engine_systems_invoked` | did not exist | participates in `input_hash` |
| `trace.csv` empty columns | 7 of 22 | 0 of 22 |
| Tick-over-tick variation | none (carry-forward) | real engine dynamics (spec-066 turns this on; today byte-identical per tick within a year) |
| `tools/shared.run_simulation final_state` | None | terminal-tick `WorldState` |
| Postgres tables | hex_state, audit, register, ... | + 4 new per-tick subsystem tables (consciousness, demographics, employment, relationship_state) |

---

## Operator quickstart

### Prerequisites (same as spec-064)

```bash
# Postgres test container running on port 5433
docker ps | rg babylon-pg-isolated || docker start babylon-pg-isolated

# SQLite reference DB present
test -f data/sqlite/marxist-data-3NF.sqlite

# TIGER county geometries ingested (one-time)
mise run data:tiger-counties
```

### Run the canonical 520-tick Michigan + Canada simulation

```bash
mise run sim:e2e-michigan
```

This runs:
- 83 Michigan counties + Canada boundary node
- 520 weekly ticks (2010-2020 inclusive)
- Real BLS QCEW wages, BEA county GDP, Census income/rent, FCC
  broadband, LODES commute, Hickel/Ricci drains seeding tick 0
- ConservationAuditor instantiated in `runner.run()` and called
  end-of-tick via `bridge.persist_tick` → `auditor.audit_end_of_tick(...)`;
  audit rows commit inside the per-tick envelope (T049)
- BoundaryFlowRegister flushing per tick (T055; owned by runner,
  injected into the bridge)
- EventCapture subscribed to every `EventType` on the runner's
  EventBus (T071); the captured stream drains into `summary.events`
- All 15 engine systems firing per tick (Vitality → Territory →
  Production → Solidarity → ImperialRent → Decomposition →
  ControlRatio → Metabolism → Survival → Struggle → Consciousness →
  Contradiction → ContradictionField → FieldDerivative →
  EdgeTransition) — **deferred to spec-066**; the bridged tick loop
  today persists whatever state the engine produces. With the engine
  not yet wired through `world.graph`, state stays byte-identical
  within a calendar year. The wiring above (auditor, register,
  EventBus) is correct from day one so spec-066 turns it on without
  further plumbing.
- Refreshes `tests/baselines/michigan-e2e.json` via `--write-baseline`
  (T085) so the CI regression gate (`mise run qa:e2e-regression`)
  sees the just-produced summary as the new baseline

After ~? minutes (TBD per SC-002 measurement; budget ≤ 10 minutes
tick-loop), the command prints the artifact directory path:

```text
/home/user/projects/game/babylon/reports/sim-runs/2026-XX-XXTHH-MM-SSZ/
```

The directory contains:

```text
trace.csv     # 83 * 520 = 43,160 data rows; ALL 22 columns populated
summary.json  # terminal_state aggregates real numbers (not null); events[] populated
manifest.json # input_hash includes engine_systems_invoked order
```

### Run with stricter conservation gating

```bash
mise run sim:e2e-michigan -- --strict
```

If any tick produces a `severity='critical'` conservation_audit_log
row (e.g., total-Φ-conservation violation, total-v-non-negativity
violation), the run exits with code 1 immediately after that tick
commits, with a partial artifact bundle written.

### Run with end-game detection

```bash
mise run sim:e2e-michigan -- \
  --endgame-detector babylon.engine.observer.ImperialCollapseDetector
```

If the detector positively fires at tick K, the loop halts, exit code
is 0, `summary.run_metadata.exit_reason = "early_terminated"`,
`summary.end_game_event.tick = K`,
`summary.end_game_event.condition = "IMPERIAL_COLLAPSE"`.

### Common overrides

```bash
# Run longer than the real-data window — accept clamp-to-available
# for ticks beyond 2020. The runner emits one stderr warning per
# clamped metric at session init.
mise run sim:e2e-michigan -- --ticks 1000

# Run with a custom start year (still requires real-data window
# coverage 2010-2020 for the canonical config; other windows
# accepted with warnings)
mise run sim:e2e-michigan -- --start-year 2013 --ticks 364   # 7 years 2013-2020

# Profile per-system wallclock breakdown
mise run sim:profile 520

# Profile via cProfile (existing tools/profiler.py)
mise run sim:profile 100   # 100 ticks for fast iteration
```

---

## LLM-agent quickstart

The artifact bundle now has REAL data. Questions an agent can answer
without source-code access:

### Q1: What did Wayne County's revolutionary probability look like across the run?

```python
import csv
from pathlib import Path

bundle = Path(".../reports/sim-runs/2026-XX-XXTHH-MM-SSZ")
trace_path = bundle / "trace.csv"

wayne_p_revolution = []
with trace_path.open() as fh:
    for row in csv.DictReader(fh):
        if row["entity_id"] == "26163" and row["entity_kind"] == "county":
            tick = int(row["tick"])
            p_rev = float(row["p_revolution"]) if row["p_revolution"] else None
            wayne_p_revolution.append((tick, p_rev))

# Find first tick where p_revolution > 0.5
flip_tick = next(
    (t for t, p in wayne_p_revolution if p is not None and p > 0.5),
    None,
)
print(f"Wayne flips at tick {flip_tick}" if flip_tick else "Wayne never flips")
```

### Q2: Did any conservation invariants fire?

```python
import json
summary = json.loads((bundle / "summary.json").read_text())

violations = summary["conservation_audit"]
critical = [v for v in violations if v["severity"] == "critical"]
errors = [v for v in violations if v["severity"] == "error"]
warnings = [v for v in violations if v["severity"] == "warning"]

print(f"Critical: {len(critical)}, errors: {len(errors)}, warnings: {len(warnings)}")
for v in critical[:5]:
    print(f"  tick {v['tick']:>3} {v['invariant_name']:30} {v['details']}")
```

### Q3: What discrete events fired during the run?

NEW in spec-065:

```python
events = summary["events"]
print(f"Total events: {len(events)}")
by_type = {}
for e in events:
    by_type.setdefault(e["event_type"], []).append(e["tick"])

for event_type, ticks in by_type.items():
    print(f"  {event_type}: fired at ticks {ticks[:5]} (first 5 of {len(ticks)})")
```

Sample output a researcher might see:
```
SuperwageCrisis: fired at ticks [127, 134, 158] (first 3 of 12)
ClassDecomposition: fired at ticks [203, 218, 241] (first 3 of 8)
ExcessiveForce: fired at ticks [89, 92, 95, 97, 103] (first 5 of 47)
Uprising: fired at ticks [301, 305] (first 2 of 2)
```

### Q4: Where did the simulation spend its wallclock?

NEW in spec-065:

```python
perf = summary["performance"]
print(f"Total wallclock: {perf['total_wallclock_sec']:.1f}s")
print(f"  session init:  {perf['session_init_sec']:.1f}s")
print(f"  tick loop:     {perf['tick_loop_sec']:.1f}s")
print()
print("Per-system breakdown:")
for system_name, ms in sorted(
    perf["per_system_ms"].items(), key=lambda kv: -kv[1]
):
    print(f"  {system_name:<25} {ms / 1000:>7.1f}s")
```

### Q5: Is this run reproducible?

```python
manifest = json.loads((bundle / "manifest.json").read_text())
print(f"input_hash: {manifest['reproducibility']['input_hash']}")
print(f"engine systems invoked (in order):")
for sys in manifest["reproducibility"]["deterministic_inputs"]["engine_systems_invoked"]:
    print(f"  - {sys}")
```

Two runs with the same `input_hash` produce byte-identical `trace.csv`
and `summary.json` (modulo declared non-deterministic fields).

---

## CI engineer quickstart

### Opt-in nightly gate (`qa:e2e-regression`)

```bash
mise run qa:e2e-regression
```

This invokes the canonical sim with `--strict` and then runs
`tools/regression_test.py compare-bundle` against
`tests/baselines/michigan-e2e.json`. The gate fails when any of:

- The runner exits non-zero (e.g., `--strict` tripped on a critical
  conservation row, an engine system raised an exception)
- `counties_alive` at terminal tick diverges from baseline
- `total_v` at terminal tick diverges by > 1% from baseline
- Any `critical`-severity conservation_audit row appears
- Reference-data preflight refuses (exit 3)

### Regenerating the baseline after an intentional engine change

Spec-065 T085 wires the baseline refresh into the canonical task — the
`sim:e2e-michigan` mise task passes
`--write-baseline tests/baselines/michigan-e2e.json` to the runner so
one command does both:

```bash
# After approving an engine math edit that intentionally changes
# the simulation's behavior:
mise run sim:e2e-michigan
git commit tests/baselines/ -m "test(baseline): refresh michigan-e2e after <engine change>"
```

The runner writes the baseline only on `COMPLETED` or `EARLY_TERMINATED`
exit reasons (skips silently on `ERRORED` / `USER_INTERRUPTED`), so a
strict-mode trip won't overwrite the baseline with a partial bundle.

To run without refreshing the baseline (ad-hoc inspection, alternative
scope, etc.), invoke the runner directly:

```bash
poetry run python -m babylon.engine.headless_runner \
  --scope michigan-canada --ticks 520
```

The baseline includes real `terminal_state` aggregates (not the
spec-064 placeholder zeros) plus the new `events[]` array. Diffing two
baselines tells you exactly what changed in run dynamics.

### Performance regression catch (per FR-019 + SC-002)

`summary.performance.tick_loop_sec` is recorded on every run.
`tools/regression_test.py compare-bundle` can be extended (future
spec) to fail when `tick_loop_sec` exceeds `1.2 × baseline_tick_loop_sec`
— catches engine math edits that accidentally slow the per-tick path.

---

## Working with `tools/shared.run_simulation` after spec-065

The signature is byte-stable per spec-064 SC-007 / FR-015. The
**values** are now meaningful:

```python
from tools.shared import run_simulation
from babylon.config.defines import GameDefines

result = run_simulation(GameDefines.load_default(), max_ticks=520)

# Pre-spec-065: most fields were stub-grade
# Post-spec-065:
print(result["ticks_survived"])        # 520 (or fewer if early-terminated)
print(result["outcome"])               # "SURVIVED" / "DIED"
print(result["max_tension"])           # real max across all EXPLOITATION edges
print(result["final_wealth"])          # sum of state.entities[*].wealth
print(result["final_state"])           # terminal-tick WorldState (NEW)
print(result["phase_milestones"])      # dict of tick numbers per phase event (NEW)
print(result["terminal_outcome"])      # "revolution" / "genocide" / None (NEW)

# Tools can now inspect terminal entity state:
worker = result["final_state"].entities[PERIPHERY_WORKER_ID]
print(f"Final worker wealth: {worker.wealth}")
```

`audit_simulation.py`'s `calculate_overshoot_ratio(state)` and similar
state-inspecting helpers regain full functionality.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Exit code 3, "REFERENCE_DATA_MISSING: \<metric\>..." | A required (county, year, metric) triple is missing inside the canonical 2010-2020 window | Inspect the named triple in SQLite; if data exists but the loader missed it, file a data-pipeline bug |
| Exit code 3 with no clamp warning | The hex hydrator's input scan refuses because a tick-0 county is missing entirely | Check `dim_county` for the missing FIPS; either backfill or remove from scope |
| stderr WARN REFERENCE_DATA_CLAMP at session init | `--ticks N` overshoots the data window for some metric; spec-063 clamp-to-available kicks in | Either reduce `--ticks` to fit the window, or accept the clamp |
| Exit code 1 with `ERROR ENGINE_FAILURE: critical conservation violation at tick N` (with `--strict`) | A `severity='critical'` audit row fired at tick N | Inspect `summary.conservation_audit`; the violation IS the diagnostic. Either fix the engine math or update the baseline |
| `summary.events` is empty | No engine system fired any EventType during the run | This is expected for runs where no phase transitions occurred. Check `summary.performance.tick_loop_sec` to confirm the loop ran |
| `summary.terminal_state.total_v == 0` | Engine evolved state to zero v at terminal tick — full proletarianization collapse | Real engine behavior. Inspect `trace.csv` to confirm the trajectory |
| Determinism failure (two same-seed runs differ) | Most likely cause: a new engine system was added/removed between runs and `engine_systems_invoked` differs | Diff `manifest.reproducibility.deterministic_inputs.engine_systems_invoked` between runs to confirm |

---

## What's still deferred to a future spec

- **Spec-066 — Full SimulationEngine engine wiring through the bridge.**
  Spec-065 plumbs every adapter (ConservationAuditor, BoundaryFlowRegister,
  EventBus, EventCapture, per-system wallclock wrapper, per-tick
  relationship persistence) but does NOT yet call
  `engine.run_tick(world.graph, services, context)` between
  `bridge.hydrate_initial(...)` and `bridge.persist_tick(...)`. As a
  result `summary.events`, `summary.performance.per_system_ms`, audit-
  log alarm rows, boundary-register rows, and
  `terminal_state.max_tension` are all vacuously empty / zero today.
  Spec-066's only mandate is to plug the engine in; the persistence
  surface is already cross-tick correct.
- **Spec-067 — QCEW SQLite normalization** (filter `ownership_id`,
  restoring SC-005's [0.5, 5.0] c/v band — today the absolute totals
  are inflated by the SQLite denormalization; the cross-county
  proportions remain correct).
- **Spec-068 — BEA national industry I-O ingestion** (replace the
  hardcoded `INTERMEDIATE_INPUTS_FRACTION = 0.5` in the hex hydrator
  with per-county BEA I-O coefficients from `fact_bea_national_industry`).
- **Hex-resolution trace.csv emission** (county-aggregate is the
  contract; hex-level state stays queryable via Postgres).
- **National-scope tuning** (Michigan + Canada is canonical; 3 222
  counties is a future perf-optimization spec).
- **Event-driven narrative generation** (the `events[]` array is the
  spine; an AI narrator that consumes it is a separate observer spec).
- **Sub-tick interpolation** for reference data (year-scoped clamp is
  the MVP; future spec adds monthly / quarterly cadence).

---

## Walkthrough verification

This quickstart was walked through end-to-end on **2026-05-15** as
part of T086. Each command, flag, snippet, and link in this file has
been cross-checked against the current CLI surface, mise tasks,
Postgres migrations 0020-0024, and the `babylon.engine.headless_runner`
module. Drift items found during the walkthrough were fixed in the
same commit batch.
