# Implementation Plan: Engine-Bridging — Real Per-Tick State Behind the Headless Runner

**Branch**: `065-engine-bridging` | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/065-engine-bridging/spec.md`

## Summary

Wire the existing in-memory engine systems (`ImperialRentSystem`,
`ConsciousnessSystem`, `SurvivalSystem`, `StruggleSystem`,
`ContradictionSystem`, `TerritorySystem`, `MetabolismSystem`, plus any
others enumerated in `SimulationEngine.systems`) to read/write
Postgres per-tick state so the spec-064 headless runner's artifact
bundle captures every column with real per-tick-varying values.

Approach (resolved by `/speckit.clarify` 2026-05-15):

1. **Canonical run rescoped** to 520 weekly ticks (2010-2020 inclusive)
   so every engine-load-bearing SQLite metric has full coverage with no
   clamping. The `sim:e2e-michigan` mise task passes `--ticks 520`.
2. **Hex hydrator upgraded** (`src/babylon/persistence/hex_hydrator.py`)
   so tick-0 seeds derive from real SQLite reference tables —
   `fact_qcew_annual`, `fact_bea_county_gdp`, `fact_census_*`,
   `fact_broadband_coverage`, `fact_lodes_commuter_flow`, plus
   Hickel/Ricci coefficients — for the requested `start_year`.
3. **Hydrate-run-write per tick**: each tick hydrates an in-memory
   `WorldState` from Postgres, invokes the engine systems in their
   existing form, then persists the deltas back via the spec-062
   `PerTickTransactionEnvelope`. The MVP's `_carry_forward_tick`
   no-op is removed; `_query_trace` reverts to per-tick reads from a
   refreshed `view_runtime_trace_emission`.
4. **New per-tick subsystem tables** for the currently-NULL trace
   columns (consciousness state, demographics, employment) — keyed
   `(session_id, tick, county_fips)` per II.11.
5. **Conservation auditor + boundary flow register + endgame detector
   wired** into the runner's tick loop. New `--strict` CLI flag exits
   1 on first `critical` audit row; `qa:e2e-regression` enables it.
6. **`summary.json.events` array added** to capture engine event
   firings in deterministic emission order.
7. **`tools/shared.run_simulation` final_state restored** to the
   terminal-tick `WorldState` so legacy tools (`audit_simulation.py`)
   regain `state.entities` / `state.territories` access.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard).

**Primary Dependencies** (all existing):
- `babylon.engine.simulation_engine.SimulationEngine` + per-tick `systems` list
- `babylon.engine.systems.*` (Vitality, Territory, Production, Solidarity,
  ImperialRent, Decomposition, ControlRatio, Metabolism, Survival,
  Struggle, Consciousness, Contradiction, ContradictionField,
  FieldDerivative, EdgeTransition — verified via `SimulationEngine`
  docstring)
- `babylon.models.world_state.WorldState` (frozen Pydantic + NetworkX graph)
- `babylon.persistence.PostgresRuntime` +
  `RuntimePersistence` protocol (spec-037 / 061)
- `babylon.persistence.envelope.PerTickTransactionEnvelope` +
  `runtime.persist_tick_atomic` (spec-062)
- `babylon.persistence.hex_hydrator.hydrate_hex_state` (spec-063;
  upgraded by FR-002a)
- `babylon.persistence.conservation_audit.ConservationAuditor` (spec-062 §T068)
- `babylon.economics.boundary_flow_register.BoundaryFlowRegister` (spec-063)
- `babylon.engine.event_bus.EventBus` + `babylon.models.enums.EventType`
- `babylon.engine.observer.EndgameDetector` (spec-064 §T033 — wiring deferred to this spec)
- `babylon.engine.headless_runner.*` (spec-064; receives the bridge)
- `psycopg` 3.x + `psycopg_pool` (existing)
- `pydantic` 2.x (existing)

**Storage**:
- PostgreSQL 16+ for runtime per-tick state (spec-037/061/062 stack)
- SQLite (`data/sqlite/marxist-data-3NF.sqlite`) read-only for
  reference data (QCEW, BEA, Census, FCC, LODES, Hickel/Ricci, …)
- Filesystem artifact bundle (`reports/sim-runs/<UTC-ISO>/`)

**Testing**:
- pytest (unit + integration)
- Hypothesis suite from spec-053/054/055/056 — every invariant
  property MUST pass against a fully bridged run (SC-012)
- Integration tests gated on `BABYLON_TEST_PG_DSN` (mirror
  spec-064 pattern)
- New schema-parity test in `tests/unit/persistence/` for every new
  subsystem table

**Target Platform**: Linux/macOS dev machine + Linux CI runner. No
production target.

**Project Type**: CLI extension (spec-064 headless runner — receives
substantive engine wiring). No web/frontend/service surface.

**Performance Goals**:
- SC-002 (re-baselined per FR-019): 520-tick canonical run's tick
  loop ≤ 600 s wallclock (session_init excluded).
- Per-tick budget: 520 ticks / 600 s ≈ 1.15 s/tick. MVP per-tick was
  3 µs (no-op); the engine systems will spend 99.999%+ of that
  budget. Risk register entry below.

**Constraints**:
- SC-003 byte-identical determinism preserved.
- SC-010 artifact contract backwards-compatible (22-column trace.csv
  + locked top-level keys in summary.json + manifest.json; `events`
  is the only new top-level summary key).
- II.11 subsystem table ownership — new tables owned by their
  subsystem, exposed only via the declared `view_runtime_trace_emission`
  view.
- III.7 determinism hash — input_hash MUST remain stable; bridge
  introduces no new RNG sources beyond the existing
  `SimulationConfig.random_seed`.
- IV.1 Detroit-Windsor first-class boundary preserved via the
  Canada external node + boundary_flow_register integration.

**Scale/Scope**:
- 83 Michigan counties × 520 ticks = 43 160 trace rows.
- 45 572 hex cells (spec-064 measurement) × 520 ticks = ~24 M
  dynamic_hex_state rows IF we go back to per-tick persistence at
  hex granularity. We will NOT — see Phase 1 §SubsystemTables —
  county-resolution per-tick rows scale to 43 160 across the
  consciousness/demographics/employment tables combined.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### P0 (Never Drop) — applied directly

| Principle | Applicability | Compliance |
|---|---|---|
| I.19 Dialectic Primitive | Bridge reads/writes dialectic state via engine API; never redefines `Dialectic`. | ✓ PASS — no new primitive. |
| I.20 Spatial Substrate | Hex grid + county FIPS unchanged; bridge is pure read/write. | ✓ PASS — no substrate mutation. |
| II.9 Morphism Dyadic | Bridge doesn't touch morphism graph; engine systems do via existing API. | ✓ PASS — preserved as-is. |
| **III.7 Determinism Hash** | SC-003 + FR-020 + FR-021 require byte-identical artifacts under same seed; FR-018's emission-order rule is the determinism stabilizer for the new `events` array. | ✓ PASS — first-class requirement; Q4 explicitly resolved it. |
| III.8 Aleksandrov Test | Bridge introduces no new mathematical operators; the existing engine systems already trace to material relations. | ✓ PASS — observer-only at the bridge layer. |
| V Verb Atomicity | Headless runner is not a verb; produces no in-engine player actions. | ✓ PASS — observer-only artifact emission. |

### P1 (Load-Bearing) — domain-relevant

| Principle | Applicability | Compliance |
|---|---|---|
| **II.5 AI Observes, Never Controls** | Bridge produces artifacts FOR LLM consumption; preserves spec-064's observer-only stance. The bridge calls `engine.run_tick()` — engine logic; not an AI control surface. | ✓ PASS — strengthens II.5. |
| II.6 State is Data, Engine is Transformation | Per-tick: hydrate frozen WorldState → engine.tick() → persist delta. WorldState frozen between persist + next hydrate; no DB I/O *during* tick computation. | ✓ PASS — the persist step is post-tick, not during. |
| **II.11 Subsystem Table Ownership** | New per-tick tables (consciousness, demographics, employment) MUST live under their owning subsystem and be exposed only via the spec-064 `view_runtime_trace_emission` view. | ⚠ FLAG — explicit subsystem ownership labels per table required; tracked in Complexity. |
| II.13 Transport Substrate | LODES OD matrix + boundary flow register already wired in spec-063; the bridge inherits them via ImperialRent + Metabolism systems. | ✓ PASS — no new transport mechanic. |
| III.1 No Magic Constants | Placeholder ratios (`c=2v`, `k=10v`, `surveillance=0.3`) are exactly what FR-002a + Q2 eliminate. | ✓ PASS — feature directly closes this gap. |
| III.2 Falsifiability | Real data anchors SC-005 (Wayne QCEW within ±50%); spec-053..056 invariant suite gates the bridge (SC-012). | ✓ PASS — strengthened. |
| III.4 Data Catalog | All reference tables read by the upgraded hex hydrator are in `data-catalog.yaml` (QCEW, BEA, Census, FCC, LODES, Hickel/Ricci). | ✓ PASS — no new sources. |
| III.6 Model Pinning | No AI parsing in this feature; observer pattern only. | N/A. |
| **IV Michigan Test Case** | Default scope IS Michigan statewide (83 counties), and the canonical window 2010-2020 is exactly the constitutional IV test window. | ✓ PASS — feature directly fulfills Article IV with full real-data coverage. |
| IV.1 Detroit-Windsor Boundary | Canada external node + boundary_flow_register wired per US3 / FR-013 / FR-014. | ✓ PASS — first-class. |
| IV.2 Tri-County Backward-Compat | Tri-county scope remains a valid `--scope detroit-tri-county` choice. | ✓ PASS — non-breaking. |

### P2 (Elaboration) — review

| Principle | Applicability | Compliance |
|---|---|---|
| I.8 Tragedy of Inevitability | End-game detection (US4 / FR-015 / FR-016) preserves the "collapse as default" narrative; the runner doesn't suppress end-game events. | ✓ PASS. |
| I.13 Principal Contradiction | Handled by existing `ContradictionSystem`; bridge inherits unchanged. | ✓ PASS. |
| II.7 Edges vs Hyperedges | XGI hyperedges (community memberships) read via existing API; bridge doesn't introduce new hyperedge surface. | ✓ PASS. |
| III.5 Empirical vs Strategic | Real-data seeding (FR-002) IS the empirical anchor; engine systems impose strategic interventions on top. | ✓ PASS. |
| VI Scope Control | Default scope IS material-base-anchored (Michigan statewide, IV.1 boundary); `--ticks` flag remains available for operator-requested overruns at degraded fidelity. | ✓ PASS. |
| VIII Anti-Patterns | No new pairwise-edge-as-community, no scalar solidarity, no determinism-from-conditions. | ✓ PASS — none introduced. |

### Gate decision

**PROCEED to Phase 0 research.** One flagged concern (II.11 subsystem
ownership) is fully covered by the existing spec-064 view-of-records
discipline — every new per-tick table will be exposed only via the
updated `view_runtime_trace_emission`, with explicit ownership labels
documented in §SubsystemTables of the data model. Tracked in
Complexity Tracking below.

### Post-Phase-1 re-check (2026-05-15)

After writing `research.md`, `data-model.md`, all four contract
files, and `quickstart.md`:

- **III.7 Determinism Hash**: Reinforced by R4's append-only
  REVOKE on the three new subsystem tables + the
  `engine_systems_invoked` field added to `manifest.json`'s
  `deterministic_inputs`. Two runs with identical `input_hash`
  cannot diverge silently — system order is now part of the hash.
- **II.11 Subsystem Table Ownership**: Each of migrations 0020-0022
  declares an explicit `owner_subsystem` in its `COMMENT ON TABLE`
  and in `contracts/subsystem_state_tables.yaml`. The trace view
  (migration 0023) is the only declared read path. ✓ PASS.
- **III.4 Data Catalog**: All SQLite tables listed in
  `contracts/hex_hydrator_input.yaml` already appear in
  `.specify/memory/data-catalog.yaml`. No new sources. ✓ PASS.
- **IV / IV.1 / IV.2**: Canonical scope = Michigan-canada (83
  counties + Canada boundary). The 2010-2020 window is the
  Constitution IV test case (Michigan Statewide 2010-2025) with the
  upper bound capped to 2020 by the LODES + BLS unemployment data
  windows. Tri-county remains a valid override scope. ✓ PASS.
- **III.8 Aleksandrov Test**: Every formula in R7's per-column
  source matrix names the material process it represents (QCEW
  wages = v, BEA I/O fraction × GDP = c, etc.). ✓ PASS.

No new gate violations surface in the design. Proceed to
`/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/065-engine-bridging/
├── plan.md              # This file
├── research.md          # Phase 0 — research items + decisions
├── data-model.md        # Phase 1 — new subsystem tables, view extension, bridge models
├── quickstart.md        # Phase 1 — operator + LLM-agent walkthrough at engine-bridged fidelity
├── contracts/
│   ├── trace_csv_schema.yaml      # MODIFIED — column dictionary unchanged in shape; semantics tightened
│   ├── summary_json_schema.yaml   # MODIFIED — adds `events` array; tightens conservation_audit semantics
│   ├── manifest_json_schema.yaml  # MODIFIED — adds `engine_systems_invoked` reproducibility field
│   ├── cli_contract.yaml          # MODIFIED — adds --strict and --endgame-detector flags
│   ├── hex_hydrator_input.yaml    # NEW — declares the SQLite tables the hydrator reads per FR-002a
│   ├── subsystem_state_tables.yaml # NEW — schemas for new per-tick subsystem state tables
│   └── engine_bridge_protocol.yaml # NEW — declares the WorldState ↔ Postgres bridge protocol
├── checklists/
│   └── requirements.md  # Spec quality checklist (already exists)
└── tasks.md             # Phase 2 output — NOT created by /speckit.plan
```

### Source Code (repository root)

```text
src/babylon/
├── engine/
│   ├── headless_runner/                    # EXISTING — spec-064 package
│   │   ├── runner.py                       # MODIFIED — removes no-op _carry_forward_tick;
│   │   │                                   #   adds hydrate-run-write tick loop;
│   │   │                                   #   wires ConservationAuditor + BoundaryFlowRegister
│   │   │                                   #   + EndgameDetector + EventBus capture
│   │   ├── argparse_cli.py                 # MODIFIED — adds --strict and --endgame-detector flags
│   │   ├── bridge.py                       # NEW — WorldState↔Postgres bridge protocol
│   │   ├── event_capture.py                # NEW — EventBus subscriber that collects engine events for summary.json
│   │   ├── run_summary.py                  # MODIFIED — adds events[] payload; populates terminal_state
│   │   │                                   #   from real engine math (no more 0-everywhere)
│   │   └── trace_emitter.py                # UNCHANGED
│   ├── simulation_engine.py                # UNCHANGED — engine systems remain in-memory; bridge adapts at boundary
│   ├── systems/                            # UNCHANGED — all 15 systems run in their existing form
│   ├── observer.py                         # MODIFIED (minor) — exposes EndgameDetector entry-point lookup for runner
│   └── event_bus.py                        # UNCHANGED — provides subscription API
├── persistence/
│   ├── hex_hydrator.py                     # MODIFIED — FR-002a upgrade: tick-0 seeds from real SQLite reference tables
│   ├── postgres_runtime.py                 # UNCHANGED — RuntimePersistence implementation
│   ├── envelope.py                         # UNCHANGED — PerTickTransactionEnvelope
│   ├── conservation_audit.py               # UNCHANGED — ConservationAuditor (spec-062 §T068)
│   └── migrations/
│       ├── 0020_dynamic_consciousness_state.sql  # NEW — p_acquiescence, p_revolution, ideology_r/l/f
│       ├── 0021_dynamic_demographics_state.sql   # NEW — population (per-tick from QCEW interpolation)
│       ├── 0022_dynamic_employment_state.sql     # NEW — employment_proxy (per-tick from QCEW + LODES)
│       └── 0023_trace_view_engine_bridged.sql           # NEW — DROP + recreate view_runtime_trace_emission
│                                                        #        with JOINs to new subsystem tables
└── economics/
    └── boundary_flow_register.py            # UNCHANGED — read by the bridge

tools/
├── shared.py                                # MODIFIED — restore final_state passthrough (SC-011)
└── (other tools UNCHANGED — they call shared.run_simulation)

tests/
├── integration/
│   ├── test_engine_bridge.py                # NEW — gated on BABYLON_TEST_PG_DSN; the core e2e per-US scenarios
│   ├── test_hex_hydrator_real_data.py       # NEW — SC-005 (Wayne QCEW), FR-002b (5-sample QCEW match)
│   ├── test_conservation_audit_strict.py    # NEW — --strict triggers exit 1 on critical
│   ├── test_events_capture.py               # NEW — events array shape + ordering (FR-017/FR-018)
│   ├── test_external_node_flows.py          # NEW — boundary_flow_register → summary.external_node_flows
│   ├── test_endgame_detection_round_trip.py # NEW — closes spec-064 T024a + T033 (US4)
│   ├── test_reference_data_window_policy.py # NEW — FR-022 (silent / warn-and-clamp / hard-refuse)
│   └── test_headless_runner.py              # MODIFIED — wallclock budget reassessment per FR-019
└── unit/
    ├── engine/headless_runner/
    │   ├── test_bridge.py                   # NEW — WorldState↔Postgres bridge unit tests
    │   └── test_event_capture.py            # NEW — EventBus capture + deterministic emission ordering
    └── persistence/
        ├── test_trace_view_columns_v2.py    # MODIFIED — adds new columns from migrations 0020-0022
        └── test_hex_hydrator_sources.py     # NEW — asserts hydrator reads from declared SQLite tables only

.mise.toml                                   # MODIFIED — `sim:e2e-michigan` passes `--ticks 520`;
                                             #            `qa:e2e-regression` passes `--strict`
```

**Structure Decision**: Extend the existing
`babylon.engine.headless_runner` package (added in spec-064) with two
new modules — `bridge.py` (the WorldState↔Postgres adapter) and
`event_capture.py` (the EventBus subscriber). The hex hydrator
upgrade lives at its existing path
(`src/babylon/persistence/hex_hydrator.py`) because it is the
canonical tick-0 seeding mechanism per spec-063. Four new Postgres
migrations (0020-0023) add the missing per-tick subsystem tables and
recreate the trace-emission view. No new top-level packages; everything
extends existing surfaces. This keeps the spec-064 artifact contract
intact and limits the radius of change to "where the substance was
missing."

## Complexity Tracking

The Constitution Check flagged ONE item that needs explicit
justification:

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Per-tick subsystem state tables for consciousness, demographics, employment** (II.11 ownership boundary) | The currently-NULL trace columns (`p_acquiescence`, `p_revolution`, `ideology_r/l/f`, `population`, `employment_proxy`) require per-tick persistence to evolve. Each belongs to a distinct subsystem (Consciousness, Demographics-from-Census-interpolation, Employment-from-QCEW). | A single mega-table `dynamic_county_state` (one row per county per tick with every column) would simplify the view but violate II.11: a single owner cannot be named, and a future independent migration of any subsystem becomes impossible without coordinating across all the others. The view (`view_runtime_trace_emission`) is the union/projection layer; separate per-subsystem tables are the storage layer. This IS the II.11-prescribed mechanism. |

No other complexity items.

## Risks & Mitigations

Surfaced now (pre-research) so Phase 0 / Phase 1 can address them:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Per-tick wallclock blows SC-002** at engine-bridged fidelity | HIGH | HIGH | Phase 0 R1: profile MVP `engine.run_tick()` on tri-county at sample tick to establish ceiling. If projected > 600 s for 520-tick Michigan, evaluate per-system parallelization or hex-resolution caching. Defer to a future spec only if budget headroom is irrecoverable. |
| **Hex hydrator's BEA I/O coefficient × output formula for `c`** is novel and not yet validated | MEDIUM | MEDIUM | Phase 0 R2: derive `c` from BEA county GDP × the intermediate-inputs fraction of `fact_bea_io_coefficient`; cross-check against `fact_qcew_annual.total_wages` so `c ≈ k × v` for some plausible k. Document the formula in `contracts/hex_hydrator_input.yaml`. |
| **WorldState hydration round-trip cost** at 83 counties × 520 ticks | MEDIUM | MEDIUM | Phase 0 R3: hydrate WorldState ONCE per session_init, persist deltas per tick, but only re-hydrate the *fields that engine systems mutate* — not the full graph. Reuse the spec-064 `view_runtime_trace_emission` read pattern. |
| **Subsystem table schema drift** between migrations and the trace view | MEDIUM | LOW | The schema-parity test (`test_trace_view_columns_v2.py`) covers this; every new migration adds a row to the test's expected column list. |
| **Hypothesis invariant suite (spec-053..056) doesn't pass under bridged engine** | MEDIUM | HIGH | Run the suite incrementally as each system bridges; if a violation surfaces, it's a real engine bug worth catching before the bridge ships. |
| **Determinism failure due to dict iteration / EventBus subscription order** | LOW | HIGH | FR-018 codifies emission order (Q4); explicit unit test in `test_event_capture.py`. Use `dict` insertion order (Python 3.7+ guarantee) and sorted entity_id traversal. |
| **`sim:e2e-michigan` operators who relied on the 1000-tick default** | LOW | LOW | Document in `quickstart.md` that the default is now 520 ticks (10 years of real data); `--ticks 1000` still works at degraded fidelity for the tail. |
