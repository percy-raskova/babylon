# Contract: Consciousness Effect Calculator

**Feature**: 031-organization-base-model
**Date**: 2026-02-27

## Purpose

Defines how an Organization's ideological action affects a target community's consciousness state. This is the five-factor product formula contract — all consciousness effect calculations must follow this specification.

## Contract: Single Organization Effect

### Function Signature

```
consciousness_effect(org, target_community, defines) -> ConsciousnessDelta
```

### Preconditions

1. `org` is a valid Organization instance (any subtype).
2. `target_community` identifies a community (territory or hyperedge) where the org has PRESENCE.
3. `defines` provides `OrganizationDefines` with tunable parameters.
4. `org.cohesion > 0` (zero cohesion → zero effect, short-circuit).
5. `org.cadre_level >= 0` (zero cadre_level → zero effect, short-circuit).

### Algorithm (Phase 1)

```
Step 1: Resolve tendency_modifier
  tendency_modifier = defines.tendency_modifier[org.consciousness_tendency]

  Values (from OrganizationDefines):
    REVOLUTIONARY → +0.15  (raises collective_identity)
    LIBERAL       → -0.05  (slightly erodes oppositional consciousness)
    FASCIST       → +0.10  (applied to tendency_pressure, not CI directly)

Step 2: Resolve credibility
  credibility = derive_credibility(org)

  Derivation by subtype:
    CivilSocietyOrg → org.legitimacy
    PoliticalFaction → defines.credibility_default_faction  (0.5)
    StateApparatus  → defines.credibility_by_standing[org.legal_standing]
                      SOVEREIGN=0.8, CHARTERED=0.6, else=0.5
    Business        → employment_share (proportion of local workforce)
                      Requires target_community context for calculation.

Step 3: Compute collective_identity_delta
  For REVOLUTIONARY and LIBERAL tendencies:
    ci_delta = tendency_modifier × org.cadre_level × org.cohesion × credibility

  For FASCIST tendency:
    ci_delta = 0.0  (FASCIST does not directly change collective_identity)

Step 4: Compute tendency_pressure
  For FASCIST tendency:
    tendency_pressure = FASCIST
    tendency_magnitude = tendency_modifier × org.cadre_level × org.cohesion × credibility

  For REVOLUTIONARY and LIBERAL:
    tendency_pressure = org.consciousness_tendency
    tendency_magnitude = abs(ci_delta)

Step 5: Construct result
  return ConsciousnessDelta(
    collective_identity_delta=ci_delta,
    tendency_pressure=tendency_pressure,
    tendency_magnitude=tendency_magnitude,
    source_org_id=org.id
  )
```

### Postconditions

1. `ConsciousnessDelta` is a frozen dataclass/model.
2. `collective_identity_delta` is a finite float (may be positive, negative, or zero).
3. `tendency_pressure` is a valid `ConsciousnessTendency` enum value.
4. `tendency_magnitude` is a non-negative float.
5. `source_org_id` matches `org.id`.

### Short-Circuit Cases

| Condition | Result |
|-----------|--------|
| `org.cohesion == 0` | Zero-delta: `ci_delta=0, magnitude=0` |
| `org.cadre_level == 0` | Zero-delta: `ci_delta=0, magnitude=0` |
| `credibility == 0` | Zero-delta: `ci_delta=0, magnitude=0` |

## Contract: Concurrent Effects (Multiple Organizations)

### Function Signature

```
aggregate_consciousness_effects(deltas: list[ConsciousnessDelta]) -> AggregatedEffect
```

### Preconditions

1. All deltas are valid `ConsciousnessDelta` instances.
2. List may be empty (no orgs acting on this community this tick).

### Algorithm

```
Step 1: Sum collective_identity deltas
  total_ci_delta = sum(d.collective_identity_delta for d in deltas)

Step 2: Determine dominant tendency
  weight_by_tendency = group deltas by tendency_pressure
  for each tendency:
    total_weight = sum(d.tendency_magnitude for d in group)
  dominant_tendency = tendency with highest total_weight

  Tie-breaking: If weights are equal, maintain current community tendency (no change).

Step 3: Apply bounds
  new_ci = clamp(current_ci + total_ci_delta, 0.0, 1.0)
```

### Postconditions

1. `new_ci` is in `[0, 1]` (clamped).
2. `dominant_tendency` is the tendency with the strongest weighted presence.
3. If no deltas provided, no change to community state.

### Invariants

- CI deltas are SUMMED (additive combination).
- Tendency pressures are NOT summed — they compete. The strongest weighted tendency wins.
- A single strong REVOLUTIONARY org can outweigh multiple weak LIBERAL orgs (and vice versa).

## Contract: Credibility Derivation

### Per-Subtype Rules

**CivilSocietyOrg**:
```
credibility = org.legitimacy  # Direct field, [0, 1]
```

**PoliticalFaction**:
```
credibility = defines.credibility_default_faction  # 0.5 default
# PoliticalFactions must earn credibility through action (Phase 2)
```

**StateApparatus**:
```
credibility = defines.credibility_by_legal_standing[org.legal_standing]
# SOVEREIGN → 0.8 (state authority)
# CHARTERED → 0.6 (delegated authority)
# Others → 0.5 (default)
```

**Business**:
```
credibility = employment_share(org, target_community)
# Proportion of target community's workforce employed by this business
# Requires: org.employment_count, community total workforce
# If community workforce data unavailable, default to 0.0
```

### Credibility Bounds

- All credibility values are in `[0, 1]`.
- Zero credibility → zero consciousness effect (short-circuit).

## Worked Example: Detroit Scenario

### Setup

Three organizations act on the same community this tick:

1. **Revolutionary Workers Party** (PoliticalFaction)
   - `consciousness_tendency = REVOLUTIONARY`
   - `cadre_level = 0.7`, `cohesion = 0.6`
   - `credibility = 0.5` (default faction)

2. **First Baptist Church** (CivilSocietyOrg)
   - `consciousness_tendency = LIBERAL`
   - `cadre_level = 0.3`, `cohesion = 0.8`
   - `legitimacy = 0.7` (credibility = 0.7)

3. **Ford Motor Company** (Business)
   - `consciousness_tendency = LIBERAL`
   - `cadre_level = 0.1`, `cohesion = 0.9`
   - `employment_share = 0.15` (credibility = 0.15)

### Step-by-Step

**Org 1: Revolutionary Workers Party**
```
ci_delta = 0.15 × 0.7 × 0.6 × 0.5 = 0.0315
tendency_pressure = REVOLUTIONARY, magnitude = 0.0315
```

**Org 2: First Baptist Church**
```
ci_delta = -0.05 × 0.3 × 0.8 × 0.7 = -0.0084
tendency_pressure = LIBERAL, magnitude = 0.0084
```

**Org 3: Ford Motor Company**
```
ci_delta = -0.05 × 0.1 × 0.9 × 0.15 = -0.000675
tendency_pressure = LIBERAL, magnitude = 0.000675
```

**Aggregation**
```
total_ci_delta = 0.0315 + (-0.0084) + (-0.000675) = +0.022225
  → CI increases slightly (revolutionary org outweighs liberal orgs)

Tendency weights:
  REVOLUTIONARY = 0.0315
  LIBERAL = 0.0084 + 0.000675 = 0.009075

dominant_tendency = REVOLUTIONARY (0.0315 > 0.009075)
```

**Result**: Community CI rises by ~0.022, dominant tendency shifts toward REVOLUTIONARY. The revolutionary faction's concentrated cadre outweighs the church and Ford's diffuse liberal influence.

## Phase 2 Extension Points

The contract is designed to support these future extensions without breaking the interface:

1. **action_base coefficient**: Phase 1 defaults to 1.0. Phase 2 OODA system will provide per-action-type multipliers (EDUCATE=1.2, PROVIDE_SERVICE=0.8, etc.).
2. **Tendency durability**: `tendency_modifier` will eventually encode both magnitude AND durability (how resistant the effect is to counter-influence).
3. **Per-action-type elder capacity matrix**: Phase 1 uses single scalar; Phase 2 differentiates by action type.
4. **Credibility evolution**: PoliticalFaction credibility will be dynamic based on track record of successful actions.
