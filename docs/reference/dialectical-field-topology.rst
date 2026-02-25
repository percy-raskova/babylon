Dialectical Field Topology Reference
======================================

Technical reference for the dialectical field topology systems
implemented in Feature 002. Three systems (positions 16–18 in
``_DEFAULT_SYSTEMS``) compute contradiction fields, spatial/temporal
derivatives, and edge mode transitions on the simulation graph.

.. contents:: On this page
   :local:
   :depth: 2

Field Registry
--------------

The field registry is an extensible container of named contradiction
fields. Core computation logic (gradient, Laplacian, temporal
derivatives, principal contradiction) is field-name-agnostic — new
fields can be registered without modifying computation code.

.. list-table:: Default Contradiction Fields
   :header-rows: 1
   :widths: 20 35 20 25

   * - Field
     - Computation
     - Raw Range
     - Normalization
   * - ``exploitation``
     - ``(subsistence - wealth) / subsistence``
     - [0, 5.0+]
     - Linear ×10, clamp [0, 10]
   * - ``immiseration``
     - ``(prev_wealth - wealth) / prev_wealth``
     - [0, 1.0]
     - Linear ×10, clamp [0, 10]
   * - ``imperial_rent``
     - Direct from ``unearned_increment``
     - [0, ∞]
     - Saturating: ``10(1 - e^{-x/10})``
   * - ``displacement``
     - ``(prev_population - population) / prev_population``
     - [0, 1.0]
     - Linear ×10, clamp [0, 10]

All field values are normalized to [0.0, 10.0] for cross-field
comparability. Normalization preserves relative ordering and
derivative signs.

**Implementation:**
:py:class:`babylon.engine.field_registry.DefaultFieldRegistry`

**Protocol:**
:py:class:`babylon.engine.field_registry.FieldRegistryProtocol`

Spatial Derivatives
-------------------

Gradient (per edge)
~~~~~~~~~~~~~~~~~~~

The gradient along edge (i, j) is the signed difference:

.. math::

   \nabla f(i, j) = f(j) - f(i)

Positive gradient means the field increases from source to target.
Stored in edge attribute ``field_gradients: dict[str, float]``.

Graph Laplacian (per node)
~~~~~~~~~~~~~~~~~~~~~~~~~~

The unweighted graph Laplacian at node *i* is:

.. math::

   \Delta f(i) = \sum_{j \in N(i)} [f(j) - f(i)]

Where *N(i)* is the set of all neighbors (undirected — both
in-edges and out-edges). Stored in node attribute
``field_derivatives[field]["laplacian"]``.

.. list-table:: Laplacian Interpretation
   :header-rows: 1
   :widths: 20 80

   * - Sign
     - Meaning
   * - Negative
     - Pressure peak — node has higher field value than neighbors
   * - Positive
     - Pressure trough — node has lower field value than neighbors
   * - Zero
     - Equilibrium with neighbors, or isolated node (EC-002)

Temporal Derivatives
--------------------

Computed from tick-keyed history using backward finite differences:

.. math::

   \frac{df}{dt}(i, t) = f(i, t) - f(i, t-1)

.. math::

   \frac{d^2f}{dt^2}(i, t) = f(i, t) - 2f(i, t-1) + f(i, t-2)

.. list-table:: History Requirements
   :header-rows: 1
   :widths: 20 25 55

   * - Derivative
     - Min Ticks
     - If Insufficient
   * - df/dt
     - 2
     - Returns ``None`` (not 0.0)
   * - d²f/dt²
     - 3
     - Returns ``None`` (not 0.0)

Stored in node attribute
``field_derivatives[field]["df_dt"]``
and ``field_derivatives[field]["d2f_dt2"]``.

Predicates referencing undefined derivatives evaluate to
``False`` (EC-001).

Principal Contradiction
-----------------------

At each tick, the system identifies the principal contradiction:
the field with the largest maximum absolute first derivative
across all nodes.

**Selection criteria:**

1. Field with ``max(\|df/dt\|)`` across all nodes
2. Tie-break: total magnitude ``Σ\|df/dt\|`` descending
3. Tie-break: ``exploitation`` preferred (structural primacy)

**Output:** Graph-level attribute ``principal_contradiction``:

.. code-block:: python

   {
       "field_name": str | None,
       "max_abs_df_dt": float,
       "changed": bool,
   }

Event ``PRINCIPAL_CONTRADICTION_SHIFT`` is emitted when the
principal field changes between ticks.

Ollivier-Ricci Curvature
------------------------

Discrete curvature computed per edge using optimal transport.
Structural property — recomputed only when topology changes.

.. math::

   \kappa(u, v) = 1 - \frac{W_1(\mu_u, \mu_v)}{d(u, v)}

Where:

- :math:`\mu_u, \mu_v` = probability measures over neighborhoods
- :math:`\alpha` = self-loop weight (default 0.5)
- :math:`1 - \alpha` = uniform distribution over neighbors
- :math:`W_1` = Wasserstein-1 (Earth Mover's) distance
- :math:`d(u,v)` = shortest-path distance

.. list-table:: Curvature Interpretation
   :header-rows: 1
   :widths: 20 80

   * - Sign
     - Meaning
   * - κ > 0
     - Well-connected, clustered (redundant topology)
   * - κ < 0
     - Bottleneck (bridge between sparse regions)
   * - κ ≈ 0
     - Balanced, flat topology

.. list-table:: Validated Topologies
   :header-rows: 1
   :widths: 20 30 50

   * - Graph
     - Expected κ
     - Note
   * - K₄ (complete)
     - Positive
     - High redundancy
   * - P₄ (path)
     - Negative at bridges
     - Bridge edges are bottlenecks
   * - S₄ (star)
     - Known hub value
     - Hub-spoke topology

**Implementation:**
:py:func:`babylon.formulas.curvature.compute_ollivier_ricci`

**Dependencies:** scipy (linear programming), numpy, networkx

Edge Mode Transition State Machine
-----------------------------------

Five Modes
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 18 15 22 22 23

   * - Mode
     - Direction
     - Value Flow
     - Political Content
     - Stability
   * - EXTRACTIVE
     - Unidirectional
     - Exploited → exploiter
     - Produces resistance
     - Unstable
   * - TRANSACTIONAL
     - Symmetric
     - Market exchange
     - Neutral
     - Stable until disrupted
   * - SOLIDARISTIC
     - Mutual
     - Shared reproduction
     - Builds collective power
     - Stable under pressure
   * - ANTAGONISTIC
     - Oppositional
     - Contested/destroyed
     - Open conflict
     - Unstable
   * - CO_OPTIVE
     - Asymmetric
     - Concessions for quiescence
     - Prevents resistance
     - Fragile to crisis

17 Permissible Transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 18 18 30 10

   * - From
     - To
     - Condition (summary)
     - Priority
   * - EXTRACTIVE
     - ANTAGONISTIC
     - Exploitation >5.0 AND rising
     - 10
   * - EXTRACTIVE
     - TRANSACTIONAL
     - Exploitation <2.0
     - 5
   * - EXTRACTIVE
     - CO_OPTIVE
     - Exploitation >3.0, rent >2.0
     - 8
   * - TRANSACTIONAL
     - SOLIDARISTIC
     - Exploitation <2.0 both sides
     - 5
   * - TRANSACTIONAL
     - ANTAGONISTIC
     - Immiseration rising >1.0
     - 10
   * - TRANSACTIONAL
     - EXTRACTIVE
     - Exploitation >5.0
     - 7
   * - TRANSACTIONAL
     - CO_OPTIVE
     - Imperial rent >3.0
     - 6
   * - SOLIDARISTIC
     - TRANSACTIONAL
     - Immiseration >6.0
     - 5
   * - SOLIDARISTIC
     - ANTAGONISTIC
     - Exploitation spike >3.0
     - 10
   * - ANTAGONISTIC
     - TRANSACTIONAL
     - Exploitation falling AND <3.0
     - 5
   * - ANTAGONISTIC
     - SOLIDARISTIC
     - Exploitation >7.0 both sides
     - 8
   * - ANTAGONISTIC
     - CO_OPTIVE
     - Rent >3.0, not rising
     - 6
   * - CO_OPTIVE
     - TRANSACTIONAL
     - Exploitation <2.0, not rising
     - 5
   * - CO_OPTIVE
     - ANTAGONISTIC
     - Exploitation rising >1.0
     - **10**
   * - CO_OPTIVE
     - SOLIDARISTIC
     - Exploitation >5.0 both sides
     - 3
   * - CO_OPTIVE
     - EXTRACTIVE
     - Imperial rent <1.0
     - 7
   * - ANTAGONISTIC
     - ANTAGONISTIC
     - Persistence (no resolution)
     - —

Transitions not listed are **prohibited** — they require passing
through intermediate states.

When multiple transitions are eligible simultaneously, the
highest-priority transition fires (EC-003).

Compound Predicates
~~~~~~~~~~~~~~~~~~~

Each transition is governed by a compound predicate — a conjunction
of threshold conditions:

.. code-block:: python

   PredicateCondition(
       field="exploitation",
       metric="df_dt",        # or "value", "d2f_dt2", "laplacian"
       operator="gt",         # "lt", "gte", "lte"
       threshold=0.0,
       scope="source",        # or "target"
   )

A compound predicate evaluates to ``True`` only when **all**
conditions are satisfied. Conditions referencing undefined
derivatives (insufficient history) evaluate to ``False``.

CO-OPTIVE Mechanics
-------------------

Suppression
~~~~~~~~~~~

Each CO-OPTIVE edge declares which contradiction fields it
suppresses (per-edge configurable via
``co_optive_suppressed_fields``). The suppression applies to
df/dt at the co-opted node:

.. math::

   \text{suppressed} = \frac{df}{dt} \times r_s

Where :math:`r_s` = ``co_optive_suppression_rate`` (default 1.0,
meaning full suppression).

Suppressed df/dt accumulates as **latent contradiction** — tracked
per-source-node per-field in persistent data.

Breakdown and Latent Release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a CO-OPTIVE edge transitions away (typically to ANTAGONISTIC),
the accumulated latent contradiction is released:

.. math::

   \text{released} = \text{latent} \times m_r

Where :math:`m_r` = ``latent_release_multiplier`` (default 1.5).

This produces a **spike** in df/dt that may cause exploitation
to reassert itself as the principal contradiction — the "return
of the repressed" dynamic.

George Jackson Bifurcation
~~~~~~~~~~~~~~~~~~~~~~~~~~

When CO-OPTIVE breakdown produces ANTAGONISTIC edges, the
direction of antagonism is determined by solidarity topology:

- **Upward (revolutionary):** total solidarity strength across
  the colonial divide > within-group solidarity
- **Lateral (fascist):** within-group solidarity > cross-divide
  solidarity

Contradiction Character
~~~~~~~~~~~~~~~~~~~~~~~

Every edge carries a ``contradiction_character`` flag
(``ANTAGONISTIC`` or ``NON_ANTAGONISTIC``), independent of edge
mode. An EXTRACTIVE edge with ANTAGONISTIC character is closer
to rupture than one with NON_ANTAGONISTIC character.

Aspect Reversal
~~~~~~~~~~~~~~~

When the dominant party on a directed edge switches (determined
by wealth comparison), an ``ASPECT_REVERSAL`` event is emitted.
The dominant party is tracked in edge attribute
``_dominant_party``.

Configuration
-------------

.. list-table:: ContradictionFieldDefines
   :header-rows: 1
   :widths: 30 10 10 50

   * - Parameter
     - Default
     - Range
     - Description
   * - ``field_min``
     - 0.0
     - [0, ∞)
     - Minimum normalized field value
   * - ``field_max``
     - 10.0
     - (0, ∞)
     - Maximum normalized field value
   * - ``history_window``
     - 3
     - [2, 10]
     - Rolling tick window for temporal derivatives
   * - ``curvature_alpha``
     - 0.5
     - (0, 1]
     - Self-loop weight for Ricci probability measures
   * - ``co_optive_suppression_rate``
     - 1.0
     - [0, 1]
     - Fraction of df/dt suppressed by CO-OPTIVE edges
   * - ``latent_release_multiplier``
     - 1.5
     - [1, 5]
     - Multiplier on released latent contradictions
   * - ``default_transition_priority``
     - 0
     - [0, ∞)
     - Default priority for transitions

Event Types
-----------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Event Type
     - Description
   * - ``EDGE_MODE_TRANSITION``
     - Edge qualitative mode changed
   * - ``PRINCIPAL_CONTRADICTION_SHIFT``
     - Principal field (max \|df/dt\|) changed
   * - ``CO_OPTIVE_BREAKDOWN``
     - CO-OPTIVE edge failed, latent released
   * - ``LATENT_CONTRADICTION_RELEASE``
     - Suppressed df/dt spike after CO-OPTIVE loss
   * - ``ASPECT_REVERSAL``
     - Dominant party switched on directed edge

System Execution Order
----------------------

.. list-table::
   :header-rows: 1
   :widths: 5 30 65

   * - #
     - System
     - Purpose
   * - 16
     - ContradictionFieldSystem
     - Compute normalized field values at social-class nodes
   * - 17
     - FieldDerivativeSystem
     - Gradients, Laplacian, df/dt, d²f/dt², principal contradiction
   * - 18
     - EdgeTransitionSystem
     - CO-OPTIVE suppression, predicate evaluation, mode transitions

All three systems are no-ops when ``services.field_registry``
is ``None`` (backward compatible).

See Also
--------

- :doc:`/concepts/dialectical-field-theory` — Theoretical exposition
- :doc:`/reference/formulas` — Complete formula reference
- :doc:`/reference/systems` — All simulation systems
- :doc:`/reference/configuration` — GameDefines parameter reference
