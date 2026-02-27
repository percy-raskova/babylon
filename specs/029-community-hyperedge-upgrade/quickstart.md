# Quickstart: Community Hyperedge Layer Upgrade

**Feature**: 029-community-hyperedge-upgrade
**Date**: 2026-02-27

## Integration Scenario 1: Taxonomy Query

```python
from babylon.models.enums import CommunityType, HyperedgeCategory
from babylon.models.entities.community import (
    COMMUNITY_CATEGORY_MAP,
    is_hegemonic,
    is_marginalized,
    get_contradiction_axis,
    get_opposing_communities,
)

# Every community type maps to exactly one category
assert COMMUNITY_CATEGORY_MAP[CommunityType.SETTLER] == HyperedgeCategory.CONTRADICTION_PAIR
assert COMMUNITY_CATEGORY_MAP[CommunityType.DISABLED] == HyperedgeCategory.INSTITUTIONAL_EXCLUSION
assert COMMUNITY_CATEGORY_MAP[CommunityType.YOUTH] == HyperedgeCategory.LIFECYCLE_PHASE

# Hegemonic/marginalized predicates
assert is_hegemonic(CommunityType.SETTLER)
assert not is_hegemonic(CommunityType.NEW_AFRIKAN)
assert is_marginalized(CommunityType.DISABLED)  # exclusion counts as marginalized
assert not is_marginalized(CommunityType.YOUTH)  # lifecycle, not marginalized

# Axis queries
axis = get_contradiction_axis(CommunityType.SETTLER)
assert axis is not None
assert axis.name == "Colonial"
assert get_opposing_communities(CommunityType.SETTLER) == [
    CommunityType.NEW_AFRIKAN, CommunityType.FIRST_NATIONS, CommunityType.CHICANO
]
assert get_contradiction_axis(CommunityType.DISABLED) is None  # no axis
```

## Integration Scenario 2: Consciousness Model

```python
from babylon.models.entities.community import (
    CommunityConsciousness,
    CommunityState,
    CONSCIOUSNESS_DEFAULTS,
)
from babylon.models.enums import CommunityType, ConsciousnessTendency

# Load default consciousness for a community
defaults = CONSCIOUSNESS_DEFAULTS[CommunityType.INCARCERATED]
assert defaults.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
assert defaults.collective_identity == 0.6

# Create community state — category auto-assigned, consciousness defaulted
state = CommunityState(community_type=CommunityType.NEW_AFRIKAN)
assert state.category == HyperedgeCategory.CONTRADICTION_PAIR
assert state.consciousness.collective_identity == 0.3  # CommunityConsciousness default

# Create with explicit consciousness
state = CommunityState(
    community_type=CommunityType.NEW_AFRIKAN,
    consciousness=CONSCIOUSNESS_DEFAULTS[CommunityType.NEW_AFRIKAN],
)
assert state.consciousness.collective_identity == 0.5

# Serialization roundtrip
data = state.model_dump(mode="json")
restored = CommunityState.model_validate(data)
assert restored.consciousness == state.consciousness
```

## Integration Scenario 3: Infiltration Resistance

```python
from babylon.models.entities.community import CommunityState, effective_infiltration_ceiling
from babylon.models.enums import CommunityType

# High consciousness + high cohesion = high resistance
state = CommunityState(
    community_type=CommunityType.NEW_AFRIKAN,
    cohesion=0.8,
    consciousness=CommunityConsciousness(collective_identity=0.9),
)
assert state.infiltration_resistance > 0.85

# Low consciousness + low cohesion = low resistance
weak = CommunityState(
    community_type=CommunityType.SETTLER,
    cohesion=0.2,
    consciousness=CommunityConsciousness(collective_identity=0.1),
)
assert weak.infiltration_resistance < 0.15

# Effective ceiling reduction
base_ceiling = 0.8
reduced = effective_infiltration_ceiling(base_ceiling, [state])
assert reduced < base_ceiling * 0.6  # Significant reduction

# No communities = no reduction
assert effective_infiltration_ceiling(base_ceiling, []) == base_ceiling
```

## Integration Scenario 4: Cross-Class Bridge Detection

```python
from babylon.models.entities.community import (
    CommunityMembership,
    CommunityState,
    COLONIAL_AXIS,
)
from babylon.engine.systems.community import (
    build_community_hypergraph,
    communities_spanning_axis,
)
from babylon.models.enums import CommunityType

# Agent A is SETTLER + DISABLED, Agent B is NEW_AFRIKAN + DISABLED
memberships = [
    CommunityMembership(agent_id="a", community_type=CommunityType.SETTLER),
    CommunityMembership(agent_id="a", community_type=CommunityType.DISABLED),
    CommunityMembership(agent_id="b", community_type=CommunityType.NEW_AFRIKAN),
    CommunityMembership(agent_id="b", community_type=CommunityType.DISABLED),
]
states = {ct: CommunityState(community_type=ct) for ct in CommunityType}
H = build_community_hypergraph(memberships, states)

bridges = communities_spanning_axis(H, COLONIAL_AXIS)
assert CommunityType.DISABLED in bridges  # Spans colonial axis
```

## Integration Scenario 5: Backward Compatibility

```python
# Existing code continues to work without changes
state = CommunityState(community_type=CommunityType.QUEER)
# All existing fields preserved with same defaults
assert float(state.heat) == 0.0
assert float(state.cohesion) == 0.5
assert float(state.infrastructure) == 0.3
assert float(state.visibility) == 0.5
assert state.reproduction_cost_modifier == 1.0
assert float(state.rent_access_modifier) == 1.0

# New fields are auto-populated
assert state.category == HyperedgeCategory.INSTITUTIONAL_EXCLUSION
assert state.consciousness is not None
assert state.is_cross_class_bridge is True  # institutional exclusion
```
