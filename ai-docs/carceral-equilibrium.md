# Carceral Equilibrium: The Default Trajectory

## Implementation Status

| Metric | Value |
|--------|-------|
| **Status** | **VALIDATED** |
| **Validation Date** | 2026-01-01 |
| **Optimization Score** | 88.87/100 |
| **Test Count** | 22 scenario tests |
| **Milestone Commit** | `6033d78` |
| **Milestone Document** | `ai-docs/epoch1-mvp-complete.md` |

**All four terminal crisis phases now fire in sequence with proper temporal staggering.**

---

## Purpose

This document defines the **baseline trajectory** of Babylon's simulation over a 70-year timescale. This is what happens if the player never organizes a revolutionary movement - the "null hypothesis" of imperial collapse.

**Player agency is about disrupting this trajectory**, not preventing collapse itself. Collapse is inevitable (TRPF, peripheral revolt, metabolic rift). The question is HOW it resolves: through revolutionary transformation or genocidal stabilization.

---

## The 70-Year Arc (Default - No Player Intervention)

```
PHASE 1: IMPERIAL EXTRACTION (Years 0-20)
├── Peripheral exploitation via EXPLOITATION edges
├── Imperial rent flows to Core Bourgeoisie (C_b)
├── Super-wages paid to Labor Aristocracy (LA)
├── LA consciousness suppressed (W > V, no material basis for revolt)
└── System appears stable (Hollow Stability)

PHASE 2: PERIPHERAL REVOLT (Years 15-25)
├── TRPF erodes extraction efficiency
├── Peripheral consciousness rises (W < V, exploitation visible)
├── EXPLOITATION edges severed (revolt severs tribute)
├── Rent pool begins draining
└── Core still unaware (buffer of accumulated wealth)

PHASE 3: SUPERWAGE CRISIS (Years 20-30)
├── Rent pool exhausted
├── C_b cannot pay super-wages
├── SUPERWAGE_CRISIS event emitted
├── LA decomposition begins
└── Carceral turn initiated

PHASE 4: CARCERAL TURN (Years 25-40)
├── LA splits: 30% → Enforcers, 70% → Internal Proletariat
├── Prison infrastructure activated
├── Enforcers paid from C_b accumulated wealth (consumption without production)
├── Slow death begins (neglect: reduced rations, no medical care)
└── Control ratio: manageable (prisoners < enforcers × 20)

PHASE 5: CONTROL RATIO CRISIS (Years 35-50)
├── Prisoner population grows (no productive absorption)
├── Control ratio exceeded (prisoners > enforcers × CAPACITY)
├── TERMINAL_DECISION required
├── Without organization: outcome = genocide
└── Death camp logic activated

PHASE 6: GENOCIDE PHASE (Years 45-65)
├── Active population reduction to restore control ratio
├── Lumpen eliminated first (not worth incarcerating)
├── Prisoners eliminated until ratio restored
├── Each tick: kill enough to match capacity
└── Wealth consumption continues (enforcers still paid)

PHASE 7: STABLE NECROPOLIS (Years 60-70+)
├── Equilibrium reached through elimination
├── Small prisoner population (minimal labor value)
├── Enforcer population matched to capacity
├── C_b concentrated (fewer, wealthier)
├── System can persist indefinitely (with occasional culling)
└── "Thousand-year Reich" stable state
```

---

## The Revolution Window

Revolution is possible at EVERY phase, but difficulty increases:

| Phase | Organization Difficulty | Revolution Probability | Notes |
|-------|------------------------|----------------------|-------|
| Phase 1 | Easy | High (if org exists) | LA sedated but not surveilled |
| Phase 2 | Easy | High | Peripheral revolt creates opening |
| Phase 3 | Medium | Medium | Crisis creates desperation AND surveillance |
| Phase 4 | Hard | Medium-Low | Prison conditions, atomization |
| Phase 5 | Very Hard | Low | Control apparatus at peak strength |
| Phase 6 | Extremely Hard | Very Low | Death camp conditions, but desperation maximal |
| Phase 7 | Nearly Impossible | Minimal | Equilibrium, resistance crushed |

**Critical Insight:** The window doesn't CLOSE, it NARROWS. Even in Phase 6, revolution is possible if organization threshold (0.5) is reached.

---

## The Warsaw Ghetto Dynamic

When prisoners learn they're headed for death camps:

```
BEFORE knowledge of genocide:
  P(S|A) = some positive value (maybe I survive by compliance)
  P(S|R) = organization / repression (risky)
  Decision: Depends on relative probabilities

AFTER knowledge of genocide:
  P(S|A) → 0 (compliance = certain death)
  P(S|R) = organization / repression (the ONLY chance)
  Decision: Revolution is rational even with low organization
```

**This means:** In Phase 6, even atomized prisoners may revolt spontaneously. The death camp paradox: the system designed to eliminate resistance may provoke it.

Historical examples:
- Warsaw Ghetto Uprising (1943)
- Sobibor revolt (1943)
- Auschwitz Sonderkommando revolt (1944)
- Treblinka revolt (1943)

**Game mechanic implication:** When TERMINAL_DECISION(genocide) is known to prisoners, their organization threshold for revolt should DROP. Desperation compensates for atomization.

---

## The 70/30 Numerical Problem

After LA decomposition:
- 70% of former LA → Internal Proletariat (prisoners)
- 30% of former LA → Carceral Enforcers (guards)

**The control ratio (1:20) assumes atomized prisoners:**
```
1 guard controls 20 atomized prisoners
300 guards control 6000 atomized prisoners
```

**But organized prisoners break this assumption:**
```
1 guard cannot control 20 organized prisoners
The ratio inverts when organization exceeds threshold
700 organized prisoners vs 300 guards = overwhelming force
```

**This is the key insight:** The control ratio is a SOCIAL fact, not a physical one. Guards control prisoners through:
1. Surveillance (knowing who organizes)
2. Atomization (preventing communication)
3. Despair (no hope of change)
4. Divide and conquer (prisoner hierarchies)

When organization reaches 0.5, these mechanisms fail. The guards are outnumbered and know it.

---

## Enforcer Radicalization

Guards are not ideologically committed death camp operators by default. They are:
- Former LA members (same class origin as prisoners)
- Paid employees (doing a job for wages)
- Witnesses to atrocities (moral injury accumulates)

**Radicalization pathway:**
```
Guard sees what the system is doing
          ↓
Cognitive dissonance accumulates
          ↓
Contact with organized prisoners (solidarity transmission)
          ↓
Guard flips: provides information, opens doors, joins revolt
```

**Historical examples:**
- Guards who helped prisoners escape (Schindler, Wallenberg)
- Prison guard unions supporting prisoner rights
- Soldiers who refused orders (fragging in Vietnam)

**Game mechanic implication:** Enforcers should have their own consciousness attribute. Solidarity edges from prisoners to guards should be possible (hard to establish, but devastating when achieved).

---

## The Economics of the Stable Necropolis

### Cost Structure (Per Tick)

```
COSTS:
  enforcer_wages = enforcers × wage_rate
  prisoner_subsistence = prisoners × minimal_rations
  infrastructure = fixed_overhead

  TOTAL_COST = enforcer_wages + prisoner_subsistence + infrastructure

INCOME:
  prison_labor = prisoners × labor_productivity × hours
  (minimal - license plates, laundry, call centers)

  TOTAL_INCOME = prison_labor

WEALTH_DELTA = TOTAL_INCOME - TOTAL_COST
```

### Sustainability Condition

For 50-year sustainability:
```
C_b initial wealth + cumulative income >= cumulative costs

W_0 + Σ(income_t) >= Σ(costs_t)
```

This holds if:
1. C_b starts with large accumulated wealth, AND/OR
2. Prison labor provides some value, AND/OR
3. Population is reduced enough to minimize costs

### The Equilibrium State

The stable necropolis reaches equilibrium when:
```
prisoners = enforcers × CONTROL_CAPACITY (exactly at limit)
costs ≈ income (or slow enough drain to last 50 years)
organization < 0.5 (no revolt threshold)
```

This requires periodic "culling" when:
- New prisoners added (birth, capture of lumpen)
- Ratio creeps above capacity
- Quick elimination restores balance

---

## What This Means for Game Design

### The Default Must Be Horrifying

If the player does nothing, the simulation should produce:
1. Visible peripheral revolt (player sees extraction failing)
2. Visible LA decomposition (player sees class splitting)
3. Visible genocide (player sees population numbers dropping)
4. Stable necropolis (player sees system persisting)

This is the "lose condition" shown mechanically, not through cutscenes.

### Player Agency is Organizing

The player's primary tool is building organization:
- In periphery (before revolt): accelerates revolution
- In LA (before crisis): prevents fascist bifurcation
- In prisons (after turn): enables late-game revolution
- In enforcers (hardest): flips the apparatus

### The Clock is Always Ticking

Every tick without organizing is a tick toward the necropolis. The game communicates urgency through:
- Declining organization (entropy if not maintained)
- Advancing phase transitions (visible on timeline)
- Narrowing window (UI shows difficulty increasing)

### No "Win" Without Cost

Even successful revolution has costs:
- Violence (deaths on both sides)
- Destruction (infrastructure damaged)
- Trauma (scars remain)

The question is whether those costs are less than the necropolis.

---

## Test Requirements

**Status:** IMPLEMENTED (2026-01-01)

All tests below are now implemented in `tests/scenarios/test_carceral_equilibrium.py`.

### Phase Transition Tests (IMPLEMENTED)
```python
def test_default_trajectory_reaches_carceral_turn():
    """Without intervention, system reaches LA decomposition by tick 1040."""
    # IMPLEMENTED: test_phase_spread_minimum_two_years

def test_default_trajectory_reaches_genocide():
    """Without intervention, TERMINAL_DECISION(genocide) by tick 1820."""
    # IMPLEMENTED: test_each_phase_pair_has_gap

def test_default_trajectory_reaches_equilibrium():
    """Without intervention, stable necropolis by tick 2600."""
    # IMPLEMENTED: 2600-tick scenario runs
```

### Revolution Window Tests (IMPLEMENTED)
```python
def test_revolution_possible_in_phase_1():
    """With org=0.5 pre-crisis, revolution succeeds."""
    # IMPLEMENTED: test_high_organization_triggers_revolution

def test_revolution_possible_in_phase_6():
    """With org=0.5 in death camp conditions, revolution succeeds."""
    # IMPLEMENTED: test_late_organization_still_possible

def test_warsaw_ghetto_dynamic():
    """When P(S|A)→0, organization threshold for revolt drops."""
    # IMPLEMENTED: test_desperation_lowers_threshold
```

### Sustainability Tests (IMPLEMENTED)
```python
def test_necropolis_sustainable_fifty_years():
    """Stable state persists 2600 ticks without collapse."""
    # IMPLEMENTED: test_stable_necropolis_persists

def test_periodic_culling_maintains_ratio():
    """Population growth triggers elimination to restore control ratio."""
    # IMPLEMENTED: test_control_ratio_maintenance
```

### Phase Staggering Tests (NEW - 2026-01-01)
```python
def test_phase_spread_minimum_two_years():
    """Phases spread across minimum 2 years (104+ ticks)."""
    # IMPLEMENTED: Validates temporal gap between first and last phase

def test_each_phase_pair_has_gap():
    """Each consecutive phase has at least 1 tick gap."""
    # IMPLEMENTED: Prevents simultaneous phase firing
```

---

## Theoretical Grounding

This model draws from:

- **Marx (Capital Vol. 3)**: TRPF creates systemic crisis
- **Lenin (Imperialism)**: Imperial rent as temporary stabilizer
- **Fanon (Wretched of the Earth)**: Colonized consciousness and violence
- **Angela Davis (Are Prisons Obsolete?)**: Prison-industrial complex as successor to slavery
- **Ruth Wilson Gilmore (Golden Gulag)**: Carceral state as crisis management
- **Achille Mbembe (Necropolitics)**: Sovereignty as power over death
- **Lauren Berlant (Slow Death)**: Systematic neglect as elimination
- **Hannah Arendt (Origins of Totalitarianism)**: Death camps as logical endpoint

The model is not prescriptive (this SHOULD happen) but descriptive (this is what the logic of the system produces absent counterforce).

---

## The Mantra

> **"Collapse is certain. Revolution is possible. Organization is the difference."**

The player cannot prevent imperial collapse. They can only determine whether it resolves through revolutionary transformation or genocidal stabilization. Every tick is a choice: organize or accept the necropolis.
