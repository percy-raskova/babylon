# Quickstart: OODA Loop System (Feature 032)

**Feature Branch**: `032-ooda-loop-system`
**Date**: 2026-02-28

## What This Feature Does

The OODA Loop System adds organizational action resolution to the Babylon simulation. Each tick, organizations observe their environment, orient to conditions, decide on actions, and act — constrained by their OODA profile. Actions produce both direct effects and consciousness side-effects on target communities.

**Key concepts**:
- **Three-phase turn**: Layer 0 (automatic metabolism) → Action Phase (initiative-ordered) → Layer 3 (consequence propagation)
- **Initiative scoring**: Dynamic ordering — state starts with advantage but revolutionaries can seize initiative
- **21 action types**: EDUCATE, RECRUIT, REPRESS, SURVEIL, etc. — each with eligibility rules and consciousness effects
- **Community-modified costs**: Actions cost less in your own community, more across contradiction axes

## Prerequisites

- Feature 031 (Organization Base Model) — org subtypes, consciousness effects
- Feature 029 (Community Hyperedge Upgrade) — community consciousness, contradiction axes
- Feature 030 (D-P-D' Lifecycle Circuit) — lifecycle composition

## Code Layout

```
src/babylon/ooda/              # Domain logic
├── types.py                   # OODAProfile, Action, ActionResult, etc.
├── initiative.py              # Initiative score computation
├── cycle_time.py              # OODA cycle time from profile
├── action_costs.py            # Cost modifiers by org-community relationship
├── action_eligibility.py      # Which orgs can do which actions
├── action_effects.py          # Action execution + consciousness effects
├── layer0.py                  # Automatic economic metabolism
├── layer3.py                  # Consequence propagation
└── npc_stub.py                # Simple NPC action selection

src/babylon/engine/systems/
└── ooda.py                    # OODASystem (engine integration)

src/babylon/config/defines.py  # OODADefines sub-model added
src/babylon/models/enums.py    # DecisionMode, ActionType enums added
```

## How to Use

### Creating an OODAProfile

```python
from babylon.ooda.types import OODAProfile
from babylon.models.enums import DecisionMode

# Fast vanguard party
vanguard_profile = OODAProfile(
    sensor_latency=2,
    ideological_coherence=0.8,
    analytical_capacity=0.7,
    decision_mode=DecisionMode.AUTOCRATIC,
    bureaucratic_depth=0.2,
    action_points=4,
    coordination_range=3,
    autonomy=0.2,
)

# Slow consensus-based CSO
church_profile = OODAProfile(
    sensor_latency=2,
    ideological_coherence=0.3,
    decision_mode=DecisionMode.CONSENSUS,
    bureaucratic_depth=0.2,
    action_points=2,
    coordination_range=1,
    autonomy=0.7,
)
```

### Computing Cycle Time and Initiative

```python
from babylon.ooda.cycle_time import compute_cycle_time
from babylon.ooda.initiative import compute_initiative_score
from babylon.config.defines import GameDefines

defines = GameDefines()

# Cycle time (lower = faster)
ct = compute_cycle_time(vanguard_profile, defines.ooda)
# ct ≈ 5.12

# Initiative score
score = compute_initiative_score(
    org_id="faction_1",
    cycle_time=ct,
    jurisdiction=None,  # Not a state apparatus
    counter_intel_score=0.6,
    community_embeddedness=0.9,
    momentum=0.3,
    defines=defines.ooda,
)
# score.score ≈ 2.59 (can exceed local PD)
```

### Creating and Resolving Actions

```python
from babylon.ooda.types import Action
from babylon.models.enums import ActionType
from babylon.ooda.action_eligibility import check_eligibility
from babylon.ooda.action_effects import resolve_action

# Create an EDUCATE action
action = Action(
    org_id="faction_1",
    action_type=ActionType.EDUCATE,
    target_id="community_new_afrikan_detroit",
    action_point_cost=1,
)

# Check eligibility
assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.EDUCATE, org_attrs)

# Resolve
result = resolve_action(action, org_attrs, target_attrs, graph, defines.ooda)
# result.consciousness_delta.collective_identity_delta ≈ +0.034
```

### Full Tick Resolution (via Engine)

The OODASystem integrates with the existing SimulationEngine:

```python
from babylon.engine.simulation_engine import step

# OODASystem is registered at position 14 in _DEFAULT_SYSTEMS
new_state = step(state, config)
# Organizations have acted, consciousness has shifted, heat has changed
```

## Key Design Decisions

1. **Additive initiative formula**: Speed + institutional + counter-intel + embeddedness + momentum. Additive so no single zero kills the score.

2. **DPDState pattern for storage**: OODAProfile stored as serialized dict on org nodes (`ooda_profile=profile.model_dump()`), not as flat attributes.

3. **Extend Feature 031 consciousness formula**: Action base multiplier scales the existing five-factor product. No separate formula per action type.

4. **Three-tier cost modification**: Embedded (discount), outsider (surcharge), contradiction (heavy surcharge). Membership overlap drives the discount.

5. **NPC priority stub**: Deterministic, not random. Each org type has a fixed priority list of preferred actions.

## Testing Approach

```bash
# Run all OODA unit tests
poetry run pytest tests/unit/ooda/ -v

# Run specific test file
poetry run pytest tests/unit/ooda/test_initiative.py -v

# Run Detroit integration test
poetry run pytest tests/integration/test_ooda_detroit.py -v

# Type check the ooda package
poetry run mypy src/babylon/ooda/ --strict
```

## Configuration

All coefficients are in `GameDefines.ooda` (instance of `OODADefines`). Key parameters to tune:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `institutional_bonus_federal` | 5.0 | How much advantage FBI has |
| `institutional_bonus_local` | 1.5 | How much advantage local PD has |
| `max_ci_delta_per_tick` | 0.05 | Maximum consciousness change per action per tick |
| `agitation_educate_bonus` | 1.5 | EDUCATE bonus in agitated communities |
| `contradiction_cost_multiplier` | 2.5 | Cost penalty across contradiction axis |
| `momentum_decay` | 0.8 | How fast momentum fades |
