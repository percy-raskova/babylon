# Contract: Initiative Scoring

**Feature**: 032-ooda-loop-system
**Date**: 2026-02-28

## Purpose

Defines how initiative scores are computed for each organization per tick, and how organizations are ordered for Action Phase resolution. Initiative determines who acts first — the fundamental strategic advantage.

## Contract: Compute Initiative Score

### Function Signature

```
compute_initiative_score(
    org_id: str,
    cycle_time: float,
    jurisdiction: JurisdictionLevel | None,
    counter_intel_score: float,
    community_embeddedness: float,
    momentum: float,
    defines: OODADefines,
) -> InitiativeScore
```

### Preconditions

1. `cycle_time > 0` (from compute_cycle_time).
2. `jurisdiction` is non-None for StateApparatus; None for other org types.
3. `counter_intel_score` in `[0, 1]`.
4. `community_embeddedness` in `[0, 1]`.
5. `momentum >= 0`.
6. `defines` provides all initiative weights and institutional bonus values.

### Algorithm

```
Step 1: Speed component
  speed = defines.initiative_weight_speed * (1.0 / cycle_time)

Step 2: Institutional component
  if jurisdiction is not None:
    institutional = defines.initiative_weight_institutional * institutional_bonus[jurisdiction]
  else:
    institutional = defines.initiative_weight_institutional * defines.institutional_bonus_nonstate

Step 3: Counter-intelligence component
  counterintel = defines.initiative_weight_counterintel * counter_intel_score

Step 4: Embeddedness component
  embeddedness = defines.initiative_weight_embeddedness * community_embeddedness

Step 5: Momentum component
  momentum_val = defines.initiative_weight_momentum * momentum

Step 6: Composite score
  score = speed + institutional + counterintel + embeddedness + momentum_val
```

### Postconditions

1. `score > 0` always (speed component > 0 since cycle_time > 0).
2. All component values are non-negative.
3. `InitiativeScore` is frozen — components are transparent for debugging.

## Contract: Resolve Action Order

### Function Signature

```
resolve_action_order(scores: list[InitiativeScore]) -> list[InitiativeScore]
```

### Algorithm

```
Sort scores by:
  1. score (descending — highest initiative first)
  2. org_id (ascending — deterministic tiebreaker)
```

### Postconditions

1. Returned list is sorted by descending score.
2. Equal scores broken by org_id (lexicographic ascending).
3. Deterministic: same inputs always produce same ordering.

## Contract: Community Embeddedness

### Function Signature

```
compute_community_embeddedness(org_id: str, graph: GraphProtocol) -> float
```

### Algorithm

```
Step 1: Find all communities where org has members
  org_communities = set of community_types from MEMBERSHIP edge targets

Step 2: Find all communities in org's territories
  territory_communities = set of community_types present in org's territory_ids

Step 3: Compute overlap
  if no territory_communities:
    return 0.0
  overlap = len(org_communities & territory_communities) / len(territory_communities)
  return clamp(overlap, 0.0, 1.0)
```

### Rationale

Embeddedness measures how deeply the organization's membership is woven into the communities it operates in. An org whose members ARE the community has perfect embeddedness. An org parachuted in from outside has zero.

## Contract: Momentum Update

### Function Signature

```
update_momentum(current_momentum: float, action_succeeded: bool, defines: OODADefines) -> float
```

### Algorithm

```
new_momentum = current_momentum * defines.momentum_decay
if action_succeeded:
  new_momentum += defines.momentum_success_bonus
return new_momentum
```

### Properties

1. Momentum decays exponentially (factor 0.8 per tick by default).
2. Each successful action adds a fixed bonus.
3. Momentum is unbounded upward but decays naturally.
4. An organization must keep succeeding to maintain high momentum.

## Worked Example: FBI vs Revolutionary Faction

### Game Start (Tick 0)

**FBI** (StateApparatus, FEDERAL jurisdiction):
```
cycle_time = 4.90 (from profile contract)
speed = 2.0 * (1.0 / 4.90) = 0.408
institutional = 1.0 * 5.0 = 5.0
counterintel = 1.5 * 0.0 = 0.0  (no counter-intel yet)
embeddedness = 1.0 * 0.1 = 0.1  (state is not embedded in communities)
momentum = 0.5 * 0.0 = 0.0      (no actions yet)
TOTAL = 5.508
```

**Revolutionary Faction** (PoliticalFaction):
```
cycle_time = 5.12 (from profile contract)
speed = 2.0 * (1.0 / 5.12) = 0.391
institutional = 1.0 * 0.0 = 0.0  (non-state)
counterintel = 1.5 * 0.0 = 0.0
embeddedness = 1.0 * 0.7 = 0.7  (deeply embedded in community)
momentum = 0.5 * 0.0 = 0.0
TOTAL = 1.091
```

**Result**: FBI (5.508) >> Faction (1.091). State acts first at game start.

### After 20 Ticks of Organizing

**FBI** (unchanged OODA):
```
speed = 0.408
institutional = 5.0
counterintel = 0.0
embeddedness = 0.1
momentum = 0.5 * 0.3 = 0.15  (some successes)
TOTAL = 5.658
```

**Revolutionary Faction** (built counter-intel, high embeddedness, momentum):
```
speed = 0.391
institutional = 0.0
counterintel = 1.5 * 0.6 = 0.9  (counter-intel built over time)
embeddedness = 1.0 * 0.9 = 0.9  (deepened community roots)
momentum = 0.5 * 0.8 = 0.4     (sustained successful actions)
TOTAL = 2.591
```

**Result**: FBI (5.658) > Faction (2.591). FBI still leads — federal bonus is very hard to overcome. But the gap closed from 5:1 to 2:1.

### Against Local PD Instead

**Local PD** (StateApparatus, LOCAL jurisdiction):
```
speed = 2.0 * (1.0 / 6.5) = 0.308  (slower OODA)
institutional = 1.0 * 1.5 = 1.5     (local bonus much lower)
counterintel = 0.0
embeddedness = 0.1
momentum = 0.15
TOTAL = 2.058
```

**Result**: Faction (2.591) > Local PD (2.058). **The faction has seized the initiative from local police.** This demonstrates FR-044: revolutionary organization can exceed local state initiative but federal remains harder.
