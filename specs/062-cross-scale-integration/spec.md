# Feature Specification: Cross-Scale Integration — Value, Substrate, and Tick Propagation

**Feature Branch**: `062-cross-scale-integration`
**Created**: 2026-05-12
**Status**: Draft
**Input**: Architectural document "Cross-Scale Integration: Value, Substrate, and Tick Propagation" — eight-level spatial hierarchy with conservation rules, two-phase SQLite-init/Postgres-runtime persistence, weekly tick semantics, substrate ledger insertion at pipeline position 2.5, five distinct cross-scale flow types, international integration as boundary nodes, and per-tick conservation audit logging.

## Clarifications

### Session 2026-05-12

- Q: Industry-share derivation strategy for the Vol III equalization flow — derive on read, persist per-(hex, NAICS), or hybrid top-K + tail derivation? → A: Option A — derive on demand from QCEW employment shares applied to hex-aggregated c/v/s; hex c/v/s remains the only primary state. (Confirms FR-031 / FR-030 / FR-029.)
- Q: Tick-write atomicity boundary — per-tick transaction, per-system sub-transactions, or session-level commit? → A: Option A — per-tick transaction. All `dynamic_*` writes plus all audit-log rows for a given tick commit atomically; crash recovery resumes from the last committed tick. (Adds FR-008a; supersedes the prior assumption about asynchronous audit-log flush.)
- Q: Severity-alarm operational policy when `|residual| > 1e-6` is detected mid-run — continue silently, continue with structured event emission, or halt with operator override? → A: Option B — continue with surfacing. Alarm rows emit a structured event onto the existing event bus / observer channel, but the tick proceeds without halting. (Refines FR-047.)
- Q: Reference-data year coverage at initialization — copy all years available, copy declared scenario range only, or buffered ±1? → A: Option B — copy `start_year` through `start_year + scenario_length_years` only. Scenario length is declared at session creation and becomes part of the session contract. (Refines FR-004; adds FR-004a.)
- Q: α_weekly equalization-rate calibration target — pin α_weekly ≈ 0.000193, pin α_weekly ≈ 0.00203, or keep configurable in GameDefines with documented default and Phase 0 empirical calibration? → A: Option C — α_annual is configurable in `GameDefines` (documented default `α_annual = 0.01`); runtime derives `α_weekly = 1 − (1 − α_annual)^(1/52)` using the same geometric form as the depreciation rate (FR-014). Empirical calibration is deferred to `/speckit.plan` Phase 0 research. (Refines FR-029; adds FR-029a.)
- Amendment (Phase 0 / GATE-5 closure / Constitution IV.1): FR-036 minimum external node list expanded to **8 regions** — China, EU, India, Sub-Saharan Africa, Latin America, Russia/CSI, Southeast Asia, **and Canada**. Canada is mandated by Constitution IV.1 (Detroit-Windsor Boundary Condition) and absorbs cross-border commute, automotive supply chain, and water-rights flows that Rest-of-USA cannot. See `research.md` §4.
- Amendment (Spec Analysis 2026-05-12): Three text-level fixes from `/speckit.analyze`: (1) **FR-040** boundary-register row schema rewritten to the discriminator-enum form ratified in `research.md` §2 (R2) and `data-model.md` §2.3 / `contracts/boundary_register.yaml`. (2) **FR-053** disambiguated — Production runs at pipeline slot 3, Solidarity at slot 4 is **not** a flow stage and operates on independent consciousness state, and the remaining four economic flow stages execute as strict sequential sub-stages 5a–5d within the ImperialRent slot. (3) **Assumptions "External-node set extensibility"** and **SC-015** corrected from the obsolete pre-amendment counts (7 nodes) to the post-Canada accurate counts (8 international + 1 Rest-of-USA = 9 external nodes total).

## Overview

This feature codifies the **cross-scale propagation engine** that ties together every previously-specified component of the Babylon simulation. It does not introduce new economic theory; it specifies the load-bearing scaffolding that lets value, physical substrate, and time advance coherently across an eight-level spatial hierarchy (hex res 7 → hex res 6 → hex res 5 → county → state → region → national → international), one weekly tick at a time, with rigorously-enforced conservation at every level.

It also clarifies the **two-phase persistence boundary**: SQLite is read once at simulation start to calibrate the initial world state, and is never touched again at runtime. After initialization, the simulation runs entirely against Postgres, with the SQLite reference data copied into `immutable_reference_*` tables on Postgres so that the simulation has a single read source during play.

The feature defines the contract that every downstream system — substrate, production, circulation, equalization, distribution, imperial rent — depends on. It is foundational to the Detroit 2010–2025 (780-tick) test scenario.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Two-Phase Initialization Boundary (Priority: P1)

Persephone (the simulation engineer) starts a new game session for the Detroit test scenario. She selects `start_year = 2010` and clicks "Initialize". The system must (a) read the immutable reference database once to hydrate the initial world state at her chosen calendar year, (b) copy any annual time series needed at runtime into the runtime database, and (c) close the reference database before tick 0 begins. From that point on the simulation must run entirely from the runtime store with no further reads of the initialization-only database.

**Why this priority**: Without a clean initialization boundary, downstream systems may inadvertently read stale or absent reference data during play, producing silent drift. Cleanly separating "init reads" from "runtime reads" is the single most foundational invariant of the entire engine.

**Independent Test**: With the simulation running past tick 0, sever access to the initialization-only database (rename it, take it offline, or revoke read permission). The simulation must continue executing further ticks without raising any file/connection errors. Conversely, before tick 0, the system must successfully hydrate every county-level value from the reference store and report which years' coefficients it copied to the runtime store.

**Acceptance Scenarios**:

1. **Given** a fresh Postgres runtime DB and an intact SQLite reference DB, **When** the engineer initializes a session at `start_year = 2010`, **Then** the runtime DB contains hex-level c/v/s, capital stock K, biocapacity stocks, internet/surveillance state, and international boundary node state for the entire study area, and the runtime DB contains reference rows for at least all years from `start_year` to the latest year required by the configured scenario length.
2. **Given** an initialized session at tick 0, **When** the reference SQLite database is made unreadable, **Then** ticks 1 through the configured scenario length all complete without raising any read errors against the initialization-only store, and every system reads coefficients exclusively from the runtime store.
3. **Given** an initialization attempt where the reference DB lacks the requested `start_year`, **Then** the system must refuse to initialize and report which year(s) of reference data are missing.

---

### User Story 2 — Weekly Tick Cadence with Year-Scoped Coefficients (Priority: P1)

Persephone runs a 780-tick simulation (Detroit 2010-2025, 15 years × 52 weeks). At any tick `t`, every system that consumes annual reference data (BEA input-output coefficients, MELT τ, basket visibility γ, ERDI ratios, Hickel drain time series) must reliably retrieve the values appropriate for the *currently simulated year*, with smooth interpolation across the 52 weeks of each year for slowly-varying series and step-function lookup for inherently event-discrete series.

**Why this priority**: A simulation that crosses year boundaries with wrong coefficient lookups will silently bake calibration errors into every downstream invariant. Weekly tick semantics — and the lookup discipline that goes with it — is what makes the engine quantitatively meaningful. P1 because every other story depends on temporally-correct coefficient lookup.

**Independent Test**: Initialize a session and step it through one full simulated decade. For each system that consumes annual reference data, sample its active coefficient values at ticks 0, 51, 52, 103, 104, 155, 156, ... and verify that (a) at year-boundary ticks the lookup advances to the next annual row of reference data, (b) for slowly-varying series the interpolated value matches the linear blend of the bracketing annual rows at the fractional position `(tick mod 52)/52`, and (c) for event-discrete series the value is the step-function of the prior or new year's row exactly at the boundary tick.

**Acceptance Scenarios**:

1. **Given** a session at `start_year = 2010`, **When** the engine reports the currently-simulated year at any tick `t`, **Then** the reported year equals `start_year + (t // 52)`.
2. **Given** a slowly-varying reference series with `value(2010) = A` and `value(2011) = B`, **When** the engine reports its active coefficient at tick `26` (mid-year 2010), **Then** the value equals approximately `A + (B - A) × (26 / 52)`, within floating-point tolerance.
3. **Given** an event-discrete reference series, **When** the engine reports its active coefficient at ticks `51` and `52`, **Then** tick `51` reports the year-N value and tick `52` reports the year-(N+1) value with no interpolation between them.
4. **Given** the perpetual-inventory capital stock evolution with annual depreciation rate δ_annual, **When** the engine advances one tick, **Then** the per-tick depreciation applied is `1 - (1 - δ_annual)^(1/52)`, not `δ_annual / 52`.

---

### User Story 3 — Cross-Scale Aggregation Without Stored Duplicates (Priority: P1)

Persephone, looking at the dashboard, asks the engine: "What is the total surplus value extracted in Wayne County this tick?" The engine must produce the answer by summing the hex-level surplus values for every hex whose `h3_to_county()` mapping resolves to Wayne County, *without ever having persisted a duplicate "county-level surplus" row* that could drift from the hex-level source of truth.

**Why this priority**: The single most reliable way to fail conservation is to store the same quantity at two different scales and let them drift. By making hex (resolution 7) the only persisted level of c/v/s and computing every coarser scale as a query, the engine forecloses an entire class of bugs. P1 because every dashboard, every test, and every cross-scale invariant depends on this discipline.

**Independent Test**: Populate hex-level c/v/s for every hex in the study area, then query county-level, state-level, and national-level c/v/s. Independently sum the hex-level values offline and compare the results to the engine's query outputs; they must match to within ε = 1e-10. Then mutate a single hex's value and verify the query results at every coarser scale change by exactly the same delta.

**Acceptance Scenarios**:

1. **Given** a fully-populated study area, **When** the engine reports county-level c, v, s for any county, **Then** the reported value equals the exact sum of c, v, s respectively over all hexes mapped to that county.
2. **Given** the same state, **When** the engine reports state-level c, v, s, **Then** the reported value equals the exact sum of c, v, s respectively over all counties in that state.
3. **Given** any cross-scale query, **When** the engine retrieves a parent-scale value, **Then** that value is *not* read from a stored aggregate row — it is computed on read from the hex-level primitive.
4. **Given** an isolated mutation to a single hex's surplus value of magnitude Δ, **When** the engine re-reports county / state / national surplus, **Then** every parent-scale value increases by exactly Δ.

---

### User Story 4 — Five Flow Types with Correct Scale Boundaries (Priority: P1)

For a given tick, the engine must apply five distinct flow types in a fixed sequence: (1) **Production** (Vol I, hex-local), (2) **Imperial Rent inflow** (Φ, distributed from international boundary), (3) **Circulation** (Vol II wage redistribution between hexes via the commute OD matrix), (4) **Equalization** (Vol III Part I capital migration toward higher rate of profit), and (5) **Distribution** (Vol III Parts IV–VI surplus split into profit, interest, rent, taxes at county scale). Each flow respects its own scale rule; conservation holds at every level for every operation.

**Why this priority**: Marx's three-volume framework loses meaning if the geographic and industrial scales at which each flow operates are wrong. Conflating hex-local equalization with industry-bound equalization (the existing prototype's bug) silently mis-represents how capital actually moves. P1 because the entire economic-mechanics surface depends on getting each flow's scale right.

**Independent Test**: Construct a contrived two-hex, two-industry, one-county scenario with known inputs. Step one tick. After each of the five flow stages, snapshot c, v, s at hex level and verify (a) Production grew total v+s by exactly the labor input that tick, (b) Imperial Rent inflow increased the receiving county's c by exactly the Φ_week distributed share, (c) Circulation moved v between hexes without changing the per-tick sum, (d) Equalization redistributed c across industries within each hex but preserved both per-hex and per-industry sums modulo cross-hex industry transfers, and (e) Distribution split s into p+i+r+t at the county scale, summing exactly back to the pre-split s.

**Acceptance Scenarios**:

1. **Given** a one-county study area with two hexes A and B, **When** Production runs, **Then** sum(c+v+s) over A and B at tick t+1 equals sum(c+v+s) at tick t plus that tick's living-labor-derived s, and no value moves between A and B during the Production stage.
2. **Given** the same area and a commute OD matrix routing 30% of B's workers to A, **When** Circulation runs after Production, **Then** v[A] increases by 0.3 × v[B]_pre-circulation, v[B] decreases by the same amount, and sum(v) over the tri-county region is unchanged.
3. **Given** a hex with one auto-industry firm (low r) and one tech-industry firm (high r), **When** Equalization runs, **Then** capital migrates *within each industry across hexes*, not from auto to tech within the single hex.
4. **Given** a county with extracted surplus S at the end of Equalization, **When** Distribution runs using the county's interest, rent, and tax shares for the current year, **Then** p + i + r + t = S exactly (to within floating-point tolerance), where each share is determined from the relevant federal financial data series for the active simulated year.
5. **Given** a national Φ_year inflow from Hickel's drain time series for the current simulated year, **When** the engine distributes Φ to counties by import-share-weighted exposure, **Then** sum over all counties of the per-week Φ_week share equals Φ_year / 52, with the residual within tolerance.

---

### User Story 5 — Per-Tick Conservation Audit Log (Priority: P2)

Persephone, debugging a divergent simulation, opens the conservation audit log. For each tick, she sees one row per scale-invariant pair (e.g., `tick=137, scale='county', invariant='hex_to_county_sum_c', computed=…, expected=…, residual=2.3e-12`). She can immediately identify the first tick at which any invariant's residual exceeded ε, the scale at which the divergence originated, and the specific invariant violated.

**Why this priority**: Without a forensic log, conservation failures present as mysterious dashboard inconsistencies hours of debugging later. With one, the divergence is timestamped, scoped, and named at the moment it occurs. P2 (not P1) because the engine can function without the log; the log is what makes debugging tractable.

**Independent Test**: Run 100 ticks against a known-good scenario; the audit log must contain exactly `100 × N_invariants` rows with `|residual| < ε`. Then deliberately introduce a conservation defect (e.g., add a small constant to v on every Circulation step). Re-run; the audit log must show the defect detected with `|residual| > ε` at the appropriate tick and scope. The first defect-bearing row must be identifiable by a single ORDER BY tick, scale, invariant query.

**Acceptance Scenarios**:

1. **Given** a 100-tick simulation run, **When** the audit log is queried, **Then** it contains at least one row per (tick, scale, invariant) combination, where the enumerated set of invariants includes hex→county, county→state, state→national, and global Φ-balance checks for c, v, and s.
2. **Given** any audit row, **Then** `|computed - expected| ≤ ε` for ε = 1e-10, *or* the row is explicitly flagged with a non-zero severity indicator.
3. **Given** a deliberately-broken flow that adds 0.01 to total v each tick, **When** Circulation runs, **Then** within one tick the audit log records a row with `|residual| ≥ 0.01` flagged for review.

---

### User Story 6 — International Boundary Nodes (Priority: P2)

The engine models the rest of the world as a small set of external nodes (China, EU, India, Sub-Saharan Africa, Latin America, Russia/CSI, Southeast Asia) sitting in the same graph as the internal hex study area. Each external node carries country-aggregate state (Φ-source magnitude per year, bilateral trade volumes, ERDI ratio) but no internal hex structure. Edges between US hexes/counties and external nodes are either *trade edges* (bidirectional, physical goods and value) or *drain edges* (directional periphery → core, carrying Φ). All cross-boundary flows are absorbed by the boundary flow register so that within-study-area conservation is exact, and a separate global-Φ invariant relates periphery outflow to core inflow on the annual scale.

**Why this priority**: The fundamental theorem of MLM-TW — that core revolution is impossible while W_c > V_c — depends entirely on the imperial rent inflow Φ. Without the international boundary, Φ has no source and the theorem is empty. P2 (not P1) because the internal mechanics can be tested with synthetic boundary nodes before real bilateral trade data is fully wired in.

**Independent Test**: Instantiate one external node (e.g., China) connected to one US county via a single drain edge carrying Φ_year = $100M for simulated year 2010. Step one full simulated year (52 ticks). The boundary flow register must record 52 weekly Φ inflows summing to $100M (within ε), the receiving county's c must show the cumulative inflow, and the global annual Φ-balance invariant must report `|sum_periphery_outflow - sum_core_inflow| < ε` after tick 52.

**Acceptance Scenarios**:

1. **Given** a study area with one external node sourcing Φ_year, **When** the engine completes 52 ticks of a simulated year, **Then** the receiving country's cumulative Φ inflow equals Φ_year to within floating-point tolerance.
2. **Given** a bilateral trade edge with country-aggregate FAF tonnage and Ricci $-value for the current simulated year, **When** the engine reports the per-week flow across that edge, **Then** the reported flow is consistent with the annual quantity divided across the 52 weeks of the year.
3. **Given** a boundary flow from a specific US hex to a specific external node, **When** the engine records the flow in the boundary flow register, **Then** the recorded tuple identifies the source hex, the destination external node, the flow type, the magnitude, and the tick.

---

### User Story 7 — Substrate Ledger Insertion at Pipeline Position 2.5 (Priority: P3)

The materialist causality pipeline has 15 systems in a fixed order. The substrate system — which tracks the *physical* stocks of raw materials, energy, capacity, and biocapacity that production consumes — must execute at position 2.5, after Territory (system 2) and before Production (system 3). Production reads from the substrate's just-computed physical stocks; if substrate runs out of position, production reads stale or incorrect physical state.

**Why this priority**: Without the substrate slot, value flows lose their material anchor — the engine becomes a price/quantity-only model with no link to ecological limits or physical bottlenecks. P3 (not P1) because the value-only model is still useful for many scenarios; substrate becomes critical only when ecological constraints bind or supply chains break.

**Independent Test**: Run one tick on a scenario where a hex's physical raw-material stock has been deliberately zeroed. Verify the engine ran systems in order Vitality → Territory → Substrate → Production → ..., that Substrate computed the zero stock first, and that Production downstream consumed *that just-computed value* and produced zero output for the affected hex.

**Acceptance Scenarios**:

1. **Given** the engine pipeline ordering, **When** any tick runs, **Then** the Substrate system executes after Territory and before Production in deterministic order.
2. **Given** Substrate computes a zero physical stock for some hex, **When** Production runs in the same tick, **Then** Production sees the zero stock (not a stale prior value) and outputs are constrained accordingly.

---

### Edge Cases

- **Missing reference year**: Initialization is attempted for a `start_year` that is outside the range covered by the reference database. The system must refuse to initialize and report the missing year(s).
- **Boundary year crossing**: A simulation spans more years than the reference data covers (e.g., starts at 2024 with 2-year scenario, but reference data ends at 2024). At the first tick beyond the last covered year, the engine must clamp coefficient lookups to the last available year and emit a one-time warning (not refuse to continue).
- **Audit residual just above tolerance**: A flow accumulates a 1e-9 residual after 100 ticks (above ε but still tiny in absolute terms). The system flags the row but does not halt the simulation; severity is graded.
- **Boundary register saturation**: The boundary flow register grows by `tick × N_boundary_edges` rows. After 780 ticks with **9 external nodes** (8 international + 1 Rest-of-USA per the Canada amendment to FR-036) and ~1700 internal hexes, total rows could exceed 9M. The system must remain queryable within reasonable latency (single-second range) for any tick-scoped or hex-scoped slice.
- **Crisis discontinuous reset within a tick**: A contradiction-field threshold is crossed mid-tick. The system applies the coefficient reset categorically (not by smooth drift), treats sub-tick dynamics as aggregated into the tick, and records the reset event in the audit log.
- **Industry equalization without per-hex industry breakdown**: Equalization must move capital within an industry across hexes. If hex c/v/s is stored hex-aggregated (not per-industry), the engine derives industry shares from QCEW employment shares on read; this is not a stored duplicate.
- **External node referencing a year with no Hickel/Ricci coverage**: For years prior to Hickel's window (pre-1995), the engine uses the nearest covered year and flags the substitution.
- **Hex that maps to no county (study-area edge hex)**: Some H3 cells at the edge of the tri-county study area may not be fully contained in any FIPS county. The system maps these to a "rest-of-USA" boundary node rather than dropping them silently.

## Requirements *(mandatory)*

### Functional Requirements

**Two-Phase Persistence (FR-001 to FR-008)**

- **FR-001**: The system MUST treat the SQLite reference database (`marxist-data-3NF.sqlite`) as read-only and accessed exclusively during the initialization phase before tick 0.
- **FR-002**: The system MUST close all connections to the SQLite reference database before the first runtime tick executes.
- **FR-003**: The system MUST hydrate Postgres `dynamic_*` tables with the calibrated initial WorldState during initialization, including hex-level c/v/s, capital stock K, biocapacity stocks, internet/surveillance coupling, and international boundary node state.
- **FR-004**: The system MUST copy every annual reference series needed at runtime from SQLite into Postgres `immutable_reference_*` tables during initialization, preserving the year column as a primary lookup key. The year range copied MUST be exactly `[start_year, start_year + scenario_length_years]` inclusive — no narrower (would miss years the simulation reads), no wider (wastes init storage and muddies the init contract).
- **FR-004a** *(added 2026-05-12 via Clarifications)*: `scenario_length_years` MUST be declared at session creation alongside `start_year` and MUST be immutable for the session's lifetime. The pair `(start_year, scenario_length_years)` together define the year-range envelope the session is contractually bound to.
- **FR-005**: The system MUST never write to `immutable_reference_*` tables after initialization completes.
- **FR-006**: The system MUST execute every runtime tick by reading from Postgres `dynamic_*` and `immutable_reference_*` tables and writing back to Postgres `dynamic_*` tables only.
- **FR-007**: The system MUST append a row to the `conservation_audit_log` Postgres table for each (tick, scale, invariant) combination evaluated on every tick.
- **FR-008**: The system MUST report, at end-of-initialization, which years of reference data were copied into Postgres and the count of hex-level records hydrated.
- **FR-008a** *(added 2026-05-12 via Clarifications)*: Every runtime tick MUST execute its `dynamic_*` writes and its conservation-audit-log appends inside a single Postgres transaction scoped to that tick. The transaction MUST either commit as a whole or roll back as a whole; partially-written ticks MUST NOT be observable from any subsequent read. After a crash, the system MUST resume from the last committed tick with no partial-tick state present.

**Tick & Temporal Mechanics (FR-009 to FR-016)**

- **FR-009**: One tick MUST represent one calendar week. Tick `0` corresponds to the first week of the configured `start_year`.
- **FR-010**: The currently-simulated calendar year MUST be derivable as `start_year + (tick // 52)` for any tick.
- **FR-011**: For every reference series consumed at runtime, the system MUST classify it as either **slowly-varying** (subject to linear interpolation across the 52 weeks of each year) or **event-discrete** (subject to step-function lookup with jumps at year-boundary ticks). The classification MUST be explicit and recorded as configuration, not implicit per-call-site behavior.
- **FR-012**: For slowly-varying series, the active coefficient at tick `t` MUST equal `v(y) + (v(y+1) - v(y)) × ((t mod 52) / 52)`, where `y = start_year + (t // 52)` and `v(y)` is the reference row for year `y`.
- **FR-013**: For event-discrete series, the active coefficient at tick `t` MUST equal `v(start_year + (t // 52))` with no inter-year interpolation.
- **FR-014**: Capital stock perpetual-inventory evolution MUST use the geometric weekly depreciation rate `δ_weekly = 1 - (1 - δ_annual)^(1/52)`, not the linear approximation `δ_annual / 52`.
- **FR-015**: For the canonical default `δ_annual = 0.07`, the system MUST apply `δ_weekly ≈ 0.001397` and MUST verify this exactly during a doctest/regression check (within floating-point tolerance).
- **FR-016**: If the simulated year derived from the current tick exceeds the latest reference year present in `immutable_reference_*`, the system MUST clamp coefficient lookups to the latest available year and emit a one-time warning per series.

**Spatial Hierarchy & Aggregation (FR-017 to FR-024)**

- **FR-017**: The system MUST recognize exactly eight nesting levels: hex resolution 7, hex resolution 6, hex resolution 5, county (FIPS), state (FIPS state), Census region / MSA / CFS area, national (USA), and international.
- **FR-018**: Hex resolution 7 MUST be the *only* persisted source of truth for c, v, s, capital stock K, and biocapacity stocks. All coarser-scale values MUST be computed on read by summing over child hexes.
- **FR-019**: The system MUST NOT persist a row representing aggregated c/v/s, K, or biocapacity at any level coarser than hex resolution 7.
- **FR-020**: Aggregation from one level to its parent MUST hold exactly within floating-point tolerance `ε = 1e-10`. Specifically, for c (and analogously for v, s, K, biocapacity):
  - `c[county] = Σ_{h in county} c[h]`
  - `c[state] = Σ_{cty in state} c[cty]`
  - `c[nation] = Σ_{st in nation} c[st] + boundary_inflow_c − boundary_outflow_c`
- **FR-021**: Distribution rules used at initialization to push county-level federal data down to hexes (e.g., LODES workplace density for QCEW, Census housing density for BEA REIS, import-share-weighted exposure for Hickel drain) MUST be stored as coefficient configuration in `GameDefines`, not as data tables.
- **FR-022**: For any hex at the edge of the study area that is not fully contained in any FIPS county, the system MUST map it to the appropriate boundary node ("rest-of-USA" or specific external node) rather than dropping it.
- **FR-023**: County → state mapping MUST use the FIPS county code prefix; state → region/MSA mapping MUST use the canonical Census definitions in reference data; nation has exactly one identifier "USA" for the simulation.
- **FR-024**: Coarser-scale queries (county, state, region, national) MUST be exposed as named read-only views on the runtime store, not as application-level computations duplicated across systems.

**Five Flow Types (FR-025 to FR-035)**

- **FR-025**: The per-tick pipeline MUST execute the five economic flow types in the fixed order: Production (Vol I) → Imperial Rent inflow → Circulation (Vol II) → Equalization (Vol III Pt I) → Distribution (Vol III Pts IV–VI).
- **FR-026**: Production MUST be hex-local: it consumes substrate physical stocks and labor at a single hex and produces c+v+s at the same hex. No cross-hex movement occurs during the Production stage.
- **FR-027**: Production MUST grow total v+s by exactly the labor-derived surplus value generated that tick; c is conserved during Production (it is consumed and transformed but not created or destroyed).
- **FR-028**: Circulation MUST move variable capital v between hexes via the commute OD matrix, with conservation: `Σ_{hexes in study area} v[h, t]` is preserved within the study-area boundary modulo flows absorbed by the boundary flow register.
- **FR-029**: Equalization MUST move capital within each industry across hexes toward higher rate of profit. The per-tick coefficient `α_weekly` MUST be derived from a configurable annual rate `α_annual` (declared in `GameDefines` with documented default `α_annual = 0.01`) using the geometric form `α_weekly = 1 − (1 − α_annual)^(1/52)` — the same form mandated for depreciation in FR-014. Empirical calibration of `α_annual` against observed industry-of-profit-rate convergence is deferred to `/speckit.plan` Phase 0 research.
- **FR-029a** *(added 2026-05-12 via Clarifications)*: Whichever value of `α_annual` is configured, the runtime MUST verify `α_weekly < 1/52` (i.e., complete equalization horizon is longer than one year) as a startup invariant. A value violating this MUST fail initialization with an explicit message naming the configured value and the implied per-week rate.
- **FR-030**: Equalization MUST NOT mix capital across industries within a single hex (that is not what profit equalization means in the Marxist framework).
- **FR-031**: Industry breakdown for Equalization MUST be derived on demand from QCEW employment shares applied to hex-aggregated c/v/s; per-(hex, industry) c/v/s MUST NOT be persisted as primary state.
- **FR-032**: Distribution MUST operate at county scale, splitting the period's surplus s into profit, interest, rent, and taxes (p+i+r+t) using county-level financial data series for the currently-simulated year.
- **FR-033**: Distribution MUST conserve s exactly: `p + i + r + t = s` within floating-point tolerance after the operation.
- **FR-034**: Imperial Rent inflow Φ_week MUST be derived from the Hickel annual drain time series, distributed to counties by their import-share-weighted exposure (computed from BEA I-O import shares and county-level industry mix).
- **FR-035**: Per-week Φ MUST equal annual Φ_year divided by 52, applied uniformly across the 52 weeks of each year (no sub-annual seasonality is asserted by Hickel and none is fabricated).

**International Boundary Nodes (FR-036 to FR-042)**

- **FR-036**: The system MUST instantiate external nodes for at least the following 8 world regions in the initial WorldState: China, EU, India, Sub-Saharan Africa, Latin America, Russia/CSI, Southeast Asia, **and Canada** (the latter mandated by Constitution IV.1 — Detroit-Windsor Boundary Condition). The specific node count is a configuration parameter and the list may be extended.
- **FR-037**: Each external node MUST carry country-aggregate state including (a) Φ-source magnitude for the current simulated year (from Hickel), (b) bilateral trade volumes (from Comtrade/Ricci when present, synthetic baseline otherwise), and (c) the ERDI ratio for unequal-exchange computation.
- **FR-038**: External nodes MUST have no internal hex structure and no internal class state — they are reduced state representations of "the rest of the world relative to the study area".
- **FR-039**: Edges between internal nodes and external nodes MUST be one of exactly two types: **trade edges** (bidirectional, carrying physical FAF/Comtrade tonnage and Ricci $-value) or **drain edges** (directional periphery → core, carrying Hickel Φ).
- **FR-040**: The Boundary Flow Register MUST record each cross-boundary flow as a dyadic-flow row with these dimensional fields: `(tick, source_node_id, source_kind, dest_node_id, dest_kind, flow_type, magnitude)`. The kind discriminators `source_kind` and `dest_kind` MUST each be one of `{hex, county, state, national, external}`, identifying which ID space the corresponding `*_node_id` lives in (H3 res-7 index, 5-digit FIPS county code, 2-digit FIPS state code, `"USA"`, or external-node identifier respectively). Per-hex source/destination resolution is required for commute flows in particular; the discriminator pattern enables mixed-kind rows (e.g., `external → county` for Φ drain, `hex → external` for cross-border commute). The full schema is normative in `contracts/boundary_register.yaml` and `data-model.md` §2.3.
- **FR-041**: For years prior to the earliest year covered by Hickel/Ricci data, the system MUST use the nearest available year and flag the substitution in the audit log.
- **FR-042**: An "Rest-of-USA" boundary node MUST exist as the destination for all internal flows that exit the tri-county study area without crossing the international boundary (e.g., commute to Chicago or Toledo).

**Conservation Invariants & Audit Log (FR-043 to FR-049)**

- **FR-043**: For every tick `t`, the system MUST verify and log at minimum the following invariants per quantity in `{c, v, s, K, biocapacity}`:
  - `hex → county sum invariant` (one row per county per quantity)
  - `county → state sum invariant` (one row per state per quantity)
  - `state → national sum invariant` (one row per quantity)
  - `study-area boundary balance invariant`: `inflow − outflow ≈ change in study-area total` (one row per quantity)
- **FR-044**: For every simulated year, on the first tick after each year boundary, the system MUST verify and log the global Φ-balance invariant: `Σ_periphery Φ_outflow_year ≈ Σ_core Φ_inflow_year`.
- **FR-045**: Each conservation audit row MUST contain at minimum: `(tick, scale, invariant_name, computed_value, expected_value, residual, severity)`.
- **FR-046**: A row with `|residual| ≤ ε` MUST be tagged `severity='ok'`. A row with `ε < |residual| ≤ 1e-6` MUST be tagged `severity='warn'`. A row with `|residual| > 1e-6` MUST be tagged `severity='alarm'`.
- **FR-047**: An `severity='alarm'` row MUST NOT halt the simulation by default, but MUST be queryable and reportable via a single tick-ordered query. When such a row is written, the engine MUST emit a structured event onto the existing event bus / observer channel (subscribers — UI banners, batch-mode stderr loggers — render the alarm without blocking the tick).
- **FR-048**: Within-stage conservation MUST hold per-operation: Production strictly grows v+s (by labor-derived increment); Imperial Rent inflow strictly increases study-area c by Φ_week; Circulation preserves sum(v) modulo boundary register; Equalization preserves per-industry sum(c) within study area; Distribution preserves s as p+i+r+t.
- **FR-049**: The audit log table MUST be append-only at the row level. Existing rows MUST NOT be modified or deleted by any runtime tick logic.

**Pipeline Ordering (FR-050 to FR-053)**

- **FR-050**: The materialist causality pipeline MUST execute its 15 systems in a deterministic order per tick: Vitality (1) → Territory (2) → **Substrate (2.5, this feature)** → Production (3) → Solidarity (4) → ImperialRent (5) → Consciousness (6) → ... → remaining 9 systems.
- **FR-051**: The Substrate system MUST run after Territory and before Production on every tick, providing the physical-stock values that Production consumes.
- **FR-052**: Production MUST consume the just-computed Substrate values (not stale prior-tick values).
- **FR-053**: The five Vol I/II/III economic flow stages execute at two pipeline locations within the 15-system order, not in a single contiguous block:
  1. **Production** runs at slot 3 (hex-local; consumes Substrate output from slot 2.5; FR-026/FR-027).
  2. **Solidarity** at slot 4 operates on independent consciousness state and is NOT a flow stage; it intervenes between Production and the next four flow stages by design.
  3. The remaining four flow stages execute as **sequential sub-stages within slot 5** in the strict order: **(5a) Imperial Rent inflow → (5b) Vol II Circulation → (5c) Vol III Equalization → (5d) Vol III Distribution**. Each sub-stage's outputs are the next sub-stage's inputs; no other system intervenes between them.
  4. Implementations MAY register slot 5 either as one composite `ImperialRentSystem` with four internal phases or as four sibling systems registered at 5a–5d; both satisfy this requirement.

### Key Entities

- **HexResolutionLevel**: Enumeration `{res_7, res_6, res_5}` distinguishing the three hex aggregation levels.
- **ScaleLevel**: Enumeration `{hex_7, hex_6, hex_5, county, state, region, national, international}`. The lookup hierarchy by which any quantity may be aggregated.
- **DynamicHexState**: The persisted per-hex-per-tick state, including c, v, s, K (capital stock), biocapacity stocks, internet access, and surveillance coupling. Source of truth at hex resolution 7 only.
- **ImmutableReferenceSeries**: A year-indexed annual series in Postgres copied from SQLite at initialization, e.g., BEA I-O coefficients, MELT τ, ERDI, basket visibility γ, Hickel drain, Ricci unequal exchange, EIA energy, USGS minerals, FCC broadband, FAF freight.
- **CoefficientLookupPolicy**: Per-series classification `{slowly_varying, event_discrete}` determining whether linear interpolation or step-function lookup applies across the 52 weeks of each year.
- **ExternalNode**: A world-region node (China, EU, India, etc.) sitting in the runtime graph with country-aggregate state but no internal hex structure.
- **BoundaryEdge**: An edge between an internal node and an external node, classified as `trade_edge` (bidirectional) or `drain_edge` (directional periphery → core).
- **BoundaryFlowRegisterRow**: An append-only record of a single cross-boundary flow with fields `(tick, source_hex_or_node, dest_hex_or_node, flow_type, magnitude)`.
- **ConservationAuditRow**: An append-only audit record `(tick, scale, invariant_name, computed_value, expected_value, residual, severity)` produced once per (tick, scale, invariant) combination.
- **PipelineOrdering**: The fixed 15-system ordering with Substrate inserted at position 2.5.
- **FlowSequence**: The fixed five-stage economic flow ordering: Production → ImperialRent → Circulation → Equalization → Distribution within the materialist pipeline slot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After initialization at any supported `start_year`, the SQLite reference database may be made inaccessible (renamed or unreadable) and the simulation MUST complete a full configured-length run (up to 780 ticks for Detroit) with zero read errors against that database.
- **SC-002**: For any tick `t` and any quantity in `{c, v, s, K, biocapacity}`, the absolute residual between the engine's reported aggregate at any scale and an independent hex-level sum MUST be `≤ 1e-10`.
- **SC-003**: A 780-tick simulation MUST complete within a wall-time budget of 60 minutes on the standard development workstation (i.e., the per-tick cost must average ≤ ~4.6 seconds).
- **SC-004**: For 100% of conservation invariants evaluated on a clean baseline scenario, the audit log row MUST be tagged `severity='ok'`.
- **SC-005**: Across a 780-tick simulation, the audit log MUST contain at least one row per (tick, scale, invariant) combination, totaling no fewer than `780 × (4 quantities × 4 scales + global Φ invariant per year)` rows.
- **SC-006**: When a deliberate per-tick conservation defect of magnitude ≥ 1e-6 is injected, the first audit row tagged `severity='alarm'` MUST occur within ≤ 1 tick of the defect injection and MUST identify the correct quantity and scale.
- **SC-007**: For a slowly-varying reference series with `v(y)=A` and `v(y+1)=B`, the engine's reported active value at the midpoint of year `y` (tick `start_year_tick_0 + 26`) MUST equal `0.5 × (A + B)` to within floating-point tolerance.
- **SC-008**: For an event-discrete reference series, the engine's reported active value at tick `52` MUST equal exactly `v(start_year + 1)`, not the linear blend.
- **SC-009**: The geometric weekly depreciation invariant `(1 − δ_weekly)^52 ≈ 1 − δ_annual` MUST hold to within floating-point tolerance for the canonical `δ_annual = 0.07`.
- **SC-010**: After one full simulated year (52 ticks), cumulative Φ inflow recorded in the Boundary Flow Register from any single external node MUST equal that node's `Φ_year` from the active reference row, to within `ε = 1e-10`.
- **SC-011**: For any single tick of a baseline scenario, the per-stage conservation property MUST hold: Production grows v+s by exactly the new labor-derived increment; Circulation preserves sum(v) in study area modulo boundary; Equalization preserves per-industry sum(c); Distribution preserves s as p+i+r+t.
- **SC-012**: A query "What is the total surplus value extracted in `<any county>` at tick `<t>`?" MUST return a value identical to the independent offline sum of hex-level surplus values mapped to that county at that tick, with zero stored aggregate rows involved.
- **SC-013**: The pipeline ordering for any tick MUST be deterministic and reproducible: two runs of an identical seed MUST produce identical sequences of system invocations and identical hex-level state at every tick.
- **SC-014**: The conservation audit log MUST be append-only: no existing row may be modified or deleted by runtime tick logic, verifiable by replaying the log against the dynamic state evolution.
- **SC-015**: For the Detroit 2010–2025 scenario specifically (780 ticks, ~1700 study-area hexes, **9 external nodes** = 8 international + 1 Rest-of-USA per the Canada amendment to FR-036), the boundary flow register MUST remain queryable for tick-scoped or hex-scoped slices in the single-second range after the full run completes.

## Assumptions

- **Tick definition**: A tick represents exactly one calendar week (52 ticks per simulated year). This is fixed for this feature and not configurable.
- **Reference data window**: The SQLite reference database is assumed to cover at least the full simulation window. For Detroit 2010–2025 specifically, all required series (QCEW, BEA county GDP, BEA I-O coefficients, EIA energy, USGS minerals, FCC broadband, Hickel, Ricci, FAF) are assumed available; integration with Comtrade is in scope to the extent existing CSVs cover.
- **Depreciation rate**: The canonical annual depreciation rate `δ_annual = 0.07` (from existing `GameDefines`) is used unless overridden; the geometric weekly conversion is applied universally for all capital-stock and biocapacity perpetual-inventory updates.
- **Industry-share derivation**: Per-industry capital allocation at any hex is derived on read from QCEW employment shares applied to hex-aggregated c/v/s. Per-(hex, industry) c/v/s is not stored as primary state.
- **Single Rest-of-USA node**: All sub-national flows that exit the tri-county study area are absorbed into a single "rest-of-USA" boundary node in v1. Future specs may split this into Chicago / Tennessee / California / etc. as required by the modeling fidelity needed.
- **Sub-week crisis aggregation**: Crisis dynamics that resolve faster than one week (e.g., a 3-day financial panic) are aggregated into a single tick's coefficient reset; sub-tick temporal resolution is not modeled.
- **Interpolation default**: Slowly-varying reference series default to linear interpolation across 52 weeks; event-discrete series default to step-function lookup at year boundaries. The classification is per-series and recorded as configuration.
- **Boundary register growth**: At ~12,000 rows per tick (boundary edges × tick events) for the Detroit scenario, ~10M rows over 780 ticks is acceptable storage; future specs may introduce archival/compaction policies.
- **External-node set extensibility**: The initial **eight** international world-region external nodes (China, EU, India, Sub-Saharan Africa, Latin America, Russia/CSI, Southeast Asia, Canada) plus the single Rest-of-USA domestic node — **nine external nodes total** — are the v1 starting point per the Canada amendment to FR-036. Per-spec extensions may add or split regions; this v1 fixes the nine as the minimum.
- **No SQLite reads at runtime**: Reads against the SQLite reference database during any runtime tick are an architectural violation. The audit log will not enforce this directly, but the test harness MUST verify it.
- **Audit log durability**: Audit log rows are synchronously committed inside the per-tick transaction (see FR-008a). On clean shutdown or crash, every committed tick has a complete audit-log set; no committed tick has missing audit rows.
- **Initialization is single-threaded**: The initialization phase is assumed serial; concurrent initialization of multiple sessions is not required for this feature.
- **Federal data year resolution**: Per-week disaggregation of annual federal data uses uniform 1/52 distribution unless an explicit seasonal pattern is present in the source. No seasonal patterns are fabricated.

## Out of Scope

- The substrate ledger's internal accounting (what physical-stock fields it tracks, how it computes price equivalents): tracked separately and integrated into Position 2.5 by reference.
- Per-(hex, industry) primary state storage: explicitly rejected; industry breakdown is derived on read.
- Sub-tick temporal resolution: out of scope; sub-week dynamics are aggregated into single ticks.
- Real-time refresh of federal reference data during play: out of scope; runtime is Postgres-only.
- Optimization of the boundary flow register beyond reasonable queryability for the Detroit scenario: future spec.
- UI / dashboard changes consuming the new aggregation views: out of scope (covered by separate UI specs).
- Mid-session change of `start_year`: out of scope; `start_year` is fixed at session creation.
- Splitting the Rest-of-USA node into sub-regions: out of scope for v1; honest single-boundary approach.
- Bilateral trade data loading beyond what existing Hickel/Ricci/Comtrade CSVs provide: tracked as a separate data-onboarding spec.

## Dependencies

- **Spec 037 (Postgres Runtime Database)**: Provides the Postgres connection pool, schema migration tooling, and `dynamic_*` / `immutable_reference_*` table family conventions. Hard prerequisite.
- **Spec 057 (Leontief Imperial Rent Integration)**: Provides the BEA I-O production-chain rent decomposition used to compute Φ from ERDI-adjusted import shares. Hard prerequisite for FR-034 and User Story 6.
- **Spec 060 (Value-Form Invariants)**: Provides the c/v/s value-form algebraic invariants the per-stage conservation checks rely on. Hard prerequisite for FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, and the conservation audit log entries.
- **Spec 053 (Conservation Invariants)** / **Spec 054 (Bound Invariants)** / **Spec 055 (Topology Invariants)** / **Spec 056 (Causal Invariants)**: Provide the Hypothesis-based property testing harness used to validate cross-scale conservation in test suites. Hard prerequisites for the test design.
- **Spec 011 (Fundamental Tensor Primitive)** / **Spec 013 (MELT, Basket, Visibility)** / **Spec 015 (Gamma Visibility Tensor)** / **Spec 016 (Class Dynamics Engine)** / **Spec 017 (Simulation Tick Dynamics)** / **Spec 018 (Crisis & Devaluation Mechanics)**: Provide ValueTensor4x3, MELT τ, basket visibility γ, class position classifier, imperial rent calculator, and tick-dynamics primitives the initialization phase uses. Hard prerequisites for User Story 1 initialization.
- **Spec 022 (Hypergraph Community Layer)** / **Spec 029 (Community Hyperedge Upgrade)**: Provide XGI hypergraph hydration semantics from Postgres dynamic tables.
- **Spec 020 (Detroit Vertical Slice)**: Provides the Detroit 2010–2025 test scenario this feature is calibrated against and that all SC-* criteria reference.
- **ADR032 (Materialist Causality System Order)**: Defines the 15-system pipeline ordering that FR-050 extends with the new position 2.5 substrate slot.
- **Existing `HexGrid` / `HexEqualizationComputer` / `BoundaryFlowRegister` / `InterpolatingBEASource`**: Existing codebase components that this feature extends (does not replace).
- **PostgreSQL extensions PostGIS, pgvector, uuid-ossp**: Required by FR-007, FR-024 (PostGIS for spatial join queries on hex geometries; the others already in use).
