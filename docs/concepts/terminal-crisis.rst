Terminal Crisis Dynamics
========================

From Plantation to Death Camp
-----------------------------

This document captures the complete arc of imperial system collapse, from
peripheral extraction through internal colonization to the terminal decision
point between revolution and genocide.

The Imperial Circuit at Height
------------------------------

During stable imperial extraction::

    Periphery (1 billion)
        ↓ [EXPLOITATION]
    Comprador
        ↓ [TRIBUTE]
    Core Bourgeoisie (10 million)
        ↓ [SUPER-WAGES]
    Labor Aristocracy (100 million)

**Key ratios:**

- Exploited : Bribed : Owners ≈ 100 : 10 : 1
- Extraction exceeds super-wage costs → C_b accumulates
- LA is bribed into complicity → social peace in core
- Periphery is geographically distant → exploitation invisible

The Four Phases
---------------

Phase 1: Peripheral Revolt
^^^^^^^^^^^^^^^^^^^^^^^^^^

When peripheral extraction becomes untenable:

**Triggers:**

- Ecological collapse (metabolic rift exhausts biocapacity)
- Peripheral organization (P(S|R) exceeds P(S|A))
- Anti-colonial revolution severs extraction edges

**Effects:**

- Imperial rent stops flowing
- C_b loses tribute inflow
- Super-wage budget depletes
- LA begins proletarianization

Phase 2: The Carceral Turn
^^^^^^^^^^^^^^^^^^^^^^^^^^

C_b attempts internal colonization to replace lost peripheral extraction.
The Labor Aristocracy splits:

- **Carceral Enforcers** (15%): Guards, cops, jailers
- **Internal Proletariat** (85%): Lumpen, precariat

Same function (bribed buffer class), different labor:
*coercion replaces creation*.

Phase 3: The Arithmetic Failure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**The fundamental contradiction:** Internal colonization cannot scale.

.. list-table::
   :header-rows: 1

   * - Model
     - Ratio
     - Why
   * - Imperial
     - 1 guard : 100 periphery workers
     - Distance + military power
   * - Carceral
     - 1 guard : 10 prisoners
     - Proximity + constant surveillance

When ``prisoners > guards × control_capacity``:

- Prison revolts become inevitable
- Cost of repression exceeds value of extraction
- System hemorrhages resources maintaining order

Phase 4: The Terminal Decision
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The system faces a bifurcation::

                        ┌─────────────────────────────────┐
                        │   Cost of Repression > Value    │
                        │   Control Ratio Inverted        │
                        └───────────────┬─────────────────┘
                                        │
                ┌───────────────────────┴───────────────────────┐
                │                                               │
                ▼                                               ▼
        ┌───────────────┐                               ┌───────────────┐
        │  REVOLUTION   │                               │   GENOCIDE    │
        │               │                               │               │
        │ Prisoners +   │                               │ Eliminate     │
        │ Guards unite  │                               │ surplus       │
        │ against C_b   │                               │ population    │
        └───────────────┘                               └───────────────┘

The Institutional Progression
-----------------------------

Each stage represents a shift in the relationship between extraction and
elimination:

.. list-table::
   :header-rows: 1

   * - Institution
     - Function
     - Value Extracted
     - Violence Level
   * - Plantation
     - Extract labor
     - High
     - Targeted
   * - Prison
     - Extract labor + warehouse
     - Medium
     - Systematic
   * - Concentration Camp
     - Pure warehousing
     - Zero
     - Mass
   * - Death Camp
     - Elimination
     - Negative (saves costs)
     - Genocidal

**The logic:**

- **Plantation:** Surplus population is an asset (labor power)
- **Prison:** Surplus population is break-even (some labor, high costs)
- **Concentration Camp:** Surplus population is a liability (pure cost)
- **Death Camp:** Surplus population is eliminated (liability removed)

The Genocidal "Rationality"
---------------------------

When the system calculates:

.. code-block:: python

   cost_of_warehousing = prisoners * (food + shelter + guards + infrastructure)
   value_of_labor = prisoners * (productivity * extraction_rate)
   risk_of_revolt = prisoners / (guards * control_capacity)

   if cost_of_warehousing > value_of_labor:
       if risk_of_revolt > acceptable_threshold:
           # "Rational" conclusion: eliminate surplus population
           decision = GENOCIDE

This is the horrific logic of fascism: when exploitation becomes unprofitable
and repression becomes unsustainable, elimination becomes the "solution."

Historical Parallels
--------------------

**Nazi Germany:**

1. Lost colonies (WWI) → imperial extraction ended
2. Economic crisis → LA proletarianization
3. Internal colonization → target Jews, Roma, disabled, communists
4. Concentration camps → warehousing + some labor extraction
5. Death camps → "Final Solution" when warehousing costs exceeded value

**American Trajectory:**

1. Deindustrialization → LA begins shrinking
2. War on Drugs → mass incarceration begins
3. Prison-industrial complex → extraction from prison labor
4. Private prisons → cost optimization pressure
5. Conditions worsen → approaching concentration camp logic

Implementation
--------------

The terminal crisis is implemented across multiple systems:

- :py:mod:`babylon.engine.systems.decomposition` - LA decomposition
- :py:mod:`babylon.engine.systems.control_ratio` - Control ratio tracking

Key parameters in ``GameDefines.carceral``:

- ``control_capacity``: 4 (1:4 ratio, US average)
- ``enforcer_fraction``: 0.15
- ``proletariat_fraction``: 0.85
- ``revolution_threshold``: 0.5

Theoretical Sources
-------------------

- Marx: Reserve army of labor, primitive accumulation, TRPF
- Lenin: Imperialism as highest stage, labor aristocracy theory
- Fanon: Colonial violence, the wretched of the earth
- Angela Davis: Prison-industrial complex, abolition democracy
- Ruth Wilson Gilmore: Golden gulag, organized abandonment
- Cedric Robinson: Racial capitalism, Black Marxism

The synthesis: **When imperial extraction fails, capital turns genocidal
rather than accept revolution.**

See Also
--------

- :doc:`carceral-equilibrium` - The 70-year default trajectory
- :doc:`carceral-geography` - Spatial dimensions of carceral management
- :doc:`theory` - MLM-TW theoretical foundation
