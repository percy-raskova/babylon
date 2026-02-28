# Research: OODA Loop System (Feature 032)

**Feature Branch**: `032-ooda-loop-system`
**Date**: 2026-02-28

## R1: Action Vocabulary Alignment (Constitution V vs Spec FR-009)

### Question

The constitution defines 9 player verbs and 6 state verbs. The spec defines 21 action types. How do these map?

### Findings

**Player Verbs (Constitution V) -> Spec Action Types**:

| Player Verb | Maps To | Notes |
|-------------|---------|-------|
| Educate | EDUCATE | Direct 1:1 |
| Aid | PROVIDE_SERVICE | "Aid" is the player-facing name |
| Attack | EXPROPRIATE, ATTACK_INFRASTRUCTURE | Two attack modes: seize resources or destroy infrastructure |
| Mobilize | AGITATE, PROTEST, STRIKE | Mobilization spectrum: consciousness → demonstration → economic action |
| Campaign | PROPAGANDIZE | Campaign = sustained propaganda effort |
| Move | (not in spec) | Spatial movement is implicit in territory_ids, not an action type |
| Investigate | MAP_NETWORK, COUNTER_INTEL | Player intelligence: map state networks or build counter-intelligence |
| Reproduce | RECRUIT, ORGANIZE | Organizational reproduction: grow membership, build structure |
| Negotiate | PROPOSE_ALLIANCE, DENOUNCE | Diplomacy: positive (alliance) or negative (denounce) |

**State Verbs (Constitution V) -> Spec Action Types**:

| State Verb | Maps To | Notes |
|------------|---------|-------|
| Administer | (Layer 0 automatic) | State administration is metabolism, not an OODA action |
| Develop | BUILD_INFRASTRUCTURE | State infrastructure investment |
| Research | (not in spec) | Deferred to future features |
| Co-opt | ASSIMILATE, EMPLOY | Assimilation (ideological) and employment (material) as co-optation |
| Repress | REPRESS, SURVEIL, INFILTRATE | Repression escalation ladder |
| Withdraw | (not in spec) | Strategic withdrawal deferred — requires coalition/territory mechanics |

**Missing from spec**: Move and Withdraw are territorial/strategic verbs not yet needed. Research is a state-only verb deferred to future features.

**Extra in spec**: FUNDRAISE (organizational resource generation) has no direct constitutional verb but falls under "Reproduce" (resource reproduction for the organization).

### Decision

The 21 action types are a valid decomposition of the constitutional vocabulary. Move and Withdraw are scope exclusions. FUNDRAISE maps to organizational reproduction. No constitution violation.

### Alternatives Considered

1. **Exact 1:1 mapping**: Rejected because the constitutional verbs are player-facing abstractions while action types are engine-level primitives. Many verbs decompose into multiple actions.
2. **Fewer action types**: Rejected because collapsing (e.g., REPRESS + SURVEIL into one) loses the escalation ladder semantics required by Constitution V.

---

## R2: Initiative Score Formula Design

### Question

How should the initiative score be computed from its five components (cycle_time, institutional_bonus, counter_intelligence, community_embeddedness, momentum)?

### Findings

The spec requires (FR-002):
- Faster OODA cycle = higher initiative
- State starts with high institutional bonus
- Non-state can overcome state advantage through counter-intel, community support, momentum
- Federal > state > local for institutional bonus (FR-042)
- Dynamic, contested, not fixed (FR-044)

**Design: Additive composite with normalization**

```
initiative_score = (
    w_speed * (1.0 / cycle_time) +          # Faster = higher
    w_institutional * institutional_bonus +    # State advantage (erodes)
    w_counterintel * counter_intel_score +     # Reduces state advantage
    w_embeddedness * community_embeddedness +  # Local support
    w_momentum * momentum                     # Recent success
)
```

Where all `w_*` weights are in `GameDefines.ooda`.

**Institutional bonus by jurisdiction** (initial values, tunable):
- `FEDERAL`: 5.0 (FBI, ATF — very high, hard to overcome)
- `STATE`: 3.0 (State police, national guard)
- `LOCAL`: 1.5 (Local PD — can be overcome by organized movement)
- Non-state default: 0.0

**Component derivations**:
- `cycle_time`: Computed from OODAProfile (see R3)
- `counter_intel_score`: Accumulated from successful COUNTER_INTEL actions (stored on org node)
- `community_embeddedness`: Average membership overlap with org's territory communities
- `momentum`: Decaying accumulator of recent successful actions (e.g., `momentum = momentum * decay + success_bonus`)

### Decision

Additive composite formula. All weights in GameDefines. Institutional bonus as the primary state advantage, with three levers (counter-intel, embeddedness, momentum) plus OODA speed for non-state organizations to contest it.

### Alternatives Considered

1. **Multiplicative formula**: Rejected because zero in any component would zero the entire score, which is too punishing.
2. **Fixed layer ordering**: Rejected by spec clarification — the spec explicitly moves away from "state always first."
3. **Random component**: Rejected because Constitution II.5 requires reproducibility and III.2 requires falsifiability.

---

## R3: Cycle Time Computation

### Question

How should cycle_time be computed from the four OODA phases?

### Findings

The spec requires (FR-006): AUTOCRATIC < DELEGATE < DEMOCRATIC < CONSENSUS for cycle time.

**Design: Weighted sum of phase durations**

```
cycle_time = (
    observe_time +    # = base_observe + sensor_latency * latency_weight
    orient_time +     # = base_orient * (1.0 - ideological_coherence * coherence_weight)
    decide_time +     # = decision_mode_base[mode] * (1.0 + bureaucratic_depth * depth_weight)
    act_time          # = base_act / (1.0 + coordination * coord_weight)
)
```

**Decision mode base values** (configurable in GameDefines):
- AUTOCRATIC: 1.0 (fastest — one person decides)
- DELEGATE: 2.0 (moderate — trusted delegates)
- DEMOCRATIC: 3.0 (slower — majority deliberation)
- CONSENSUS: 5.0 (slowest — full consensus required)

**Orient phase**: Higher `ideological_coherence` reduces orient time (coherent orgs orient faster per FR acceptance scenario 2.2).

**Decide phase**: Higher `bureaucratic_depth` increases decide time (more layers = slower decisions).

**Act phase**: `coordination_range` and `autonomy` affect act duration but are mainly enforcement constraints, not cycle time contributors.

### Decision

Additive four-phase model. Each phase has a base time modulated by the relevant profile attribute. All base values and weights in GameDefines.

### Alternatives Considered

1. **Single lookup table**: Rejected because it loses the compositional nature of OODA — each phase should contribute independently.
2. **Multiplicative phases**: Rejected because one zero-time phase shouldn't collapse total cycle time to zero.

---

## R4: Action-Consciousness Coupling

### Question

How should the consciousness effect contract (Feature 031) be extended for action-type-specific effects?

### Findings

Feature 031's `consciousness_effect()` computes a base delta from `tendency_modifier * cadre_level * cohesion * credibility`. The contract explicitly notes (line 227): "Phase 2 OODA system will provide per-action-type multipliers."

**Design: Action base multiplier**

Each action type has an `action_base` coefficient that scales the consciousness effect:

| Action Type | action_base | Rationale |
|-------------|-------------|-----------|
| EDUCATE | 1.2 | Primary consciousness-raising action |
| AGITATE | 0.0 (special) | Increases contestation, not CI directly |
| PROVIDE_SERVICE | 0.6 | Material aid with ideological side-effect |
| RECRUIT | 0.3 | Recruitment has minor consciousness effect |
| ORGANIZE | 0.5 | Organizational building raises consciousness |
| REPRESS | -0.8 (special) | State repression increases CI (backfire effect) |
| SURVEIL | -0.2 (special) | Surveillance slightly increases CI (paranoia → solidarity) |
| ASSIMILATE | -1.0 (special) | Actively destroys CI |
| PROPAGANDIZE | 0.8 | Mass communication, less targeted than EDUCATE |
| Others | 0.0 | No consciousness side-effect |

"Special" values bypass the standard formula — AGITATE modifies `ideological_contestation` not `collective_identity`. REPRESS and SURVEIL produce negative `action_base` applied to the STATE's tendency but positive CI effect on the target (backfire). ASSIMILATE directly reduces CI.

**Credibility modification**: The existing credibility derivation is extended with membership overlap. For any consciousness-affecting action:
```
effective_credibility = base_credibility * membership_overlap_factor
```
Where `membership_overlap_factor` is the proportion of the target community that are members of the acting org (0.0 to 1.0). Zero overlap = near-zero effect (FR-020).

### Decision

Extend the existing consciousness_effect formula with an `action_base` multiplier per action type. All multipliers in GameDefines. Credibility incorporates membership overlap. Special actions (AGITATE, REPRESS, SURVEIL, ASSIMILATE) have custom resolution paths.

### Alternatives Considered

1. **Completely separate formula per action**: Rejected because it duplicates the five-factor product and violates DRY.
2. **Same formula for all actions**: Rejected because EDUCATE should have a stronger consciousness effect than FUNDRAISE.

---

## R5: Community-Modified Action Costs

### Question

How should action costs vary based on org-community relationship?

### Findings

The spec requires:
- Shared membership reduces cost (FR-021)
- Contradiction pair increases cost significantly (FR-022)
- No membership = higher cost + credibility penalty (FR-023)

**Design: Cost modifier lookup**

```
effective_cost = base_cost * cost_modifier(org, target_community, action_type)
```

**Modifier computation**:
```python
def compute_cost_modifier(membership_overlap, is_contradiction_pair, action_type):
    if membership_overlap > 0:
        # Embedded: discount proportional to overlap
        return max(min_cost_modifier, 1.0 - membership_overlap * embeddedness_discount)
    elif is_contradiction_pair:
        # Across contradiction axis: significant surcharge
        return contradiction_cost_multiplier  # e.g., 2.5x
    else:
        # No membership but no contradiction: moderate surcharge
        return outsider_cost_multiplier  # e.g., 1.5x
```

All modifier values (`embeddedness_discount`, `contradiction_cost_multiplier`, `outsider_cost_multiplier`, `min_cost_modifier`) in GameDefines.

### Decision

Three-tier cost modification: embedded (discount), outsider (surcharge), contradiction (heavy surcharge). Membership overlap determines the embedded discount magnitude. All values configurable.

---

## R6: System Registration Position

### Question

Where should OODASystem be positioned in the `_DEFAULT_SYSTEMS` execution order?

### Findings

Current system order (20 systems):
1. VitalitySystem
2. TerritorySystem
3. ProductionSystem
4. TickDynamicsSystem
5. ReserveArmySystem
6. CommunitySystem
7. LifecycleSystem
8. SolidaritySystem
9. ImperialRentSystem
10. DispossessionEventSystem
11. DecompositionSystem
12. ControlRatioSystem
13. MetabolismSystem
14. SurvivalSystem
15. StruggleSystem
16. ConsciousnessSystem
17. ContradictionSystem
18. ContradictionFieldSystem
19. FieldDerivativeSystem
20. EdgeTransitionSystem

The OODA system needs to:
- Run AFTER economic systems (1-13) because Layer 0 depends on economic state already computed
- Run AFTER CommunitySystem (6) and LifecycleSystem (7) because it reads community and lifecycle state
- Run BEFORE or concurrent with ConsciousnessSystem (16) — Layer 3 propagation includes consciousness updates

**Design**: Insert OODASystem at position 14 (after MetabolismSystem, before SurvivalSystem). Rationale:
- Economic base (systems 1-13) is fully computed
- Community state and lifecycle composition available
- OODA actions (including consciousness effects) resolve before the broader ConsciousnessSystem, which handles non-organizational consciousness drift
- Survival calculations (system 14→15) can then incorporate organizational action effects

### Decision

Register OODASystem at position 14 in `_DEFAULT_SYSTEMS`, between MetabolismSystem and SurvivalSystem.

### Alternatives Considered

1. **After all existing systems (position 21)**: Rejected because SurvivalSystem and ConsciousnessSystem should see OODA effects.
2. **Before economic systems**: Rejected because Layer 0 depends on economic state.

---

## R7: OODAProfile Storage

### Question

How should OODAProfile be stored on organization graph nodes?

### Findings

Organizations are stored as graph nodes with `_node_type="organization"`. All model fields are serialized as flat attributes via `model_dump()`.

**Pattern from Feature 031**: Organization fields are stored directly on the node:
```python
graph.update_node(org_id, cohesion=0.5, cadre_level=0.3, ...)
```

**DPDState pattern from Feature 030**: Complex nested state is stored as a serialized dict:
```python
graph.update_node(territory_id, dpd_state=dpd_state.model_dump())
# Read back:
dpd_data = attrs.get("dpd_state")
if dpd_data:
    dpd_state = DPDState(**dpd_data)
```

### Decision

Follow the DPDState pattern. Store OODAProfile as a serialized dict on the organization node:
```python
graph.update_node(org_id, ooda_profile=profile.model_dump())
```

This keeps the OODAProfile as a cohesive unit and avoids polluting the flat attribute namespace with 8+ individual OODA fields (sensor_latency, ideological_coherence, analytical_capacity, decision_mode, bureaucratic_depth, action_points, coordination_range, autonomy).

**Initiative-related dynamic state** (counter_intel_score, momentum) stored as separate flat attributes since they change independently:
```python
graph.update_node(org_id, counter_intel_score=0.3, momentum=0.1)
```

---

## R8: NPC Action Selection Stub

### Question

How should the NPC stub select actions (FR-038)?

### Findings

The spec requires "simple priority rules" — not AI, not random, deterministic.

**Design: Priority queue by org type**

Each org subtype has a fixed priority list of preferred actions. The stub:
1. Gets the org's preferred action list
2. Filters by eligibility (action_eligibility module)
3. Filters by affordability (action_points remaining)
4. Selects top N actions that fit within action_point budget

**Default priorities**:
- StateApparatus: SURVEIL, REPRESS, INFILTRATE, ASSIMILATE
- PoliticalFaction (REVOLUTIONARY): EDUCATE, AGITATE, ORGANIZE, RECRUIT
- PoliticalFaction (LIBERAL): PROPAGANDIZE, PROVIDE_SERVICE, RECRUIT
- PoliticalFaction (FASCIST): AGITATE, RECRUIT, PROPAGANDIZE
- CivilSocietyOrg: PROVIDE_SERVICE, EDUCATE, FUNDRAISE
- Business: EMPLOY, FUNDRAISE

### Decision

Deterministic priority-based stub. Priority lists in GameDefines or as class-level constants. No randomness, fully reproducible.
