# Quickstart: Hypergraph Community Layer

**Feature 022** | **Date**: 2026-02-25

## Prerequisites

- Python 3.12+
- Poetry environment with `xgi >= 0.10` (already in pyproject.toml)
- Existing Babylon simulation engine functional

## Verify XGI Available

```bash
poetry run python -c "import xgi; print(xgi.__version__)"
```

## Run Tests

```bash
# Unit tests for community models and formulas
poetry run pytest tests/unit/models/test_community_models.py -v
poetry run pytest tests/unit/formulas/test_community_formulas.py -v

# Unit tests for CommunitySystem
poetry run pytest tests/unit/engine/systems/test_community_system.py -v

# Integration tests (full pipeline with community layer)
poetry run pytest tests/integration/test_community_integration.py -v

# All community tests at once
poetry run pytest -k "community" -v
```

## Type Checking

```bash
poetry run mypy src/babylon/models/entities/community.py --strict
poetry run mypy src/babylon/engine/systems/community.py --strict
poetry run mypy src/babylon/formulas/community.py --strict
```

## Basic Usage

```python
from babylon.models.enums import CommunityType, LegalStatus, MembershipRole
from babylon.models.entities.community import CommunityState, CommunityMembership

# Create a community state
community = CommunityState(
    community_type=CommunityType.NEW_AFRIKAN,
    heat=0.4,
    legal_status=LegalStatus.SURVEILLED,
    cohesion=0.6,
    infrastructure=0.5,
    visibility=0.8,
    reproduction_cost_modifier=1.15,
    rent_access_modifier=0.85,
)

# Create a membership
membership = CommunityMembership(
    agent_id="agent_42",
    community_type=CommunityType.NEW_AFRIKAN,
    role=MembershipRole.ACTIVE,
    strength=0.7,
    visibility=0.6,
    overt=False,
)

# Effective visibility respects overt flag
assert membership.effective_visibility == 0.6
overt_membership = membership.model_copy(update={"overt": True})
assert overt_membership.effective_visibility == 1.0
```

## Verify Simulation Integration

```bash
# Run simulation trace with community layer active
mise run sim:trace

# Run Detroit scenario to verify community effects
mise run sim:run
```
