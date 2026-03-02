Community System Reference
==========================

API reference for the hypergraph community layer (Features 022 and 029).

The community system maintains an XGI hypergraph alongside the NetworkX
flow graph. Communities are n-ary membership structures (hyperedges);
value/solidarity/repression flows remain NetworkX edges. Feature 029
adds a three-category taxonomy, contradiction axes, community
consciousness, infiltration resistance, and cross-class bridge detection.

.. contents:: On this page
   :local:
   :depth: 2

Enums
-----

CommunityType
~~~~~~~~~~~~~

14 community types organized into three structural categories.

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Value
     - Category
     - Description
   * - ``settler``
     - CONTRADICTION_PAIR
     - Settler nation (hegemonic). HOAs, police unions, border militias.
   * - ``patriarchal``
     - CONTRADICTION_PAIR
     - Patriarchal order (hegemonic). Gendered wage systems, family structure.
   * - ``new_afrikan``
     - CONTRADICTION_PAIR
     - New Afrikan / Black internal nation (marginalized)
   * - ``first_nations``
     - CONTRADICTION_PAIR
     - Indigenous / First Nations peoples (marginalized)
   * - ``chicano``
     - CONTRADICTION_PAIR
     - Chicano / Mexican-American nation (marginalized)
   * - ``women``
     - CONTRADICTION_PAIR
     - Women — reproductive labor allocation (marginalized)
   * - ``trans``
     - CONTRADICTION_PAIR
     - Transgender / gender non-conforming (marginalized)
   * - ``disabled``
     - INSTITUTIONAL_EXCLUSION
     - Built environment assumes able-bodiedness
   * - ``queer``
     - INSTITUTIONAL_EXCLUSION
     - Institutional heteronormativity
   * - ``undocumented``
     - INSTITUTIONAL_EXCLUSION
     - Legal exclusion from protections
   * - ``incarcerated``
     - INSTITUTIONAL_EXCLUSION
     - Carceral system, civil death
   * - ``youth``
     - LIFECYCLE_PHASE
     - D phase. Pre-productive, dependent, receives socialization.
   * - ``adult``
     - LIFECYCLE_PHASE
     - P phase. Sells labor-power. Where C-M-C and M-C-M' operate.
   * - ``elder``
     - LIFECYCLE_PHASE
     - D' phase. Post-productive. Legitimation bargain.

Defined in :py:class:`~babylon.models.enums.CommunityType`.

HyperedgeCategory
~~~~~~~~~~~~~~~~~

Structural category for community hyperedges (Feature 029).

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Value
     - Description
   * - ``contradiction_pair``
     - Both hegemonic and marginalized sides exist as real hyperedges
       with extraction flows between them.
   * - ``institutional_exclusion``
     - Only the marginalized side exists. Oppression flows through
       institutional defaults, not a paired oppressor community.
   * - ``lifecycle_phase``
     - Universal temporal positions in D-P-D' intergenerational
       lifecycle. Defined by relationship to production.

Defined in :py:class:`~babylon.models.enums.HyperedgeCategory`.

ConsciousnessTendency
~~~~~~~~~~~~~~~~~~~~~

Dominant ideological tendency within a community (Feature 029).

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Description
   * - ``liberal``
     - Seeks inclusion in existing institutions without transforming them.
       Organizational vehicle: liberal CSOs, Democratic Party.
   * - ``fascist``
     - Collaboration with hegemonic order for individual escape. Strategy:
       shrink the marginalized definition, exclude the most marginal.
   * - ``revolutionary``
     - Oppositional collective identity, independent power. The
       contradiction is material, not a misunderstanding.

Defined in :py:class:`~babylon.models.enums.ConsciousnessTendency`.

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

CommunityConsciousness (TernaryConsciousness)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CommunityConsciousness`` is a type alias for
:class:`~babylon.models.entities.consciousness.TernaryConsciousness`
(Feature 034). The consciousness model is a 2-simplex where
``r + l + f = 1.0``.

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Field
     - Type
     - Default
     - Description
   * - ``r``
     - Probability
     - 0.3
     - Revolutionary consciousness [0, 1]
   * - ``l``
     - Probability
     - 0.6
     - Liberal consciousness [0, 1]
   * - ``f``
     - Probability
     - 0.1
     - Fascist consciousness [0, 1]
   * - ``contestation_stored``
     - float | None
     - None
     - Legacy contestation value (None = use Shannon entropy)

**Computed properties** (backward-compatible with the old scalar model):

- ``collective_identity`` — equals ``r``
- ``dominant_tendency`` — argmax of ``(r, l, f)`` (ties favor liberal)
- ``ideological_contestation`` — ``contestation_stored`` if set,
  otherwise normalized Shannon entropy of ``(r, l, f)``
- ``assimilation_ratio`` — ``f / (l + f)``

Supports three construction paths: native ``(r, l, f)``, legacy
``(collective_identity, dominant_tendency, ideological_contestation)``,
and default. See :doc:`/reference/ternary-consciousness` for full details.

Defined in :py:mod:`babylon.models.entities.consciousness` (primary),
aliased in :py:mod:`babylon.models.entities.community`.

ContradictionAxis
~~~~~~~~~~~~~~~~~

Frozen Pydantic model. Structural axis of contradiction with hegemonic
and marginalized sides (Feature 029).

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``id``
     - str
     - Short identifier (``"colonial"``, ``"patriarchal"``)
   * - ``name``
     - str
     - Human-readable axis name
   * - ``hegemonic``
     - CommunityType
     - The hegemonic community type on this axis
   * - ``marginalized``
     - list[CommunityType]
     - Marginalized community types on this axis
   * - ``extraction_mechanism``
     - str
     - Description of the material extraction
   * - ``exclusive``
     - bool
     - Whether membership is mutually exclusive
   * - ``permeable``
     - bool
     - Whether agents can cross the axis boundary

Defined in :py:class:`~babylon.models.entities.community.ContradictionAxis`.

CommunityState
~~~~~~~~~~~~~~

Frozen Pydantic model. Per-community attributes including Feature 029
additions (``category``, ``consciousness``, computed properties).

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
   * - ``category``
     - HyperedgeCategory
     - *auto-assigned*
     - Structural category from ``COMMUNITY_CATEGORY_MAP``
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
   * - ``consciousness``
     - CommunityConsciousness
     - *(default factory)*
     - Ideological dimension of the community

**Computed properties:**

- ``infiltration_resistance`` — Community resistance to state infiltration.
  See :ref:`infiltration-resistance-formula`.
- ``is_cross_class_bridge`` — ``True`` if ``category`` is
  ``INSTITUTIONAL_EXCLUSION``, indicating structural potential for
  bridging contradiction axes.

The ``category`` field is auto-assigned via a model validator that reads
``COMMUNITY_CATEGORY_MAP[community_type]``.

Defined in :py:class:`~babylon.models.entities.community.CommunityState`.

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

Constants
---------

Category and Side Mappings
~~~~~~~~~~~~~~~~~~~~~~~~~~

**COMMUNITY_CATEGORY_MAP** — Maps every ``CommunityType`` to exactly one
``HyperedgeCategory``. Fixed at import time. Exhaustively validated —
missing types raise ``RuntimeError``.

**HEGEMONIC_COMMUNITIES** — ``frozenset({SETTLER, PATRIARCHAL})``

**MARGINALIZED_COMMUNITIES** — ``frozenset({NEW_AFRIKAN, FIRST_NATIONS,
CHICANO, WOMEN, TRANS, DISABLED, QUEER, UNDOCUMENTED, INCARCERATED})``

**LIFECYCLE_COMMUNITIES** — ``frozenset({YOUTH, ADULT, ELDER})``

Contradiction Axes
~~~~~~~~~~~~~~~~~~

**COLONIAL_AXIS** — Hegemonic: SETTLER. Marginalized: NEW_AFRIKAN,
FIRST_NATIONS, CHICANO. Extraction: land, imperial rent, carceral labor,
property value regimes. Exclusive, not permeable.

**PATRIARCHAL_AXIS** — Hegemonic: PATRIARCHAL. Marginalized: WOMEN,
TRANS. Extraction: unwaged reproductive labor, wage gap, care
externalization. Exclusive, not permeable.

**CONTRADICTION_AXES** — ``[COLONIAL_AXIS, PATRIARCHAL_AXIS]``

Default Consciousness Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**CONSCIOUSNESS_DEFAULTS** — Starting ternary ``(r, l, f)`` values for
all 14 community types. Synthetic data for Detroit 2010 test case.
Contestation is now derived as Shannon entropy of the distribution.

See :ref:`consciousness-defaults-table` in the
:doc:`/reference/ternary-consciousness` for the complete table with all
14 rows.

Infiltration Constants
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Constant
     - Value
     - Purpose
   * - ``INFILTRATION_CI_WEIGHT``
     - 0.6
     - Weight of collective identity in resistance formula
   * - ``INFILTRATION_COHESION_WEIGHT``
     - 0.3
     - Weight of cohesion in resistance formula
   * - ``INFILTRATION_INTERACTION_WEIGHT``
     - 0.1
     - Weight of CI * cohesion interaction term
   * - ``INFILTRATION_CEILING_FACTOR``
     - 0.7
     - How much max resistance reduces infiltration ceiling

All constants defined in :py:mod:`babylon.models.entities.community`.

.. _infiltration-resistance-formula:

Infiltration Resistance
-----------------------

Community resistance to state infiltration, computed from collective
identity and internal cohesion.

**Resistance formula:**

.. math::

   IR = CI \times 0.6 + \text{cohesion} \times 0.3 + CI \times \text{cohesion} \times 0.1

The interaction term means collective identity and cohesion reinforce
each other. Maximum resistance is 1.0 (when CI = 1.0 and cohesion = 1.0).

**Effective ceiling reduction:**

.. math::

   \text{ceiling}_{\text{eff}} = \text{ceiling}_{\text{base}} \times (1 - IR_{\max} \times 0.7)

Where :math:`IR_{\max}` is the highest infiltration resistance across all
communities the target belongs to. At maximum resistance, the effective
ceiling drops to 30% of base.

Implemented as computed property ``CommunityState.infiltration_resistance``
and standalone function ``effective_infiltration_ceiling()``.

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

**Feature 022 helpers** (from :py:mod:`babylon.engine.systems.community`):

- ``build_community_hypergraph(memberships, community_states)`` -- Builds XGI Hypergraph.
- ``shared_communities(H, agent_a, agent_b)`` -- Returns set of shared hyperedge IDs.
- ``community_overlap_matrix(H)`` -- Returns ``(overlap_ndarray, node_index_dict)``.

**Feature 029 helpers** (from :py:mod:`babylon.models.entities.community`):

- ``get_contradiction_axis(community)`` -- Returns the ``ContradictionAxis`` a
  community belongs to, or ``None`` if not a contradiction pair.
- ``is_hegemonic(community)`` -- ``True`` if on the hegemonic side of any axis.
- ``is_marginalized(community)`` -- ``True`` if marginalized (including
  institutional exclusion).
- ``get_opposing_communities(community)`` -- Returns communities on the
  opposite side of the contradiction axis. Empty list if not a pair.
- ``shared_marginalized_communities(agent_a_communities, agent_b_communities)``
  -- Returns marginalized communities shared by two agents.
- ``effective_infiltration_ceiling(base_ceiling, target_community_states)``
  -- Computes effective ceiling reduced by community resistance.

**Feature 029 helpers** (from :py:mod:`babylon.engine.systems.community`):

- ``communities_spanning_axis(H, axis)`` -- Finds institutional exclusion
  communities that bridge a contradiction axis by containing members from
  both hegemonic and marginalized sides.

See Also
--------

- :doc:`/concepts/consciousness-taxonomy` -- Taxonomy theory and consciousness model
- :doc:`/concepts/ternary-consciousness` -- Why consciousness is modeled as a ternary simplex
- :doc:`/reference/ternary-consciousness` -- Ternary consciousness API reference
- :doc:`/concepts/community-hypergraph` -- Why hyperedges, not pairwise edges
- :doc:`/concepts/george-jackson-model` -- Bifurcation and consciousness tendencies
- :doc:`/reference/formulas` -- All simulation formulas
- :doc:`/reference/systems` -- System execution order
