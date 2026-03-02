# Research: State Apparatus AI (Feature 039)

**Feature Branch**: `039-state-apparatus-ai`
**Date**: 2026-03-02
**Spec**: `specs/039-state-apparatus-ai/spec.md`

---

## R1: StateActionType Enum — Separate vs Extend ActionType

**Context**: The existing `ActionType` enum (`src/babylon/models/enums.py:785`) has 21 player-facing values (RECRUIT, ORGANIZE, EDUCATE, AGITATE, etc.) with a resource profile of CL/SL cost and action points. The spec defines 6 top-level state verbs with ~24 sub-verbs (FR-B01 through FR-B07) that use a structurally different resource profile: budget cost, thread cost, and legitimacy cost. FR-B08 mandates asymmetry: players cannot execute state verbs and vice versa.

**Decision**: Create a SEPARATE `StateActionType` enum. Do NOT extend `ActionType`.

**Rationale**:
- `ActionType` models player/org actions with CL/SL cost profiles. State verbs have a structurally different resource profile: budget cost, thread cost, and legitimacy cost. These are different type signatures, not different values of the same type.
- FR-B08 explicitly mandates asymmetry. Separate enums enforce this constraint at the type level. A function accepting `ActionType` cannot silently accept LIQUIDATE as a player action. Static analysis catches the error before runtime.
- The existing `_NPC_PRIORITIES` dict (`npc_stub.py:20-47`) maps `OrgType -> list[ActionType]`. The state apparatus entries (SURVEIL, REPRESS, INFILTRATE) are Feature 032 stubs that will be replaced by the state AI decision function. Non-state org types continue using `ActionType` unchanged.
- The OODA system's `select_npc_actions()` (`src/babylon/ooda/npc_stub.py:50`) returns `list[Action]` where `Action.action_type` is `ActionType`. The state AI will return `StateAction` with `StateAction.verb` as `StateActionType`. This type distinction is structural.

**Enum structure**: A single flat `StateActionType` enum containing both top-level verbs (6 values: ADMINISTER, DEVELOP, RESEARCH, CO_OPT, REPRESS, WITHDRAW) and sub-verbs (~24 values: FUND, STAFF, LEGISLATE, AUDIT, INVEST, REZONE, etc.) with simple naming. An explicit `VERB_CHILDREN` mapping dict (`parent → frozenset[children]`) encodes the hierarchy and is the source of truth for parent-child validation in the `StateAction` model.

**Phase 1 refinement**: The initial design proposed prefix naming (`ADMINISTER_FUND`, `DEVELOP_INVEST`) with `startswith()`-based grouping. This was replaced in data-model.md with simple naming + `VERB_CHILDREN` mapping, which is more robust (no string parsing), avoids duplicating hierarchy information, and keeps enum values clean.

**Alternatives Considered**:
- (a) Extend `ActionType` with state values: Rejected because it weakens type safety. A function accepting `ActionType` would silently accept LIQUIDATE as a player action. The asymmetry between player and state actions is fundamental to the game design, not incidental. Mixing them into one enum creates type confusion and bloats the priority tables.
- (b) Union type `PlayerAction | StateAction`: Rejected because the resource profiles are structurally different (CL/SL vs budget/thread/legitimacy). A union obscures this distinction. The two types should never appear in the same typed collection.
- (c) Nested enum (top-level verb enum + sub-verb enum per verb): Rejected because Pydantic serialization of nested enums is awkward. Flat enum with explicit mapping is simpler and equally expressive.
- (d) Prefix naming (`ADMINISTER_FUND`): Replaced by simple naming + VERB_CHILDREN mapping. Prefix convention duplicates hierarchy in both enum names and mapping. Simple names with explicit mapping are cleaner.

**Code Location**: `src/babylon/models/enums.py` (new `StateActionType` enum), `src/babylon/models/entities/state_apparatus_ai.py` (VERB_CHILDREN mapping, `StateAction` model).

---

## R2: FactionBalance State Storage Location

**Context**: FR-C01/C02 require a `FactionBalance` weight vector (summing to 1.0) with a computed dominant faction and stability metric. FR-C04/C05 define shift triggers based on player actions and material conditions. This is global state (one per simulation), not per-organization.

**Decision**: Store as a keyed entry in `context.persistent_data` under the key `"faction_balance"`, using a frozen Pydantic model updated via `model_copy()`.

**Rationale**:
- FactionBalance is global state: one per simulation, not per-StateApparatus. Storing it on individual apparatus nodes would duplicate it or require a "primary apparatus" convention.
- The `persistent_data` pattern is established for cross-tick mutable state in this codebase. Existing users include: `ConsciousnessSystem` (`ideology.py:101-102`) stores `_previous_wages`; `DecompositionSystem` (`decomposition.py:100-101`) stores crisis timing; `FieldDerivativeSystem` (`field_derivative.py:72-73`) stores contradiction history; `ControlRatioSystem` (`control_ratio.py:120-121`) stores phase timing. All use the same `context.persistent_data` dict.
- `CrisisState` from Feature 018 established the precedent of storing complex frozen Pydantic models in `persistent_data` with `model_copy(update={})` for mutations. FactionBalance follows this pattern exactly.
- FactionBalance changes every tick in Layer 3 (consequence propagation), making `persistent_data` the natural location since it persists across ticks but is accessible within the tick context.
- Frozen Pydantic model follows project convention. The weight vector is primitive state (stored); `dominant_faction` and `stability` are computed (derived), satisfying Constitution II.2 (Primitives vs Derived).

**Model shape** (validated):
```python
class FactionBalance(BaseModel):
    model_config = ConfigDict(frozen=True)

    finance_capital: float = Field(default=0.45, ge=0.0, le=1.0)
    security_state: float = Field(default=0.30, ge=0.0, le=1.0)
    settler_populist: float = Field(default=0.25, ge=0.0, le=1.0)
    stability: float = Field(default=1.0, ge=0.0, le=1.0)
    legitimacy: float = Field(default=0.8, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> FactionBalance:
        total = self.finance_capital + self.security_state + self.settler_populist
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Faction weights must sum to 1.0, got {total}")
        return self
```

Shift deltas are clamped per tick to prevent oscillation (max delta per faction per tick configurable in GameDefines, default 0.05). When shifts are applied, all three weights are adjusted and re-normalized, guaranteeing the sum-to-1.0 invariant.

**Alternatives Considered**:
- (a) Store on each StateApparatus node as a graph attribute: Rejected because FactionBalance is global, not per-apparatus. Each apparatus has a `factional_alignment` field (e.g., FBI=SECURITY_STATE per FR-C08), but the balance itself is system-wide. Storing it per-apparatus would require a "canonical" apparatus or redundant copies.
- (b) Store directly on WorldState as a new field: Rejected because WorldState is frozen (`ConfigDict(frozen=True)`) and balance shifts every tick. Adding it to WorldState would require `model_copy()` on the entire WorldState each tick for a single field change. `persistent_data` is the mutable channel.
- (c) Store as a singleton graph node (`_node_type="faction_balance"`): Rejected because FactionBalance is not an entity with edges. It does not participate in graph traversal. It is metadata about the simulation state, not a graph participant. `persistent_data` is semantically correct and avoids polluting the graph namespace with non-entity nodes.

---

## R3: Attention Thread Representation in the Graph

**Context**: FR-A01 through FR-A08 require attention threads with rich state (phase, intel_completeness, observed_subgraph, stickiness, ticks_active, surveillance_method, Sparrow analysis results) that are finite resources created and destroyed by the state AI.

**Decision**: Threads as SEPARATE graph nodes (`_node_type="attention_thread"`) with edges to their targets.

**Rationale**:
- Threads have complex state: `phase` (DORMANT/MONITORING/ACTIVE_INVESTIGATION/DISRUPTION), `intel_completeness` (float, monotonically increasing absent counter-intel per SC-006), `observed_node_ids` (set of discovered nodes), `stickiness` (float, resists reallocation per edge case #2), `ticks_active` (int), `surveillance_method` (enum), plus Sparrow analysis results (centrality rankings, equivalence classes, identified singletons, cutsets). This is too rich for a flat attribute on another node.
- Threads need graph traversal. Key queries: "find all threads targeting org X" (total surveillance pressure), "find all threads owned by apparatus Y" (capacity accounting), "find all threads in territory Z" (heat computation). These are naturally expressed as edge traversals on typed edges.
- Threads are finite resources that can be created, reassigned, and destroyed. First-class graph node identity integrates with the existing `to_graph()`/`from_graph()` serialization pattern. The existing `WorldState.from_graph()` dispatch (`src/babylon/models/world_state.py:265`) already handles multiple `_node_type` values: `social_class`, `territory`, `organization`, `key_figure`. Adding `attention_thread` follows the established pattern.
- One target can have multiple threads from different apparatuses (FBI + local PD both surveilling the same org). Node representation handles this naturally; attribute-on-target representation does not.
- Thread pool size is derived from the sum of `surveillance_capacity` across all StateApparatus nodes (`OrganizationDefines.surveillance_capacity_default` at `defines.py:2018`). FUND and STAFF actions that increase `surveillance_capacity` grow the pool. Detroit 2010 baseline: ~5-8 total threads.

**Edge types**: New `EdgeType` values:
- `TARGETS`: AttentionThread -> target (Organization, Territory, or Community). Carries `surveillance_method`.
- `OWNED_BY`: AttentionThread -> StateApparatus. Thread capacity accounting.

**Alternatives Considered**:
- (a) Store as attributes on target nodes (e.g., `org_node["threads"] = [...]`): Rejected because one target can have multiple threads from different apparatuses, threads have rich state that does not flatten into node attributes, and reverse queries ("which apparatus owns this thread?") require graph edges.
- (b) Store in `persistent_data` as a list: Rejected because Sparrow analysis needs to traverse from thread to target to target's neighbors, which is inherently a graph operation. `persistent_data` does not support edge-based queries.
- (c) Store as XGI hyperedges: Rejected because threads are directed (apparatus -> target) and XGI hyperedges are undirected sets. Threads also have rich per-thread state that does not map to hyperedge attributes cleanly.

**Code Location**: New `AttentionThread` model in `src/babylon/models/entities/attention_thread.py`, with serialization support in `WorldState.to_graph()`/`from_graph()`.

---

## R4: G_observed Construction (State's Partial View)

**Context**: FR-A02 requires the state to operate on `G_observed`, an incomplete and distorted view of the actual graph. Five surveillance methods (FR-A06) have different intelligence yields. FR-A07 enforces observation ceilings per apparatus.

**Decision**: `G_observed` is a DERIVED subgraph extracted from `G_actual` using observation model filters, built fresh each time Sparrow analysis runs on a thread. Not stored persistently.

**Rationale**:
- `G_observed` is a function of: (1) the actual graph `G_actual`, (2) the thread's observation model (which surveillance methods are active), (3) the apparatus's observation ceiling, (4) the target org's topology type (cell topology reduces effective ceiling per FR-A07), (5) accumulated `intel_completeness`. All inputs can change between ticks. Building fresh prevents stale intelligence.
- The spec distinguishes five distortion types (FR-A02): edge type conflation, temporal flattening, informant incentive distortion, cash invisibility, face-to-face blindness. Each is a filter applied during construction. The construction function copies discovered nodes/edges from `G_actual` with distortions applied (e.g., edge type conflation may show a SOLIDARITY edge as TRANSACTIONAL).
- What IS stored persistently on the thread node: `intel_completeness` (grows monotonically absent counter-intel), `observed_node_ids` (which nodes have been "seen"), and `sparrow_results` (latest analysis output). The construction function uses `observed_node_ids` plus the observation model to extract and distort the relevant subgraph from `G_actual`.
- Implemented as a separate `nx.DiGraph` copy, not a NetworkX subgraph view, because distortions modify edge attributes. A subgraph view would reflect `G_actual`; a copy allows divergence. This is the observation gap made concrete.

**Construction algorithm**:
1. Start with thread's `observed_node_ids` (accumulated over time).
2. Extract the subgraph of `G_actual` induced by these nodes.
3. Apply observation ceiling: cap the fraction of edges visible.
4. Apply distortion filters per observation model capabilities.
5. Return the distorted `nx.DiGraph` for Sparrow analysis.

**Surveillance method discovery rules**:

| Method | Reveals | Misses |
|--------|---------|--------|
| SIGNALS | Communication edges, org size estimates | Face-to-face meetings, cash flows, consciousness levels |
| FINANCIAL | Resource flow edges, fundraising sources | Ideology, solidarity strength, cell membership |
| SOCIAL_MEDIA | Public-facing nodes, declared affiliations | Clandestine structure, commitment levels, internal disputes |
| INFORMANT | Internal state (with distortion), leadership identity | Full topology (limited to informant's cell), accurate edge weights |
| PHYSICAL | Face-to-face meeting edges, location data | Digital communication, financial flows, ideology |

**Alternatives Considered**:
- (a) Maintain a persistent shadow graph per thread: Rejected because it duplicates graph state, creates synchronization problems (must update whenever `G_actual` changes), and violates the principle that derived state should be computed, not stored.
- (b) Use edge attributes for visibility (e.g., `edge["visible_to_fbi"] = True`): Rejected because the state sees a DISTORTED view, not just a filtered one. Edge type conflation means the state may see a SOLIDARITY edge as a TRANSACTIONAL edge. Attribute flags cannot represent distortion, only visibility.
- (c) Boolean discovery (node is known or unknown): Rejected because it loses partial information. A node can be in `G_observed` but with incorrect attributes (informant incentive distortion exaggerates threat to maintain relevance).

**Code Location**: `src/babylon/ooda/attention/observation.py` (G_observed construction and distortion filters).

---

## R5: State Budget Modeling

**Context**: FR-D05 requires budget as a binding constraint on state omnipotence. The spec defines revenue from tax (territory economic indicators), federal transfers, and imperial rent pool. Budget is allocated across verb categories per tick, influenced by faction balance.

**Decision**: `StateBudget` as a frozen Pydantic model stored in `context.persistent_data` under key `"state_budget"`, updated via `model_copy()` each tick during Layer 0.

**Rationale**:
- Budget is global state (one per simulation, like FactionBalance). It is not an attribute of any single apparatus. Budget allocation across apparatuses is itself a strategic decision made by the state AI.
- Budget has memory: surplus/deficit carries over between ticks. Revenue is computed each tick from territory economic indicators, but the accumulated balance persists. This rules out pure derivation.
- `persistent_data` is the correct location for cross-tick mutable state that is not an entity with graph edges (same reasoning as R2).
- Layer 0 (automatic metabolism) already exists (`process_layer0()` at `src/babylon/ooda/layer0.py`). Budget revenue computation is a natural extension of Layer 0 processing.
- Frozen model ensures budget is immutable within a tick phase. State AI reads the budget to determine affordability, then a new `StateBudget` with consumed resources is written via `model_copy()` after action resolution.
- Three revenue sources map to the three factional material bases: Finance-Capital controls tax base, Security-State draws federal transfers, Settler-Populist claims imperial rent. Revenue itself is factionally contested.
- Allocation via faction-weighted verb preferences reuses the preference table from FR-C03. The dot product of faction weights and verb preference vectors produces the allocation per verb category.

**Model shape**:
```python
class StateBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_revenue: float = Field(default=100.0, ge=0.0)
    available: float = Field(default=100.0, ge=0.0)
    allocated: dict[str, float] = Field(default_factory=dict)  # verb -> budget share
    deficit_accumulated: float = Field(default=0.0, ge=0.0)
```

**Alternatives Considered**:
- (a) Compute budget fresh from territory economic indicators each tick with no carry-over: Rejected because budget has memory (surplus/deficit carry over). A territory that was wealthy last tick but is now depressed should have accumulated surplus. Purely derived budgets lose this.
- (b) Store per-apparatus: Rejected because budget allocation across apparatuses IS the state AI's strategic decision (FR-D01). Individual apparatus budgets are the output of the AI, not the input.
- (c) Store as a graph node: Rejected for the same reason as FactionBalance (R2): budget is not an entity with edges, it is simulation metadata that does not participate in graph traversal.

---

## R6: LegalFramework Graph Representation

**Context**: FR-B09 requires LEGISLATE to create legal frameworks that modify game rules within a jurisdiction scope. Clarification (2026-03-02) confirms: all legislation persists until explicitly revoked via LEGISLATE(REVOKE). No automatic expiry. Different law types affect different territories and systems (SURVEILLANCE_AUTH increases observation ceiling, ANTI_PROTEST raises Heat generation, EMERGENCY_POWERS doubles thread capacity).

**Decision**: `LegalFramework` as frozen Pydantic model nodes in the graph (`_node_type="legal_framework"`), with edges to affected territories via a new `JURISDICTION` edge type.

**Rationale**:
- Legislation has scope (jurisdiction), effects (modifier values), and lifecycle (created by LEGISLATE, removed by LEGISLATE(REVOKE)). Making them graph nodes enables spatial queries: "what laws affect this territory?" is a simple edge traversal from territory to connected `legal_framework` nodes.
- Laws span multiple territories (e.g., EMERGENCY_POWERS for an entire state jurisdiction). Storing law effects as territory attributes would duplicate data across all affected territories and make revocation expensive (must update every territory).
- Laws have distinct types with different effects: SURVEILLANCE_AUTH increases observation ceiling, ANTI_PROTEST raises Heat generation, EMERGENCY_POWERS doubles thread capacity, ZONING enables DEVELOP. These are structurally different modifiers that benefit from first-class entity representation.
- Laws interact with multiple systems: the attention thread system reads SURVEILLANCE_AUTH to compute effective observation ceiling; the heat system reads ANTI_PROTEST to compute Heat generation modifiers; the OODA system reads EMERGENCY_POWERS to determine LIQUIDATE availability (FR-B10). Graph node representation makes these reads natural traversals.
- REVOKE removes the `LegalFramework` node and its `JURISDICTION` edges. EMERGENCY_POWERS doubling thread capacity is a multiplicative modifier on the pool size formula: if apparatus `surveillance_capacity` sums to 6, EMERGENCY_POWERS makes it 12. Revoking reverts to base sum.

**Model shape**:
```python
class LegalFramework(BaseModel):
    model_config = ConfigDict(frozen=True)

    framework_type: LegalFrameworkType  # SURVEILLANCE_AUTH, ANTI_PROTEST, EMERGENCY_POWERS, etc.
    jurisdiction: JurisdictionLevel
    enacted_tick: int
    enacted_by: str  # StateApparatus org_id
    modifiers: dict[str, float]  # effect_name -> magnitude
    legitimacy_cost: float  # cost paid at enactment
```

**Alternatives Considered**:
- (a) Store as attributes on Territory nodes: Rejected because a single law spans multiple territories. EMERGENCY_POWERS for Michigan affects all Michigan territories. Duplicating the law entity on each territory node wastes space, creates update/revocation complexity, and does not represent the law as a coherent entity.
- (b) Store in `persistent_data` as a list: Rejected because spatial queries ("what laws affect territory T?") require linear scan and manual jurisdiction-to-territory mapping. Graph edges handle this naturally. Additionally, laws need to be discoverable by multiple systems (attention threads, heat, OODA), and graph traversal is the established pattern for cross-system data access.
- (c) Store as XGI hyperedges (law "covers" a set of territories): Rejected because laws are directed (enacted by an apparatus, affecting territories), carry rich state, and interact with the graph protocol's node-based update pattern. Hyperedges are better suited for symmetric community membership.

**Code Location**: New `LegalFramework` model in `src/babylon/models/entities/state_apparatus_ai.py`, with serialization in `WorldState.to_graph()`/`from_graph()`.

---

## R7: Escalation Ladder Implementation

**Context**: FR-D06/D07 require escalation/de-escalation mechanics. The state prefers cheap, low-visibility actions and escalates only when cheaper options fail. The spec provides an explicit ordering (spec.md lines 441-444): `PROPAGANDIZE -> BRIBE -> ... -> SCORCHED_EARTH`.

**Decision**: Ordered preference list in GameDefines (`StateApparatusAIDefines.escalation_ladder`) with cost and visibility scores per sub-verb. The state AI scores candidates against the factional objective function AND escalation position.

**Rationale**:
- The escalation ladder is a game design parameter that should be tunable, not hardcoded. Placing it in GameDefines follows constitution III.1 (no magic constants) and the existing pattern of `OODADefines` storing action costs and weights.
- The scoring function combines two independent dimensions: (1) factional preference (which faction dominates determines which verbs are favored), and (2) escalation position (how costly the verb is in visibility and legitimacy). The final score is a weighted product: `score = factional_preference * escalation_discount(position)`. Low-escalation verbs get a bonus; high-escalation verbs pay a penalty unless the threat level justifies it.
- De-escalation (FR-D07) emerges naturally from this design: when threat subsides, cheaper actions score higher because the factional objective function rewards stability (Finance-Capital) over threat suppression (Security-State). The escalation ladder provides the ordering; the faction weights determine where on the ladder the state operates.
- Each sub-verb in the ladder has three tunable costs: `base_budget_cost` (currency), `legitimacy_cost` (float), `visibility` (float). Higher-escalation verbs cost more in all three dimensions. These costs are the binding constraints that prevent the AI from jumping straight to LIQUIDATE.

**Data shape in GameDefines**:
```python
class EscalationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub_verb: str
    position: int  # 0 = lowest escalation, higher = more extreme
    base_budget_cost: float
    legitimacy_cost: float
    visibility: float  # 0.0 = invisible, 1.0 = maximum public attention
```

**Alternatives Considered**:
- (a) Hardcode the escalation order: Rejected per constitution III.1. Game designers should be able to reorder escalation steps without code changes.
- (b) Let the factional objective function implicitly determine order: Rejected because escalation logic is orthogonal to faction preference. Even Finance-Capital escalates to REPRESS when profit rate crashes. Without an explicit ladder, the AI would jump directly to LIQUIDATE whenever its objective function scored it highest, producing unrealistic behavior. The ladder constrains the AI's action space independently of which faction dominates.
- (c) Simple list without per-entry costs: Rejected because different sub-verbs have different resource profiles. PROPAGANDIZE is cheap in budget but costs thread time; RAID is expensive in budget and legitimacy. Per-entry cost profiles are essential for resource-constrained decision-making.

**Code Location**: `src/babylon/config/defines.py` (new `StateApparatusAIDefines` sub-model within `GameDefines`).

---

## R8: NPCDecisionStrategy Protocol Structure

**Context**: FR-D09 requires a hot-swappable decision strategy. The existing `select_npc_actions()` in `npc_stub.py` is a bare function, not a protocol. Feature 039 needs a protocol that allows the rule-based state AI stub to be swapped for an LLM-backed strategy in the future.

**Decision**: Protocol with single method `select_action(world_view, org_id, org_attrs, context) -> StateAction | None`, with `DefaultStateAIStrategy` implementing the factional objective function.

**Rationale**:
- Single-method protocol keeps the interface narrow and focused. The OODA loop (Observe/Orient/Decide/Act) is an internal implementation detail of `DefaultStateAIStrategy`, not part of the protocol contract. A future LLM strategy might skip the explicit OODA decomposition entirely.
- Returning `StateAction | None` (not a list): FR-D05 specifies "exactly one action" per tick (configurable). `None` means "no action this tick" (budget exhausted or no target worth acting on). Multi-action support (future) would be handled by calling the method multiple times per tick with decreasing budget, not by changing the return type.
- `world_view` parameter is an `ObservedWorldState` (the state's partial view), not the raw graph. This enforces the observation gap at the protocol level: strategies can only see what the attention threads have revealed. The raw graph is never passed to the strategy.
- The existing `select_npc_actions()` continues to exist for non-state NPC org types (PoliticalFaction, CivilSocietyOrg, Business). The state AI strategy replaces ONLY the state apparatus decision path.

**Protocol shape**:
```python
class NPCDecisionStrategy(Protocol):
    def select_action(
        self,
        world_view: ObservedWorldState,
        org_id: str,
        org_attrs: dict[str, Any],
        context: TickContext,
    ) -> StateAction | None: ...
```

**Integration point**: In `OODASystem.step()` (`src/babylon/engine/systems/ooda.py:146-155`), the current code path `select_npc_actions(org_id, org_attrs, target_id, defines)` for `STATE_APPARATUS` orgs is replaced with `strategy.select_action(world_view, org_id, org_attrs, context)`. The strategy is injected via `ServiceContainer` (dependency injection), consistent with how `defines` and `event_bus` are already provided. Non-state orgs continue using `select_npc_actions()`.

**Alternatives Considered**:
- (a) Multi-method protocol (separate `observe()`, `orient()`, `decide()`, `act()` methods): Rejected because OODA is the internal structure of one specific strategy implementation (rule-based), not a universal contract. An LLM strategy would receive the world view and return an action in a single call. Forcing all implementations through four-phase decomposition over-constrains the interface.
- (b) Return `list[StateAction]`: Rejected because FR-D05 specifies one action per tick (default). Returning a list invites multi-action at the protocol level, which should be the caller's responsibility (call N times with decreasing budget).
- (c) Modify existing `select_npc_actions()` signature: Rejected because the function handles all org types. Overloading it with state-specific logic (faction balance, budget, attention threads) would violate SRP. The function signature (`org_attrs: dict, target_id: str, defines: OODADefines`) is inadequate for state AI which needs `FactionBalance`, `StateBudget`, `ObservedWorldState`.

**Code Location**: `src/babylon/ooda/state_ai/protocols.py` (protocol), `src/babylon/ooda/state_ai/decision.py` (default implementation).

---

## R9: Territory Effects from DEVELOP/WITHDRAW

**Context**: FR-E08 defines DEVELOP effects (INVEST, REZONE, DISPLACE, NEGLECT) on territories. FR-E09 defines WITHDRAW effects (STRATEGIC_WITHDRAWAL, TACTICAL_RETREAT, SCORCHED_EARTH). Territories are already graph nodes with mutable attributes via `GraphProtocol.update_node()`.

**Decision**: Effects applied as territory node attribute mutations via `GraphProtocol.update_node()`, following the existing copy-modify-writeback pattern. Each sub-verb targets specific attributes.

**Attribute mappings per sub-verb**:
- **INVEST**: Raises `property_value_proxy` (configurable delta per tick), which increases `V_reproduction` for residents. Creates gentrification pressure. The existing `V_reproduction` calculation in the economic subsystem already reads `property_value_proxy` from territory nodes, so INVEST effects propagate automatically.
- **REZONE**: May shift territory toward different development type. Requires prior LEGISLATE(ZONING).
- **DISPLACE**: Removes population (reduces `population`), severs `TENANCY` edges for displaced residents, degrades `community_infrastructure`. Follows the existing eviction pipeline pattern from TerritorySystem (Feature 007).
- **NEGLECT**: Degrades `infrastructure_quality` via exponential decay (`quality *= (1 - decay_rate)`) per tick toward a configurable floor. Also decays `property_value_proxy` slowly and reduces `service_level`.
- **STRATEGIC_WITHDRAWAL**: Removes `PRESENCE` edges for state apparatus, sets state investment to zero, applies accelerated NEGLECT decay. Player inherits a territory with degraded infrastructure.
- **SCORCHED_EARTH**: Sets `infrastructure_quality` to 0.0, destroys `community_infrastructure`, applies population displacement.

**Rationale**:
- Territory is already a graph node with mutable attributes. The existing pattern (used by `TerritorySystem`, `ControlRatioSystem`, `StruggleSystem`) is: read attributes from node, compute new values, write back via `graph.update_node(territory_id, attr=new_value)`. DEVELOP/WITHDRAW effects follow this pattern exactly.
- Effects are applied in Layer 1 (action resolution) of the OODA tick, consistent with how player actions are resolved. Layer 3 propagates consequences (consciousness shifts from displacement, heat changes from development).
- New territory attributes (`property_value_proxy`, `infrastructure_quality`, `service_level`, `community_infrastructure`) are managed as graph-only attributes, not Territory model fields. This follows the existing pattern where `heat` is a graph attribute managed by TerritorySystem, not a Territory model field.

**Alternatives Considered**:
- (a) Create new `TerritoryEffect` event types for each verb: Events are per-tick notifications consumed by observers; they do not represent persistent state changes. INVEST raises property values persistently, not just for one tick. Events should be emitted alongside the mutation (for observer/narrative consumption), but the mutation itself is a graph attribute update.
- (b) Modify the Territory Pydantic model to add all new attributes: The Territory model is frozen. Adding fields would require changes to `WorldState.to_graph()`/`from_graph()` and downstream systems that construct Territory objects. Graph-only attributes are the lighter approach and follow the `heat` precedent.
- (c) Single "DEVELOP" effect applied uniformly: The four sub-verbs have qualitatively different effects. A single numeric `development_level` would obscure whether the state is building up or tearing down.

**Code Location**: `src/babylon/ooda/state_ai/` (resolve functions for DEVELOP/WITHDRAW sub-verbs), effects applied to territory graph nodes via GraphProtocol.

---

## R10: Consciousness Geography (Spatial Variation of Collective Identity)

**Context**: FR-E04 requires consciousness to vary spatially: EDUCATE in Territory A affects community members in Territory A first, then diffuses community-wide via solidarity edges.

**Decision**: Consciousness varies by territory through community hyperedge membership + territory intersection. This is a DERIVED computation, not new stored state.

**Rationale**:
- Community consciousness is already modeled via XGI hyperedge membership (Feature 029, `src/babylon/community/`). Each community has `collective_identity` as a community-level attribute.
- Territory intersection is computable from existing graph structure: community members (SocialClass blocks) have `TENANCY` edges to territories. To compute "consciousness in Territory A", filter community members by those with `TENANCY` edges to Territory A, then compute their weighted contribution to the community's `collective_identity`.
- EDUCATE locality: when the state AI or player applies EDUCATE targeting a territory, the consciousness delta is weighted by the fraction of the target community that has `TENANCY` in that territory. If 80% of Community X lives in Territory A, EDUCATE in Territory A reaches 80% of Community X. The remaining 20% receives a diffused effect via SOLIDARITY edges (existing transmission mechanic from Feature 008, `SolidaritySystem`).
- No new stored state is required. The territory-specific consciousness value is derived each time it is needed (for threat assessment, EDUCATE targeting, heat computation). This follows Constitution II.2 (Primitives vs Derived).

**Computation sketch**:
```python
def territory_consciousness(
    community_id: str, territory_id: str, graph: nx.DiGraph
) -> float:
    """Fraction of community members in territory, weighted by population."""
    community_members = get_community_members(community_id, graph)  # set of node IDs
    territory_residents = get_tenants(territory_id, graph)  # set of node IDs via TENANCY edges
    overlap = community_members & territory_residents
    if not community_members:
        return 0.0
    return len(overlap) / len(community_members)
```

The state AI's threat assessment multiplies this territorial fraction by the community's `collective_identity` to get territory-level threat: `threat = community_ci * territory_fraction`.

**Alternatives Considered**:
- (a) Store per-territory consciousness values as territory node attributes: Rejected because consciousness belongs to communities, not territories. A territory has no consciousness of its own; it is a geographic container. What the state perceives as "territory consciousness" is the projection of community consciousness onto geographic space. Storing it on territories would duplicate community state and create synchronization issues.
- (b) Ignore spatial variation entirely: Rejected because FR-E04 explicitly requires it, and it is essential for the DEVELOP/WITHDRAW mechanic. Displacement is only meaningful if consciousness has spatial structure. Without spatial variation, DISPLACE in Territory A has no different consciousness effect than DISPLACE in Territory B.

**Code Location**: Helper function in `src/babylon/ooda/attention/intelligence.py` (used by threat assessment) and `src/babylon/ooda/state_ai/effects.py` (used by EDUCATE locality).

---

## R11: God Mode Debug Toggle

**Context**: FR-D12 requires a debug toggle that exposes all state internals (faction weights, budget, thread targets, AI scoring) to the player for testing and development.

**Decision**: Boolean flag in GameDefines (`StateApparatusAIDefines.god_mode_enabled = False`), checked by the event emission layer to decide whether state internal events are included in the player-visible event stream.

**Rationale**:
- `GameDefines` is the canonical location for all configuration flags. The flag is loaded from `defines.yaml` and is accessible throughout the simulation via `services.defines.state_ai.god_mode_enabled`.
- The simplest possible toggle: a boolean. When enabled, the state AI emits additional events with full internal state as event payload. When disabled, these events are suppressed at the emission point. The AI logic itself is identical regardless of the flag. Only the event emission layer checks the flag.
- Testable in pytest: `GameDefines(state_ai=StateApparatusAIDefines(god_mode_enabled=True))` enables full visibility in test assertions without environment variable hacks or monkeypatching.

**New EventType values** (emitted only when `god_mode_enabled`):
- `STATE_AI_DECISION`: Contains verb selection scoring, faction objective values, budget state.
- `FACTION_BALANCE_SHIFT`: Contains old and new weights, triggering conditions.
- `THREAD_ALLOCATION`: Contains thread assignments, priority scores, intel_completeness per thread.
- `STATE_BUDGET_UPDATE`: Contains revenue, allocation, deficit state.

**Additional EventType values** (emitted always, player-observable):
- `STATE_ACTION_EXECUTED`: After any state verb resolves. Contains verb, sub_verb, target, observable effects.
- `LEGISLATION_ENACTED`: When LEGISLATE creates a framework. Contains framework_type, jurisdiction.
- `LEGISLATION_REVOKED`: When LEGISLATE(REVOKE) removes a framework.
- `DISPLACEMENT_CASCADE`: When DISPLACE triggers population movement. Contains territory, population affected.

**Alternatives Considered**:
- (a) Separate debug service injected via DI: Over-engineered for a boolean toggle. A debug service would need its own protocol, implementation, and registration for what is ultimately "emit or don't emit."
- (b) Environment variable (`BABYLON_GOD_MODE=1`): Not testable in pytest without monkeypatching. `GameDefines` is already the mechanism for passing configuration to the simulation. Environment variables bypass the type-safe configuration system.
- (c) EventBus interceptor that filters god-mode events: Viable but inverted. It is simpler to not emit the events in the first place than to emit them and then filter them out. The interceptor pattern (`src/babylon/engine/interceptor.py`) is designed for adversarial event modification (counter-intel blocking events), not debug visibility.

**Code Location**: Flag in `src/babylon/config/defines.py` (`StateApparatusAIDefines`). Emission checks in `src/babylon/ooda/state_ai/decision.py` (decision logging) and `src/babylon/ooda/state_ai/effects.py` (effect logging).

---

## R12: Integration with Existing OODA System

**Context**: The OODA system (`src/babylon/engine/systems/ooda.py`) currently handles all org types in a single `step()` method. State apparatus orgs use `select_npc_actions()` from `npc_stub.py` (lines 151-155). Feature 039 replaces this path with the state AI strategy.

**Decision**: No new system registration. All Feature 039 logic executes within the existing OODASystem's three-phase structure. State apparatus orgs use the `NPCDecisionStrategy` protocol; all other org types continue using `select_npc_actions()`.

**Phase integration**:
- **Layer 0** (extended): Budget revenue computation added to existing `process_layer0()`.
- **Action Phase** (branched): State apparatus orgs dispatched to `NPCDecisionStrategy.select_action()` instead of `select_npc_actions()`. Non-state orgs continue using the existing priority queue stub. State actions resolve in initiative order alongside other org actions.
- **Layer 3** (extended): Faction balance shift computation, legitimacy updates, and budget reconciliation added to existing `process_layer3()`.

**Rationale**:
- The OODASystem already runs at position 14 in `_DEFAULT_SYSTEMS` (between MetabolismSystem and SurvivalSystem per Feature 032 R6). This position ensures: economic base (systems 1-13) is computed before the state AI reads it; state actions resolve before SurvivalSystem and ConsciousnessSystem propagate their effects.
- The initiative score mechanism already handles inter-org ordering. State apparatus orgs participate in the same initiative ordering (they already have `OODAProfile` and `institutional_bonus`). Adding a parallel system would bypass initiative ordering for state actions.
- The existing code already branches on org type: Business orgs are skipped in the action phase (`ooda.py:130-131`). Adding a state apparatus branch follows the same pattern.

**Modified code path** (conceptual):
```python
# In OODASystem.step(), action resolution loop:
if org_data.get("org_type") == OrgType.STATE_APPARATUS.value:
    state_action = services.state_ai_strategy.select_action(
        world_view, score.org_id, org_data, context,
    )
    if state_action is not None:
        result = resolve_state_action(state_action, graph, services)
        action_phase_results.append(result)
else:
    # Existing NPC stub path for non-state orgs
    npc_actions = select_npc_actions(...)
```

**Alternatives Considered**:
- (a) Register a separate `StateAISystem` at a new position: Rejected because the state AI's actions must be initiative-ordered alongside player/NPC actions. A separate system would either duplicate initiative ordering or bypass it.
- (b) Replace `select_npc_actions()` entirely: Rejected because the function still serves non-state NPCs (PoliticalFaction, CivilSocietyOrg, Business). Only the STATE_APPARATUS path changes.

---

## R13: GameDefines Extension — StateApparatusAIDefines

**Context**: Constitution III.1 (No Magic Constants) and FR requirements specify numerous configurable thresholds, effect floors, observation ceilings, and faction verb preferences. Features 031 and 032 established `OrganizationDefines` (14 params) and `OODADefines` (30+ params).

**Decision**: New `StateApparatusAIDefines` frozen Pydantic sub-model in `GameDefines`, separate from `OrganizationDefines` and `OODADefines`.

**Rationale**:
- `OrganizationDefines` covers all org types (consciousness tendency modifiers, cohesion, credibility). State AI parameters are specific to the state apparatus adversary system.
- `OODADefines` covers cycle time, initiative, action costs: the generic OODA framework. State AI parameters are about factional politics, escalation preferences, and intelligence allocation: a different concern.
- Separation follows the existing pattern: `GameDefines` has ~30 sub-sections, each scoped to a specific subsystem.

**Parameter groups**:

| Category | Key Parameters | Count |
|----------|---------------|-------|
| Faction defaults | `initial_fc_weight`, `initial_ss_weight`, `initial_sp_weight` | 3 |
| Faction shift limits | `max_faction_shift_per_tick` (0.05), `min_effect_floor` (0.02) | 2 |
| Faction shift rates | `heat_ss_shift`, `extraction_disruption_fc_shift`, `legitimacy_coop_fc_shift`, `repression_failure_ss_shift` | 4 |
| Faction verb preferences | 3x6 matrix (FC, SS, SP x 6 verbs) as nested dict | 18 |
| Fascist convergence | `ss_convergence_threshold` (0.4), `settler_ci_threshold` (0.6), `fc_acquiescence_threshold` (0.25), `convergence_confirmation_ticks` (2), `reversion_ss_threshold` (0.25), `reversion_ci_threshold` (0.3) | 6 |
| Escalation ladder | Ordered list of `EscalationEntry` (~24 entries) | ~24 |
| Thread allocation | `base_thread_capacity`, `thread_allocation_stickiness`, `meta_ooda_interval` | 3 |
| Budget | `base_revenue`, `deficit_carry_rate`, `budget_verb_allocation_default` | 3 |
| Effect sizes | `invest_property_delta`, `neglect_decay_rate`, `neglect_quality_floor`, `displace_population_fraction` | 4 |
| Debug | `god_mode_enabled` (False) | 1 |

**Total**: ~68 parameters. Comparable in scale to `OODADefines` (~35 params) and `BifurcationDefines` (~20 params).

All Detroit 2010 initialization values are flagged as SYNTHETIC in docstrings per Assumption A-006 and Constitution III.4 (Data Source Traceability).

**Alternatives Considered**:
- (a) Merge into `OrganizationDefines`: Rejected because OrganizationDefines serves ALL org types. State AI parameters are adversary-specific. Merging would bloat OrganizationDefines from 14 to 82+ params.
- (b) Merge into `OODADefines`: Rejected because OODADefines covers the generic action framework. The state's factional objective function and escalation ladder are game design parameters, not OODA framework parameters.
- (c) Multiple sub-models (FactionDefines, ThreadDefines, EscalationDefines): Considered but rejected as premature fragmentation. One `StateApparatusAIDefines` with clear category comments is more discoverable. Can be split later if it grows beyond ~100 params.

**Code Location**: `src/babylon/config/defines.py` (new `StateApparatusAIDefines` class, new `state_ai` field on `GameDefines`).

---

## R14: Existing Code Reuse Assessment

**Context**: Per CLAUDE.md DRY Super Rule: before writing ANY new code, search for existing code to reuse. What existing code can Feature 039 leverage directly?

| Requirement | Existing Code | File Path | Reuse Plan |
|-------------|---------------|-----------|------------|
| FR-A03 (Sparrow analysis) | `find_critical_singletons()`, `compute_equivalence_classes()`, `compute_purge_resilience()`, `find_critical_cutsets()` | `src/babylon/bifurcation/resilience.py` | Direct reuse: these functions operate on arbitrary subgraphs; pass `G_observed` |
| FR-A07 (Observation ceiling) | `observation_ceiling_local_pd`, `observation_ceiling_fusion`, `observation_ceiling_fbi` | `src/babylon/config/defines.py:1948-1965` | Direct reuse: read existing GameDefines parameters |
| FR-C06 (Fascist convergence) | `_compute_legitimation_index()`, `BifurcationResult.legitimation_index` | `src/babylon/bifurcation/analysis.py:279`, `types.py:151` | Extend: add fascist convergence detector that reads legitimation_index + faction balance |
| FR-D05 (Initiative ordering) | `compute_initiative_score()`, `resolve_action_order()` | `src/babylon/ooda/initiative.py` | Direct reuse: state orgs participate in same initiative ordering |
| FR-D08 (Determinism) | `OODASystem.step()` | `src/babylon/engine/systems/ooda.py` | Direct reuse: existing system is already deterministic given seed |
| FR-E01 (PRESENCE edges) | `EdgeType.PRESENCE` | `src/babylon/models/enums.py` | Direct reuse: already exists from Feature 031 |
| FR-E02 (Heat mechanics) | TerritorySystem heat computation | `src/babylon/engine/systems/territory.py` | Extend: add thread allocation as heat source |
| FR-E04 (Consciousness geography) | Community membership queries | `src/babylon/community/` | Reuse: compute territory intersection from existing TENANCY edges |
| FR-E06 (Eviction cascade) | TerritorySystem displacement pipeline | `src/babylon/engine/systems/territory.py` | Extend: trigger from DISPLACE sub-verb |
| FR-F01 (StateApparatus model) | `StateApparatus` class with jurisdiction, violence_capacity, surveillance_capacity, intel_methodology | `src/babylon/models/entities/organization.py:211-247` | Extend: add `factional_alignment` field |
| FR-F02 (EventBus) | `EventBus.publish()`, interceptor chain | `src/babylon/engine/event_bus.py` | Direct reuse: emit state events through existing bus |
| FR-F03 (BifurcationMonitor) | `TopologyMonitor`, `BifurcationResult` | `src/babylon/bifurcation/` | Extend: add fascist convergence as monitored condition |

**DRY Assessment**: 6 of 12 requirements can reuse existing code directly. 5 require extending existing code. 1 requires a new module only (state AI strategy). 0 require rewriting existing code.
