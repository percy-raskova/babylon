# The Warlord Trajectory: Epoch 2 Expansion

> "When the money runs out, the man with the gun becomes the boss."

## Overview

This document outlines a proposed Epoch 2 expansion that adds **branching trajectories** to the Carceral Equilibrium endgame. The current simulation models a single outcome; Epoch 2 will implement conditional branching based on material conditions.

## The Discovery

Running 100-year simulations revealed unexpected wealth dynamics:

```
Year 0:   C_b wealth = 1.10    LA wealth = 9.62
Year 100: C_b wealth = 0.01    LA wealth = 15,954.87
```

### Two Interpretations

**Interpretation A: Bug (Classical Political Economy)**
- Capital should concentrate upward during crisis
- The bourgeoisie should thrive while others suffer
- This is how capitalism has historically functioned
- The math is fundamentally flawed

**Interpretation B: Feature (Warlord Trajectory)**
- When bourgeoisie can no longer pay enforcers, a coup becomes possible
- Enforcers control the actual means of violence (tanks, drones, helicopters)
- The bourgeoisie only controls violence BY PROXY through money
- This is historically accurate for failed states and military juntas

**Resolution: Both are valid trajectories that should branch based on conditions.**

---

## The Key Insight: Means of Violence

The bourgeoisie do not personally control the means of violence. They control them **by proxy through money**:

```
C_b (bourgeoisie)
    │
    ├──[PAYMENT]──► Enforcers ──[CONTROL]──► Means of Violence
    │                                            │
    │                                            ├── Tanks
    │                                            ├── Helicopters
    │                                            ├── Drones
    │                                            ├── Machine guns
    │                                            └── Prisons
    │
    └──[PROFIT]──► C_b accumulates wealth
```

When payment stops, enforcers still have the weapons. The chain of command depends on continued payment.

### The Coup Opportunity

```
IF C_b.wealth < threshold AND payment_streak == 0:
    enforcers realize they have the guns
    enforcers realize C_b is vulnerable
    WARLORD_COUP becomes possible
```

---

## Historical Parallels

### The Praetorian Guard Problem

The Roman Praetorian Guard was the personal bodyguard of the Emperor. Over time, they realized their power:

- 41 CE: Assassinated Caligula, installed Claudius
- 193 CE: Auctioned the empire to the highest bidder
- 217 CE: Killed Caracalla
- 235-284 CE: The Crisis of the Third Century (50 years, 26 emperors)

The Guard controlled the means of violence. When emperors couldn't pay or satisfy them, they made new emperors.

### Modern Military Juntas

| Country | Year | Pattern |
|---------|------|---------|
| Chile | 1973 | Pinochet's coup against Allende |
| Argentina | 1976 | Videla's junta against Peron |
| Myanmar | 2021 | Min Aung Hlaing against civilian government |
| Egypt | 2013 | Sisi against Morsi |
| Thailand | 2014 | Prayuth against civilian government |

Common pattern: Military/police forces realize they have the actual power and seize it from civilian leadership that can no longer maintain control.

### The Private Prison Industry

In the American context, the enforcers may not stage a traditional coup but rather become the new capitalist class:

- CoreCivic and GEO Group executives
- Prison labor extraction as the new surplus value source
- Lobbying for criminalization (more prisoners = more profit)
- Revolving door between corrections and government

The enforcers don't need a coup - they can simply become the new bourgeoisie through the carceral apparatus itself.

---

## Proposed Implementation

### New Event Types

```python
class EventType(StrEnum):
    # ... existing ...
    ENFORCER_MUTINY = "enforcer_mutiny"      # Enforcers refuse orders
    WARLORD_COUP = "warlord_coup"            # Enforcers seize power
    JUNTA_ESTABLISHED = "junta_established"  # New military ruling class
    ENFORCER_LOYALTY_CRISIS = "enforcer_loyalty_crisis"  # Payment streak broken
```

### New State Variables

```python
@dataclass
class EnforcerLoyalty:
    payment_streak: int          # Consecutive ticks of successful payment
    loyalty_score: float         # 0.0 (mutinous) to 1.0 (loyal)
    class_consciousness: float   # Do enforcers identify with C_b or as separate class?
    pay_ratio: float            # What fraction of expected pay did they receive?
```

### Branching Logic

```python
def check_trajectory_branch(state: WorldState) -> str:
    """Determine which endgame trajectory the simulation takes."""
    c_b = get_entity(state, "C_b")
    enforcers = get_entity(state, "Enforcers")

    # Can C_b still pay enforcers?
    required_pay = enforcers.population * ENFORCER_WAGE_RATE
    can_pay = c_b.wealth >= required_pay

    if can_pay:
        # Trajectory A: Classical Concentration
        # C_b maintains loyalty, accumulates wealth, rules the necropolis
        return "CLASSICAL_CONCENTRATION"
    else:
        # Check enforcer consciousness
        if enforcers.class_consciousness > COUP_THRESHOLD:
            # Trajectory B: Warlord Coup
            # Enforcers realize their power, seize control
            return "WARLORD_COUP"
        else:
            # Enforcers too atomized to organize
            # System collapses into chaos rather than new order
            return "FAILED_STATE"
```

### The Two Stable States

**Trajectory A: Classical Concentration**
```
Before:
C_b (bourgeoisie) → controls via money → Enforcers → control → Prisoners

After:
C_b (bourgeoisie) → maintains payment → Enforcers → control → Prisoners
                 ↑                                              │
                 └──────────── prison labor extraction ─────────┘
```

The bourgeoisie fix the payment issue (perhaps by more extreme extraction from prisoners or external sources) and maintain control. This is the "pure" necropolis.

**Trajectory B: Warlord Coup**
```
Before:
C_b (bourgeoisie) → fails to pay → Enforcers → control → Prisoners

After:
Enforcers (warlords) → control directly → Prisoners
                    ↑                        │
                    └── prison labor ────────┘

C_b → eliminated or subordinated
```

The enforcers realize they have the guns and don't need the bourgeoisie. They establish a military junta that rules the necropolis directly. This is the "warlord era."

---

## Player Agency Implications

In Epoch 2, players can influence which trajectory occurs:

### Accelerating Trajectory B (Warlord Coup)
- Reduce C_b wealth through sabotage
- Disrupt payment channels
- Raise enforcer class consciousness
- Create solidarity between enforcers and prisoners

### Preventing Both Trajectories (Revolution)
- Organize prisoners despite conditions
- Flip enforcers to revolutionary side
- Build solidarity networks that span class lines
- Exploit the transition chaos

The Warsaw Ghetto Dynamic still applies: when P(S|A) → 0, revolution becomes the only rational choice regardless of organization level.

---

## Related ADRs

- **ADR037**: Original discovery, now marked as "deferred to Epoch 2"
- **ADR001**: Embedded Trinity (material base determines outcomes)
- **ADR032**: Materialist Causality (systems run in deterministic order)

## Related Documents

- `ai-docs/carceral-equilibrium.md`: The 70-year trajectory theory
- `ai-docs/terminal-crisis-dynamics.md`: Endgame mechanics
- `ai-docs/epoch1-mvp-complete.md`: MVP milestone documentation

---

## The Mantra Extended

> "Collapse is certain. Revolution is possible. Organization is the difference."

With the Warlord Trajectory, we add:

> "And if revolution fails, even the victors change."

The necropolis may be ruled by capitalists or by warlords. Either way, it remains a necropolis. The only escape is revolutionary organization.
