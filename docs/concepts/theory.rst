MLM-TW Theoretical Foundation
==============================

Babylon's mechanics are grounded in Marxist-Leninist-Maoist Third Worldist
(MLM-TW) theory. This document explains *why* the simulation works the way
it does, grounding game mechanics in materialist analysis.

Core Thesis
-----------

   **Revolution in the imperial core is structurally impossible while
   imperial rent extraction continues.**

This is a mechanical constraint emerging from material conditions, not a
moral claim or prediction. The simulation models this mathematically through
the :doc:`imperial-rent` and :doc:`survival-calculus`.

The Fundamental Theorem
-----------------------

.. math::

   \text{If } W_c > V_c, \text{ then } P(\text{Revolution in Core}) \to 0

Where:

- :math:`W_c` = Wages paid to core (First World) workers
- :math:`V_c` = Value produced by core workers
- :math:`\Phi = W_c - V_c` = Imperial Rent

When :math:`\Phi > 0`, core workers receive more value than they produce.
The difference comes from exploitation of peripheral (Third World) workers
through unequal exchange.

**Implications:**

1. Core workers have *material interest* in maintaining imperialism
2. This creates the **labor aristocracy**---workers whose class interest
   aligns with capital against the global proletariat
3. Revolutionary potential is concentrated in the periphery, not the core

See :doc:`imperial-rent` for implementation details.

Class Categories
----------------

.. list-table::
   :header-rows: 1

   * - Class
     - Relation to Production
     - Revolutionary Potential
   * - Bourgeoisie
     - Owns means of production
     - Counter-revolutionary
   * - Proletariat
     - Sells labor power
     - High (in periphery)
   * - Petty Bourgeoisie
     - Small owners, professionals
     - Vacillating
   * - Peasantry
     - Agricultural producers
     - Variable by context
   * - Labor Aristocracy
     - Core workers with Φ benefit
     - Low
   * - Lumpenproletariat
     - Outside formal economy
     - Unreliable

The Fascist Bifurcation
-----------------------

Economic crisis does **not** automatically produce revolutionary consciousness.
This is the fundamental error of accelerationism.

When material conditions deteriorate, workers experience **agitation energy**:

.. math::

   \text{Agitation Energy} = |\Delta W| \times \lambda_{\text{loss aversion}}

This energy has no inherent direction. The direction---whether toward class
consciousness or national chauvinism---depends entirely on **pre-existing
solidarity infrastructure**:

.. code-block:: python

   if solidarity_strength > 0:
       direction = class_consciousness  # "The boss is exploiting us"
   else:
       direction = national_identity    # "Foreigners took our jobs"

**The Mantra:**

   *Agitation without solidarity produces fascism, not revolution.*

Historical Examples
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Case
     - Material Conditions
     - Solidarity Infrastructure
     - Outcome
   * - Weimar Germany 1929-1933
     - Economic collapse
     - Weak (divided left)
     - Fascism
   * - Russia 1917
     - War exhaustion, shortages
     - Strong (Zimmerwald movement)
     - Revolution

See ADR016 for implementation details.

Proletarian Internationalism
----------------------------

If imperial rent is the mechanism that pacifies core workers, proletarian
internationalism is the counterforce that can overcome this pacification.

Two competing forces act on core worker consciousness:

.. math::

   \frac{d\Psi}{dt} = \underbrace{k(1 - \frac{W_c}{V_c}) - \lambda\Psi}_{\text{Material (sedative)}}
   + \underbrace{\sigma_{\text{edge}} \times (\Psi_{\text{periphery}} - \Psi_{\text{core}})}_{\text{Solidarity (awakening)}}

**Material force:** When :math:`W_c > V_c`, the material term is negative.
Core workers have no material incentive for revolution.

**Solidarity force:** Consciousness can transmit FROM revolutionary periphery
TO sedated core through SOLIDARITY edges. This requires built infrastructure
(:math:`\sigma_{\text{edge}} > 0`).

**Victory condition for core revolution:**

.. math::

   \sigma_{\text{edge}} \times (\Psi_{\text{periphery}} - \Psi_{\text{core}})
   > |k(1 - \frac{W_c}{V_c}) - \lambda\Psi|

The Tendency of the Rate of Profit to Fall
------------------------------------------

From Marx's *Capital* Volume 3, Chapters 13-15, capitalism contains an
internal economic contradiction: the tendency of the rate of profit to fall.

.. math::

   p' = \frac{s}{c + v}

Where:

- :math:`s` = Surplus Value (extracted from labor beyond wages)
- :math:`c` = Constant Capital (machinery, materials---"dead labor")
- :math:`v` = Variable Capital (wages---"living labor")

The **Organic Composition of Capital** (OCC):

.. math::

   OCC = \frac{c}{v}

As capitalism develops, capitalists invest in machinery to increase
productivity. This raises :math:`c` relative to :math:`v`. Since surplus
value can only be extracted from living labor, the profit *rate* falls
even as absolute profit *mass* may increase.

**Connection to MLM-TW:** Imperial rent (Marx's Factor #5---Foreign Trade)
temporarily offsets TRPF for core capitalists while accelerating it for
peripheral capital. This explains both the stability of core capitalism
AND its ultimate unsustainability.

Epoch 1 models TRPF as time-dependent decay:

.. code-block:: python

   trpf_multiplier = max(0.1, 1.0 - (trpf_coefficient * tick))
   effective_extraction = base_extraction * trpf_multiplier

The Metabolic Rift
------------------

The Metabolic Rift, theorized by Marx and developed by John Bellamy Foster,
describes the fundamental incompatibility between capitalist accumulation
and ecological sustainability.

.. math::

   \Delta B = R - (E \times \eta)

Where:

- :math:`B` = Biocapacity
- :math:`R` = Regeneration rate
- :math:`E` = Extraction rate
- :math:`\eta` = Entropy factor (thermodynamic inefficiency, default 1.2)

Capital externalizes regeneration costs, extracting more than can be renewed.
This gap---the rift---widens with each cycle of accumulation.

The Tragedy of Inevitability
----------------------------

   *"The question is not whether the empire falls. The question is how."*

Babylon operates under a fundamental constraint: **entropy is irreversible**.
The player cannot "win" in the traditional sense. They cannot reverse the
Metabolic Rift or create perpetual imperial accumulation.

Player agency is limited to:

1. **Accelerating collapse** through revolutionary action
2. **Decelerating collapse** through system maintenance (delays inevitable)
3. **Shaping the character of collapse** (revolutionary vs fascist resolution)

The tragedy is not that collapse occurs. The tragedy is that the player
must choose who dies. When biocapacity falls below aggregate consumption,
someone's consumption must be eliminated:

- **Socialist resolution:** Reduce :math:`S_{\text{class}}` (luxury consumption)
- **Fascist resolution:** Eliminate :math:`S_{\text{bio}}` (survival) of
  "surplus populations"

Without solidarity infrastructure, the default is fascism.

Sources
-------

The theoretical framework draws from:

- Marx, *Capital* Volume 1 (value theory, exploitation)
- Marx, *Capital* Volume 3, Chapters 13-15 (TRPF, organic composition)
- Lenin, *Imperialism* (monopoly capital, labor aristocracy)
- Mao, *On Contradiction* (dialectical analysis)
- Gramsci, *Prison Notebooks* (hegemony, civil society)
- Zak Cope, *Divided World Divided Class* (modern labor aristocracy thesis)
- Samir Amin, *Unequal Development* (unequal exchange)

See Also
--------

- :doc:`imperial-rent` - Imperial rent extraction mechanics
- :doc:`survival-calculus` - P(S|A) and P(S|R) formulas
- :doc:`george-jackson-model` - Consciousness bifurcation dynamics
- :doc:`percolation-theory` - Phase transitions in solidarity networks
- :doc:`/reference/formulas` - Complete formula reference
