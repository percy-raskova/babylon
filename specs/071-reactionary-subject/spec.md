# Feature Specification: The Reactionary Subject

**Feature Branch**: `071-reactionary-subject`
**Created**: 2026-07-03
**Status**: Draft
**Advisory catalog number**: audit Part 3, Wave 1, "spec-071 — Reactionary Subject (Entitlement + Chauvinism + FascistFactionSystem)". Complexity L (~50–70 h).
**Depends on**: spec-070 Balkanization (BalkanizationFaction live), ADR051 Lawverian dialectics (StanceIntervention hook, dialectical_regime), ADR052 rustworkx substrate.
**Input**: Full catalog entry per `project/03-next-spec-071.md` — no MVP scoping.

## Overview *(context, not a template section)*

The 2026-07-02 work built **hegemony**: US core county workers are labor
aristocracy (LA), super-waged out of imperial rent (Φ), pacified with
P(S|A) → 0.995 while agitation stays flat (crisis-gated). spec-071 builds
the OTHER branch of the George Jackson bifurcation (Constitution I.4): what
the bribed strata DO when the bribe decays. When Φ falls, agitation that
would route to revolution under solidarity instead routes to **fascism** in
its absence — the labor aristocracy and the petty/comprador bourgeoisie
become the reactionary mass base. This is Cope's "divided world, divided
class" rendered as a mechanic: privilege under threat produces reaction, not
revolution.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entitled strata drift fascist under crisis (Priority: P1)

The privileged strata (labor aristocracy C_la, petty/comprador bourgeoisie
C_pb) carry an **entitlement** — a stake in the imperial order. When
material crisis generates agitation AND solidarity is absent, that
agitation is amplified by entitlement into a **fascist pull**. Sustained
fascist pull drives a per-node **fascist_alignment** counter upward; at
saturation the node is captured by (reassigned to) a fascist faction.

**Why this priority**: This is the core theoretical payload of the spec —
the fascism branch of the bifurcation. Everything else elaborates it.

**Independent Test**: Construct an in-memory world with a C_la node under
induced crisis (rising agitation, no SOLIDARITY edge, high entitlement) and
step the engine; assert `fascist_alignment` rises, a `FASCIST_DRIFT` event
fires when the pull exceeds threshold, and (with a fascist faction present)
`FASCIST_RECRUITMENT` fires with faction reassignment at saturation.

**Acceptance Scenarios**:

1. **Given** a C_la node with high entitlement, positive agitation, and no
   incident SOLIDARITY edge, **When** the FascistFactionSystem steps, **Then**
   `Fascist_Pull = Agitation × (Entitlement / (Solidarity + 0.1))` exceeds
   1.0, `fascist_alignment` increases by the drift increment, and a
   `FASCIST_DRIFT` event is published.
2. **Given** a node whose `fascist_alignment` reaches ≥ 1.0 and a fascist
   BalkanizationFaction exists in the world, **When** the system steps,
   **Then** the node is reassigned to that faction and a
   `FASCIST_RECRUITMENT` event is published.
3. **Given** the pacified canonical decade (Φ growing, agitation ≈ 0),
   **When** the 520-tick run executes, **Then** near-zero `FASCIST_DRIFT`
   events fire (hegemony holds; drift is crisis-gated, not a passive ramp).
4. **Given** a node with a strong incident SOLIDARITY edge under identical
   agitation, **When** the system steps, **Then** the fascist pull is
   suppressed (solidarity denominator dampens the pull) and drift is lower
   than the no-solidarity case.

---

### User Story 2 - Labor-aristocratic chauvinism and org defection (Priority: P2)

Labor-aristocracy members recruited into a player organization accumulate
**chauvinism** each tick (faster when super-waged). On a crisis event each
LA member rolls a defection probability `sigmoid(chauvinism − discipline)`.
Defections fracture the organization (`ORGANIZATIONAL_FRACTURE`); a majority
defection is a `RED_BROWN_COUP` — the org captured by its own reactionary base.

**Why this priority**: Models the internal danger of recruiting the labor
aristocracy — the "red-brown" failure mode. Depends on P1's reactionary
substrate but is an independent org-internal mechanic.

**Independent Test**: Build an org with MEMBERSHIP edges to LA class nodes,
step ticks to accumulate chauvinism, publish a crisis event, and assert
defection rolls fire `ORGANIZATIONAL_FRACTURE`, and > 50% defection fires
`RED_BROWN_COUP`.

**Acceptance Scenarios**:

1. **Given** an org with an LA member (MEMBERSHIP edge), **When** a tick
   passes, **Then** the membership's chauvinism increases by the base rate,
   plus a super-wage bonus when the member holds a WAGES edge with a
   positive super-wage.
2. **Given** an accumulated-chauvinism LA membership and a crisis event this
   tick, **When** the system rolls defection and it succeeds, **Then**
   `ORGANIZATIONAL_FRACTURE` fires for that org.
3. **Given** an org where more than half of LA members defect in one crisis,
   **When** the system resolves defections, **Then** `RED_BROWN_COUP` fires.

---

### User Story 3 - Lumpen volatility → spontaneous riot (Priority: P2)

The lumpenproletariat (L_u) carries high **volatility**. Its capacity for
disorder is gated by `volatility × (1 − organizational_discipline)`: high
volatility with low discipline produces a `SPONTANEOUS_RIOT` — undirected,
non-revolutionary disorder (distinct from the organized UPRISING).

**Why this priority**: Completes the reactionary-subject picture (the
declassed stratum) and integrates with the existing StruggleSystem without
breaking the hegemony-holds income circuit.

**Independent Test**: Construct an L_u node with high volatility and low
discipline, step StruggleSystem, and assert `SPONTANEOUS_RIOT` risk fires;
assert the income-circuit hegemony suite stays green (no EXPLOITATION-edge
severing regressions).

**Acceptance Scenarios**:

1. **Given** an L_u node with high volatility and low organizational
   discipline, **When** StruggleSystem steps, **Then** the spontaneous-riot
   risk exceeds threshold and a `SPONTANEOUS_RIOT` event is published.
2. **Given** an L_u node with high discipline, **When** StruggleSystem steps,
   **Then** the riot risk is suppressed (discipline gates volatility).
3. **Given** the canonical world (LA workers, no L_u under crisis), **When**
   the income-circuit suite runs, **Then** all existing tests stay green.

---

### User Story 4 - Fascist action verbs in OODA (Priority: P3)

Reactionary organizations gain fascist action verbs: `POGROM`, `LOCKOUT`,
`VIGILANTISM`, and the auto-triggered `RED_BROWN_COUP`. These resolve through
the OODA action layer with materially-grounded effects.

**Why this priority**: Gives reactionary formations agency (Constitution
I.16 — orgs are the agents). Depends on P1/P2's substrate.

**Independent Test**: Register the verbs in the ActionType enum and resolve
each through OODA, asserting each emits its event with graph effects.

**Acceptance Scenarios**:

1. **Given** an eligible reactionary org, **When** it resolves a `POGROM` /
   `LOCKOUT` / `VIGILANTISM` action, **Then** the corresponding event is
   published with the expected graph effect.
2. **Given** a majority LA defection, **When** the coup resolves, **Then**
   `RED_BROWN_COUP` fires without an explicit player selection (auto-trigger).

---

### User Story 5 - Carceral-enforcer decomposition gap closed (Priority: P3)

When LA super-wages fail (`SUPERWAGE_CRISIS`), DecompositionSystem splits the
LA into carceral enforcers (~30%) and internal proletariat (~70%). Today the
enforcer branch no-ops because the bridged world seeds no
`CARCERAL_ENFORCER` entity. 071 induces this crisis in tests, so the gap is
closed: the system creates the target entities on demand.

**Why this priority**: Required for 071's crisis tests to exercise the
terminal arc; the canonical decade (rent exhaustion ≈ year 43) is unaffected.

**Independent Test**: Induce `SUPERWAGE_CRISIS` in a world with no seeded
enforcer and assert the enforcer + internal-proletariat populations are
created and `CLASS_DECOMPOSITION` reports non-zero transfers.

**Acceptance Scenarios**:

1. **Given** a decomposing LA and no existing `CARCERAL_ENFORCER` /
   `INTERNAL_PROLETARIAT` node, **When** decomposition executes, **Then**
   those entities are created and receive the split population/wealth.
2. **Given** the canonical 10-year run (no superwage crisis), **When** it
   executes, **Then** no enforcer entities are created (baseline unchanged).

---

### User Story 6 - RLF simplex discipline (Priority: P3)

The ternary consciousness `(r, l, f)` (revolutionary / liberal / fascist)
obeys the ratified simplex constraints (ADR051 §9.4): `r + l + f = 1` with
liberal tie-break; `ideological_contestation = H(r,l,f)/log 3` as a
DIAGNOSTIC only; the `f → r` transition is forbidden / ε-gated
(proletarianization ∧ adjacent-r ∧ solidarity) — breaking detailed balance
so no potential function exists; `assimilation_ratio = f/(l+f)`.

**Why this priority**: An inherited obligation deferred to 071. It grounds
the asymmetry of fascist recruitment (easy to enter, hard to leave).

**Independent Test**: Unit-test `normalize_to_simplex` sums to 1 with liberal
default; test the `f → r` gate rejects ungated transitions and permits gated
ones; test `assimilation_ratio` and the entropy diagnostic.

**Acceptance Scenarios**:

1. **Given** any `(r, l, f)` triple, **When** normalized, **Then** it sums to
   1.0 and the residual assigns to liberal.
2. **Given** an `f → r` transition request without the proletarianization ∧
   adjacent-r ∧ solidarity precondition, **When** evaluated, **Then** the
   transition is refused (ε-gated to zero).

---

### Edge Cases

- **Zero solidarity**: the `Solidarity + 0.1` denominator prevents division
  by zero and yields the maximal (unsuppressed) fascist pull.
- **No fascist faction present**: drift accumulates and `FASCIST_DRIFT` still
  fires, but reassignment is deferred until a fascist faction exists (no
  crash, no silent capture).
- **Node already saturated**: `fascist_alignment` is clamped to [0, 1]; once
  reassigned, re-firing `FASCIST_RECRUITMENT` is idempotent (guarded by the
  existing alignment attribution).
- **Determinism**: all stochastic rolls (defection, spontaneous riot) use a
  seed-deterministic RNG (the spec-070 `_resolve_rng(services, tick)` pattern)
  so replay (Constitution III.7) holds.
- **Graph round-trip**: new SocialClass fields survive `to_graph()` /
  `from_graph()`; chauvinism is graph-state on MEMBERSHIP edges.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: SocialClass MUST carry `entitlement: Intensity`, role-defaulted
  (PERIPHERY_PROLETARIAT = 0.2, LUMPENPROLETARIAT = 0.0, COMPRADOR_BOURGEOISIE
  = 0.7, LABOR_ARISTOCRACY = 0.8; all other roles = 0.0).
- **FR-002**: SocialClass MUST carry `volatility: Intensity`, role-defaulted
  (LUMPENPROLETARIAT = 0.8; all other roles = 0.0).
- **FR-003**: SocialClass MUST carry `fascist_alignment: Intensity` (drift
  counter, default 0.0) and `aligned_faction_id: str | None` (the faction the
  node has been captured by, default None).
- **FR-004**: All new SocialClass fields MUST survive the graph round-trip
  (`to_graph()` serializes them; `from_graph()` reconstructs them) with tests.
- **FR-005**: A new `FascistFactionSystem` MUST run in the CONSEQUENCE phase
  after ConsciousnessSystem (position ~17.x, see plan for exact placement vs
  spec-070 SovereigntySystem at 17.5) and be registered in the spec-056
  partition sets.
- **FR-006**: For each active C_pb / C_la node, the system MUST compute
  `Fascist_Pull = Agitation × (Entitlement / (Solidarity + 0.1))`; when it
  exceeds the configured threshold (default 1.0) it MUST increment
  `fascist_alignment` by the configured drift step (default 0.05) and publish
  `FASCIST_DRIFT`.
- **FR-007**: When a node's `fascist_alignment` reaches ≥ 1.0 and a fascist
  faction exists, the system MUST set `aligned_faction_id` to that faction and
  publish `FASCIST_RECRUITMENT` (idempotent once captured).
- **FR-008**: The fascist pull MUST be expressed as a signed
  `StanceIntervention` on the relevant opposition's balance (written to the
  `opposition_interventions` graph attr consumed by ContradictionSystem),
  NOT as a parallel ad-hoc counter.
- **FR-009**: The system MUST READ the `dialectical_regime` graph attribute
  (from ContradictionSystem) rather than recompute regime classification.
- **FR-010**: Organization MEMBERSHIP edges to LABOR_ARISTOCRACY nodes MUST
  accumulate `chauvinism` per tick (base rate, default 0.01; +0.02 when the
  member holds a WAGES edge with positive super-wage).
- **FR-011**: On a crisis event, each LA member MUST roll
  `P_defection = sigmoid(chauvinism − discipline)`; a successful roll MUST
  publish `ORGANIZATIONAL_FRACTURE`; > 50% of an org's LA members defecting
  MUST publish `RED_BROWN_COUP`.
- **FR-012**: StruggleSystem MUST gate LUMPENPROLETARIAT spontaneous disorder
  on `volatility × (1 − organizational_discipline)`; exceeding threshold MUST
  publish `SPONTANEOUS_RIOT`. Existing income-circuit hegemony behavior MUST
  be preserved.
- **FR-013**: ActionType MUST gain `POGROM`, `LOCKOUT`, `VIGILANTISM`,
  `RED_BROWN_COUP`; OODA resolution MUST resolve the first three as player/
  org actions and auto-trigger `RED_BROWN_COUP`.
- **FR-014**: EventType MUST gain `FASCIST_DRIFT`, `FASCIST_RECRUITMENT`,
  `ORGANIZATIONAL_FRACTURE`, `RED_BROWN_COUP`, `POGROM`, `LOCKOUT`,
  `VIGILANTISM`, `SPONTANEOUS_RIOT`.
- **FR-015**: `src/babylon/formulas/reactionary.py` MUST provide
  `calculate_fascist_pull`, `calculate_defection_probability`,
  `calculate_spontaneous_riot_risk`, `calculate_entitlement_effective`, each
  with RST docstrings and passing doctests.
- **FR-016**: ALL numeric constants introduced MUST live in GameDefines (a new
  `ReactionaryDefines` category) — no magic numbers in systems (Constitution
  III.1).
- **FR-017**: The RLF simplex constraints MUST be honored: `normalize_to_simplex`
  enforces `r+l+f=1` with liberal tie-break; `assimilation_ratio = f/(l+f)`
  and `ideological_contestation = H(r,l,f)/log 3` (diagnostic only) MUST be
  available; the `f→r` transition MUST be ε-gated on
  (proletarianization ∧ adjacent-r ∧ solidarity).
- **FR-018**: DecompositionSystem MUST create the `CARCERAL_ENFORCER` and
  `INTERNAL_PROLETARIAT` target entities on demand when they are absent, so
  the enforcer split no longer no-ops under `SUPERWAGE_CRISIS`.
- **FR-019**: All stochastic decisions MUST be deterministic given the seed
  (Constitution III.7): a repeated run with the same config reproduces the
  same event stream.

### Key Entities

- **SocialClass** (extended): adds `entitlement`, `volatility`,
  `fascist_alignment`, `aligned_faction_id`. Frozen Pydantic, Intensity types.
- **BalkanizationFaction** (spec-070, reused): the capture target for drifted
  nodes; a "fascist faction" is identified by ideology tag / settler UPHOLD
  stance (see Decisions).
- **MEMBERSHIP edge** (Organization → SocialClass): carries `chauvinism`
  (graph edge state) for LA recruits.
- **FascistFactionSystem** (new): the consequence-phase system computing pull,
  drift, reassignment, chauvinism accumulation, defection, and coup.
- **ReactionaryDefines** (new GameDefines category): all tunable constants.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A crisis-induction scenario (wage cut / pool drain) fires
  `FASCIST_DRIFT` and, with a fascist faction present, `FASCIST_RECRUITMENT`
  with node reassignment — asserted by an integration test.
- **SC-002**: The pacified canonical 520-tick run completes with 83/83 county
  liveness AND near-zero `FASCIST_DRIFT` during the pacified decade (hegemony
  holds; drift is crisis-gated).
- **SC-003**: `mise run check` (lint + format + typecheck + unit) is green.
- **SC-004**: The income-circuit integration suite
  (`tests/integration/test_bridge_income_circuit.py`) stays green, including
  `test_hegemony_holds_exploitation_edge_persists`.
- **SC-005**: `mise run qa:e2e-regression` passes against the proven baseline
  (byte-identical if dynamics unchanged for the tri-county gate, or a written
  proof + regenerated baseline if 071's always-on systems move it).
- **SC-006**: All new formulas have passing doctests; all new constants are in
  GameDefines (zero magic numbers introduced in systems).
- **SC-007**: A repeated crisis scenario with the same seed produces an
  identical event stream (determinism).

## Assumptions

- **Player orgs are absent from the base canonical world**: the bridge seeds
  worker + bourgeois entities and 3 edges (EXPLOITATION, TENANCY, WAGES) per
  county; no organizations, no MEMBERSHIP edges, no BalkanizationFactions.
  Therefore the chauvinism/defection/coup path and faction reassignment are
  DORMANT in the canonical decade and exercised only in dedicated tests that
  construct the necessary substrate. This keeps the canonical baseline stable.
- **Agitation is crisis-gated** (`02-engine-truths.md` §4): flat consciousness
  during the growing-bribe decade is CORRECT, so near-zero drift is the
  expected canonical behavior — not a missing wire.
- **The fascist pull's "always-on" reach**: the FascistFactionSystem runs
  every tick over C_pb/C_la nodes. In the canonical world all core workers are
  LA, so the system reads them every tick. Because agitation ≈ 0 during
  hegemony, `Fascist_Pull ≈ 0` and no drift/intervention fires — but the
  per-node reads and StanceIntervention hook are new always-on behavior. If
  this shifts the tri-county 5-tick gate, R-PROOF (written proof + regenerate)
  applies; if not, the baseline is byte-identical.
- **Determinism RNG**: reuse the spec-070 `_resolve_rng(services, tick)`
  fallback (`random.Random(0xBA1AC1A + tick)`) for defection/riot rolls.
- **`calculate_entitlement_effective` is shipped-but-inert**: FR-015 requires
  the formula to EXIST with doctests (satisfied), and `entitlement_threat_gain`
  is in `ReactionaryDefines`. But the threat-amplification is NOT wired into
  the drift math — wiring it would change canonical dynamics and break the
  byte-identical baseline, so it is deferred to a Wave-2 refinement that opens
  its own proof window. The formula + coefficient are the ready substrate.

## Decisions *(ambiguities resolved from kit docs + theory grounding; no user available)*

- **D1 — Pipeline position**: FascistFactionSystem is placed at **17.4**,
  immediately after ConsciousnessSystem (17) and BEFORE SovereigntySystem
  (17.5). Rationale: the reactionary subject forms as a direct ideological
  consequence of the bifurcation/agitation computed at 17; it must read that
  tick's agitation and last tick's `dialectical_regime`; keeping it adjacent to
  ConsciousnessSystem groups the ideological-consequence systems before the
  spec-070 political-topology chain. It writes `opposition_interventions` for
  ContradictionSystem (18) to consume this tick. (Resolves the 03 §"Position
  conflict".)
- **D2 — "Reassign node to the fascist Faction"**: realized by setting a new
  `aligned_faction_id: str | None` attribution on the SocialClass node (a
  persistent, round-tripping field), NOT by mutating spec-070 INFLUENCES edges
  (those are faction→territory overlays per I.20). A "fascist faction" is a
  BalkanizationFaction with `is_settler_formation = True` AND
  `colonial_stance = UPHOLD`, or an explicit `ideology` tag containing
  "fascist"/"reaction" (see plan for the exact predicate). This is a class-
  level political capture consistent with I.16 (factions are the agents that
  recruit substrate classes).
- **D3 — Chauvinism storage**: stored as a `chauvinism` attribute on the
  MEMBERSHIP edge (Organization → LA class node), the "member record". It is
  graph edge-state that persists in-place across ticks in the bridged runner;
  round-trip via WorldState is out of scope for the canonical run (no orgs in
  the base world) but the edge attribute is documented.
  - **Facade limitation** (review-noted): because `chauvinism` is graph
    edge-state and NOT a `Relationship` model field, `WorldState.from_graph`
    drops it. In the canonical BRIDGED runner the graph persists in-place, so
    chauvinism accrues correctly; but the in-memory `Simulation` facade
    (rebuilds the graph from `WorldState` each tick) resets it to 0.0, so
    chauvinism-driven defection cannot accumulate on that path. Deliberate —
    adding a Relationship field would risk perturbing serialization/
    determinism; the org/defection layer is a spec-072+ bridged-runner concern.
- **D4 — Carceral-enforcer gap**: closed by the CREATE-ON-DEMAND option
  (DecompositionSystem creates the enforcer / internal-proletariat entities
  when absent), NOT by seeding them per-county in the bridge. Rationale:
  create-on-demand is baseline-preserving (the canonical decade never
  decomposes), whereas per-county seeding would add 2×83 nodes to every tick
  and force a baseline regeneration for no canonical benefit.
- **D5 — Fascist pull as monad quantity**: the pull is applied as a signed
  `StanceIntervention` (FR-008), so the reactionary drift moves the opposition
  registry's balance (the ADR051 hook designed for 071) rather than a
  free-floating counter. `fascist_alignment` remains the per-node accumulator
  the reassignment reads (the quantity that becomes the quality at ≥ 1.0,
  Constitution I.7).
- **D6 — SPONTANEOUS_RIOT vs UPRISING**: the riot is undirected disorder from
  the declassed L_u (volatility-gated), distinct from the organized,
  solidarity-building UPRISING. It destroys wealth but builds NO solidarity
  infrastructure (the reactionary inverse of the George Floyd dynamic).
