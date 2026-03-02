# Quickstart: State Apparatus AI (039)

**Purpose**: Developer onboarding for implementing and consuming the state apparatus AI system.

---

## What This Feature Does

The state apparatus AI models the US state as a factional coalition of Finance-Capital, Security-State, and Settler-Populist interests. Each tick, the state selects one action from a six-verb taxonomy (ADMINISTER, DEVELOP, RESEARCH, CO_OPT, REPRESS, WITHDRAW) based on a factional objective function, budget constraints, and intelligence gathered through attention threads. The player's actions do not just provoke state responses -- they shift which faction dominates, changing the character of the adversary itself.

---

## Key Concepts

| Term | Definition |
|------|-----------|
| **FactionBalance** | A weight vector (3 floats summing to 1.0) representing the relative influence of Finance-Capital, Security-State, and Settler-Populist factions within the state. Shifts based on player actions and material conditions. Frozen Pydantic model. |
| **StateBudget** | Per-tick revenue (tax + federal transfers + imperial rent pool) allocated across verb categories by faction-weighted preferences. The binding constraint on non-REPRESS state actions. Budget = 0 forces zero-cost verbs only. |
| **AttentionThread** | A state intelligence resource tracking one target (organization, territory, or community). Accumulates `intel_completeness` over time through surveillance methods. Operates on `G_observed` (incomplete, distorted subgraph of `G_actual`). Progresses through phases: DORMANT, MONITORING, ACTIVE_INVESTIGATION, DISRUPTION. |
| **StateActionType** | Enum of ~24 state verb+sub-verb combinations (e.g., `REPRESS_RAID`, `CO_OPT_BRIBE`, `DEVELOP_INVEST`). Separate from the player's `ActionType` enum -- the two action spaces are disjoint (asymmetry). |
| **SparrowAnalysis** | Network analysis results computed on `G_observed` using Sparrow's (1991) framework: centrality rankings, equivalence classes, singleton identification, cutset detection. Always partial, always potentially wrong due to observation gap. |
| **Fascist Convergence** | A phase transition detected when three conditions hold simultaneously: Security-State weight > 0.4, settler collective_identity > 0.6 (ASSIMILATIONIST_FASCIST), Finance-Capital weight < 0.25. Near-absorbing state -- harder to exit than to enter. |
| **Observation Gap** | The fundamental asymmetry between `G_actual` (true organization topology) and `G_observed` (what the state sees). Distortions include edge type conflation, temporal flattening, informant incentive bias, cash invisibility, and face-to-face blindness. |

---

## Dependencies

This feature builds on six prior specs:

| Spec | Provides | Used By 039 For |
|------|----------|-----------------|
| **031** Organization Base Model | `Organization`, `StateApparatus`, `KeyFigure`, `OrgType` entities; COMMAND/MEMBERSHIP edges | Extending `StateApparatus` with `factional_alignment`; KeyFigure targeting for INCORPORATE |
| **032** OODA Loop System | `OODASystem`, `Action`, `ActionType`, Layer 0/Action/Layer 3 phase structure, `npc_stub.py` | Hook into Layer 1 for state actions; Layer 3 for faction balance shifts; `NPCDecisionStrategy` protocol |
| **033** Bifurcation Topology | `BifurcationMonitor`, `TopologySnapshot`, percolation theory, phase transition detection | Fascist convergence as a new phase transition type; `FASCIST_CONVERGENCE` event |
| **034** Ternary Consciousness | `collective_identity` on communities, consciousness tendency enum (ASSIMILATIONIST_FASCIST, etc.) | Settler CI as fascist convergence input; PROPAGANDIZE targets collective_identity |
| **036** Infrastructure Topology | Territory infrastructure entities, PRESENCE edges, heat dynamics, eviction pipeline | DEVELOP/WITHDRAW effects on territory; heat mechanics; DISPLACE severing infrastructure |
| **038** Unified Class System | `ClassPosition`, community filtration, solidarity potential, class-pair matrix | Class composition effects from INVEST/DISPLACE; solidarity edge targeting for DIVIDE |

---

## Quick Usage Examples

### Creating a FactionBalance

```python
from babylon.models.entities.state_apparatus_ai import FactionBalance

# Detroit 2010 defaults
balance = FactionBalance(
    finance_capital=0.45,
    security_state=0.30,
    settler_populist=0.25,
)

# Computed properties
dominant = balance.dominant_faction  # StateFaction.FINANCE_CAPITAL
```

### Creating an AttentionThread

```python
from babylon.models.entities.attention_thread import AttentionThread
from babylon.models.enums import ThreadPhase, SurveillanceMethod

thread = AttentionThread(
    thread_id="fbi-thread-001",
    target_id="player-org-detroit",
    phase=ThreadPhase.MONITORING,
    intel_completeness=0.0,
    observation_ceiling=0.4,  # FBI ceiling
    active_methods=[SurveillanceMethod.SIGNALS],
    ticks_active=0,
)
```

### Constructing a StateAction

```python
from babylon.models.entities.state_apparatus_ai import StateAction
from babylon.models.enums import StateActionType

action = StateAction(
    verb=StateActionType.CO_OPT_PROPAGANDIZE,
    target_id="community-detroit-sw",
    budget_cost=5.0,
    legitimacy_cost=0.01,
    faction_alignment="FINANCE_CAPITAL",
)
```

### Checking Fascist Convergence

```python
from babylon.formulas.state_ai import is_fascist_convergence

converged = is_fascist_convergence(
    balance=balance,
    settler_ci=0.65,
    settler_tendency="ASSIMILATIONIST_FASCIST",
    defines=game_defines.state_apparatus_ai,
)
# converged = False (FC=0.45 > 0.25 threshold)
```

### Running the State AI Decision Function

```python
from babylon.ooda.state_ai.decision import DefaultStateAIStrategy

strategy = DefaultStateAIStrategy(defines=game_defines.state_apparatus_ai)

action = strategy.select_action(
    world_state=world,
    faction_balance=balance,
    budget=state_budget,
    threads=thread_pool,
    rng=rng,
)
# Returns a StateAction or None if no feasible action exists
```

---

## File Map

```
src/babylon/
  models/
    enums.py                          # EXTEND: StateActionType, StateFaction,
                                      #   ThreadPhase, SurveillanceMethod
    entities/
      state_apparatus_ai.py           # NEW: FactionBalance, StateBudget,
                                      #   StateAction, LegalFramework
      attention_thread.py             # NEW: AttentionThread, ObservationModel,
                                      #   SparrowAnalysis
  ooda/
    npc_stub.py                       # EXTEND: dispatch to NPCDecisionStrategy
                                      #   for StateApparatus org types
    state_ai/                         # NEW: state AI decision architecture
      __init__.py
      decision.py                     #   Factional objective function, verb scoring
      escalation.py                   #   Escalation/de-escalation logic
      faction_dynamics.py             #   Faction balance shift calculations
      protocols.py                    #   NPCDecisionStrategy protocol
    attention/                        # NEW: attention thread system
      __init__.py
      thread_manager.py               #   Thread allocation, meta-OODA
      sparrow.py                      #   Sparrow network analysis on G_observed
      observation.py                  #   Observation gap, surveillance methods
      thread_ooda.py                  #   Per-thread OODA cycle
  formulas/
    state_ai.py                       # NEW: faction shift formulas,
                                      #   fascist convergence check
  config/
    defines.py                        # EXTEND: StateApparatusAIDefines sub-section

tests/
  unit/
    state_ai/                         # NEW: unit tests
      test_faction_balance.py
      test_state_verbs.py
      test_escalation.py
      test_attention_threads.py
      test_sparrow.py
      test_territory_effects.py
  contract/
    state_ai/                         # NEW: behavioral contract tests
      test_decision_contract.py       #   Contracts D-01 through D-06
      test_thread_contract.py         #   Contracts T-01 through T-06
      test_faction_contract.py        #   Contracts F-01 through F-05
      test_territory_contract.py      #   Contracts TE-01 through TE-07
  integration/
    test_state_ai_integration.py      # NEW: 52-tick integration tests
```

---

## Testing

```bash
# Run all state AI unit tests
poetry run pytest tests/unit/state_ai/ -v

# Run behavioral contract tests
poetry run pytest tests/contract/state_ai/ -v

# Run integration tests (52-tick simulations)
poetry run pytest tests/integration/test_state_ai_integration.py -v

# Run a specific contract test file
poetry run pytest tests/contract/state_ai/test_faction_contract.py -v

# Run with coverage
poetry run pytest tests/unit/state_ai/ tests/contract/state_ai/ -v \
    --cov=src/babylon/ooda/state_ai \
    --cov=src/babylon/ooda/attention \
    --cov=src/babylon/formulas/state_ai
```

---

## Integration Points

### 1. npc_stub.py Hook (Primary Entry Point)

The existing `select_npc_actions()` in `src/babylon/ooda/npc_stub.py` dispatches NPC behavior by `OrgType`. For `OrgType.STATE_APPARATUS`, it will delegate to the `NPCDecisionStrategy` protocol instead of the generic priority queue. This is the primary integration seam.

### 2. OODA Layer 1 (State Acts First)

State actions resolve in Layer 1 of the OODASystem, BEFORE initiative-ordered player/NPC actions. The `SimulationEngine` tick pipeline gains a state-action phase between Layer 0 (automatic Business metabolism) and the Action Phase. The state sets the conditions that other organizations respond to.

### 3. Layer 3 Consequences (Faction Balance Shifts)

Faction balance shifts are computed in Layer 3 as consequences of the tick's events. Both state and player actions contribute to faction shifts:
- Player Heat generation shifts Security-State weight upward
- Failed repression shifts Security-State weight downward
- Extraction disruption shifts Finance-Capital toward panic
- Successful co-optation reinforces Finance-Capital weight

### 4. EventBus Integration

New event types emitted by the state AI system:
- `FASCIST_CONVERGENCE`: Consumed by BifurcationMonitor (Feature 033)
- `STATE_ACTION_EXECUTED`: Consumed by SessionRecorder for replay/debug
- `FACTION_BALANCE_SHIFTED`: Consumed by observers for narrative generation
- `THREAD_ALLOCATED` / `THREAD_DEALLOCATED`: Consumed by God Mode dashboard
