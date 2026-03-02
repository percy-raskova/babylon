# Contract: UnifiedClassifier

**Spec**: FR-001, FR-002, FR-003, FR-004, FR-012
**Module**: `src/babylon/economics/melt/unified_classifier.py`
**Pattern**: Protocol + DefaultUnifiedClassifier

---

## Protocol Definition

```python
from __future__ import annotations

from typing import Protocol, Sequence

from babylon.economics.melt.types import ClassPosition, PrecarityStatus
from babylon.economics.melt.filtration import FiltrationResult
from babylon.models.enums import CommunityType
from babylon.models.entities.community import CommunityMembership, CommunityState


class UnifiedClassifier(Protocol):
    """Classify households with community filtration support.

    Wraps the existing ClassPositionClassifier with filtration predicates
    that modify classification inputs based on community memberships.
    When no community data is provided, results are identical to
    DefaultClassPositionClassifier (FR-012 backward compatibility).
    """

    def classify_with_filtration(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        memberships: Sequence[CommunityMembership] | None = None,
        community_states: dict[CommunityType, CommunityState] | None = None,
    ) -> ClassPosition:
        """Classify with optional community filtration.

        Args:
            wealth_percentile: Raw wealth percentile [0, 100].
            precarity: Raw precarity status.
            memberships: Agent's community memberships (None = no filtration).
            community_states: Current community states (None = no filtration).

        Returns:
            ClassPosition after filtration (if applicable).
        """
        ...

    def apply_filtration(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        memberships: Sequence[CommunityMembership],
        community_states: dict[CommunityType, CommunityState],
    ) -> FiltrationResult:
        """Apply community filtration predicates to classification inputs.

        Applies all applicable predicates. When multiple predicates fire,
        the most restrictive result is used (FR-004).

        Args:
            wealth_percentile: Raw wealth percentile [0, 100].
            precarity: Raw precarity status.
            memberships: Agent's community memberships.
            community_states: Current community states.

        Returns:
            FiltrationResult with original and effective values.
        """
        ...

    def classify_dual_criteria(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        v_produced: float,
        v_reproduction: float,
        memberships: Sequence[CommunityMembership] | None = None,
        community_states: dict[CommunityType, CommunityState] | None = None,
    ) -> DualCriteriaResult:
        """Classify using both criteria and report disagreement (FR-002).

        Args:
            wealth_percentile: Raw wealth percentile [0, 100].
            precarity: Raw precarity status.
            v_produced: Value produced by household.
            v_reproduction: Value required for household reproduction.
            memberships: Optional community memberships for filtration.
            community_states: Optional community states for filtration.

        Returns:
            DualCriteriaResult with both classifications and agreement status.
        """
        ...
```

---

## Behavioral Contracts

### BC-001: Backward Compatibility (FR-012)
```
GIVEN wealth_percentile and precarity with NO memberships/community_states
WHEN classify_with_filtration is called
THEN result MUST be identical to DefaultClassPositionClassifier.classify_by_wealth_and_precarity(wealth_percentile, precarity)
```

### BC-002: Filtration Direction (FR-003)
```
GIVEN wealth_percentile and precarity with filtration-triggering memberships
WHEN classify_with_filtration is called
THEN effective_wealth_percentile <= original_wealth_percentile
AND effective_precarity severity >= original_precarity severity
```

### BC-003: FIRST_NATIONS Trust Land Discount
```
GIVEN FIRST_NATIONS membership
WHEN apply_filtration is called
THEN effective_wealth_percentile = wealth_percentile * trust_land_discount
AND "FIRST_NATIONS_trust_land" in applied_predicates
```

### BC-004: INCARCERATED Override
```
GIVEN INCARCERATED membership
WHEN apply_filtration is called
THEN effective_precarity = PrecarityStatus.EXCLUDED
AND "INCARCERATED_precarity_override" in applied_predicates
```

### BC-005: UNDOCUMENTED Discount + Floor
```
GIVEN UNDOCUMENTED membership
WHEN apply_filtration is called
THEN effective_wealth_percentile = wealth_percentile * documentation_exclusion_factor
AND effective_precarity severity >= PrecarityStatus.PRECARIOUS
AND "UNDOCUMENTED_documentation_exclusion" in applied_predicates
```

### BC-006: DISABLED Reproduction Cost
```
GIVEN DISABLED membership with CommunityState.reproduction_cost_modifier = M
WHEN apply_filtration is called
THEN effective_wealth_percentile = wealth_percentile / M (higher cost = lower effective wealth)
AND "DISABLED_reproduction_cost" in applied_predicates
```

### BC-007: Most Restrictive Wins (FR-004)
```
GIVEN multiple filtration-triggering memberships
WHEN apply_filtration is called
THEN effective_wealth_percentile = min(all filtration-adjusted percentiles)
AND effective_precarity = max_severity(all filtration-adjusted precarities)
```

### BC-008: FIRST_NATIONS Overrides SETTLER Property
```
GIVEN both SETTLER and FIRST_NATIONS memberships (mixed context)
WHEN apply_filtration is called
THEN FIRST_NATIONS trust_land_discount is applied
AND SETTLER property interpretation is NOT used
```

### BC-009: Dual Criteria Disagreement Event
```
GIVEN wealth_class != accounting_class from classify_dual_criteria
WHEN agrees = False
THEN a CALIBRATION_DISAGREEMENT event SHOULD be emitted
WITH payload containing agent_id, tick, both classifications, magnitude
```
