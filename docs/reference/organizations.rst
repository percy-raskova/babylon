Organization Reference
======================

Technical reference for the Organization Base Model (Feature 031).
Covers entity models, discriminated union dispatch, composition calculators,
consciousness effect formula, topology classification, key figure analysis,
and legacy migration.

**Import:**

.. code-block:: python

   from babylon.models.entities.organization import (
       Organization,
       StateApparatus,
       Business,
       PoliticalFaction,
       CivilSocietyOrg,
       OrganizationType,
       IntelMethodology,
       KeyFigure,
   )

.. contents:: On this page
   :local:
   :depth: 2


Entity Models
-------------

Organization (Base)
~~~~~~~~~~~~~~~~~~~

All four subtypes inherit these 15 fields. Frozen (immutable).

.. list-table::
   :header-rows: 1
   :widths: 25 20 10 45

   * - Field
     - Type
     - Default
     - Description
   * - ``id``
     - ``str``
     -
     - Unique organization identifier (min length 1).
   * - ``name``
     - ``str``
     -
     - Human-readable name (min length 1).
   * - ``org_type``
     - ``OrgType``
     -
     - Discriminator for subtype dispatch.
   * - ``class_character``
     - ``ClassCharacter``
     -
     - Which class this org serves (BOURGEOIS, PROLETARIAN, CONTESTED).
   * - ``cohesion``
     - ``Probability``
     - 0.1
     - Internal unity [0=atomized, 1=unified].
   * - ``cadre_level``
     - ``Probability``
     - 0.0
     - Leadership quality [0=none, 1=elite].
   * - ``budget``
     - ``Currency``
     - 0.0
     - Available resources.
   * - ``legal_standing``
     - ``LegalStanding``
     - REGISTERED
     - Legal status (SOVEREIGN, CHARTERED, REGISTERED, INFORMAL, UNDERGROUND).
   * - ``consciousness_tendency``
     - ``ConsciousnessTendency``
     - LIBERAL
     - Ideological tendency pushed on communities.
   * - ``territory_ids``
     - ``list[str]``
     - ``[]``
     - Territories where org operates.
   * - ``headquarters_id``
     - ``str | None``
     - ``None``
     - Primary location. Must be in ``territory_ids`` if set.
   * - ``heat``
     - ``Probability``
     - 0.0
     - State attention level [0=invisible, 1=targeted].
   * - ``is_institution``
     - ``bool``
     - ``False``
     - **Deprecated** (Feature 040). Use ``Institution`` entity instead.
       Emits ``DeprecationWarning`` when set to ``True``.
   * - ``institutional_persistence``
     - ``float | None``
     - ``None``
     - **Deprecated** (Feature 040). Use ``Institution.formalization_level``
       and ``Institution.institutional_inertia``. Emits ``DeprecationWarning``
       when set to a non-None value.
   * - ``member_node_ids``
     - ``list[str]``
     - ``[]``
     - Key figure and cadre node IDs.

**Validators:**

- ``headquarters_id`` must be in ``territory_ids`` if set.
- ``institutional_persistence`` must be ``None`` when ``is_institution`` is ``False``.


StateApparatus
~~~~~~~~~~~~~~

Wields state violence and surveillance. Default ``legal_standing`` is ``SOVEREIGN``.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Field
     - Type
     - Default
     - Description
   * - ``org_type``
     - ``Literal[STATE_APPARATUS]``
     -
     - Fixed discriminator.
   * - ``legal_standing``
     - ``LegalStanding``
     - SOVEREIGN
     - Overrides base default.
   * - ``jurisdiction``
     - ``JurisdictionLevel``
     -
     - Scope of authority (MUNICIPAL, STATE, NATIONAL, FEDERAL).
   * - ``violence_capacity``
     - ``Probability``
     - 0.0
     - Capacity for coercive force [0, 1].
   * - ``surveillance_capacity``
     - ``Probability``
     - 0.0
     - Capacity for surveillance [0, 1].
   * - ``legal_authority``
     - ``list[str]``
     - ``[]``
     - Specific authorities wielded (e.g. "arrest", "search_warrant").
   * - ``intel_methodology``
     - ``IntelMethodology``
     - (default)
     - Intelligence capabilities (Sparrow-grounded).


Business
~~~~~~~~

Accumulates capital and employs labor.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Field
     - Type
     - Default
     - Description
   * - ``org_type``
     - ``Literal[BUSINESS]``
     -
     - Fixed discriminator.
   * - ``sector``
     - ``str``
     -
     - NAICS sector description (min length 1).
   * - ``employment_count``
     - ``int``
     - 0
     - Number of employees (>= 0).
   * - ``surplus_extraction_rate``
     - ``Coefficient``
     - 0.0
     - Rate of surplus value extraction [0, 1].
   * - ``revenue``
     - ``Currency``
     - 0.0
     - Annual revenue.


PoliticalFaction
~~~~~~~~~~~~~~~~

Contests political power. The player's faction is marked with ``is_player``.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Field
     - Type
     - Default
     - Description
   * - ``org_type``
     - ``Literal[POLITICAL_FACTION]``
     -
     - Fixed discriminator.
   * - ``ideology``
     - ``str``
     -
     - Ideological label (min length 1). E.g. "Marxism-Leninism".
   * - ``is_player``
     - ``bool``
     - ``False``
     - Whether this is the player's faction.
   * - ``relationship_to_player``
     - ``str``
     - "neutral"
     - Relationship state.


CivilSocietyOrg
~~~~~~~~~~~~~~~~

Non-state, non-business collective providing community services.
``legitimacy`` doubles as the credibility factor in the consciousness
effect formula.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Field
     - Type
     - Default
     - Description
   * - ``org_type``
     - ``Literal[CIVIL_SOCIETY]``
     -
     - Fixed discriminator.
   * - ``service_type``
     - ``ServiceType``
     -
     - Domain of service (RELIGIOUS, EDUCATIONAL, MEDIA, LABOR).
   * - ``legitimacy``
     - ``Probability``
     - 0.5
     - Community trust/credibility [0, 1].


Discriminated Union
~~~~~~~~~~~~~~~~~~~

``OrganizationType`` dispatches on the ``org_type`` field for automatic
Pydantic deserialization:

.. code-block:: python

   from pydantic import TypeAdapter
   from babylon.models.entities.organization import OrganizationType

   adapter = TypeAdapter(OrganizationType)
   org = adapter.validate_python({
       "org_type": "state_apparatus",
       "id": "sa-1",
       "name": "Detroit PD",
   })
   # Returns StateApparatus instance


Supporting Models
-----------------

IntelMethodology
~~~~~~~~~~~~~~~~

Intelligence methodology capabilities (Sparrow-grounded). Defines which
social network analysis techniques an intelligence agency can employ.

.. list-table::
   :header-rows: 1
   :widths: 30 15 10 45

   * - Field
     - Type
     - Default
     - Description
   * - ``centrality_analysis``
     - ``bool``
     - ``False``
     - Can identify hub nodes and bridges.
   * - ``equivalence_analysis``
     - ``bool``
     - ``False``
     - Can find structurally equivalent positions (Sparrow 1993).
   * - ``template_matching``
     - ``bool``
     - ``False``
     - Can match against known org templates.
   * - ``temporal_analysis``
     - ``bool``
     - ``False``
     - Can detect activation pattern changes over time.
   * - ``observation_ceiling``
     - ``Probability``
     - 0.2
     - Max fraction of true topology observable [0, 1].

**Presets:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Preset
     - Centrality
     - Equivalence
     - Template
     - Temporal
     - Ceiling
   * - ``local_pd()``
     - Yes
     - No
     - No
     - No
     - 0.2
   * - ``fusion_center()``
     - Yes
     - No
     - No
     - Yes
     - 0.5
   * - ``fbi()``
     - Yes
     - Yes
     - Yes
     - Yes
     - 0.4

Each preset accepts an optional ``defines: OrganizationDefines`` parameter
to override ceiling values from tunable configuration.


KeyFigure
~~~~~~~~~

Individual node within organizational topology. Stored as a separate graph
node with ``_node_type="key_figure"``. COMMAND edges connect KeyFigure nodes
within the same organization.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Field
     - Type
     - Default
     - Description
   * - ``id``
     - ``str``
     -
     - Unique key figure identifier.
   * - ``name``
     - ``str``
     -
     - Name.
   * - ``organization_id``
     - ``str``
     -
     - Parent organization ID.
   * - ``role``
     - ``str``
     -
     - Position title/function.
   * - ``structural_importance``
     - ``Probability``
     - 0.5
     - Topological criticality [0, 1].
   * - ``is_singleton``
     - ``bool``
     - ``False``
     - No structural equivalent (Sparrow).


Enums
-----

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Enum
     - Values
   * - ``OrgType``
     - ``STATE_APPARATUS``, ``BUSINESS``, ``POLITICAL_FACTION``, ``CIVIL_SOCIETY``
   * - ``ClassCharacter``
     - ``BOURGEOIS``, ``PROLETARIAN``, ``CONTESTED``
   * - ``TopologyType``
     - ``STAR``, ``HIERARCHY``, ``MESH``, ``CELL``
   * - ``LegalStanding``
     - ``SOVEREIGN``, ``CHARTERED``, ``REGISTERED``, ``INFORMAL``, ``UNDERGROUND``
   * - ``JurisdictionLevel``
     - ``MUNICIPAL``, ``STATE``, ``NATIONAL``, ``FEDERAL``
   * - ``ServiceType``
     - ``RELIGIOUS``, ``EDUCATIONAL``, ``MEDIA``, ``LABOR``
   * - ``ConsciousnessTendency``
     - ``LIBERAL``, ``FASCIST``, ``REVOLUTIONARY``

**Edge types** (added to ``EdgeType``):

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Type
     - Direction
     - Description
   * - ``MEMBERSHIP``
     - Organization -> SocialClass
     - Weighted population membership.
   * - ``RECRUITMENT``
     - Organization -> SocialClass
     - Active recruitment pipeline.
   * - ``EMPLOYMENT``
     - Business -> SocialClass
     - Employer relationship.
   * - ``COMMAND``
     - KeyFigure -> KeyFigure
     - Internal hierarchy edge.
   * - ``PRESENCE``
     - Organization -> Territory
     - Operational footprint.


Computed Types
--------------

Frozen Pydantic models produced by calculators. Not stored on entities.

**Import:**

.. code-block:: python

   from babylon.organizations.types import (
       ConsciousnessDelta,
       AggregatedEffect,
       CompositionResult,
       TopologyClassification,
   )

ConsciousnessDelta
~~~~~~~~~~~~~~~~~~

Result of a single organization's consciousness effect.

- ``collective_identity_delta: float`` -- Change to CI.
- ``tendency_pressure: ConsciousnessTendency`` -- Direction.
- ``tendency_magnitude: float`` -- Strength (>= 0).
- ``source_org_id: str`` -- Which org caused this.

AggregatedEffect
~~~~~~~~~~~~~~~~~

Result of aggregating multiple deltas.

- ``total_ci_delta: float`` -- Sum of all CI deltas.
- ``dominant_tendency: ConsciousnessTendency | None`` -- Strongest.
- ``tendency_weights: dict[ConsciousnessTendency, float]`` -- Per-tendency magnitudes.
- ``new_ci: float`` -- Clamped [0, 1] result.

CompositionResult
~~~~~~~~~~~~~~~~~

Result of membership composition analysis.

- ``distribution: dict[str, float]`` -- Proportional breakdown.
- ``total_members: float`` -- Total membership count.
- ``axis: str`` -- "class", "community", or "lifecycle".

TopologyClassification
~~~~~~~~~~~~~~~~~~~~~~

Result of COMMAND subgraph classification.

- ``topology_type: TopologyType | None`` -- STAR, HIERARCHY, MESH, CELL, or None.
- ``articulation_points: list[str]`` -- Structurally critical node IDs.
- ``component_count: int`` -- Connected components (>= 0).
- ``is_connected: bool`` -- Whether the subgraph is connected.


Composition Calculators
-----------------------

**Import:**

.. code-block:: python

   from babylon.organizations.composition import (
       class_composition,
       community_composition,
       lifecycle_composition,
       effective_capacity,
   )

class_composition
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def class_composition(org_id: str, G: nx.DiGraph) -> CompositionResult: ...

Computes proportional class breakdown via MEMBERSHIP edges. Groups members
by their ``role`` attribute. Returns ``axis="class"``.

community_composition
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def community_composition(org_id: str, G: nx.DiGraph) -> CompositionResult: ...

Computes community breakdown via MEMBERSHIP edges. Groups members by their
``community`` attribute. Returns ``axis="community"``.

lifecycle_composition
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def lifecycle_composition(org_id: str, G: nx.DiGraph) -> CompositionResult: ...

Computes D/P/D' lifecycle phase distribution via MEMBERSHIP edges.
Groups members by ``lifecycle_phase``. Returns ``axis="lifecycle"``.

effective_capacity
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def effective_capacity(
       lifecycle: CompositionResult,
       elder_capacity_factor: float,
   ) -> float: ...

Computes lifecycle-weighted capacity. Youth contribute 0.0, adults 1.0,
elders ``elder_capacity_factor`` (default 0.2 from ``OrganizationDefines``).
Returns a value in [0, 1].


Consciousness Effect Formula
-----------------------------

**Import:**

.. code-block:: python

   from babylon.organizations.consciousness import (
       consciousness_effect,
       derive_credibility,
       aggregate_consciousness_effects,
   )

derive_credibility
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def derive_credibility(
       org: Organization,
       defines: OrganizationDefines,
       community_workforce: int | None = None,
   ) -> float: ...

Returns credibility factor by subtype:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Subtype
     - Credibility
   * - ``CivilSocietyOrg``
     - ``org.legitimacy``
   * - ``PoliticalFaction``
     - ``defines.credibility_default_faction`` (0.5)
   * - ``StateApparatus``
     - SOVEREIGN: ``defines.credibility_sovereign`` (0.8),
       CHARTERED: ``defines.credibility_chartered`` (0.6),
       other: ``defines.credibility_default_state`` (0.5)
   * - ``Business``
     - ``min(employment_count / community_workforce, 1.0)``

consciousness_effect
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def consciousness_effect(
       org: Organization,
       defines: OrganizationDefines,
       community_workforce: int | None = None,
   ) -> ConsciousnessDelta: ...

Five-factor product formula::

   consciousness_delta = tendency_modifier x cadre_level x cohesion x credibility

Tendency modifiers (from ``OrganizationDefines``):

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Tendency
     - Default
     - CI Behavior
   * - REVOLUTIONARY
     - +0.15
     - Positive CI delta (raises consciousness).
   * - LIBERAL
     - -0.05
     - Negative CI delta (suppresses consciousness).
   * - FASCIST
     - +0.10
     - Zero CI delta. Non-zero tendency pressure only.

aggregate_consciousness_effects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def aggregate_consciousness_effects(
       deltas: list[ConsciousnessDelta],
       current_ci: float,
   ) -> AggregatedEffect: ...

Sums CI deltas. Dominant tendency is the one with highest total magnitude
weight. Result CI clamped to [0, 1].


Topology Classification
-----------------------

**Import:**

.. code-block:: python

   from babylon.organizations.topology import (
       classify_topology,
       identify_key_figures,
       cohesion_loss_on_removal,
   )

classify_topology
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def classify_topology(
       org_id: str,
       member_node_ids: list[str],
       G: nx.DiGraph,
   ) -> TopologyClassification: ...

Extracts the undirected COMMAND subgraph and classifies it.
Priority order:

1. **MESH**: density > 0.6, requires 3+ nodes.
2. **STAR**: hub with degree >= N-1, requires 3+ nodes.
3. **CELL**: articulation points present, has cycles (edges > N-1).
4. **HIERARCHY**: connected tree or sparse connected graph.
5. ``None``: disconnected or fewer than 2 nodes.

identify_key_figures
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def identify_key_figures(
       org_id: str,
       member_node_ids: list[str],
       G: nx.DiGraph,
   ) -> list[KeyFigure]: ...

Returns a ``KeyFigure`` for each articulation point in the COMMAND subgraph.

- ``structural_importance = (components_after_removal - 1) / (n - 1)``
  normalized to [0, 1].
- ``is_singleton = True`` when no other node shares the same degree
  and neighborhood structure.

cohesion_loss_on_removal
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def cohesion_loss_on_removal(
       current_cohesion: float,
       removed_count: int,
       defines: OrganizationDefines,
   ) -> float: ...

Returns ``max(cohesion - count * loss, floor)`` where
``loss = defines.cohesion_loss_per_key_figure`` and
``floor = defines.min_cohesion_threshold``.
Default loss is 0.2 per key figure, floor is 0.05.


Legacy Migration
----------------

**Import:**

.. code-block:: python

   from babylon.organizations.migration import (
       migrate_faction,
       migrate_institution,
       migrate_all,
   )

One-time migration of ``factions.json`` (4 factions) and ``institutions.json``
(7 institutions) into typed Organization subtypes.

migrate_faction
~~~~~~~~~~~~~~~

.. code-block:: python

   def migrate_faction(faction_data: dict) -> PoliticalFaction: ...

Maps ``ideology`` to ``ConsciousnessTendency``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Ideology
     - Tendency
   * - Fascism
     - FASCIST
   * - Liberal Democracy
     - LIBERAL
   * - Marxism-Leninism
     - REVOLUTIONARY
   * - Marxism-Leninism-Maoism
     - REVOLUTIONARY

migrate_institution
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def migrate_institution(inst_data: dict) -> OrganizationType | None: ...

Dispatches by institution type:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Type
     - Target
     - Notes
   * - State, Legal
     - ``StateApparatus``
     - State -> NATIONAL, Legal -> STATE jurisdiction.
   * - Cultural
     - ``CivilSocietyOrg``
     - service_type=MEDIA
   * - Economic
     - ``CivilSocietyOrg``
     - service_type=LABOR
   * - Religious
     - ``CivilSocietyOrg``
     - service_type=RELIGIOUS
   * - Educational
     - ``CivilSocietyOrg``
     - service_type=EDUCATIONAL

Returns ``None`` for "Systemic Racism" (social relation, not organization
per Constitution I.16).

migrate_all
~~~~~~~~~~~

.. code-block:: python

   def migrate_all(
       factions_path: Path,
       institutions_path: Path,
   ) -> dict[str, OrganizationType]: ...

Batch migration. Returns dict keyed by organization ID.
Expected: 4 factions + 6 institutions (1 dropped) = 10 organizations.


Graph Integration
-----------------

Organizations and key figures are stored on ``WorldState`` and participate
in the ``to_graph()``/``from_graph()`` round-trip:

.. code-block:: python

   from babylon.models.world_state import WorldState

   world = WorldState(
       tick=0,
       organizations={"org_1": detroit_pd, "org_2": ford},
       key_figures={"kf_1": pastor},
   )

   graph = world.to_graph()
   # graph.nodes["org_1"]["_node_type"] == "organization"
   # graph.nodes["kf_1"]["_node_type"] == "key_figure"

   reconstructed = WorldState.from_graph(graph, tick=0)
   assert isinstance(reconstructed.organizations["org_1"], StateApparatus)

``to_graph()`` also creates ``PRESENCE`` edges from each organization
to its ``territory_ids``.


OrganizationDefines
-------------------

Tunable parameters in ``GameDefines.organization``:

.. list-table::
   :header-rows: 1
   :widths: 40 10 50

   * - Parameter
     - Default
     - Description
   * - ``elder_capacity_factor``
     - 0.2
     - BLS 65+ LFPR: D'-phase capacity scalar.
   * - ``tendency_modifier_revolutionary``
     - 0.15
     - CI delta for REVOLUTIONARY tendency.
   * - ``tendency_modifier_liberal``
     - -0.05
     - CI delta for LIBERAL tendency.
   * - ``tendency_modifier_fascist``
     - 0.10
     - Tendency pressure for FASCIST.
   * - ``observation_ceiling_local_pd``
     - 0.2
     - Sparrow: Local PD observation ceiling.
   * - ``observation_ceiling_fusion``
     - 0.5
     - Sparrow: Fusion center ceiling.
   * - ``observation_ceiling_fbi``
     - 0.4
     - Sparrow: FBI ceiling.
   * - ``cohesion_loss_per_key_figure``
     - 0.2
     - Cohesion drop per key figure removal.
   * - ``min_cohesion_threshold``
     - 0.05
     - Floor cohesion (never reaches zero).
   * - ``credibility_default_faction``
     - 0.5
     - Default PoliticalFaction credibility.
   * - ``credibility_sovereign``
     - 0.8
     - SOVEREIGN standing credibility.
   * - ``credibility_chartered``
     - 0.6
     - CHARTERED standing credibility.
   * - ``credibility_default_state``
     - 0.5
     - StateApparatus fallthrough credibility.
   * - ``violence_capacity_default``
     - 0.5
     - Default violence capacity.
   * - ``surveillance_capacity_default``
     - 0.3
     - Default surveillance capacity.


See Also
--------

- :doc:`/concepts/organization-model` -- Why the model is structured this way
- :doc:`/reference/institutions` -- Institution Base Model reference (Feature 040)
- :doc:`/reference/data-models` -- SocialClass and Territory models
- :doc:`/reference/formulas` -- Consciousness drift and solidarity formulas
- :py:mod:`babylon.organizations` -- Source code
- :py:mod:`babylon.models.entities.organization` -- Entity source code
