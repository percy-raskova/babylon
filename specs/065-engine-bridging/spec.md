# Feature Specification: Engine-Bridging — Real Per-Tick State Behind the Headless Runner

**Feature Branch**: `065-engine-bridging`
**Created**: 2026-05-15
**Status**: Draft
**Input**: User description: "Lets do engine-bridging in a formal, rigorous specification as you described above. The desired end state is that **when we run our simulation CLI, that all of the various data formats we spit out capture every bit of detail from in-game as if we are playing the game itself**. The simulation should be scoped to the entire state of michigan as well and not merely tri-county area. It should run and populate based on the real data we gathered in our SQLite database"

## Context (informational)

Spec-064 shipped a Postgres-backed headless simulation runner with a
locked artifact-bundle contract (`trace.csv` + `summary.json` +
`manifest.json`). An empirical audit of an actual canonical run
(`reports/sim-runs/2026-05-15T03-47-07Z/`) shows that, while the
plumbing is solid, the artifacts are stub-grade:

- 7 of 22 `trace.csv` columns are always empty
  (`p_acquiescence`, `p_revolution`, `ideology_r`, `ideology_l`,
  `ideology_f`, `population`, `employment_proxy`);
- the populated economic columns carry hardcoded placeholder ratios
  (`c = 2 × v`, `s = 0`, `k = 10 × v`) instead of real engine math;
- `surveillance_coupling` and `internet_access_pct` are uniform across
  all 83 counties (fallback constants instead of per-county FCC data);
- `energy_stock == raw_material_stock` always (placeholder formula);
- tick 999 economically equals tick 0 — the MVP runner's per-tick
  advancement is a no-op carry-forward;
- `external_node_flows: []` and `conservation_audit: []` always — the
  spec-063 BoundaryFlowRegister and spec-062 ConservationAuditor are
  not wired into the runner.

The plumbing is right; the substance is missing. Engine systems that
exist today (`ImperialRentSystem`, `ConsciousnessSystem`,
`SurvivalSystem`, `StruggleSystem`, `ContradictionSystem`,
`TerritorySystem`, `MetabolismSystem`, etc., in
`src/babylon/engine/systems/`) operate on in-memory `WorldState`
graphs in unit tests. The headless runner does not currently invoke
them. This feature closes that gap.

## Clarifications

### Session 2026-05-15

- Q: How should the runner handle reference-data window mismatches
  when the requested simulation window overshoots the available data
  for one or more metrics?
  → A: Rescope the canonical run to fit entirely within the real-data
  window. The canonical run becomes **520 weekly ticks = 10 years**
  starting at **2010**, ending at **2020**. Every metric the engine
  systems read (QCEW wages + employment 2010-2024, LODES commute
  2010-2021, Census income / rent / poverty 2010-2023, BEA county GDP
  2001-2023, BLS unemployment 2005-2020) has complete real-data
  coverage for all 83 Michigan counties across this window. No
  clamping, no extrapolation, no fabricated values for the canonical
  run. Operators may still request longer runs via `--ticks`, in
  which case ticks beyond the data window trigger the spec-063
  clamp-to-available policy and the runner emits a per-metric stderr
  warning at session init naming which years will use clamped values.
- Q: How should the hex hydrator's tick-0 placeholder seeds (`c = 2v`,
  `s = 0`, `k = 10v`, uniform `surveillance_coupling = 0.3`,
  `energy_stock = raw_material_stock = biocapacity/2`) be replaced
  with real-data-driven seeds?
  → A: **Upgrade the hex hydrator in this spec.** The hex hydrator
  (`src/babylon/persistence/hex_hydrator.py`) is the canonical
  tick-0 seeding mechanism per spec-063 and gets rewritten as part
  of this feature so its outputs derive directly from
  `fact_qcew_annual` (for `v`, `employment_proxy`),
  `fact_bea_county_gdp` (for `c` via I/O coefficient × output, and
  `s` as residual of GDP - v - c), `fact_census_median_income` (as a
  cross-check on `v`), `fact_broadband_coverage`
  (`internet_access_pct`, `surveillance_coupling` via spec-063
  coupling formula), `fact_lodes_commuter_flow` (boundary commute
  flows for `k` allocation), `fact_census_population` (`population`),
  and Hickel/Ricci coefficients (`biocapacity_stock`,
  `energy_stock`, `raw_material_stock` via per-county apportionment
  of national reserves) — all keyed on the requested `start_year`.
  No parallel reseed pass; one source of truth.
- Q: Should the CI regression gate (`qa:e2e-regression` mise task)
  use `--strict` by default, so a `critical` conservation violation
  hard-fails the gate?
  → A: **Yes — CI default uses `--strict`.** The `qa:e2e-regression`
  mise task SHALL invoke the runner with `--strict` so any `critical`
  audit row immediately fails the gate with exit code `1`, regardless
  of baseline-diff outcome. The baseline-compare step still runs (and
  can fail independently) for non-critical drift. The `--strict` flag
  remains opt-in for the ad-hoc CLI default (per A4 / FR-012); only
  the CI mise task hardcodes `--strict` on. Operators can run the
  diagnostic-mode equivalent by invoking the runner directly without
  the flag.
- Q: How should events within a single tick be ordered in
  `summary.json.events` to satisfy the SC-003 byte-identical
  determinism contract?
  → A: **Engine emission order.** Events are appended to the array
  exactly as the `EventBus` receives them during each system's
  `step()` call within the tick. The `SimulationEngine.systems` list
  order is the canonical system order (Vitality → Territory →
  Production → Solidarity → ImperialRent → … → Contradiction per
  CLAUDE.md / ADR032), and within each system, events are emitted in
  ascending `entity_id` traversal order over the graph (deterministic
  given the frozen `WorldState`). Zero post-tick sort step. This
  preserves the "which system fired first" signal and requires no
  additional ordering machinery; SC-003 holds because every input is
  deterministic.
- Q: Should `tools/shared.run_simulation()` continue to return
  `final_state = None` (spec-064 status quo) or pass through the
  terminal-tick `WorldState` the bridge already builds?
  → A: **Pass through the terminal-tick `WorldState`.** Under the
  hydrate-run-write strategy (A2), the bridge constructs a
  `WorldState` instance each tick; the last one is the
  highest-fidelity in-memory representation available. The result
  dict's `final_state` field SHALL carry that terminal `WorldState`
  (read-only Pydantic instance — no `step()` calls). This restores
  in-memory `state.entities` / `state.territories` access for legacy
  tool consumers (e.g., `tools/audit_simulation.py`'s
  `calculate_overshoot_ratio`) without violating SC-007 (no engine
  *import* leaks; the consumer doesn't advance state). Callers
  holding the reference after a long run accept the multi-MB
  memory cost.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Headless run produces full-fidelity per-tick state for all 83 Michigan counties (Priority: P1) 🎯 MVP

An operator runs `mise run sim:e2e-michigan`. The resulting
`trace.csv` has 43 160 data rows (83 counties × 520 weekly ticks
covering 2010-2020) in which **every column that applies to
`entity_kind="county"` is populated with a non-empty value**, those
values **vary tick-over-tick** in response to engine math driving
real economic dynamics, and the initial conditions at tick 0 are
seeded from the SQLite reference database (real BLS QCEW wages, real
LODES commute flows, real Census income/poverty/rent, real BEA county
GDP, real FCC broadband penetration, real Hickel/Ricci drain
coefficients) rather than from constant ratios. Every metric the
engine reads has full real-data coverage across the canonical window
— no clamping, no extrapolation.

**Why this priority**: This is the substance behind the headless
runner. Without it the spec-064 artifact contract is shape-only.
Researchers, LLM-agent consumers, and the CI regression gate all need
artifacts that reflect real Babylon dynamics, not no-op carry-forward.

**Independent Test**: Run `mise run sim:e2e-michigan`. Open
`trace.csv`. Confirm: (a) every `entity_kind="county"` row has a
non-null value in every county-applicable column; (b) at least three
distinct columns show ≥ 5 % relative change between tick 0 and tick
519 for at least one county; (c) Wayne County's tick-0 `v` is within
±50 % of its real BLS QCEW 2010 annualized wages divided by 52; (d)
per-county `surveillance_coupling` and `internet_access_pct` show
variance across the 83 counties (standard deviation > 0).

**Acceptance Scenarios**:

1. **Given** the canonical run completed successfully, **When** an LLM
   agent loads `trace.csv` and inspects any county row, **Then** all
   22 columns (4 identity + 4 Marx primitives + 2 survival calculus +
   3 ternary ideology + 2 territory ratios + 3 substrate stocks + 2
   derived rates + 2 demographics) carry meaningful non-null values.
2. **Given** the same run, **When** the agent compares Wayne County
   (FIPS 26163) tick 0 against tick 519, **Then** at least one of
   `v`, `c`, `s`, `k`, `p_revolution`, `ideology_r` shows a difference
   reflecting genuine engine evolution (not floating-point noise).
3. **Given** two identical runs with the same `--seed`, **When** the
   `trace.csv` files are compared byte-for-byte, **Then** they are
   identical (determinism preserved across the bridge).
4. **Given** the run completed, **When** terminal aggregates in
   `summary.json.terminal_state` are inspected, **Then** they reflect
   sums and means over the actual evolved tick-519 state, not the
   tick-0 snapshot.

---

### User Story 2 — Conservation invariants are continuously audited and surfaced (Priority: P2)

The operator runs the canonical sim. The `summary.json` includes a
populated `conservation_audit` array whenever any spec-053/054/055/056
Hypothesis-derived invariant ever fires during the 520-tick run.
Each entry carries the tick, scale, invariant name, severity, and
computed/expected/residual values. A clean run produces zero entries
with severity `critical`. A run with a deliberately injected math
regression produces at least one `critical` entry, and the exit code
remains `0` (the audit log is informational by default), with an
opt-in `--strict` flag turning critical violations into exit code 1.

**Why this priority**: Conservation invariants are the project's
falsifiability backstop (Constitution III.7 / GATE-1). Without them
surfaced per tick, the CI regression gate from spec-064 US4 has
nothing to gate on beyond gross terminal aggregates.

**Independent Test**: Run with an injected invariant violation
(monkey-patch `ImperialRentSystem` to skip a phi-distribution write
for one tick). Confirm `summary.json.conservation_audit` contains an
entry at the injected tick with `severity` in `{"error", "critical"}`.

**Acceptance Scenarios**:

1. **Given** a clean canonical run, **When** the operator inspects
   `summary.conservation_audit`, **Then** zero entries have
   `severity = "critical"`.
2. **Given** an artificially perturbed run, **When** the operator
   inspects `summary.conservation_audit`, **Then** the violation
   appears with the correct `tick`, `invariant_name`, and
   `severity ∈ {"error", "critical"}`.
3. **Given** the canonical run plus `--strict`, **When** any
   `critical` violation fires, **Then** the run exits with code `1`
   and stderr emits the canonical FR-020-format error message.

---

### User Story 3 — External boundary flows persist per tick (Priority: P2)

The canonical sim's `summary.json.external_node_flows` array carries
one object per external boundary node (`canada` at minimum) with
non-zero, monotonically-accumulating `total_phi_inflow`,
`total_trade_inbound`, `total_commute_outbound`, and a positive
`tick_count_with_inflow`. These figures aggregate the per-tick rows
written by the spec-063 `BoundaryFlowRegister` into
`boundary_flow_register`, which is wired into the engine's
`ImperialRentSystem` and `MetabolismSystem` per-tick advancement.

**Why this priority**: Detroit-Windsor and the Canada boundary node
(Constitution IV.1) are first-class international boundary nodes. The
canonical scope (Michigan + Canada) is incomplete without these flows
populating the artifact.

**Independent Test**: Run the canonical sim. Query
`boundary_flow_register` for the session; confirm > 0 rows. Open
`summary.json.external_node_flows`; confirm the `canada` entry's
`total_phi_inflow` equals the sum of `magnitude` for
`flow_type = "drain_edge"` rows targeting Canada in the register.

**Acceptance Scenarios**:

1. **Given** the canonical run, **When** Canada's
   `total_phi_inflow` is computed two ways (Postgres aggregate query
   vs `summary.json` field), **Then** they match within 1 cent.
2. **Given** the run, **When** the operator filters `trace.csv` for
   tick-by-tick changes in Wayne County's `v`, **Then** these
   correlate with Canada's per-tick inflow magnitudes (cross-border
   commute / drain coupling visible).

---

### User Story 4 — End-game detection wired (Priority: P3)

The runner detects end-game conditions surfaced by existing engine
observers and short-circuits the tick loop. When an end-game
condition fires, the run exits cleanly with `exit_reason =
"early_terminated"`, the `summary.json` carries an `end_game_event`
block with the firing `tick` and `condition`, and the artifact
bundle is otherwise complete. This closes spec-064 tasks T024a +
T033, which were deferred because the MVP carry-forward never fired
end-game conditions.

**Why this priority**: End-game detection is the engine's signal
that a run has reached a terminal narrative state (Imperial Collapse,
All-Counties-Dead, Revolution Succeeded). Without it, every run goes
to the full tick budget regardless of in-simulation events.

**Independent Test**: Inject an `EndgameDetector` that forces
`IMPERIAL_COLLAPSE` at tick 250. Run with `--ticks 1000`. Confirm:
exit code 0, `ticks_completed = 250`, `exit_reason =
"early_terminated"`, `end_game_event.tick = 250`,
`end_game_event.condition = "IMPERIAL_COLLAPSE"`.

**Acceptance Scenarios**:

1. **Given** the canonical sim runs under conditions that trigger an
   end-game event mid-run, **When** the run completes, **Then**
   `ticks_completed < ticks_requested`, `exit_reason =
   "early_terminated"`, and `end_game_event` is present in the
   summary.
2. **Given** the canonical sim runs without any end-game trigger,
   **When** the run completes, **Then** `ticks_completed =
   ticks_requested`, `exit_reason = "completed"`, and
   `end_game_event` is absent from the summary.

---

### User Story 5 — Artifacts capture discrete narrative events (Priority: P3)

In addition to the per-tick × per-county economic state in
`trace.csv`, the artifact bundle exposes the engine's discrete event
stream — the firing of `SuperwageCrisis`, `ClassDecomposition`,
`ControlRatioCrisis`, `TerminalDecision`, `ExcessiveForce`,
`Uprising`, and similar `EventType`s emitted during the tick loop.
These appear in a new `events` array within `summary.json` (each
entry: `tick`, `event_type`, `entity_ids`, `severity`, `details`),
giving LLM agents the narrative spine of the run alongside the
numeric trace.

**Why this priority**: A simulation that just emits numbers misses
the story. Events are where the engine's qualitative phase transitions
become legible. Without them, a researcher or LLM agent reading the
bundle cannot answer "what happened narratively in this run" without
re-running and watching stderr.

**Independent Test**: Run the canonical sim. Confirm
`summary.json.events` is a list (empty list acceptable if no events
fired). For at least one event in the list, confirm: `tick` is in
`[0, ticks_completed)`, `event_type` is one of the documented enum
values, and `entity_ids` is non-empty when applicable.

**Acceptance Scenarios**:

1. **Given** a run where engine systems fire at least one event,
   **When** the operator inspects `summary.events`, **Then** every
   firing is represented as a structured entry with `tick` + type +
   payload.
2. **Given** the events list, **When** an LLM agent answers "did a
   superwage crisis occur, and when?", **Then** the answer can be
   derived from `summary.events` alone without source-code access.

---

### Edge Cases

- **E1 — Engine system raises an unhandled exception mid-tick**: the
  per-tick Postgres transaction (spec-062 `PerTickTransactionEnvelope`)
  rolls back so no partial state persists for the failed tick. The
  runner catches the exception, marks `exit_reason = "errored"`,
  writes an `error` block into `summary.json` with the failing tick +
  system name + Python exception class + traceback (paths redacted to
  runner-relative), and exits with code `1`. The artifact bundle is
  partial; `manifest.partial = true`.
- **E2 — A formula returns NaN or +/-Inf**: the engine system that
  produced the bad value MUST be the system that catches it. The
  formula registry's existing constraint types (`Probability`,
  `Currency`, `Coefficient`) already raise `ValidationError` on NaN /
  Inf, so this normally surfaces as E1. If it leaks past validation,
  the conservation auditor flags the affected row at severity `error`;
  the run continues.
- **E3 — A subsystem table is missing rows for tick K**: the trace
  view emits NULL for the missing columns (current MVP behavior).
  The conservation auditor logs a warning. The run continues. This
  case surfaces during bridging for subsystems not yet wired; it
  MUST NOT surface on a fully-bridged run.
- **E4 — Conservation auditor fires a CRITICAL violation**: by
  default the run continues (informational logging); the violation
  appears in `summary.conservation_audit`. With `--strict`, the run
  aborts at the end of the offending tick with exit code `1` and the
  canonical stderr error format.
- **E5 — SQLite reference data is missing rows for a county or
  metric**: reference hydration treats this as a fatal preflight
  failure with exit code `3` (`REFERENCE_DATA_MISSING`); the runner
  refuses to start a sim with incomplete inputs (no silent
  zero-filling).
- **E6 — The per-tick wallclock blows the SC-002 budget**: not a
  runtime error; surfaced via
  `summary.performance.tick_loop_sec > (SC-002 budget − session_init_sec)`.
  The run still completes; the slow-tick metric is the regression
  signal.

## Requirements *(mandatory)*

### Functional Requirements

#### Data fidelity & population (US1)

- **FR-001**: Every column declared `applies_to: ["county", ...]` in
  `contracts/trace_csv_schema.yaml` MUST carry a non-null value for
  every `entity_kind = "county"` row in `trace.csv`, on every tick
  from `0` through `ticks_completed − 1`.
- **FR-002**: Initial-tick (tick 0) values for `v`, `c`, `k`,
  `surveillance_coupling`, `internet_access_pct`, `biocapacity_stock`,
  `energy_stock`, `raw_material_stock`, `population`, and
  `employment_proxy` MUST derive from real reference data in the
  SQLite database (BLS QCEW wages, BEA county GDP, Census median
  income / rent / poverty / population, FCC broadband, LODES commute,
  Hickel-Ricci drain rates), not from constant ratios.
- **FR-002a**: The seeding mechanism MUST be the spec-063 hex
  hydrator (`src/babylon/persistence/hex_hydrator.py`), upgraded as
  part of this feature so its tick-0 writes derive from the SQLite
  reference tables listed in FR-002 for the requested `start_year`.
  No parallel "reseed pass" exists; the hex hydrator is the single
  source of tick-0 truth.
- **FR-002b**: The upgraded hex hydrator MUST produce per-county
  values whose magnitudes match the underlying reference data within
  the SC-005 tolerance band: for at least 5 randomly-sampled
  Michigan counties at `start_year = 2010`, the emitted tick-0 `v`
  is within ± 50 % of `(fact_qcew_annual.total_wages for that
  county-year) / 52`. (This guards against the previous placeholder
  formulas `c = 2v`, `k = 10v` returning silently.)
- **FR-003**: Per-tick advancement of `v`, `c`, `s`, `k`,
  `p_acquiescence`, `p_revolution`, `ideology_r`, `ideology_l`,
  `ideology_f`, `surveillance_coupling`, `internet_access_pct`,
  `biocapacity_stock`, `energy_stock`, and `raw_material_stock` MUST
  invoke the corresponding existing engine system (per
  `src/babylon/engine/systems/`), reading inputs from the current
  Postgres-resident state and writing outputs back inside the spec-062
  `PerTickTransactionEnvelope`.
- **FR-004**: For each county and each tick, the simplex constraint
  `ideology_r + ideology_l + ideology_f ≈ 1.0` (within ±1e-9)
  MUST hold (US3 invariant from the Hypothesis suite).
- **FR-005**: `population` and `employment_proxy` MUST evolve per
  tick from the Census / QCEW reference data (interpolated to weekly
  cadence per spec-062 §III.5) when the reference data covers the
  simulated year window; the runner MUST refuse to start (exit `3`)
  when the requested year window falls outside the reference window
  for any in-scope county.

#### Architectural discipline

- **FR-006**: Each per-tick subsystem state MUST be persisted via a
  declared Postgres table (or a declared extension to
  `dynamic_hex_state`), in keeping with Constitution II.11 (subsystem
  table ownership). New tables MUST be created via numbered
  migrations under `src/babylon/persistence/migrations/`.
- **FR-007**: The `view_runtime_trace_emission` view MUST be updated
  in the same migration that introduces each new subsystem table, so
  the 22-column external contract is satisfied without ad-hoc
  cross-subsystem joins from runner code.
- **FR-008**: The runner MUST NOT short-circuit the tick loop with
  the spec-064 MVP carry-forward optimization. Each tick MUST invoke
  the configured engine systems and persist their writes.
- **FR-009**: All engine systems currently in
  `src/babylon/engine/systems/` — ImperialRent, Solidarity,
  Consciousness, Survival, Struggle, Contradiction, Territory, and
  Metabolism, plus any other system enumerated in the
  `SimulationEngine.systems` list at implementation time — MUST be
  bridged. None may be silently skipped.

#### Conservation audit (US2)

- **FR-010**: A `ConservationAuditor` instance (spec-062 §T068) MUST
  be attached to the `SimulationEngine` for every headless runner
  invocation. Its end-of-tick check MUST run on every committed tick.
- **FR-011**: Every audit row produced by the auditor MUST appear in
  `summary.json.conservation_audit` as a projection (per
  `contracts/summary_json_schema.yaml`), with Postgres severities
  (`ok` / `warn` / `alarm`) mapped deterministically to the contract
  severities (`info` / `warning` / `error` or `critical`).
- **FR-012**: When invoked with `--strict`, the runner MUST exit with
  code `1` the moment any audit row with severity `critical` is
  committed; partial artifacts MUST still be written.
- **FR-012a**: The `qa:e2e-regression` mise task (inherited from
  spec-064 US4) MUST invoke the runner with `--strict` so the CI
  gate hard-fails on any `critical` conservation violation. The
  baseline-compare step (`tools/regression_test.py compare-bundle`)
  still runs after the simulation; it can fail independently on
  non-critical drift exceeding documented tolerances. The ad-hoc
  CLI default (`mise run sim:e2e-michigan` without further flags)
  remains opt-in `--strict`-off per FR-012 / A4.

#### External boundary flows (US3)

- **FR-013**: The `BoundaryFlowRegister` MUST be flushed every tick;
  its rows MUST land in the `boundary_flow_register` Postgres table
  inside the same `PerTickTransactionEnvelope` as the hex state writes.
- **FR-014**: `summary.json.external_node_flows` MUST aggregate
  `boundary_flow_register` rows by `(source_node_id, dest_node_id,
  flow_type)` and produce one entry per external node with
  `total_phi_inflow`, `total_trade_inbound`, `total_commute_outbound`,
  and `tick_count_with_inflow` fields populated from real flow
  magnitudes (not placeholder zeros).

#### End-game detection (US4)

- **FR-015**: The runner MUST poll the configured `EndgameDetector`
  observer at the end of every tick. On a positive detection, the
  runner MUST commit the current tick, halt the loop, and set
  `exit_reason = "early_terminated"`.
- **FR-016**: When the loop halts on an end-game event,
  `summary.json` MUST include an `end_game_event` object with `tick`,
  `condition` (one of the enum values in
  `contracts/summary_json_schema.yaml`), and `details`. The
  `manifest.json.generator.partial` flag remains `false` (an early
  termination is a clean completion, not a partial bundle).

#### Event narrative (US5)

- **FR-017**: Every `EventType` fired by any engine system during the
  tick loop MUST be captured to a new `summary.json.events` array.
  Each entry MUST carry `tick`, `event_type`, `entity_ids` (list of
  affected county FIPS), `severity`, and `details` (free-form JSON
  object).
- **FR-018**: The `events` array MUST be in deterministic
  emission order:
  1. **Inter-tick**: events from tick `N` precede events from tick
     `N+1` for all `N < ticks_completed - 1`.
  2. **Intra-tick, across systems**: events emitted during system
     `S_i.step()` precede events emitted during system `S_j.step()`
     when `i < j` in the canonical `SimulationEngine.systems` list.
  3. **Intra-tick, within a system**: events MUST be emitted via the
     `EventBus` while iterating entities in ascending `entity_id`
     order (or H3 cell index order for hex-resolution systems);
     events for the same entity are emitted in the order the system
     code generates them.

  This ordering rule guarantees byte-identical `summary.json.events`
  serialization across reruns with identical `--seed` (SC-003).

#### Performance & determinism

- **FR-019**: A canonical Michigan + Canada 520-tick run (10 years,
  2010-2020) MUST complete within `session_init_sec + 600 s`
  wallclock — i.e., the tick loop itself stays under 10 minutes
  (SC-002 retained but re-baselined to (a) the new 520-tick canonical
  duration and (b) a tick-loop budget so session init is not
  penalized). The 1000-tick `--ticks` CLI default is preserved for
  operators who want longer runs at degraded data fidelity beyond
  2020.
- **FR-020**: Determinism contract from spec-064 §SC-003 MUST hold:
  two runs with identical `SimulationRunConfig` MUST produce
  byte-identical `trace.csv` and byte-identical `summary.json` modulo
  the documented non-deterministic fields (wallclock, hostname,
  session_id).
- **FR-021**: The `input_hash` in `manifest.json` MUST remain a stable
  function of the deterministic inputs across the engine bridge; two
  runs whose `input_hash` matches MUST produce byte-identical
  artifacts (modulo the non-deterministic fields above).

#### Reference data validation

- **FR-022**: At session init, the runner MUST verify that the SQLite
  reference DB carries non-null values for every required
  `(county_fips, year, metric)` triple in the requested simulation
  window. Behavior depends on the requested window vs the canonical
  real-data coverage:

  - When the requested `(start_year, start_year + ticks/52)` window
    falls **entirely within** the canonical real-data window
    (`2010` to `2020` inclusive for engine-load-bearing metrics —
    QCEW, LODES, Census income/rent/poverty, BEA county GDP, BLS
    unemployment) AND every required `(county_fips, year, metric)`
    triple is non-null in SQLite, the runner proceeds silently.
  - When the requested window **partially overshoots** the data
    window for one or more metrics, the runner emits one stderr
    warning per overshooting metric at session init in the form
    `WARN REFERENCE_DATA_CLAMP: <metric> data ends <max_year>; ticks
    >= <N> will use clamped values from <max_year>` and then
    proceeds with the spec-063 clamp-to-available lookup policy.
  - When any required `(county_fips, year, metric)` triple inside
    the canonical real-data window (2010–2020) is **missing entirely**
    (not just clamped — actually absent from the table for that
    county), the runner MUST exit with code `3`
    (`REFERENCE_DATA_MISSING`), naming the first missing triple in
    the stderr error message.

### Key Entities

- **EngineSystem (existing)**: One of the seven (or more) systems in
  `SimulationEngine.systems`. Currently designed against an in-memory
  `WorldState` (Pydantic + NetworkX). The bridge MUST keep the system
  classes themselves unchanged where possible; the bridge adapts
  state at the boundary.
- **PerTickEngineContext (new conceptual entity)**: The bundle of
  inputs and outputs each engine system needs for one tick. Inputs:
  the prior tick's state read from Postgres. Outputs: the next tick's
  state written through the spec-062 envelope. Conceptual only; no
  specific shape mandated.
- **SubsystemStateTable (new — one per missing column family)**: For
  each subsystem whose state currently appears as NULL in the trace
  view (consciousness, demographics, employment), a per-tick table
  keyed on `(session_id, tick, county_fips)` (or `(session_id, tick,
  h3_index)` for hex-resolution data). Each table is owned by its
  originating subsystem per II.11.
- **Event (new artifact element)**: A discrete engine-emitted event,
  surfaced in `summary.json.events`. Carries `tick`, `event_type`,
  `entity_ids`, `severity`, `details`.
- **ConservationAuditRow (existing)**: Already in
  `conservation_audit_log` (spec-062 §T009). This feature ensures the
  auditor is actually attached and its rows reach
  `summary.conservation_audit`.

## Success Criteria *(mandatory)*

Measured against a single canonical `mise run sim:e2e-michigan` run
with default arguments (`--scope michigan-canada`, `--ticks 520`,
`--seed 2010`, `--start-year 2010`) — 10 years of weekly ticks
covering 2010-2020, fully inside the real-data window for every
engine-load-bearing metric.

- **SC-001 — Zero empty cells**: For every `entity_kind = "county"`
  row in `trace.csv`, every column declared `applies_to` that
  includes `"county"` carries a non-null value. Current MVP baseline:
  7 of 22 columns are always empty (32 %). Target: 0 columns always
  empty.
- **SC-002 — Tick-loop budget**: The 520-tick canonical run's tick
  loop completes in ≤ 600 s wallclock on the developer reference
  machine (session init excluded from the budget). The MVP
  measurement is 0.003 s tick-loop + 31.5 s session init; the
  engine-bridged version must keep total wallclock under 10 min on
  the dev machine (≤ 630 s total).
- **SC-003 — Determinism preserved**: Two runs with identical
  `--seed` produce byte-identical `trace.csv` and byte-identical
  `summary.json` (modulo declared non-deterministic fields).
- **SC-004 — Tick-over-tick evolution**: For at least three distinct
  columns from `{v, c, s, k, p_acquiescence, p_revolution, ideology_r,
  ideology_l, ideology_f, surveillance_coupling, internet_access_pct,
  biocapacity_stock, energy_stock, raw_material_stock,
  employment_proxy}`, the canonical run shows ≥ 5 % relative change
  between tick 0 and tick 519 for at least one in-scope county. (No
  more silent carry-forward.)
- **SC-005 — Real-data anchor**: At tick 0, Wayne County's `v` is
  within ± 50 % of the BLS QCEW 2010 annualized wages for FIPS 26163
  divided by 52. (Anchors the seed against real economic magnitude
  for the canonical start year.)
- **SC-006 — Conservation audit firing**: A clean canonical run
  produces zero `summary.conservation_audit` entries with
  `severity = "critical"`. A run with a deliberately injected math
  regression (skipping the phi-distribution write for one tick)
  produces at least one entry with `severity ∈ {"error", "critical"}`
  at the injected tick.
- **SC-007 — Boundary flows populated**: A clean canonical run
  produces a non-empty `summary.external_node_flows` array containing
  the `canada` entry with `total_phi_inflow > 0`,
  `tick_count_with_inflow > 0`, and
  `total_trade_inbound + total_commute_outbound > 0`.
- **SC-008 — Events captured**: `summary.json.events` is present and
  is a chronologically-ordered list. For the canonical run, the list
  is non-empty (at least one engine event fires across 520 ticks),
  or — if zero events fire — the operator can confirm via stderr logs
  that no engine event types were triggered during that specific run.
- **SC-009 — End-game detection round-trip**: With a forced
  `EndgameDetector` firing at tick 250, the run exits with code `0`,
  `ticks_completed = 250`, `exit_reason = "early_terminated"`, and
  `end_game_event.tick = 250`.
- **SC-010 — Backward-compatible artifact shape**: The 22 columns in
  `trace.csv` and the top-level keys of `summary.json` and
  `manifest.json` remain exactly as locked in spec-064. The new
  `events` array is added under `summary.json` without renaming or
  reordering existing keys. The
  `contracts/trace_csv_schema.yaml`,
  `contracts/summary_json_schema.yaml`, and
  `contracts/manifest_json_schema.yaml` files are updated in-place;
  no parallel v2 schemas.
- **SC-011 — `tools/shared.run_simulation` fidelity restored**: After
  the bridge, the `tools/shared.run_simulation()` result dict's
  previously-degraded fields (`max_tension`, `final_wealth`,
  `phase_milestones`, `terminal_outcome`) carry meaningful non-zero
  values reflecting the bridged engine state, so the Monte Carlo /
  parameter sweep tools recover real statistical signal. **The
  `final_state` field SHALL be populated with the terminal-tick
  `WorldState` instance** the bridge built during its final tick
  iteration — restoring in-memory `state.entities` /
  `state.territories` access for legacy tool consumers (e.g.,
  `tools/audit_simulation.py`'s `calculate_overshoot_ratio`).
  Returned as a read-only frozen Pydantic model; consumers MUST NOT
  invoke `step()` or any mutating engine call on it (SC-007 import
  audit still enforces no engine-internal imports in `tools/`).
- **SC-012 — Hypothesis invariant suite passes**: The full
  spec-053/054/055/056 invariant suite (`test:invariants` or
  equivalent) passes against a fully-bridged run.

## Assumptions

- **A1 — Artifact contract stays backwards-compatible**: The 22-column
  `trace.csv` and the locked top-level keys in `summary.json` /
  `manifest.json` stay byte-stable for existing consumers. The
  `events` array is the only new top-level key added. (The user
  phrase "every bit of detail" is interpreted as "fill the existing
  contract" + "add events"; not "add hex-level rows" or "explode
  every engine internal variable".)
- **A2 — Hydration strategy is read-from-Postgres → engine →
  write-to-Postgres**: Each tick hydrates the in-memory `WorldState`
  from Postgres, runs the engine systems in their existing form, and
  persists the delta. The alternative — porting every engine system
  to read/write Postgres directly — is significantly more invasive
  and reserved for a later optimization spec if the hydration
  round-trip blows SC-002.
- **A3 — Failure policy is fail-fast on engine exception**: An
  unhandled exception inside any engine system aborts the current
  tick (transaction rollback), writes a partial artifact bundle, and
  exits with code `1`. The audit log surfaces non-fatal anomalies
  (NaN clamps, near-zero residuals); only unhandled Python exceptions
  trip the abort.
- **A4 — Conservation auditor is informational by default,
  strict-via-flag**: A `critical` audit row is logged + surfaced in
  `summary.conservation_audit` but does NOT abort the run; the
  operator opts into hard-fail-on-critical with the new `--strict`
  CLI flag.
- **A5 — End-game detection is wired but defaults to "no detector"**:
  The runner accepts an optional `--endgame-detector` flag pointing
  at an entry-point name; absent the flag, no end-game checks fire
  (the run goes to full tick budget). This preserves the spec-064
  default behaviour while making US4 testable.
- **A6 — Subsystem table ownership**: New per-tick state tables
  (consciousness, demographics, etc.) live alongside
  `dynamic_hex_state` under `src/babylon/persistence/migrations/`
  with numbered files following the 0020+ sequence. Each table is
  keyed on `(session_id, tick, county_fips)` for county-resolution
  state or `(session_id, tick, h3_index)` for hex-resolution.
- **A7 — Reference data window**: The canonical run is scoped to
  fit entirely within the real-data window. The canonical
  `(start_year, ticks) = (2010, 520)` covers 2010-2020 inclusive,
  inside the coverage of every engine-load-bearing SQLite metric.
  Operators who request `--ticks > 520` (or other start years that
  push the window past 2020) receive per-metric stderr warnings at
  session init and the run proceeds with spec-063 clamp-to-available
  lookups for the overshooting tail. The runner only hard-refuses
  (exit `3`) when a required `(county, year, metric)` triple inside
  the canonical window is missing entirely from SQLite (data
  integrity failure, not extrapolation).
- **A8 — `sim:e2e-michigan` mise task default**: The canonical mise
  task `sim:e2e-michigan` SHALL pass `--ticks 520` explicitly so the
  canonical operator invocation runs entirely inside real data. The
  CLI flag default (`--ticks 1000`, inherited from spec-064) is
  preserved for direct `python -m babylon.engine.headless_runner`
  invocations; operators wanting the canonical run via the module
  entry point should pass `--ticks 520`.

## Out of Scope

- New engine systems beyond those already in
  `src/babylon/engine/systems/` (bridge what exists; do not extend
  the engine itself in this spec). The hex hydrator in
  `src/babylon/persistence/hex_hydrator.py` IS in scope (FR-002a) —
  it is the tick-0 seeding mechanism, not a new engine system.
- Multiplayer / human-in-the-loop simulation (this is a *headless*
  runner; the in-game-experience metaphor refers to data fidelity,
  not interaction).
- AI / RAG narrative generation from the artifact bundle (separate
  feature; observer pattern only).
- Full-national-scope (3 222 counties) tuning — the Michigan + Canada
  scope is canonical for this spec. National-scope perf is a future
  optimization.
- Hex-resolution trace.csv emission (county-aggregate is the
  contract). Hex-level state remains queryable via Postgres for
  researchers; not exported to the artifact bundle.
- New artifact files beyond the locked trio (`trace.csv` +
  `summary.json` + `manifest.json`).
- AI observer integration with the artifact bundle (per Constitution
  II.5, observers consume artifacts; this spec produces them).

## Dependencies

- **Spec 037 (PostgresRuntime)**: Provides the `RuntimePersistence`
  protocol and `PostgresRuntime` implementation the bridge writes
  through.
- **Spec 061 (Real Backend Wireup)**: Provides the session_id /
  cleanup contract and the `initialize_session` entry point.
- **Spec 062 (Cross-Scale Integration)**: Provides
  `PerTickTransactionEnvelope`, `ConservationAuditor`, the spec for
  II.11 subsystem ownership, and the conservation audit log schema.
- **Spec 063 (Vol II Circulation)**: Provides the
  `BoundaryFlowRegister`, the year-scoped coefficient interpolation
  policy, and the hex hydrator that the bridge inherits as its
  tick-0 state source.
- **Spec 064 (Headless Sim Runner)**: Provides the artifact contracts
  (locked), the CLI surface (extended with `--strict` and
  `--endgame-detector`), the `view_runtime_trace_emission` view
  (extended), and the integration test scaffold this spec exercises.
- **Spec 053 / 054 / 055 / 056 (Invariant suites)**: Provides the
  Hypothesis-driven property tests that gate the bridged engine's
  correctness.
