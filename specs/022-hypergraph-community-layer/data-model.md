# Data Model: Hypergraph Community Layer

**Phase 1 Output** | **Date**: 2026-02-25

## Enums

### CommunityType

```
Values: NEW_AFRIKAN, FIRST_NATIONS, CHICANO, QUEER, TRANS, DISABLED, UNDOCUMENTED, WOMEN
```

Extensible enum. Each value represents a structural community category derived from theoretical analysis. Added to `src/babylon/models/enums.py`.

### LegalStatus

```
Values: LEGAL, SURVEILLED, DESIGNATED_EXTREMIST, DESIGNATED_TERRORIST, CRIMINALIZED
Threat multipliers: 0.1, 0.5, 1.0, 2.0, 3.0
```

Escalation is strictly one-way for state action. De-escalation requires political struggle (player action). Added to `src/babylon/models/enums.py`.

### MembershipRole

```
Values: CORE_ORGANIZER, ACTIVE, PARTICIPANT, PERIPHERAL, SYMPATHIZER
Strength weights: 1.0, 0.7, 0.4, 0.2, 0.1
```

Determines agent's integration level within a community. Added to `src/babylon/models/enums.py`.

## Entity Models

### CommunityState

**Location**: `src/babylon/models/entities/community.py`
**Config**: `frozen=True`

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| community_type | CommunityType | required | enum | Community identity |
| heat | Probability | 0.0 | [0.0, 1.0] | State attention/surveillance intensity |
| legal_status | LegalStatus | LEGAL | enum | Current legal designation |
| cohesion | Probability | 0.5 | [0.0, 1.0] | Internal trust and mutual aid effectiveness |
| infrastructure | Probability | 0.3 | [0.0, 1.0] | Meeting spaces, comms, mutual aid networks |
| visibility | Probability | 0.5 | [0.0, 1.0] | Legibility to state surveillance |
| reproduction_cost_modifier | float | 1.0 | ge=0.0 | Multiplier on V_reproduction for members |
| rent_access_modifier | Coefficient | 1.0 | [0.0, 1.0] | Multiplier on Φ received by members |

### CommunityMembership

**Location**: `src/babylon/models/entities/community.py`
**Config**: `frozen=True`

| Field | Type | Default | Constraint | Description |
|-------|------|---------|------------|-------------|
| agent_id | str | required | | Agent identifier |
| community_type | CommunityType | required | enum | Which community |
| role | MembershipRole | PARTICIPANT | enum | Integration level |
| strength | Coefficient | 0.4 | [0.0, 1.0] | Membership weight (derived from role default) |
| visibility | Probability | 0.5 | [0.0, 1.0] | Base legibility to state |
| overt | bool | False | | Publicly identified — overrides visibility to 1.0 |

**Computed property**: `effective_visibility` → `1.0 if self.overt else self.visibility`

### SocialClass Extension

**Location**: `src/babylon/models/entities/social_class.py`

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| community_memberships | list[CommunityMembership] | [] | Communities this agent belongs to |
| community_cost_modifier | float | 1.0 | Compound reproduction cost modifier from communities |

`community_cost_modifier` is computed as `Π(cs.reproduction_cost_modifier for cs in communities)` and multiplied with the existing `subsistence_multiplier` when computing effective reproduction cost. Updated on membership change events (between ticks).

## Relationships

```
Agent (SocialClass) ──membership──► Community (CommunityState)
  via CommunityMembership (role, strength, visibility, overt)

Community ──hyperedge──► {Agent, Agent, Agent, ...}
  via XGI Hypergraph (n-ary membership structure)

Agent ──solidarity_potential──► Agent
  via overlap matrix (number of shared communities)
  realized as solidarity_strength amplification on existing SOLIDARITY edges
```

## State Transitions

### Legal Status (one-way escalation)

```
LEGAL → SURVEILLED → DESIGNATED_EXTREMIST → DESIGNATED_TERRORIST → CRIMINALIZED
```

Triggered by state Repress:Designate action. Each step increases threat multiplier. No state-initiated de-escalation — only political struggle reverses.

### Community State Drift (alpha-smoothing per tick)

```
heat:           decays toward 0.0 (state attention fades without provocation)
cohesion:       decays toward 0.0 (requires organizing work to maintain)
infrastructure: decays toward 0.0 (requires CORE_ORGANIZER + player Aid to sustain)
```

Decay rate: `new_value = old_value × (1 - alpha)` where alpha is a per-attribute smoothing constant from `CommunityDefines`.

### Membership Change (between ticks)

```
Agent gains membership  → recompute community_cost_modifier, rebuild hypergraph
Agent loses membership  → recompute community_cost_modifier, rebuild hypergraph
Agent role changes      → update membership strength, no hypergraph rebuild needed
```

## Formulas

### Solidarity Potential

```
solidarity_potential(A, B) = base_class_solidarity
                           + community_overlap_bonus × |communities(A) ∩ communities(B)|
                           - rent_differential_penalty × |Φ_A - Φ_B|
```

Where `community_overlap_bonus` and `rent_differential_penalty` are `CommunityDefines` coefficients.

### Solidarity Transmission Amplification

```
amplified_strength = base_solidarity_strength × (
    1 + Σ(c.infrastructure × c.cohesion × strength_A × strength_B
        for c in shared_communities(A, B))
)
```

Applied to `solidarity_strength` on SOLIDARITY edges before `SolidaritySystem` reads them.

### Threat Score

```
threat_score(agent) = Σ(
    c.heat × m.effective_visibility × role_weight[m.role] × legal_status_multiplier[c.legal_status]
    for m in agent.community_memberships
    for c = community_state[m.community_type]
)
```

### Infrastructure Decay

```
new_infrastructure = old_infrastructure × (1 - decay_alpha)
                   + core_organizer_maintenance × decay_alpha
```

Where `core_organizer_maintenance` is proportional to the number of CORE_ORGANIZER members remaining in the community.
