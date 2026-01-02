The Warlord Trajectory
======================

   *"When the money runs out, the man with the gun becomes the boss."*

Discovery Context
-----------------

During Epoch 1 MVP validation, running 100-year Carceral Equilibrium
simulations revealed unexpected wealth dynamics:

.. code-block:: text

   Year 0:   C_b wealth = 1.10    LA wealth = 9.62
   Year 100: C_b wealth = 0.01    LA wealth = 15,954.87

The bourgeoisie wealth collapsed to near-zero while Labor Aristocracy
accumulated massively. Initially flagged as a critical bug, this
actually represents a historically valid trajectory: **the Warlord Coup**.

The Key Insight
---------------

The bourgeoisie do not personally control the means of violence. They
control them **by proxy through money**::

    C_b (bourgeoisie)
        ├──[PAYMENT]──► Enforcers ──[CONTROL]──► Means of Violence
        │                                            ├── Tanks
        │                                            ├── Helicopters
        │                                            ├── Drones
        │                                            ├── Machine guns
        │                                            └── Prisons
        └──[PROFIT]──► C_b accumulates wealth

When payment stops, **enforcers still have the weapons**. The chain of
command depends on continued payment. When bourgeoisie cannot pay,
enforcers can seize power themselves.

Two Valid Interpretations
-------------------------

Interpretation A: Bug (Classical Political Economy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Capital should concentrate upward during crisis
- The bourgeoisie should thrive while workers suffer
- This is how capitalism has historically functioned
- **Fix required:** Add EXPLOITATION edge from LA to C_b

Interpretation B: Feature (Warlord Trajectory)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- When bourgeoisie can't pay enforcers, coup becomes possible
- Enforcers control the actual means of violence
- Historically accurate for failed states and military juntas
- **Keep dynamics:** Model enforcer class consciousness and loyalty

**Resolution:** Both trajectories are valid. Epoch 2 implements branching
based on material conditions.

Historical Parallels
--------------------

The Praetorian Guard Problem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Roman Praetorian Guard was the personal bodyguard of the Emperor.
Over time, they realized their power:

- 41 CE: Assassinated Caligula, installed Claudius
- 193 CE: Auctioned the empire to the highest bidder
- 235-284 CE: Crisis of the Third Century (50 years, 26 emperors)

When emperors couldn't pay or satisfy them, they made new emperors.

Modern Military Juntas
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Country
     - Year
     - Pattern
   * - Chile
     - 1973
     - Pinochet's coup against Allende
   * - Argentina
     - 1976
     - Videla's junta against Peron
   * - Myanmar
     - 2021
     - Min Aung Hlaing against civilian government
   * - Egypt
     - 2013
     - Sisi against Morsi

Common pattern: Military/police forces realize they have the actual power
and seize it when civilian leadership can no longer maintain control.

The Private Prison Industry
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the American context, the enforcers may not stage a traditional coup
but rather **become the new capitalist class**:

- CoreCivic and GEO Group executives
- Prison labor extraction as new surplus value source
- Lobbying for criminalization (more prisoners = more profit)
- Revolving door between corrections and government

The enforcers don't need a coup—they become the new bourgeoisie through
the carceral apparatus itself.

Epoch 2 Branching Design
------------------------

Trajectory A: Classical Concentration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    C_b (bourgeoisie) → maintains payment → Enforcers → control → Prisoners
                     ↑                                              │
                     └──────────── prison labor extraction ─────────┘

The bourgeoisie fix payment (through extreme extraction) and maintain
control. This is the "pure" necropolis ruled by capitalists.

Trajectory B: Warlord Coup
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    Enforcers (warlords) → control directly → Prisoners
                        ↑                        │
                        └── prison labor ────────┘

    C_b → eliminated or subordinated

The enforcers establish a military junta that rules the necropolis directly.
This is the "warlord era."

Branching Condition
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   enforcer_loyalty = f(C_b_wealth, payment_consistency, enforcer_consciousness)

   if can_pay:
       return TRAJECTORY_A  # Classical Concentration
   elif enforcer_consciousness > COUP_THRESHOLD:
       return TRAJECTORY_B  # Warlord Coup
   else:
       return FAILED_STATE  # System collapses into chaos

Player Agency Implications
--------------------------

**Accelerating Warlord Coup:**

- Reduce C_b wealth through sabotage
- Disrupt payment channels
- Raise enforcer class consciousness

**Preventing Both Trajectories (Revolution):**

- Organize prisoners despite conditions
- Flip enforcers to revolutionary side
- Build solidarity networks spanning class lines
- Exploit transition chaos

The Warsaw Ghetto Dynamic still applies: when P(S|A) → 0, revolution
becomes the only rational choice.

The Mantra Extended
-------------------

   *"Collapse is certain. Revolution is possible. Organization is the
   difference."*

With the Warlord Trajectory, we add:

   *"And if revolution fails, even the victors change."*

The necropolis may be ruled by capitalists or by warlords. Either way,
it remains a necropolis. **The only escape is revolutionary organization.**

Status
------

- **Discovered:** 2026-01-01 (Session #139)
- **Status:** Deferred to Epoch 2
- **Priority:** Before player agency systems

See Also
--------

- :doc:`carceral-equilibrium` - The 70-year trajectory theory
- :doc:`terminal-crisis` - Endgame mechanics
- :doc:`theory` - MLM-TW theoretical foundation
