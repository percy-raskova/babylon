# Contract: State AI Decision Function

**Spec**: FR-D01, FR-D02, FR-D03, FR-D04, FR-D05, FR-D06, FR-D07, FR-D08
**Module**: `src/babylon/ooda/state_ai/decision.py`
**Pattern**: Protocol (`NPCDecisionStrategy`) + rule-based stub implementation

---

## Behavioral Contracts

### D-01: Factional Objective Scoring

```
GIVEN a WorldState and candidate StateAction
WHEN state_objective(world, action, balance) is called
THEN returns a weighted sum of faction-specific scores
  where score = sum(balance.faction_weight_i * faction_objective_i(action))
  using the current FactionBalance weights
INVARIANT score is deterministic given identical inputs and RNG seed
```

**Faction sub-objectives** (FR-D02, FR-D03, FR-D04):
- Finance-Capital: maximizes extraction_efficiency, profit_rate, stability; minimizes market_disruption, uncertainty
- Security-State: maximizes threat_suppression, apparatus_size, surveillance_coverage; minimizes percolation_ratio, max_collective_identity
- Settler-Populist: maximizes settler_property_values, cultural_homogeneity, imperial_rent_to_base; minimizes cross_line_solidarity, demographic_change

**Test**: Two candidate actions scored under identical world state with different `FactionBalance` weights MUST produce different rankings when the dominant faction changes. For example, `REPRESS_RAID` scores higher than `CO_OPT_BRIBE` under Security-State dominance (SS=0.5), and the reverse under Finance-Capital dominance (FC=0.5).

---

### D-02: Verb Selection Under Budget Constraint

```
GIVEN StateBudget with remaining > 0 and candidate actions with varying budget_cost
WHEN the AI selects an action
THEN selected action has budget_cost <= remaining
AND no budget violation occurs
```

```
GIVEN StateBudget with remaining = 0
WHEN the AI selects an action
THEN returns a zero-cost action (NEGLECT, PROPAGANDIZE with existing infrastructure,
     SURVEIL with existing threads) or None
AND budget remains at 0 (no overdraft)
```

**Invariant**: Across a full 52-tick simulation, the sum of all action budget_costs MUST NOT exceed the sum of all per-tick revenue allocations. No tick ends with `remaining < 0`.

**Test**: Run a 52-tick simulation where initial budget is set to 0.0 and revenue is set to 0.0. Verify that every action selected has `budget_cost == 0.0` or is `None`.

---

### D-03: Escalation Sequence

```
GIVEN monotonically increasing player Heat over N ticks (Heat rises from <0.2 to >0.6)
WHEN state verb selections are recorded over those ticks
THEN verbs shift from low-cost/low-visibility
     (PROPAGANDIZE, SURVEIL, BRIBE)
     toward high-cost/high-visibility
     (RAID, PROSECUTE, DISPLACE)
     in a statistically significant trend
```

**Escalation ladder** (FR-D06, preferred order low to high):
```
PROPAGANDIZE -> BRIBE -> INCORPORATE -> SURVEIL -> DIVIDE
    -> INFILTRATE -> INVEST/REZONE -> FUND(security) -> LEGISLATE
        -> RAID -> PROSECUTE -> DISPLACE -> STRATEGIC_WITHDRAWAL
            -> EMERGENCY_POWERS -> MASS_RAID -> LIQUIDATE -> SCORCHED_EARTH
```

**Statistical test**: Over 100 seeded runs with monotonically increasing Heat, the mean escalation-ladder rank of selected verbs in the last 10 ticks MUST be significantly higher (p<0.05, 2-sided t-test) than in the first 10 ticks. The effect size MUST correspond to at least a 2x increase in REPRESS-category frequency under Security-State dominance (SC-002).

---

### D-04: De-escalation

```
GIVEN player Heat drops to <0.2 after a period of high activity (Heat was >0.6)
WHEN 8 ticks elapse with sustained low Heat
THEN state verb selections shift back toward low-cost options
AND REPRESS-category frequency decreases relative to the high-Heat period
```

**Mechanism** (FR-D07): When player pressure subsides, the factional objective function re-scores actions. With lower Heat, Security-State sub-objectives (threat_suppression) return lower scores, shifting the weighted sum toward Finance-Capital preferences (CO_OPT, DEVELOP).

**Test**: Run a 30-tick simulation: ticks 1-10 with rising Heat (0.2 to 0.8), ticks 11-20 with sustained Heat (0.8), ticks 21-30 with declining Heat (0.8 to 0.1). The mean escalation-ladder rank in ticks 25-30 MUST be lower than in ticks 15-20.

---

### D-05: Determinism

```
GIVEN identical WorldState and RNG seed
WHEN the AI selects actions for 52 ticks
THEN the EXACT same sequence of StateActions is produced
```

**Invariant**: No external state, no system clock, no non-deterministic operations. The decision function is a pure function of (WorldState, FactionBalance, StateBudget, AttentionThreadPool, RNG).

**Test**: Two independent runs with `seed=42` and identical initial WorldState produce byte-identical action sequences. Any divergence is a determinism violation (FR-D08).

---

### D-06: One Action Per Tick (Default)

```
GIVEN default configuration (actions_per_tick=1)
WHEN state AI completes a tick
THEN exactly one StateAction (or None) is emitted
```

```
GIVEN configuration with actions_per_tick=3
WHEN state AI completes a tick
THEN at most 3 StateActions are emitted
AND each action's budget_cost is checked against remaining budget AFTER
    previous actions in the same tick have consumed their costs
```

**Design note** (FR-D05): `actions_per_tick` is configurable in `StateApparatusAIDefines` to allow future multi-action mechanics without architectural changes. The default of 1 is sufficient for Detroit-scale MVP.
