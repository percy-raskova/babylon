Simulation Systems Reference
============================

API reference for Babylon's twelve core simulation systems.

System Protocol
---------------

All systems implement this protocol:

.. code-block:: python

   class System(Protocol):
       def step(
           self,
           graph: nx.DiGraph[str],
           services: ServiceContainer,
           context: ContextType,  # Union[dict[str, Any], TickContext]
       ) -> None:
           """Mutate graph according to system logic."""
           ...

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``graph``
     - NetworkX DiGraph to mutate (nodes are string IDs)
   * - ``services``
     - Dependency injection container (config, formulas, event_bus, database, defines)
   * - ``context``
     - Mutable dict with ``"tick"`` key and any persistent state

System Execution Order (ADR032)
-------------------------------

Systems execute in strict **materialist causality** order: material base before
superstructure. This ensures physical reality (life, space, production) determines
social responses (consciousness, struggle), not vice versa.

.. list-table::
   :header-rows: 1
   :widths: 5 25 10 60

   * - #
     - System
     - Phase
     - Purpose
   * - 1
     - VitalitySystem
     - Base
     - The Drain + Grinding Attrition + The Reaper
   * - 2
     - TerritorySystem
     - Base
     - Heat dynamics, eviction pipeline, necropolitics
   * - 3
     - ProductionSystem
     - Base
     - Value creation from labor × biocapacity
   * - 4
     - SolidaritySystem
     - Base
     - Transmit consciousness via SOLIDARITY edges
   * - 5
     - ImperialRentSystem
     - Base
     - 5-phase Imperial Circuit with pool tracking
   * - 6
     - DecompositionSystem
     - Crisis
     - LA decomposition during super-wage crisis
   * - 7
     - ControlRatioSystem
     - Crisis
     - Guard:prisoner ratio + terminal decision
   * - 8
     - MetabolismSystem
     - Base
     - Biocapacity depletion + ecological overshoot
   * - 9
     - SurvivalSystem
     - Super
     - Calculate P(S|A) and P(S|R)
   * - 10
     - StruggleSystem
     - Super
     - George Floyd Dynamic (agency layer)
   * - 11
     - ConsciousnessSystem
     - Super
     - Ideological drift + George Jackson bifurcation
   * - 12
     - ContradictionSystem
     - Super
     - Accumulate tension, flag ruptures

**Phase Legend:**

- **Base**: Material base systems (physical reality, production, extraction)
- **Crisis**: Terminal crisis systems (class decomposition, carceral dynamics)
- **Super**: Superstructure systems (consciousness, ideology, struggle)

VitalitySystem
--------------

:py:class:`babylon.engine.systems.vitality.VitalitySystem`

**Purpose:** The Drain, The Attrition, and The Reaper - three-phase mortality check.

This system runs **FIRST** in the materialist causality chain. Life requires material
sustenance. Living costs wealth. No wealth = no life.

Three-Phase Mortality
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Phase
     - Name
     - Logic
   * - 1
     - The Drain
     - Population-scaled subsistence burn: ``cost = (base_subsistence × population) × multiplier``
   * - 2
     - Grinding Attrition
     - Coverage ratio threshold mortality (see formula below)
   * - 3
     - The Reaper
     - Extinction check: ``active = False`` when population reaches zero

**Coverage Ratio Threshold Formula (Phase 2):**

.. math::

   \text{coverage\_ratio} = \frac{W_{pc}}{S}

   \text{threshold} = 1 + I

   \text{deficit} = \max(0, \text{threshold} - \text{coverage\_ratio})

   \text{attrition\_rate} = \text{clamp}(\text{deficit} \times (0.5 + I), 0, 1)

   \text{deaths} = \lfloor \text{population} \times \text{attrition\_rate} \rfloor

Where:

- :math:`W_{pc}` = Wealth per capita (wealth / population)
- :math:`S` = Subsistence needs (s_bio + s_class)
- :math:`I` = Inequality coefficient [0, 1]

**Malthusian Correction:** When deaths occur, population decreases → per-capita wealth
increases → future mortality decreases → equilibrium. Wealth is NOT reduced when people
die (the poor die with 0 wealth).

**Events Emitted:**

- ``POPULATION_ATTRITION``: Coverage deficit deaths from inequality
- ``ENTITY_DEATH``: Full extinction of a demographic block

TerritorySystem
---------------

:py:class:`babylon.engine.systems.territory.TerritorySystem`

**Purpose:** Process territorial heat, eviction, displacement, and necropolitics.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Territory heat, operational profiles, TENANCY edges
   * - **Outputs**
     - Updated heat, displaced classes, detention states

Sub-Phases
~~~~~~~~~~

1. **Heat Dynamics**: HIGH_PROFILE gains heat, LOW_PROFILE decays
2. **Eviction Pipeline**: Triggered when heat ≥ threshold, routes population to sinks
3. **Spillover**: Heat spreads via ADJACENCY edges
4. **Necropolitics**: CONCENTRATION_CAMP elimination, PENAL_COLONY suppression

**Displacement Priority Modes:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Mode
     - Sink Priority Order
   * - EXTRACTION
     - Prison → Reservation → Camp
   * - CONTAINMENT
     - Reservation → Prison → Camp
   * - ELIMINATION
     - Camp → Prison → Reservation

**Operational Profiles:**

- ``HIGH_PROFILE``: Visible activity, generates heat
- ``LOW_PROFILE``: Covert activity, heat decays naturally

ProductionSystem
----------------

:py:class:`babylon.engine.systems.production.ProductionSystem`

**Purpose:** Value creation - The Soil. Workers generate wealth from labor × biocapacity.

Historical Materialist Principle: Value comes from labor applied to nature.
Dead land = no production. Production depletes nature.

**Producer Roles:** ``PERIPHERY_PROLETARIAT``, ``LABOR_ARISTOCRACY``

**Production Formula:**

.. math::

   \text{produced\_value} = (\text{base\_labor\_power} \times \text{population}) \times \frac{B}{B_{max}}

Where:

- :math:`B` = Current biocapacity
- :math:`B_{max}` = Maximum biocapacity

**Extraction Intensity:**

After production, sets ``extraction_intensity`` on each territory for MetabolismSystem:

.. math::

   \text{intensity} = \min(1.0, \frac{\text{total\_production}}{B_{max}})

SolidaritySystem
----------------

:py:class:`babylon.engine.systems.solidarity.SolidaritySystem`

**Purpose:** Transmit class consciousness via SOLIDARITY edges.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - SOLIDARITY edges, consciousness values
   * - **Outputs**
     - Updated consciousness, decayed solidarity strengths

**Key Design:** ``solidarity_strength`` is **PERSISTENT ON EDGE**, not auto-calculated.

**Transmission Formula:**

.. math::

   \Delta\Psi_{target} = \sigma \times (\Psi_{source} - \Psi_{target})

**Activation Condition:**

.. code-block:: text

   source_consciousness > activation_threshold AND solidarity_strength > 0

**Events Emitted:**

- ``CONSCIOUSNESS_TRANSMISSION``: Consciousness delta transmitted
- ``MASS_AWAKENING``: When target crosses ``mass_awakening_threshold``

ImperialRentSystem
------------------

:py:class:`babylon.engine.systems.economic.ImperialRentSystem`

**Purpose:** Implement the 5-phase Imperial Circuit with pool-based resource tracking.

The Imperial Circuit (Sprint 3.4.1, 3.4.4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Imperial Circuit models MLM-TW value extraction as a 5-phase cycle with
finite resources tracked via an ``imperial_rent_pool`` ("The Gas Tank"):

.. mermaid::

   flowchart LR
       subgraph extraction["Value Extraction"]
           P_w["P_w<br/>(Periphery Worker)"]
           P_c["P_c<br/>(Comprador Class)"]
       end

       subgraph core["Core Distribution"]
           C_b["C_b<br/>(Core Bourgeoisie)"]
           C_w["C_w<br/>(Labor Aristocracy)"]
       end

       subgraph pool["Imperial Rent Pool"]
           POOL[("The Gas Tank")]
       end

       P_w -->|"Phase 1: EXPLOITATION"| P_c
       P_c -->|"Phase 2: TRIBUTE"| C_b
       P_c -.->|"FEEDS"| POOL
       C_b -->|"Phase 3: WAGES"| C_w
       C_b -.->|"DRAINS"| POOL
       C_b -->|"Phase 4: CLIENT_STATE<br/>(Iron Lung)"| P_c
       C_b -.->|"DRAINS"| POOL
       POOL -->|"Phase 5: DECISION"| C_b

   %% Necropolis Codex styling
   classDef periphery fill:#4A1818,stroke:#6B4A3A,color:#D4C9B8
   classDef core fill:#6B4A3A,stroke:#8B7B6B,color:#D4C9B8
   classDef pool fill:#1A3A1A,stroke:#2A6B2A,color:#39FF14

   class P_w,P_c periphery
   class C_b,C_w core
   class POOL pool

**Phase Summary:**

.. list-table::
   :header-rows: 1
   :widths: 10 15 30 20 25

   * - Phase
     - Edge Type
     - Description
     - Pool Effect
     - Formula
   * - 1
     - EXPLOITATION
     - Extract imperial rent from periphery workers
     - (direct to C_b feeds pool)
     - :math:`\Phi = \alpha W_p (1 - \Psi_p)`
   * - 2
     - TRIBUTE
     - Comprador sends 85% to core (keeps 15% cut)
     - **FEEDS** pool
     - ``tribute = wealth * (1 - comprador_cut)``
   * - 3
     - WAGES
     - Super-wages to labor aristocracy
     - **DRAINS** pool
     - ``wages = tribute_inflow * wage_rate``
   * - 4
     - CLIENT_STATE
     - Subsidy converts to repression capacity
     - **DRAINS** pool
     - Triggered when :math:`P(S|R) \geq \theta \cdot P(S|A)`
   * - 5
     - (internal)
     - Bourgeoisie decision heuristics
     - Adjusts rates
     - See Decision Matrix below

The PPP Model (Super-Wages)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Super-wages don't manifest as direct cash transfers. Instead, the labor
aristocracy receives nominal wages but enjoys enhanced purchasing power
due to cheap commodities from the periphery. This is **Purchasing Power Parity**:

.. math::

   \text{PPP Multiplier} = 1 + (\alpha \times m_{superwage} \times p_{impact})

.. math::

   \text{Effective Wealth} = W_{nominal} + W_{nominal} \times (\text{PPP Mult} - 1)

.. math::

   \text{Unearned Increment} = \text{Effective Wealth} - W_{nominal}

The "unearned increment" is the material basis of labor aristocracy loyalty -
they receive more than they produce via imperial rent transfer.

The Iron Lung (Client State Subsidy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a client state becomes unstable (:math:`P(S|R) \geq \theta \times P(S|A)`),
the core provides subsidy that **converts to repression capacity**, not wealth.
This models military aid, police training, and suppression infrastructure.

Wealth is NOT conserved - it transforms into suppression capability:

.. code-block:: python

   repression_boost = subsidy_amount * conversion_rate
   target["repression_faced"] = min(1.0, current + repression_boost)

Decision Heuristics (Phase 5)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Based on ``pool_ratio`` and ``aggregate_tension``, the bourgeoisie chooses:

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 20 20

   * - Decision
     - Pool Ratio
     - Tension
     - Wage Delta
     - Repression Delta
   * - **BRIBERY**
     - ≥ 0.7
     - < 0.3
     - +5%
     - 0
   * - **NO_CHANGE**
     - 0.3-0.7
     - any
     - 0
     - 0
   * - **AUSTERITY**
     - < 0.3
     - ≤ 0.5
     - -5%
     - 0
   * - **IRON_FIST**
     - < 0.3
     - > 0.5
     - 0
     - +10%
   * - **CRISIS**
     - < 0.1
     - any
     - -15%
     - +20%

**Events Emitted:**

- ``SURPLUS_EXTRACTION``: On each rent extraction (Phase 1)
- ``IMPERIAL_SUBSIDY``: On client state subsidy (Phase 4)
- ``ECONOMIC_CRISIS``: When CRISIS decision triggers (Phase 5)
- ``SUPERWAGE_CRISIS``: When pool cannot pay super-wages (triggers decomposition)

DecompositionSystem
-------------------

:py:class:`babylon.engine.systems.decomposition.DecompositionSystem`

**Purpose:** Handle Labor Aristocracy decomposition during terminal crisis.

When the imperial rent pool cannot sustain super-wages, the Labor Aristocracy
decomposes into two fractions:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Fraction
     - Default
     - Destination
   * - Enforcer
     - 15%
     - CARCERAL_ENFORCER (guards, cops, prison staff)
   * - Proletariat
     - 85%
     - INTERNAL_PROLETARIAT (precariat, unemployed)

**Trigger:** ``SUPERWAGE_CRISIS`` event + configurable delay (``decomposition_delay``)

**Fallback Trigger:** If LA wealth falls below subsistence, decomposition happens
immediately to prevent the class from dying before the carceral phase can execute.

**Events Emitted:**

- ``CLASS_DECOMPOSITION``: LA splits into enforcer and proletariat fractions

ControlRatioSystem
------------------

:py:class:`babylon.engine.systems.control_ratio.ControlRatioSystem`

**Purpose:** Track guard:prisoner ratio and trigger terminal decision.

When the carceral state cannot control its surplus population, a terminal
decision bifurcation occurs based on prisoner organization levels.

**Prisoner Classes:** ``INTERNAL_PROLETARIAT``, ``LUMPENPROLETARIAT``

**Control Capacity:**

.. math::

   \text{max\_controllable} = \text{enforcer\_population} \times \text{control\_capacity}

Default control capacity: 1:4 (1 guard controls 4 prisoners).
Historical reference: US average ~4:1, Federal baseline 15:1, crisis >20:1.

**Terminal Decision Bifurcation:**

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Condition
     - Outcome
     - Meaning
   * - avg_organization ≥ 0.5
     - **REVOLUTION**
     - Organized prisoners + radicalized guards unite
   * - avg_organization < 0.5
     - **GENOCIDE**
     - Atomized surplus cannot resist elimination

**Events Emitted:**

- ``CONTROL_RATIO_CRISIS``: Prisoners exceed control capacity
- ``TERMINAL_DECISION``: Final outcome (revolution or genocide)

MetabolismSystem
----------------

:py:class:`babylon.engine.systems.metabolism.MetabolismSystem`

**Purpose:** Track the metabolic rift between extraction and regeneration.

The metabolic rift is the core dynamic of imperial accumulation: extraction
systematically exceeds regeneration because profit requires externalizing
regeneration costs.

**Biocapacity Delta Formula:**

.. math::

   \Delta B = R - (E \times \eta)

Where:

- :math:`R` = Regeneration (``regeneration_rate × max_biocapacity``)
- :math:`E` = Extraction (``extraction_intensity × current_biocapacity``)
- :math:`\eta` = Entropy factor (default 1.2, models waste/inefficiency)

**Overshoot Ratio:**

.. math::

   O = \frac{C}{B}

Where :math:`C` = total consumption, :math:`B` = total biocapacity.
When :math:`O > 1.0`, the system is in ecological overshoot.

**Events Emitted:**

- ``ECOLOGICAL_OVERSHOOT``: When overshoot ratio exceeds threshold

SurvivalSystem
--------------

:py:class:`babylon.engine.systems.survival.SurvivalSystem`

**Purpose:** Calculate survival probabilities.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Wealth, organization, repression values
   * - **Outputs**
     - Updated P_acquiescence, P_revolution values

**Per-Capita Normalization (Mass Line Phase 4):**

.. code-block:: python

   wealth_per_capita = wealth / population  # Not aggregate wealth

**Dynamic Organization:**

Organization is amplified by incoming SOLIDARITY edges:

.. code-block:: text

   solidarity_multiplier = 1.0 + sum(strength for incoming SOLIDARITY edges)
   effective_organization = min(1.0, base_organization * solidarity_multiplier)

**Formulas:**

.. math::

   P(S|A) = \frac{1}{1 + e^{-k(W_{pc} - S_{min})}}

.. math::

   P(S|R) = \frac{O_{effective}}{R + \epsilon}

**Rupture condition:** When P(S|R) > P(S|A), revolution is rational.

StruggleSystem
--------------

:py:class:`babylon.engine.systems.struggle.StruggleSystem`

**Purpose:** Implement the George Floyd Dynamic - agency responses to state action.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Repression events, organization levels
   * - **Outputs**
     - Uprising events, changed class states

**Target Roles:** ``PERIPHERY_PROLETARIAT``, ``LUMPENPROLETARIAT``

**The George Floyd Dynamic:**

1. **The Spark:** Police brutality (EXCESSIVE_FORCE) is stochastic function of repression
2. **The Combustion:** Spark becomes UPRISING if population is agitated and hopeless
3. **The Result:** Uprisings destroy wealth, permanently increase solidarity infrastructure

**Events Emitted:**

- ``EXCESSIVE_FORCE``: State violence spark event
- ``UPRISING``: Mass revolt triggered
- ``SOLIDARITY_SPIKE``: Solidarity infrastructure permanently built

**Key insight:** Repression can backfire when directed at organized classes.

ConsciousnessSystem
-------------------

:py:class:`babylon.engine.systems.ideology.ConsciousnessSystem`

**Purpose:** Apply George Jackson bifurcation to ideology.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Agitation levels, SOLIDARITY presence, wage/wealth changes
   * - **Outputs**
     - Updated ideology values (three-dimensional IdeologicalProfile)

**Three-Dimensional IdeologicalProfile:**

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Dimension
     - Range
     - Meaning
   * - class_consciousness
     - [0, 1]
     - Relationship to Capital (0=False, 1=Revolutionary)
   * - national_identity
     - [0, 1]
     - Relationship to State (0=Internationalist, 1=Fascist)
   * - agitation
     - [0, ∞)
     - Raw political energy from crisis

**Ideological Routing Formula:**

.. math::

   E_{agitation} = (|W_{change}| + |X_{change}|) \times \lambda_{loss}

Where :math:`\lambda_{loss} = 2.25` (Kahneman-Tversky loss aversion).

**George Jackson Bifurcation:**

- With solidarity: Agitation routes to class_consciousness (→ revolution)
- Without solidarity: Agitation routes to national_identity (→ fascism)

ContradictionSystem
-------------------

:py:class:`babylon.engine.systems.contradiction.ContradictionSystem`

**Purpose:** Accumulate tension from class contradictions.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Class attributes, wealth gaps
   * - **Outputs**
     - Updated tension values, potential rupture flags

**Tension Accumulation:**

.. code-block:: python

   wealth_gap = abs(target_wealth - source_wealth)
   tension_delta = wealth_gap * tension_accumulation_rate
   new_tension = min(1.0, current_tension + tension_delta)

**Rupture Event:**

Emitted when ``new_tension >= 1.0`` AND ``current_tension < 1.0``
(i.e., the moment tension reaches maximum).

See Also
--------

- :doc:`/concepts/simulation-systems` - Why systems work this way
- :doc:`/how-to/add-custom-system` - Create custom systems
- :doc:`configuration` - System parameters (GameDefines)
- :py:mod:`babylon.engine.systems` - Source code
