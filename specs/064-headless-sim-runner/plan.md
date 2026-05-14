# Implementation Plan: Headless Postgres-Backed Simulation Runner

**Branch**: `064-headless-sim-runner` | **Date**: 2026-05-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/064-headless-sim-runner/spec.md`

## Summary

A single Python CLI entry point (invoked via `mise run sim:e2e-michigan` or
`poetry run python -m babylon.engine.headless_runner`) executes a complete
Postgres-backed Babylon simulation for a configurable tick count (default
1000), over a configurable geographic scope (default: 83 Michigan counties
plus Canada boundary node), starting from a configurable calendar year
(default 2010), producing a deterministic artifact bundle: `trace.csv`
(per-tick × per-entity 22-column maximal state), `summary.json`
(run metadata + terminal aggregates + conservation audit + start-year
resolution), and `manifest.json` (schema dictionary + reproducibility hash
inputs).

The runner becomes the canonical execution substrate for all six existing
`tools/` analysis scripts that today bypass Postgres entirely
(`audit_simulation`, `monte_carlo`, `parameter_analysis`,
`sensitivity_analysis`, `profiler`, `landscape_analysis`). The migration seam
is `tools/shared.py:run_simulation`, which gets a new implementation pointing
at the runner; pre-existing tool flags and mise task names are preserved
(FR-014, SC-004).

Determinism, partial-artifacts-on-SIGINT, overwrite-on-collision semantics,
and tqdm-to-stderr progress reporting are all resolved per the
2026-05-14 `/speckit.clarify` session.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard).

**Primary Dependencies**:
- `babylon.persistence.PostgresRuntime` + `RuntimePersistence` (spec-061)
- `babylon.persistence.postgres_initialization.initialize_session`
  (spec-061 / extended in spec-063 for hex hydration)
- `babylon.engine.simulation_engine.step` + `SimulationEngine.run_tick`
  (existing canonical engine path)
- `babylon.persistence.envelope.PerTickTransactionEnvelope` +
  `runtime.persist_tick_atomic` (spec-062 atomicity inheritance)
- `babylon.persistence.tiger_ingestion.ingest_tiger_counties_from_sqlite`
  (yesterday's SQLite-canonical path)
- `babylon.economics.lodes_commute_matrix.LODESCommuteMatrixLoader`
  (spec-063, includes `clamp_to_available` for year-window overflow)
- `tqdm` 4.x (already in `pyproject.toml` — used by other tools)
- `psycopg` 3.x + `psycopg_pool` (existing)
- Pydantic 2.x (existing — frozen models for `SimulationRunConfig`,
  `RunMetadata`, etc.)
- `argparse` (stdlib, matches `tools/` convention)

**Storage**:
- PostgreSQL 16+ for runtime simulation state (per spec-037/061)
- SQLite reference DB (`data/sqlite/marxist-data-3NF.sqlite`) for bootstrap
- Filesystem for artifact bundle (default
  `reports/sim-runs/<UTC-ISO-timestamp>/`)

**Testing**:
- pytest (unit + integration)
- Hypothesis-driven invariant suite from spec-053/054/055/056 — the runner
  MUST surface violations cleanly via `conservation_audit` in `summary.json`
  (FR-009, SC-008)
- New integration tests gated on `BABYLON_TEST_PG_DSN` env var (same pattern
  as `tests/integration/test_tiger_ingestion.py`)

**Target Platform**: Linux/macOS developer machine, Linux CI runner.
Hetzner production server is NOT in scope for this feature (CI gating in
US4 stays opt-in; production runs are out of scope per spec).

**Project Type**: CLI (Python module + mise task wrapper). No web,
no frontend, no service.

**Performance Goals**: SC-002 — 1000-tick Michigan + Canada run completes in
≤ 10 min wallclock on the developer reference machine.

**Constraints**:
- SC-003: deterministic given a seed (byte-identical trace.csv +
  summary.json modulo declared non-deterministic timestamp fields)
- FR-012: stdout reserved strictly for the artifact directory path
- FR-018: SIGINT → exit 130 with partial-artifact bundle written
- FR-007: existing output directory overwritten silently
- SC-007: no `tools/` script may import `create_imperial_circuit_scenario`,
  `WorldState`, or `babylon.engine.simulation_engine.step` after refactor

**Scale/Scope**:
- Default: 83 MI counties + 1 Canada boundary node, weekly tick rate, 1000
  ticks ≈ 19.2 years. Start year 2010 → terminal year ~2029.
- Hex substrate: at H3 res-7 over Michigan land area (~150,000 km² ex.
  Great Lakes), ~30,000 hex cells. Spec-063's hex hydration scaled to 83
  counties is a load test for the hydrator itself.
- Trace artifact: 83 entities × 1000 ticks × 22 columns ≈ 1.8 M CSV cells,
  ~2 MB on disk.
- Postgres per-tick rowcount: spec-062 persistence is already proven at
  tri-county scope; statewide will be ~30× more rows per tick. Performance
  budget for the runner depends on this scaling holding.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### P0 (Never Drop) — applied directly

| Principle | Applicability | Compliance |
|---|---|---|
| I.19 Dialectic Primitive | Runner reads dialectic state via engine API, never redefines `Dialectic` | ✓ PASS — no new primitive |
| I.20 Spatial Substrate | Michigan + Canada uses immutable hex/county substrate | ✓ PASS — no substrate mutation |
| II.9 Morphism Dyadic | Runner doesn't touch morphism graph | ✓ PASS — out of scope |
| **III.7 Determinism Hash** | SC-003 + FR-004 require byte-identical artifacts under same seed | ✓ PASS — first-class requirement |
| III.8 Aleksandrov Test | Runner introduces no new mathematical operators | ✓ PASS — only invokes existing |
| V Verb Atomicity | Runner is not a verb; produces no in-engine actions | ✓ PASS — observer-only |

### P1 (Load-Bearing) — domain-relevant

| Principle | Applicability | Compliance |
|---|---|---|
| **II.5 AI Observes, Never Controls** | Runner produces artifacts FOR LLM consumption (observer pattern). Runner does NOT enable LLM-driven engine intervention. | ✓ PASS — strengthens II.5; LLM consumes `observe()`-style artifact projections |
| II.6 State is Data, Engine is Transformation | Runner uses existing engine.tick() unchanged; artifacts are pure state snapshots | ✓ PASS |
| **II.11 Subsystem Table Ownership** | Trace generation reads across ALL subsystem tables (economic, consciousness, territory, etc.). | ⚠ FLAG — see Complexity Tracking. Resolution: trace generation goes through a single trace-emission view defined in this feature's migration, not via direct cross-subsystem reads from the runner. |
| II.13 Transport Substrate | Detroit-Windsor + LODES OD already wired (spec-063); Michigan statewide extends to all 83 counties | ✓ PASS — no new transport mechanic |
| III.1 No Magic Constants | Start year 2010 traces to spec-063 quickstart convention | ✓ PASS — anchored |
| III.2 Falsifiability | Default start year inside historical-data window enables ground-truth comparison | ✓ PASS — explicit design choice (Q5 clarification) |
| III.4 Data Catalog | LODES / QCEW / BEA / FRED / TIGER all already in catalog | ✓ PASS |
| **IV Michigan Test Case** | Default scope IS Michigan statewide (83 counties) | ✓ PASS — feature directly fulfills Article IV |
| IV.1 Detroit-Windsor Boundary | Canada boundary node is included in default scope | ✓ PASS |
| IV.2 Tri-County Backward-Compat | Spec assumes scope override; tri-county is a supported smaller scope | ✓ PASS |

### P2 (Elaboration) — review

| Principle | Applicability | Compliance |
|---|---|---|
| I.8 Tragedy of Inevitability | Early-termination on end-game condition is a valid outcome (FR-017) | ✓ PASS — collapse-as-default honored |
| III.5 Empirical vs Strategic | Historical-data anchor (Q5) supports empirical comparison; strategic intervention via overrides | ✓ PASS |
| VI Scope Control | Default scope IS material-base-anchored (Michigan + counties + Canada); flag override forces explicit scope decision | ✓ PASS |
| VIII Anti-Patterns | No new pairwise-edge-as-community, no scalar solidarity, no determinism-from-conditions | ✓ PASS — none introduced |

### Gate decision

**PROCEED to Phase 0 research.** Only one flagged concern (II.11 subsystem
boundary), resolved via the trace-emission view described in
Complexity Tracking + research.md.

## Project Structure

### Documentation (this feature)

```text
specs/064-headless-sim-runner/
├── plan.md              # This file
├── research.md          # Phase 0 — research items + decisions
├── data-model.md        # Phase 1 — SimulationRunConfig, TraceRow, RunSummary, etc.
├── quickstart.md        # Phase 1 — operator + LLM-agent walkthrough
├── contracts/
│   ├── trace_csv_schema.yaml      # Phase 1 — CSV column dictionary
│   ├── summary_json_schema.yaml   # Phase 1 — JSON Schema for summary.json
│   ├── manifest_json_schema.yaml  # Phase 1 — JSON Schema for manifest.json
│   └── cli_contract.yaml          # Phase 1 — CLI flag dictionary + exit codes
├── checklists/
│   └── requirements.md  # Spec quality checklist (already exists)
└── tasks.md             # Phase 2 output — NOT created by /speckit.plan
```

### Source Code (repository root)

```text
src/babylon/
├── engine/
│   ├── headless_runner/              # NEW — package (cohesive ~6 closely-related modules)
│   │   ├── __init__.py               # NEW — re-exports `run` from runner.py
│   │   ├── __main__.py               # NEW — `python -m babylon.engine.headless_runner` entry
│   │   ├── runner.py                 # NEW — main `run()` function + tick loop
│   │   ├── argparse_cli.py           # NEW — argparse parser per cli_contract.yaml
│   │   ├── scopes.py                 # NEW — predefined scope registry (michigan-canada, etc.)
│   │   ├── models.py                 # NEW — Pydantic entities (SimulationRunConfig, etc.)
│   │   ├── trace_emitter.py          # NEW — per-tick CSV row capture
│   │   ├── run_summary.py            # NEW — summary.json builder
│   │   └── manifest.py               # NEW — manifest.json + input_hash builder
│   └── simulation_engine.py          # EXISTING — used unchanged
├── persistence/
│   ├── postgres_initialization.py    # EXISTING — extended in spec-063 for hex hydration
│   ├── postgres_runtime.py           # EXISTING — used unchanged
│   ├── tiger_ingestion.py            # EXISTING (yesterday) — reused
│   └── migrations/
│       └── 0019_trace_emission_view.sql  # NEW — cross-subsystem view for trace emission
└── __main__.py                       # EXISTING — `python -m babylon` smoke-test only

tools/
├── shared.py                     # MODIFIED — run_simulation() routes to headless_runner
├── audit_simulation.py           # MODIFIED — imports updated; mise task unchanged
├── monte_carlo.py                # MODIFIED — same pattern
├── parameter_analysis.py         # MODIFIED — same pattern
├── sensitivity_analysis.py       # MODIFIED — same pattern
├── profiler.py                   # MODIFIED — same pattern
└── landscape_analysis.py         # MODIFIED — same pattern

tests/
├── integration/
│   ├── test_headless_runner.py   # NEW — gated on BABYLON_TEST_PG_DSN
│   ├── test_headless_runner_determinism.py  # NEW — byte-identical artifacts under same seed
│   └── test_tools_migration.py   # NEW — assert no SC-007 import violations
└── unit/
    ├── engine/
    │   ├── test_trace_emitter.py # NEW — per-row CSV emission with column ordering
    │   └── test_run_summary.py   # NEW — summary builder against fixture state
    └── tools/
        └── test_shared_dispatch.py  # NEW — tools/shared.py routes to headless_runner

.mise.toml                        # MODIFIED — new `sim:e2e-michigan` task; existing tasks may be retired or re-wired
```

**Structure Decision**: Single project layout with a NEW package
`babylon.engine.headless_runner` as the canonical entry point. The runner
is a **package** (subdirectory with `__init__.py`), not a single module,
because the ~6 closely-related modules (runner, argparse_cli, scopes,
models, trace_emitter, run_summary, manifest) benefit from cohesion under
one namespace. Callers import `from babylon.engine.headless_runner import
run` (re-exported from `runner.py` via `__init__.py`). The runner lives
under `babylon.engine` (not `tools/`) because it IS the engine's canonical
CLI surface — `tools/` is the analysis layer that calls down into it via
`tools/shared.py`. This separation enforces SC-007 (no `tools/` script
imports the in-memory engine path) since the public engine surface becomes
`headless_runner.run()` instead of `step()` + `WorldState`.

## Complexity Tracking

The Constitution Check flagged ONE complexity item that needs explicit
justification:

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Cross-subsystem read for trace emission** (II.11 risk) | The trace CSV needs per-tick per-county snapshot pulling from economic, consciousness, territory, AND tensor subsystems. Going through 4+ separate single-subsystem reads + reassembling in Python is N×slower than a single SQL view. | Pure single-subsystem trace would force EITHER (a) writing 4 separate CSV files and forcing operators to join them — operationally hostile; OR (b) keeping a "trace fact table" written by every subsystem at every tick — couples all subsystems to a foreign trace concern. The view approach owns the cross-subsystem read in a single declared interface (migration `0019_trace_emission_view.sql`) — which IS the II.11-prescribed mechanism ("Cross-subsystem reads MUST go through declared interfaces: SQL views with explicit contracts, RPC boundaries, or event streams"). The complexity is in scope, but it's complexity in the *correct* place: a declared view contract, not ad-hoc cross-table joins from runner code. |

No other complexity items.
