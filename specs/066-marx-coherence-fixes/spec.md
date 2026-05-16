# Feature Specification: Marx-Coherence Fixes — Make the Trace Economically and Politically Real

**Feature Branch**: `066-marx-coherence-fixes`
**Created**: 2026-05-15
**Status**: Draft
**Input**: User description: "I want a formal, rigorous specification for all of the bugs we have identified here in the past few iterations of this chat, based on your findings from the data investigation as well as what I pointed out about Consciousness. this specification should include the consciousness fixing. for the seeding values of ideology, that'll have to be thought out in detail but for now you can just assume a uniform baseline of 50% liberal, 45% fascist, 5% revolutionary uniformly. i'll have to think through a principled way to do seed values based on data though. but for now? that works as long as we document it explicitly"

**Notation reminder (per /speckit.analyze C1 fix)**: per the ternary simplex axis labels, `ideology_r` = revolutionary, `ideology_l` = liberal, `ideology_f` = fascist. The user's "50% liberal, 45% fascist, 5% revolutionary" therefore maps to `(ideology_r=0.05, ideology_l=0.50, ideology_f=0.45)`.

## Background

Spec-065 ("Engine-Bridging") shipped a real-data-driven persistence pipeline: SQLite → hex hydrator → bridge → 7 Postgres subsystem tables → trace view → CSV. The first canonical Michigan-Canada 520-tick run completed cleanly on 2026-05-15 (artifact dir `reports/sim-runs/2026-05-15T23-03-39Z/`, 43,160 rows, all 22 trace columns populated, baseline refreshed atomically).

A rigorous post-run audit against (a) Marx's canonical accounting identities from Capital Vol I-III on marxists.org, (b) Shaikh's modern US empirical magnitudes, and (c) the project's own MLM-TW principles in `CLAUDE.md` identified **five categorical bugs** that make the simulation's output economically incoherent and politically static. By Marx's own theory the simulation currently shows zero surplus value extracted in any week of a 10-year Michigan run, identical class consciousness in Wayne County (Detroit) and Keweenaw County (rural Upper Peninsula), and consciousness that never evolves across 520 weekly ticks despite material conditions changing.

This specification fixes all five bugs in one coherent sweep so that the next canonical Michigan run produces output that satisfies Marx's accounting identities (W = c + v + s), Marx's value-added identity (GDP = v + s), the dialectical principle that material conditions drive consciousness, and the project's stated objective ("model class struggle as deterministic output of material conditions").

## Clarifications

### Session 2026-05-15

- Q: SC-002 rate of profit band — which `v` definition (Shaikh-narrow productive labor vs BEA-broad total compensation)? → A: Option B — relax the band to `[0.05, 0.50]` to accommodate BEA-broad `v` (QCEW gives all compensation, not productive-labor only). Productive-labor classification is out of scope.
- Q: Engine integration — full 15 systems or minimum viable subset? → A: Option A — full 15 systems in declared order. No graceful degradation; any system failure fails the tick and the spec.
- Q: MVP shipping unit — incremental P1-first or atomic all-five? → A: Option A — incremental. P1 (US1 + US2) lands first as MVP on the `066-marx-coherence-fixes` branch; US3, US4, US5 follow as separate commits/PRs within the same branch (not separate specs).
- Phase 0 research findings (research.md): the canonical engine has **21 systems**, not 15; `WorldState.relationships` is empty in the spec-065 bridge and NO engine system creates EXPLOITATION/SOLIDARITY edges; `ConsciousnessSystem` default coefficients are too slow to clear SC-005 (`≥5%` drift) — coefficient bumps required (`routing_scale 0.1 → 0.2` minimum); SQLite per-tick reads dominate the bridge wallclock cost so SC-011 relaxes from ≤45 min to ≤90 min and an optimization follow-up (spec-069) is documented. See research.md for full Decision/Rationale/Alternatives per question.
- Q: Where should EXPLOITATION/SOLIDARITY edge creation live (engine system, scenario loader, bridge, verb-driven)? → A: Option A (data-driven scenario loader, EXTRACTIVE only). The bridge's hydrate_initial creates ONE `EdgeType.EXPLOITATION` Relationship per county (proletariat → bourgeoisie within county) — the base EXTRACTIVE relation that ImperialRentSystem iterates to extract Φ. **NO SOLIDARITY edges are created at any scope** per Constitution III.5 ("solidaristic edges, organizing, consciousness-raising" are strategic intervention NOT from data). The canonical headless run therefore models an UN-ORGANIZED population: ConsciousnessSystem routes ALL agitation to fascism (`national_identity` axis rises, `class_consciousness` axis stays low) — which is theoretically correct per Marx + the project's MLM-TW frame for US 2010-2020. CO_OPTIVE edge mode handling (for labor-aristocracy / imperial-subsidy modeling) is deferred to a future spec. SOLIDARITY-edge creation via player verbs (Mobilize, Organize, Educate per Constitution V) is also a future spec — the headless runner has no player.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Surplus value is non-zero and Marxist-coherent (Priority: P1)

A researcher inspecting `summary.json.terminal_state` for any Michigan county should see a non-zero `total_s` (state aggregate surplus value, in USD per week) that satisfies Marx's accounting identity W = c + v + s with W ≥ 0 across every persisted tick. The implied rate of profit p' = s / (c + v) should land in the empirical band 0.20 ≤ p' ≤ 0.50 (consistent with Vol III Ch 13's illustrative table and Shaikh's modern US estimates).

**Why this priority**: Without non-zero `s`, the simulation is mathematically degenerate. Every downstream Marxist primitive (rate of profit, rate of exploitation, organic composition, imperial rent Φ) cascades to zero or undefined. The whole TVT (Theory of Value Transfer) substrate that spec-057 / spec-021 / spec-024 layered over spec-065 is dead-letter while `s = 0` everywhere. This is the load-bearing invariant for the entire economic-correctness story.

**Independent Test**: Run `mise run sim:e2e-michigan` for a 5-tick tri-county or full Michigan run; query `summary.json.terminal_state.total_s`; assert `total_s > 0`. Additionally assert `0.05 ≤ p' ≤ 0.50` for at least one large county (Wayne, Macomb, Oakland) and at least one small county (Keweenaw, Ontonagon). The band reflects QCEW-broad `v` (all compensation of employees) rather than Shaikh-narrow productive-labor `v`.

**Acceptance Scenarios**:

1. **Given** a fresh Michigan-Canada 520-tick run, **When** the operator inspects `summary.json.terminal_state`, **Then** `total_s > 0` and the implied state rate of profit `total_s / (total_c + total_v)` falls in [0.05, 0.50].
2. **Given** a 5-tick tri-county run, **When** the operator inspects per-county snapshots, **Then** every county with `v > 0` shows `s > 0`, `profit_rate > 0`, and `exploitation_rate > 0`.
3. **Given** any persisted tick, **When** the operator computes `c + v + s` per county, **Then** the result equals the implied gross output W reported by the hex hydrator (within ±$1).
4. **Given** any persisted tick, **When** the operator computes `v + s` per county, **Then** the result equals BEA county GDP / 52 within ±5% (the GDP = value-added identity).

---

### User Story 2 - Consciousness evolves with material conditions (Priority: P1)

A researcher inspecting `trace.csv` for any single county across 520 ticks should see `ideology_r`, `ideology_l`, and `ideology_f` change over time as material conditions (wages, employment, repression, solidarity edges) change. Wayne County undergoing the 2008-2010 auto industry collapse should drift differently than Oakland County's suburban professional base. The MLM-TW bifurcation principle (when wages fall, agitation routes to either Fascism or Revolution based on SOLIDARITY edge presence) should be visible in the trace.

**Why this priority**: This is the load-bearing invariant for the project's stated mantra "Graph + Math = History" and the Marxist principle "social being determines social consciousness". A consciousness simulation where consciousness never evolves with being is structurally non-Marxist; it inverts Marx's relation between base and superstructure. P1 alongside US1 because the project's identity depends on it.

**Independent Test**: Run a full 520-tick Michigan-Canada simulation; for any single county, assert that at least one of `{ideology_r, ideology_l, ideology_f}` changes by ≥5% relative magnitude between tick 0 and tick 519. Additionally assert that two structurally different counties (e.g., Wayne vs Keweenaw) show distinct trajectories — they should NOT have identical (r, l, f) at every tick. **Important per Clarifications Q4**: in the un-organized canonical run (no SOLIDARITY edges, no player verbs), drift will occur primarily on the `ideology_f` (fascism / national_identity) axis as ConsciousnessSystem routes agitation to fascism in the absence of solidarity. Drift on `ideology_r` (revolutionary axis) is NOT expected to clear the ≥5% threshold — that requires SOLIDARITY edges to exist, which is deferred to a future spec.

**Acceptance Scenarios**:

1. **Given** a 520-tick Michigan run, **When** the operator inspects `trace.csv` filtered to entity_id="26163" (Wayne) and the `ideology_f` column, **Then** the column has at least 10 distinct values across the 520 ticks AND `|ideology_f(519) - ideology_f(0)| / ideology_f(0) ≥ 0.05`.
2. **Given** the same run, **When** the operator compares the `ideology_f` trajectories of two structurally different counties (Wayne high-Φ vs Keweenaw low-Φ), **Then** the trajectories diverge — Pearson correlation between Wayne's `ideology_f` time-series and Keweenaw's is < 0.95. The divergence emerges from differential EXTRACTIVE edge weights (Wayne's higher imperial rent extraction → faster agitation generation → faster routing to fascism).
3. **Given** a county where wages fall by ≥10% relative within any 52-tick window during the run (real QCEW data, e.g., Wayne 2008-2010 auto collapse), **When** the operator inspects that county's `summary.events`, **Then** at least one `BIFURCATION_THRESHOLD` or `CONSCIOUSNESS_SHIFT` event fires. (`SOLIDARITY_AWAKENING` events will NOT fire in the un-organized canonical run; they require SOLIDARITY edges to exist.)

---

### User Story 3 - Initial ideology is documented + uniform across counties (Priority: P2)

A researcher querying `trace.csv` at tick 0 should see every Michigan county initialized to **(ideology_r = 0.05, ideology_l = 0.50, ideology_f = 0.45)** — 5% revolutionary, 50% liberal, 45% fascist (reactionary) — as an explicit placeholder baseline. The `quickstart.md` and an ADR must document this as a deliberate non-data-driven initialization pending a future spec to design a principled per-county seeding from material indicators (union density, industrial composition, Census ACS demographics, election results, etc.).

**Why this priority**: Per-county data-driven ideology seeding requires its own design work (which proxies to use, how to combine them, calibration against survey data). The user explicitly chose to defer that work. But without an explicit, documented placeholder, future readers will mistake the uniform initialization for either a bug or a hidden assumption. P2 because correctness-of-initial-state matters less than evolution (US2) for the simulation's first-cut behavioral validity, but documentation matters for the project's intellectual honesty.

**Independent Test**: Run any simulation; query `trace.csv` at tick 0 for any county; assert `ideology_r = 0.05 ± 1e-9`, `ideology_l = 0.50 ± 1e-9`, `ideology_f = 0.45 ± 1e-9`, and `r + l + f = 1.0 ± 1e-9` (ternary simplex preserved).

**Acceptance Scenarios**:

1. **Given** a fresh Michigan-Canada simulation, **When** the operator queries `trace.csv` filtered to tick=0, **Then** every one of the 83 counties has `ideology_r=0.05, ideology_l=0.50, ideology_f=0.45` (within ±1e-9 float tolerance).
2. **Given** a reader new to the project, **When** they read `quickstart.md` and the spec-066 ADR, **Then** they find an explicit statement that the (0.05, 0.50, 0.45) baseline is a placeholder and that a principled per-county seeding scheme is deferred to a future spec.

---

### User Story 4 - Employment magnitudes match BLS QCEW reality (Priority: P2)

A researcher inspecting `total_population` and `total_employment_proxy` aggregates for Michigan tick 0 should see employment numbers within ±15% of BLS QCEW state-level published totals (~4.2M employed in Michigan 2010). Today the simulation reports ~552K — an 8× undercount caused by treating QCEW monthly average employment (a stock) as if it were an annualized flow and dividing by 52.

**Why this priority**: The employment number propagates into `p_acquiescence` (survival via wages), `p_revolution` (organization / repression), and the bifurcation thresholds in `ConsciousnessSystem`. An 8× undercount means survival probabilities, repression ratios, and organization coefficients all sample from a wrong-by-an-order-of-magnitude distribution. P2 because the impact is downstream of US1/US2 but the fix is small and self-contained.

**Independent Test**: Run any simulation; sum `employment_proxy` across all 83 Michigan counties at tick 0; assert the sum lies in [3.5M, 4.8M] (a ±15% band around the BLS QCEW MI 2010 published total of ~4.2M).

**Acceptance Scenarios**:

1. **Given** a Michigan-Canada simulation at tick 0, **When** the operator sums `employment_proxy` across all 83 counties, **Then** the sum equals the BLS QCEW Michigan 2010 published employment total (~4.2M) within ±15%.
2. **Given** any single county at any tick, **When** the operator divides `employment_proxy` by `population`, **Then** the labor-force participation ratio falls in [0.30, 0.65] (Bureau of Labor Statistics empirical range for US counties).

---

### User Story 5 - Substrate stocks reflect real geological vs demographic apportionment (Priority: P3)

A researcher inspecting `energy_stock` and `raw_material_stock` for two structurally different counties (e.g., a densely populated metro like Wayne vs a geologically rich rural county like Marquette in the Upper Peninsula) should see distinct values reflecting that energy reserves follow population (where consumption + storage happens) while raw material stocks follow geological / land area (where mining happens). Today both columns are byte-identical for every county.

**Why this priority**: Substrate stock heterogeneity matters for the MetabolismSystem's depletion dynamics and for territorial conflict modeling (rural-extractive vs urban-consumptive county dialectic). P3 because the magnitudes are abstract units and the metabolism system isn't yet exercising these in the spec-065 first cut, but the fix is small and the bug is architecturally honest.

**Independent Test**: Run any simulation; for tick 0, assert `energy_stock != raw_material_stock` for at least 50% of counties. Additionally verify that two large counties with similar populations but different land areas (e.g., Wayne 614 sq mi vs Marquette 1,808 sq mi) show distinct `raw_material_stock` values.

**Acceptance Scenarios**:

1. **Given** a Michigan-Canada simulation at tick 0, **When** the operator queries `trace.csv` for any county, **Then** `energy_stock` and `raw_material_stock` are computed from distinct apportionment formulas (population-weighted for energy, land-area-weighted for raw materials).
2. **Given** two counties with similar population but different land area, **When** the operator compares their `raw_material_stock` values, **Then** the values differ in proportion to the area ratio (within ±10%).

---

### Edge Cases

- **Negative residual surplus**: If the corrected `s` formula still produces a negative residual for a county-year (e.g., a county where `v` from QCEW exceeds GDP from BEA due to data-source mismatch like commuter wages reported in the work county vs GDP reported in the residence county), the simulation MUST emit a `severity='alarm'` audit row identifying the county and year, AND clamp `s = 0` for that county-tick. The audit row is a calibration signal, not a hard error.
- **Counties missing QCEW or BEA data for a given year**: When real data is missing for a (county, year) pair within the canonical 2010-2020 window, the FR-022 preflight (already shipped in spec-065) refuses the run with exit code 3. This spec preserves that behavior.
- **Engine-system exception during `ConsciousnessSystem.step()`**: A system raising an exception MUST NOT corrupt the per-tick envelope. The bridge MUST roll back the in-flight envelope and either retry the tick or fail the run with exit code 1 — never commit partial subsystem rows.
- **Ideology drift outside the simplex**: Float drift during ConsciousnessSystem evolution may push (r + l + f) slightly off 1.0. The bridge's persist-tick path MUST renormalize to the simplex (r' = r/sum, etc.) before writing rows, so the DB CHECK constraint `r + l + f ∈ [1 - ε, 1 + ε]` (ε = 1e-9) holds.
- **County with zero population at tick 0**: A county with population=0 contributes nothing to aggregates but MUST still emit a row (with all-zero economic fields) so the trace.csv contract (one row per (county, tick)) holds.

## Requirements *(mandatory)*

### Functional Requirements

#### Bug A — Surplus value formula correctness

- **FR-001**: System MUST compute weekly surplus value per county using the value-added identity `s_per_week = max(0, GDP_per_week - v_per_week)` rather than the current `s_per_week = max(0, GDP_per_week - v_per_week - c_per_week)`. The existing formula is a category error: GDP in BEA accounting is value-added (= v + s in Marx terms), so subtracting `c` from GDP double-counts the constant-capital pass-through.
- **FR-002**: System MUST normalize the QCEW total_wages_usd ingestion so that `v_per_week` for any (county, year) lies within ±50% of the BLS-published establishment-survey wage total for that county-year (after accounting for ownership filters). The current SQLite snapshot inflates `v` by ~5× due to denormalization across (industry × ownership × establishment) rows.
- **FR-003**: System MUST replace the hardcoded `INTERMEDIATE_INPUTS_FRACTION = 0.5` constant with a per-industry coefficient sourced from BEA national industry input-output tables, or — if the tables are not yet ingested — document the constant as a calibrated national-average proxy whose value MUST satisfy "implied state-level c/v organic composition for Michigan 2010 falls in [0.5, 5.0]" (the Shaikh-tractable empirical band).
- **FR-004**: System MUST emit a `severity='alarm'` conservation_audit_log row for any county-tick where `s_raw < 0` (i.e., the residual surplus would be negative before clamping), naming the county FIPS and the year, so downstream calibration tools can identify data-source mismatches.

#### Bug B — Employment unit fix

- **FR-005**: System MUST compute `employment_proxy` for each county as `SUM(qcew.employment) / 12` (monthly average) NOT `SUM(qcew.employment) / 52` (which treats a monthly-stock as a weekly-flow). The output unit is "average employed persons during the year", not "employment-weeks per week".
- **FR-006**: System MUST satisfy "the sum of `employment_proxy` across all Michigan counties at tick 0 lies in [3.5M, 4.8M]" — a ±15% band around the BLS QCEW MI 2010 state total.

#### Bug C — Substrate stock apportionment

- **FR-007**: System MUST compute `energy_stock` per county as `state_energy_value × (county_population / state_population)`, with the state value sourced from EIA state-level energy production data or — if not yet ingested — from a documented GameDefines fallback, and the county/state population sourced from the existing Census loader.
- **FR-008**: System MUST compute `raw_material_stock` per county as `state_nonfuel_mineral_value × (county_land_area_sqmi / state_land_area_sqmi)`, with `county_land_area_sqmi` sourced from the TIGER county geometry table (already loaded per spec-063).
- **FR-009**: System MUST satisfy "for at least 50% of Michigan counties at tick 0, `energy_stock != raw_material_stock`" — a structural distinguishability check.

#### Bug D — Per-county ideology initialization

- **FR-010**: System MUST initialize every county's proletariat and bourgeoisie SocialClass entities so that the bridge's ternary mapping produces (`ideology_r = 0.05`, `ideology_l = 0.50`, `ideology_f = 0.45`) at tick 0. The baseline is uniform across all 83 Michigan counties.
- **FR-011**: System MUST document the (0.05, 0.50, 0.45) baseline in `quickstart.md` AND in a new ADR (e.g., ADR043) as an explicit placeholder pending a future spec to design principled per-county seeding from material indicators (union density, industrial composition, Census ACS demographics, election results, etc.).
- **FR-012**: System MUST satisfy the ternary simplex invariant `r + l + f = 1.0 ± 1e-9` for every county at tick 0.

#### Bug E — Consciousness evolution wiring (engine integration scope)

- **FR-013**: System MUST invoke the full `SimulationEngine.run_tick(world.graph, services, context)` between `bridge.hydrate_initial(...)` and `bridge.persist_tick(...)` on every tick, passing the runner-owned ServiceContainer (with EventBus, ConservationAuditor, BoundaryFlowRegister, FormulaRegistry, GameDefines, MetricsCollector all wired). The **21 systems** (corrected from "15" per Phase 0 research R3) run in the canonical order defined by `simulation_engine.py:_DEFAULT_SYSTEMS`: Vitality → Territory → Substrate → Production → TickDynamics → ReserveArmy → Community → Lifecycle → Solidarity → ImperialRent → DispossessionEvent → Decomposition → ControlRatio → Metabolism → OODA → Survival → Struggle → Consciousness → Contradiction → ContradictionField → FieldDerivative → EdgeTransition. **No graceful degradation**: any system raising an exception MUST fail the tick (and therefore the run with exit code 1) per the edge-case rule on engine-system exception handling. Per-system try/except wrappers that swallow errors are explicitly NOT acceptable — partial-state runs are worse than no run for downstream calibration trust.
- **FR-014**: System MUST satisfy "for any single county across 520 ticks, at least one of {`ideology_r`, `ideology_l`, `ideology_f`} changes by ≥5% relative magnitude between tick 0 and tick 519." This is the SC-004 closure condition that spec-065 left as xfail (T028).
- **FR-015**: System MUST satisfy "for two structurally different counties (e.g., Wayne vs Keweenaw), the Pearson correlation between their `ideology_l` time-series is < 0.95." This verifies that consciousness evolution responds to per-county material conditions, not just global drift.
- **FR-016**: System MUST publish at least one event from each of the following EventType families during a canonical 520-tick run, observable in `summary.events`: `BIFURCATION_THRESHOLD`, `CONSCIOUSNESS_SHIFT`, and one of `{EXCESSIVE_FORCE, FASCIST_REVANCHISM, FASCIST_CONVERGENCE}` (the un-organized canonical run routes agitation to fascism so reactionary-side events are expected; `SOLIDARITY_AWAKENING`, `UPRISING`, `REVOLUTIONARY_OFFENSIVE` etc. require SOLIDARITY edges and are NOT expected in this spec scope). Failure to publish any of these indicates the corresponding engine system is not actually firing on the bridged path.
- **FR-017**: System MUST populate `summary.performance.per_system_ms` with non-zero entries for each of the 15 invoked systems. The wrapper infrastructure already exists (spec-065 T074); this requirement closes it by ensuring the wrapper actually runs.
- **FR-018**: System MUST satisfy "the average per-tick wallclock for a 520-tick Michigan-Canada run is ≤ 10 seconds" (matches SC-011 relaxed budget of ≤ 90 minutes total per Phase 0 R8). The original spec draft said ≤ 5 seconds; that was relaxed post-research because the bridge's per-tick SQLite reads dominate the wallclock cost and engine systems can't fit under the original ceiling. Future spec-069 (SQLite cache optimization) will enable tightening.

#### Cross-cutting requirements

- **FR-019**: ~~Originally said: "System MUST satisfy Marx's accounting identity `c + v + s = W` (gross output) per county per tick within ±$1."~~ **DROPPED per /speckit.analyze U1** — after FR-001's formula change (`s = max(0, GDP/52 - v)`), the gross-output identity becomes tautological by construction: `c + v + s = c + v + (GDP/52 - v) = c + GDP/52`. There is no independent W to test against. The calibration property (whether implied W matches BEA empirical gross-output / GDP ≈ 1.85) is covered by FR-003's organic-composition band check. No replacement FR needed.
- **FR-020**: System MUST satisfy Marx's value-added identity `v + s = GDP_per_week` per county per tick within ±5% (calibration tolerance accounting for QCEW/BEA accounting-base differences and within-county commuter-wage attribution).
- **FR-021**: System MUST satisfy "the implied Michigan state rate of profit `total_s / (total_c + total_v)` at any tick falls in [0.05, 0.50]" — Vol III Ch 13 illustrative range (0.20-0.67) relaxed at the lower bound to accommodate BEA-broad `v` (all compensation of employees), since QCEW data is not Shaikh-narrowed to productive labor only. A productive-labor-classification filter is explicitly out of scope for this spec.
- **FR-022**: System MUST preserve the spec-065 baseline contract: `mise run sim:e2e-michigan` produces a successful 520-tick run, refreshes `tests/baselines/michigan-e2e.json` via `--write-baseline`, and the resulting `trace.csv` has zero empty cells in any of the 22 county-applicable columns.
- **FR-023**: System MUST close the xfail on `tests/integration/test_engine_bridge.py::test_tick_over_tick_evolution` (T028) — at least 3 of the SC-004 columns (v, c, s, k, p_acquiescence, p_revolution, ideology_r, ideology_l, ideology_f) MUST show ≥5% relative change between tick 0 and tick 5 for at least one county.
- **FR-024**: System MUST update `ai-docs/state.yaml` and `ai-docs/decisions/` to document the bug fixes, the (0.05, 0.50, 0.45) ideology placeholder, and the new ADR for spec-066.

#### Bug F — Edge bootstrap (added per Phase 0 research, Clarifications Q4)

- **FR-025**: The bridge's `hydrate_initial(...)` MUST seed exactly one `Relationship(source_id=proletariat_id, target_id=bourgeoisie_id, edge_type=EdgeType.EXPLOITATION, value_flow=0.0, tension=0.1)` per county at tick 0. This satisfies the EXTRACTIVE base relation that ImperialRentSystem iterates to extract Φ. The seeded edges are derived from the structural fact that proletariat and bourgeoisie coexist in each county under capitalism — **per Constitution III.5**, this is an empirical (not strategic) edge and therefore lives in the data-loading path (the bridge), not in a player-verb path.
- **FR-026**: The bridge MUST NOT seed any `EdgeType.SOLIDARITY` relationships at tick 0. Per Constitution III.5 ("solidaristic edges, organizing, consciousness-raising are strategic intervention NOT from data") and Clarifications Q4, the un-organized canonical run is the modeled trajectory. As a consequence, ConsciousnessSystem will route ALL agitation to `national_identity` (fascism axis) — which is theoretically correct per Marx + the project's MLM-TW frame for un-organized US 2010-2020.
- **FR-027**: ConsciousnessSystem coefficient calibration MUST set `routing_scale ≥ 0.2` (or document why a smaller value is sufficient to clear SC-005). Default `0.1` produces ~0.000045 drift/tick which does not clear ≥5% over 520 ticks. The bump must be applied via `defines/consciousness.py` overlay or directly in the source defaults.
- **FR-028**: CO_OPTIVE edge mode handling (for labor-aristocracy / imperial-subsidy modeling per `ai-docs/spec-prompts/edge-mode-completeness-analysis.md`) is **explicitly out of scope** for spec-066. A future spec will introduce CO_OPTIVE edge bootstrap from BEA wage-differential data. The `EdgeMode.CO_OPTIVE` enum value already exists in the codebase (`src/babylon/models/enums/topology.py:60`); spec-066 does not exercise it.

### Key Entities

- **CountyMarxPrimitives**: The per-county tuple `(c, v, s, k)` representing constant capital (intermediate inputs consumed weekly), variable capital (wages paid weekly), surplus value (residual extracted weekly), and accumulated capital stock. Currently degenerate (`s = 0` everywhere); after this spec they MUST satisfy Marx's identities.
- **CountyIdeologyProfile**: The per-county ternary `(r, l, f)` simplex coordinate representing the population-weighted distribution of class consciousness (revolutionary), liberal consciousness, and reactionary/fascist consciousness. Currently uniform across all 83 counties; after this spec the *initial* values remain uniform (per the documented placeholder) but evolve per-tick per material conditions.
- **CountyEmploymentMetric**: The per-county "average employed persons during the year" computed from BLS QCEW data. Currently undercounts ~8× due to a unit-conversion bug; after this spec MUST match BLS state aggregates within ±15%.
- **CountySubstrateStocks**: The per-county tuple `(biocapacity_stock, energy_stock, raw_material_stock)` representing ecological + extractive stocks. `energy_stock` is population-apportioned; `raw_material_stock` is land-area-apportioned. Currently `energy_stock == raw_material_stock` for every county due to a missing area-weighting branch.
- **TickContext** (per `src/babylon/engine/context.py:19`): The per-tick context passed to `SimulationEngine.run_tick(graph, services, context)` carrying tick number, correlation_id, and observer hooks. Spec-065 wired the ServiceContainer fields (auditor, boundary_register, event_bus); this spec wires the actual `engine.run_tick(...)` invocation. The spec previously referred to this as `EngineRunContext`; corrected per /speckit.analyze U2 — the actual class name in the codebase is `TickContext`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A canonical 520-tick Michigan-Canada simulation produces `summary.json.terminal_state.total_s > 0` (state-aggregate surplus value strictly positive).
- **SC-002**: The implied state-aggregate rate of profit `total_s / (total_c + total_v)` at terminal tick falls within the relaxed band [0.05, 0.50] — Vol III Ch 13 illustrative range with the lower bound widened to accommodate BEA-broad `v` (QCEW total compensation, not Shaikh-narrow productive labor).
- **SC-003**: ~~Originally said: "Marx's gross-output identity `c + v + s = W` holds per county per tick within ±$1."~~ **DROPPED per /speckit.analyze U1** alongside FR-019 — tautological after FR-001 formula fix.
- **SC-004**: Marx's value-added identity `v + s = GDP_per_week` holds per county per tick within ±5% across all persisted rows (calibration tolerance).
- **SC-005**: For at least one county across the canonical run, the `ideology_f` (fascism / national_identity) axis changes by ≥5% relative magnitude between tick 0 and tick 519. Closes T028 xfail. Per Clarifications Q4, drift on the `ideology_r` (revolutionary) axis is NOT expected in the un-organized canonical run; this requires SOLIDARITY edges which are explicitly out of scope.
- **SC-006**: For Wayne County (high-Φ industrial core) and Keweenaw County (low-Φ rural periphery), the Pearson correlation between their `ideology_f` time-series across the canonical run is strictly less than 0.95 (verifying per-county material-conditions-driven divergence). Divergence emerges from differential EXTRACTIVE edge weights — Wayne's higher imperial rent extraction generates more agitation per tick than Keweenaw's, producing distinct fascism-routing trajectories.
- **SC-007**: The state-aggregate `employment_proxy` total at tick 0 lies within ±15% of the BLS QCEW Michigan 2010 published total (~4.2M).
- **SC-008**: For at least 50% of Michigan counties at tick 0, `energy_stock` and `raw_material_stock` differ in value (structural distinguishability).
- **SC-009**: Every county at tick 0 satisfies `(ideology_r, ideology_l, ideology_f) = (0.05, 0.50, 0.45)` within ±1e-9 float tolerance, and `r + l + f = 1.0 ± 1e-9`.
- **SC-010**: `summary.performance.per_system_ms` contains exactly 21 entries (one per engine system per the canonical `_DEFAULT_SYSTEMS` list) with all values strictly positive.
- **SC-011**: The canonical 520-tick Michigan-Canada wallclock total is ≤ 90 minutes (≤ 5400 seconds), giving a per-tick mean of ≤ 10 seconds. Relaxed from the spec-original ≤ 45 min per Phase 0 research R8 — SQLite per-tick read overhead in the bridge dominates current cost; a follow-up spec (provisionally spec-069) will optimize the SQLite read path to enable a future tightening of this budget.
- **SC-012**: `summary.events` contains at least one event from each of: `BIFURCATION_THRESHOLD`, `CONSCIOUSNESS_SHIFT`, and one of `{EXCESSIVE_FORCE, FASCIST_REVANCHISM, FASCIST_CONVERGENCE}` (the un-organized canonical run produces fascism-side events, not solidarity-side).
- **SC-013**: `tests/integration/test_engine_bridge.py::test_tick_over_tick_evolution` (T028) passes (xfail removed).
- **SC-014**: A reader of `quickstart.md` and `ai-docs/decisions/ADR043*` finds an explicit, prominent statement that the (0.05, 0.50, 0.45) ideology baseline is a deliberate placeholder pending a future spec to design principled per-county seeding.
- **SC-015**: All spec-065 acceptance tests continue to pass (no regression in the persistence pipeline).

## Assumptions

- The 5 bug categories identified in the spec-065 audit-to-standard sweep on 2026-05-15 are the complete set of correctness issues blocking economic and political coherence. Any additional bugs surfaced during implementation may be added to this spec via amendment, OR deferred to a successor spec, at the implementer's judgment.
- The user has explicitly chosen the uniform (0.05, 0.50, 0.45) ideology baseline as a placeholder. Designing a principled per-county data-driven ideology seeding scheme is **explicitly out of scope** for this spec; it is documented as deferred to a future spec to be authored when the user has thought through the proxies, weighting scheme, and calibration approach.
- The SC-011 budget is relaxed (per Phase 0 R8) from spec-065's ≤ 600s (10 min) to ≤ 5400s (90 min) to accommodate the per-tick engine-system cost. The current spec-065 measured baseline is 2880s (48 min) without the engine running; spec-066's engine adds an estimated 200-400ms/tick → ~104 minutes for full Michigan-Canada. The 90-minute ceiling is achievable IF (a) the SQLite per-tick reads are even modestly optimized OR (b) the spec-069 SQLite caching follow-up lands first. The spec-065 T074 wallclock wrapper measures per-system overhead honestly.
- The spec-066 work depends on existing engine infrastructure (the 15 systems already implemented per `CLAUDE.md`'s engine architecture section). No new engine systems are required; only their invocation from the bridged runner.
- The QCEW SQLite normalization fix (FR-002) requires either re-ingesting QCEW data with proper ownership filtering, or applying a SQL-level filter at hex hydration time. The implementer chooses; both produce the same observable trace output.
- The BEA national industry I-O table (FR-003) is not yet ingested in the current SQLite snapshot. The fix may either: (a) ingest the table and use per-industry coefficients, OR (b) calibrate the existing single-fraction constant against the implied-c/v invariant. Both satisfy the spec.
- The spec-065 baseline at `tests/baselines/michigan-e2e.json` will be regenerated as part of this spec's work. Diffing the spec-065 baseline (degenerate `s = 0`) against the spec-066 baseline (Marxist-coherent `s > 0`) constitutes the headline change visible to CI.
- The `--write-baseline` flag added in spec-065 T085 continues to refresh the baseline atomically as part of the canonical mise task.
- The 15-system engine integration will use the existing ServiceContainer wiring shipped in spec-065 (auditor, boundary_register, event_bus, etc.). No further bridge-side wiring is required for ServiceContainer construction; the runner only needs to call `services = ServiceContainer.create(...)` with the bridge-owned components and pass `services` to `engine.run_tick(...)`.
- **Delivery model** (per Clarifications Q3): the spec ships incrementally on a single branch. The MVP commit closes US1 + US2 (both P1). Subsequent commits close US3, US4, US5 (each P2/P3) independently. The spec is "done" only when all 5 user stories close, but partial completion is shippable as MVP. This mirrors the spec-065 Phase 3 US1 → Phases 4-7 → Phase 8 delivery sequence.
