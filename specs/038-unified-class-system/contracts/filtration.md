# Contract: Filtration Predicates

**Spec**: FR-003, FR-004
**Module**: `src/babylon/economics/melt/filtration.py`

---

## Function Signatures

```python
from __future__ import annotations

from typing import Sequence

from babylon.config.defines import ClassSystemDefines
from babylon.economics.melt.types import PrecarityStatus
from babylon.models.enums import CommunityType
from babylon.models.entities.community import CommunityMembership, CommunityState


def apply_filtration(
    wealth_percentile: float,
    precarity: PrecarityStatus,
    memberships: Sequence[CommunityMembership],
    community_states: dict[CommunityType, CommunityState],
    defines: ClassSystemDefines,
) -> FiltrationResult:
    """Apply all applicable community filtration predicates.

    Each community membership is checked against its filtration predicate.
    Multiple predicates compose via most-restrictive-wins (FR-004).

    Args:
        wealth_percentile: Raw wealth percentile [0, 100].
        precarity: Raw precarity status.
        memberships: Agent's community memberships.
        community_states: Current community states (for reproduction_cost_modifier).
        defines: ClassSystemDefines for filtration parameters.

    Returns:
        FiltrationResult with effective values after all predicates applied.
    """
    ...
```

---

## Predicate Specifications

### FIRST_NATIONS Trust Land Discount
**Trigger**: Agent has membership with `community_type == CommunityType.FIRST_NATIONS`
**Effect**: `effective_wealth *= defines.trust_land_discount`
**Rationale**: Reservation property operates under qualitatively different property regime. No appreciation trajectory, no equity extraction, trust land tenure.

### INCARCERATED Precarity Override
**Trigger**: Agent has membership with `community_type == CommunityType.INCARCERATED`
**Effect**: `effective_precarity = max_severity(current, PrecarityStatus.EXCLUDED)`
**Rationale**: Incarceration severs labor market participation entirely.

### UNDOCUMENTED Documentation Exclusion
**Trigger**: Agent has membership with `community_type == CommunityType.UNDOCUMENTED`
**Effect**:
- `effective_wealth *= defines.documentation_exclusion_factor`
- `effective_precarity = max_severity(current, PrecarityStatus.PRECARIOUS)`
**Rationale**: Legal exclusion from formal labor protections, housing markets, banking.

### DISABLED Reproduction Cost
**Trigger**: Agent has membership with `community_type == CommunityType.DISABLED`
**Requires**: `CommunityState` for DISABLED community with `reproduction_cost_modifier > 1.0`
**Effect**: `effective_wealth *= (1.0 / state.reproduction_cost_modifier)`
**Rationale**: Higher V_reproduction (accommodation, medical, care) means same nominal wealth buys less class security.

---

## Composition Rules (FR-004)

1. **Independent application**: Each predicate is evaluated independently against the *original* inputs
2. **Most restrictive wins**: `effective_wealth = min(all adjusted percentiles)`
3. **Precarity escalation**: `effective_precarity = max_severity(all adjusted precarities)`
4. **FIRST_NATIONS overrides SETTLER**: If both FIRST_NATIONS and SETTLER memberships present, trust_land_discount applies (SETTLER property interpretation suppressed)
5. **Order-independent**: Result must be the same regardless of membership iteration order

---

## Precarity Severity Order

```
STABLE < PRECARIOUS < MARGINALLY_ATTACHED < EXCLUDED
```

`max_severity(a, b)` returns whichever is more severe (higher in this ordering).
