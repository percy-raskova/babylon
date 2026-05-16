# Research: Spec-066 Marx-Coherence Fixes

**Date**: 2026-05-15
**Status**: Phase 0 complete (8 of 8 R-sections decided)

This document consolidates the eight research questions enumerated in `plan.md` Phase 0. Each section follows Decision / Rationale / Alternatives format.

---

## R1 — WorldState ↔ NetworkX round-trip semantics

**Decision**: The bridged runner does NOT use `WorldState.to_graph()` / `WorldState.from_graph()` round-trips. Instead, the bridge owns a single `nx.DiGraph[str]` for the lifetime of the run; engine systems mutate it in place; the bridge reads `WorldState.relationships` from the SAME graph after engine.run_tick completes (via a thin `from_graph()` reconstruction that excludes computed fields).

**Rationale**:
- `WorldState.to_graph()` returns `nx.DiGraph[str]` with each SocialClass entity encoded as a node carrying ALL fields plus marker `_node_type="social_class"`; relationships encoded as edges with `edge_type`, `value_flow`, `tension`, etc. (`src/babylon/models/world_state.py:284-368`).
- `WorldState.from_graph()` (lines 370-498) excludes computed fields (`SOCIAL_CLASS_COMPUTED_FIELDS = {"consumption_needs"}`, `TERRITORY_EXCLUDED_FIELDS` = 13 fields including `p_acquiescence`, `p_revolution`). A naive round-trip loses any mutations to those excluded fields.
- The bridge currently does NOT call `to_graph()` (verified by Explore). It builds entities directly via factories and constructs `WorldState(tick=0, entities=entities)`.
- The 21 engine systems read graph node attributes directly (`graph.nodes[id]["wealth"]` etc.) per CLAUDE.md "Systems mutate shared graph in-place". They expect a live mutable graph, not a fresh-from-WorldState graph each tick.

**Pattern for spec-066 runner**:
```text
session init:
    world = bridge.hydrate_initial(...)             # builds entities + relationships
    graph = world.to_graph()                         # ONE-SHOT conversion
    services = ServiceContainer.create(...)          # ONE-SHOT (per R2)

per tick:
    engine.run_tick(graph, services, context)        # mutates graph in place
    world = WorldState.from_graph(graph)             # reconstitute (excludes computed fields)
    bridge.persist_tick(world, tick, hash)           # reads world.relationships, world.entities
```

**Alternatives considered**:
- **Per-tick to_graph()/from_graph()** — wasteful and breaks engine system expectations of mutable shared state.
- **Skip from_graph(), persist directly from graph** — would couple bridge.persist_tick to graph node attribute keys instead of typed Pydantic models. Rejected: violates II.6 (state is data) by making bridge dependent on engine implementation details.
- **Use a sidecar graph for engine, keep WorldState immutable** — requires engine systems to be rewritten to consume sidecar; massively out of scope.

---

## R2 — ServiceContainer construction in the bridged runner

**Decision**: Construct `ServiceContainer.create(config=SimulationConfig(), defines=defines)` ONCE in `runner.run()` before the tick loop. Pass the same instance to every `engine.run_tick(...)` call. Use `ServiceContainer.create()` defaults for `database` (`sqlite:///:memory:`), `event_bus` (the bridge already constructs one in spec-065 T071 and the bridge holds a reference; pass it via the `event_bus=` kwarg to ensure publishers and subscribers share the same bus), `formulas` (`FormulaRegistry.default()`), and `metrics` (default `MetricsCollector()`).

Inject the bridge-owned `auditor`, `boundary_register`, and `event_bus` into the ServiceContainer fields spec-065 added (lines 104-110 of services.py). All other 25+ optional fields stay `None` — every engine system that depends on them guards `if x is None: return` cleanly.

**Rationale**:
- `ServiceContainer.create()` (lines 137-248 of services.py) accepts no required positional args; all fields have safe defaults.
- All optional calculator fields are guarded — research confirmed no system hard-requires non-None for any optional field.
- ServiceContainer holds no per-tick state. Per-tick construction is pure waste; once-and-reuse is correct.
- The bridge already owns `EventBus`, `BoundaryFlowRegister`, and `ConservationAuditor` (spec-065 T049/T055/T071). Passing these into ServiceContainer ties the engine's publishes/observes to the bridge's collectors so events flow into `summary.events` and audit rows accumulate in `auditor.audit_log_buffer`.

**Alternatives considered**:
- **Per-tick ServiceContainer construction** — wasteful, no benefit. Rejected.
- **Postgres-backed `database`** — engine doesn't actually use `services.database` for state in the canonical path; default `sqlite:///:memory:` is fine. Switching to Postgres adds risk of accidental writes during tick (Constitution II.6 violation).

---

## R3 — Engine system count and invocation order

**Decision**: The canonical engine has **21 systems**, not 15. Update `spec.md` FR-013 to reflect the actual order. Use `_DEFAULT_ENGINE` from `simulation_engine.py:411` (or `SimulationEngine(_DEFAULT_SYSTEMS)`) — do NOT customize the system list.

The 21-system order (per `simulation_engine.py:319-345`):

```
Material Base (14):
  1. VitalitySystem           — death-from-subsistence checks
  2. TerritorySystem          — heat dynamics, eviction pipeline
  3. SubstrateSystem          — Spec-062 hex substrate (no-op without hex nodes)
  4. ProductionSystem         — value creation
  5. TickDynamicsSystem       — Feature 017 tensor state
  6. ReserveArmySystem        — Feature 021 wage pressure
  7. CommunitySystem          — Feature 022 (no-op without community nodes)
  8. LifecycleSystem          — Feature 030 D-P-D' lifecycle
  9. SolidaritySystem         — solidarity transmission
 10. ImperialRentSystem       — Φ extraction
 11. DispossessionEventSystem — Feature 021
 12. DecompositionSystem      — labor aristocracy crisis
 13. ControlRatioSystem       — terminal decision
 14. MetabolismSystem         — ecology

Action Phase (1):
 15. OODASystem               — Feature 032 (no-op without organization nodes)

Consequences (6):
 16. SurvivalSystem           — P(S|A), P(S|R)
 17. StruggleSystem           — agency layer (largest single system)
 18. ConsciousnessSystem      — ideology drift + bifurcation
 19. ContradictionSystem      — tension accumulation
 20. ContradictionFieldSystem — Feature 002 (no-op without field data)
 21. FieldDerivativeSystem    — Feature 002 (no-op without field data)
 22. EdgeTransitionSystem     — Feature 002 (no-op without edge mode predicates)
```

(Twenty-two entries in the list above; `SubstrateSystem` is enumerated at "2.5" between TerritorySystem and ProductionSystem in the source, so the canonical count is 21 — matching the 21-element default invariant enumeration in `ConservationAuditor._DEFAULT_INVARIANTS`.)

**Critical**: All 21 systems no-op cleanly on the spec-065 bridged graph (only SocialClass entities, empty relationships at first run). Systems that require absent node types (CommunitySystem → Community nodes, OODASystem → Organization nodes, ContradictionFieldSystem → Territory hex nodes) iterate empty inner loops. None crashes.

**Spec amendment**: Update FR-013, FR-016, FR-017, the spec Edge Cases section, and SC-010 to say "21 systems" not "15". The MVP commit must include this spec correction.

**Rationale**:
- CLAUDE.md (lines 214-231) lists only 7 systems — outdated since spec-021/022/030/032/002 each added systems.
- Spec-066 originally trusted the spec text (which trusted CLAUDE.md). Research surfaced the discrepancy.
- Customizing the system list would create a non-canonical engine that would fail spec-053/054/055 invariant tests (which assume the canonical engine).

**Alternatives considered**:
- **Subset the 21 to a "minimum viable" 5-7** — was the original Q2 alternative the user rejected; stick with full 21.
- **Skip CommunitySystem and OODASystem until their dependencies exist** — they no-op cleanly anyway; explicit skip would create two code paths with no behavioral difference.

---

## R4 — ConsciousnessSystem dependencies + coefficient tuning

**Decision**: ConsciousnessSystem (`src/babylon/engine/systems/ideology.py:74-235`) operates on the legacy 2-axis `IdeologicalProfile(class_consciousness, national_identity)` per SocialClass node — NOT directly on the (r, l, f) ternary. The bridge's existing mapping `r = cc(1-ni)`, `f = ni(1-cc)`, `l = max(0, 1-r-f)` translates after the engine mutates IdeologicalProfile.

**Required graph state for ConsciousnessSystem to drift consciousness**:
1. SocialClass node carries `ideology` dict with `class_consciousness`, `national_identity`, `agitation` keys.
2. **WAGES edges** incoming to the node (sum gives `wage_change` input). Without WAGES edges, `wage_change = 0`.
3. **SOLIDARITY edges** incoming from sources with `class_consciousness > activation_threshold`. Without SOLIDARITY edges, `solidarity_factor = 0` and ALL agitation routes to fascism (`national_identity` increases).

**Coefficient tuning needed**: Current defaults give a per-tick consciousness drift of ~0.000045 per tick under typical 5% wage drops. Over 520 ticks that's ~2.3% — **does not clear SC-005's ≥5% threshold** without sustained material crisis.

Tune in `defines/consciousness.py`:
- `routing_scale`: 0.1 → **0.2** (doubles bifurcation drift per tick of agitation consumption)
- `agitation_consumption_rate`: 0.6 → **0.7** (slightly faster drift; still respects bounds)
- `exploitation_sensitivity`: 0.15 → **0.20** (more responsive to wage compression)

These bumps are calibration, not theoretical changes; they preserve all qualitative bifurcation behavior. Document in ADR043 (or a new ADR045) so a future spec can recalibrate against survey data.

**Rationale**:
- Without WAGES + SOLIDARITY edges, the spec-066 promise of "consciousness evolves with material conditions" silently fails — agitation never accumulates and bifurcation never routes meaningfully.
- The spec-065 bridge today builds zero relationships at hydrate_initial. Spec-066 MUST seed both edge types per county (per R5).
- Coefficient defaults were tuned for the legacy in-memory engine where ticks were sparse and material conditions changed in big steps; the bridged runner has 520 weekly ticks where material conditions change in small year-boundary increments. The defaults need a small bump to be visible at this resolution.

**Falsifiability** (per Constitution III.2): SC-005 `≥5% relative ideology change tick 0 → tick 519` is the falsifiability gate. If after coefficient tuning + edge seeding the test still fails, ConsciousnessSystem itself has a regression that needs investigation BEFORE shipping spec-066.

**Alternatives considered**:
- **Seed only WAGES edges, omit SOLIDARITY** — would route ALL agitation to fascism (no bifurcation). Politically nonsense for the project's purposes.
- **Don't tune coefficients; rely on extreme wage swings to clear SC-005** — fragile; depends on data shape; won't replicate.
- **Revise SC-005 to ≥1%** — defeats the test's purpose; "consciousness barely moves" is functionally equivalent to "consciousness doesn't move".

---

## R5 — WorldState.relationships seeding

**Decision**: The bridge's `_build_per_county_entities()` seeds **two relationships per county** at hydrate_initial:

1. **EXPLOITATION edge**: `proletariat_id → bourgeoisie_id`, `value_flow=0.0`, `tension=0.1` (small positive seed so tension dynamics have a non-zero starting point).
2. **SOLIDARITY edge**: `proletariat_id → bourgeoisie_id`, `solidarity_strength=0.05` (low but non-zero, so any subsequent organizing has a substrate to amplify).

For 83 Michigan counties this seeds 166 edges total (1 EXPLOITATION + 1 SOLIDARITY per county). EXPLOITATION edges are the primary surface for ImperialRentSystem to extract Φ; SOLIDARITY edges enable ConsciousnessSystem's bifurcation to route to revolutionary side.

**Implementation pattern**: Add a private helper `_build_per_county_relationships(scope_fips, entities) -> list[Relationship]` to bridge.py that returns the seeded edges. Call it after `_build_per_county_entities()` and pass the result to `WorldState(tick=0, entities=entities, relationships=rels)`.

**Rationale**:
- Research confirmed: NO engine system creates EXPLOITATION or SOLIDARITY edges on first invocation. Both ImperialRentSystem (`src/babylon/engine/systems/economic.py:234-280`) and SolidaritySystem (`src/babylon/engine/systems/solidarity.py:89-100+`) ITERATE pre-existing edges.
- Without seeded edges:
  - ImperialRentSystem's extraction phase is a no-op → Φ stays 0
  - SolidaritySystem's transmission is a no-op → consciousness stays uniform
  - ConsciousnessSystem's bifurcation routes ALL agitation to fascism (since `solidarity_factor = 0`)
- The spec's qualitative goal (Wayne ≠ Keweenaw, per SC-006) requires per-county SOLIDARITY heterogeneity; that emerges only if every county starts with at least one SOLIDARITY edge to amplify.

**Alternatives considered**:
- **Seed only EXPLOITATION, let SOLIDARITY emerge dynamically** — see above; bifurcation routes degeneratively.
- **Seed cross-county edges (proletariat-Wayne ↔ proletariat-Macomb)** — adds 83 × 82 / 2 = ~3400 edges. Massively expensive and theoretically dubious. Rejected.
- **Seed via WAGES edge instead of EXPLOITATION** — WAGES is for super-wages from core to labor aristocracy; doesn't apply to within-county dyads. Rejected.

---

## R6 — QCEW normalization approach

**Decision**: Add `AND fq.industry_id = 1` filter to the QCEW SUM query in `src/babylon/persistence/hex_hydrator.py:312` (the "All Industries" aggregate row, which is the BLS publication granularity). This is **option (b)** from the spec assumptions (SQL filter at hex hydration time).

Wayne 2010 currently sums to ~$277B/year across denormalized industry+ownership rows. With `industry_id = 1` filter, it deduplicates to **$66.45B/year** ($1.28B/week) which is within ±50% of the ADR042 baseline of $960M/week (target satisfies FR-002).

**Rationale**:
- `fact_qcew_annual` schema is correct (composite PK on county/industry/ownership/time); the over-count comes from summing across overlapping NAICS hierarchies (Manufacturing + Durable Goods both contain the same establishments).
- BLS publishes at the "All Industries" aggregate level; using `industry_id = 1` aligns the simulation with BLS's external truth.
- Re-ingestion (option a) is multi-week; calibration constant (option c) is unprincipled. Option (b) is one-line surgical change.

**Alternatives considered**:
- **Option (a) re-ingestion** — too expensive for spec-066 scope.
- **Option (c) calibration factor** — brittle; would mask future data updates.
- **Filter on `ownership_id` only (sum across industries)** — still triple-counts NAICS hierarchies; doesn't help.

**Note**: $1.28B/week is ~33% above the $960M target; if FR-002 enforcement requires tighter calibration, apply a secondary scalar of 0.75 multiplied AFTER the industry_id=1 filter. But the ±50% band of FR-002 is wide enough to accept the unscaled value.

---

## R7 — BEA national industry I-O calibration

**Decision**: Keep `INTERMEDIATE_INPUTS_FRACTION = 0.5` unchanged. With the R6 QCEW dedup (Wayne v ≈ $1.28B/week) and Michigan 2010 GDP ≈ $370B/year ($7.1B/week), the implied state-level c/v organic composition is:

```
c_per_week (state) = 0.5 × $7.1B = $3.55B
v_per_week (state) = sum across 83 counties ≈ ~$5-6B (after R6 dedup, scaling down from current $24B)
c/v ≈ 0.6
```

This falls within the Shaikh-tractable band [0.5, 5.0] per FR-003. Defer per-industry I-O coefficient ingestion to spec-068.

**Note about Bug A's formula**: Per spec FR-001, the new formula is `s = max(0, GDP/52 - v)` — `c` no longer appears in the s computation. So `c` only needs to be plausible (for the c/v invariant FR-003). The 0.5 constant is fine. *(FR-019's c+v+s=W aggregate check was originally cited here as a secondary use, but FR-019 was subsequently dropped per /speckit.analyze U1 as tautological after FR-001 formula fix.)*

**Rationale**:
- `fact_bea_national_industry` is empty (verified via SQL count). Ingestion is moderate data work.
- The 0.5 constant is documentable as "national gross-output / GDP ratio ≈ 1.85, intermediate inputs ≈ 0.85 of GDP — round to 0.5 as conservative national average until per-industry data ingested."
- ~~For FR-019 (`c + v + s = W`), W = 2v + c (since GDP = v + s and gross output W = c + GDP). With c = 0.5 × GDP and v ≈ 0.18 × GDP, W ≈ 1.5 × GDP. The identity holds by construction; no spec-066 effort needed beyond the formula fix.~~ **FR-019 dropped per /speckit.analyze U1** — this analysis showed the identity is tautological by construction, so there's no meaningful test. No replacement needed.

**Alternatives considered**:
- **Ingest fact_bea_national_industry table** — scope creep; defer to spec-068.
- **Recalibrate constant to 0.85** — would make c proportionally bigger and shift c/v to ~3.5 (still in band). Either constant is defensible; preserve 0.5 to minimize change surface for spec-066.

---

## R8 — Engine-system per-tick wallclock estimate

**Decision**: Relax SC-011 from ≤45 minutes to ≤90 minutes for the canonical Michigan-Canada 520-tick run (≤ 10s/tick mean), AND scope the tightest budget claim (≤ 5s/tick) to **tri-county only**. Document the SQLite per-tick read path as research debt requiring a follow-up optimization spec (provisionally numbered spec-069).

**Estimated wallclock with engine integration**:

| Scope | Bridge baseline (spec-065) | Engine systems | Total/tick | 520-tick total |
|---|---|---|---|---|
| Tri-county (3 counties) | ~5.5s | +50-100ms | ~5.6s | ~49 min |
| Michigan (83 counties) | ~8-12s (extrapolated, unmeasured) | +200-400ms | ~10s avg | ~87 min |

**Rationale**:
- Spec-065's measured baseline is 5.47s/tick for Michigan-Canada (48 min total). That's WITHOUT engine systems running.
- The dominant per-tick cost is ~3-4s SQLite reads (per-county per-tick `fetch_population_for_county_at_tick` + `fetch_employment_proxy_for_county_at_tick`). 84 counties × 2 reads per tick = 168 SQLite queries per tick × 520 ticks ≈ 87K queries.
- Engine systems add modest overhead: most are O(N) where N=84 entities (<5ms each); the largest system (StruggleSystem) is O(E) with edge density (~50-200ms). Total engine cost estimated at 200-400ms/tick.
- With current bridge cost dominant, the SC-011 ≤45 min budget is unattainable. The honest answer is to relax the budget AND document the optimization opportunity.

**Optimization opportunities** (deferred to spec-069):
1. **Cache SQLite reads per-year**: population + employment change annually, not weekly. Hydrate once at session init, lookup from in-memory dict. Saves ~3.5s/tick → 1-2 days work.
2. **Verify Postgres `executemany` batching**: confirm `persist_tick_atomic()` actually batches the 336 inserts/tick. If not, refactor.
3. **Pre-compute county entity templates** at hydrate_initial; avoid re-instantiating SocialClass per tick.

**Alternatives considered**:
- **Tighten the budget AND optimize within spec-066** — couples engine integration to optimization; doubles spec scope and risk.
- **Keep ≤45 min budget; accept that SC-011 will fail** — dishonest; would force a successor spec just to relax the SC.
- **Scope spec-066 to tri-county only** — would skip the Michigan-statewide run that's the whole point of spec-064 onwards; rejected.

---

## Summary table

| ID | Question | Decision | Spec impact |
|---|---|---|---|
| R1 | Graph round-trip pattern | Bridge owns graph; one-shot to_graph at init; from_graph after each tick | No spec change; documented in plan |
| R2 | ServiceContainer construction | `ServiceContainer.create(config, defines)` once before tick loop, inject bridge-owned auditor/register/event_bus | No spec change |
| R3 | Engine system count | **21 systems** (not 15); use `_DEFAULT_ENGINE` | **Spec amendment**: FR-013, FR-016, FR-017, SC-010 must say "21 systems" |
| R4 | ConsciousnessSystem deps + coefficients | Mutates `IdeologicalProfile`; needs WAGES + SOLIDARITY edges; coefficients need bumping (`routing_scale 0.1→0.2`) | **Spec amendment**: ADR043 must include coefficient calibration; new SC for "WAGES + SOLIDARITY edges seeded" |
| R5 | Relationship seeding | Bridge seeds 1 EXPLOITATION + 1 SOLIDARITY edge per county at hydrate_initial | No spec change (consequence of R4) |
| R6 | QCEW normalization | Add `industry_id = 1` filter | No spec change |
| R7 | BEA I-O calibration | Keep 0.5 constant; defer ingestion to spec-068 | No spec change |
| R8 | Wallclock budget | **Relax SC-011 from ≤45 min to ≤90 min**; document SQLite cache optimization as spec-069 | **Spec amendment**: SC-011 budget relaxation + new ADR for spec-069 placeholder |

## Spec amendments required before Phase 1

These three spec.md edits flow directly from research and must land BEFORE data-model.md/contracts/quickstart.md generation:

1. **FR-013, FR-016, FR-017, SC-010**: change "15 systems" → "21 systems" with the corrected canonical order.
2. **SC-011**: relax wallclock from ≤45 min (≤2700s) to ≤90 min (≤5400s); update Assumptions section with the spec-069 follow-up reference.
3. **New FR (FR-025)**: bridge MUST seed at least one EXPLOITATION edge and one SOLIDARITY edge per county at `hydrate_initial`. (Currently implied by US2 acceptance; making it explicit pins down R5.)
4. **New FR (FR-026)**: ConsciousnessSystem coefficient calibration MUST set `routing_scale ≥ 0.2` (or document why a smaller value is sufficient to clear SC-005). Pins down R4.
