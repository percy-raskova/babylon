# Data Model: Spec-066 Marx-Coherence Fixes

**Date**: 2026-05-15
**Status**: Phase 1 (post-research)

This document enumerates the entities spec-066 reads, writes, and constrains. **No new persistent entities are introduced** — every entity below already exists in the spec-064/065 codebase. Spec-066 changes the *invariants* that hold over them and (in one case) the *initial state* the bridge constructs.

## 1. CountyMarxPrimitives (existing — invariants tightened)

**Storage**: `dynamic_hex_state` Postgres table (one row per `(session_id, tick, h3_index)`); per-county aggregate emitted via `view_runtime_trace_emission`.

**Fields**:
- `c: float` — constant capital consumed per week (USD/week)
- `v: float` — variable capital paid per week (USD/week)
- `s: float` — surplus value extracted per week (USD/week)
- `k: float` — accumulated capital stock (USD)

**Invariants ADDED by spec-066** (FR-001, FR-020):
- `s ≥ 0` (clamp; emit `severity='alarm'` audit row when raw computation is negative per FR-004)
- `s = max(0, GDP_per_week - v)` — Marx's value-added identity (formula change from `s = max(0, GDP_per_week - v - c)`)
- `v + s = GDP_per_week ± 5%` (FR-020 calibration tolerance)
- Implied state-aggregate `total_s / (total_c + total_v) ∈ [0.05, 0.50]` per Vol III Ch 13 + Shaikh-broad-v relaxation (FR-021, SC-002)
- *(Previously listed: `c + v + s = W ± $1` per FR-019; **dropped per /speckit.analyze U1** — tautological after FR-001 formula fix since `c + v + s = c + GDP/52` by construction.)*

**Magnitudes (Wayne County 2010, post-fix)**:
- `v` ≈ $1.28B/week (after R6 QCEW `industry_id=1` filter)
- `c` ≈ $735M/week (unchanged; INTERMEDIATE_INPUTS_FRACTION=0.5)
- `GDP` ≈ $1.47B/week
- `s` = max(0, 1.47B − 1.28B) ≈ **$190M/week** (was 0)
- `s/v` ≈ 0.15 (rate of exploitation, broad-v)
- `s/(c+v)` ≈ 0.094 (rate of profit, broad-v) — within [0.05, 0.50] ✓

## 2. CountyIdeologyProfile (existing — initial values fixed)

**Storage**: `dynamic_consciousness_state` Postgres table (one row per `(session_id, tick, county_fips)`).

**Fields**:
- `ideology_r: float ∈ [0,1]` — revolutionary axis
- `ideology_l: float ∈ [0,1]` — liberal axis
- `ideology_f: float ∈ [0,1]` — fascism axis
- `p_acquiescence: float ∈ [0,1]` — survival via acquiescence (mutated by SurvivalSystem)
- `p_revolution: float ∈ [0,1]` — survival via revolution (mutated by SurvivalSystem)

**Bridge mapping** (existing per spec-065 R10): the bridge converts in-memory `IdeologicalProfile(class_consciousness, national_identity)` (mutated by `ConsciousnessSystem`) into the persisted ternary `(r, l, f)` via:
- `r = class_consciousness × (1 − national_identity)`
- `f = national_identity × (1 − class_consciousness)`
- `l = max(0, 1 − r − f)`

**Initial values at tick 0** (FR-010, SC-009): every county MUST satisfy `(ideology_r, ideology_l, ideology_f) = (0.05, 0.50, 0.45)` (revolutionary, liberal, fascist axes) within ±1e-9 float tolerance. Per Clarifications Q3 this is an explicit placeholder pending data-driven seeding (future spec).

To produce these (r, l, f) values via the bridge mapping, the factory `IdeologicalProfile` defaults must be solved:
- `cc × (1 − ni) = 0.05` (revolutionary)
- `ni × (1 − cc) = 0.45` (fascist)
- `max(0, 1 − 0.05 − 0.45) = 0.50` ✓ (liberal — remainder)

Solving the two simultaneous equations yields two candidate solutions: `(cc=0.5, ni=0.9)` and `(cc=0.1, ni=0.5)`. The first ("high class consciousness AND high national identity") is theoretically dubious — Marx treats these as antagonistic; co-existing high values would mean the population is simultaneously class-aware AND nationalist, an unstable contradiction. The second `(cc=0.1, ni=0.5)` ("low class consciousness, moderate national identity") matches the empirical 2010 US baseline of un-organized, moderately nationalist labor. **Spec-066 selects `cc=0.1, ni=0.5`.** The factories `create_proletariat()` and `create_bourgeoisie()` accept an `ideology=IdeologicalProfile(class_consciousness=0.1, national_identity=0.5)` keyword argument that the bridge passes uniformly to all 83 × 2 = 166 entities.

**Per-tick mutation invariants** (FR-012, FR-014, SC-005):
- Ternary simplex preserved: `r + l + f = 1.0 ± 1e-9` (renormalize before persist if needed)
- For at least one county across 520 ticks, `|ideology_f(519) − ideology_f(0)| / ideology_f(0) ≥ 0.05` (the un-organized canonical run drifts further on the fascism axis from its initial 0.45 baseline)

## 3. CountyEmploymentMetric (existing — unit fix)

**Storage**: `dynamic_employment_state` Postgres table (one row per `(session_id, tick, county_fips)`).

**Field**:
- `employment_proxy: float ≥ 0` — average employed persons during the year (NOT employment-weeks)

**Formula change** (FR-005): `employment_proxy = SUM(qcew.employment) / 12` (monthly average) NOT `/ 52` (which incorrectly converts a stock to a flow).

**Magnitude invariant** (FR-006, SC-007): state-aggregate `SUM(employment_proxy)` across all 83 Michigan counties at tick 0 ∈ [3.5M, 4.8M] (±15% of BLS QCEW MI 2010 published total ~4.2M).

## 4. CountySubstrateStocks (existing — apportionment fix)

**Storage**: `dynamic_hex_state` (per-hex with county aggregates; FR-008 adjusts only the apportionment formula, not the storage shape).

**Fields**:
- `biocapacity_stock: float ≥ 0` — abstract Hickel/Ricci units, population-weighted (unchanged)
- `energy_stock: float ≥ 0` — population-weighted apportionment of state-level energy production (unchanged)
- `raw_material_stock: float ≥ 0` — area-weighted apportionment of state-level non-fuel mineral production (FIXED)

**Formula change** (FR-008): `raw_material_stock = state_nonfuel_mineral_value × (county_land_area_sqmi / state_land_area_sqmi)`. Source for `county_land_area_sqmi` is the TIGER county geometry table (already loaded per spec-063).

**Distinguishability invariant** (FR-009, SC-008): for ≥50% of Michigan counties at tick 0, `energy_stock != raw_material_stock` (structural distinguishability — they're computed from different formulas).

## 5. TickContext (existing — wiring fixed)

**Construction**: `runner.run()` constructs ONE `ServiceContainer` before the tick loop and reuses it for all 520 calls to `engine.run_tick(graph, services, context)`.

**Required services** (per Phase 0 R2):
- `config: SimulationConfig` — `SimulationConfig()` defaults
- `defines: GameDefines` — `GameDefines.load_default()` with the spec-066 `routing_scale` overlay (FR-027)
- `event_bus: EventBus` — the bridge-owned bus (already wired per spec-065 T071)
- `auditor: ConservationAuditor` — bridge-owned (spec-065 T049)
- `boundary_register: BoundaryFlowRegister` — bridge-owned (spec-065 T055)
- `formulas: FormulaRegistry.default()`
- `metrics: MetricsCollector()` — engine's own (in-memory; per_system_ms read from `engine.per_system_ms` post-tick per spec-065 T074)
- `database: DatabaseConnection(url="sqlite:///:memory:")` — engine doesn't write to it

**Per-tick context**:
- `tick: int` — current tick number (0 to config.ticks − 1)
- `correlation_id: str` — UUID4 per tick (for log tracing per spec-008)
- `persistent_data: dict` — engine-side scratchpad (existing pattern)

## 6. CountyEdgeBootstrap (NEW conceptual — implementation in bridge)

**No new entity type**; this section documents the seeding pattern for the spec-066 EXTRACTIVE edges (FR-025).

**Per-county seeding** at `bridge.hydrate_initial(...)`:
- For each county FIPS in `scope_fips`, the bridge's `_build_per_county_relationships(...)` helper returns:
  - `Relationship(source_id=proletariat_id, target_id=bourgeoisie_id, edge_type=EdgeType.EXPLOITATION, value_flow=0.0, tension=0.1)` — ONE edge

For 83 Michigan counties this seeds 83 EXPLOITATION edges. Per FR-026 NO `EdgeType.SOLIDARITY` edges are seeded.

**Why `tension=0.1` not `0.0`**: ContradictionSystem accumulates tension on each tick proportional to `(s/v − reproduction_threshold)`. A non-zero starting tension gives the system a numerical anchor to drift from; zero is fine but slows initial dynamics.

**Edge attribute injection (post-spec-066, deferred)**: Once spec-066 ships, `EdgeTransitionSystem` may set `edge_mode = EdgeMode.EXTRACTIVE` (or CO_OPTIVE for high-Φ counties) as a graph attribute. Spec-066 does NOT exercise CO_OPTIVE per FR-028.

## Relationships diagram (text)

```
TickContext (per tick) — runner constructs:
ServiceContainer ─owns→
                          ├── auditor          ─writes→ CountyMarxPrimitives.audit rows (via persist_tick envelope)
                          ├── boundary_register ─writes→ external_node_flows
                          ├── event_bus        ─publishes→ EngineEvent (drained to summary.events)
                          └── defines.consciousness.routing_scale (≥0.2 per FR-027)

bridge.hydrate_initial ─seeds→ CountyEdgeBootstrap (1 EXPLOITATION edge per county)
                       ─instantiates→ {proletariat, bourgeoisie} per county with IdeologicalProfile(cc=0.1, ni=0.5)

per tick:
    engine.run_tick(graph, services, context)
        ├── 21 systems mutate `graph` in-place
        │     (notably: ConsciousnessSystem mutates ideology dict via routing_scale)
        ├── auditor.audit_end_of_tick(...) populates audit_log_buffer
        └── per_system_ms accumulates into engine state

bridge.persist_tick(world, tick, hash) ─reads→ world.relationships, world.entities
                                       ─writes→ dynamic_hex_state, dynamic_consciousness_state,
                                                dynamic_demographics_state, dynamic_employment_state,
                                                dynamic_relationship_state, audit_log_rows,
                                                boundary_register_rows
```
