# Contract: Consciousness & Infiltration API

**Feature**: 029-community-hyperedge-upgrade
**Covers**: FR-003, FR-004, FR-005, FR-006, FR-009

## Models

### CommunityConsciousness

**Invariants**:
- `collective_identity` in [0.0, 1.0] (Probability type)
- `ideological_contestation` in [0.0, 1.0] (Probability type)
- `dominant_tendency` is a valid ConsciousnessTendency member
- Frozen (immutable after creation)

**Serialization Contract**:
```python
# Must survive roundtrip
original = CommunityConsciousness(collective_identity=0.5, ...)
data = original.model_dump(mode="json")
restored = CommunityConsciousness.model_validate(data)
assert restored == original
```

## Functions

### infiltration_resistance (computed field on CommunityState)

```python
@computed_field
def infiltration_resistance(self) -> float:
    ci = self.consciousness.collective_identity
    coh = self.cohesion
    return float(ci) * 0.6 + float(coh) * 0.3 + float(ci) * float(coh) * 0.1
```

**Properties**:
- Range: [0.0, 1.0]
- Monotonically increasing with both CI and cohesion
- Maximum (1.0) at CI=1.0, cohesion=1.0
- Minimum (0.0) at CI=0.0, cohesion=0.0

**Test Cases**:
| CI | Cohesion | Expected |
|----|----------|----------|
| 0.9 | 0.8 | 0.852 |
| 0.1 | 0.2 | 0.122 |
| 0.9 | 0.1 | 0.579 |
| 0.1 | 0.9 | 0.339 |
| 0.0 | 0.0 | 0.0 |
| 1.0 | 1.0 | 1.0 |

### effective_infiltration_ceiling

```python
def effective_infiltration_ceiling(
    base_ceiling: float,
    target_community_states: list[CommunityState],
) -> float:
```

**Formula**: `base_ceiling * (1.0 - max_resistance * 0.7)`

**Preconditions**: `base_ceiling` in [0, 1]
**Postconditions**:
- Returns `base_ceiling` unchanged if `target_community_states` is empty
- Returns reduced ceiling proportional to max infiltration_resistance
- At max resistance (~1.0), ceiling drops to ~30% of base

**Test Cases**:
| Base Ceiling | Max Resistance | Expected |
|--------------|---------------|----------|
| 0.8 | 0.0 | 0.8 |
| 0.8 | 0.85 | 0.324 |
| 0.8 | 1.0 | 0.24 |
| 0.8 | (empty list) | 0.8 |

## CONSCIOUSNESS_DEFAULTS Contract

All 14 CommunityType members MUST have an entry. Values are SYNTHETIC (flagged in code comments).

**Notable entries**:
| Type | CI | Tendency | Contestation |
|------|----|----------|-------------|
| INCARCERATED | 0.6 | REVOLUTIONARY | 0.3 |
| FIRST_NATIONS | 0.6 | REVOLUTIONARY | 0.3 |
| SETTLER | 0.4 | ASSIMILATIONIST_LIBERAL | 0.3 |
| YOUTH | 0.2 | ASSIMILATIONIST_LIBERAL | 0.5 |
| ADULT | 0.1 | ASSIMILATIONIST_LIBERAL | 0.1 |
