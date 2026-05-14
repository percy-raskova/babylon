# Feature Specification: Headless Postgres-Backed Simulation Runner

**Feature Branch**: `064-headless-sim-runner`
**Created**: 2026-05-14
**Status**: Draft
**Input**: User description: "make a specification feature branch for basically refactoring, condensing, and getting the command line utility to run the Babylon simulation for a thousand ticks using Postgres to simulate running the game engine without player intervention. This should log data to a CSV file as well as a JSON file containing all relevant information. The intention behind these Artefacts is so that an LLM coding agent such as yourself, can parse the output of the game engine, after it has ran. This simulation should be at the scale of Michigan including Canada and will be a kind of e2e test utility. We should also be able to run our Monte Carlo data, and all our other tools in @tools/ to do that statistical analysis, parameter sweeps, adjustments, etc. Just as things were before."

## Overview

A single command-line utility — invoked by an operator, an LLM coding agent, or
CI — runs a complete, deterministic, player-free Babylon simulation against the
canonical Postgres runtime persistence layer at Michigan-state-plus-Canada
scale, for a configurable number of ticks (default 1000), and emits a
structured artifact bundle (CSV trace + JSON summary + manifest) that any
downstream consumer can parse without ambiguity.

The same runner is the substrate for all existing statistical-analysis tooling
in `tools/` — Monte Carlo, parameter sweeps, sensitivity analysis,
profiling, audits — which today run against an obsolete in-memory engine path
that bypasses Postgres, hex hydration, and cross-scale integration. Those tools
must continue to provide their pre-existing interface contract (same mise
tasks, same flags, same artifact shapes) but execute against the new
Postgres-backed runner.

The end state is: one canonical way to run a Babylon simulation for analysis,
testing, or research; deterministic given a seed; producing artifacts an LLM
can read; covering the full Michigan + Canadian-border circuit that spec-062
and spec-063 made possible.

## Clarifications

### Session 2026-05-14

- Q: What is the canonical column set for `trace.csv` (one row per tick per
  measured entity)? → A: **Maximal** — every measured per-county field per
  tick. Specifically: `tick`, `simulated_year`, `entity_id`, `entity_kind`,
  `v`, `c`, `s`, `k`, `p_acquiescence`, `p_revolution`, `ideology_r`,
  `ideology_l`, `ideology_f`, `surveillance_coupling`,
  `internet_access_pct`, `biocapacity_stock`, `energy_stock`,
  `raw_material_stock`, `profit_rate`, `exploitation_rate`, `population`,
  `employment_proxy` (~22 columns, ~2 MB per 1000-tick Michigan run).
  Fields not applicable to a given `entity_kind` (e.g., `population` for an
  external node) are emitted as empty strings.
- Q: What is the output-directory collision policy when the target path
  already exists? → A: **Overwrite silently** — existing contents are
  destroyed and replaced with the new run's artifacts. Optimizes for CI
  re-run ergonomics and same-second collision tolerance; operators wanting
  to preserve prior runs must pass a fresh `--output-dir` per invocation
  or rely on the default timestamp-based naming.
- Q: What is the SIGINT (Ctrl-C) behavior during a long-running simulation?
  → A: **Graceful, exit 130** — the runner installs a SIGINT handler that
  stops the tick loop cleanly, writes whatever partial artifacts it has
  (CSV rows up to the last completed tick + a summary.json with
  `exit_reason = "user_interrupted"` and `ticks_completed = N`), and exits
  with the standard Unix SIGINT exit code 130 so shells and CI see it as
  an interrupt rather than a normal completion.
- Q: What progress feedback does the runner emit during a long simulation?
  → A: **tqdm bar to stderr** — the runner emits an interactive tqdm-style
  progress bar to stderr, auto-suppressed when stderr is not a TTY
  (piping, CI, redirected logs). stdout remains strictly reserved for the
  final artifact-directory path on success, preserving FR-012's
  `$(mise run ...)` capture contract.
- Q: What calendar year should the default 1000-tick run start from?
  → A: **Configurable, default 2010** — matches spec-063 quickstart
  convention (`start_year=2010` Detroit tri-county fixture) and, more
  importantly, anchors the simulation INSIDE the historical-data window
  (LODES 2002–2022, QCEW 2003–2024, BEA varies) so the trace can be
  validated against ground-truth historical outcomes for the majority
  of the 19-year run. The 1000-tick weekly run from 2010 reaches ~2029,
  with the post-data-window years (~2023+) handled by spec-063's existing
  clamp policy. Operators override via `--start-year <YYYY>`. The
  resolved value MUST be recorded in `summary.json` and `manifest.json`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — LLM agent runs a 1000-tick Michigan simulation and parses the results (Priority: P1)

An LLM coding agent (or a human developer) invokes a single mise task to run
the simulation headlessly for 1000 ticks at Michigan + Canada scale. When the
task finishes (success or controlled failure), the working tree contains a
self-describing directory with a CSV time-series and a JSON summary. The agent
can read both files programmatically and answer: did the run succeed? what
were the terminal aggregates? did any conservation invariant break? which
counties showed the largest economic change over the run?

**Why this priority**: This is the core deliverable. Without P1, none of the
other stories matter. Every other tool listed in `tools/` is downstream of
this primary runner.

**Independent Test**: Invoke the new mise task with default settings; assert
that exactly one new output directory appears under the configured artifact
root; assert that the directory contains a non-empty CSV, a JSON file
satisfying the documented summary schema, and a `manifest.json` describing
both. Parse both artifacts with a third-party JSON/CSV library; assert
schema-validity without referencing any internal simulation type.

**Acceptance Scenarios**:

1. **Given** a fresh Postgres test database and a populated SQLite reference
   DB, **When** the operator runs `mise run sim:e2e-michigan`, **Then** the
   command exits 0, prints the artifact directory path on stdout, and the
   directory contains `trace.csv`, `summary.json`, and `manifest.json`.
2. **Given** the same fresh database, **When** the operator runs the same
   command twice with the same seed and the same parameter overrides,
   **Then** both artifact directories produce byte-identical `trace.csv` and
   byte-identical `summary.json` (modulo timestamp fields scoped to a
   declared "non-deterministic" subsection of the manifest).
3. **Given** an LLM coding agent with read-only filesystem access to the
   artifact directory, **When** the agent inspects `summary.json`, **Then**
   the agent can determine: number of ticks run, exit reason (completed /
   early-terminated / errored), tick at which any end-game condition fired,
   sum of imperial rent extracted per external node, sum of conservation-audit
   discrepancies, and a per-county snapshot at terminal tick — all without
   needing access to the running engine.

---

### User Story 2 — Existing Monte Carlo tooling continues to work, now against Postgres (Priority: P2)

A researcher runs `mise run sim:monte-carlo` (or invokes `tools/monte_carlo.py`
directly) with a sample count. The command runs N replicate Michigan simulations
through the same runner used in User Story 1, varying only the random seed
across replicates. The existing CSV-per-sample + aggregate-statistics output
contract is preserved.

**Why this priority**: P2 — required for parity with the pre-existing tool
surface ("Just as things were before"). Researchers and the CI pipeline already
expect this interface.

**Independent Test**: Invoke `mise run sim:monte-carlo 10` (10 samples, fast).
Assert that the output CSV has 10 sample rows, the documented statistical
columns are present (mean, std, CI bounds), and that each row's terminal-tick
aggregates were drawn from a real simulation run (not a stub).

**Acceptance Scenarios**:

1. **Given** the new runner is in place, **When** Monte Carlo runs with 10
   samples and a fixed top-level seed, **Then** the per-sample CSV has
   exactly 10 rows and the aggregate statistics row reports a non-zero
   variance across samples (proving real stochastic divergence, not seed
   reuse).
2. **Given** the same invocation as scenario 1, **When** repeated with the
   same top-level seed, **Then** the full output CSV is byte-identical
   (per-sample reproducibility chain holds end-to-end).

---

### User Story 3 — Parameter sweeps, sensitivity analysis, and profiling continue to work (Priority: P2)

A researcher invokes `mise run sim:sweep`, `mise run tune:morris`, `mise run
tune:sobol`, `mise run tune:landscape`, or `mise run sim:profile` and gets the
same artifact shapes as before, now backed by the new Postgres runner.

**Why this priority**: P2 — same parity argument as US2 but for a wider tool
surface. Each tool is independently valuable but secondary to the headless
runner itself.

**Independent Test**: For each of the listed mise tasks, invoke with small
test parameters (e.g., 3-point sweep, 8-sample Morris); assert the documented
output file appears with non-empty content; assert at least one column varies
non-trivially across rows.

**Acceptance Scenarios**:

1. **Given** the new runner is in place, **When** `mise run sim:sweep` runs
   a 3-point sweep over `economy.extraction_efficiency`, **Then** the output
   CSV has 3 rows and the swept parameter takes 3 distinct values across rows.
2. **Given** the new runner is in place, **When** `mise run sim:profile`
   runs with default ticks, **Then** a cProfile-style report is emitted and
   identifies the top-N hot functions by cumulative time, drawn from the
   actual engine call graph (not the obsolete in-memory path).

---

### User Story 4 — CI gate: 1000-tick Michigan run as an e2e regression check (Priority: P3)

The CI pipeline invokes the headless runner as a long-form regression test
(opt-in, not on every push). The pipeline asserts:
(a) the runner exits 0;
(b) all conservation invariants the codebase tracks (spec-053/054/055/056)
hold at every tick;
(c) selected high-level outcome metrics (e.g., terminal imperial rent total,
terminal county-count-still-alive) fall within tolerance bounds against a
committed baseline.

**Why this priority**: P3 — high value but not blocking for the runner itself
to land. The runner can ship as a developer/LLM tool first, and CI gating can
follow when the team is ready to commit to a wallclock budget.

**Independent Test**: Run the proposed CI invocation locally; assert that
the artifact summary includes a "conservation_audit" section listing zero
violations; assert the runner's exit code is 0.

**Acceptance Scenarios**:

1. **Given** a clean test Postgres instance, **When** the CI invocation runs
   the headless runner, **Then** the run completes within the documented
   wallclock budget and the `summary.json` reports zero conservation
   violations across all 1000 ticks.
2. **Given** an intentional regression (e.g., a parameter value that breaks
   the rent-distribution accounting), **When** CI invokes the runner,
   **Then** the runner exits non-zero and `summary.json` flags the violating
   tick(s) and the violated invariant.

---

### Edge Cases

- **Postgres unreachable**: the runner MUST fail fast with a clear error
  identifying the connection problem; no artifacts written; exit code
  non-zero.
- **SQLite reference DB missing or stale**: the runner MUST fail fast with a
  pointer to `tools/ingest_tiger_geometry.py` (the documented bootstrap path);
  exit code non-zero.
- **Hex hydration produces zero rows**: same fail-fast posture as above.
- **End-game condition fires before tick 1000** (e.g., IMPERIAL_COLLAPSE,
  all counties dead, etc.): the runner MUST stop the loop cleanly, write
  the full artifact bundle, mark `exit_reason = "early_termination"` in
  `summary.json` with the tick + condition, and exit 0 (this is a *valid*
  simulation outcome, not a failure).
- **Disk fills mid-run**: artifacts are written incrementally where possible;
  if writing fails the runner re-raises with a clear error and the partial
  artifacts remain on disk for debugging.
- **Conservation invariant violated mid-run**: the runner records the
  violation in `summary.json` but does NOT abort; the simulation continues
  through tick 1000 so the operator has the full trace. Exit code is 0
  unless the orchestrator (e.g., CI gate in US4) chooses to enforce strictly.
- **A `tools/` analysis script runs against the legacy in-memory path**
  during the transition: this MUST surface as a lint/test error, not a
  silent fallback. Either the script is migrated to the new runner, or it is
  explicitly opted out of the migration in `tools/shared.py`.

## Requirements *(mandatory)*

### Functional Requirements

**The headless runner itself**

- **FR-001**: System MUST provide a single command-line entry point (a mise
  task) that runs a complete headless simulation against the Postgres runtime
  persistence layer without any interactive input.
- **FR-002**: System MUST default to a tick count of 1000 and accept a
  command-line override (`--ticks` or equivalent).
- **FR-002a**: System MUST default the simulation start year to **2010**
  and accept an `--start-year <YYYY>` override. The 2010 default anchors
  the run within the historical-data window so trace output can be
  validated against ground-truth historical outcomes for the majority of
  the 19-year span (LODES 2002–2022, QCEW 2003–2024, BEA varies). Years
  beyond available data (~2023+ for the default run) are handled by
  spec-063's existing clamp policy
  (`LODESCommuteMatrixLoader.clamp_to_available` and analogous fallbacks
  for QCEW/BEA/FRED). The resolved start year MUST be recorded in
  `summary.json` (run metadata) and `manifest.json` (reproducibility hash
  input).
- **FR-003**: System MUST default to a geographic scope of all 83 Michigan
  counties plus the Canadian boundary node and accept overrides for both
  scope dimensions.
- **FR-004**: System MUST accept a configurable random seed and, when given
  the same seed, produce byte-identical CSV and JSON artifacts across runs.
- **FR-005**: System MUST initialize a fresh Postgres session per run
  (`initialize_session` from spec-061 + spec-063 hex hydration) and tear down
  cleanly on exit, regardless of success or failure.
- **FR-006**: System MUST run each tick through the canonical engine path
  (spec-053/054/055/056 invariants enforced), with no in-memory shortcut.

**Output artifacts**

- **FR-007**: System MUST emit, per run, a directory at a configurable
  artifact root (default `reports/sim-runs/<UTC-ISO-timestamp>/`) containing
  at minimum `trace.csv`, `summary.json`, and `manifest.json`. If the target
  directory already exists (operator-supplied `--output-dir` collision, or
  rare same-timestamp re-invocation), the runner MUST overwrite the
  existing contents silently — no error, no suffix-renaming. Operators who
  need to preserve a prior run must pass a fresh `--output-dir` per
  invocation.
- **FR-008**: `trace.csv` MUST contain one row per tick per measured entity
  (county-level granularity by default), with the **maximal** stable column
  set: `tick`, `simulated_year`, `entity_id`, `entity_kind`, `v`, `c`, `s`,
  `k`, `p_acquiescence`, `p_revolution`, `ideology_r`, `ideology_l`,
  `ideology_f`, `surveillance_coupling`, `internet_access_pct`,
  `biocapacity_stock`, `energy_stock`, `raw_material_stock`, `profit_rate`,
  `exploitation_rate`, `population`, `employment_proxy`. Empty string for
  fields that do not apply to a given `entity_kind`. The complete column
  dictionary (column name, type, units, semantics) MUST also appear in
  `manifest.json` so consumers can validate without inspecting source.
- **FR-009**: `summary.json` MUST contain at minimum: run metadata (seed,
  ticks requested, ticks actually run, start/end wallclock, exit reason),
  per-external-node aggregate flows (e.g., total imperial rent for the run),
  per-county terminal-tick snapshot, and a `conservation_audit` section
  listing any invariant violations with tick number + invariant name.
- **FR-010**: `manifest.json` MUST describe the bundle: which files are
  present, their schema versions, the column/field dictionaries, and which
  fields are non-deterministic (timestamps, wallclock durations) versus
  deterministic (everything else).
- **FR-011**: All three artifacts MUST be parseable by standard libraries
  (CSV reader, JSON parser) with no Babylon-internal types required.
- **FR-012**: System MUST print the artifact directory path to stdout on
  success — and ONLY the artifact directory path — so calling shells and
  agents can capture it via `$(mise run sim:e2e-michigan)`. All progress
  feedback, log messages, and tqdm output MUST go to stderr.
- **FR-012a**: System MUST display an interactive tqdm-style progress bar
  on stderr during the tick loop, auto-suppressed when stderr is not a TTY
  (piped output, CI, redirected logs).

**Tool surface preservation**

- **FR-013**: System MUST refactor `tools/audit_simulation.py`,
  `tools/monte_carlo.py`, `tools/parameter_analysis.py`,
  `tools/sensitivity_analysis.py`, `tools/profiler.py`, and
  `tools/landscape_analysis.py` to invoke the new runner instead of the
  legacy in-memory `create_imperial_circuit_scenario` + `step` path.
- **FR-014**: The pre-existing user-facing surface of each tool MUST be
  preserved: same mise task name, same CLI flags, same output-file shapes,
  same column conventions.
- **FR-015**: System MUST update `tools/shared.py` so that its
  `run_simulation` helper (or replacement) returns artifacts compatible with
  the new runner's contract, while preserving any pre-existing callers'
  expectations.
- **FR-016**: System MUST NOT silently fall back to the legacy in-memory
  path when Postgres is unavailable — failure modes are explicit and
  surfaced (per Edge Cases).

**Exit semantics**

- **FR-017**: Exit code 0 on: full 1000-tick run completed; valid
  early-termination (end-game condition fired in the simulation itself).
- **FR-018**: Exit code 130 on user-requested abort via SIGINT (Ctrl-C).
  The runner MUST install a SIGINT handler that stops the tick loop at the
  next safe boundary, writes a partial artifact bundle (CSV rows for all
  completed ticks, `summary.json` with `exit_reason = "user_interrupted"`
  and `ticks_completed = N`, and `manifest.json` flagged
  `partial = true`), and exits 130 (standard Unix SIGINT exit code) so
  shells and CI distinguish interrupt from normal completion.
- **FR-019**: Exit code non-zero (and not 130) on: Postgres unreachable;
  reference data missing; hex hydration produces zero rows; engine raises
  an exception not caught by any system.
- **FR-020**: All non-zero exits MUST emit a structured error message on
  stderr (one-line summary + path to any partial artifacts).

### Key Entities

- **SimulationRun**: A single execution. Carries seed, requested-tick count,
  county set, parameter overrides, output-directory path.
- **TraceRow**: One row in `trace.csv`. Keys: tick, simulated_year,
  entity_id, entity_kind (county / external / national / hex-aggregate);
  measured columns documented in manifest.
- **RunSummary**: One `summary.json`. Sections: run metadata, terminal
  state aggregates, per-external aggregate flows, per-county terminal
  snapshot, conservation audit log, performance summary.
- **ArtifactBundle**: One on-disk directory. Contains `trace.csv`,
  `summary.json`, `manifest.json`, and optionally auxiliary files (e.g.,
  cProfile output when invoked from `sim:profile`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An LLM coding agent unfamiliar with this codebase, given only
  the artifact bundle directory and the manifest, can answer the four core
  questions in US1's Independent Test on the first attempt — without
  reading source code.
- **SC-002**: A 1000-tick Michigan + Canada run completes in under 10
  minutes of wallclock on the developer reference machine (commodity laptop
  with local Postgres on port 5433).
- **SC-003**: Running the same invocation twice with the same seed produces
  byte-identical `trace.csv` AND byte-identical `summary.json` (excepting
  the documented "non-deterministic" subsection — timestamps and durations).
- **SC-004**: All six listed `tools/` scripts (FR-013) continue to work
  through their pre-existing mise tasks after refactor — zero changes to
  task names, flag names, or output-file column orderings.
- **SC-005**: The new mise task is discoverable via `mise tasks` and has a
  clear one-line description.
- **SC-006**: When invoked with a deliberately-broken parameter (e.g., a
  negative wage rate), the runner exits non-zero within 30 seconds with a
  human-readable error pointing to the broken field.
- **SC-007**: No `tools/` script imports `create_imperial_circuit_scenario`,
  `WorldState`, or `babylon.engine.simulation_engine.step` after the
  refactor — these in-memory engine entry points become internal to the
  runner package, not surfaced as tooling APIs.
- **SC-008**: Zero conservation-invariant violations across a 1000-tick
  baseline Michigan run with default parameters and default seed (this is a
  regression guard).

## Assumptions

- **Reference data is preloaded**: The 3NF SQLite reference DB at
  `data/sqlite/marxist-data-3NF.sqlite` is populated (TIGER + QCEW + BEA +
  LODES + ...) per the existing data pipeline. The runner is not responsible
  for bootstrapping reference data.
- **Postgres is running**: A Postgres 16+ instance with the project schema
  applied is reachable via `BABYLON_PG_DSN` or `BABYLON_TEST_PG_DSN`. The
  runner does not provision Postgres.
- **Single Postgres database per run**: Each headless run gets a fresh
  session within a single database; multi-tenant or cross-database scenarios
  are out of scope for v1.
- **Default scope is Michigan + Canada**: Smaller scopes (e.g., Detroit
  tri-county) and larger scopes (multi-state, full-nation) are supported via
  the scope override flag but the canonical CI/test scope is the full state
  of Michigan plus the Canadian boundary node.
- **Existing engine systems are correct**: This feature does not modify
  engine math; it provides a new way to *invoke* the existing engine. Any
  conservation-violation surfacing reveals pre-existing bugs to fix in
  follow-up work.
- **Per-tick CSV granularity is county-level**: Per-hex-per-tick trace
  rows would produce ~1500 hexes × 1000 ticks = 1.5M rows per Michigan run.
  v1 trace defaults to county-level (83 rows × 1000 ticks ≈ 83K rows,
  manageable) with a flag to opt into hex-level for debugging.
- **`tools/shared.py` is the migration seam**: The single function
  `run_simulation` in `tools/shared.py` (ADR036) is the most common
  cross-tool import path. Migrating that function's implementation to call
  the new runner gives most callers an automatic upgrade with no per-tool
  changes; only callers that bypass `shared.py` need direct rewrites.
- **`mise run sim:run` may be retired**: The current `sim:run` task is
  `python -m babylon` and is essentially a smoke-test. It is a candidate for
  retirement in favor of the new `sim:e2e-michigan` task, but the decision
  is deferred — `sim:run` stays for back-compat unless explicitly removed.

## Dependencies

- Spec-061 (`PostgresRuntime`, `RuntimePersistence`, session initialization)
- Spec-062 (cross-scale aggregation, conservation audit log)
- Spec-063 (Vol II circulation, LODES OD ingestion, TIGER + hex hydration)
- Spec-053/054/055/056 (Hypothesis-driven invariant suite — the runner must
  not break any of these and should surface violations cleanly)
- `tools/shared.py` (ADR036 — single source of truth for tool helpers)
- The `data/sqlite/marxist-data-3NF.sqlite` reference DB (populated per
  the existing data pipeline)

## Out of Scope

- New simulation mechanics or engine systems
- New economic theory or formulas
- Frontend visualization of artifact bundles
- Multi-tenant Postgres or distributed simulation
- Streaming / live artifact emission (artifacts are written at end of run,
  not as a websocket stream)
- Cross-run analytics (e.g., comparing two artifact bundles) beyond what
  existing Monte Carlo / sweep tools already produce
- Refactor of any `tools/` script not listed in FR-013 (e.g., `init_db.py`,
  `ingest_*.py`, `generate_fascist_*.py`, `interview_persona.py`,
  `validate_*.py`, `vertical_slice.py` — these are independently scoped and
  remain on their existing entry points)
