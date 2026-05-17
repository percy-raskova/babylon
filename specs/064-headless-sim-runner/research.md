# Phase 0: Research — Headless Postgres-Backed Simulation Runner

**Feature**: 064-headless-sim-runner
**Date**: 2026-05-14

This document resolves all open implementation questions identified by the
Technical Context and Constitution Check passes in `plan.md`. Each section
follows the canonical pattern: **Decision** / **Rationale** / **Alternatives
considered**.

---

## R1: Hex hydration performance at Michigan statewide scale

**Open question**: Spec-063 demonstrated hex hydration for the Detroit
tri-county (3 counties → ~1,045 H3 res-7 cells). Default Michigan scope is
83 counties → estimated ~30,000 cells. Will `hydrate_hex_state()` complete
within a reasonable session-init budget at this scale, or do we need to
batch / parallelize / cache?

**Decision**: **Treat hex hydration as a one-shot Postgres-resident
operation**, executed once at session init via the existing
`hydrate_hex_state()`. No batching, no parallelization, no in-memory cache.
Acceptable session-init budget: ≤ 60 seconds for Michigan statewide. If
measurements exceed this, the optimization happens INSIDE
`hydrate_hex_state()` (it is the canonical hydrator), not in the runner.

**Rationale**:
- Spec-063 hydrator is straight-line geopandas + numpy; ~1000 cells took
  <2s in the closure-test (`tests/integration/test_hex_hydration.py`).
  Linear scaling to ~30K cells projects ≤ 60s — well within budget.
- The hydrator's bottleneck is `h3.polygon_to_cells()` per county polygon
  (3,235 counties exist nationally; 83 for MI) plus `executemany` INSERT.
  Both are bounded by I/O on the Postgres side, not Python compute.
- If the projection turns out wrong, the FIX belongs in the hydrator
  itself, not in a runner-side cache layer. Caching at runner level would
  violate II.11 (cross-subsystem ownership) and would be premature.

**Alternatives considered**:
- *In-memory per-county hex cache* — rejected: premature optimization,
  violates II.11.
- *Pre-computed hex inventory in `bridge_county_h3` SQLite table* —
  potentially viable as a future optimization for the SQLite-canonical
  path. Out of scope for v1.
- *Skip hex hydration for the headless runner* — rejected: hex-level state
  is required by the cross-scale aggregation pipeline (spec-062).

**Acceptance test**: Integration test `test_headless_runner_smoke` (US1)
must complete in < 5 minutes wallclock at default scope. Hex hydration
time will be a recorded field in `summary.json.performance` so we can
audit if it grows.

---

## R2: tqdm with stderr + TTY detection for hybrid interactive/CI use

**Open question**: FR-012a requires tqdm progress bar on stderr that
auto-suppresses when stderr is not a TTY. What's the canonical Python
pattern, and how does it interact with our existing `tools/shared.py`
logging setup?

**Decision**: Use `tqdm(... file=sys.stderr, disable=not sys.stderr.isatty())`
with a `mininterval=1.0` to keep updates sparse during fast iteration.

**Rationale**:
- `tqdm` already supports the exact behavior via `disable=` parameter.
- `sys.stderr.isatty()` is the standard Unix-detection idiom; works
  identically on Linux + macOS + Windows (where the runner is not yet
  supported but the idiom won't fight us).
- `mininterval=1.0` prevents update spam when ticks are sub-second; keeps
  the bar update rate human-readable.
- When `disable=True`, tqdm becomes a thin pass-through iterator — zero
  output, zero TTY-control characters. CI logs stay clean.

**Code shape**:
```python
import sys
from tqdm import tqdm

for tick in tqdm(
    range(start_tick, end_tick),
    desc="ticks",
    file=sys.stderr,
    disable=not sys.stderr.isatty(),
    mininterval=1.0,
    unit="tick",
):
    ...
```

**Alternatives considered**:
- *`rich.progress`* — much heavier dep; `tqdm` is already in pyproject.
- *Custom progress emitter* — reinvents the wheel.
- *`logging.info` per N ticks* — loses the visual feedback that motivates
  the choice; only matches the "fallback when piped" half of the spec.

---

## R3: SIGINT handler that's safe with open Postgres transactions

**Open question**: FR-018 requires graceful shutdown on Ctrl-C with partial
artifacts written. The runner holds open Postgres transactions
(per spec-062 `PerTickTransactionEnvelope`). If SIGINT fires mid-tick, the
transaction must be either (a) committed cleanly or (b) rolled back — never
left half-open. What's the safe pattern?

**Decision**: **Cooperative SIGINT via a flag checked at tick boundaries**.
Install a signal handler that sets a `_interrupt_requested` flag; the tick
loop checks the flag BETWEEN ticks (after the in-flight tick's transaction
fully commits via `persist_tick_atomic`). On flag detection, exit the loop,
write partial artifacts, exit 130.

**Rationale**:
- This is the standard "graceful shutdown" pattern for transactional
  workers (matches kubectl, terraform, postgres autovacuum's signal
  handling).
- It guarantees the in-flight tick's transaction completes atomically —
  never partial state in Postgres.
- The user sees responsiveness ≤ 1 tick (sub-second to a few seconds
  depending on per-tick wallclock).
- Two consecutive SIGINTs raise `KeyboardInterrupt` normally (Python's
  default behavior after the handler is replaced once is to re-arm with
  default handler). This gives the operator an escape hatch.

**Code shape**:
```python
import signal

_interrupt_requested = False

def _sigint_handler(signum, frame):
    global _interrupt_requested
    _interrupt_requested = True
    # Restore default handler so a second Ctrl-C aborts immediately
    signal.signal(signal.SIGINT, signal.SIG_DFL)

signal.signal(signal.SIGINT, _sigint_handler)

for tick in tick_iter:
    if _interrupt_requested:
        break
    runtime.persist_tick_atomic(envelope_for_tick(tick))  # atomic commit
```

**Alternatives considered**:
- *Raise KeyboardInterrupt and catch* — risks half-committed transactions
  if the exception fires mid-`executemany`.
- *Two-tier (graceful then immediate)* — Q3 considered this; user chose
  single-tier graceful with exit 130. The "second Ctrl-C escape hatch"
  comes for free because we restore the default handler after the first
  SIGINT.
- *threading.Event* — overkill; Python signals on the main thread can
  use a simple module-level boolean.

---

## R4: Conservation invariant surfacing in `summary.json`

**Open question**: FR-009 requires `conservation_audit` section in
summary.json listing invariant violations with tick number + invariant
name. What's the existing audit log shape from spec-062's
`conservation_audit_log` Postgres table, and how does it map to
spec-053/054/055/056's Hypothesis-driven invariant suite?

**Decision**: **The `conservation_audit` JSON section is a Python projection
of the spec-062 `conservation_audit_log` Postgres table**, filtered to the
current session and ordered by tick. Each row becomes one JSON object with
the same fields the table has: `tick`, `invariant_name`, `severity`,
`details_json`. The Hypothesis-driven invariant suite (spec-053/054/055/056)
already writes to this table at end-of-tick via the `ConservationAuditor`
observer, so the runner does NOT need to re-run invariant checks — it
only needs to read the log.

**Rationale**:
- Spec-062's audit log is the single source of truth. Re-running invariant
  checks in the runner would duplicate logic and risk drift.
- Reading from the audit log respects II.11: the runner reads a single
  declared interface (the audit log table), not the underlying subsystem
  state.
- If the table is empty for the run's session_id, the JSON section is `[]`
  — explicit, easy to validate.

**Schema shape** (see `contracts/summary_json_schema.yaml` for canonical
form):
```json
"conservation_audit": [
  {
    "tick": 423,
    "invariant_name": "US1_no_double_counting",
    "severity": "warning",
    "details": {
      "actual": 1.0001,
      "expected": 1.0,
      "tolerance": 1e-6,
      "discrepancy_pct": 0.01
    }
  }
]
```

**Alternatives considered**:
- *Re-run invariant checks against the trace post-hoc* — duplicates the
  Hypothesis suite, breaks single-source-of-truth.
- *Surface only as boolean "any violations"* — too lossy; FR-009
  requires per-violation detail.

---

## R5: Determinism strategy across all engine systems

**Open question**: SC-003 requires byte-identical artifacts under same
seed. How is RNG currently seeded across all engine systems
(`StruggleSystem.EXCESSIVE_FORCE`, `ConsciousnessSystem` ideology drift,
etc.), and where does the runner inject the top-level seed?

**Decision**: **Single top-level seed plumbed via
`SimulationConfig.random_seed`**, which the engine already supports
(per spec-001 + spec-011). The runner accepts `--seed` (default: a fixed
constant `2010`, NOT derived from `time.time()` so the default produces
deterministic output too) and passes it into `initialize_session(...,
random_seed=N)`.

**Rationale**:
- The engine already has a single-seed contract through `SimulationConfig`.
  No new seeding infrastructure needed.
- A FIXED default seed (rather than randomized-on-each-run) means the
  canonical `mise run sim:e2e-michigan` produces identical artifacts every
  invocation — this is desirable for the LLM-agent use case (US1) where
  consistent reference outputs matter more than fresh randomness.
- Monte Carlo (US2) overrides the seed per-sample, producing the
  cross-sample variance researchers want.
- A "deterministic" marker in `manifest.json` documents that the run's
  seed-input chain is fully deterministic given the recorded inputs.

**Alternatives considered**:
- *Per-system seeds* — over-complicates the contract; existing engine
  uses single-seed already.
- *Hash-derived seed from (run-config + start-time)* — breaks the
  reproducibility property without operator opt-in.

---

## R6: tools/shared.py migration strategy

**Open question**: SC-007 forbids `tools/` scripts from importing the
in-memory engine path (`create_imperial_circuit_scenario`, `WorldState`,
`step`). Today, `tools/shared.run_simulation()` IS this path. What does
the migrated signature look like, and how do downstream tools adapt?

**Decision**: **Replace `tools/shared.run_simulation()`** with a new
function of the same name and shape but pointing at the new
`babylon.engine.headless_runner.run()` under the hood. Pre-existing call
sites (`tools/monte_carlo.py`, `tools/audit_simulation.py`, etc.) keep
calling `shared.run_simulation(...)` and get the new behavior for free.

The signature is preserved by extracting two new pieces:
1. An `engine.headless_runner.run(config, runtime) → RunResult` core
   function (no CLI logic, pure invocation).
2. A wrapper in `shared.run_simulation()` that builds the Postgres runtime,
   composes the config from the existing tool flags, calls
   `headless_runner.run()`, then projects the result into the shape
   pre-existing tools expect (a list of tick-level dicts plus a metadata
   dict — same shape `shared.run_simulation` returns today).

**Rationale**:
- ADR036 says `shared.py` is the single source of truth — this means it's
  also the single migration seam.
- Wrapper-translation preserves SC-004 (no changes to per-tool flags or
  output shapes) while routing all execution through the new canonical
  path.
- The `headless_runner.run()` core function is what CI and US1 invoke
  directly via the `sim:e2e-michigan` mise task. Tools call it
  indirectly via the wrapper.

**Alternatives considered**:
- *Per-tool rewrites* — high churn, error-prone, breaks "Just as things
  were before" for users.
- *New `tools/shared_postgres.py` alongside old `shared.py`* — leaves dead
  code; violates the SC-007 invariant since old shared.py would still
  import the legacy path.

---

## R7: Trace emission view design (II.11 compliance)

**Open question**: The trace CSV needs a per-tick × per-entity snapshot
pulling from multiple subsystems (economic, consciousness, territory,
tensor). How do we satisfy II.11 (cross-subsystem reads via declared
interfaces)?

**Decision**: **Create a Postgres view
`view_runtime_trace_emission`** in migration
`0019_trace_emission_view.sql`. The view JOINs the relevant dynamic
per-tick tables (`dynamic_county_economic_state`,
`dynamic_county_consciousness_state`, `dynamic_county_territory_state`,
etc.) on `(session_id, tick, fips)`, exposing exactly the 22 trace
columns. The runner queries ONLY this view; it never touches the
underlying tables.

**Rationale**:
- II.11 explicitly allows cross-subsystem reads through SQL views with
  declared contracts. This is the canonical mechanism.
- The view's column list IS the trace contract — schema drift in any
  subsystem table is immediately visible as a view-definition diff.
- The view enables future optimization (e.g., materialized view, indexed
  scan) without changing the runner's read code.

**Schema shape** (canonical form in
`contracts/trace_csv_schema.yaml`):
```sql
CREATE OR REPLACE VIEW view_runtime_trace_emission AS
SELECT
    ce.session_id, ce.tick, /* + simulated_year computed */
    ce.fips AS entity_id, 'county' AS entity_kind,
    ce.v, ce.c, ce.s, ce.k,
    cc.p_acquiescence, cc.p_revolution,
    cc.r AS ideology_r, cc.l AS ideology_l, cc.f AS ideology_f,
    ct.surveillance_coupling, ct.internet_access_pct,
    ct.biocapacity_stock, ct.energy_stock, ct.raw_material_stock,
    /* derived rates: profit_rate, exploitation_rate */ ...
    pop.population, emp.employment_proxy
FROM dynamic_county_economic_state ce
LEFT JOIN dynamic_county_consciousness_state cc USING (session_id, tick, fips)
LEFT JOIN dynamic_county_territory_state ct USING (session_id, tick, fips)
LEFT JOIN ...;
```

**Alternatives considered**:
- *4 separate queries + Python join* — N+1 problem at 30K hexes (if we
  extend to hex-level), and re-implements join logic in Python.
- *Materialized view* — premature optimization; can be added later
  without API change.
- *Single per-tick fact table written by every subsystem* — couples all
  subsystems to a foreign trace concern. Rejected per II.11.

---

## R8: Manifest.json structure for reproducibility hashing

**Open question**: FR-010 says manifest.json must list which fields are
deterministic vs non-deterministic, and (per FR-002a) must record
inputs to the reproducibility hash. What's the canonical structure?

**Decision**: `manifest.json` has 4 top-level keys:

```json
{
  "schema_version": "1.0",
  "files": [
    { "name": "trace.csv", "schema_ref": "trace_csv_schema_v1", "row_count": 83000, "sha256": "..." },
    { "name": "summary.json", "schema_ref": "summary_json_schema_v1", "sha256": "..." }
  ],
  "reproducibility": {
    "deterministic_inputs": {
      "seed": 2010,
      "ticks": 1000,
      "start_year": 2010,
      "scope_fips": ["26001", "26003", ...],
      "external_nodes": ["canada"],
      "defines_hash": "sha256-of-GameDefines.load_default()-serialization",
      "data_versions": { "tiger_vintage": "2024", "lodes_max_year": 2022, ... }
    },
    "non_deterministic_inputs": {
      "wallclock_start": "2026-05-14T16:30:00Z",
      "wallclock_end": "2026-05-14T16:38:42Z",
      "hostname": "..."
    },
    "input_hash": "sha256-of-canonical-JSON-of-deterministic_inputs"
  },
  "column_dictionaries": {
    "trace_csv": [
      { "name": "tick", "type": "int", "units": "weekly_tick", "semantics": "..." },
      ...
    ]
  }
}
```

**Rationale**:
- `input_hash` makes determinism testable: two runs with the same hash
  must produce byte-identical `trace.csv` and `summary.json`.
- `deterministic_inputs` is the canonical set of "if you change this,
  output changes"; `non_deterministic_inputs` is "this changes every
  run, ignore for determinism comparison".
- `column_dictionaries` lets LLM agents parse trace.csv without prior
  knowledge — SC-001's first-attempt parseability requirement.
- `schema_ref` strings point at the canonical schema files in this spec's
  `contracts/` directory, versioned via the `schema_version` field.

**Alternatives considered**:
- *No manifest, schemas inline in summary.json* — bloats summary; less
  clean separation.
- *External JSON-Schema URLs* — would force network access for
  validation. Local schema names are sufficient.

---

## R9: CLI flag dictionary and exit code semantics

**Open question**: What's the complete CLI flag surface, and how do exit
codes map to FR-017/018/019/020?

**Decision**: See `contracts/cli_contract.yaml` for the canonical CLI
contract. Summary:

| Flag | Default | Description |
|---|---|---|
| `--ticks` | 1000 | Number of ticks to simulate |
| `--start-year` | 2010 | Calendar year for tick 0 |
| `--seed` | 2010 | Top-level RNG seed |
| `--scope` | `michigan-canada` | Predefined: `michigan-canada`, `detroit-tri-county`, `national`; OR `--fips=26001,26003,...` for explicit list |
| `--external` | `canada` | Comma-separated external nodes (`canada`, `china`, `rest_of_usa`) |
| `--output-dir` | `reports/sim-runs/<ts>/` | Override the artifact directory |
| `--defines` | (none) | Optional path to a TOML overlay for GameDefines overrides |
| `-v` / `--verbose` | INFO | stderr log level (DEBUG / INFO / WARNING / ERROR) |
| `--dry-run` | False | Bootstrap + tick 0 only; no full loop; useful for smoke-test |

| Exit code | Meaning |
|---|---|
| 0 | Run completed (full 1000 ticks OR valid end-game early-termination) |
| 130 | SIGINT received; partial artifacts written |
| 1 | Generic failure (engine exception not caught by any system) |
| 2 | Configuration error (bad flags, unknown scope) |
| 3 | Reference data missing (SQLite or hex hydration empty) |
| 4 | Postgres unreachable / schema mismatch |

**Rationale**:
- Distinct non-zero codes let CI gate (US4) distinguish "engine bug" (1)
  from "operator misconfig" (2-4). Avoids the antipattern of all errors
  collapsing into `exit 1`.
- Code 130 reserved for SIGINT per Unix convention (per Q3 clarification).
- `--scope` accepts both predefined names and explicit FIPS lists,
  resolving the Q4-adjacent assumption deferred from /speckit.clarify.

**Alternatives considered**:
- *Flat exit code 1 for all errors* — collapses operator-vs-engine
  diagnostics. Rejected.
- *YAML config file instead of flags* — adds a fixture surface; flags are
  enough for v1. A config file is trivial to add later.

---

## R10: Wallclock budget verification approach

**Open question**: SC-002 sets the wallclock budget at ≤10 minutes for
1000-tick Michigan + Canada. How do we verify, and what's the rollback
plan if measurements exceed?

**Decision**: **Add wallclock measurement to `summary.json.performance`
section**, and create a smoke-test integration test that ASSERTS the
end-to-end run completes in under 10 minutes (skipping if Postgres test
DB is not present). Track per-system wallclock breakdown:

```json
"performance": {
  "total_wallclock_sec": 487.3,
  "session_init_sec": 28.4,
  "hex_hydration_sec": 14.7,
  "tick_loop_sec": 444.1,
  "artifact_emission_sec": 0.1,
  "per_tick_median_ms": 442.0,
  "per_tick_p99_ms": 1280.0
}
```

If the integration test fails the budget, ROLLBACK plan is:
- **First pivot**: reduce default scope to "lower-michigan" (the lower
  peninsula counties only, ~~50 counties) to bring scope down ~40%.
- **Second pivot**: reduce default ticks to 500 (still ~10 years run).
- **Third pivot**: investigate per-system wallclock; the highest spender
  per the breakdown becomes the optimization target. The runner itself
  is not the bottleneck — engine systems are.

**Rationale**:
- Measure-then-decide. Don't optimize before the integration test runs.
- Per-system breakdown gives concrete attack surface if the budget breaks.
- Pivots are reversible (default scope/ticks are flags) — emergency
  budget relief if needed, not a redesign.

**Alternatives considered**:
- *Pre-measure with a profiler before writing runner* — defers the
  feature; better to ship + measure + iterate.
- *Set a tighter budget (5 minutes)* — premature without measurement.
