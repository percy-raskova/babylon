# Implementation Plan: Marx-Coherence Fixes

**Branch**: `066-marx-coherence-fixes` | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/066-marx-coherence-fixes/spec.md`

## Summary

Fix five categorical bugs identified by the spec-065 audit-to-standard sweep so that the canonical Michigan-Canada 520-tick run produces output that satisfies Marx's accounting identities (W = c + v + s, GDP = v + s) and the dialectical principle that material conditions drive consciousness:

1. **Bug A (formula)** — Replace `s = max(0, GDP/52 - v - c)` with `s = max(0, GDP/52 - v)` (the value-added identity); calibrate the `c` fraction; document QCEW denormalization handling.
2. **Bug B (units)** — Fix `employment_proxy = SUM(qcew.employment) / 52` (treats stock as flow) → `/ 12` (monthly average).
3. **Bug C (apportionment)** — Wire area-weighted formula for `raw_material_stock`; keep population-weighted for `energy_stock`.
4. **Bug D (initialization)** — Seed every county at tick 0 with `(ideology_r=0.05, ideology_l=0.50, ideology_f=0.45)` via factory parameter; document as placeholder pending data-driven seeding spec.
5. **Bug E (engine wiring)** — Invoke the full 15-system `SimulationEngine.run_tick(world.graph, services, context)` between `bridge.hydrate_initial(...)` and `bridge.persist_tick(...)` on every tick. No graceful degradation.

Delivery is **incremental** per Clarifications Q3: the MVP commit closes US1 + US2 (both P1); US3, US4, US5 follow as separate commits within the same `066-marx-coherence-fixes` branch.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models), NetworkX 3.x (graph), SQLAlchemy 2.x (reference DB ORM), psycopg 3.x + psycopg_pool (Postgres runtime), XGI 0.10 (hypergraph — not new in this spec but referenced via existing community/ subsystem)
**Storage**: PostgreSQL 16+ for runtime state (existing `dynamic_consciousness_state`, `dynamic_relationship_state` etc. from spec-062/065); SQLite for read-only reference data (`marxist-data-3NF.sqlite` for QCEW, BEA, FCC, Census, Hickel/Ricci); no new tables required (migrations 0020-0024 already shipped)
**Testing**: pytest with marker discipline (`unit`, `integration`, `red_phase`); `BABYLON_TEST_PG_DSN` for integration; `BABYLON_SLOW_TESTS=1` gate for the canonical Michigan e2e wallclock test; Hypothesis ^6.149.0 for invariant suite (spec-053/054/055/056)
**Target Platform**: Linux/macOS dev machines + Hetzner production (per Constitution X.5)
**Project Type**: Single-project Python CLI/library (the `babylon` package + `tools/` operator scripts + `tests/` discipline)
**Performance Goals**: ≤ 10 s/tick mean, ≤ 90 min total for 83 counties × 520 ticks (relaxed from spec-065 SC-002 budget per Phase 0 R8 — SQLite per-tick read overhead dominates; spec-069 will optimize). The spec-066 engine integration adds an estimated 200-400ms/tick on top of the spec-065 bridge baseline of ~5.5s/tick.
**Constraints**: Determinism — same seed produces byte-identical trace.csv (spec-064 SC-007 / FR-015 + Constitution III.7); no engine-system exception silencing (Clarifications Q2 + spec edge case); ternary simplex `r + l + f = 1.0 ± 1e-9` invariant (spec-053 / 055)
**Scale/Scope**: 83 Michigan counties + 1 Canada boundary node; 520 weekly ticks (2010–2020); ~166 SocialClass entities; ~84 EXPLOITATION edges (one per county); 7 envelope row-types per tick; ~44K relationship rows over a full run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The Constitution v2.6.1 P0 + load-bearing P1 principles for this feature, evaluated against the spec:

### P0 — Never-Drop Principles

| Principle | Spec Alignment | Status |
|---|---|---|
| **I.19 Dialectic Primitive** | Consciousness IS a dialectic; ConsciousnessSystem operates on the (r, l, f) ternary. The bridge maps `IdeologicalProfile(cc, ni)` → `(r, l, f)` per the existing transition-state mapping. | ✅ PASS — no new dialectic primitives introduced |
| **I.20 Spatial Substrate** | No mutations to the H3 hex grid or county geometry. Spec only adds derived state (consciousness, relationships) at edge resolution. | ✅ PASS |
| **II.9 Morphism Dyadic** | Relationships persisted via migration 0024 are dyadic (`source_node_id, target_node_id, edge_type`). No N-ary morphisms. | ✅ PASS |
| **III.7 Determinism Hash** | Engine.run_tick must remain deterministic given seed; spec FR-022 preserves spec-065's same-seed-byte-identical guarantee. | ✅ PASS |
| **III.8 Aleksandrov Test** | Every formula change traces to material relation: `s = GDP - v` is Marx's value-added identity (Vol I Ch 9); `employment_proxy / 12` is BLS QCEW monthly average; area-weighted `raw_material_stock` traces to "mining follows geology". | ✅ PASS |
| **V Verb Atomicity** | This spec invokes existing engine systems (verbs); does not add new verbs or atomicity violations. | ✅ PASS |

### P1 — Load-Bearing Principles

| Principle | Spec Alignment | Status |
|---|---|---|
| **I.4 George Jackson Bifurcation** | US2 (consciousness evolves) is exactly the bifurcation in action: when wages fall (material crisis), agitation routes to Fascism or Revolution based on SOLIDARITY edges. | ✅ PASS — required by US2 acceptance |
| **I.6 Solidarity as Edge Mode** | SolidaritySystem (one of the 15) operates on edge modes; spec doesn't override this — just invokes the existing system. | ✅ PASS |
| **I.7 Quantitative → Qualitative** | Ideology drift `(r, l, f)` is quantitative (continuous floats); BIFURCATION_THRESHOLD events are qualitative (discrete EventType emissions per FR-016). | ✅ PASS |
| **I.16 Organizations are Agents** | TRANSITION STATE for v2 organization-as-agent. **This spec does NOT introduce Organization entities** — it operates on the existing SocialClass entity surface that the bridge already builds. Organization integration is a future spec. | ⚠️ DEFER (acceptable; consistent with spec-065 scope) |
| **I.17 OODA** | TRANSITION STATE pending Amendment C. **This spec does NOT add OODA logic.** Engine systems that depend on OODA profiles will operate in their current state (default profiles). | ⚠️ DEFER |
| **II.6 State is Data, Engine is Transformation** | The runner constructs `world: WorldState` (frozen Pydantic), invokes `engine.run_tick(graph, services, context)`, then persists. State stays as data; engine is the pure transformation. | ✅ PASS |
| **II.11 Subsystem Table Ownership** | `dynamic_consciousness_state` (migration 0020) owned by ConsciousnessSystem; `dynamic_relationship_state` (migration 0024 from spec-065) owned by Contradiction + Solidarity systems. Cross-subsystem reads via `view_runtime_trace_emission`. No new tables. | ✅ PASS |
| **III.1 No Magic Constants** | The (0.05, 0.50, 0.45) ideology baseline is a magic constant. **JUSTIFY in Complexity Tracking.** | ⚠️ JUSTIFIED — see Complexity Tracking |
| **III.2 Falsifiability Required** | Every FR has a measurable threshold; SC-001 through SC-015 are testable assertions. SC-005 (`≥5%` ideology drift) and SC-006 (Wayne ≠ Keweenaw correlation < 0.95) are the falsifiability gates for "consciousness responds to material conditions." | ✅ PASS |
| **IV Michigan Test Case** | Canonical Michigan-Canada 520-tick run is the load-bearing acceptance test. Tri-county subset preserved (per IV.2) via `test_smoke_tri_county_full_fidelity`. | ✅ PASS |

### Other Constitutional Concerns

- **I.18 Material-Ideological Distinction (TRANSITION STATE)** — The (c, v, s, k) per county is the material basis; the (r, l, f) per county is the ideological dimension. The "gap" Marx names is the difference between class-in-itself (material position) and class-for-itself (consciousness). Bug E's fix wires the engine that makes consciousness respond to material change — exactly preserving the material-ideological distinction. The current bridge mapping (cc, ni) → (r, l, f) is the v2 transition-state implementation; this spec does not break the constraint and does not depend on Amendment D ratification.
- **I.21 Sparrow (TRANSITION STATE)** — Spec doesn't add Repress sub-verbs. ✅
- **VIII.6 Constants Without Data Sources** — The (0.05, 0.50, 0.45) baseline IS a constant without a per-county data source. **JUSTIFY in Complexity Tracking.**

### Constitution Check Verdict: **PASS WITH JUSTIFIED VIOLATIONS**

Two violations require justification (see Complexity Tracking below):
1. III.1 / VIII.6 — magic constant `(0.05, 0.50, 0.45)` ideology baseline.
2. I.16 / I.17 — Organization-as-agent and OODA logic deferred to future specs.

## Project Structure

### Documentation (this feature)

```text
specs/066-marx-coherence-fixes/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── engine_invocation_contract.yaml      # Bug E — runner ↔ engine integration
│   ├── marx_identity_invariants.yaml        # Bug A — accounting identities
│   ├── employment_proxy_contract.yaml       # Bug B — unit fix + magnitude band
│   ├── substrate_apportionment_contract.yaml # Bug C — area vs population weighting
│   └── ideology_baseline_contract.yaml      # Bug D — (0.05, 0.50, 0.45) seeding
├── checklists/
│   └── requirements.md  # Already created by /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This spec modifies existing files in the spec-064/065 codebase. No new top-level directories.

```text
src/babylon/
├── persistence/
│   ├── hex_hydrator.py                  # Bug A formula fix; Bug B /12 fix; Bug C area weighting
│   └── conservation_audit.py            # Bug A FR-004 audit row for s_raw < 0
├── engine/
│   ├── simulation_engine.py             # Already wired (spec-065 T074); no change
│   ├── factories.py                     # Bug D — accept ideology kwarg in create_proletariat / create_bourgeoisie
│   ├── services.py                      # Already extended (spec-065); no change
│   └── headless_runner/
│       ├── runner.py                    # Bug E — construct ServiceContainer, call engine.run_tick(...)
│       └── bridge.py                    # Bug D pass through; WorldState ↔ graph round-trip
├── models/
│   ├── entities/social_class.py         # Bug D — IdeologicalProfile defaults already wire-able via factory
│   └── world_state.py                   # to_graph() / from_graph() already exist; no change expected
├── config/
│   └── defines/                         # GameDefines coefficient overlay for any new tunables
└── (existing 15 engine systems untouched — they already work; spec just invokes them)

tests/
├── integration/
│   ├── test_engine_bridge.py            # Remove xfail on test_tick_over_tick_evolution (T028)
│   ├── test_marx_identities.py          # NEW — SC-003 / SC-004 cross-county invariant suite
│   └── test_consciousness_evolution.py  # NEW — SC-005 / SC-006 ideology drift assertions
├── unit/
│   ├── persistence/test_hex_hydrator_marx.py       # NEW — Bug A formula unit tests
│   ├── persistence/test_employment_proxy_units.py  # NEW — Bug B /12 unit tests
│   ├── persistence/test_substrate_apportionment.py # NEW — Bug C area vs population unit tests
│   ├── engine/test_factories_ideology_seed.py      # NEW — Bug D factory parameter unit tests
│   └── engine/headless_runner/test_runner_engine_invocation.py  # NEW — Bug E ServiceContainer + run_tick wiring

ai-docs/
├── decisions/
│   ├── ADR043_ideology_baseline_placeholder.yaml  # NEW — documents the (0.05, 0.50, 0.45) decision
│   └── ADR044_engine_integration.yaml             # NEW — documents the spec-066 engine wiring approach
└── state.yaml                                       # Bumped to v2.9.0; spec-066 status block

specs/065-engine-bridging/
└── (no changes — spec-065 stays as the historical record)
```

**Structure Decision**: Modify-in-place against the spec-064/065 codebase. No new packages or top-level directories. The bug fixes are surgical edits to existing files (`hex_hydrator.py`, `runner.py`, `factories.py`); the engine wiring (Bug E) is the single largest change but reuses the spec-065 ServiceContainer scaffolding.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **III.1 / VIII.6 — Magic constant `(ideology_r=0.05, ideology_l=0.50, ideology_f=0.45)` baseline** | The user (per Clarifications Q3 of `/speckit.specify`) explicitly chose to defer principled per-county data-driven ideology seeding to a future spec. Designing the seeding scheme requires its own planning work (which proxies to use, how to combine them, calibration against survey/election data). Without a documented placeholder, the simulation cannot run at all (the bridge needs *some* values to seed each county). | Per-county data-driven seeding from union density, industrial composition, ACS demographics, election shares is the principled alternative — explicitly deferred per Clarifications Q3 to a future spec to be authored when proxy selection has been thought through. The placeholder is documented in ADR043 with a "REPLACE WHEN" condition stating the future spec must replace it. |
| **I.16 — Organizations as Agents (TRANSITION STATE)** | This spec operates on the existing SocialClass entity surface (proletariat / bourgeoisie per county) that spec-065 already shipped. Introducing Organization entities at this layer would expand scope beyond bug-fix into a parallel architecture migration. | Organization-as-agent is in transition pending Amendment C (OODA placement). A future spec is required to introduce Organization entities through the bridge. Until then, SocialClass + Territory are the substrate the engine operates on, consistent with spec-065. |
| **I.17 — OODA (TRANSITION STATE)** | Adding OODA profiles requires Amendment C ratification (deferred to v2.8.0). Spec-066 cannot block on a constitutional amendment cycle. | The 15 engine systems already include OODASystem; if it requires OODA profiles on entities it lacks, that system can be skipped in this spec's invocation order — but per Clarifications Q2 (no graceful degradation), if OODASystem fails the run fails. **Mitigation:** confirmed during research.md whether OODASystem can run cleanly without explicit Organization entities; if not, this spec must enable a minimal `default_ooda_profile` on SocialClass to unblock. |

These three violations are individually justified and collectively bounded — each has a documented "REPLACE WHEN" or "MITIGATION" clause that specifies the path back to constitutional compliance.

## Phase 0 — Outline & Research

Research tasks dispatched in parallel to resolve technical-context unknowns and integration patterns. Each task returns a Decision / Rationale / Alternatives section consolidated into `research.md`.

**Research questions** (each becomes one section in research.md):

1. **R1: WorldState ↔ NetworkX round-trip semantics** — How does `WorldState.to_graph()` produce a graph the 15 engine systems can mutate, and how does `WorldState.from_graph()` reconstitute the WorldState after mutations? Per CLAUDE.md "Graph Round-Trip Can Lose Mutations" gotcha, what fields are excluded by `from_graph()` in the current implementation? Does the bridge need a custom round-trip path?

2. **R2: ServiceContainer construction in the bridged runner** — Spec-065 added auditor/boundary_register/event_bus fields to ServiceContainer but the bridged runner doesn't yet construct one. What's the minimum-viable ServiceContainer construction sequence in `runner.run()`? What `metrics`, `formulas`, `database`, `config` does the engine need? Does it work with `DatabaseConnection(url="sqlite:///:memory:")` since the runner uses Postgres for state?

3. **R3: 15-system invocation order vs declared order** — Does `simulation_engine.py` enforce the order the spec declares (Vitality → Territory → Production → Solidarity → ImperialRent → Decomposition → ControlRatio → Metabolism → Survival → Struggle → Consciousness → Contradiction → ContradictionField → FieldDerivative → EdgeTransition)? If different in code, which is canonical? Do any systems require entities the bridge doesn't yet provide (Organizations, Communities, Institutions)?

4. **R4: ConsciousnessSystem dependencies** — What inputs from the graph does ConsciousnessSystem.step() need to drift `IdeologicalProfile(class_consciousness, national_identity)`? Does it require SOLIDARITY edges (which spec-066 must seed at tick 0) to make consciousness drift heterogeneous? What `defines.consciousness.*` coefficients are referenced?

5. **R5: WorldState.relationships seeding** — Currently `WorldState.relationships=[]` after `bridge.hydrate_initial`. Which engine system creates the initial EXPLOITATION + SOLIDARITY edges between proletariat and bourgeoisie per county? If no system creates them, the bridge must seed them at tick 0 — what's the canonical seeding pattern?

6. **R6: QCEW normalization approach** — Re-ingestion (multi-week data work) vs SQL filter at hex hydration time (small) vs calibration factor (cheapest). The spec assumption section says "implementer chooses; both produce same observable trace output" but a concrete decision is needed for the task plan. Pick the smallest path that satisfies FR-002 (`v` within ±50% of BLS-published).

7. **R7: BEA national industry I-O ingestion vs calibrated single constant** — Same trade-off as R6 for FR-003. Smallest path that satisfies the implied-c/v invariant `[0.5, 5.0]` for state aggregate.

8. **R8: Empirical engine-system per-tick cost** — Profile each of the 15 systems' single-step cost on the canonical 84-entity graph. Spec-065 measured ~5.47s/tick without engine; spec-066 budget is ≤5s/tick total (implies engine adds zero overhead, which is unrealistic). Decision: is the budget achievable, or does it need further relaxation? If unachievable, propose the realistic ceiling AND identify the per-system optimization targets.

**Output**: `specs/066-marx-coherence-fixes/research.md` with R1–R8 each in Decision/Rationale/Alternatives format.

## Phase 1 — Design & Contracts

**Prerequisites**: research.md complete (8 R-section decisions made).

### 1. Data Model (`data-model.md`)

Document the entities the spec operates on. Most are already defined in the spec-064/065 codebase; this section documents which fields change and which invariants this spec adds.

Entities documented (all existing — no new entities):

- **`CountyMarxPrimitives`** (per-county tuple stored in `dynamic_hex_state` and emitted via `view_runtime_trace_emission`)
  - Fields: `c`, `v`, `s`, `k` (USD/week or USD-stock per spec-064 contract)
  - Invariants ADDED by spec-066:
    - `v + s = GDP_per_week ± 5%` (Marx value-added identity, per FR-020)
    - `c + v + s = W ± $1` (Marx gross-output identity, per FR-019)
    - `s ≥ 0` (clamp; emit alarm row when raw is negative per FR-004)
- **`CountyIdeologyProfile`** (per-county tuple in `dynamic_consciousness_state`)
  - Fields: `ideology_r`, `ideology_l`, `ideology_f` (each in [0, 1])
  - Initial values (spec-066 placeholder): `(0.05, 0.50, 0.45)` for every county
  - Invariants: ternary simplex `r + l + f = 1.0 ± 1e-9`
- **`CountyEmploymentMetric`** (per-county scalar in `dynamic_employment_state`)
  - Fields: `employment_proxy` (average employed persons during the year)
  - Unit FIX: divide raw QCEW employment by 12 (months), not 52 (weeks)
- **`CountySubstrateStocks`** (per-county tuple in `dynamic_hex_state`)
  - Fields: `biocapacity_stock`, `energy_stock`, `raw_material_stock`
  - Apportionment: energy = state × pop_share; raw_material = state × area_share
- **`TickContext`** (per `src/babylon/engine/context.py:19`; per-tick context passed to engine.run_tick) — the spec previously referred to this as `EngineRunContext`; corrected per /speckit.analyze U2
  - Fields: `tick`, `correlation_id`, `services`, `defines`
  - Construction: runner builds `ServiceContainer` with bridge-owned components (auditor, boundary_register, event_bus, formulas, defines, metrics, database, config)

### 2. Contracts (`contracts/`)

Five YAML contracts, one per bug, defining the observable behavior:

- `contracts/marx_identity_invariants.yaml` — Bug A: per-tick assertions on c/v/s/k satisfying Marx identities
- `contracts/employment_proxy_contract.yaml` — Bug B: state-aggregate employment within ±15% of BLS QCEW Michigan 2010
- `contracts/substrate_apportionment_contract.yaml` — Bug C: energy_stock != raw_material_stock for ≥50% of counties
- `contracts/ideology_baseline_contract.yaml` — Bug D: tick-0 (0.05, 0.50, 0.45) for every county; ternary simplex preserved
- `contracts/engine_invocation_contract.yaml` — Bug E: 15 systems invoked per tick in declared order; per_system_ms populated; specific event types fired during a 520-tick run

### 3. Quickstart (`quickstart.md`)

A 4-section operator/researcher walkthrough:

- **Section 1**: Validating the Marx identities post-run (one Python snippet that loads `summary.json` + `trace.csv` and asserts SC-003 + SC-004 across all 43,160+ rows)
- **Section 2**: Inspecting consciousness evolution (Python snippet for SC-005 + SC-006 — Wayne vs Keweenaw correlation)
- **Section 3**: Comparing the spec-065 baseline vs the spec-066 baseline (`tests/baselines/michigan-e2e.json` diff, headlining the s=0 → s>0 transition)
- **Section 4**: Running the canonical pipeline (`mise run sim:e2e-michigan` end-to-end with the new wallclock expectations)

### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to update the project-level `CLAUDE.md` with new technology references introduced by this spec. Spec-066 introduces NO new dependencies (per Technical Context); the agent context update will note the spec-066 work in the "Recent Changes" section and reference ADR043 + ADR044.

**Output**:
- `specs/066-marx-coherence-fixes/data-model.md`
- `specs/066-marx-coherence-fixes/contracts/{5 yaml files}`
- `specs/066-marx-coherence-fixes/quickstart.md`
- Updated `CLAUDE.md` (project-level)

## Phase 2 — Tasks (`/speckit.tasks` only; not generated by `/speckit.plan`)

`/speckit.tasks` will generate `tasks.md` with phased delivery per the spec's incremental MVP plan:

- **Phase A — Setup + Foundational**: Test infrastructure scaffolding, CI gate hooks
- **Phase B — Bug A (US1)**: Formula fix + QCEW + I-O calibration; SC-001/SC-002/SC-004 closure (SC-003 dropped per /speckit.analyze U1 — tautological after FR-001 formula fix)
- **Phase C — Bug E (US2)**: Engine wiring; SC-005/SC-006/SC-010/SC-012/SC-013 closure (THIS IS THE MVP — Phase B + Phase C together)
- **Phase D — Bug D (US3)**: Ideology factory parameter + ADR043; SC-009/SC-014 closure
- **Phase E — Bug B (US4)**: Employment unit fix; SC-007 closure
- **Phase F — Bug C (US5)**: Substrate apportionment fix; SC-008 closure
- **Phase G — Polish**: Baseline regen, ADR044, state.yaml bump, quickstart walkthrough, CI gate close
