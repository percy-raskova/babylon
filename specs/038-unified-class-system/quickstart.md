# Quickstart: Unified Class System (038)

**Purpose**: Developer onboarding for implementing and consuming the unified class system.

---

## What This Feature Does

The unified class system reconciles two class determination frameworks:

1. **Accounting criterion**: V_produced vs V_reproduction (theoretical)
2. **Wealth percentile**: Fed SCF data mapped to five ClassPosition values (empirical)

It adds **community filtration** — hyperedge memberships (FIRST_NATIONS, INCARCERATED, UNDOCUMENTED, DISABLED) modify classification inputs before classification. It also provides **solidarity potential** between class-block pairs using a 5x5 class-pair matrix, community overlap, and imperial rent differential.

---

## Key Files

| File | Role |
|------|------|
| `src/babylon/economics/melt/unified_classifier.py` | **NEW** — UnifiedClassifier protocol + default impl |
| `src/babylon/economics/melt/filtration.py` | **NEW** — FiltrationResult, apply_filtration() |
| `src/babylon/economics/melt/rent_differential.py` | **NEW** — RentDifferentialCalculator protocol + default impl |
| `src/babylon/config/defines.py` | **MODIFIED** — +ClassSystemDefines sub-model |
| `src/babylon/models/enums.py` | **MODIFIED** — +CALIBRATION_DISAGREEMENT EventType |
| `src/babylon/economics/melt/class_position.py` | **UNCHANGED** — base classifier (wrapped, not modified) |
| `src/babylon/formulas/community.py` | **UNCHANGED** — solidarity potential formula |
| `src/babylon/economics/melt/wealth_proxy.py` | **UNCHANGED** — LA share proxy |

---

## Usage Examples

### Classify without filtration (backward compatible)

```python
from babylon.economics.melt.unified_classifier import DefaultUnifiedClassifier
from babylon.economics.melt.types import PrecarityStatus

classifier = DefaultUnifiedClassifier()

# Identical to DefaultClassPositionClassifier
position = classifier.classify_with_filtration(
    wealth_percentile=75.0,
    precarity=PrecarityStatus.STABLE,
)
# → ClassPosition.LABOR_ARISTOCRACY
```

### Classify with community filtration

```python
from babylon.economics.melt.unified_classifier import DefaultUnifiedClassifier
from babylon.economics.melt.types import PrecarityStatus
from babylon.models.enums import CommunityType
from babylon.models.entities.community import CommunityMembership, CommunityState

classifier = DefaultUnifiedClassifier()

# FIRST_NATIONS household with 60th percentile wealth
memberships = [
    CommunityMembership(agent_id="H001", community_type=CommunityType.FIRST_NATIONS),
]
states = {
    CommunityType.FIRST_NATIONS: CommunityState(community_type=CommunityType.FIRST_NATIONS),
}

position = classifier.classify_with_filtration(
    wealth_percentile=60.0,
    precarity=PrecarityStatus.STABLE,
    memberships=memberships,
    community_states=states,
)
# effective_wealth = 60.0 * 0.5 (trust_land_discount) = 30.0
# → ClassPosition.PROLETARIAT (below 50th percentile after filtration)
```

### Inspect filtration details

```python
result = classifier.apply_filtration(
    wealth_percentile=60.0,
    precarity=PrecarityStatus.STABLE,
    memberships=memberships,
    community_states=states,
)
# result.original_wealth_percentile = 60.0
# result.effective_wealth_percentile = 30.0
# result.applied_predicates = ["FIRST_NATIONS_trust_land"]
# result.most_restrictive_community = CommunityType.FIRST_NATIONS
```

### Compute solidarity potential with class-pair matrix

```python
from babylon.config.defines import GameDefines
from babylon.formulas.community import calculate_solidarity_potential

defines = GameDefines()

# Two proletarians sharing one community, no rent differential
base = defines.class_system.get_base_solidarity("PROLETARIAT", "PROLETARIAT")
# base = 0.80

potential = calculate_solidarity_potential(
    base_solidarity=base,
    shared_count=1,
    rent_a=0.02,
    rent_b=0.02,
    overlap_bonus=defines.community.community_overlap_bonus,
    rent_penalty=defines.community.rent_differential_penalty,
)
# potential = 0.80 + 0.1*1 - 0.05*0.0 = 0.90

# Bourgeoisie vs proletariat across colonial divide
base_antag = defines.class_system.get_base_solidarity("BOURGEOISIE", "PROLETARIAT")
# base_antag = 0.00

potential_antag = calculate_solidarity_potential(
    base_solidarity=base_antag,
    shared_count=0,
    rent_a=0.15,
    rent_b=0.02,
    overlap_bonus=defines.community.community_overlap_bonus,
    rent_penalty=defines.community.rent_differential_penalty,
)
# potential_antag = 0.00 + 0.0 - 0.05*0.13 = -0.0065 (active antagonism)
```

---

## Testing Strategy

All tests follow TDD (Red-Green-Refactor). Test files mirror source modules:

```bash
# Run all unified class system tests
poetry run pytest tests/unit/economics/melt/test_filtration.py -v
poetry run pytest tests/unit/economics/melt/test_unified_classifier.py -v
poetry run pytest tests/unit/economics/melt/test_rent_differential.py -v

# Run with coverage
poetry run pytest tests/unit/economics/melt/ -v --cov=src/babylon/economics/melt
```

---

## Architecture Decisions

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| Wrapper, not subclass | SRP + backward compat (FR-012) | research.md R-001 |
| No Household model | Spec is agnostic; SocialClass works at current resolution | research.md R-002 |
| FIRST_NATIONS not INDIGENOUS | Matches existing CommunityType enum | research.md R-003 |
| Filtration in economics/melt/ | Same subsystem as classification | research.md R-004 |
| Event bus for calibration log | Follows existing observer pattern | research.md R-006 |
| Rent differential Protocol | Follows project's DI convention | research.md R-007 |

---

## Dependencies to Verify Before Implementation

1. `CommunityType.FIRST_NATIONS` exists in `models/enums.py` (confirmed)
2. `CommunityState.reproduction_cost_modifier` exists (confirmed, default 1.0)
3. `CommunityDefines.community_overlap_bonus` exists (confirmed, default 0.1)
4. `CommunityDefines.rent_differential_penalty` exists (confirmed, default 0.05)
5. `DefaultClassPositionClassifier` can be instantiated standalone (confirmed, no constructor args)
6. `calculate_solidarity_potential` signature matches expected usage (confirmed)
7. `NoDataSentinel` importable from `economics/tensor.py` (confirmed)
