# Contract: OODA Consciousness Effects

**Feature**: 032-ooda-loop-system
**Date**: 2026-02-28
**Extends**: Feature 031 Consciousness Effect Contract

## Purpose

Extends the Feature 031 consciousness effect formula with action-type-specific multipliers, membership overlap credibility, AGITATE-EDUCATE coupling, and per-tick delta clamping. The base five-factor product from Feature 031 is preserved; this contract adds the action layer.

## Contract: Action-Modified Consciousness Effect

### Function Signature

```
compute_consciousness_delta(
    org: Organization,
    target_community_id: str,
    action_type: ActionType,
    graph: GraphProtocol,
    defines: OODADefines,
    org_defines: OrganizationDefines,
) -> ConsciousnessDelta
```

### Preconditions

1. `org` is a valid Organization.
2. `target_community_id` identifies a valid community node in the graph.
3. `action_type` is a consciousness-affecting action (EDUCATE, RECRUIT, ORGANIZE, etc.).
4. Feature 031 `consciousness_effect()` is available as base calculator.

### Algorithm

```
Step 1: Get action base multiplier
  action_base = defines.action_base[action_type]  # From OODADefines
  if action_base == 0.0:
    return zero_delta  # This action has no consciousness effect

Step 2: Compute membership overlap
  org_member_ids = set of node_ids via MEMBERSHIP edges from org
  community_member_ids = set of node_ids in target community
  overlap = len(org_member_ids & community_member_ids) / max(len(community_member_ids), 1)

Step 3: Scale credibility by overlap (FR-020)
  base_credibility = derive_credibility(org, org_defines)
  effective_credibility = base_credibility * max(overlap, 0.01)  # Near-zero floor

Step 4: Compute base delta using Feature 031 formula
  base_delta = tendency_modifier * org.cadre_level * org.cohesion * effective_credibility

Step 5: Apply action base multiplier
  scaled_delta = base_delta * action_base

Step 6: Apply autonomy modifier (FR-041)
  if autonomy and multiple targets this tick:
    scaled_delta = apply_autonomy_modifier(scaled_delta, org.ooda_profile.autonomy, num_targets)

Step 7: Apply contestation bonus for EDUCATE (FR-016)
  if action_type == EDUCATE:
    community_contestation = get community's ideological_contestation
    if community_contestation > defines.contestation_threshold:
      scaled_delta *= defines.agitation_educate_bonus

Step 8: Clamp to max per-tick delta (FR-019)
  scaled_delta = clamp(scaled_delta, -defines.max_ci_delta_per_tick, defines.max_ci_delta_per_tick)

Step 9: Construct result
  return ConsciousnessDelta(
    collective_identity_delta=scaled_delta,
    tendency_pressure=org.consciousness_tendency,
    tendency_magnitude=abs(scaled_delta),
    source_org_id=org.id
  )
```

### Postconditions

1. `|collective_identity_delta| <= defines.max_ci_delta_per_tick` always.
2. Zero membership overlap → near-zero effect (FR-020).
3. Same interface as Feature 031 `ConsciousnessDelta` — aggregation contract unchanged.

## Contract: Special Action Effects

### AGITATE (FR-016)

AGITATE does NOT produce a `ConsciousnessDelta` on collective_identity. Instead:

```
direct_effect = {
    "contestation_delta": defines.agitation_contestation_delta  # e.g., +0.1
}
```

Applied in Layer 3:
```
new_contestation = clamp(old_contestation + contestation_delta, 0.0, 1.0)
```

**AGITATE-EDUCATE coupling**: EDUCATE in a community with `ideological_contestation > threshold` gets a bonus multiplier (`agitation_educate_bonus`). This encodes: you must first agitate (raise contestation, make people question the status quo) before education is effective.

### REPRESS Backfire (FR-014)

State repression increases target community's collective_identity (backfire effect):

```
backfire_ci_delta = +defines.action_base_repress * credibility * repress_intensity
```

Direction is POSITIVE on target community — repression builds solidarity among the repressed. The state intends to suppress, but the side-effect is consciousness-raising.

### SURVEIL Backfire (FR-014)

Similar to REPRESS but smaller magnitude:

```
backfire_ci_delta = +defines.action_base_surveil * credibility * surveil_intensity
```

Surveillance creates paranoia which can strengthen group identity.

### ASSIMILATE (FR-017)

Directly reduces collective_identity:

```
ci_delta = -defines.action_base_assimilate * credibility
tendency_pressure = LIBERAL (assimilation pushes toward hegemonic norm)
```

### PROVIDE_SERVICE Tendency Split (FR-018)

```
if org.consciousness_tendency == REVOLUTIONARY:
    action_base = +defines.action_base_provide_service  # Positive CI effect
elif org.consciousness_tendency == LIBERAL:
    action_base = -defines.action_base_provide_service * 0.3  # Slight negative
else:
    action_base = 0.0  # No CI effect for other tendencies
```

## Contract: Layer 3 Consciousness Aggregation

Uses Feature 031's `aggregate_consciousness_effects()` unchanged:

```
all_deltas = collect all ConsciousnessDeltas targeting each community
for each community:
    aggregated = aggregate_consciousness_effects(community_deltas, current_ci)
    graph.update_node(community_id, consciousness={
        "collective_identity": aggregated.new_ci,
        "dominant_tendency": aggregated.dominant_tendency.value,
        "ideological_contestation": new_contestation,
    })
```

### Invariants

1. Feature 031 aggregation contract is NOT modified.
2. New `ConsciousnessDelta` instances are compatible with existing aggregation.
3. Per-tick max delta is enforced per-action (Step 8), not per-community aggregate. Multiple actions can exceed the per-action limit in aggregate.

## Worked Examples

### Revolutionary EDUCATE in Agitated Community

```
Org: REVOLUTIONARY, cadre=0.7, cohesion=0.6, credibility=0.5
Community: CI=0.3, contestation=0.6, overlap=0.8

effective_credibility = 0.5 * 0.8 = 0.4
base_delta = 0.15 * 0.7 * 0.6 * 0.4 = 0.0252
action_base = 1.2
scaled = 0.0252 * 1.2 = 0.03024
contestation bonus (0.6 > threshold): * 1.5 = 0.04536
clamped to 0.05: 0.04536 (within limit)

Result: CI increases by 0.045, tendency = REVOLUTIONARY
```

### Liberal EDUCATE in Same Community

```
Org: LIBERAL, cadre=0.3, cohesion=0.8, credibility=0.7
Community: same as above, overlap=0.2

effective_credibility = 0.7 * 0.2 = 0.14
base_delta = -0.05 * 0.3 * 0.8 * 0.14 = -0.00168
action_base = 1.2
scaled = -0.00168 * 1.2 = -0.002016
contestation bonus: * 1.5 = -0.003024

Result: CI decreases by 0.003, tendency = LIBERAL
```

### EDUCATE with Zero Overlap

```
Org: REVOLUTIONARY, cadre=0.7, cohesion=0.6, credibility=0.5
Community: overlap=0.0

effective_credibility = 0.5 * max(0.0, 0.01) = 0.005
base_delta = 0.15 * 0.7 * 0.6 * 0.005 = 0.000315
action_base = 1.2
scaled = 0.000315 * 1.2 = 0.000378

Result: CI increases by 0.0004 — near-zero effect. You can't raise consciousness from outside.
```

### REPRESS Backfire

```
State: StateApparatus, credibility=0.8
Community: CI=0.3, target of REPRESS

backfire_ci_delta = +0.8 * 0.8 * 1.0 = +0.64
clamped to max_ci_delta_per_tick (0.05): +0.05

Result: Community CI jumps to 0.35. Repression backfires.
```

### 52-Tick Compounding (1 Simulated Year)

```
Revolutionary EDUCATE each tick, effect ~0.03 per tick:
  0.03 * 52 = 1.56 total CI delta
  Community CI moves from 0.3 → 1.0 (clamped) over one simulated year

Liberal EDUCATE each tick, effect ~-0.003 per tick:
  -0.003 * 52 = -0.156 total CI delta
  Community CI moves from 0.3 → 0.144 over one simulated year
```

This demonstrates SC-010: small per-tick changes compound to meaningful shifts over simulated time.
