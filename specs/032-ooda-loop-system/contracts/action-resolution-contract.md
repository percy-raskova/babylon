# Contract: Action Resolution

**Feature**: 032-ooda-loop-system
**Date**: 2026-02-28

## Purpose

Defines the complete action resolution pipeline: eligibility checking, cost computation, action execution, and result production. This is the core loop of the Action Phase.

## Contract: Action Eligibility

### Function Signature

```
check_eligibility(org_type: OrgType, action_type: ActionType, org_attrs: dict) -> bool
```

### Eligibility Matrix

| Action Type | StateApparatus | PoliticalFaction | CivilSocietyOrg | Business |
|------------|---------------|-----------------|-----------------|----------|
| RECRUIT | yes | yes | yes | no |
| ORGANIZE | yes | yes | yes | no |
| EDUCATE | yes | yes | yes | no |
| AGITATE | no | yes | yes | no |
| PROPAGANDIZE | yes | yes | yes | yes |
| FUNDRAISE | no | yes | yes | yes |
| PROVIDE_SERVICE | yes | yes | yes | no |
| EMPLOY | no | no | no | yes |
| REPRESS | yes* | no | no | no |
| PROTEST | no | yes | yes | no |
| STRIKE | no | yes | no | no |
| EXPROPRIATE | no | yes | no | no |
| SURVEIL | yes* | no | no | no |
| INFILTRATE | yes | no | no | no |
| COUNTER_INTEL | no | yes | yes | no |
| MAP_NETWORK | no | yes | yes | no |
| PROPOSE_ALLIANCE | yes | yes | yes | no |
| DENOUNCE | yes | yes | yes | no |
| BUILD_INFRASTRUCTURE | yes | yes | yes | yes |
| ATTACK_INFRASTRUCTURE | yes | yes | no | no |
| ASSIMILATE | yes | yes** | yes** | no |

`*` Also available to non-state orgs with `violence_capacity > 0` (REPRESS) or `surveillance_capacity > 0` (SURVEIL).

`**` Only if `consciousness_tendency == LIBERAL` and `is_institution == True`.

### Postconditions

1. Returns `True` if the action is permitted for this org type and attributes.
2. Returns `False` with no side effects if ineligible.
3. Ineligible actions do NOT consume action points (FR edge case).

## Contract: Action Cost Computation

### Function Signature

```
compute_action_cost(
    action_type: ActionType,
    org_id: str,
    target_id: str,
    graph: GraphProtocol,
    defines: OODADefines,
) -> ActionCostModifier
```

### Algorithm

```
Step 1: Get base cost
  base_cost = defines.base_cost[action_type]

Step 2: Compute membership overlap with target community
  org_members = set of node_ids connected via MEMBERSHIP edges from org
  community_members = set of node_ids in target community hyperedge
  overlap = len(org_members & community_members) / max(len(community_members), 1)

Step 3: Check contradiction axis
  org_communities = community types of org members
  target_community_type = community type of target
  is_contradiction = any contradiction axis where org is hegemonic and target is marginalized (or vice versa)

Step 4: Compute modifier
  if overlap > 0:
    modifier = max(defines.min_cost_modifier, 1.0 - overlap * defines.embeddedness_discount)
    reason = f"Embedded (overlap={overlap:.2f})"
  elif is_contradiction:
    modifier = defines.contradiction_cost_multiplier
    reason = "Across contradiction axis"
  else:
    modifier = defines.outsider_cost_multiplier
    reason = "No membership in target community"

Step 5: Compute effective cost
  effective_cost = max(1, ceil(base_cost * modifier))
```

### Postconditions

1. `effective_cost >= 1` always (minimum 1 AP per action).
2. `modifier < 1.0` for embedded orgs (discount).
3. `modifier > 1.0` for outsider and contradiction orgs (surcharge).
4. `reason` is human-readable for debugging.

## Contract: Action Execution

### Function Signature

```
resolve_action(
    action: Action,
    org_attrs: dict,
    target_attrs: dict,
    graph: GraphProtocol,
    defines: OODADefines,
) -> ActionResult
```

### Preconditions

1. Action has passed eligibility check.
2. Action cost has been paid (action_points decremented).
3. `org_attrs` and `target_attrs` are fresh from graph.

### Resolution by Action Type

**EDUCATE**:
```
consciousness_delta = compute_consciousness_delta(org, target, ActionType.EDUCATE, defines)
contestation_bonus = defines.agitation_educate_bonus if target.ideological_contestation > 0.3 else 1.0
consciousness_delta = scale_delta(consciousness_delta, contestation_bonus)
direct_effects = {}
```

**AGITATE**:
```
consciousness_delta = None  # AGITATE does not produce CI change
direct_effects = {"contestation_delta": defines.agitation_contestation_delta}
```

**RECRUIT**:
```
consciousness_delta = compute_consciousness_delta(org, target, ActionType.RECRUIT, defines)
direct_effects = {"membership_growth": recruitment_amount}
```

**ORGANIZE**:
```
consciousness_delta = compute_consciousness_delta(org, target, ActionType.ORGANIZE, defines)
direct_effects = {"edge_transition_candidates": affected_edge_ids}
```

**REPRESS**:
```
consciousness_delta = compute_repress_backfire(org, target, defines)
direct_effects = {"heat_delta": heat_increment, "target_suppression": suppression_amount}
events = [EventType.STATE_REPRESSION]
```

**SURVEIL**:
```
consciousness_delta = compute_surveil_backfire(org, target, defines)
direct_effects = {"visibility_increase": vis_amount, "heat_delta": heat_increment}
events = [EventType.STATE_SURVEILLANCE]
```

**ASSIMILATE**:
```
consciousness_delta = ConsciousnessDelta(
    collective_identity_delta = -defines.action_base_assimilate * credibility,
    tendency_pressure = ConsciousnessTendency.LIBERAL,
    tendency_magnitude = defines.action_base_assimilate * credibility,
    source_org_id = org_id
)
direct_effects = {}
```

**PROVIDE_SERVICE**:
```
consciousness_delta = compute_consciousness_delta(org, target, ActionType.PROVIDE_SERVICE, defines)
direct_effects = {"service_benefit": benefit_amount}
```

**BUILD_INFRASTRUCTURE**:
```
consciousness_delta = None
direct_effects = {"infrastructure_delta": build_increment}
events = [EventType.INFRASTRUCTURE_CHANGE]
```

**ATTACK_INFRASTRUCTURE**:
```
consciousness_delta = None
direct_effects = {"infrastructure_delta": -attack_decrement, "reproduction_cost_delta": cost_increase}
events = [EventType.INFRASTRUCTURE_CHANGE]
```

**EMPLOY**:
```
consciousness_delta = compute_consciousness_delta(org, target, ActionType.EMPLOY, defines)
direct_effects = {"employment_change": employment_delta}
```

**PROTEST, STRIKE, EXPROPRIATE**: Primarily direct effects with minor consciousness side-effects.

**INFILTRATE, COUNTER_INTEL, MAP_NETWORK**: Intelligence actions with no direct consciousness effect.

**PROPOSE_ALLIANCE, DENOUNCE**: Relationship changes with no consciousness effect.

**FUNDRAISE**: Resource generation with no consciousness effect.
```
direct_effects = {"budget_delta": fundraise_amount}
```

### Postconditions

1. `ActionResult` is frozen.
2. `success` is True unless the action was blocked (target doesn't exist, etc.).
3. `consciousness_delta` is None for actions with no consciousness effect.
4. `events_generated` lists all EventType strings to emit.
5. `failure_reason` is None on success, descriptive string on failure.

## Contract: Action Points Enforcement

### Function Signature

```
enforce_action_points(
    actions: list[Action],
    available_points: int,
) -> tuple[list[Action], list[Action]]
```

### Algorithm

```
accepted = []
rejected = []
remaining_points = available_points

for action in actions:  # in submission order
    if action.action_point_cost <= remaining_points:
        accepted.append(action)
        remaining_points -= action.action_point_cost
    else:
        rejected.append(action)
        # rejected actions are NOT charged

return accepted, rejected
```

### Postconditions

1. `sum(a.action_point_cost for a in accepted) <= available_points`.
2. All rejected actions have `action_point_cost > remaining_points` at time of evaluation.
3. Order of accepted actions preserves submission order.

## Contract: Coordination Range Enforcement

### Function Signature

```
enforce_coordination_range(
    actions: list[Action],
    org_territory_ids: list[str],
    headquarters_id: str | None,
    coordination_range: int,
    graph: GraphProtocol,
) -> tuple[list[Action], list[Action]]
```

### Algorithm

```
reachable = compute_reachable_territories(headquarters_id, org_territory_ids, coordination_range, graph)
distinct_targets = set()
accepted = []
rejected = []

for action in actions:
    territory = get_territory_of_target(action.target_id, graph)
    if territory not in reachable:
        rejected.append(action)  # Out of range
        continue
    distinct_targets.add(territory)
    if len(distinct_targets) > coordination_range:
        rejected.append(action)  # Exceeds territory limit
        continue
    accepted.append(action)

return accepted, rejected
```

### Postconditions

1. All accepted action targets are within reachable territories.
2. Number of distinct target territories <= coordination_range.
3. Rejected actions not charged.

## Contract: Autonomy Effectiveness Tradeoff

### Function Signature

```
apply_autonomy_modifier(
    base_effect: float,
    autonomy: float,
    num_targets: int,
    defines: OODADefines,
) -> float
```

### Algorithm

```
# High autonomy: spread thin, reduced per-target effect
# Low autonomy: concentrated, amplified per-target effect
concentration = 1.0 - autonomy  # 0 = fully dispersed, 1 = fully concentrated

if num_targets <= 1:
    effectiveness = 1.0 + concentration * defines.autonomy_effectiveness_scale
else:
    effectiveness = 1.0 - autonomy * defines.autonomy_effectiveness_scale * (num_targets - 1) / num_targets
    effectiveness = max(effectiveness, 0.1)  # Floor: never zero

return base_effect * effectiveness
```

### Properties

1. Low autonomy (0.0) on single target: maximum effectiveness (1.5x with default scale).
2. High autonomy (1.0) spread across many targets: reduced per-target effectiveness.
3. Effectiveness never drops below 0.1x.

## Worked Example: EDUCATE Action

**Setup**: Revolutionary PoliticalFaction educates in NEW_AFRIKAN community.

```
Org: consciousness_tendency=REVOLUTIONARY, cadre_level=0.7, cohesion=0.6
Community: collective_identity=0.3, ideological_contestation=0.5
Membership overlap: 0.6 (60% of community are org members)

Step 1: Eligibility
  PoliticalFaction can EDUCATE → eligible

Step 2: Cost
  base_cost = 1 (EDUCATE)
  overlap = 0.6 → modifier = max(0.5, 1.0 - 0.6 * 0.5) = max(0.5, 0.7) = 0.7
  effective_cost = max(1, ceil(1 * 0.7)) = 1 AP

Step 3: Consciousness delta
  action_base = 1.2 (EDUCATE)
  tendency_modifier = 0.15 (REVOLUTIONARY)
  credibility = 0.5 (default faction) * overlap_factor = 0.5 * 0.6 = 0.3
  ci_delta = action_base * tendency_modifier * cadre * cohesion * credibility
           = 1.2 * 0.15 * 0.7 * 0.6 * 0.3 = 0.02268

  Contestation bonus (contestation > 0.3): *= 1.5
  ci_delta = 0.02268 * 1.5 = 0.03402

  Clamped to max_ci_delta_per_tick (0.05): 0.03402 (within limit)

Step 4: Result
  ActionResult(
    action=Action(org_id="faction_1", action_type=EDUCATE, target_id="community_new_afrikan"),
    success=True,
    consciousness_delta=ConsciousnessDelta(
      collective_identity_delta=0.03402,
      tendency_pressure=REVOLUTIONARY,
      tendency_magnitude=0.03402,
      source_org_id="faction_1"
    ),
    direct_effects={},
    events_generated=[],
    failure_reason=None
  )
```
