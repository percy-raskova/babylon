# Phase 0: Research — Engine-Bridging

**Feature**: 065-engine-bridging
**Date**: 2026-05-15

This document resolves the open implementation questions surfaced by
the Technical Context, Constitution Check, and Risks sections of
`plan.md`. Each section follows the canonical pattern: **Decision** /
**Rationale** / **Alternatives considered**.

---

## R1: Per-tick wallclock at engine-bridged fidelity (SC-002 risk)

**Open question**: The MVP runner's per-tick cost is 3 µs (literal
no-op). Real engine systems execute the full
`SimulationEngine.systems` list (~15 systems per tick at the time of
this writing). Will the per-tick cost stay under the 1.15 s budget
implied by SC-002 (520 ticks / 600 s) for Michigan-statewide scope (83
counties × ~30 000 hex cells)?

**Decision**: **Profile-then-bridge**. The bridge ships with whatever
per-tick cost the existing engine systems produce. We do NOT
pre-emptively optimize. We DO measure and emit per-system wallclock
into `summary.performance.per_system_ms` (extension to the existing
`performance` block — does not break SC-010 since `performance` is
already an object and we're adding an internal sub-key).

If the canonical run blows SC-002, we have three pre-staged escalations
documented in this section, applied in order until budget holds:

1. **Per-county loop fusion** in the hottest system: many systems
   currently iterate `for entity in state.entities` with a single-pass
   loop body. Refactor to fuse mathematical steps within one pass.
   Touches engine internals — out of THIS spec's scope; would file
   a follow-up spec.
2. **Reduce hex resolution effective scope** by aggregating to county
   at engine read time (existing `view_runtime_trace_emission` already
   does this for emission). Means engine systems operate on
   county-resolution `WorldState` instead of hex-resolution. Faithful
   to spec-064's contract (county-aggregate trace.csv) but loses the
   hex-level state that future specs might need.
3. **Reduce default `--ticks`** from 520 to a smaller multiple of 52
   (e.g., 260 = 5 years) for the canonical mise task. Operator opt-in
   for longer runs. Last resort; degrades the "10 years of real data"
   contract from the user.

**Rationale**:
- We have no empirical engine-bridged measurement yet. Speculating on
  the budget is engineering theater.
- The existing `SimulationEngine.run_tick()` is already optimized as a
  unit (operates on a single `WorldState`); the cost is dominated by
  the systems themselves, not the orchestration.
- All three escalation paths preserve SC-010 (artifact contract
  unchanged) and SC-003 (determinism).

**Alternatives considered**:
- *Pre-optimize before bridging*: rejected. The engine systems are
  already in active use under `pytest`; whatever per-tick cost they
  carry there is the cost we'll inherit. Optimizing without
  measurement risks chasing the wrong bottleneck.
- *Cache `WorldState` across N ticks, only resync periodically*:
  rejected. Violates the spec-062 PerTickTransactionEnvelope contract
  (every tick is a transactional unit); creates a window of
  inconsistency between Postgres and the in-memory engine.

**Verification**: `tests/integration/test_engine_bridge.py::test_engine_bridged_wallclock_budget`
asserts the 520-tick canonical run completes in ≤ 600 s tick-loop on
the dev reference machine.

---

## R2: Hex hydrator formula for `c` (constant capital) from BEA + QCEW

**Open question**: FR-002 requires tick-0 `c` (constant capital
consumed per tick) to derive from real reference data, not from
`c = 2v`. SQLite has `fact_bea_county_gdp` (annual GDP per county)
and `fact_bea_io_coefficient` (national-level input-output
coefficients per industry). What's the formula?

**Decision**: **`c_county = GDP_county × intermediate_inputs_fraction
× (1/52)`**, where:
- `GDP_county` = `fact_bea_county_gdp.gdp_millions × 1e6` for the
  requested `start_year` and `county_id`.
- `intermediate_inputs_fraction` =
  `SUM(fact_bea_national_industry.intermediate_inputs_millions) /
  SUM(fact_bea_national_industry.gross_output_millions)` aggregated
  over all industries for the requested `start_year`. This is the
  national-level c/(c+v+s) ratio.
- `(1/52)` converts annual to weekly.

Cross-check: `c + v` should approximate intermediate consumption plus
wages. Anchor: `c / v` should be within `[0.5, 5.0]` per Michigan
county (the national average organic composition of capital is
roughly 2:1 for 2010; rural ag counties skew lower, manufacturing-
intensive counties skew higher).

**Rationale**:
- BEA county GDP is the most direct measure of county-level
  production.
- The national I/O intermediate-inputs fraction is the canonical
  c/output ratio (the entry-point for Marx's `c = constant capital
  consumed`).
- Allocating national fractions to county scale is standard in
  regional economic accounting; we lose intra-Michigan variation in
  organic composition but the magnitude is right.
- Refining to per-industry county breakdowns (using `fact_qcew_annual`
  employment shares by NAICS) is a future-spec optimization; the
  national fraction is good enough for tick-0 seeding.

**Alternatives considered**:
- *Use county-level I/O coefficients directly*: no such table exists
  at county resolution in the data catalog; would require manual
  imputation.
- *Derive `c` from energy consumption * fuel price*: requires energy
  consumption per county data; coverage is sparse in the existing
  SQLite tables.
- *Keep `c = 2 × v` (current placeholder)*: rejected, violates FR-002a
  and SC-005 / FR-002b.

**Verification**: `tests/integration/test_hex_hydrator_real_data.py::test_c_v_ratio_within_plausible_band`
samples 5 Michigan counties at `start_year = 2010` and asserts
`0.5 ≤ c / v ≤ 5.0`.

---

## R3: WorldState hydration round-trip cost reduction

**Open question**: Each tick, the bridge needs to (a) read the
previous tick's state from Postgres into a Pydantic `WorldState`,
(b) invoke `engine.run_tick(graph, services, context)`,
(c) write the delta back. If full re-hydration is O(N counties + M
hexes), the bridge cost dwarfs the engine cost. Can we partial-hydrate?

**Decision**: **Full WorldState hydration once at session init;
delta-based updates per tick**. Specifically:

- At session init, after the upgraded hex hydrator writes tick 0,
  build the initial in-memory `WorldState` from Postgres ONCE.
- Each tick: invoke `engine.run_tick(graph, services, context)` on
  the in-memory `WorldState`. The engine systems mutate the graph
  in-place (existing II.11-compliant per-subsystem mutations).
- After each tick: serialize the *changed* subset of `WorldState`
  into a `PerTickTransactionEnvelope` and persist via
  `runtime.persist_tick_atomic(envelope)`.
- The in-memory `WorldState` is the source of truth between ticks;
  Postgres is the durability layer.

The trace view (`view_runtime_trace_emission`) reads from Postgres,
not the in-memory `WorldState`, so trace.csv emission still respects
II.11 (cross-subsystem read via declared interface).

**Rationale**:
- Hydration cost is paid ONCE (~31.5 s per MVP measurement). Per-tick
  cost becomes pure engine-systems + delta-persist, no hydration.
- The in-memory `WorldState` is already the engine's natural
  representation; building it from Postgres every tick would be pure
  overhead.
- Postgres remains durable: a crash mid-run can resume from the
  last-committed tick via `runtime.get_last_committed_tick()`
  (spec-062 §T070).

**Alternatives considered**:
- *Per-tick full re-hydration from Postgres*: rejected, dominates
  wallclock budget for no benefit.
- *Engine systems read/write Postgres directly (no `WorldState`)*:
  rejected, requires rewriting every engine system; massive scope
  expansion outside this spec.

**Implementation contract**: `engine/headless_runner/bridge.py`
exposes a `WorldStateBridge` class with:
- `bridge.hydrate_initial(session_id, scope_fips) → WorldState`
- `bridge.persist_tick(world: WorldState, tick: int) → PerTickTransactionEnvelope`
- `bridge.refresh_event_log() → list[EngineEvent]`

The `WorldState` is mutated in-place by engine systems between
`hydrate_initial` and the next `persist_tick`; the bridge never
re-hydrates from Postgres after session init.

---

## R4: New subsystem state tables — schema design

**Open question**: FR-006 requires per-tick subsystem state tables
for consciousness, demographics, and employment, keyed
`(session_id, tick, county_fips)`. What are the columns?

**Decision**: Three new tables; one per subsystem. All keyed
`(session_id UUID, tick INTEGER, county_fips TEXT)` with PRIMARY KEY
on the triple. Append-only enforced via REVOKE UPDATE, DELETE on
runtime role (same pattern as `conservation_audit_log` in
spec-062 §T009).

### 4.1 `dynamic_consciousness_state` (migration 0020)

Owner subsystem: **consciousness** (`ConsciousnessSystem`,
spec-034 / 043 ternary simplex).

```sql
session_id        UUID NOT NULL,
tick              INTEGER NOT NULL CHECK (tick >= 0),
county_fips       TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
p_acquiescence    DOUBLE PRECISION CHECK (p_acquiescence BETWEEN 0 AND 1),
p_revolution      DOUBLE PRECISION CHECK (p_revolution BETWEEN 0 AND 1),
ideology_r        DOUBLE PRECISION CHECK (ideology_r BETWEEN 0 AND 1),
ideology_l        DOUBLE PRECISION CHECK (ideology_l BETWEEN 0 AND 1),
ideology_f        DOUBLE PRECISION CHECK (ideology_f BETWEEN 0 AND 1),
-- US3 simplex invariant: r + l + f ≈ 1.0 (within ±1e-9). Enforced by
-- the engine system; not a DB CHECK because float drift may exceed CHECK tolerance.
PRIMARY KEY (session_id, tick, county_fips)
```

### 4.2 `dynamic_demographics_state` (migration 0021)

Owner subsystem: **demographics** (new conceptual subsystem; the
in-engine demographic state lives on the SocialClass entities, but
the per-tick aggregate to county lives here).

```sql
session_id        UUID NOT NULL,
tick              INTEGER NOT NULL CHECK (tick >= 0),
county_fips       TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
population        BIGINT NOT NULL CHECK (population >= 0),
PRIMARY KEY (session_id, tick, county_fips)
```

### 4.3 `dynamic_employment_state` (migration 0022)

Owner subsystem: **employment** (read from QCEW interpolated; written
by ImperialRentSystem after wage extraction).

```sql
session_id          UUID NOT NULL,
tick                INTEGER NOT NULL CHECK (tick >= 0),
county_fips         TEXT NOT NULL CHECK (county_fips ~ '^\d{5}$'),
employment_proxy    DOUBLE PRECISION NOT NULL CHECK (employment_proxy >= 0),
PRIMARY KEY (session_id, tick, county_fips)
```

### 4.4 Migration 0023 — recreate `view_runtime_trace_emission`

Drops the spec-064 v1 view and recreates it with LEFT JOINs to all
three new subsystem tables. Column ordering and names remain
identical to the spec-064 trace_csv_schema.yaml contract; the
view's columns simply stop being NULL.

**Rationale**:
- One table per subsystem per II.11; the view is the union/projection.
- All three tables have the same key shape (session_id, tick, fips),
  which keeps the view's JOINs simple and the spec-064 schema-parity
  test extensible.
- The `r + l + f = 1` simplex invariant is enforced by the engine
  (US3 invariant), not by the DB, because float drift in serialization
  may exceed any reasonable CHECK tolerance.

**Alternatives considered**:
- *One mega-table `dynamic_county_state`*: rejected per Complexity
  Tracking — violates II.11.
- *Hex-resolution tables for consciousness/demographics/employment*:
  rejected. These quantities are county-aggregate by nature (you don't
  have per-hex population from Census; you have block-group population
  imputed up). Hex aggregation would multiply storage 360× without
  added information.
- *Skip the DB CHECK on `[0, 1]` ranges for probabilities*: rejected.
  The engine's `Probability` constrained type already guarantees this
  range; the DB CHECK is defense-in-depth at the persistence boundary.

---

## R5: Event capture from EventBus → summary.json

**Open question**: FR-017 requires `summary.json.events` to capture
every `EventType` fired during the tick loop. The engine already
emits events via `EventBus.publish(...)`. How does the bridge
subscribe?

**Decision**: New `event_capture.py` module exposes `EventCapture`,
a thin `EventBus.subscribe`-implementing object that appends a
plain-dict representation of each emitted event into an in-memory
deque keyed by tick. The bridge owns one `EventCapture` per session.

```python
class EventCapture:
    """Subscribes to EventBus; collects engine events for summary.json."""

    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._current_tick: int = 0

    def set_tick(self, tick: int) -> None:
        """Called by runner at the start of each tick."""
        self._current_tick = tick

    def on_event(self, event: BaseEvent) -> None:
        """EventBus subscriber callback. Emission order preserved (FR-018)."""
        self._buffer.append({
            "tick": self._current_tick,
            "event_type": event.event_type.value,
            "entity_ids": list(event.affected_entity_ids),
            "severity": getattr(event, "severity", "info"),
            "details": event.model_dump(exclude={"event_type", "affected_entity_ids"}),
        })

    def drain(self) -> list[dict]:
        return list(self._buffer)
```

The runner's tick loop:
1. `event_capture.set_tick(tick)` at start of tick
2. `engine.run_tick(...)` — engine systems fire `EventBus.publish(...)` calls; `EventCapture.on_event` receives them in emission order
3. After tick commit, the captured events stay in the buffer
4. At end of run, `event_capture.drain()` becomes `summary.events`

**Rationale**:
- The `EventBus` is already a publish/subscribe surface; we just need
  one more subscriber.
- Capturing event payloads via `model_dump(exclude={...})` preserves
  whatever event-specific fields exist without coupling the capture
  module to the full `EventType` enumeration.
- FR-018's emission-order rule (Q4) holds naturally because
  `EventBus.publish` is synchronous and we append in publish order.

**Alternatives considered**:
- *Post-tick scan of `conservation_audit_log` for events*: rejected.
  Audit log is conservation-specific, not the general event stream.
- *Persist events to a new Postgres table and re-read at end*:
  rejected. Events are small (≤ 1000 per run typically), don't need
  Postgres durability, and persisting to DB would add a per-tick
  write hop for no benefit. In-memory deque is sufficient.

**Implementation note**: `affected_entity_ids` field is sourced from
each event's payload. Different event types expose different fields
(`SuperwageCrisisEvent.affected_class_id`, `UprisingEvent.county_fips`,
etc.). The capture module reads via `getattr` with a documented
fallback list of candidate attribute names; if no recognized
attribute exists, `entity_ids` is an empty list.

---

## R6: EndgameDetector entry point wiring

**Open question**: FR-015 / FR-016 require the runner to poll an
`EndgameDetector` at the end of each tick. Spec-064 defined the
observer protocol but deferred wiring (T024a + T033). The
`--endgame-detector` CLI flag (per A5) accepts a string; how does
that string become an object?

**Decision**: **Entry-point name dispatch via `importlib`**. The
`--endgame-detector` flag accepts a dotted path like
`babylon.engine.observer.ImperialCollapseDetector`. The runner
resolves it via `importlib.import_module` + `getattr`. If the
attribute is not found or doesn't implement the `EndgameDetector`
Protocol, the runner exits with `CONFIG_ERROR` (code 2).

If `--endgame-detector` is unset, no end-game detection runs — the
loop goes to `--ticks`. This matches A5 (default = "no detector",
preserving spec-064 baseline).

**Rationale**:
- Mirrors the standard Python entry-point pattern used by pytest
  plugins, setuptools entry points, etc.
- No new CLI flag formats to learn.
- Detectors implementing the Protocol can live anywhere in the
  package tree; the operator decides which one fires.
- Test-time injection (US4 acceptance: "inject an EndgameDetector
  that fires at tick 250") works via a test-local detector class
  registered as `tests.integration.fixtures.endgame.TestDetector`.

**Alternatives considered**:
- *Hardcoded detector list*: rejected — couples the runner to specific
  detector classes; reduces test injectability.
- *Plugin auto-discovery via setuptools entry_points*: overkill for
  this spec; adds packaging surface area.

---

## R7: Hex hydrator real-data formula table (FR-002a)

**Open question**: FR-002a says the upgraded hex hydrator reads from
specific SQLite tables; what's the per-column source/formula?

**Decision**: Per-column source matrix (committed to
`contracts/hex_hydrator_input.yaml` in Phase 1):

| Trace column | Source(s) | Formula |
|---|---|---|
| `v` | `fact_qcew_annual` | `SUM(total_wages) / 52` over all industries for `(county_id, start_year)` |
| `c` | `fact_bea_county_gdp` + `fact_bea_national_industry` | (R2 above) `(GDP_county × intermediate_inputs_fraction) / 52` |
| `s` | (derived) | `(GDP_county / 52) − v − c`; clamped to non-negative; falls back to `0` on negative residuals (which is a data anomaly flagged by audit) |
| `k` | (perpetual-inventory carry-forward) | At tick 0: `k = capital_output_ratio × GDP_county`, with `capital_output_ratio = 3.0` (national average for 2010 per BEA fixed-asset accounts). Refined per spec-021. |
| `surveillance_coupling` | `fact_broadband_coverage` + `fact_coercive_infrastructure` | spec-063 coupling formula: `0.3 + 0.4 × broadband.pct_100_20 + 0.3 × coercive.facility_count_normalized` |
| `internet_access_pct` | `fact_broadband_coverage` | Direct: `pct_25_3` (FCC 25/3 Mbps threshold; standard broadband definition) |
| `biocapacity_stock` | `fact_hickel_erdi_annual` + county area | National biocapacity × county_land_area / national_land_area |
| `energy_stock` | `fact_state_minerals` + county energy share | State-level energy production allocated by county population share |
| `raw_material_stock` | `fact_state_minerals` (non-energy commodities) | State-level non-fuel mineral production allocated by county area share |
| `population` | `fact_census_*` (median income table has total_households; use ACS tables in dim_county) | County-level Census population for the year |
| `employment_proxy` | `fact_qcew_annual` | `SUM(employment) over all industries for (county_id, start_year)` |
| `p_acquiescence` | (engine-computed at tick 0) | `Sigmoid(v − subsistence_threshold)` per spec-001 survival calculus |
| `p_revolution` | (engine-computed at tick 0) | `Organization / Repression` per spec-001 |
| `ideology_r/l/f` | (engine-computed at tick 0) | Initialized to ternary midpoint `(1/3, 1/3, 1/3)` for all counties; subsequent ticks evolve via ConsciousnessSystem |

**Rationale**:
- Every formula traces to a material relation (Constitution III.8
  Aleksandrov Test).
- Where the formula's inputs are unambiguous (`v` from QCEW, `c` from
  BEA), the value is direct. Where the formula requires apportionment
  (energy from state to county), we use the simplest defensible
  weighting (population share or area share, documented per column).
- Engine-computed columns (`p_acquiescence`, `p_revolution`, ideology)
  are NOT seeded from data — they emerge from initial economic state
  + engine math at tick 0. This preserves the existing engine system
  contracts (don't pre-bake state the engine is supposed to compute).

**Alternatives considered**:
- *Skip apportionment; emit NULL for state-level metrics*: rejected,
  violates SC-001 (zero empty cells).
- *Use richer apportionment models (econometric, gravity-weighted)*:
  rejected for MVP scope. The current per-county weighting is the
  simplest correct floor; refinements are future-spec.

---

## R8: tools/shared.run_simulation surface restoration (SC-011)

**Open question**: Q5 resolved that `final_state` carries the
terminal-tick `WorldState`. Spec-064 currently returns
`final_state = None` and `phase_milestones = {all None}` etc. What
else needs restoration?

**Decision**: All seven legacy result-dict fields are restored to
meaningful values:

| Field | Current MVP value | Engine-bridged value | Source |
|---|---|---|---|
| `ticks_survived` | `ticks_completed` (no change) | Same | `result.ticks_completed` |
| `max_tension` | `0.0` | Maximum `relationship.tension` over all EXPLOITATION edges over all ticks | Tracked by `event_capture` (extension) |
| `outcome` | "SURVIVED" / "DIED" via `ExitReason` | Same logic but accurate | `result.exit_reason` |
| `final_wealth` | `0.0` | Sum of `state.entities[*].wealth` at terminal tick | `final_state.entities` |
| `final_state` | `None` | Terminal-tick `WorldState` | Bridge's last in-memory snapshot |
| `phase_milestones` | `{all None}` | Per-phase tick numbers from EventCapture | Filtered from `events` array |
| `terminal_outcome` | `None` | `"revolution"` / `"genocide"` / `None` from `TerminalDecision` event | Filtered from `events` array |

**Rationale**:
- The bridge already builds the data; not exposing it through
  `shared.run_simulation` would be wasteful and would block tools
  that need it (`audit_simulation.py`, `tune_agent.py`).
- All fields read from existing in-memory state; no new bookkeeping
  beyond what the bridge already does.

**Alternatives considered**:
- *Restore only `final_state`, keep the rest as None*: rejected. The
  user explicitly resolved Q5 to "full fidelity"; partial restoration
  would be inconsistent.

---

## R9: SC-002 wallclock baseline measurement plan

**Open question**: How do we measure the canonical 520-tick Michigan
run's tick-loop wallclock to verify SC-002 holds?

**Decision**: **Three measurement passes**:

1. **Tri-county smoke (1 tick + 5 ticks)** — confirms the bridge
   works end-to-end at small scope. Establishes per-tick cost
   floor.
2. **Tri-county full (520 ticks)** — confirms per-tick cost is
   stable across tick numbers (no compounding overhead).
3. **Michigan-statewide full (520 ticks)** — the SC-002 acceptance
   measurement. Asserts `tick_loop_sec ≤ 600`.

Each measurement writes `summary.performance.per_system_ms` (new
sub-key — see Phase 1). If pass 3 fails the budget, R1's escalation
ladder applies.

Test harness: `tests/integration/test_engine_bridge.py::test_canonical_wallclock_budget`,
gated on `BABYLON_TEST_PG_DSN` + `BABYLON_SLOW_TESTS=1`.

**Rationale**:
- Three passes catch three failure modes: (a) bridge correctness at
  small scope, (b) per-tick cost compounding, (c) Michigan-scale
  budget violation.
- All three runs reuse the same canonical seed (2010) so
  determinism is verifiable across the three passes.

**Alternatives considered**:
- *Only run Michigan-scale*: rejected. If it fails, we don't know
  whether the bug is at small scope (failing fast on tri-county would
  catch it cheaper) or compounding (failing fast on full tri-county
  would catch it).
- *Profile via cProfile and aggregate*: useful but additive, not
  primary. cProfile is exposed via `tools/profiler.py` for operators
  who want flamegraph-level detail; the integration test just asserts
  the budget.

---

## R10: WorldState ↔ subsystem state reconciliation (post-foundation gap)

**Open question** (surfaced during Phase 1+2 implementation review, 2026-05-15):
The spec's `contracts/subsystem_state_tables.yaml` and `tasks.md` T037–T039
prescribed `source_engine_value` paths that do not exist on the current
`WorldState`:

- `world.consciousness_simplex[county_fips]` — no such field
- `world.demographics_per_county[county_fips]` — no such field
- `world.employment_per_county[county_fips]` — no such field
- `state.entities[county_fips]` — `WorldState.entities` is `dict[str, SocialClass]`
  where the `SocialClass.id` validator pattern is `^C[0-9]{3}$`
  (e.g., `"C001"`), NOT a 5-digit FIPS code

Verified by `WorldState.model_fields.keys()`:
```
contradiction_frames, economy, entities, event_log, events,
industries, institution_relations, institutions, key_figures,
organizations, relationships, state_finances, territories, tick
```

Additionally:
- `TernaryConsciousness(r, l, f)` exists as a Pydantic model in
  `babylon.models.entities.consciousness`, but it is attached to
  `CommunityState`, which is itself NOT a top-level WorldState
  field — communities are stored hypergraph-side (Feature 022/029),
  not on WorldState directly.
- `SocialClass.ideology` is an `IdeologicalProfile`
  (`class_consciousness`, `national_identity`, `agitation`) — the
  legacy dual-axis model from Sprint 3.4.3 (George Jackson refactor),
  NOT a `TernaryConsciousness`.
- Per-county `population` and `employment` are not WorldState fields
  at all. Population exists per-`SocialClass` ("block size", line 368
  of `models/entities/social_class.py`) and per-`Territory`
  ("human shield count", line 112 of `models/entities/territory.py`),
  but neither is county-indexed.

**Decision**: The bridge is a **derivation/aggregation adapter**, not a
flat field-by-field WorldState→table serializer. The 5 previously-NULL
columns flow from these sources:

| Column | Source kind | Concrete derivation |
|---|---|---|
| `population` | reference data | SQLite `fact_census_*` for `(county_fips, year)` interpolated to weekly per spec-062 year-scoped policy. Fall back to `fact_qcew_annual.employment × 2.5` if Census missing for that county-year (with audit row warning). |
| `employment_proxy` | reference data | `SUM(fact_qcew_annual.employment) / 52` for `(county_fips, year)`. Same source as hex `v`. |
| `p_acquiescence` | engine-computed → aggregated | Population-weighted mean of `entity.p_acquiescence` over `entities` where `entity.county_fips == fips`. |
| `p_revolution` | engine-computed → aggregated | Population-weighted mean of `entity.p_revolution` over `entities` where `entity.county_fips == fips`. |
| `ideology_r`, `ideology_l`, `ideology_f` | engine-computed → mapped → aggregated | For each entity in the county: apply the **bridge mapping** below to convert `IdeologicalProfile → (r, l, f)`. Then population-weighted average per county. |

**Bridge mapping (IdeologicalProfile → TernaryConsciousness)**:

```
r = class_consciousness × (1 - national_identity)
f = national_identity × (1 - class_consciousness)
l = max(0, 1 - r - f)
```

Properties of this mapping (verified algebraically):
- `r + l + f = 1` by construction (l is the remainder).
- All three are in `[0, 1]` (both `cc` and `ni` are `Probability` ∈ [0, 1],
  products are in [0, 1], `r + f ≤ 1` so `l ≥ 0`).
- The corners of `(cc, ni)` map to the corners of the simplex:
  - `(1, 0)` → `(r=1, l=0, f=0)` — pure revolutionary (class-conscious + internationalist)
  - `(0, 1)` → `(r=0, l=0, f=1)` — pure fascist (false-conscious + nativist)
  - `(0, 0)` → `(r=0, l=1, f=0)` — pure liberal (no class consciousness, no nativism)
  - `(0.5, 0.5)` → `(r=0.25, l=0.5, f=0.25)` — Jackson's "liberal hegemony" midpoint
  - `(1, 1)` → `(r=0, l=0, f=0)` then l=1 — degenerate (a "national revolutionary"
    is ambiguous; conventionally we route to liberal). Documented as edge case;
    the audit row emits a `warning` severity when an entity hits this corner.

This is the spec-065 bridge convention; it is NOT the spec-034 native
`compute_ternary_consciousness(community_type, org_landscape, substrate_floor)`
computation. Spec-034's native computation requires per-community
organizational landscapes which are not yet wired to per-county output;
that upgrade is deferred to a future spec. The mapping above is the
minimal-invasive route that produces real, non-uniform, simplex-valid
`(r, l, f)` from existing per-entity `IdeologicalProfile` state.

**Schema change required**: `SocialClass.county_fips: str | None = None`.

This is the **only** WorldState-side change for spec-065. Rationale:

- Optional, defaults to `None` — every existing test that doesn't care
  about county attribution continues to pass without modification.
- 5-digit FIPS pattern is documented in the field's `description` and
  validated by a regex if non-None.
- The factories (`create_proletariat`, `create_bourgeoisie`) gain an
  optional `county_fips` keyword that runs are free to pass.
- Spec-064 MVP creates a single set of entities for the whole scope;
  spec-065 Phase 3 will create per-county entity sets (one proletariat
  + one bourgeoisie per county_fips) and tag them with the FIPS code.
- The aggregation step in `bridge.persist_tick` iterates
  `world.entities.values()`, filters by `entity.county_fips == fips`,
  and computes population-weighted means.

**Why this resolution (vs. add `world.county_subsystem_state: dict[str, …]`)**:

- The proposed dict would be **derived state**, not authoritative state.
  Adding derived state to WorldState breaks Constitution II.6 (State
  is Data, Engine is Transformation) — derived values belong on
  computed views (which is exactly what `view_runtime_trace_emission`
  is).
- Per-county aggregates have one canonical home: the trace view.
  They're materialized into the subsystem tables at `persist_tick`,
  read back via the view, and never re-read from WorldState by any
  engine system. Storing them on WorldState would duplicate data and
  invite drift between engine state and derived rollups.
- A single new `county_fips` field on SocialClass is a 3-line schema
  change with default `None`; the alternative would be a new top-level
  Pydantic model + dict field on WorldState (10+ lines, plus
  `to_graph`/`from_graph` serialization updates, plus a derived-state
  rule violation).

**Rationale**:
- The spec's high-level goal — "every column populated with real,
  tick-varying values" — is satisfied. `population` and
  `employment_proxy` come from real reference data (same source as
  hex `v`). `p_acquiescence`, `p_revolution`, and ideology r/l/f come
  from real per-entity engine state aggregated per county.
- The single `county_fips` field is the minimum invasive change
  needed to make per-entity state attributable per county.
- The bridge mapping for ideology is documented, deterministic,
  simplex-preserving, and uses only data already in `IdeologicalProfile`.

**Alternatives considered**:

- *Add `world.consciousness_simplex: dict[str, TernaryConsciousness]`,
  `world.demographics_per_county`, `world.employment_per_county` as
  the spec originally prescribed* — rejected. Per-county aggregates
  are derived state; storing them on WorldState violates II.6 and
  invites drift. The trace view already serves as the canonical
  derived-rollup interface.
- *Treat each county as a single SocialClass with id == FIPS code,
  relaxing the `^C[0-9]{3}$` pattern* — rejected. Pattern relaxation
  is a broader schema change; the optional `county_fips` field is
  surgical. Also, distinct entities per role (proletariat,
  bourgeoisie, etc.) per county is the natural model and preserves
  the existing per-role distinctions that engine systems already use.
- *Use spec-034's `compute_ternary_consciousness` from organizational
  landscapes* — rejected for MVP scope. Organizations are not yet
  attributed per county; that wiring is bigger than spec-065 should
  swallow. The bridge mapping from `IdeologicalProfile` is the
  shippable substitute.

**Implementation plan** (replaces original T037-T039 scope; tracked in
the updated `tasks.md`):

- **T037a** (new): Add `county_fips: str | None = None` field to
  `SocialClass` with optional pattern validation. Migrate factories
  to accept the field as an optional kwarg.
- **T037b** (new): Implement
  `babylon.persistence.county_aggregation.aggregate_survival_for_county(world, fips)`
  returning `(p_acquiescence, p_revolution, total_population)` —
  population-weighted means over entities filtered by `county_fips`.
- **T037c** (new): Implement
  `babylon.persistence.county_aggregation.aggregate_consciousness_for_county(world, fips)`
  returning `TernaryConsciousness(r, l, f)` — population-weighted
  means of the bridge-mapped ideology components.
- **T038** (rewritten): Implement
  `babylon.persistence.county_aggregation.fetch_population_for_county_at_tick(runtime, fips, tick, start_year)` —
  SQLite query against `fact_census_*` with year-scoped interpolation.
- **T039** (rewritten): Implement
  `babylon.persistence.county_aggregation.fetch_employment_proxy_for_county_at_tick(runtime, fips, tick, start_year)` —
  SQLite query against `fact_qcew_annual` with `/52` weekly scaling.
- **T040** (rewritten): `WorldStateBridge.hydrate_initial` creates
  per-county entity sets tagged with `county_fips`. Tick 0 invokes
  `engine.run_tick` once to populate `p_acquiescence`, `p_revolution`,
  ideology via the existing engine systems.
- **T041** (rewritten): `WorldStateBridge.persist_tick` calls the
  four aggregator/fetcher helpers per county, assembles the three
  new envelope row-lists, and persists.

R7 (line 396-400) is partially superseded by R10. R7's claim that
"population" comes from `fact_census_*` stands. R7's claim that
"ideology_r/l/f is initialized to (1/3, 1/3, 1/3) at tick 0 and
evolves via ConsciousnessSystem" is rewritten by R10: at tick 0 the
mapping above runs against the engine-initialized `IdeologicalProfile`
defaults; in subsequent ticks the same mapping runs against engine-mutated
`IdeologicalProfile` state. There is no separate ConsciousnessSystem
producing per-county TernaryConsciousness in spec-065 scope.
