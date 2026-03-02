# Contract: Faction Balance

**Spec**: FR-C01, FR-C02, FR-C03, FR-C04, FR-C05, FR-C06, FR-C07, FR-C08
**Module**: `src/babylon/models/entities/state_apparatus_ai.py` (model), `src/babylon/ooda/state_ai/faction_dynamics.py` (shift logic), `src/babylon/formulas/state_ai.py` (convergence check)
**Pattern**: Frozen Pydantic model with `model_copy(update={})` for mutations

---

## Model Definition

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class FactionBalance(BaseModel):
    """Weight vector over three state factions, summing to 1.0.

    Primitive fields (stored): finance_capital, security_state, settler_populist.
    Computed (derived): dominant_faction, stability.
    Satisfies Constitution II.2 (Primitives vs Derived).

    Args:
        finance_capital: Weight of Finance-Capital faction [0.0, 1.0].
        security_state: Weight of Security-State faction [0.0, 1.0].
        settler_populist: Weight of Settler-Populist faction [0.0, 1.0].
    """

    model_config = ConfigDict(frozen=True)

    finance_capital: float
    security_state: float
    settler_populist: float

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> FactionBalance:
        total = self.finance_capital + self.security_state + self.settler_populist
        if not (0.99 <= total <= 1.01):
            msg = f"Faction weights must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self
```

---

## Behavioral Contracts

### F-01: Weight Normalization

```
GIVEN any FactionBalance instance
WHEN faction weights are accessed
THEN finance_capital + security_state + settler_populist is within [0.99, 1.01]
```

**Mechanism**: `model_validator(mode="after")` enforces the constraint at construction time. The 0.01 tolerance accounts for floating-point arithmetic in re-normalization after shifts.

**Invariant**: No code path can produce a `FactionBalance` that violates this constraint. Any shift operation MUST re-normalize before constructing the new `FactionBalance`.

---

### F-02: Heat Triggers Security-State Shift

```
GIVEN player generates sustained Heat > 0.5 for 8 consecutive ticks
WHEN faction balance is updated in Layer 3 consequence propagation
THEN security_state weight has increased by at least
     minimum_effect_floor (default 0.02) from its value at tick 0
AND the increase is sourced from finance_capital and settler_populist
     (re-normalized to sum to 1.0)
```

**Shift mechanics** (FR-C04): Player-generated Heat is the primary trigger for Security-State weight gain. The shift magnitude is proportional to Heat level, clamped to `max_faction_shift_per_tick` (default 0.05) per tick.

**Test** (SC-010): Over 100 seeded runs with sustained Heat > 0.5, the Security-State weight increase MUST be detectable by 2-sided t-test at p<0.05. Minimum shift: 0.02 per triggering event.

---

### F-03: Successful Repression Failure Triggers Security-State Decline

```
GIVEN state performs REPRESS_RAID targeting a player organization
AND the target organization survives (membership retained > 50%)
WHEN Layer 3 consequence propagation runs for that tick
THEN security_state weight decreases
AND the decrease magnitude is at least minimum_effect_floor (0.02)
```

**Rationale** (FR-C04): "Surviving repression decreases Security-State credibility." Failed repression demonstrates that the repressive apparatus is ineffective, shifting factional balance away from Security-State toward Finance-Capital (which prefers co-optation) or Settler-Populist (which may demand harsher measures).

**Survival threshold**: "Membership retained > 50%" means the organization's post-RAID membership count is more than half the pre-RAID count. Partial survival (e.g., 60% retained) still counts as a repression failure for this contract.

---

### F-04: Fascist Convergence Detection

```
GIVEN FactionBalance with:
  - security_state > 0.4
  - settler collective_identity > 0.6 with ASSIMILATIONIST_FASCIST tendency
  - finance_capital < 0.25
AND these conditions hold for convergence_confirmation_ticks (default 2)
    consecutive ticks
WHEN is_fascist_convergence() is called
THEN returns True
```

**Three-pillar model** (FR-C06, R-008):
1. Security-State dominance: the repressive apparatus has internal control
2. Settler-Populist mass base: lateral antagonism provides popular support for repression
3. Finance-Capital acquiescence: capital has given up on co-optation as a strategy

**All three conditions MUST hold simultaneously.** Missing any single condition returns `False`:
- SS > 0.4 but settler CI < 0.6: police state, not fascism (no mass base)
- SS > 0.4 and settler CI > 0.6 but FC > 0.25: contested state, Finance-Capital still resisting
- Settler CI > 0.6 but SS < 0.4: populist reaction without repressive apparatus backing

**Confirmation window**: Conditions must hold for `convergence_confirmation_ticks` consecutive ticks to prevent single-tick spikes from triggering convergence. Default 2 ticks is the minimum non-trivial confirmation.

**Integration**: Emits `FASCIST_CONVERGENCE` event via EventBus when convergence is first detected, consumed by BifurcationMonitor (Feature 033).

---

### F-05: Fascist Near-Absorbing State

```
GIVEN fascist convergence has been detected (F-04 returned True)
WHEN conditions partially revert (e.g., security_state drops to 0.38)
THEN the system resists reversion with high friction
AND fascist mode persists UNLESS:
  - security_state drops below reversion_ss_threshold (default 0.25)
  AND settler collective_identity drops below reversion_ci_threshold (default 0.30)
```

**Asymmetric entry/exit thresholds** (FR-C07, R-008):
- Entry: SS > 0.4, settler CI > 0.6, FC < 0.25
- Exit: SS < 0.25, settler CI < 0.30

The exit thresholds are substantially harder to reach than the entry thresholds. Security-State must drop from >0.4 to <0.25 (a 0.15+ swing), and settler CI from >0.6 to <0.30. This models the historical reality that fascism is easier to enter than to exit.

**Fascist mode behavioral changes** (FR-C07):
- CO_OPT budget redirects to REPRESS
- DEVELOP shifts to displacement-oriented sub-verbs (DISPLACE, REZONE)
- WITHDRAW becomes SCORCHED_EARTH in contested territories
- LEGISLATE shifts toward EMERGENCY_POWERS

**Test**: Enter fascist convergence. Set SS to 0.38 (above reversion threshold). Verify `is_fascist_convergence()` still returns `True` (near-absorbing). Then set SS to 0.24 AND settler CI to 0.29. Verify `is_fascist_convergence()` returns `False` (reversion achieved).
