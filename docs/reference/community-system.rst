Community System Reference
==========================

API reference for the hypergraph community layer (Feature 022).

The community system maintains an XGI hypergraph alongside the NetworkX
flow graph. Communities are n-ary membership structures (hyperedges);
value/solidarity/repression flows remain NetworkX edges.

.. contents:: On this page
   :local:
   :depth: 2

Enums
-----

CommunityType
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Description
   * - ``new_afrikan``
     - New Afrikan / Black internal nation
   * - ``first_nations``
     - Indigenous / First Nations peoples
   * - ``chicano``
     - Chicano / Mexican-American nation
   * - ``white``
     - White settler nation (hegemonic)
   * - ``queer``
     - Queer / LGBQ sexuality
   * - ``heterosexual``
     - Heterosexual (hegemonic sexuality)
   * - ``trans``
     - Transgender / gender non-conforming
   * - ``cisgender``
     - Cisgender (hegemonic gender identity)
   * - ``disabled``
     - Disabled / disability community
   * - ``abled``
     - Able-bodied (hegemonic ability)
   * - ``undocumented``
     - Undocumented immigration status
   * - ``women``
     - Women (reproductive labor allocation)

Defined in :mod:`babylon.models.enums`.

LegalStatus
~~~~~~~~~~~

One-way escalation ratchet. State action can only escalate; de-escalation
requires player political struggle.

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Value
     - Threat Multiplier
     - Description
   * - ``legal``
     - 0.1
     - Normal status, minimal state attention
   * - ``surveilled``
     - 0.5
     - Active monitoring
   * - ``designated_extremist``
     - 1.0
     - Formal extremist designation
   * - ``designated_terrorist``
     - 2.0
     - Formal terrorist designation
   * - ``criminalized``
     - 3.0
     - Membership itself criminalized

MembershipRole
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Value
     - Strength Weight
     - Description
   * - ``core_organizer``
     - 1.0
     - Infrastructure maintainers, visible leaders
   * - ``active``
     - 0.7
     - Regular participants
   * - ``participant``
     - 0.4
     - Occasional engagement
   * - ``peripheral``
     - 0.2
     - Marginal connection
   * - ``sympathizer``
     - 0.1
     - External ally, not legible as member

Models
------

CommunityState
~~~~~~~~~~~~~~

Frozen Pydantic model. Per-community attributes.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Field
     - Type
     - Default
     - Description
   * - ``community_type``
     - CommunityType
     - *required*
     - Community identity
   * - ``heat``
     - Probability
     - 0.0
     - State attention/surveillance intensity [0, 1]
   * - ``legal_status``
     - LegalStatus
     - LEGAL
     - Current legal designation
   * - ``cohesion``
     - Probability
     - 0.5
     - Internal trust and mutual aid effectiveness [0, 1]
   * - ``infrastructure``
     - Probability
     - 0.3
     - Organizational capacity [0, 1]
   * - ``visibility``
     - Probability
     - 0.5
     - Legibility to state surveillance [0, 1]
   * - ``reproduction_cost_modifier``
     - float
     - 1.0
     - Multiplier on V_reproduction for members (>=0)
   * - ``rent_access_modifier``
     - Coefficient
     - 1.0
     - Multiplier on imperial rent received [0, 1]

Defined in :mod:`babylon.models.entities.community`.

CommunityMembership
~~~~~~~~~~~~~~~~~~~

Frozen Pydantic model. Per-agent-per-community relationship.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Field
     - Type
     - Default
     - Description
   * - ``agent_id``
     - str
     - *required*
     - Agent identifier
   * - ``community_type``
     - CommunityType
     - *required*
     - Which community
   * - ``role``
     - MembershipRole
     - PARTICIPANT
     - Integration level
   * - ``strength``
     - Coefficient
     - 0.4
     - Membership weight [0, 1]
   * - ``visibility``
     - Probability
     - 0.5
     - Base legibility to state [0, 1]
   * - ``overt``
     - bool
     - False
     - Publicly identified (overrides visibility to 1.0)

**Computed property:** ``effective_visibility`` returns 1.0 if ``overt``
is True, otherwise returns the base ``visibility`` value.

Formulas
--------

All formulas registered in :class:`~babylon.engine.formula_registry.FormulaRegistry`.

calculate_solidarity_potential
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   calculate_solidarity_potential(
       base_solidarity: float,
       shared_count: int,
       rent_a: float,
       rent_b: float,
       overlap_bonus: float = 0.1,
       rent_penalty: float = 0.05,
   ) -> float

Returns ``base_solidarity + overlap_bonus * shared_count - rent_penalty * |rent_a - rent_b|``.

calculate_threat_score
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   calculate_threat_score(
       memberships: list[tuple[float, float, float, float]],
   ) -> float

Each tuple is ``(heat, effective_visibility, role_weight, legal_status_multiplier)``.
Returns the sum of all products.

calculate_infrastructure_decay
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   calculate_infrastructure_decay(
       current: float,
       decay_alpha: float,
       core_organizer_count: int,
       maintenance_factor: float = 0.1,
   ) -> float

Returns ``current * (1 - alpha) + min(count * factor, 1.0) * alpha``,
clamped to [0, 1].

calculate_solidarity_amplification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   calculate_solidarity_amplification(
       base_strength: float,
       shared_communities: list[tuple[float, float, float, float]],
   ) -> float

Each tuple is ``(infrastructure, cohesion, strength_a, strength_b)``.
Returns ``base * (1 + sum(infra * cohesion * str_a * str_b))``.

compute_community_cost_modifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_community_cost_modifier(
       memberships: list[Any],
       community_states: dict[Any, Any],
   ) -> float

Returns the product of ``reproduction_cost_modifier`` across all
communities the agent belongs to. Returns 1.0 if no memberships.

CommunitySystem
---------------

Registered at position 6 in ``_DEFAULT_SYSTEMS`` (between
ReserveArmySystem and SolidaritySystem).

**System name:** ``"community"``

Step Phases
~~~~~~~~~~~

The ``step()`` method executes five phases per tick:

1. **Collect memberships** from active ``social_class`` graph nodes
2. **Build XGI hypergraph** from collected memberships
3. **Amplify solidarity** on SOLIDARITY edges via community overlap
4. **Compute threat scores** per agent from community heat and legal status
5. **Compute cost modifiers** per agent from community reproduction modifiers
6. **Apply decay** to community state (heat, cohesion, infrastructure)

Graph Mutations
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Node/Edge
     - Attribute
     - Effect
   * - Agent node
     - ``threat_score``
     - Written each tick (cumulative across memberships)
   * - Agent node
     - ``community_cost_modifier``
     - Written each tick (multiplicative product)
   * - SOLIDARITY edge
     - ``solidarity_strength``
     - Amplified by shared community infrastructure

Repression Actions
~~~~~~~~~~~~~~~~~~

Standalone functions for state AI ``Repress`` verb:

- ``legal_status_escalate(state)`` -- Advances legal status one step. No-op at CRIMINALIZED.
- ``designate_community(state, heat_increase=0.3)`` -- Escalates + raises heat.
- ``infiltrate_community(state, cohesion_reduction=0.2)`` -- Reduces cohesion.
- ``disrupt_infrastructure(state, infrastructure_reduction=0.4)`` -- Reduces infrastructure.

All return new ``CommunityState`` via ``model_copy()``.

Configuration
~~~~~~~~~~~~~

``GameDefines.community`` provides tuning coefficients:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``heat_decay_alpha``
     - 0.05
     - Rate heat decays toward 0 per tick
   * - ``cohesion_decay_alpha``
     - 0.03
     - Rate cohesion decays without organizing
   * - ``infrastructure_decay_alpha``
     - 0.04
     - Rate infrastructure decays without maintenance
   * - ``community_overlap_bonus``
     - 0.1
     - Solidarity potential bonus per shared community
   * - ``rent_differential_penalty``
     - 0.05
     - Solidarity potential penalty per unit rent gap
   * - ``core_organizer_maintenance_factor``
     - 0.1
     - Infrastructure maintenance per CORE_ORGANIZER

Helper Functions
~~~~~~~~~~~~~~~~

- ``build_community_hypergraph(memberships, community_states)`` -- Builds XGI Hypergraph.
- ``shared_communities(H, agent_a, agent_b)`` -- Returns set of shared hyperedge IDs.
- ``community_overlap_matrix(H)`` -- Returns ``(overlap_ndarray, node_index_dict)``.

See Also
--------

- :doc:`/concepts/community-hypergraph` -- Why hyperedges, not pairwise edges
- :doc:`/reference/formulas` -- All simulation formulas
- :doc:`/reference/systems` -- System execution order
