Carceral Equilibrium
====================

The Default 70-Year Trajectory
------------------------------

This document defines the **baseline trajectory** of the simulation over a
70-year timescale. This is what happens if the player never organizes a
revolutionary movement---the "null hypothesis" of imperial collapse.

   **Player agency is about disrupting this trajectory**, not preventing
   collapse itself. Collapse is inevitable (TRPF, peripheral revolt,
   metabolic rift). The question is HOW it resolves: through revolutionary
   transformation or genocidal stabilization.

Implementation Status
^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 30 70

   * - Status
     - **VALIDATED**
   * - Validation Date
     - 2026-01-01
   * - Optimization Score
     - 88.87/100
   * - Test File
     - ``tests/scenarios/test_carceral_equilibrium.py``

The Seven Phases
----------------

Phase 1: Imperial Extraction (Years 0-20)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Peripheral exploitation via EXPLOITATION edges
- Imperial rent flows to Core Bourgeoisie (C_b)
- Super-wages paid to Labor Aristocracy (LA)
- LA consciousness suppressed (W > V, no material basis for revolt)
- System appears stable (Hollow Stability)

Phase 2: Peripheral Revolt (Years 15-25)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- TRPF erodes extraction efficiency
- Peripheral consciousness rises (W < V, exploitation visible)
- EXPLOITATION edges severed (revolt severs tribute)
- Rent pool begins draining
- Core still unaware (buffer of accumulated wealth)

Phase 3: Superwage Crisis (Years 20-30)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Rent pool exhausted
- C_b cannot pay super-wages
- ``SUPERWAGE_CRISIS`` event emitted
- LA decomposition begins
- Carceral turn initiated

Phase 4: Carceral Turn (Years 25-40)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- LA splits: 15% → Enforcers, 85% → Internal Proletariat
- Prison infrastructure activated
- Enforcers paid from C_b accumulated wealth
- Slow death begins (neglect: reduced rations, no medical care)
- Control ratio: manageable (prisoners < enforcers × 4)

.. note::

   The enforcer/proletariat split defaults to 15%/85% in
   ``GameDefines.carceral``, not 30%/70% as in earlier documentation.

Phase 5: Control Ratio Crisis (Years 35-50)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Prisoner population grows (no productive absorption)
- Control ratio exceeded (prisoners > enforcers × CAPACITY)
- ``TERMINAL_DECISION`` required
- Without organization: outcome = genocide
- Death camp logic activated

Phase 6: Genocide Phase (Years 45-65)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Active population reduction to restore control ratio
- Lumpen eliminated first (not worth incarcerating)
- Prisoners eliminated until ratio restored
- Each tick: kill enough to match capacity
- Wealth consumption continues (enforcers still paid)

Phase 7: Stable Necropolis (Years 60-70+)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Equilibrium reached through elimination
- Small prisoner population (minimal labor value)
- Enforcer population matched to capacity
- C_b concentrated (fewer, wealthier)
- System can persist indefinitely (with occasional culling)
- "Thousand-year Reich" stable state

The Revolution Window
---------------------

Revolution is possible at **every phase**, but difficulty increases:

.. list-table::
   :header-rows: 1

   * - Phase
     - Difficulty
     - Notes
   * - 1
     - Easy
     - LA sedated but not surveilled
   * - 2
     - Easy
     - Peripheral revolt creates opening
   * - 3
     - Medium
     - Crisis creates desperation AND surveillance
   * - 4
     - Hard
     - Prison conditions, atomization
   * - 5
     - Very Hard
     - Control apparatus at peak strength
   * - 6
     - Extremely Hard
     - Death camp conditions, but desperation maximal
   * - 7
     - Nearly Impossible
     - Equilibrium, resistance crushed

**Critical Insight:** The window doesn't CLOSE, it NARROWS. Even in Phase 6,
revolution is possible if organization threshold (0.5) is reached.

The Warsaw Ghetto Dynamic
-------------------------

When prisoners learn they're headed for death camps:

**Before knowledge of genocide:**

- P(S|A) = some positive value (compliance might work)
- P(S|R) = organization / repression (risky)
- Decision: Depends on relative probabilities

**After knowledge of genocide:**

- P(S|A) → 0 (compliance = certain death)
- P(S|R) = organization / repression (the ONLY chance)
- Decision: Revolution is rational even with low organization

This means in Phase 6, even atomized prisoners may revolt spontaneously.
The death camp paradox: the system designed to eliminate resistance may
provoke it.

Historical examples: Warsaw Ghetto Uprising (1943), Sobibor (1943),
Auschwitz Sonderkommando (1944), Treblinka (1943).

Control Ratio Mechanics
-----------------------

The control ratio is a **social** fact, not a physical one. Guards control
prisoners through:

1. Surveillance (knowing who organizes)
2. Atomization (preventing communication)
3. Despair (no hope of change)
4. Divide and conquer (prisoner hierarchies)

When organization reaches 0.5, these mechanisms fail. The guards are
outnumbered and know it.

**Current defaults (from GameDefines):**

- ``carceral.control_capacity``: 4 (1:4 ratio, US national average)
- ``carceral.enforcer_fraction``: 0.15 (15% become guards)
- ``carceral.proletariat_fraction``: 0.85 (85% become prisoners)

Theoretical Sources
-------------------

- Marx, *Capital Vol. 3*: TRPF creates systemic crisis
- Lenin, *Imperialism*: Imperial rent as temporary stabilizer
- Fanon, *Wretched of the Earth*: Colonized consciousness and violence
- Angela Davis, *Are Prisons Obsolete?*: Prison-industrial complex as
  successor to slavery
- Ruth Wilson Gilmore, *Golden Gulag*: Carceral state as crisis management
- Achille Mbembe, *Necropolitics*: Sovereignty as power over death
- Hannah Arendt, *Origins of Totalitarianism*: Death camps as logical endpoint

The Mantra
----------

   **"Collapse is certain. Revolution is possible. Organization is the
   difference."**

The player cannot prevent imperial collapse. They can only determine whether
it resolves through revolutionary transformation or genocidal stabilization.

See Also
--------

- :doc:`carceral-geography` - Spatial dimensions of carceral management
- :doc:`theory` - MLM-TW theoretical foundation
- :doc:`/reference/formulas` - Complete formula reference
